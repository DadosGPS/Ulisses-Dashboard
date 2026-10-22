"""Ficha longitudinal do atleta — todas as épocas numa só ficha.

Junta, para cada atleta da academia:
  • o percurso (épocas × escalões × equipas);
  • as avaliações físicas ao longo dos anos — as registadas na ficha
    (tabela `avaliacoes`) e os testes neuromusculares já importados com o GPS;
  • a maturação biológica (maturity offset / idade prevista do PHV);
  • entrada vs última avaliação, em valor e em percentil face aos atletas da
    academia com a mesma idade;
  • a carga de jogo por 90' em cada época.

As funções de cálculo são puras (testáveis); o acesso à base de dados está no
fim do ficheiro.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

# ── Catálogo de métricas ─────────────────────────────────────────────────────
# maior_melhor: True (mais = melhor), False (menos = melhor, ex.: tempos),
# None (neutro, ex.: antropometria — sem "melhor" nem percentil de desempenho).
CATALOGO = [
    {"chave": "altura_cm", "label": "Altura", "unidade": "cm", "grupo": "Antropometria", "maior_melhor": None, "casas": 1},
    {"chave": "peso_kg", "label": "Peso", "unidade": "kg", "grupo": "Antropometria", "maior_melhor": None, "casas": 1},
    {"chave": "sprint_5m_s", "label": "5 m", "unidade": "s", "grupo": "Velocidade", "maior_melhor": False, "casas": 2},
    {"chave": "sprint_10m_s", "label": "10 m", "unidade": "s", "grupo": "Velocidade", "maior_melhor": False, "casas": 2},
    {"chave": "sprint_20m_s", "label": "20 m", "unidade": "s", "grupo": "Velocidade", "maior_melhor": False, "casas": 2},
    {"chave": "sprint_30m_s", "label": "30 m", "unidade": "s", "grupo": "Velocidade", "maior_melhor": False, "casas": 2},
    {"chave": "corrida_1km_s", "label": "1 km", "unidade": "s", "grupo": "Resistência", "maior_melhor": False, "casas": 0},
    {"chave": "cmj_cm", "label": "CMJ", "unidade": "cm", "grupo": "Saltos", "maior_melhor": True, "casas": 1},
    {"chave": "dj_altura_cm", "label": "Drop jump — altura", "unidade": "cm", "grupo": "Saltos", "maior_melhor": True, "casas": 1},
    {"chave": "dj_contacto_ms", "label": "Drop jump — contacto", "unidade": "ms", "grupo": "Saltos", "maior_melhor": False, "casas": 0},
    {"chave": "rsi", "label": "RSI", "unidade": "", "grupo": "Saltos", "maior_melhor": True, "casas": 2},
    {"chave": "potencia_rel_wkg", "label": "Potência relativa", "unidade": "W/kg", "grupo": "Saltos", "maior_melhor": True, "casas": 1},
]
# Baterias de testes por separador de equipa (ordem das colunas).
BATERIAS = {
    "velocidade": {"titulo": "Velocidade", "metricas": ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s"]},
    "resistencia": {"titulo": "Resistência 1 km", "metricas": ["corrida_1km_s"]},
    "maturacao": {"titulo": "Maturação", "metricas": ["altura_cm", "peso_kg"]},
    "saltos": {"titulo": "CMJ e Drop jump", "metricas": ["cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi"]},
}
POR_CHAVE = {m["chave"]: m for m in CATALOGO}

# Testes neuromusculares importados com o GPS → métricas do catálogo.
DE_TESTES = {"altura_salto_cm": "cmj_cm", "potencia_rel_wkg": "potencia_rel_wkg", "rsi": "rsi"}

MIN_COORTE = 5  # amostra mínima por idade para mostrar um percentil


# ── Cálculos puros ───────────────────────────────────────────────────────────
def momento_por_data(d: date) -> int:
    """Momento de avaliação deduzido pela data (época jul→jun): T1 jul–set,
    T2 out–dez, T3 jan–mar, T4 abr–jun."""
    return {7: 1, 8: 1, 9: 1, 10: 2, 11: 2, 12: 2, 1: 3, 2: 3, 3: 3}.get(d.month, 4)


def limites_epoca(epoca: str | None, hoje: date | None = None) -> tuple[date, date]:
    """'2026/27' → 2026-07-01 a 2027-06-30 (sem época: a época de hoje)."""
    try:
        ini = int((epoca or "")[:4])
    except ValueError:
        d = hoje or date.today()
        ini = d.year if d.month >= 7 else d.year - 1
    return date(ini, 7, 1), date(ini + 1, 6, 30)


def rsi_drop_jump(altura_cm: float | None, contacto_ms: float | None) -> float | None:
    """RSI = altura do salto (m) ÷ tempo de contacto (s)."""
    if not altura_cm or not contacto_ms:
        return None
    return round((altura_cm / 100) / (contacto_ms / 1000), 2)


def idade(nascimento: date | None, dia: date) -> float | None:
    if not nascimento:
        return None
    return round((pd.Timestamp(dia) - pd.Timestamp(nascimento)).days / 365.25, 2)


def maturacao(idade_anos: float | None, altura_cm: float | None, peso_kg: float | None,
              altura_pai_cm: float | None, altura_mae_cm: float | None) -> dict | None:
    """Estado maturacional pelo método de Khamis-Roche (ver khamis_roche.py):
    estatura adulta prevista, % já atingida e categoria de Cumming et al. 2017."""
    from app.services.khamis_roche import estatura_adulta_prevista
    if idade_anos is None:
        return None
    return estatura_adulta_prevista(idade_anos, altura_cm, peso_kg, altura_pai_cm, altura_mae_cm)


def percentil(valor: float, amostra: list[float], maior_melhor: bool | None) -> float | None:
    """Percentil de desempenho (0–100, alto = melhor) face à amostra.
    Métricas neutras (antropometria) devolvem o percentil "bruto" (alto = maior)."""
    vals = [v for v in amostra if v is not None]
    if len(vals) < MIN_COORTE:
        return None
    abaixo = sum(1 for v in vals if v < valor) + 0.5 * sum(1 for v in vals if v == valor)
    p = abaixo / len(vals) * 100
    p = 100 - p if maior_melhor is False else p
    return float(min(99, max(1, round(p))))  # P1–P99, como é habitual


def entrada_vs_ultima(serie: pd.DataFrame, coorte: pd.DataFrame) -> list[dict]:
    """Por métrica: primeira e última avaliação, variação e percentil (face aos
    atletas da academia com a mesma idade inteira na data do teste).

    `serie`: colunas metrica, data, valor, idade.
    `coorte`: colunas metrica, idade, valor (todas as avaliações da academia).
    """
    out = []
    if serie is None or serie.empty:
        return out
    for metrica, g in serie.sort_values("data").groupby("metrica", sort=False):
        meta = POR_CHAVE.get(metrica)
        if not meta:
            continue
        ini, fim = g.iloc[0], g.iloc[-1]

        def pct(linha):
            if pd.isna(linha["idade"]) or coorte is None or coorte.empty:
                return None
            idade_int = int(linha["idade"])
            amostra = coorte[(coorte["metrica"] == metrica) & (coorte["idade"].astype(float).astype(int) == idade_int)]["valor"].tolist()
            return percentil(float(linha["valor"]), amostra, meta["maior_melhor"])

        variacao = float(fim["valor"]) - float(ini["valor"])
        var_pct = round(variacao / float(ini["valor"]) * 100, 1) if float(ini["valor"]) else None
        melhorou = None
        if len(g) > 1 and meta["maior_melhor"] is not None:
            melhorou = variacao > 0 if meta["maior_melhor"] else variacao < 0
        out.append({
            "metrica": metrica, "label": meta["label"], "unidade": meta["unidade"], "grupo": meta["grupo"],
            "maior_melhor": meta["maior_melhor"], "casas": meta["casas"],
            "entrada": {"data": ini["data"].strftime("%Y-%m-%d"), "valor": round(float(ini["valor"]), meta["casas"]),
                        "idade": None if pd.isna(ini["idade"]) else round(float(ini["idade"]), 1), "percentil": pct(ini)},
            "ultima": {"data": fim["data"].strftime("%Y-%m-%d"), "valor": round(float(fim["valor"]), meta["casas"]),
                       "idade": None if pd.isna(fim["idade"]) else round(float(fim["idade"]), 1), "percentil": pct(fim)},
            "n_avaliacoes": int(len(g)),
            "variacao": round(variacao, meta["casas"]),
            "variacao_pct": var_pct,
            "melhorou": melhorou,
        })
    ordem = {m["chave"]: i for i, m in enumerate(CATALOGO)}
    out.sort(key=lambda x: ordem.get(x["metrica"], 99))
    return out


def serie_maturacao(serie: pd.DataFrame, altura_pai_cm: float | None, altura_mae_cm: float | None) -> list[dict]:
    """Maturação em cada dia com altura E peso (e a altura dos pais na ficha)."""
    if serie is None or serie.empty or not altura_pai_cm or not altura_mae_cm:
        return []
    antrop = serie[serie["metrica"].isin(["altura_cm", "peso_kg"])]
    out = []
    for dia, g in antrop.groupby("data"):
        valores = dict(zip(g["metrica"], g["valor"]))
        ida = g["idade"].dropna()
        if ida.empty or "altura_cm" not in valores or "peso_kg" not in valores:
            continue
        m = maturacao(float(ida.iloc[0]), float(valores["altura_cm"]), float(valores["peso_kg"]), float(altura_pai_cm), float(altura_mae_cm))
        if m:
            out.append({"data": dia.strftime("%Y-%m-%d"), "idade": round(float(ida.iloc[0]), 1), "altura_cm": round(float(valores["altura_cm"]), 1), **m})
    return out


def carga_jogo_por_epoca(sessoes: pd.DataFrame) -> list[dict]:
    """Por época: média por 90' (jogos com ≥ 60') de distância, HSR e sprint,
    pico de velocidade, nº de jogos e minutos. `sessoes` tem a coluna «Época»."""
    from app.services.referencia_jogo import COL_DURACAO, MIN_MINUTOS, mascara_jogo

    if sessoes is None or sessoes.empty:
        return []
    jogos = sessoes[mascara_jogo(sessoes)]
    out = []
    for epoca, g in jogos.groupby("Época", sort=True):
        completos = g[g[COL_DURACAO] >= MIN_MINUTOS] if COL_DURACAO in g.columns else g.iloc[0:0]
        linha = {
            "epoca": epoca,
            "escalao": g["Escalão"].dropna().iloc[0] if "Escalão" in g.columns and g["Escalão"].notna().any() else None,
            "jogos": int(len(g)),
            "minutos": int(g[COL_DURACAO].fillna(0).sum()) if COL_DURACAO in g.columns else None,
            "jogos_completos": int(len(completos)),
        }
        for col, chave in (("Distância Total (m)", "distancia_90"), ("HSR (m)", "hsr_90"), ("Sprint (m)", "sprint_90")):
            if col in completos.columns and not completos.empty and completos[col].notna().any():
                linha[chave] = round(float((completos[col] / completos[COL_DURACAO] * 90).mean()), 0)
            else:
                linha[chave] = None
        linha["vmax"] = round(float(g["Vel. Máx (km/h)"].max()), 1) if "Vel. Máx (km/h)" in g.columns and g["Vel. Máx (km/h)"].notna().any() else None
        out.append(linha)
    return out


# ── Acesso à base de dados ───────────────────────────────────────────────────
MSG_MIGRACAO = (
    "As avaliações ainda não existem na base de dados. Aplica as migrações "
    "0009_academia.sql e 0010_avaliacoes_atleta.sql no SQL Editor do Supabase."
)


def disponivel() -> bool:
    from app.core.db import get_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.avaliacoes') is not null and to_regclass('public.atletas') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


def _academias_do_utilizador(cur, user_id: str) -> list[str]:
    cur.execute("select academia_id from academia_membros where user_id = %s", (user_id,))
    return [str(r[0]) for r in cur.fetchall()]


def _tem_altura_pais(cur) -> bool:
    cur.execute("select exists (select 1 from information_schema.columns where table_name = 'atletas' and column_name = 'altura_pai_cm')")
    return bool(cur.fetchone()[0])


def _verificar_atleta(cur, user_id: str, atleta_id: str) -> tuple[str, str, date | None, str | None, str | None]:
    cur.execute(
        """
        select a.academia_id, a.nome, a.data_nascimento, a.posicao_principal, a.pe_dominante
        from atletas a join academia_membros am on am.academia_id = a.academia_id
        where a.id = %s and am.user_id = %s
        """,
        (atleta_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise PermissionError("Atleta não encontrado nesta academia.")
    return str(row[0]), row[1], row[2], row[3], row[4]


def _altura_pais(cur, atleta_id: str) -> tuple[float | None, float | None, bool | None]:
    if not _tem_altura_pais(cur):
        return None, None, None
    cur.execute("select altura_pai_cm::float, altura_mae_cm::float, altura_pais_medida from atletas where id = %s", (atleta_id,))
    row = cur.fetchone()
    return (row[0], row[1], row[2]) if row else (None, None, None)


def _avaliacoes_academia(cur, academia_id: str, atleta_id: str | None = None) -> pd.DataFrame:
    """Avaliações da academia (ou de um atleta): as da ficha + os testes
    neuromusculares importados. Colunas: id, atleta_id, data, metrica, valor,
    origem, team_id, nascimento."""
    filtro_a = "and av.atleta_id = %s" if atleta_id else ""
    filtro_t = "and p.atleta_id = %s" if atleta_id else ""
    params_a = [academia_id] + ([atleta_id] if atleta_id else [])
    cur.execute(
        f"""
        select av.id::text, av.atleta_id::text, av.data, av.metrica, av.valor::float, 'ficha', av.team_id::text, a.data_nascimento
        from avaliacoes av join atletas a on a.id = av.atleta_id
        where av.academia_id = %s {filtro_a}
        """,
        params_a,
    )
    linhas = list(cur.fetchall())
    params_t = [academia_id] + ([atleta_id] if atleta_id else [])
    cur.execute(
        f"""
        select t.id::text, p.atleta_id::text, t.data, t.altura_salto_cm::float, t.potencia_rel_wkg::float, t.rsi::float,
               t.team_id::text, a.data_nascimento
        from testes_neuromusculares t
        join players p on p.id = t.player_id
        join atletas a on a.id = p.atleta_id
        where a.academia_id = %s and t.data is not null {filtro_t}
        """,
        params_t,
    )
    for tid, aid, dia, salto, pot, rsi, team_id, nasc in cur.fetchall():
        for col, valor in (("altura_salto_cm", salto), ("potencia_rel_wkg", pot), ("rsi", rsi)):
            if valor is not None:
                linhas.append((f"teste:{tid}:{col}", aid, dia, DE_TESTES[col], valor, "importado", team_id, nasc))
    df = pd.DataFrame(linhas, columns=["id", "atleta_id", "data", "metrica", "valor", "origem", "team_id", "nascimento"])
    if df.empty:
        return df.assign(idade=pd.Series(dtype=float))
    df["data"] = pd.to_datetime(df["data"])
    df["idade"] = [idade(n, d.date()) if n else None for n, d in zip(df["nascimento"], df["data"])]
    # Se a mesma métrica foi registada na ficha e importada no mesmo dia, fica a da ficha.
    df = df.sort_values("origem").drop_duplicates(subset=["atleta_id", "data", "metrica"], keep="first")
    return df


def listar_atletas(user_id: str) -> dict:
    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            academias = _academias_do_utilizador(cur, user_id)
            if not academias:
                return {"atletas": [], "catalogo": CATALOGO}
            cur.execute(
                """
                with percurso as (
                  select p.atleta_id, t.escalao, t.epoca, t.id as team_id,
                         row_number() over (partition by p.atleta_id order by t.epoca desc nulls last, t.criado_em desc) as rn
                  from players p join teams t on t.id = p.team_id
                  where p.atleta_id is not null
                )
                select a.id::text, a.nome, a.data_nascimento, a.posicao_principal,
                       (select count(distinct epoca) from percurso pc where pc.atleta_id = a.id) as epocas,
                       (select escalao from percurso pc where pc.atleta_id = a.id and rn = 1) as escalao_atual,
                       (select epoca from percurso pc where pc.atleta_id = a.id and rn = 1) as epoca_atual,
                       (select count(*) from avaliacoes av where av.atleta_id = a.id) as n_avaliacoes,
                       (select max(av.data) from avaliacoes av where av.atleta_id = a.id) as ultima_avaliacao
                from atletas a where a.academia_id = any(%s::uuid[])
                order by a.nome
                """,
                (academias,),
            )
            linhas = cur.fetchall()
            cur.execute(
                """
                select p.atleta_id::text, t.id::text, t.escalao, t.epoca, t.nome
                from players p join teams t on t.id = p.team_id
                where p.ativo and p.atleta_id is not null and t.academia_id = any(%s::uuid[])
                order by t.epoca desc nulls last, t.escalao
                """,
                (academias,),
            )
            consent: dict[str, bool] = {}
            if _tem_consentimento(cur):
                cur.execute("select id::text, consentimento_dados_em is not null from atletas where academia_id = any(%s::uuid[])", (academias,))
                consent = dict(cur.fetchall())
            equipas: dict[str, list[dict]] = {}
            for aid, tid, esc, ep, nome_t in cur.fetchall():
                equipas.setdefault(aid, []).append(
                    {"team_id": tid, "escalao": esc, "epoca": ep, "rotulo": f"{esc} · {ep}" if esc and ep else nome_t})
    hoje = date.today()
    return {
        "catalogo": CATALOGO,
        "atletas": [
            {"atleta_id": aid, "nome": nome, "data_nascimento": nasc.isoformat() if nasc else None,
             "idade": idade(nasc, hoje), "posicao": pos, "epocas": int(ep or 0),
             "escalao_atual": esc, "epoca_atual": epa, "n_avaliacoes": int(nav or 0),
             "ultima_avaliacao": ua.isoformat() if ua else None, "equipas": equipas.get(aid, []),
             "consentimento": consent.get(aid)}
            for aid, nome, nasc, pos, ep, esc, epa, nav, ua in linhas
        ],
    }


def obter_ficha(user_id: str, atleta_id: str) -> dict:
    from app.core.db import get_conn
    from app.services.dados_equipa import carregar_df_equipa

    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, nome, nasc, posicao, pe = _verificar_atleta(cur, user_id, atleta_id)
            pai, mae, pais_medida = _altura_pais(cur, atleta_id)
            consentimento = None
            if _tem_consentimento(cur):
                cur.execute("select consentimento_dados_em, consentimento_por, consentimento_notas from atletas where id = %s", (atleta_id,))
                c_d, c_por, c_notas = cur.fetchone()
                consentimento = {"data": c_d.isoformat() if c_d else None, "por": c_por, "notas": c_notas}
            migracao_pais = _tem_altura_pais(cur)
            cur.execute(
                """
                select p.id::text, t.id::text, t.nome, t.escalao, t.epoca, p.posicao, p.ativo,
                       (select count(*) from gps_sessions gs where gs.player_id = p.id) as sessoes,
                       (select count(*) from lesoes l where l.player_id = p.id) as lesoes
                from players p join teams t on t.id = p.team_id
                where p.atleta_id = %s order by t.epoca nulls last, t.criado_em
                """,
                (atleta_id,),
            )
            percurso = cur.fetchall()
            av_atleta = _avaliacoes_academia(cur, academia_id, atleta_id)
            coorte = _avaliacoes_academia(cur, academia_id)
            cur.execute("select id::text, rotulo from (select id, coalesce(escalao || ' · ' || epoca, nome) as rotulo, academia_id from teams) x where academia_id = %s", (academia_id,))
            equipas_academia = cur.fetchall()

    # Sessões de jogo do atleta em todas as equipas/épocas (cada equipa à parte,
    # com o cache de cada uma).
    partes = []
    for player_id, team_id, team_nome, escalao, epoca, *_ in percurso:
        df = carregar_df_equipa(team_id)
        if df.empty or "player_id" not in df.columns:
            continue
        sub = df[df["player_id"].astype(str) == player_id].copy()
        if not sub.empty:
            sub["Época"] = epoca or team_nome
            sub["Escalão"] = escalao
            partes.append(sub)
    sessoes = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()

    serie = av_atleta.sort_values(["metrica", "data"]) if not av_atleta.empty else av_atleta
    series_json = {}
    for metrica, g in (serie.groupby("metrica") if not serie.empty else []):
        meta = POR_CHAVE.get(metrica)
        if not meta:
            continue
        series_json[metrica] = [
            {"id": r["id"], "data": r["data"].strftime("%Y-%m-%d"), "valor": round(float(r["valor"]), meta["casas"]),
             "idade": None if pd.isna(r["idade"]) else round(float(r["idade"]), 1), "origem": r["origem"]}
            for _, r in g.iterrows()
        ]

    # Referência da coorte por idade (p25, mediana, p75) para desenhar a banda.
    bandas = {}
    if not coorte.empty and coorte["idade"].notna().any():
        c = coorte.dropna(subset=["idade"]).copy()
        c["idade_int"] = c["idade"].astype(float).astype(int)
        for (metrica, ida), g in c.groupby(["metrica", "idade_int"]):
            if len(g) >= MIN_COORTE:
                bandas.setdefault(metrica, []).append({
                    "idade": int(ida), "n": int(len(g)),
                    "p25": round(float(g["valor"].quantile(0.25)), 2),
                    "p50": round(float(g["valor"].median()), 2),
                    "p75": round(float(g["valor"].quantile(0.75)), 2),
                })

    hoje = date.today()
    return {
        "atleta": {
            "atleta_id": atleta_id, "nome": nome, "data_nascimento": nasc.isoformat() if nasc else None,
            "idade": idade(nasc, hoje), "posicao": posicao or next((p[5] for p in reversed(percurso) if p[5]), None),
            "pe_dominante": pe,
            "altura_pai_cm": pai, "altura_mae_cm": mae, "altura_pais_medida": pais_medida,
            "consentimento": consentimento,
        },
        "percurso": [
            {"player_id": pid, "team_id": tid, "equipa": tn, "escalao": esc, "epoca": ep, "posicao": pos,
             "ativo": ativo, "sessoes": int(ns or 0), "lesoes": int(nl or 0)}
            for pid, tid, tn, esc, ep, pos, ativo, ns, nl in percurso
        ],
        "catalogo": CATALOGO,
        "equipas": [{"team_id": t, "rotulo": r} for t, r in equipas_academia],
        "series": series_json,
        "bandas": bandas,
        "maturacao": serie_maturacao(serie, pai, mae),
        "maturacao_disponivel": migracao_pais,
        "entrada_vs_ultima": entrada_vs_ultima(serie, coorte[["metrica", "idade", "valor"]].dropna() if not coorte.empty else coorte),
        "carga_jogo": carga_jogo_por_epoca(sessoes),
        "sem_data_nascimento": nasc is None,
    }


def atualizar_atleta(user_id: str, atleta_id: str, data_nascimento: str | None, posicao: str | None, pe: str | None,
                     altura_pai_cm: float | None = None, altura_mae_cm: float | None = None,
                     altura_pais_medida: bool | None = None) -> dict:
    from app.core.db import get_conn
    dn = date.fromisoformat(data_nascimento) if data_nascimento else None
    if dn and not (date(1980, 1, 1) <= dn <= date.today()):
        raise ValueError("Data de nascimento inválida.")
    if pe and pe not in ("direito", "esquerdo", "ambos"):
        raise ValueError("Pé dominante inválido.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            _verificar_atleta(cur, user_id, atleta_id)
            cur.execute(
                "update atletas set data_nascimento = %s, posicao_principal = %s, pe_dominante = %s where id = %s",
                (dn, (posicao or "").strip() or None, pe or None, atleta_id),
            )
            # A data de nascimento também nos jogadores ligados (mantém a identidade coerente).
            cur.execute("update players set data_nascimento = %s where atleta_id = %s", (dn, atleta_id))
            if _tem_altura_pais(cur):
                for valor, (mn, mx), quem in ((altura_pai_cm, (130, 230), "do pai"), (altura_mae_cm, (120, 215), "da mãe")):
                    if valor is not None and not mn <= float(valor) <= mx:
                        raise ValueError(f"Altura {quem} fora do intervalo plausível ({mn}–{mx} cm).")
                cur.execute(
                    "update atletas set altura_pai_cm = %s, altura_mae_cm = %s, altura_pais_medida = %s where id = %s",
                    (altura_pai_cm, altura_mae_cm, altura_pais_medida, atleta_id),
                )
    return {"ok": True}


def registar_avaliacao(user_id: str, atleta_id: str, dia: str, valores: dict, team_id: str | None, notas: str | None) -> dict:
    from app.core.db import get_conn
    d = date.fromisoformat(dia)
    if d > date.today():
        raise ValueError("A data não pode ser no futuro.")
    limpos = {}
    for chave, v in (valores or {}).items():
        if chave not in POR_CHAVE or v in (None, ""):
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Valor inválido em {POR_CHAVE[chave]['label']}.")
        if n <= 0:
            raise ValueError(f"{POR_CHAVE[chave]['label']} tem de ser maior do que zero.")
        limpos[chave] = n
    if not limpos:
        raise ValueError("Preenche pelo menos uma métrica.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, *_ = _verificar_atleta(cur, user_id, atleta_id)
            for chave, n in limpos.items():
                cur.execute(
                    """
                    insert into avaliacoes (academia_id, atleta_id, team_id, data, metrica, valor, notas, criado_por)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (atleta_id, data, metrica) do update set valor = excluded.valor,
                        notas = coalesce(excluded.notas, avaliacoes.notas), team_id = coalesce(excluded.team_id, avaliacoes.team_id)
                    """,
                    (academia_id, atleta_id, team_id or None, d, chave, n, (notas or "").strip() or None, user_id),
                )
    return {"ok": True, "registadas": len(limpos)}


def apagar_avaliacao(user_id: str, avaliacao_id: str) -> dict:
    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                delete from avaliacoes av using academia_membros am
                where av.id = %s and am.academia_id = av.academia_id and am.user_id = %s
                """,
                (avaliacao_id, user_id),
            )
            return {"ok": cur.rowcount > 0}



