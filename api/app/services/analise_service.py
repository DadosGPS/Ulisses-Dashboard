"""Análise — substitui o antigo "Dashboard" (reestruturação pedida pelo
utilizador). Foco em carga semanal/diária e monotonia/strain corretos
(ver utils/calculos.calcular_monotonia_strain), não em ACWR/alertas.
"""
import pandas as pd

from utils.calculos import DIAS_MD_ORDEM, calcular_acwr_global, calcular_monotonia_strain

from app.services.alertas_service import classificar_acwr
from app.services.dados_equipa import carregar_df_equipa
from app.services.estado_service import listar_estados
from app.services.limites_service import DEFAULTS

# Limiar estatístico (z-score) da divergência PSE vs GPS — significância
# estatística, não um limiar fisiológico que o preparador físico configure.
_DIVERGENCIA_Z = 1.0


def _calcular_alertas(
    df: pd.DataFrame,
    df_semana: pd.DataFrame,
    estados: dict[str, dict],
    limites: dict[str, float] | None = None,
) -> dict:
    """Junta ACWR + wellness (Hooper) num único sinal — sem isto, o
    preparador físico tinha de cruzar manualmente a página Equipa (ACWR) com
    a página Jogadores (wellness) para saber quem precisa de atenção hoje.

    Jogadores já marcados como não-aptos (ver estado_service) são excluídos:
    um ACWR alto num jogador já lesionado não é um alerta novo, é a razão
    provável da lesão — por isso aparecem à parte, em "indisponíveis".

    Os limiares (ACWR, wellness, dias sem dados, queda de velocidade) vêm de
    `limites` (limites_service) — o MESMO dicionário que alimenta os alertas do
    dashboard. Sem `limites` usa os valores por omissão, idênticos aos que
    antes estavam fixos aqui no código.
    """
    lim = {**DEFAULTS, **(limites or {})}
    prioritarios = []

    acwr_dict = calcular_acwr_global(df)
    for jog, dados in acwr_dict.items():
        if estados.get(jog, {}).get("estado", "apto") != "apto":
            continue
        v = dados["acwr"]
        severidade, estado_acwr = classificar_acwr(v, lim)
        if severidade >= 1:
            prioritarios.append({
                "jogador": jog, "tipo": "ACWR",
                "valor": round(float(v), 2) if pd.notna(v) else None,
                "estado": estado_acwr,
            })

    if {"Hooper Index", "Jogador", "Data"}.issubset(df_semana.columns):
        ultima = df_semana.dropna(subset=["Hooper Index"]).sort_values("Data").groupby("Jogador").last().reset_index()
        for _, row in ultima.iterrows():
            jog = row["Jogador"]
            if estados.get(jog, {}).get("estado", "apto") != "apto":
                continue
            hi = row["Hooper Index"]
            if pd.notna(hi) and hi >= lim["hooper_alto"]:
                prioritarios.append({"jogador": jog, "tipo": "Wellness", "valor": round(float(hi), 1), "estado": "🔴 RISCO"})

    # Jogador ativo sem sessões registadas há vários dias — pode ser lesão
    # por marcar, ausência, ou simplesmente um esquecimento no registo; de
    # qualquer forma, vale a pena o preparador físico saber.
    LIMITE_DIAS_SEM_DADOS = lim["dias_sem_dados"]
    if {"Data", "Jogador"}.issubset(df.columns) and df["Data"].notna().any():
        referencia = df["Data"].max()
        ultima_sessao = df.dropna(subset=["Data", "Jogador"]).groupby("Jogador")["Data"].max()
        for jog, ultima in ultima_sessao.items():
            if estados.get(jog, {}).get("estado", "apto") != "apto":
                continue
            dias_sem_dados = (referencia - ultima).days
            if dias_sem_dados >= LIMITE_DIAS_SEM_DADOS:
                prioritarios.append({
                    "jogador": jog, "tipo": "Dados",
                    "valor": dias_sem_dados, "estado": "⚪ SEM DADOS",
                })

    # Queda de velocidade — recorde da época vs média das últimas 3 sessões
    # com valor registado. Uma queda sustentada é um sinal clássico de
    # fadiga acumulada ou lesão a instalar-se, mesmo sem dor referida.
    LIMITE_PCT_QUEDA_VELOCIDADE = 1 - lim["velocidade_queda_sustentada"] / 100
    if {"Vel. Máx (km/h)", "Jogador", "Data"}.issubset(df.columns):
        for jog, g in df.dropna(subset=["Vel. Máx (km/h)", "Jogador"]).groupby("Jogador"):
            if estados.get(jog, {}).get("estado", "apto") != "apto":
                continue
            recorde = g["Vel. Máx (km/h)"].max()
            if not recorde or recorde <= 0:
                continue
            recentes = g.sort_values("Data").tail(3)["Vel. Máx (km/h)"]
            if recentes.empty:
                continue
            pct = float(recentes.mean()) / float(recorde)
            if pct < LIMITE_PCT_QUEDA_VELOCIDADE:
                prioritarios.append({
                    "jogador": jog, "tipo": "Velocidade",
                    "valor": round(pct * 100, 0), "estado": "🟠 QUEDA DE VELOCIDADE",
                })

    # Divergência PSE vs GPS — quando a perceção de esforço (subjetivo) e a
    # distância percorrida (objetivo) se afastam muito do padrão habitual do
    # próprio atleta, e em direções opostas, é frequentemente o primeiro
    # sinal de fadiga não visível na carga interna sozinha, ou de doença.
    if {"PSE Sessão", "Distância Total (m)", "Jogador", "Data"}.issubset(df.columns):
        for jog, g in df.dropna(subset=["Jogador"]).groupby("Jogador"):
            if estados.get(jog, {}).get("estado", "apto") != "apto":
                continue
            ambos = g.sort_values("Data").dropna(subset=["PSE Sessão", "Distância Total (m)"])
            if len(ambos) < 4:
                continue
            ultima, historico = ambos.iloc[-1], ambos.iloc[:-1]
            dp_pse, dp_dist = historico["PSE Sessão"].std(), historico["Distância Total (m)"].std()
            if not dp_pse or not dp_dist:
                continue
            z_pse = (ultima["PSE Sessão"] - historico["PSE Sessão"].mean()) / dp_pse
            z_dist = (ultima["Distância Total (m)"] - historico["Distância Total (m)"].mean()) / dp_dist
            if z_pse * z_dist < 0 and abs(z_pse) > _DIVERGENCIA_Z and abs(z_dist) > _DIVERGENCIA_Z:
                prioritarios.append({
                    "jogador": jog, "tipo": "PSE vs GPS",
                    "valor": round(z_pse - z_dist, 1), "estado": "🟣 DIVERGÊNCIA",
                })

    prioritarios.sort(key=lambda a: 0 if "RISCO" in a["estado"] else 1)

    indisponiveis = [
        {
            "jogador": nome, "estado": info["estado"],
            "motivo": info.get("estado_motivo"), "desde": info.get("estado_desde"),
        }
        for nome, info in estados.items() if info.get("estado") != "apto"
    ]

    return {"prioritarios": prioritarios[:8], "indisponiveis": indisponiveis}


