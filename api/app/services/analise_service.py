"""Análise — substitui o antigo "Dashboard" (reestruturação pedida pelo
utilizador). Foco em carga semanal/diária e monotonia/strain corretos
(ver utils/calculos.calcular_monotonia_strain), não em ACWR/alertas.
"""
import pandas as pd

from utils.calculos import DIAS_MD_ORDEM, calcular_acwr_global, calcular_monotonia_strain

from app.core.db import get_conn
from app.services.alertas_service import classificar_acwr
from app.services.dados_equipa import carregar_df_equipa
from app.services.estado_service import listar_estados


def _carga_por_jogador_duas_semanas(df: pd.DataFrame, mc_a, mc_b) -> list[dict]:
    """Carga Interna total por jogador em duas semanas (microciclos), para o
    gráfico de comparação semana-a-semana. Inclui quem tem dados em qualquer
    das semanas (0 na semana em que não treinou)."""
    if "Carga Interna" not in df.columns or "Jogador" not in df.columns:
        return []

    def soma(mc):
        d = df[df["Microciclo (Nr)"] == mc] if mc is not None else df
        s = d.dropna(subset=["Carga Interna", "Jogador"]).groupby("Jogador")["Carga Interna"].sum()
        return {j: round(float(v), 0) for j, v in s.items()}

    a, b = soma(mc_a), soma(mc_b)
    jogadores = sorted(set(a) | set(b), key=lambda j: a.get(j, 0), reverse=True)
    return [{"jogador": j, "a": a.get(j, 0.0), "b": b.get(j, 0.0)} for j in jogadores]


def _pse_esperada_por_dia(team_id: str, microciclo, dias_disponiveis: list[str]) -> list[dict]:
    """PSE planeada (esperada) por dia, da tabela pse_planeado, para o gráfico
    combinado Carga+PSE. Só os dias com sessões registados (dias_disponiveis)."""
    if microciclo is None:
        return []
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select dia_md, pse_esperada from pse_planeado where team_id = %s and microciclo_nr = %s",
                    (team_id, microciclo),
                )
                esperada = {row[0]: float(row[1]) for row in cur.fetchall()}
    except Exception:
        # Sem PSE planeada (ou BD indisponível) o gráfico combinado mostra só
        # a carga e a PSE real — não é motivo para falhar a análise inteira.
        return []
    return [{"dia_md": d, "pse_esperada": esperada[d]} for d in dias_disponiveis if d in esperada]

# Tipo de alerta (o que a Análise e o relatório mostram) por sinal do motor
# único (alertas_service.construir_avisos_dashboard).
TIPO_POR_SINAL = {
    "acwr": "ACWR", "hooper": "Wellness", "cmj": "CMJ", "vmax": "Velocidade",
    "sem_dados": "Dados", "pse_gps": "PSE vs GPS", "crescimento": "Crescimento",
    "hsr_baixo": "Exposição", "hsr_alto": "Exposição", "sprint_baixo": "Exposição", "sprint_alto": "Exposição",
}
ESTADO_POR_SEVERIDADE = {2: "🔴 PRIORITÁRIO", 1: "🟠 VIGIAR"}


def _calcular_alertas(
    df: pd.DataFrame,
    df_semana: pd.DataFrame,
    estados: dict[str, dict],
    limites: dict[str, float] | None = None,
    testes: pd.DataFrame | None = None,
    hoje=None,
) -> dict:
    """«Quem precisa de atenção» da Análise e do relatório — lido do MESMO
    motor do Centro de Controlo (construir_avisos_dashboard), para a mesma
    pessoa não ter estados diferentes consoante a página. Esta função só
    converte cada sinal para a forma {jogador, tipo, valor, estado, severidade}.

    Jogadores não-aptos (ver estado_service) ficam de fora dos sinais e
    aparecem à parte, em "indisponíveis". `df_semana` mantém-se na assinatura
    por compatibilidade (o motor decide as janelas de cada sinal).
    """
    from app.services.alertas_service import construir_avisos_dashboard

    so_estado = {nome: (info or {}).get("estado", "apto") for nome, info in estados.items()}
    avisos = construir_avisos_dashboard(df, limites, estados=so_estado, testes=testes, hoje=hoje) if not df.empty else []

    acwr = calcular_acwr_global(df) if not df.empty else {}
    prioritarios = []
    for a in avisos:
        for sinal in a.get("sinais", []):
            chave = sinal["chave"]
            tipo = TIPO_POR_SINAL.get(chave, "Habitual" if chave.startswith("habitual") else chave)
            sev = int(sinal.get("severidade", 1))
            if chave == "acwr":
                sev, estado = classificar_acwr(acwr.get(a["player_name"], {}).get("acwr"), limites)
            elif chave == "sem_dados":
                estado = "⚪ SEM DADOS"
            else:
                estado = ESTADO_POR_SEVERIDADE[sev]
            prioritarios.append({"jogador": a["player_name"], "tipo": tipo,
                                 "valor": sinal["detalhe"].get("valor"), "estado": estado, "severidade": sev})

    prioritarios.sort(key=lambda p: -p["severidade"])

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
    from datetime import date

    from app.services.prontidao_service import _carregar_testes
    alertas = _calcular_alertas(df, df_semana, estados, limites, testes=_carregar_testes(team_id),
                                hoje=pd.Timestamp(date.today()))

    # Comparação de microciclos (A = selecionado, B = comparar_microciclo).
    comparacao = None
    mc_comparar = comparar_microciclo if (comparar_microciclo is not None and comparar_microciclo in microciclos_disponiveis) else None
    if mc_comparar is not None and mc_comparar != mc_selecionado:
        comparacao = {
            "a": _resumo_semana(df, mc_selecionado, DIAS_MD_ORDEM),
            "b": _resumo_semana(df, mc_comparar, DIAS_MD_ORDEM),
            "por_jogador": _carga_por_jogador_duas_semanas(df, mc_selecionado, mc_comparar),
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
        "pse_esperada_por_dia": _pse_esperada_por_dia(team_id, mc_selecionado, dias_md_disponiveis),
        "monotonia_media": monotonia_media,
        "strain_medio": strain_medio,
        "ranking_carga": ranking_carga,
        "alertas": alertas,
    }