# ── Separador de equipa: baterias de testes para o plantel todo ──────────────
def _verificar_equipa(cur, user_id: str, team_id: str) -> tuple[str, str]:
    cur.execute(
        """
        select t.academia_id::text, coalesce(t.escalao || ' · ' || t.epoca, t.nome)
        from teams t join academia_membros am on am.academia_id = t.academia_id
        where t.id = %s and am.user_id = %s
        """,
        (team_id, user_id),
    )
    row = cur.fetchone()
    if not row:
        raise PermissionError("Equipa não encontrada nesta academia.")
    return row[0], row[1]


def ultimos_por_metrica(serie: pd.DataFrame) -> dict[str, dict]:
    """Último e penúltimo valor de cada métrica de um atleta."""
    out: dict[str, dict] = {}
    if serie is None or serie.empty:
        return out
    for metrica, g in serie.sort_values("data").groupby("metrica"):
        ult = g.iloc[-1]
        ant = g.iloc[-2] if len(g) > 1 else None
        out[metrica] = {
            "valor": round(float(ult["valor"]), 3), "data": ult["data"].strftime("%Y-%m-%d"),
            "anterior": None if ant is None else round(float(ant["valor"]), 3),
            "data_anterior": None if ant is None else ant["data"].strftime("%Y-%m-%d"),
        }
    return out