def _resumo_semana(df: pd.DataFrame, mc, dias_ordem: list[str]) -> dict:
    """Resumo compacto de um microciclo (para a comparação A vs B): carga/PSE
    por dia, carga média e monotonia/strain. Respeita o df já filtrado (equipa
    ou um jogador)."""
    sem = df[df["Microciclo (Nr)"] == mc] if mc is not None else df
    dias = []
    if "Dia MD" in sem.columns:
        presentes = set(sem["Dia MD"].dropna().unique().tolist())
        dias = [d for d in dias_ordem if d in presentes]

    carga_por_dia, pse_por_dia = [], []
    if "Dia MD" in sem.columns:
        if "Carga Interna" in sem.columns:
            md = sem.dropna(subset=["Carga Interna", "Dia MD"]).groupby("Dia MD")["Carga Interna"].mean()
            carga_por_dia = [{"dia_md": d, "carga_media": round(float(md[d]), 0)} for d in dias if d in md.index]
        if "PSE Sessão" in sem.columns:
            mp = sem.dropna(subset=["PSE Sessão", "Dia MD"]).groupby("Dia MD")["PSE Sessão"].mean()
            pse_por_dia = [{"dia_md": d, "pse_media": round(float(mp[d]), 1)} for d in dias if d in mp.index]

    carga_atleta = (
        sem.dropna(subset=["Carga Interna", "Jogador"]).groupby("Jogador")["Carga Interna"].sum()
        if "Carga Interna" in sem.columns else pd.Series(dtype=float)
    )
    cim = round(float(carga_atleta.mean()), 0) if not carga_atleta.empty else None

    monotonia_media = strain_medio = None
    mono = calcular_monotonia_strain(sem)
    if not mono.empty:
        csm = round(float(mono["Carga Semanal Total"].mean()), 0)
        monotonia_media = round(float(mono["Monotonia"].mean()), 2)
        strain_medio = round(csm * monotonia_media, 0)

    return {
        "microciclo": int(mc) if mc is not None else None,
        "carga_interna_media": cim,
        "carga_por_dia": carga_por_dia,
        "pse_por_dia": pse_por_dia,
        "monotonia_media": monotonia_media,
        "strain_medio": strain_medio,
    }


