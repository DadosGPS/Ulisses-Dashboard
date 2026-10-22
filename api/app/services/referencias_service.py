"""Referências da academia e comparação entre equipas.

- Referências por idade: cada valor comparado com os atletas da academia com a
  mesma idade (anos inteiros) no dia do teste — todas as épocas contam.
- Referências por estado maturacional (bio-banding): cada valor comparado com
  os atletas no mesmo estado (Khamis-Roche, categorias de Cumming et al. 2017),
  seja qual for a idade. O estado de cada teste é o da medição de altura/peso
  mais próxima (até JANELA_MAT_DIAS dias).
- Comparação de equipas: estatísticas por escalão, teste e momento (T1–T4).

Em cada grupo entra um valor por atleta (o mais recente), para que quem testa
mais vezes não pese mais. Com menos de MIN_COORTE atletas não há percentil.
"""
from __future__ import annotations

import statistics
from datetime import date

import pandas as pd

from app.services.ficha_atleta_service import (
    CATALOGO, MIN_COORTE, POR_CHAVE, _academias_do_utilizador, _avaliacoes_academia, _tem_altura_pais,
    _tem_momento, idade, limites_epoca, momento_por_data, percentil, serie_maturacao,
)

CATEGORIAS_MAT = ["Pré-púbere", "Início da puberdade", "Meio da puberdade", "Fim da puberdade"]
JANELA_MAT_DIAS = 120
METRICAS_COMPARACAO = ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s", "corrida_1km_s",
                       "cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi", "altura_cm", "peso_kg"]
ANTROPOMETRIA = {"altura_cm", "peso_kg"}


# ── Cálculos puros ───────────────────────────────────────────────────────────
def maturacoes(av: pd.DataFrame, pais: dict[str, tuple[float | None, float | None]]) -> pd.DataFrame:
    """Estado maturacional de cada atleta em cada dia com altura e peso.
    Colunas: atleta_id, data, pct_pah, categoria."""
    linhas = []
    if av is not None and not av.empty:
        for aid, g in av.groupby("atleta_id"):
            pai, mae = pais.get(aid, (None, None))
            for m in serie_maturacao(g, pai, mae):
                linhas.append((aid, pd.Timestamp(m["data"]), m["pct_estatura_adulta"], m["categoria"]))
    return pd.DataFrame(linhas, columns=["atleta_id", "data", "pct_pah", "categoria"])