def obter_testes_equipa(user_id: str, team_id: str) -> dict:
    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, rotulo = _verificar_equipa(cur, user_id, team_id)
            pais = _tem_altura_pais(cur)
            cur.execute(
                f"""
                select a.id::text, a.nome, a.data_nascimento,
                       {'a.altura_pai_cm::float, a.altura_mae_cm::float' if pais else 'null::float, null::float'}
                from players p join atletas a on a.id = p.atleta_id
                where p.team_id = %s and p.ativo
                order by a.nome
                """,
                (team_id,),
            )
            atletas = cur.fetchall()
            av = _avaliacoes_academia(cur, academia_id)
    hoje = date.today()
    linhas = []
    for aid, nome, nasc, pai, mae in atletas:
        serie = av[av["atleta_id"] == aid] if not av.empty else av
        mat = serie_maturacao(serie, pai, mae)
        linhas.append({
            "atleta_id": aid, "nome": nome,
            "data_nascimento": nasc.isoformat() if nasc else None, "idade": idade(nasc, hoje),
            "altura_pai_cm": pai, "altura_mae_cm": mae,
            "ultimos": ultimos_por_metrica(serie),
            "maturacao": mat[-1] if mat else None,
        })
    return {
        "team_id": team_id, "rotulo": rotulo, "atletas": linhas,
        "catalogo": {k: POR_CHAVE[k] for b in BATERIAS.values() for k in b["metricas"]},
        "baterias": BATERIAS, "maturacao_disponivel": pais,
    }