def obter_analise(
    team_id: str,
    microciclo: int | None = None,
    dia_md: str | None = None,
    jogador: str | None = None,
    comparar_microciclo: int | None = None,
    limites: dict[str, float] | None = None,
) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"tem_dados": False}

    # Lista de jogadores (antes de filtrar) para o seletor da página.
    jogadores_disponiveis = sorted(df["Jogador"].dropna().unique().tolist()) if "Jogador" in df.columns else []
    jogador_selecionado = jogador if (jogador and jogador in jogadores_disponiveis) else None
    if jogador_selecionado:
        df = df[df["Jogador"] == jogador_selecionado]

    tem_microciclo = "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any()
    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist()) if tem_microciclo else []
    mc_recente = microciclos_disponiveis[-1] if microciclos_disponiveis else None
    mc_selecionado = microciclo if (microciclo is not None and microciclo in microciclos_disponiveis) else mc_recente
    df_semana = df[df["Microciclo (Nr)"] == mc_selecionado] if mc_selecionado is not None else df

    dias_md_disponiveis = []
    if "Dia MD" in df_semana.columns:
        presentes = set(df_semana["Dia MD"].dropna().unique().tolist())
        dias_md_disponiveis = [d for d in DIAS_MD_ORDEM if d in presentes]
    dia_md_selecionado = dia_md if dia_md in dias_md_disponiveis else None

    # Base de cálculo do KPI principal, do máximo/mínimo e do ranking: com
    # "Todos os dias" é a carga semanal total por atleta (soma); com um dia
    # específico escolhido, é a carga desse dia por atleta (soma também,
    # para cobrir o caso raro de 2 sessões no mesmo dia) — o pedido do
    # utilizador é explícito quanto a isto não poder ser "média por sessão".
    df_base = df_semana if not dia_md_selecionado else df_semana[df_semana["Dia MD"] == dia_md_selecionado]
    carga_por_atleta = (
        df_base.dropna(subset=["Carga Interna", "Jogador"]).groupby("Jogador")["Carga Interna"].sum()
        if "Carga Interna" in df_base.columns else pd.Series(dtype=float)
    )

    carga_interna_media = float(carga_por_atleta.mean()) if not carga_por_atleta.empty else None

    carga_maxima = carga_minima = None
    if not carga_por_atleta.empty:
        carga_maxima = {"jogador": carga_por_atleta.idxmax(), "valor": round(float(carga_por_atleta.max()), 0)}
        carga_minima = {"jogador": carga_por_atleta.idxmin(), "valor": round(float(carga_por_atleta.min()), 0)}

    ranking_carga = [
        {"jogador": j, "valor": round(float(v), 0)}
        for j, v in carga_por_atleta.sort_values(ascending=False).items()
    ]

    # Carga e PSE médias por dia — sempre a semana inteira (dá contexto ao
    # microciclo mesmo quando um dia específico está selecionado no filtro).
    carga_por_dia, pse_por_dia = [], []
    if "Dia MD" in df_semana.columns:
        if "Carga Interna" in df_semana.columns:
            media_dia = df_semana.dropna(subset=["Carga Interna", "Dia MD"]).groupby("Dia MD")["Carga Interna"].mean()
            carga_por_dia = [
                {"dia_md": d, "carga_media": round(float(media_dia[d]), 0)}
                for d in dias_md_disponiveis if d in media_dia.index
            ]
        if "PSE Sessão" in df_semana.columns:
            media_pse = df_semana.dropna(subset=["PSE Sessão", "Dia MD"]).groupby("Dia MD")["PSE Sessão"].mean()
            pse_por_dia = [
                {"dia_md": d, "pse_media": round(float(media_pse[d]), 1)}
                for d in dias_md_disponiveis if d in media_pse.index
            ]

    # Monotonia/Strain são sempre conceitos semanais — não fazem sentido
    # para um único dia, por isso ignoram o filtro de Dia MD.
    #
    # Strain da equipa = carga semanal total média × monotonia média — os
    # MESMOS dois valores já arredondados e mostrados no cartão, multiplicados
    # entre si (não a média dos strains individuais: mean(a*b) != mean(a)*
    # mean(b) quando a carga e a monotonia variam de atleta para atleta).
    monotonia_media = strain_medio = None
    mono = calcular_monotonia_strain(df_semana)
    if not mono.empty:
        carga_semanal_media = round(float(mono["Carga Semanal Total"].mean()), 0)
        monotonia_media = round(float(mono["Monotonia"].mean()), 2)
        strain_medio = round(carga_semanal_media * monotonia_media, 0)

    estados = {e["nome"]: e for e in listar_estados(team_id)}
    alertas = _calcular_alertas(df, df_semana, estados, limites)

    # Comparação de microciclos (A = selecionado, B = comparar_microciclo).
    comparacao = None
    mc_comparar = comparar_microciclo if (comparar_microciclo is not None and comparar_microciclo in microciclos_disponiveis) else None
    if mc_comparar is not None and mc_comparar != mc_selecionado:
        comparacao = {
            "a": _resumo_semana(df, mc_selecionado, DIAS_MD_ORDEM),
            "b": _resumo_semana(df, mc_comparar, DIAS_MD_ORDEM),
        }

    return {
        "tem_dados": True,
        "jogador_selecionado": jogador_selecionado,
        "jogadores_disponiveis": jogadores_disponiveis,
        "microciclo_recente": mc_recente,
        "microciclo_selecionado": mc_selecionado,
        "microciclo_comparar": mc_comparar,
        "microciclos_disponiveis": microciclos_disponiveis,
        "comparacao": comparacao,
        "dia_md_selecionado": dia_md_selecionado,
        "dias_md_disponiveis": dias_md_disponiveis,
        "carga_interna_media": round(carga_interna_media, 0) if carga_interna_media is not None else None,
        "carga_maxima": carga_maxima,
        "carga_minima": carga_minima,
        "carga_por_dia": carga_por_dia,
        "pse_por_dia": pse_por_dia,
        "monotonia_media": monotonia_media,
        "strain_medio": strain_medio,
        "ranking_carga": ranking_carga,
        "alertas": alertas,
    }
