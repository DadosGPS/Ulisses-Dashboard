"""Perfil do jogador a partir dos testes neuromusculares, com STEN scores.

Converte cada teste num STEN (1–10) para pôr tudo na mesma escala e ser
legível de imediato pelo staff. STEN = 5.5 + 2·z, limitado a [1, 10], com o
z-score calculado VS A POSIÇÃO do jogador (fallback ao plantel quando a
posição tem poucos jogadores). Métricas onde "menos é melhor" (tempo de
contacto, assimetria) têm o z invertido, para STEN alto = sempre melhor.
"""
import math

import pandas as pd

from app.core.db import get_conn

# maior_melhor=False → menos é melhor (inverte o z para STEN alto = melhor).
METRICAS_TESTE = [
    {"chave": "altura_salto_cm", "col": "altura_salto_cm", "label": "Altura de Salto", "unidade": "cm", "grupo": "Potência", "maior_melhor": True, "casas": 1},
    {"chave": "potencia_rel_wkg", "col": "potencia_rel_wkg", "label": "Potência Rel.", "unidade": "W/kg", "grupo": "Potência", "maior_melhor": True, "casas": 1},
    {"chave": "rfd", "col": "rfd", "label": "RFD (força explosiva)", "unidade": "N/s", "grupo": "Força", "maior_melhor": True, "casas": 0},
    {"chave": "rsi", "col": "rsi", "label": "RSI (reatividade)", "unidade": "", "grupo": "Reatividade", "maior_melhor": True, "casas": 2},
    {"chave": "tempo_contacto_ms", "col": "tempo_contacto_ms", "label": "T. Contacto", "unidade": "ms", "grupo": "Reatividade", "maior_melhor": False, "casas": 0},
    {"chave": "assimetria_pct", "col": "assimetria_pct", "label": "Assimetria", "unidade": "%", "grupo": "Equilíbrio", "maior_melhor": False, "casas": 1},
]


def _sten(valor: float, media: float, desvio: float, maior_melhor: bool) -> int | None:
    if desvio is None or desvio == 0 or media is None:
        return None
    z = (valor - media) / desvio
    if not maior_melhor:
        z = -z
    return int(max(1, min(10, round(5.5 + 2 * z))))