def _tem_momento(cur) -> bool:
    cur.execute("select exists (select 1 from information_schema.columns where table_name = 'avaliacoes' and column_name = 'momento')")
    return bool(cur.fetchone()[0])


def registar_testes_equipa(user_id: str, team_id: str, dia: str, linhas: list[dict], momento: int | None = None) -> dict:
    """Um dia de testes para o plantel: [{atleta_id, valores: {metrica: valor},
    altura_pai_cm?, altura_mae_cm?}]. O RSI do drop jump calcula-se sozinho."""
    from app.core.db import get_conn
    d = date.fromisoformat(dia)
    if d > date.today():
        raise ValueError("A data não pode ser no futuro.")
    momento = int(momento) if momento else momento_por_data(d)
    if not 1 <= momento <= 4:
        raise ValueError("O momento de avaliação vai de T1 a T4.")
    n_reg = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, _ = _verificar_equipa(cur, user_id, team_id)
            cur.execute("select atleta_id::text from players where team_id = %s and atleta_id is not null", (team_id,))
            da_equipa = {r[0] for r in cur.fetchall()}
            pais = _tem_altura_pais(cur)
            com_momento = _tem_momento(cur)
            for linha in linhas:
                aid = linha.get("atleta_id")
                if aid not in da_equipa:
                    raise PermissionError("Há atletas que não são desta equipa.")
                valores = {}
                for chave, v in (linha.get("valores") or {}).items():
                    if chave not in POR_CHAVE or v in (None, ""):
                        continue
                    try:
                        n = float(v)
                    except (TypeError, ValueError):
                        raise ValueError(f"Valor inválido em {POR_CHAVE[chave]['label']}.")
                    if n <= 0:
                        raise ValueError(f"{POR_CHAVE[chave]['label']} tem de ser maior do que zero.")
                    valores[chave] = n
                if "rsi" not in valores:
                    r = rsi_drop_jump(valores.get("dj_altura_cm"), valores.get("dj_contacto_ms"))
                    if r:
                        valores["rsi"] = r
                for chave, n in valores.items():
                    cur.execute(
                        """
                        insert into avaliacoes (academia_id, atleta_id, team_id, data, metrica, valor, criado_por)
                        values (%s, %s, %s, %s, %s, %s, %s)
                        on conflict (atleta_id, data, metrica) do update set valor = excluded.valor, team_id = excluded.team_id
                        """,
                        (academia_id, aid, team_id, d, chave, n, user_id),
                    )
                    if com_momento:
                        cur.execute("update avaliacoes set momento = %s where atleta_id = %s and data = %s and metrica = %s",
                                    (momento, aid, d, chave))
                    n_reg += 1
                if pais and ("altura_pai_cm" in linha or "altura_mae_cm" in linha):
                    for valor, (mn, mx), quem in ((linha.get("altura_pai_cm"), (130, 230), "do pai"),
                                                  (linha.get("altura_mae_cm"), (120, 215), "da mãe")):
                        if valor not in (None, "") and not mn <= float(valor) <= mx:
                            raise ValueError(f"Altura {quem} fora do intervalo plausível ({mn}–{mx} cm).")
                    cur.execute(
                        "update atletas set altura_pai_cm = %s, altura_mae_cm = %s where id = %s",
                        (linha.get("altura_pai_cm") or None, linha.get("altura_mae_cm") or None, aid),
                    )
    return {"ok": True, "registadas": n_reg, "momento": momento}