def juntar_maturacao(av: pd.DataFrame, mats: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta a `av` a coluna «categoria_mat»: o estado da medição mais
    próxima do mesmo atleta, até JANELA_MAT_DIAS dias de distância."""
    if av is None or av.empty:
        return (av if av is not None else pd.DataFrame()).assign(categoria_mat=pd.Series(dtype=object))
    if mats is None or mats.empty:
        return av.assign(categoria_mat=None)
    esq = av.reset_index(drop=True).assign(_ordem=lambda d: range(len(d))).sort_values("data")
    esq["data"] = pd.to_datetime(esq["data"]).astype("datetime64[ns]")
    dir_ = mats[["atleta_id", "data", "categoria"]].rename(columns={"categoria": "categoria_mat"})
    dir_ = dir_.assign(data=pd.to_datetime(dir_["data"]).astype("datetime64[ns]")).sort_values("data")
    juntos = pd.merge_asof(esq, dir_, on="data", by="atleta_id", direction="nearest",
                           tolerance=pd.Timedelta(days=JANELA_MAT_DIAS))
    juntos = juntos.sort_values("_ordem").drop(columns="_ordem").reset_index(drop=True)
    juntos["categoria_mat"] = juntos["categoria_mat"].astype(object).where(juntos["categoria_mat"].notna(), None)
    return juntos


def amostras(av: pd.DataFrame) -> dict[str, dict]:
    """{"idade": {(metrica, idade_int): [valores]}, "mat": {(metrica, categoria): [valores]}}
    — um valor por atleta em cada grupo (o mais recente)."""
    out: dict[str, dict] = {"idade": {}, "mat": {}}
    if av is None or av.empty:
        return out
    d = av.sort_values("data")
    com_idade = d[d["idade"].notna()].assign(_idade=lambda x: x["idade"].astype(float).astype(int))
    for (met, ida), g in com_idade.groupby(["metrica", "_idade"]):
        out["idade"][(met, int(ida))] = g.groupby("atleta_id")["valor"].last().astype(float).tolist()
    if "categoria_mat" in d.columns:
        com_mat = d[d["categoria_mat"].notna()]
        for (met, cat), g in com_mat.groupby(["metrica", "categoria_mat"]):
            out["mat"][(met, cat)] = g.groupby("atleta_id")["valor"].last().astype(float).tolist()
    return out


def resumo_ref(vals: list[float]) -> dict:
    """n e, com amostra suficiente, P25 / P50 / P75."""
    vals = sorted(v for v in vals if v is not None)
    if len(vals) < MIN_COORTE:
        return {"n": len(vals)}
    q = statistics.quantiles(vals, n=4, method="inclusive")
    return {"n": len(vals), "p25": round(q[0], 3), "p50": round(q[1], 3), "p75": round(q[2], 3)}


def anotar(entrada: dict, metrica: str, am: dict) -> dict:
    """Junta a um valor {valor, idade?, cat?} o percentil e a referência por
    idade e por estado maturacional (este último não se aplica à antropometria)."""
    meta = POR_CHAVE.get(metrica, {})
    mm = meta.get("maior_melhor")
    out = dict(entrada)
    ida = entrada.get("idade")
    if ida is not None:
        amostra = am["idade"].get((metrica, int(ida)), [])
        out["ref_idade"] = {"idade": int(ida), **resumo_ref(amostra)}
        out["p_idade"] = percentil(float(entrada["valor"]), amostra, mm)
    cat = entrada.get("cat")
    if cat and metrica not in ANTROPOMETRIA:
        amostra = am["mat"].get((metrica, cat), [])
        out["ref_mat"] = {"categoria": cat, **resumo_ref(amostra)}
        out["p_mat"] = percentil(float(entrada["valor"]), amostra, mm)
    return out


def valores_por_momento_ref(serie: pd.DataFrame) -> dict[str, dict[int, dict]]:
    """Como valores_por_momento, mas cada valor leva também a idade e o estado
    maturacional nesse dia: {metrica: {momento: {valor, data, idade, cat}}}."""
    out: dict[str, dict[int, dict]] = {}
    if serie is None or serie.empty:
        return out
    s = serie.copy()
    if "momento" not in s.columns:
        s["momento"] = None
    s["momento"] = [int(m) if pd.notna(m) else momento_por_data(d.date()) for m, d in zip(s["momento"], s["data"])]
    for (metrica, mom), g in s.sort_values("data").groupby(["metrica", "momento"]):
        ult = g.iloc[-1]
        cat = ult.get("categoria_mat") if "categoria_mat" in g.columns else None
        out.setdefault(metrica, {})[int(mom)] = {
            "valor": round(float(ult["valor"]), 3), "data": ult["data"].strftime("%Y-%m-%d"),
            "idade": None if pd.isna(ult["idade"]) else round(float(ult["idade"]), 2),
            "cat": cat if isinstance(cat, str) else None,
        }
    return out


def estatisticas(vals: list[float]) -> dict | None:
    vals = [float(v) for v in vals if v is not None]
    if not vals:
        return None
    return {
        "n": len(vals), "media": round(statistics.fmean(vals), 3),
        "dp": round(statistics.stdev(vals), 3) if len(vals) > 1 else None,
        "mediana": round(statistics.median(vals), 3), "min": round(min(vals), 3), "max": round(max(vals), 3),
    }


# ── Acesso à base de dados ───────────────────────────────────────────────────
def preparar(cur, academia_id: str) -> tuple[pd.DataFrame, dict]:
    """Todas as avaliações da academia, com momento, idade e estado
    maturacional, e as amostras de referência (todas as épocas)."""
    av = _avaliacoes_academia(cur, academia_id)
    if not av.empty and _tem_momento(cur):
        cur.execute("select id::text, momento from avaliacoes where academia_id = %s and momento is not null", (academia_id,))
        av["momento"] = av["id"].map(dict(cur.fetchall()))
    pais: dict[str, tuple] = {}
    if _tem_altura_pais(cur):
        cur.execute("select id::text, altura_pai_cm::float, altura_mae_cm::float from atletas where academia_id = %s", (academia_id,))
        pais = {a: (p, m) for a, p, m in cur.fetchall()}
    av = juntar_maturacao(av, maturacoes(av, pais))
    return av, amostras(av)


def anotar_valores(vals: dict[str, dict[int, dict]], am: dict) -> dict[str, dict[int, dict]]:
    return {met: {m: anotar(v, met, am) for m, v in por_m.items()} for met, por_m in vals.items()}


def comparar_equipas(user_id: str, epoca: str | None = None) -> dict:
    from app.core.db import get_conn
    from app.services.academia_service import ESCALOES, epoca_atual

    with get_conn() as conn:
        with conn.cursor() as cur:
            academias = _academias_do_utilizador(cur, user_id)
            if not academias:
                raise PermissionError("Ainda não pertences a nenhuma academia.")
            academia_id = academias[0]
            cur.execute(
                "select id::text, escalao, epoca from teams where academia_id = %s and escalao is not null and epoca is not null",
                (academia_id,),
            )
            equipas = cur.fetchall()
            epocas = sorted({e for _, _, e in equipas}, reverse=True)
            if not epoca:
                epoca = epoca_atual() if epoca_atual() in epocas else (epocas[0] if epocas else epoca_atual())
            da_epoca = sorted([(t, esc) for t, esc, e in equipas if e == epoca],
                              key=lambda x: ESCALOES.index(x[1]) if x[1] in ESCALOES else 99)
            plantel: dict[str, list] = {}
            for tid, _ in da_epoca:
                cur.execute(
                    """select a.id::text, a.nome, a.data_nascimento from players p join atletas a on a.id = p.atleta_id
                       where p.team_id = %s and p.ativo order by a.nome""",
                    (tid,),
                )
                plantel[tid] = cur.fetchall()
            av, am = preparar(cur, academia_id)

    ini, fim = limites_epoca(epoca)
    if not av.empty:
        av = av[(av["data"].dt.date >= ini) & (av["data"].dt.date <= fim)]
    hoje = date.today()
    por_atleta: dict[str, dict] = {}
    saida_equipas = []
    for tid, esc in da_epoca:
        linhas = []
        for aid, nome, nasc in plantel[tid]:
            if aid not in por_atleta:
                serie = av[av["atleta_id"] == aid] if not av.empty else av
                por_atleta[aid] = {"atleta_id": aid, "nome": nome, "idade": idade(nasc, hoje), "equipas": [],
                                   "valores": anotar_valores(valores_por_momento_ref(serie), am)}
            por_atleta[aid]["equipas"].append(esc)
            linhas.append(por_atleta[aid])
        stats: dict[str, dict[int, dict]] = {}
        for k in METRICAS_COMPARACAO:
            for m in range(1, 5):
                pontos = [(a["nome"], a["valores"][k][m]["valor"]) for a in linhas if m in a["valores"].get(k, {})]
                st = estatisticas([v for _, v in pontos])
                if st:
                    stats.setdefault(k, {})[m] = {**st, "valores": [{"nome": n, "valor": v} for n, v in pontos]}
        # Estado maturacional de cada atleta em cada momento: o da medição da altura.
        mats: dict[int, dict[str, int]] = {}
        for a in linhas:
            for m, v in a["valores"].get("altura_cm", {}).items():
                if v.get("cat"):
                    mats.setdefault(m, {}).setdefault(v["cat"], 0)
                    mats[m][v["cat"]] += 1
        idades = [a["idade"] for a in linhas if a["idade"] is not None]
        saida_equipas.append({
            "team_id": tid, "escalao": esc, "n_atletas": len(linhas),
            "idade_media": round(statistics.fmean(idades), 1) if idades else None,
            "estatisticas": stats, "maturacao": mats,
        })
    return {
        "epoca": epoca, "epocas": epocas or [epoca], "inicio": ini.isoformat(), "fim": fim.isoformat(),
        "metricas": [POR_CHAVE[k] for k in METRICAS_COMPARACAO],
        "categorias_mat": CATEGORIAS_MAT, "min_coorte": MIN_COORTE,
        "equipas": saida_equipas,
        "atletas": list(por_atleta.values()),
    }


__all__ = ["CATALOGO", "comparar_equipas", "preparar", "anotar_valores", "valores_por_momento_ref"]