def obter_perfis(team_id: str) -> dict:
    vazio = {"tem_dados": False, "metricas": [], "jogadores": []}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select p.nome, coalesce(p.posicao, '—') as posicao, t.data,
                           t.altura_salto_cm, t.potencia_rel_wkg, t.rfd, t.rsi,
                           t.tempo_contacto_ms, t.assimetria_pct
                    from testes_neuromusculares t
                    join players p on p.id = t.player_id
                    where t.team_id = %s
                    """,
                    (team_id,),
                )
                rows = cur.fetchall()
    except Exception:
        return vazio

    if not rows:
        return vazio

    cols = ["nome", "posicao", "data", "altura_salto_cm", "potencia_rel_wkg", "rfd", "rsi", "tempo_contacto_ms", "assimetria_pct"]
    df = pd.DataFrame(rows, columns=cols)
    for m in METRICAS_TESTE:
        df[m["col"]] = pd.to_numeric(df[m["col"]], errors="coerce")

    # Teste mais recente por jogador.
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.sort_values("data").groupby("nome", as_index=False).last()

    metricas_presentes = [m for m in METRICAS_TESTE if df[m["col"]].notna().any()]
    if not metricas_presentes:
        return vazio

    # Estatísticas do plantel inteiro, por métrica (referência do STEN).
    stats_global: dict[str, tuple] = {}
    for m in metricas_presentes:
        col = m["col"]
        s = df[col].dropna()
        stats_global[col] = (float(s.mean()), float(s.std(ddof=0))) if len(s) >= 2 else (None, None)

    jogadores = []
    for _, row in df.iterrows():
        pos = row["posicao"]
        testes = {}
        stens = []
        for m in metricas_presentes:
            col = m["col"]
            valor = row[col]
            if valor is None or (isinstance(valor, float) and math.isnan(valor)):
                continue
            # Referência = plantel inteiro (decisão do utilizador).
            media, desvio = stats_global.get(col, (None, None))
            sten = _sten(float(valor), media, desvio, m["maior_melhor"]) if media is not None else None
            testes[m["chave"]] = {"valor": round(float(valor), m["casas"]), "sten": sten}
            if sten is not None:
                stens.append(sten)
        jogadores.append({
            "jogador": row["nome"],
            "posicao": pos,
            "data": row["data"].strftime("%Y-%m-%d") if pd.notna(row["data"]) else None,
            "referencia": "plantel",
            "sten_medio": round(sum(stens) / len(stens), 1) if stens else None,
            "testes": testes,
        })
    jogadores.sort(key=lambda j: (j["sten_medio"] is None, -(j["sten_medio"] or 0)))

    return {
        "tem_dados": True,
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "grupo": m["grupo"], "maior_melhor": m["maior_melhor"]} for m in metricas_presentes],
        "jogadores": jogadores,
    }


# ── Perfil a partir dos testes da academia (T1–T4) ───────────────────────────
METRICAS_ACADEMIA = ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s", "corrida_1km_s",
                     "cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi"]


def escolher_valor(por_momento: dict, momento: int | None) -> dict | None:
    """Valor de um teste no momento pedido (T1–T4) ou, sem momento, o mais
    recente da época."""
    if not por_momento:
        return None
    if momento is not None:
        return por_momento.get(momento) or por_momento.get(str(momento))
    chave = max(por_momento, key=lambda m: int(m))
    return por_momento[chave]


def perfis_de_relatorio(rel: dict, momento: int | None) -> dict:
    """Constrói o perfil (valor + STEN vs plantel) a partir do relatório da
    época da academia. Cálculo puro — testável sem base de dados."""
    from app.services.ficha_atleta_service import POR_CHAVE

    metricas = [POR_CHAVE[k] for k in METRICAS_ACADEMIA]
    linhas = []
    for a in rel.get("atletas", []):
        vals = {}
        for m in metricas:
            v = escolher_valor(a["valores"].get(m["chave"], {}), momento)
            if v and v.get("valor") is not None:
                vals[m["chave"]] = v
        linhas.append((a, vals))

    # Todos os testes da bateria aparecem, mesmo ainda sem valores (coluna «—»).
    presentes = metricas
    stats: dict[str, tuple] = {}
    for m in presentes:
        s = pd.Series([v[m["chave"]]["valor"] for _, v in linhas if m["chave"] in v], dtype=float)
        stats[m["chave"]] = (float(s.mean()), float(s.std(ddof=0)), int(len(s))) if len(s) >= 2 else (None, None, int(len(s)))

    jogadores = []
    for a, vals in linhas:
        testes, stens, datas = {}, [], []
        for m in presentes:
            v = vals.get(m["chave"])
            if not v:
                continue
            media, desvio, _ = stats[m["chave"]]
            sten = _sten(float(v["valor"]), media, desvio, m["maior_melhor"]) if media is not None else None
            testes[m["chave"]] = {"valor": round(float(v["valor"]), m["casas"]), "sten": sten, "data": v.get("data"),
                                  "p_idade": v.get("p_idade")}
            datas.append(v.get("data"))
            if sten is not None:
                stens.append(sten)
        jogadores.append({
            "jogador": a["nome"], "atleta_id": a["atleta_id"], "posicao": a.get("posicao") or "—",
            "data": max((d for d in datas if d), default=None), "referencia": "plantel",
            "sten_medio": round(sum(stens) / len(stens), 1) if stens else None,
            "n_testes": len(testes), "testes": testes,
        })
    jogadores.sort(key=lambda j: (j["sten_medio"] is None, -(j["sten_medio"] or 0), j["jogador"]))
    return {
        "tem_dados": any(j["testes"] for j in jogadores),
        "fonte": "academia",
        "momento": momento,
        "momentos": sorted(int(m) for m in rel.get("momentos", {})),
        "rotulo": rel.get("rotulo"),
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "grupo": m["grupo"],
                      "maior_melhor": m["maior_melhor"], "casas": m["casas"]} for m in presentes],
        "medias": {k: {"media": round(v[0], 3) if v[0] is not None else None, "n": v[2]} for k, v in stats.items()},
        "jogadores": [j for j in jogadores if j["testes"]],
        "sem_testes": [j["jogador"] for j in jogadores if not j["testes"]],
    }


def obter_perfis_academia(user_id: str, team_id: str, momento: int | None = None) -> dict | None:
    """Perfil com os testes da academia; None se a equipa não for da academia
    ou ainda não tiver testes (a página cai para os testes importados)."""
    from app.services import ficha_atleta_service as ficha
    try:
        if not ficha.disponivel():
            return None
        rel = ficha.relatorio_epoca(user_id, team_id)
    except Exception:
        return None
    out = perfis_de_relatorio(rel, momento)
    return out if out["tem_dados"] else None