# ── Relatórios da época (T1–T4) ──────────────────────────────────────────────
METRICAS_RELATORIO = ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s", "corrida_1km_s",
                      "cmj_cm", "dj_altura_cm", "dj_contacto_ms", "rsi", "altura_cm", "peso_kg"]


def valores_por_momento(serie: pd.DataFrame) -> dict[str, dict[int, dict]]:
    """{metrica: {momento: {valor, data}}} — no mesmo momento fica o último registo."""
    out: dict[str, dict[int, dict]] = {}
    if serie is None or serie.empty:
        return out
    s = serie.copy()
    if "momento" not in s.columns:
        s["momento"] = None
    s["momento"] = [int(m) if pd.notna(m) else momento_por_data(d.date()) for m, d in zip(s["momento"], s["data"])]
    for (metrica, mom), g in s.sort_values("data").groupby(["metrica", "momento"]):
        ult = g.iloc[-1]
        out.setdefault(metrica, {})[int(mom)] = {"valor": round(float(ult["valor"]), 3), "data": ult["data"].strftime("%Y-%m-%d")}
    return out


def maturacao_por_momento(vals: dict, nasc: date | None, pai: float | None, mae: float | None) -> dict[int, dict]:
    from app.services.khamis_roche import estatura_adulta_prevista
    out = {}
    for mom, alt in (vals.get("altura_cm") or {}).items():
        peso = (vals.get("peso_kg") or {}).get(mom)
        if not peso or not nasc:
            continue
        r = estatura_adulta_prevista(idade(nasc, date.fromisoformat(alt["data"])), alt["valor"], peso["valor"], pai, mae)
        if r:
            out[mom] = {**r, "idade": idade(nasc, date.fromisoformat(alt["data"]))}
    return out


