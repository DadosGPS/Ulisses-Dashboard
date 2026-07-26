"""LoadMonitorSystem — Página Dashboard"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from utils.calculos import calcular_acwr_global, cor_acwr
from utils.ui_safe import botao_download_html, gerar_pdf_html, team_kpi_tile, ranking_metric_card


def render(df, excel_path):
    """Renderiza a página Dashboard."""
    # ── Contexto do utilizador (vem do session_state, definido pelo router) ───
    _lm_user  = st.session_state.get("lm_user", {})
    _lm_nome  = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")

    # ── Aplicar filtros da sidebar (FIX: Dashboard agora respeita filtros) ────
    # df_view = dados filtrados pela sidebar (microciclo, posição, dia MD).
    # df continua = dataset completo (usado no ACWR para preservar histórico).
    _filters = st.session_state.get("lm_filters", {})
    df_view = _filters.get("df_f", df)
    if df_view is None or df_view.empty:
        df_view = df  # fallback: se filtros zeram tudo, usar dados completos

    hoje = datetime.now()

    # ── Calcular tudo para o dashboard ────────────────────────────────────────
    # ACWR usa df completo (precisa de 28 dias de histórico para crónica).
    acwr_dict = calcular_acwr_global(df)
    # Mas filtra-se para mostrar só jogadores presentes na vista filtrada.
    if not df_view.empty and "Jogador" in df_view.columns:
        _jogs_view = set(df_view["Jogador"].dropna().unique())
        acwr_dict = {j: d for j, d in acwr_dict.items() if j in _jogs_view}

    # Classificar jogadores por prioridade
    alertas_criticos = []
    alertas_atencao  = []
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]; estado = cor_acwr(v)
        pos = dados.get("posicao", "—")
        if "RISCO" in estado:
            alertas_criticos.append({"jog": jog, "pos": pos, "tipo": "ACWR", "val": f"{v:.2f}", "msg": "Carga excessiva", "cor": "#e74c3c"})
        elif "ATENÇÃO" in estado:
            alertas_atencao.append({"jog": jog, "pos": pos, "tipo": "ACWR", "val": f"{v:.2f}", "msg": "Monitorizar carga", "cor": "#f39c12"})

    # Wellness alerts (filtrado)
    ultima_sessao = df_view.sort_values("Data").groupby("Jogador").last().reset_index()
    for _, row in ultima_sessao.iterrows():
        hi = row.get("Hooper Index", np.nan)
        if pd.notna(hi) and hi >= 14:
            alertas_criticos.append({"jog": row["Jogador"], "pos": row.get("Posição","—"), "tipo": "Wellness",
                                      "val": f"{hi:.0f}/20", "msg": "Fadiga/stress elevado", "cor": "#e74c3c"})

    # Vmáx alerts (filtrado)
    if "Vel. Máx (km/h)" in df_view.columns:
        for jog in df_view["Jogador"].dropna().unique():
            sub_v = df_view[df_view["Jogador"]==jog].dropna(subset=["Data","Vel. Máx (km/h)"]).sort_values("Data")
            if sub_v.empty: continue
            rec = sub_v["Vel. Máx (km/h)"].max()
            acima = sub_v[sub_v["Vel. Máx (km/h)"] >= rec * 0.90]
            if acima.empty: dias_v = 999
            else: dias_v = (sub_v["Data"].max() - acima["Data"].max()).days
            if dias_v > 7:
                alertas_criticos.append({"jog": jog, "pos": "—", "tipo": "Vmáx",
                    "val": f"{dias_v}d", "msg": f"Sem sprint ≥90% há {dias_v} dias", "cor": "#e74c3c"})
            elif dias_v >= 5:
                alertas_atencao.append({"jog": jog, "pos": "—", "tipo": "Vmáx",
                    "val": f"{dias_v}d", "msg": f"Atenção: {dias_v} dias sem ≥90% Vmáx", "cor": "#f39c12"})

    n_alertas_total = len(alertas_criticos) + len(alertas_atencao)

    # KPIs globais (baseados em df_view — respeita filtros)
    mc_recente = sorted(df_view["Microciclo (Nr)"].dropna().unique())[-1] if "Microciclo (Nr)" in df_view.columns and not df_view.empty else None
    mc_anterior = sorted(df_view["Microciclo (Nr)"].dropna().unique())[-2] if mc_recente and len(df_view["Microciclo (Nr)"].dropna().unique()) >= 2 else None
    ci_media = df_view[df_view["Microciclo (Nr)"]==mc_recente]["Carga Interna"].mean() if mc_recente and "Carga Interna" in df_view.columns else np.nan
    acwr_media = np.mean([d["acwr"] for d in acwr_dict.values()]) if acwr_dict else np.nan
    hooper_media = df_view[df_view["Microciclo (Nr)"]==mc_recente]["Hooper Index"].mean() if mc_recente and "Hooper Index" in df_view.columns else np.nan
    n_risco = len(alertas_criticos)

    # ══════════════════════════════════════════════════════════════════════════
    # RENDERIZAR DASHBOARD
    # ══════════════════════════════════════════════════════════════════════════

    # ── Header ────────────────────────────────────────────────────────────────
    meses = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril",
             "May":"Maio","June":"Junho","July":"Julho","August":"Agosto",
             "September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
    dias_s = {"Monday":"Segunda","Tuesday":"Terça","Wednesday":"Quarta","Thursday":"Quinta",
              "Friday":"Sexta","Saturday":"Sábado","Sunday":"Domingo"}
    data_str = hoje.strftime("%A, %d de %B de %Y")
    for en, pt in {**meses, **dias_s}.items():
        data_str = data_str.replace(en, pt)

    alerta_cor_header = "#e74c3c" if alertas_criticos else "#f39c12" if alertas_atencao else "#2ecc71"
    alerta_icon = "🔴" if alertas_criticos else "🟡" if alertas_atencao else "🟢"
    alerta_msg  = f"{n_alertas_total} alertas ativos" if n_alertas_total > 0 else "Sem alertas — equipa OK"
    clube_nome = _lm_user.get("clube", "")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0d1117,#161b22);border:1px solid rgba(255,255,255,0.06);
    border-radius:16px;padding:24px 28px 20px;margin-bottom:20px;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;right:0;height:3px;
        background:linear-gradient(90deg,{alerta_cor_header},transparent)"></div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
            <div>
                <div style="font-size:0.6rem;color:rgba(255,255,255,0.3);letter-spacing:3px;
                text-transform:uppercase;margin-bottom:6px">LoadMonitor{' · ' + clube_nome if clube_nome else ''}</div>
                <div style="font-family:'Space Grotesk',sans-serif;font-size:1.8rem;font-weight:700;
                color:white;line-height:1.1">{data_str}</div>
                <div style="font-size:0.8rem;color:rgba(255,255,255,0.4);margin-top:6px">
                Bem-vindo, {_lm_nome} · MC {int(mc_recente) if mc_recente else '—'} · {df_view['Jogador'].nunique()} jogadores</div>
            </div>
            <div style="background:{alerta_cor_header}18;border:1px solid {alerta_cor_header}44;
            border-radius:10px;padding:10px 16px;text-align:center">
                <div style="font-size:1.5rem">{alerta_icon}</div>
                <div style="font-size:0.75rem;font-weight:600;color:{alerta_cor_header}">{alerta_msg}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Alertas prioritários (máx 5) ──────────────────────────────────────────
    top_alertas = (alertas_criticos + alertas_atencao)[:5]
    if top_alertas:
        st.markdown('<p class="section-title">🚨 Alertas Prioritários</p>', unsafe_allow_html=True)
        for a in top_alertas:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;padding:10px 16px;margin:3px 0;'
                f'background:{a["cor"]}0d;border-left:3px solid {a["cor"]};border-radius:0 8px 8px 0">'
                f'<div style="min-width:70px"><b style="color:{a["cor"]};font-size:0.9rem">{a["jog"]}</b>'
                f'<div style="font-size:0.65rem;color:#888">{a["pos"]}</div></div>'
                f'<div style="flex:1;font-size:0.8rem;color:rgba(255,255,255,0.7)">{a["msg"]}</div>'
                f'<div style="text-align:right"><span style="background:{a["cor"]}22;color:{a["cor"]};'
                f'padding:3px 8px;border-radius:4px;font-size:0.7rem;font-weight:700">{a["tipo"]} {a["val"]}</span></div>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.success("✅ Nenhum alerta ativo — toda a equipa dentro dos parâmetros normais.")

    st.divider()

    # ── KPIs principais ───────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    # Carga Interna
    if mc_recente and "Carga Interna" in df_view.columns and not pd.isna(ci_media):
        ci_ant = df_view[df_view["Microciclo (Nr)"]==mc_anterior]["Carga Interna"].mean() if mc_anterior else np.nan
        delta_ci = f"{((ci_media-ci_ant)/ci_ant*100):+.0f}% vs MC ant." if not pd.isna(ci_ant) and ci_ant > 0 else None
        k1.metric("⚡ Carga Interna", f"{ci_media:,.0f} UA", delta=delta_ci,
                  help="Média de Carga Interna (PSE × Duração) por sessão no MC atual")
    else:
        k1.metric("⚡ Carga Interna", "—", help="PSE × Duração em minutos")

    # ACWR com zona
    if not pd.isna(acwr_media):
        if acwr_media > 1.5:     acwr_zona, acwr_dc = "🔴 Risco >1.5",    "inverse"
        elif acwr_media > 1.3:   acwr_zona, acwr_dc = "🟡 Atenção 1.3–1.5","off"
        elif acwr_media >= 0.8:  acwr_zona, acwr_dc = "🟢 Zona Segura",    "off"
        else:                    acwr_zona, acwr_dc = "🔵 Sub-carga <0.8", "normal"
        k2.metric("📊 ACWR Médio", f"{acwr_media:.2f}", delta=acwr_zona,
                  delta_color=acwr_dc, help="Rácio Carga Aguda/Crónica · Zona óptima: 0.8–1.3")
    else:
        k2.metric("📊 ACWR Médio", "—", help="Precisa de dados de Carga Interna")

    # Hooper Index (delta invertido — descida = verde)
    if not pd.isna(hooper_media) and "Hooper Index" in df_view.columns:
        hooper_ant = df_view[df_view["Microciclo (Nr)"]==mc_anterior]["Hooper Index"].mean() if mc_anterior else np.nan
        delta_h = f"{((hooper_media-hooper_ant)/hooper_ant*100):+.0f}% vs MC ant." if not pd.isna(hooper_ant) and hooper_ant > 0 else None
        h_estado = "⚠️ Risco" if hooper_media >= 14 else "👀 Monitorizar" if hooper_media >= 10 else "✅ Boa recuperação"
        k3.metric("💤 Hooper Index", f"{hooper_media:.1f}/20",
                  delta=delta_h, delta_color="inverse",
                  help=f"0=Recuperação total · 16=Exaustão · Estado: {h_estado}")
    else:
        k3.metric("💤 Hooper Index", "—", help="Precisa de dados de Wellness")

    # Jogadores em risco com breakdown
    risco_acwr_n = len([a for a in alertas_criticos if a["tipo"]=="ACWR"])
    risco_well_n = len([a for a in alertas_criticos if a["tipo"]=="Wellness"])
    risco_vmax_n = len([a for a in alertas_criticos if a["tipo"]=="Vmáx"])
    k4.metric("🚨 Em Risco", str(n_risco),
              delta=f"ACWR:{risco_acwr_n} · Well:{risco_well_n} · Vmáx:{risco_vmax_n}" if n_risco>0 else "✅ Equipa OK",
              delta_color="off",
              help="Jogadores com ACWR>1.5, Hooper≥14 ou sem sprint ≥90% Vmáx há >7 dias")

    st.divider()

    # ── Recomendação do dia ───────────────────────────────────────────────────
    st.markdown('<p class="section-title">💡 Recomendação do Dia</p>', unsafe_allow_html=True)

    # ── Contexto do Dia MD (filtrado) ─────────────────────────────────────────
    dia_md_hoje = None
    if "Dia MD" in df_view.columns and "Data" in df_view.columns and not df_view.empty:
        ultima_data = df_view["Data"].dropna().max()
        if pd.notna(ultima_data):
            sessoes_recentes = df_view[df_view["Data"].dt.date == ultima_data.date()]
            if not sessoes_recentes.empty:
                moda = sessoes_recentes["Dia MD"].mode()
                dia_md_hoje = moda.iloc[0] if not moda.empty else None

    PERFIL_DIA_MD = {
        "MD-5": {"intensidade":"alta",      "foco":"carga física elevada",            "sprint":True},
        "MD-4": {"intensidade":"media",     "foco":"trabalho técnico-tático",          "sprint":False},
        "MD-3": {"intensidade":"alta",      "foco":"jogos reduzidos competitivos",     "sprint":True},
        "MD-2": {"intensidade":"media",     "foco":"manutenção e velocidade",          "sprint":True},
        "MD-1": {"intensidade":"baixa",     "foco":"ativação neuromuscular pré-jogo",  "sprint":False},
        "MD":   {"intensidade":"jogo",      "foco":"jogo oficial",                     "sprint":True},
        "MD+1": {"intensidade":"recuperacao","foco":"recuperação ativa",               "sprint":False},
        "MD+2": {"intensidade":"baixa",     "foco":"regeneração e mobilidade",         "sprint":False},
    }
    perfil_hoje = PERFIL_DIA_MD.get(dia_md_hoje)
    recomendacoes = []

    # ── 1. Contexto do Dia MD ─────────────────────────────────────────────────
    if dia_md_hoje and perfil_hoje:
        if dia_md_hoje in ["MD+1","MD+2"]:
            recomendacoes.append(("🔵", f"DIA {dia_md_hoje} — RECUPERAÇÃO",
                f"Sessão de {perfil_hoje['foco']}. Evitar alta intensidade. "
                f"O sistema neuromuscular ainda está a recuperar do jogo — priorizar mobilidade e regeneração ativa."))
        elif dia_md_hoje == "MD-1":
            recomendacoes.append(("🟡", "DIA MD-1 — TAPERING",
                "Sessão curta de ativação neuromuscular. Volume e intensidade reduzidos — "
                "preservar energia para o jogo. Incluir: mobilidade, passes curtos, "
                "pequenos sprints de ativação (<20m, baixa velocidade). SEM sprint máximo."))
        elif dia_md_hoje == "MD":
            recomendacoes.append(("🎯", "DIA DE JOGO",
                "Aquecimento progressivo com sprints de ativação. "
                "Monitorizar Hooper Index pré-jogo e identificar jogadores com sinais de fadiga."))

    # ── 2. ACWR ───────────────────────────────────────────────────────────────
    if acwr_dict:
        acwr_vals    = [d["acwr"] for d in acwr_dict.values()]
        n_risco_acwr = len([v for v in acwr_vals if v > 1.5])
        n_atenc_acwr = len([v for v in acwr_vals if 1.3 < v <= 1.5])
        n_sub_acwr   = len([v for v in acwr_vals if v < 0.8])
        jogs_risco_a = [j for j,d in acwr_dict.items() if d["acwr"] > 1.5]
        jogs_atenc_a = [j for j,d in acwr_dict.items() if 1.3 < d["acwr"] <= 1.5]

        # Incluir posição no alerta individual (lookup no df completo)
        def get_pos(jog):
            if "Posição" not in df.columns: return ""
            p = df[df["Jogador"]==jog]["Posição"].dropna()
            return f" ({p.iloc[-1]})" if not p.empty else ""

        if n_risco_acwr >= 3:
            recomendacoes.append(("🔴", "REDUZIR CARGA — EQUIPA",
                f"{n_risco_acwr} jogadores com ACWR>1.5. Sessão de baixa intensidade para toda a equipa. "
                "Foco: trabalho técnico sem pressão, posse estática, mobilidade e recuperação ativa."))
        elif n_risco_acwr >= 1:
            jogs_str = ", ".join(f"{j}{get_pos(j)}" for j in jogs_risco_a)
            atenc_str = f" Monitorizar também: {', '.join(jogs_atenc_a)}." if jogs_atenc_a else ""
            recomendacoes.append(("🟡", "GESTÃO INDIVIDUAL — ACWR",
                f"Reduzir carga de: {jogs_str}. Restante equipa pode treinar normalmente.{atenc_str}"))
        elif n_sub_acwr >= 3 and (not perfil_hoje or perfil_hoje["intensidade"] in ["alta","media"]):
            recomendacoes.append(("🔵", "AUMENTAR ESTÍMULO",
                f"{n_sub_acwr} jogadores em sub-carga crónica (ACWR<0.8). "
                "Incluir: jogos reduzidos de alta intensidade, sprints em transição, pressing intenso."))

    # ── 3. Wellness / Hooper ──────────────────────────────────────────────────
    if not pd.isna(hooper_media):
        if hooper_media >= 14:
            recomendacoes.append(("🔴", "PRIORIZAR RECUPERAÇÃO — WELLNESS",
                f"Hooper médio {hooper_media:.1f}/20 — fadiga acumulada significativa. "
                "Reduzir volume e intensidade desta sessão. Foco em mobilidade e recuperação."))
        elif hooper_media >= 10:
            ul_df = df_view.sort_values("Data").groupby("Jogador").last().reset_index() if "Hooper Index" in df_view.columns else pd.DataFrame()
            jogs_hi = ul_df[ul_df["Hooper Index"] >= 12]["Jogador"].tolist() if not ul_df.empty else []
            if jogs_hi:
                recomendacoes.append(("🟡", "WELLNESS EM ATENÇÃO",
                    f"Hooper médio moderado ({hooper_media:.1f}/20). "
                    f"Jogadores a monitorizar: {', '.join(jogs_hi[:3])}. Considerar redução individual."))

    # ── 4. Exposição a alta velocidade ────────────────────────────────────────
    n_sem_sprint = len([a for a in alertas_criticos + alertas_atencao if a["tipo"] == "Vmáx"])
    sprint_indicado = perfil_hoje["sprint"] if perfil_hoje else True

    if n_sem_sprint >= 2:
        jogs_v = [a["jog"] for a in alertas_criticos + alertas_atencao if a["tipo"] == "Vmáx"]
        if sprint_indicado:
            recomendacoes.append(("🏃", "INCLUIR EXPOSIÇÃO A ALTA VELOCIDADE",
                f"{n_sem_sprint} jogadores sem sprint ≥90% Vmáx recentemente: {', '.join(jogs_v[:4])}. "
                "Incluir: situações 1v1 em espaço amplo, acelerações em transição, sprints progressivos."))
        else:
            recomendacoes.append(("ℹ️", "NOTA — VELOCIDADE MÁXIMA",
                f"{n_sem_sprint} jogadores sem exposição recente a alta velocidade. "
                f"O perfil deste dia ({dia_md_hoje or 'atual'}) não é ideal para sprints máximos — "
                "planear exposição na próxima sessão de alta intensidade."))

    # ── Default ───────────────────────────────────────────────────────────────
    if not recomendacoes:
        foco_txt = f" Para este {dia_md_hoje}: foco em {perfil_hoje['foco']}." if perfil_hoje and dia_md_hoje else ""
        recomendacoes.append(("🟢", "MANTER PLANO",
            f"Equipa dentro dos parâmetros normais.{foco_txt} Continuar a monitorizar individualmente."))

    # ── Renderizar badge Dia MD + recomendações ───────────────────────────────
    if dia_md_hoje:
        cor_dia = {"MD-5":"#e63946","MD-4":"#f39c12","MD-3":"#e63946",
                   "MD-2":"#f39c12","MD-1":"#9b59b6","MD":"#e63946",
                   "MD+1":"#3498db","MD+2":"#2ecc71"}.get(dia_md_hoje,"#888")
        foco_str = perfil_hoje["foco"] if perfil_hoje else "Treino"
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:8px;background:{cor_dia}15;'
            f'border:1px solid {cor_dia}40;border-radius:8px;padding:6px 14px;margin-bottom:10px">'
            f'<span style="font-family:monospace;font-weight:700;color:{cor_dia};font-size:0.85rem">{dia_md_hoje}</span>'
            f'<span style="font-size:0.75rem;color:rgba(255,255,255,0.5)">{foco_str}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    COR_REC = {"🔴":"#e74c3c","🟡":"#f39c12","🟢":"#2ecc71","🔵":"#3498db",
               "🏃":"#f39c12","🎯":"#e63946","ℹ️":"#7f8c8d"}
    for icon, titulo, texto in recomendacoes[:3]:
        cor_rec = COR_REC.get(icon, "#888")
        st.markdown(
            f'<div style="background:{cor_rec}0a;border:1px solid {cor_rec}30;border-radius:12px;'
            f'padding:16px 20px;margin:6px 0">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            f'<span style="font-size:1.2rem">{icon}</span>'
            f'<span style="font-weight:700;font-size:0.85rem;color:{cor_rec};letter-spacing:1px">{titulo}</span>'
            f'</div>'
            f'<div style="font-size:0.82rem;color:rgba(255,255,255,0.75);line-height:1.6">{texto}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.divider()

    # ── RANKING DE JOGADORES POR MÉTRICA (estilo Match Player Performance) ────
    st.markdown('<p class="section-title">🏆 Ranking de Desempenho — Semana Atual</p>', unsafe_allow_html=True)

    METRICAS = {
        "Carga Interna": {"col": "Carga Interna", "cor": "#e63946", "icon": "⚡", "unit": " UA"},
        "Distância Total": {"col": "Distância Total (m)", "cor": "#2563eb", "icon": "📏", "unit": "m"},
        "HSR": {"col": "Distância HSR (m)", "cor": "#f59e0b", "icon": "🏃", "unit": "m"},
        "Sprint": {"col": "Distância Sprint (m)", "cor": "#dc2626", "icon": "💨", "unit": "m"},
        "Velocidade Máx": {"col": "Vel. Máx (km/h)", "cor": "#8b5cf6", "icon": "🚀", "unit": " km/h"},
    }

    # Calcular ranking por jogador (MC atual) para cada métrica disponível
    metricas_disponiveis = []
    for metrica_nome, config in METRICAS.items():
        col_nome = config["col"]
        if col_nome not in df_view.columns:
            continue
        if mc_recente and "Microciclo (Nr)" in df_view.columns:
            ranking_df = df_view[df_view["Microciclo (Nr)"]==mc_recente].groupby("Jogador")[col_nome].mean().sort_values(ascending=False)
        else:
            ranking_df = df_view.groupby("Jogador")[col_nome].mean().sort_values(ascending=False)
        ranking_df = ranking_df.dropna()
        if ranking_df.empty:
            continue
        metricas_disponiveis.append((metrica_nome, config, ranking_df))

    if metricas_disponiveis:
        # ── KPI tiles com totais de equipa (estilo TEAM TOTAL DISTANCE) ────────
        kpi_cols = st.columns(len(metricas_disponiveis))
        for kpi_col, (metrica_nome, config, ranking_df) in zip(kpi_cols, metricas_disponiveis):
            with kpi_col:
                total_equipa = ranking_df.sum()
                media_jogador = ranking_df.mean()
                team_kpi_tile(
                    f"Equipa · {metrica_nome}",
                    total_equipa,
                    config["unit"].strip(),
                    f"média {media_jogador:,.0f}{config['unit']} / jogador",
                    config["cor"],
                )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        # ── Cards Top 3 / Bottom 3 com barras horizontais, grid de 2 colunas ───
        cols_grid = st.columns(2)
        for idx, (metrica_nome, config, ranking_df) in enumerate(metricas_disponiveis):
            top_3 = list(ranking_df.head(3).items())
            bottom_3 = list(ranking_df.tail(3).items())[::-1]  # pior primeiro
            with cols_grid[idx % 2]:
                ranking_metric_card(config["icon"], metrica_nome, config["cor"], top_3, bottom_3, config["unit"])
    else:
        st.info("📊 Dados de distância/velocidade não disponíveis. Mostrando apenas Carga Interna.")

    st.divider()

    # ── Evolução ACWR (últimos 4 MC) ──────────────────────────────────────────
    col_chart, col_topbot = st.columns([2, 1])

    with col_chart:
        st.markdown('<p class="section-title">📈 Evolução da Carga</p>', unsafe_allow_html=True)
        if "Carga Interna" in df_view.columns and "Microciclo (Nr)" in df_view.columns:
            mcs_ultimos = sorted(df_view["Microciclo (Nr)"].dropna().unique())[-6:]
            ci_evolucao = df_view[df_view["Microciclo (Nr)"].isin(mcs_ultimos)].groupby("Microciclo (Nr)")["Carga Interna"].mean().reset_index()
            ci_evolucao = ci_evolucao.sort_values("Microciclo (Nr)")
            fig_ci_dash = go.Figure()
            fig_ci_dash.add_trace(go.Scatter(
                x=ci_evolucao["Microciclo (Nr)"].astype(str),
                y=ci_evolucao["Carga Interna"],
                mode="lines+markers+text",
                text=ci_evolucao["Carga Interna"].round(0).astype(int).astype(str),
                textposition="top center",
                textfont=dict(size=10, color="white"),
                line=dict(color="#e63946", width=3),
                marker=dict(size=10, color="#e63946", line=dict(width=2, color="white")),
                fill="tozeroy", fillcolor="rgba(230,57,70,0.06)",
            ))
            fig_ci_dash.update_layout(
                height=260,
                yaxis_title="CI Médio (UA)",
                xaxis_title="Microciclo",
                showlegend=False,
                margin=dict(t=10, b=30, l=50, r=10),
                template="lm_professional",
            )
            st.plotly_chart(fig_ci_dash, use_container_width=True)

    with col_topbot:
        st.markdown('<p class="section-title">📊 Resumo Semanal</p>', unsafe_allow_html=True)
        if mc_recente and "Carga Interna" in df_view.columns:
            ci_jog = df_view[df_view["Microciclo (Nr)"]==mc_recente].groupby("Jogador")["Carga Interna"].mean().sort_values(ascending=False)
            if len(ci_jog) >= 3:
                ranking_metric_card(
                    "⚡", "Carga Interna", "#e63946",
                    list(ci_jog.head(3).items()),
                    list(ci_jog.tail(3).items())[::-1],
                    " UA",
                )

    st.divider()

    # ── Quick Actions ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">⚡ Ações Rápidas</p>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)
    if qa1.button("👤 Ver Jogadores", use_container_width=True):
        st.session_state["seccao"] = "jogadores"; st.rerun()
    if qa2.button("🏟️ Ver Equipa", use_container_width=True):
        st.session_state["seccao"] = "equipa"; st.rerun()
    if qa3.button("📋 Planeamento", use_container_width=True):
        st.session_state["seccao"] = "planeamento"; st.rerun()
    if qa4.button("🔬 Avançado", use_container_width=True):
        st.session_state["seccao"] = "avancado"; st.rerun()

    # ── Export button ─────────────────────────────────────────────────────────
    st.divider()
    alertas_html = "".join(
        f'<tr><td style="color:{a["cor"]};font-weight:700">{a["jog"]}</td>'
        f'<td>{a["tipo"]}</td><td>{a["msg"]}</td><td><b>{a["val"]}</b></td></tr>'
        for a in top_alertas
    )
    rec_html = "".join(f"<li><b>{t}:</b> {txt}</li>" for _, t, txt in recomendacoes[:3])
    ci_media_str   = f"{ci_media:,.0f}"   if not pd.isna(ci_media)   else "—"
    acwr_media_str = f"{acwr_media:.2f}"  if not pd.isna(acwr_media) else "—"
    hooper_str     = f"{hooper_media:.1f}" if not pd.isna(hooper_media) else "—"
    html_dash = gerar_pdf_html(f"""
<h1 style="color:#e63946">Dashboard — {data_str}</h1>
<table><tr><th>CI Médio</th><th>ACWR Médio</th><th>Hooper</th><th>Alertas</th></tr>
<tr><td>{ci_media_str}</td><td>{acwr_media_str}</td>
<td>{hooper_str}/20</td><td>{n_risco}</td></tr></table>
<h2>Alertas Prioritários</h2>
<table><tr><th>Jogador</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr>{alertas_html}</table>
<h2>Recomendações</h2><ul>{rec_html}</ul>
""", f"Dashboard_{hoje.strftime('%Y%m%d')}.html")
    botao_download_html(html_dash, f"Dashboard_{hoje.strftime('%Y%m%d')}.html", "📥 Exportar Resumo do Dia")