def relatorio_epoca(user_id: str, team_id: str) -> dict:
    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, rotulo = _verificar_equipa(cur, user_id, team_id)
            cur.execute("select epoca from teams where id = %s", (team_id,))
            epoca = cur.fetchone()[0]
            pais = _tem_altura_pais(cur)
            cur.execute(
                f"""
                select a.id::text, a.nome, a.data_nascimento, a.posicao_principal,
                       {'a.altura_pai_cm::float, a.altura_mae_cm::float' if pais else 'null::float, null::float'}
                from players p join atletas a on a.id = p.atleta_id
                where p.team_id = %s and p.ativo order by a.nome
                """,
                (team_id,),
            )
            atletas = cur.fetchall()
            av = _avaliacoes_academia(cur, academia_id)
            if not av.empty and _tem_momento(cur):
                cur.execute("select id::text, momento from avaliacoes where academia_id = %s and momento is not null", (academia_id,))
                mom = dict(cur.fetchall())
                av["momento"] = av["id"].map(mom)
    ini, fim = limites_epoca(epoca)
    if not av.empty:
        av = av[(av["data"].dt.date >= ini) & (av["data"].dt.date <= fim)]
    try:
        from app.services.jogos_service import resumo_epoca_atletas
        with get_conn() as conn:
            with conn.cursor() as cur:
                jogos_epoca = resumo_epoca_atletas(cur, [a[0] for a in atletas], ini, fim)
    except Exception:
        jogos_epoca = {}
    linhas = []
    for aid, nome, nasc, pos, pai, mae in atletas:
        serie = av[av["atleta_id"] == aid] if not av.empty else av
        vals = valores_por_momento(serie)
        linhas.append({
            "atleta_id": aid, "nome": nome, "posicao": pos,
            "data_nascimento": nasc.isoformat() if nasc else None, "idade": idade(nasc, date.today()),
            "altura_pai_cm": pai, "altura_mae_cm": mae,
            "valores": vals, "maturacao": maturacao_por_momento(vals, nasc, pai, mae),
            "jogos": jogos_epoca.get(aid),
        })
    # Datas de cada momento (intervalo em que houve testes) e médias da equipa.
    momentos = {}
    for a in linhas:
        for por_m in a["valores"].values():
            for m, v in por_m.items():
                lo, hi = momentos.get(m, (v["data"], v["data"]))
                momentos[m] = (min(lo, v["data"]), max(hi, v["data"]))
    medias: dict[str, dict[int, float]] = {}
    for k in METRICAS_RELATORIO:
        for m in range(1, 5):
            vs = [a["valores"][k][m]["valor"] for a in linhas if m in a["valores"].get(k, {})]
            if vs:
                medias.setdefault(k, {})[m] = round(sum(vs) / len(vs), 3)
    return {
        "team_id": team_id, "rotulo": rotulo, "epoca": epoca, "inicio": ini.isoformat(), "fim": fim.isoformat(),
        "metricas": [POR_CHAVE[k] for k in METRICAS_RELATORIO],
        "momentos": {m: {"de": a, "ate": b} for m, (a, b) in sorted(momentos.items())},
        "atletas": linhas, "medias": medias,
    }



# ── Proteção de dados (RGPD) ─────────────────────────────────────────────────
def _tem_consentimento(cur) -> bool:
    cur.execute("select exists (select 1 from information_schema.columns where table_name = 'atletas' and column_name = 'consentimento_dados_em')")
    return bool(cur.fetchone()[0])


def registar_consentimento(user_id: str, atleta_id: str, data: str | None, por: str | None, notas: str | None) -> dict:
    from app.core.db import get_conn
    d = date.fromisoformat(data) if data else None
    if d and d > date.today():
        raise ValueError("A data do consentimento não pode ser no futuro.")
    if por and por not in ("atleta", "encarregado"):
        raise ValueError("Indica quem deu o consentimento (atleta ou encarregado de educação).")
    with get_conn() as conn:
        with conn.cursor() as cur:
            _verificar_atleta(cur, user_id, atleta_id)
            if not _tem_consentimento(cur):
                raise ValueError("Aplica a migração 0018 para registar consentimentos.")
            cur.execute(
                "update atletas set consentimento_dados_em = %s, consentimento_por = %s, consentimento_notas = %s where id = %s",
                (d, por if d else None, (notas or "").strip()[:300] or None, atleta_id),
            )
    return {"ok": True}


def _linhas(cur, sql: str, params) -> list[dict]:
    cur.execute(sql, params)
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def exportar_atleta(user_id: str, atleta_id: str) -> dict:
    """Todos os dados guardados sobre um atleta (direito de acesso/portabilidade)."""
    from datetime import datetime, timezone

    from app.core.db import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            _verificar_atleta(cur, user_id, atleta_id)
            ficha = _linhas(cur, "select * from atletas where id = %s", (atleta_id,))[0]
            jogadores = _linhas(cur, """
                select p.*, coalesce(t.escalao || ' · ' || t.epoca, t.nome) as equipa
                from players p join teams t on t.id = p.team_id where p.atleta_id = %s""", (atleta_id,))
            pids = [j["id"] for j in jogadores]
            out = {
                "exportado_em": datetime.now(timezone.utc).isoformat(),
                "atleta": ficha,
                "equipas": jogadores,
                "avaliacoes": _linhas(cur, "select * from avaliacoes where atleta_id = %s order by data", (atleta_id,)),
            }
            por_jogador = {
                "sessoes": "select * from gps_sessions where player_id = any(%s::uuid[]) order by data",
                "testes_neuromusculares": "select * from testes_neuromusculares where player_id = any(%s::uuid[]) order by data",
                "lesoes": "select * from lesoes where player_id = any(%s::uuid[]) order by data_inicio",
                "planos_regresso": "select * from planos_rtp where player_id = any(%s::uuid[])",
                "pedidos_bem_estar_pse": "select id, team_id, data, tipo, estado_envio, enviado_em, respondido_em from pedidos_resposta where player_id = any(%s::uuid[]) order by data",
            }
            for chave, sql in por_jogador.items():
                try:
                    cur.execute("savepoint exp")
                    out[chave] = _linhas(cur, sql, (pids,)) if pids else []
                    cur.execute("release savepoint exp")
                except Exception:
                    cur.execute("rollback to savepoint exp")
                    out[chave] = []
            try:
                cur.execute("savepoint exp")
                out["jogos"] = _linhas(cur, """
                    select j.data, j.competicao, j.adversario, jp.* from jogo_participacoes jp
                    join jogos j on j.id = jp.jogo_id where jp.atleta_id = %s order by j.data""", (atleta_id,))
                cur.execute("release savepoint exp")
            except Exception:
                cur.execute("rollback to savepoint exp")
                out["jogos"] = []
    return out
