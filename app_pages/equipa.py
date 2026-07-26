"""LoadMonitorSystem — Página Equipa"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.dados import get_mets_gps
from utils.calculos import calcular_acwr, calcular_acwr_global, cor_acwr
from utils.ui_safe import lm_header, ranking_top_list, tabela_carga_colorida

def render(df, excel_path, **kwargs):
    _lm_user = kwargs.get("lm_user", {})
    _lm_plano = _lm_user.get("plano", "free")
    _lm_nome = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")
    lm_header("Equipa", "Visão global do plantel — carga, GPS, wellness e performance", "Equipa")

    # ── Estado partilhado ─────────────────────────────────────────────────────
    F = st.session_state.get("lm_filters", {})
    df_f         = F.get("df_f", df)
    df_f_dia     = F.get("df_f_dia", df)
    mc_sel       = F.get("mc_sel", [])
    dia_md_sel   = F.get("dia_md_sel", [])
    pos_sel      = F.get("pos_sel", [])
    jogador_sel  = F.get("jogador_sel", df["Jogador"].iloc[0] if "Jogador" in df.columns and not df.empty else "")
    posicoes     = F.get("posicoes", [])
    microciclos  = F.get("microciclos", [])
    jogadores    = F.get("jogadores", [])

    H = st.session_state.get("lm_helpers", {})
    scatter_jogadores = H.get("scatter_jogadores")
    calcular_delta    = H.get("calcular_delta")
    AUTH_DISPONIVEL   = H.get("AUTH_DISPONIVEL", False)
    tem_acesso        = H.get("tem_acesso", lambda u, f: False)
    _vista_eq = st.selectbox(
        "Vista",
        ["📊 Visão Geral", "📐 Por Posição", "🏃 Vmáx", "🔄 Comparar MCs", "⚡ Monotonia & Strain"],
        key="sel_vista_eq", label_visibility="collapsed"
    )
    _EQ_LABELS = ["📊 Visão Geral","📐 Por Posição","🏃 Vmáx","🔄 Comparar MCs","⚡ Monotonia & Strain"]
    _eq_idx = _EQ_LABELS.index(_vista_eq) if _vista_eq in _EQ_LABELS else 0

    if _eq_idx == 0:
        df_f = df_f_dia
        st.caption(f"{len(df_f)} registos · {df_f['Jogador'].nunique()} jogadores · {len(mc_sel)} microciclo(s) selecionado(s)")

        # ── KPIs globais com tendência ────────────────────────────────────────────
        mc_atual_eq  = mc_sel[0] if mc_sel else None
        mcs_todos    = sorted(df["Microciclo (Nr)"].dropna().unique())
        mc_ant_eq    = mcs_todos[mcs_todos.index(mc_atual_eq)-1] if mc_atual_eq in mcs_todos and mcs_todos.index(mc_atual_eq) > 0 else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sessões Totais", f"{len(df_f):,}", help="Total de registos nos filtros selecionados")

        for col_st, col_nm, fmt, label, ajuda, inverter in [
                (c2, "Distância Total (m)", ":,.0f", "Dist. Média (m)", "Distância média por sessão",         False),
                (c3, "PSE Sessão",          ":.1f",  "PSE Média",       "Perceção Subjetiva de Esforço média", False),
                (c4, "Carga Interna",       ":,.0f", "CI Médio",        "Carga Interna média (PSE × Duração)", False),
        ]:
                if col_nm in df_f.columns and mc_atual_eq:
                    val, delta = calcular_delta(df, col_nm, mc_atual_eq, mc_ant_eq)
                    # Hooper: delta negativo é BOM (menos stress/fadiga) → inverter sinal para Streamlit
                    delta_display = (-delta) if (delta is not None and inverter) else delta
                    delta_str = f"{delta_display:+.1f}% vs MC ant." if delta_display is not None else None
                    col_st.metric(label, format(val, fmt.lstrip(":")) if val is not None and not pd.isna(val) else "—",
                                  delta=delta_str,
                                  delta_color="inverse" if inverter else "normal",
                                  help=ajuda)
                else:
                    col_st.metric(label, "—", help=ajuda)

        st.divider()

        # ── ACWR por jogador (último valor) ───────────────────────────────────────
        st.markdown('<p class="section-title">🚦 ACWR — Risco por Jogador (última sessão)</p>', unsafe_allow_html=True)

        acwr_rows = []
        for jog in jogadores:
                sub = calcular_acwr(df[df["Microciclo (Nr)"].isin(mc_sel)] if mc_sel else df, jog)
                if not sub.empty and "ACWR" in sub.columns and sub["ACWR"].notna().any():
                    last = sub.dropna(subset=["ACWR"]).iloc[-1]
                    acwr_rows.append({
                        "Jogador": jog,
                        "Posição": last.get("Posição", ""),
                        "ACWR": round(last["ACWR"], 2),
                        "CI Agudo": round(last.get("Carga Aguda", 0)),
                        "CI Crónico": round(last.get("Carga Crónica", 0)),
                        "Estado": cor_acwr(last["ACWR"]),
                    })

        if acwr_rows:
                df_acwr = pd.DataFrame(acwr_rows).sort_values("ACWR", ascending=False)
                df_acwr["ACWR"] = pd.to_numeric(df_acwr["ACWR"], errors="coerce").fillna(0)

                fig_acwr = go.Figure()
                cores = []
                for _, row in df_acwr.iterrows():
                    v = row["ACWR"]
                    if v > 1.5:    cor = "#e74c3c"
                    elif v > 1.3:  cor = "#f39c12"
                    elif v >= 0.8: cor = "#2ecc71"
                    else:           cor = "#3498db"
                    cores.append(cor)

                fig_acwr.add_trace(go.Bar(
                    x=df_acwr["Jogador"], y=df_acwr["ACWR"],
                    marker_color=cores, text=df_acwr["ACWR"].round(2), textposition="outside",
                ))
                fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c",  annotation_text="Risco (1.5)")
                fig_acwr.add_hline(y=1.3, line_dash="dash", line_color="#f39c12",  annotation_text="Atenção (1.3)")
                fig_acwr.add_hline(y=0.8, line_dash="dash", line_color="#3498db",  annotation_text="Sub-carga (0.8)")
                fig_acwr.update_layout(
                    yaxis_title="ACWR",
                    height=380,
                    showlegend=False,
                    margin=dict(t=20, b=10, l=20, r=20),
                    xaxis_title="Jogador",
                    template="lm_professional",
                )
                st.plotly_chart(fig_acwr, use_container_width=True)

                # tabela resumo
                st.dataframe(
                    df_acwr.set_index("Jogador")[["Posição", "ACWR", "CI Agudo", "CI Crónico", "Estado"]],
                    use_container_width=True,
                )

        st.divider()

        # ── Carga Interna por microciclo ──────────────────────────────────────────
        st.markdown('<p class="section-title">📈 Carga Interna Média por Microciclo</p>', unsafe_allow_html=True)

        if "Carga Interna" in df_f and "Microciclo (Nr)" in df_f:
                ci_mc = df_f.groupby(["Microciclo (Nr)", "Jogador"])["Carga Interna"].mean().reset_index()
                ci_mc_mean = df_f.groupby("Microciclo (Nr)")["Carga Interna"].mean().reset_index()
                fig_ci = px.line(ci_mc_mean, x="Microciclo (Nr)", y="Carga Interna",
                                 markers=True, labels={"Carga Interna": "CI Médio", "Microciclo (Nr)": "Microciclo"})
                fig_ci.update_traces(line_color="#e63946", line_width=3, marker_size=8)
                fig_ci.update_layout(
                    height=300,
                    margin=dict(t=20, l=20, r=20, b=20),
                    template="lm_professional",
                )
                st.plotly_chart(fig_ci, use_container_width=True)

        # ── Perfil de Carga Externa (estilo Predicted External Load Profile) ──────
        st.divider()
        st.markdown('<p class="section-title">🏃 Perfil de Carga Externa — por Jogador</p>', unsafe_allow_html=True)

        COLUNAS_CARGA_EQ = [
            {"col": "Distância Total (m)",  "label": "Dist. Total (m)",  "cor": "#2563eb", "casas": 0},
            {"col": "Distância HSR (m)",    "label": "HSR (m)",          "cor": "#f59e0b", "casas": 0},
            {"col": "Distância Sprint (m)", "label": "Sprint (m)",       "cor": "#dc2626", "casas": 0},
            {"col": "Acc (n)",              "label": "Acelerações",      "cor": "#14b8a6", "casas": 0},
            {"col": "Dcc (n)",              "label": "Desacelerações",   "cor": "#10b981", "casas": 0},
            {"col": "Vel. Máx (km/h)",      "label": "Vel. Máx (km/h)",  "cor": "#8b5cf6", "casas": 1},
        ]
        colunas_carga_disp = [c for c in COLUNAS_CARGA_EQ if c["col"] in df_f.columns and df_f[c["col"]].notna().any()]

        if colunas_carga_disp:
                df_carga_jog = df_f.groupby("Jogador")[[c["col"] for c in colunas_carga_disp]].mean().reset_index()
                df_carga_jog = df_carga_jog.sort_values(colunas_carga_disp[0]["col"], ascending=False)
                tabela_carga_colorida(df_carga_jog, "Jogador", colunas_carga_disp)
        else:
                st.info("Sem métricas GPS disponíveis para os filtros selecionados.")

        # ── Scatter GPS — Perfil físico do plantel ────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🎯 Scatter — Perfil Físico do Plantel</p>', unsafe_allow_html=True)
        st.caption("Cada círculo = um jogador. Posiciona-se de acordo com as duas métricas escolhidas.")

        METS_SCATTER = get_mets_gps(df)
        mets_sc_disp = [m for m in METS_SCATTER if m in df_f.columns]

        if len(mets_sc_disp) >= 2:
                sc_col1, sc_col2, sc_col3 = st.columns(3)
                x_sc = sc_col1.selectbox("Eixo X", mets_sc_disp, index=0, key="eq_sc_x")
                y_sc = sc_col2.selectbox("Eixo Y", mets_sc_disp, index=1, key="eq_sc_y")
                size_sc = sc_col3.selectbox("Tamanho (opcional)", ["—"] + mets_sc_disp, index=0, key="eq_sc_size")

                # Médias por jogador
                df_sc_eq = df_f.groupby("Jogador")[mets_sc_disp].mean().reset_index()
                if "Posição" in df_f.columns:
                    pos_map = df_f.groupby("Jogador")["Posição"].last()
                    df_sc_eq["Posição"] = df_sc_eq["Jogador"].map(pos_map)

                fig_sc_eq = scatter_jogadores(
                    df_sc_eq, x_sc, y_sc,
                    title=f"{x_sc.split('(')[0].strip()} vs {y_sc.split('(')[0].strip()} — Médias do Plantel",
                    color_col="Posição" if "Posição" in df_sc_eq.columns else "Jogador",
                    size_col=size_sc if size_sc != "—" else None,
                    height=520,
                )
                if fig_sc_eq:
                    st.plotly_chart(fig_sc_eq, use_container_width=True)
                    st.caption("🟢 Quadrante superior direito = acima da média em ambas as métricas · Linhas pontilhadas = média da equipa")

        # ── Wellness da equipa ────────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">💤 Wellness da Equipa (médias)</p>', unsafe_allow_html=True)

        wellness_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
        wellness_disp = [c for c in wellness_cols if c in df_f.columns]

        if wellness_disp:
                w_mean = df_f[wellness_disp].mean().reset_index()
                w_mean.columns = ["Métrica", "Média"]
                fig_w = px.bar(w_mean, x="Métrica", y="Média", color="Métrica",
                               color_discrete_sequence=px.colors.qualitative.Pastel,
                               text=w_mean["Média"].round(1))
                fig_w.update_traces(textposition="outside")
                fig_w.update_layout(
                    height=320,
                    showlegend=False,
                    margin=dict(t=10, l=20, r=20, b=20),
                    template="lm_professional",
                )
                st.plotly_chart(fig_w, use_container_width=True)

        # ── Conclusões automáticas ────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)

        insights = []

        if acwr_rows:
                em_risco    = [r["Jogador"] for r in acwr_rows if "RISCO"    in r["Estado"]]
                em_atencao  = [r["Jogador"] for r in acwr_rows if "ATENÇÃO"  in r["Estado"]]
                sub_carga   = [r["Jogador"] for r in acwr_rows if "SUB-CARGA" in r["Estado"]]

                if em_risco:
                    insights.append(f"🔴 **Risco de lesão elevado**: {', '.join(em_risco)} — ACWR > 1.5. Reduzir carga imediatamente.")
                if em_atencao:
                    insights.append(f"🟡 **Monitorizar de perto**: {', '.join(em_atencao)} — ACWR entre 1.3 e 1.5.")
                if sub_carga:
                    insights.append(f"🔵 **Sub-carga**: {', '.join(sub_carga)} — ACWR < 0.8. Avaliar razão (lesão/recuperação?).")
                if not em_risco and not em_atencao:
                    insights.append("🟢 **Toda a equipa dentro do intervalo seguro de ACWR (0.8–1.3).**")

        if "Hooper Index" in df_f.columns:
                h_mean = df_f["Hooper Index"].mean()
                if h_mean >= 14:
                    insights.append(f"⚠️ **Hooper Index médio elevado** ({h_mean:.1f}/20) — equipa com sinais de fadiga/stress acumulado.")
                elif h_mean <= 8:
                    insights.append(f"✅ **Hooper Index médio excelente** ({h_mean:.1f}/20) — bem-estar geral muito positivo.")
                else:
                    insights.append(f"ℹ️ **Hooper Index médio** ({h_mean:.1f}/20) — bem-estar dentro dos parâmetros normais.")

        if "PSE Sessão" in df_f.columns:
                pse_mean = df_f["PSE Sessão"].mean()
                insights.append(f"📊 **PSE média da equipa**: {pse_mean:.1f}/10 nos microciclos selecionados.")

        if "Distância Total (m)" in df_f.columns:
                dist_mean = df_f["Distância Total (m)"].mean()
                insights.append(f"📏 **Distância média por sessão**: {dist_mean:,.0f} m.")

        for ins in insights:
                st.markdown(ins)



    if _eq_idx == 1:
            df_f = df_f_dia

            if "Posição" not in df_f.columns or df_f["Posição"].isna().all():
                st.warning("Coluna 'Posição' não encontrada nos dados.")

            metrica_pos = st.selectbox("Métrica a comparar", [
                "Distância Total (m)", "HSR (m)", "Sprint (m)",
                "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)", "Hooper Index"
            ])

            if metrica_pos in df_f.columns:
                # Box plot por posição
                fig_box = px.box(df_f, x="Posição", y=metrica_pos,
                                 color="Posição", points="all",
                                 hover_data=["Jogador", "Data"] if "Data" in df_f.columns else ["Jogador"],
                                 color_discrete_sequence=px.colors.qualitative.Bold)
                fig_box.update_layout(height=420, plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                       showlegend=False, margin=dict(t=20))
                st.plotly_chart(fig_box, use_container_width=True)

                # Scatter por posição
                st.divider()
                st.markdown('<p class="section-title">🎯 Scatter — Jogadores por Posição</p>', unsafe_allow_html=True)
                st.caption("Cada círculo = um jogador, cor = posição. Identifica padrões e outliers.")

                METS_SC_POS = get_mets_gps(df_f)
                mets_sc_pos = [m for m in METS_SC_POS if m in df_f.columns and df_f[m].notna().any()]

                if len(mets_sc_pos) >= 2:
                    sc_p1, sc_p2 = st.columns(2)
                    x_sc_pos = sc_p1.selectbox("Eixo X", mets_sc_pos, index=0, key="pos_sc_x")
                    y_sc_pos = sc_p2.selectbox("Eixo Y", mets_sc_pos, index=1, key="pos_sc_y")
                    df_sc_pos = df_f.groupby("Jogador")[mets_sc_pos].mean().reset_index()
                    if "Posição" in df_f.columns:
                        pos_map2 = df_f.groupby("Jogador")["Posição"].last()
                        df_sc_pos["Posição"] = df_sc_pos["Jogador"].map(pos_map2)
                    fig_sc_pos = scatter_jogadores(
                        df_sc_pos, x_sc_pos, y_sc_pos,
                        title=f"{x_sc_pos.split('(')[0].strip()} vs {y_sc_pos.split('(')[0].strip()}",
                        color_col="Posição" if "Posição" in df_sc_pos.columns else "Jogador",
                        height=500,
                    )
                    if fig_sc_pos:
                        st.plotly_chart(fig_sc_pos, use_container_width=True)

                st.divider()
                # Médias por posição e jogador
                st.markdown('<p class="section-title">Médias por Posição e Jogador</p>', unsafe_allow_html=True)
                df_pos = df_f.groupby(["Posição", "Jogador"])[metrica_pos].mean(numeric_only=True).reset_index()
                df_pos.columns = ["Posição", "Jogador", metrica_pos]
                df_pos = df_pos.sort_values([metrica_pos], ascending=False)

                fig_jog_pos = px.bar(df_pos, x="Jogador", y=metrica_pos,
                                      color="Posição", barmode="group",
                                      color_discrete_sequence=px.colors.qualitative.Bold,
                                      labels={metrica_pos: metrica_pos, "Jogador": ""})
                fig_jog_pos.update_layout(height=360, plot_bgcolor="rgba(0,0,0,0)",
                                           paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                st.plotly_chart(fig_jog_pos, use_container_width=True)

            # Radar por posição
            st.divider()
            st.markdown('<p class="section-title">📡 Radar de Perfil por Posição</p>', unsafe_allow_html=True)

            radar_cols = get_mets_gps(df)
            radar_disp = [c for c in radar_cols if c in df_f.columns]

            if radar_disp:
                pos_means = df_f.groupby("Posição")[radar_disp].mean(numeric_only=True).reset_index()
                # Normalizar 0-100
                for col in radar_disp:
                    max_v = pos_means[col].max()
                    pos_means[col] = pos_means[col] / max_v * 100 if max_v > 0 else 0

                fig_radar = go.Figure()
                cores_radar = px.colors.qualitative.Bold
                for i, (_, row) in enumerate(pos_means.iterrows()):
                    vals = list(row[radar_disp]) + [row[radar_disp[0]]]
                    cats = radar_disp + [radar_disp[0]]
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals, theta=cats, fill="toself",
                        name=row["Posição"],
                        line_color=cores_radar[i % len(cores_radar)],
                        opacity=0.75,
                    ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    height=440, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                )
                st.plotly_chart(fig_radar, use_container_width=True)


    if _eq_idx == 2:
            if AUTH_DISPONIVEL and not tem_acesso(_lm_user, "vmax"):
                st.warning("⚡ Esta funcionalidade é exclusiva do plano **Pro**.")
                st.markdown("Faz upgrade para aceder ao Vmáx Monitor, GPS, RHIE e muito mais.")

            # ── Calcular métricas de Vmáx a partir de BD_Carga ───────────────────────
            def calcular_vmax_monitor(df_base: pd.DataFrame):
                """Calcula perfil de Vmáx para todos os jogadores."""
                if "Vel. Máx (km/h)" not in df_base.columns or "Data" not in df_base.columns:
                    return pd.DataFrame()

                rows = []
                for jog in sorted(df_base["Jogador"].dropna().unique()):
                    sub = df_base[df_base["Jogador"] == jog].copy()
                    sub = sub.dropna(subset=["Data", "Vel. Máx (km/h)"])
                    if sub.empty:
                        continue

                    sub = sub.sort_values("Data")
                    vmax_record = sub["Vel. Máx (km/h)"].max()
                    posicao = sub["Posição"].iloc[-1] if "Posição" in sub.columns else "—"

                    # Limiar 90% do recorde
                    lim_90 = vmax_record * 0.90
                    lim_85 = vmax_record * 0.85
                    lim_95 = vmax_record * 0.95

                    # Última sessão com Vmáx ≥ 90% do recorde
                    sub_90 = sub[sub["Vel. Máx (km/h)"] >= lim_90]
                    if not sub_90.empty:
                        ultima_data_90 = sub_90["Data"].max()
                        dias_sem_90 = (sub["Data"].max() - ultima_data_90).days
                    else:
                        ultima_data_90 = pd.NaT
                        dias_sem_90 = 999

                    # Última sessão com Vmáx ≥ 95%
                    sub_95 = sub[sub["Vel. Máx (km/h)"] >= lim_95]
                    if not sub_95.empty:
                        ultima_data_95 = sub_95["Data"].max()
                        dias_sem_95 = (sub["Data"].max() - ultima_data_95).days
                    else:
                        ultima_data_95 = pd.NaT
                        dias_sem_95 = 999

                    # Total sessões ≥90%
                    total_sess_90 = len(sub_90)
                    total_sess = len(sub)
                    pct_sess_90 = total_sess_90 / total_sess if total_sess > 0 else 0

                    # Vmáx mais recente
                    vmax_ultima = sub.iloc[-1]["Vel. Máx (km/h)"]
                    pct_record = vmax_ultima / vmax_record if vmax_record > 0 else 0

                    # Alerta
                    if dias_sem_90 > 7:
                        alerta = "🔴 RISCO"
                        alerta_cor = "#e74c3c"
                    elif dias_sem_90 >= 5:
                        alerta = "🟡 ATENÇÃO"
                        alerta_cor = "#f39c12"
                    else:
                        alerta = "🟢 OK"
                        alerta_cor = "#2ecc71"

                    rows.append({
                        "Jogador": jog,
                        "Posição": posicao,
                        "Vmáx Record (km/h)": round(vmax_record, 1),
                        "Última Vmáx (km/h)": round(vmax_ultima, 1),
                        "% do Recorde": round(pct_record * 100, 1),
                        "Última Data ≥90%": ultima_data_90,
                        "Dias s/ ≥90% Vmáx": int(dias_sem_90) if dias_sem_90 < 999 else "Nunca",
                        "Última Data ≥95%": ultima_data_95,
                        "Dias s/ ≥95% Vmáx": int(dias_sem_95) if dias_sem_95 < 999 else "Nunca",
                        "Sessões ≥90%": total_sess_90,
                        "% Sessões ≥90%": round(pct_sess_90 * 100, 1),
                        "Alerta": alerta,
                        "_alerta_cor": alerta_cor,
                        "_lim_90": round(lim_90, 1),
                        "_lim_85": round(lim_85, 1),
                        "_lim_95": round(lim_95, 1),
                    })

                return pd.DataFrame(rows)

            df_vmax = calcular_vmax_monitor(df)

            if df_vmax.empty:
                st.warning("Dados de Vmáx não encontrados. Certifica-te que a folha BD_Carga tem a coluna 'Vel. Máx (km/h)'.")
                return

            # ── SECÇÃO A — Perfil geral da equipa ────────────────────────────────────
            st.markdown('<p class="section-title">A — Perfil de Velocidade & Alerta de Inatividade</p>', unsafe_allow_html=True)

            # KPIs rápidos
            c1, c2, c3, c4 = st.columns(4)
            em_risco_v   = df_vmax[df_vmax["Alerta"] == "🔴 RISCO"]
            em_atencao_v = df_vmax[df_vmax["Alerta"] == "🟡 ATENÇÃO"]
            em_ok_v      = df_vmax[df_vmax["Alerta"] == "🟢 OK"]
            c1.metric("🔴 Em Risco (>7 dias s/ ≥90%)",    len(em_risco_v))
            c2.metric("🟡 Em Atenção (5–7 dias)",            len(em_atencao_v))
            c3.metric("🟢 OK (<7 dias)",                    len(em_ok_v))
            c4.metric("Vmáx Record da Equipa",              f"{df_vmax['Vmáx Record (km/h)'].max():.1f} km/h")

            st.divider()

            # Gráfico de barras — Vmáx Record vs Última Vmáx
            st.markdown('<p class="section-title">Vmáx Record vs Última Vmáx por Jogador</p>', unsafe_allow_html=True)

            df_vmax_sorted = df_vmax.sort_values("Vmáx Record (km/h)", ascending=True)

            fig_vmax_bars = go.Figure()
            fig_vmax_bars.add_trace(go.Bar(
                y=df_vmax_sorted["Jogador"],
                x=df_vmax_sorted["Vmáx Record (km/h)"],
                name="Vmáx Record",
                orientation="h",
                marker_color="#e63946",
                opacity=0.85,
            ))
            fig_vmax_bars.add_trace(go.Bar(
                y=df_vmax_sorted["Jogador"],
                x=df_vmax_sorted["Última Vmáx (km/h)"],
                name="Última Vmáx",
                orientation="h",
                marker_color="#457b9d",
                opacity=0.85,
            ))
            fig_vmax_bars.update_layout(
                barmode="overlay",
                height=max(320, len(df_vmax_sorted) * 42),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                xaxis_title="km/h",
                legend=dict(orientation="h", y=1.05),
                margin=dict(t=30, b=10),
            )
            st.plotly_chart(fig_vmax_bars, use_container_width=True)

            # Gráfico de dias sem ≥90% Vmáx
            st.markdown('<p class="section-title">Dias sem Atingir ≥90% Vmáx Record</p>', unsafe_allow_html=True)

            df_dias = df_vmax.copy()
            df_dias["Dias_num"] = pd.to_numeric(df_dias["Dias s/ ≥90% Vmáx"], errors="coerce").fillna(999)
            df_dias = df_dias.sort_values("Dias_num", ascending=False)

            cores_dias = []
            for _, row in df_dias.iterrows():
                d = row["Dias_num"]
                if d > 7:    cores_dias.append("#e74c3c")
                elif d > 3:  cores_dias.append("#f39c12")
                else:        cores_dias.append("#2ecc71")

            fig_dias = go.Figure(go.Bar(
                x=df_dias["Jogador"],
                y=df_dias["Dias_num"],
                marker_color=cores_dias,
                text=[f"{int(d)}d" if d < 999 else "—" for d in df_dias["Dias_num"]],
                textposition="outside",
            ))
            fig_dias.add_hline(y=7, line_dash="dash", line_color="#e74c3c", annotation_text="Risco >7 dias")
            fig_dias.add_hline(y=5,  line_dash="dot",  line_color="#f39c12", annotation_text="Atenção ≥5 dias")
            fig_dias.update_layout(
                yaxis_title="Dias",
                height=360,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                margin=dict(t=20, b=10),
            )
            st.plotly_chart(fig_dias, use_container_width=True)

            # % do Recorde — gauge style bar
            st.markdown('<p class="section-title">% do Recorde Pessoal (Última Sessão)</p>', unsafe_allow_html=True)

            df_pct = df_vmax.sort_values("% do Recorde", ascending=True)
            cores_pct = []
            for v in df_pct["% do Recorde"]:
                if v >= 95:   cores_pct.append("#2ecc71")
                elif v >= 90: cores_pct.append("#f39c12")
                else:         cores_pct.append("#e74c3c")

            fig_pct = go.Figure(go.Bar(
                y=df_pct["Jogador"],
                x=df_pct["% do Recorde"],
                orientation="h",
                marker_color=cores_pct,
                text=[f"{v:.1f}%" for v in df_pct["% do Recorde"]],
                textposition="outside",
            ))
            fig_pct.add_vline(x=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
            fig_pct.add_vline(x=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
            fig_pct.update_layout(
                xaxis=dict(title="% do Recorde", range=[70, 105]),
                height=max(300, len(df_pct) * 40),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)",
                margin=dict(t=10, b=10),
            )
            st.plotly_chart(fig_pct, use_container_width=True)

            # Tabela resumo Secção A
            st.markdown('<p class="section-title">Tabela Resumo — Todos os Jogadores</p>', unsafe_allow_html=True)
            cols_tabela = ["Jogador", "Posição", "Vmáx Record (km/h)", "Última Vmáx (km/h)",
                           "% do Recorde", "Dias s/ ≥90% Vmáx", "Dias s/ ≥95% Vmáx",
                           "Sessões ≥90%", "% Sessões ≥90%", "Alerta"]
            st.dataframe(df_vmax[cols_tabela].set_index("Jogador"), use_container_width=True)

            # Scatter Vmáx Record vs Dias sem ≥90%
            st.divider()
            st.markdown('<p class="section-title">🎯 Scatter — Vmáx Record vs Dias sem ≥90%</p>', unsafe_allow_html=True)
            st.caption("Canto superior esquerdo = jogadores rápidos sem exposição recente → máximo risco")

            df_sc_vmax = df_vmax.copy()
            df_sc_vmax["Dias_num"] = pd.to_numeric(df_sc_vmax["Dias s/ ≥90% Vmáx"], errors="coerce").fillna(0)

            if not df_sc_vmax.empty:
                fig_sc_vmax = go.Figure()
                for _, row in df_sc_vmax.iterrows():
                    d = row["Dias_num"]
                    v = row["Vmáx Record (km/h)"]
                    if d > 7:    cor_v = "#e74c3c"
                    elif d > 3:  cor_v = "#f39c12"
                    else:        cor_v = "#2ecc71"
                    fig_sc_vmax.add_trace(go.Scatter(
                        x=[v], y=[d],
                        mode="markers+text",
                        text=[row["Jogador"].split()[0] if isinstance(row["Jogador"], str) else row["Jogador"]],
                        textposition="top center",
                        textfont=dict(size=10, color="white"),
                        marker=dict(size=28, color=cor_v, opacity=0.85, line=dict(width=2, color="white")),
                        hovertext=f'<b>{row["Jogador"]}</b><br>Vmáx Record: {v:.1f} km/h<br>Dias s/ ≥90%: {int(d)}',
                        hoverinfo="text",
                        showlegend=False,
                    ))
                fig_sc_vmax.add_hline(y=7, line_dash="dash", line_color="#e74c3c", annotation_text="Risco >7 dias")
                fig_sc_vmax.add_hline(y=5,  line_dash="dot",  line_color="#f39c12", annotation_text="Atenção ≥5 dias")
                fig_sc_vmax.update_layout(
                    xaxis_title="Vmáx Record (km/h)", yaxis_title="Dias sem ≥90% Vmáx",
                    height=460, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                )
                st.plotly_chart(fig_sc_vmax, use_container_width=True)

            st.divider()

            # ── SECÇÃO B — Histórico individual ──────────────────────────────────────
            st.markdown('<p class="section-title">B — Histórico de Velocidade Individual</p>', unsafe_allow_html=True)

            jog_vmax = st.selectbox("Seleciona o Jogador", sorted(df["Jogador"].dropna().unique()), key="vmax_jog")

            sub_hist = df[df["Jogador"] == jog_vmax].dropna(subset=["Data", "Vel. Máx (km/h)"]).sort_values("Data")

            if not sub_hist.empty:
                vmax_rec = sub_hist["Vel. Máx (km/h)"].max()
                lim_90 = vmax_rec * 0.90
                lim_85 = vmax_rec * 0.85
                lim_95 = vmax_rec * 0.95

                # % do recorde por sessão
                sub_hist = sub_hist.copy()
                sub_hist["% Record"] = (sub_hist["Vel. Máx (km/h)"] / vmax_rec * 100).round(1)

                # KPIs do jogador
                info_jog = df_vmax[df_vmax["Jogador"] == jog_vmax]
                if not info_jog.empty:
                    r = info_jog.iloc[0]
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Vmáx Record", f"{r['Vmáx Record (km/h)']} km/h")
                    k2.metric("Limiar 90%",  f"{r['_lim_90']} km/h")
                    k3.metric("Limiar 95%",  f"{r['_lim_95']} km/h")
                    k4.metric("Alerta",      r["Alerta"])

                # Gráfico histórico Vmáx
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Scatter(
                    x=sub_hist["Data"], y=sub_hist["Vel. Máx (km/h)"],
                    mode="lines+markers", name="Vmáx Sessão",
                    line_color="#e63946", line_width=2, marker_size=7,
                ))
                fig_hist.add_hline(y=vmax_rec, line_dash="solid",  line_color="#f39c12", line_width=2,
                                    annotation_text=f"Recorde {vmax_rec:.1f} km/h", annotation_position="top left")
                fig_hist.add_hline(y=lim_95,   line_dash="dash",   line_color="#2ecc71",
                                    annotation_text=f"≥95% ({lim_95:.1f})", annotation_position="bottom right")
                fig_hist.add_hline(y=lim_90,   line_dash="dash",   line_color="#f39c12",
                                    annotation_text=f"≥90% ({lim_90:.1f})", annotation_position="bottom right")
                fig_hist.add_hline(y=lim_85,   line_dash="dot",    line_color="#3498db",
                                    annotation_text=f"≥85% ({lim_85:.1f})", annotation_position="bottom right")

                # Colorir pontos por zona
                cores_pts = []
                for v in sub_hist["Vel. Máx (km/h)"]:
                    if v >= lim_95:   cores_pts.append("#2ecc71")
                    elif v >= lim_90: cores_pts.append("#f39c12")
                    elif v >= lim_85: cores_pts.append("#3498db")
                    else:             cores_pts.append("#e74c3c")
                fig_hist.update_traces(marker_color=cores_pts, selector=dict(name="Vmáx Sessão"))

                fig_hist.update_layout(
                    height=400,
                    yaxis_title="Vel. Máx (km/h)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                    showlegend=False,
                    margin=dict(t=20),
                )
                st.plotly_chart(fig_hist, use_container_width=True)

                # Gráfico % do Recorde ao longo do tempo
                st.markdown('<p class="section-title">% do Recorde por Sessão</p>', unsafe_allow_html=True)
                fig_pct_hist = go.Figure()
                fig_pct_hist.add_trace(go.Bar(
                    x=sub_hist["Data"], y=sub_hist["% Record"],
                    marker_color=[
                        "#2ecc71" if v >= 95 else "#f39c12" if v >= 90 else "#3498db" if v >= 85 else "#e74c3c"
                        for v in sub_hist["% Record"]
                    ],
                    text=sub_hist["% Record"].astype(str) + "%",
                    textposition="outside",
                ))
                fig_pct_hist.add_hline(y=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
                fig_pct_hist.add_hline(y=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
                fig_pct_hist.update_layout(
                    yaxis=dict(title="% do Recorde", range=[60, 108]),
                    height=320,
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10),
                )
                st.plotly_chart(fig_pct_hist, use_container_width=True)

                # Exposição por zonas — Nº sprints ≥85/90/95%
                cols_sprints = ["Nº ≥85% Vmáx", "Nº ≥90% Vmáx", "Nº ≥95% Vmáx"]
                cols_sprints_disp = [c for c in cols_sprints if c in sub_hist.columns]
                if cols_sprints_disp:
                    st.markdown('<p class="section-title">Nº de Ações por Zona de Velocidade</p>', unsafe_allow_html=True)
                    fig_sprints = px.line(sub_hist, x="Data", y=cols_sprints_disp,
                                           markers=True,
                                           color_discrete_map={
                                               "Nº ≥85% Vmáx": "#3498db",
                                               "Nº ≥90% Vmáx": "#f39c12",
                                               "Nº ≥95% Vmáx": "#e74c3c",
                                           })
                    fig_sprints.update_layout(
                        height=300,
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)",
                        legend_title="Zona",
                        margin=dict(t=10),
                    )
                    st.plotly_chart(fig_sprints, use_container_width=True)

                # Tabela de dados brutos
                with st.expander("📋 Ver histórico completo de Vmáx"):
                    colunas_hist = ["Data", "Microciclo (Nr)", "Dia MD", "Vel. Máx (km/h)", "% Record"] + cols_sprints_disp
                    colunas_hist_disp = [c for c in colunas_hist if c in sub_hist.columns]
                    st.dataframe(sub_hist[colunas_hist_disp].sort_values("Data", ascending=False), use_container_width=True)

            # ── Conclusões Vmáx ───────────────────────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões — Vmáx Monitor</p>', unsafe_allow_html=True)

            if not df_vmax.empty:
                criticos = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce") > 7]["Jogador"].tolist()
                atencao_v = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce").between(4, 7)]["Jogador"].tolist()
                baixo_pct = df_vmax[df_vmax["% do Recorde"] < 90]["Jogador"].tolist()

                if criticos:
                    st.markdown(f"🔴 **Risco de desadaptação neural** — {', '.join(criticos)}: mais de 7 dias sem atingir ≥90% do recorde. Expor a estímulos de alta velocidade com urgência.")
                if atencao_v:
                    st.markdown(f"🟡 **Monitorizar** — {', '.join(atencao_v)}: entre 4-7 dias sem ≥90% Vmáx.")
                if baixo_pct:
                    st.markdown(f"📉 **Abaixo de 90% do recorde** na última sessão — {', '.join(baixo_pct)}. Verificar se é recuperação intencional ou sinal de fadiga.")
                if not criticos and not atencao_v:
                    st.markdown("🟢 **Toda a equipa em dia** com exposição a alta velocidade (<7 dias).")

                melhor = df_vmax.loc[df_vmax["Vmáx Record (km/h)"].idxmax()]
                st.markdown(f"⚡ **Jogador mais rápido**: {melhor['Jogador']} com recorde de **{melhor['Vmáx Record (km/h)']} km/h**.")



    if _eq_idx == 3:

            METS_COMP = get_mets_gps(df)
            mets_comp_disp = [m for m in METS_COMP if m in df.columns]

            mcs_todos = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
            if len(mcs_todos) < 2:
                st.warning("Precisas de pelo menos 2 microciclos para comparar.")
                return

            col_mc1, col_mc2, col_mc3 = st.columns(3)
            mc_A = col_mc1.selectbox("Microciclo A", mcs_todos, index=0, key="comp_mcA")
            mc_B = col_mc2.selectbox("Microciclo B", mcs_todos, index=1, key="comp_mcB")
            nivel_comp = col_mc3.radio("Nível", ["Equipa", "Jogador"], horizontal=True, key="comp_nivel")

            if mc_A == mc_B:
                st.warning("Seleciona dois microciclos diferentes.")

            df_A = df[df["Microciclo (Nr)"] == mc_A]
            df_B = df[df["Microciclo (Nr)"] == mc_B]

            st.divider()

            if nivel_comp == "Equipa":
                # ── KPIs lado a lado ──────────────────────────────────────────────────
                st.markdown('<p class="section-title">📊 Médias da Equipa — Lado a Lado</p>', unsafe_allow_html=True)

                # Chunked em linhas de 6 colunas para evitar truncar labels/valores
                _PER_ROW = 6
                _idx_global = 0
                for _row_start in range(0, len(mets_comp_disp), _PER_ROW):
                    _row_mets = mets_comp_disp[_row_start:_row_start + _PER_ROW]
                    cols_comp = st.columns(_PER_ROW)
                    for _j, met in enumerate(_row_mets):
                        val_A = df_A[met].mean()
                        val_B = df_B[met].mean()
                        if pd.isna(val_A) and pd.isna(val_B):
                            continue
                        delta = ((val_A - val_B) / abs(val_B) * 100) if (not pd.isna(val_B) and val_B != 0) else None
                        delta_str = f"{delta:+.1f}% vs MC {int(mc_B)}" if delta is not None else None
                        label = met.replace("Distância Total","Dist.").replace(" (m)","").replace(" (n)","").replace(" (km/h)","").replace("Velocidade Máxima","Vel.Máx").replace("PSE Sessão","PSE").replace("Carga Interna","CI").replace("Hooper Index","Hooper")
                        cols_comp[_j].metric(
                            f"{label} (MC {int(mc_A)})",
                            f"{val_A:,.1f}" if not pd.isna(val_A) else "—",
                            delta=delta_str,
                            help=f"MC {int(mc_A)}: {val_A:,.1f} | MC {int(mc_B)}: {val_B:,.1f}"
                        )

                st.divider()

                # ── Gráfico barras agrupadas ───────────────────────────────────────────
                st.markdown('<p class="section-title">📊 Comparação Visual — Todas as Métricas</p>', unsafe_allow_html=True)

                comp_rows = []
                for met in mets_comp_disp:
                    val_A = df_A[met].mean()
                    val_B = df_B[met].mean()
                    if pd.isna(val_A) and pd.isna(val_B): continue
                    comp_rows.append({"Métrica": met.split("(")[0].strip(),
                                       f"MC {int(mc_A)}": round(val_A, 1) if not pd.isna(val_A) else 0,
                                       f"MC {int(mc_B)}": round(val_B, 1) if not pd.isna(val_B) else 0})

                if comp_rows:
                    df_comp = pd.DataFrame(comp_rows)
                    fig_comp = go.Figure()
                    fig_comp.add_trace(go.Bar(
                        name=f"MC {int(mc_A)}", x=df_comp["Métrica"],
                        y=df_comp[f"MC {int(mc_A)}"],
                        marker_color="#e63946", text=df_comp[f"MC {int(mc_A)}"].round(1),
                        textposition="outside",
                    ))
                    fig_comp.add_trace(go.Bar(
                        name=f"MC {int(mc_B)}", x=df_comp["Métrica"],
                        y=df_comp[f"MC {int(mc_B)}"],
                        marker_color="#457b9d", text=df_comp[f"MC {int(mc_B)}"].round(1),
                        textposition="outside",
                    ))
                    fig_comp.update_layout(
                        barmode="group", height=420,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                        legend=dict(orientation="h", y=1.05),
                    )
                    st.plotly_chart(fig_comp, use_container_width=True)

                st.divider()

                # ── Radar comparativo ──────────────────────────────────────────────────
                st.markdown('<p class="section-title">📡 Radar Comparativo</p>', unsafe_allow_html=True)
                mets_radar = [m for m in get_mets_gps(df_f)[:6] if m in df.columns]
                if len(mets_radar) >= 3:
                    max_vals = {m: df[m].replace(0, np.nan).max() for m in mets_radar if m in df.columns and df[m].notna().any()}
                    vals_A = [df_A[m].mean() / max_vals[m] * 100 if max_vals[m] > 0 else 0 for m in mets_radar]
                    vals_B = [df_B[m].mean() / max_vals[m] * 100 if max_vals[m] > 0 else 0 for m in mets_radar]
                    labs   = [m.split("(")[0].strip() for m in mets_radar]

                    fig_radar_comp = go.Figure()
                    fig_radar_comp.add_trace(go.Scatterpolar(
                        r=vals_A + [vals_A[0]], theta=labs + [labs[0]],
                        fill="toself", name=f"MC {int(mc_A)}", line_color="#e63946", opacity=0.8,
                    ))
                    fig_radar_comp.add_trace(go.Scatterpolar(
                        r=vals_B + [vals_B[0]], theta=labs + [labs[0]],
                        fill="toself", name=f"MC {int(mc_B)}", line_color="#457b9d", opacity=0.8,
                    ))
                    fig_radar_comp.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0,100], ticksuffix="%")),
                        height=440, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_comp, use_container_width=True)

                # ── Dia MD comparativo ─────────────────────────────────────────────────
                if "Dia MD" in df.columns:
                    st.divider()
                    st.markdown('<p class="section-title">📅 Por Dia MD — Comparação</p>', unsafe_allow_html=True)
                    met_dia_comp = st.selectbox("Métrica", mets_comp_disp, key="comp_dia_met")
                    dias_ordem = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1","MD+2"]

                    rows_dias = []
                    for dia in dias_ordem:
                        vA = df_A[df_A["Dia MD"] == dia][met_dia_comp].mean()
                        vB = df_B[df_B["Dia MD"] == dia][met_dia_comp].mean()
                        if pd.isna(vA) and pd.isna(vB): continue
                        rows_dias.append({"Dia MD": dia, f"MC {int(mc_A)}": round(vA,1) if not pd.isna(vA) else 0,
                                           f"MC {int(mc_B)}": round(vB,1) if not pd.isna(vB) else 0})

                    if rows_dias:
                        df_dias_comp = pd.DataFrame(rows_dias)
                        fig_dias_comp = go.Figure()
                        fig_dias_comp.add_trace(go.Scatter(
                            x=df_dias_comp["Dia MD"], y=df_dias_comp[f"MC {int(mc_A)}"],
                            mode="lines+markers", name=f"MC {int(mc_A)}",
                            line_color="#e63946", line_width=3, marker_size=10,
                        ))
                        fig_dias_comp.add_trace(go.Scatter(
                            x=df_dias_comp["Dia MD"], y=df_dias_comp[f"MC {int(mc_B)}"],
                            mode="lines+markers", name=f"MC {int(mc_B)}",
                            line_color="#457b9d", line_width=3, marker_size=10,
                        ))
                        fig_dias_comp.update_layout(
                            height=360, yaxis_title=met_dia_comp,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                        )
                        st.plotly_chart(fig_dias_comp, use_container_width=True)

            else:  # Nível Jogador
                jog_comp = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="comp_jog")
                df_A_jog = df_A[df_A["Jogador"] == jog_comp]
                df_B_jog = df_B[df_B["Jogador"] == jog_comp]

                st.markdown(f'<p class="section-title">📊 {jog_comp} — MC {int(mc_A)} vs MC {int(mc_B)}</p>', unsafe_allow_html=True)

                # Chunked em linhas de 6 colunas
                _PER_ROW = 6
                for _row_start in range(0, len(mets_comp_disp), _PER_ROW):
                    _row_mets = mets_comp_disp[_row_start:_row_start + _PER_ROW]
                    cols_j = st.columns(_PER_ROW)
                    for _j, met in enumerate(_row_mets):
                        vA = df_A_jog[met].mean()
                        vB = df_B_jog[met].mean()
                        if pd.isna(vA) and pd.isna(vB): continue
                        delta = ((vA - vB) / abs(vB) * 100) if (not pd.isna(vB) and vB != 0) else None
                        label = met.split("(")[0].strip()
                        cols_j[_j].metric(
                            f"{label}",
                            f"{vA:,.1f}" if not pd.isna(vA) else "—",
                            delta=f"{delta:+.1f}% vs MC {int(mc_B)}" if delta else None,
                        )

                # Scatter comparativo jogador
                if len(mets_comp_disp) >= 2:
                    st.divider()
                    sc_j1, sc_j2 = st.columns(2)
                    x_cj = sc_j1.selectbox("Eixo X", mets_comp_disp, index=0, key="comp_jog_x")
                    y_cj = sc_j2.selectbox("Eixo Y", mets_comp_disp, index=1, key="comp_jog_y")

                    df_jog_todos = df[df["Jogador"] == jog_comp].dropna(subset=[x_cj, y_cj])
                    if not df_jog_todos.empty:
                        fig_ev_jog = go.Figure()
                        fig_ev_jog.add_trace(go.Scatter(
                            x=df_jog_todos[x_cj], y=df_jog_todos[y_cj],
                            mode="markers", name="Todas as sessões",
                            marker=dict(size=10, color="#457b9d", opacity=0.5),
                        ))
                        for mc_c, cor_c, nome_c in [(mc_A, "#e63946", f"MC {int(mc_A)}"), (mc_B, "#f39c12", f"MC {int(mc_B)}")]:
                            sub_mc = df_jog_todos[df_jog_todos["Microciclo (Nr)"] == mc_c]
                            if not sub_mc.empty:
                                fig_ev_jog.add_trace(go.Scatter(
                                    x=[sub_mc[x_cj].mean()], y=[sub_mc[y_cj].mean()],
                                    mode="markers+text", text=[nome_c],
                                    textposition="top center",
                                    marker=dict(size=22, color=cor_c, line=dict(width=2, color="white")),
                                    name=nome_c,
                                ))
                        fig_ev_jog.update_layout(
                            height=420, xaxis_title=x_cj, yaxis_title=y_cj,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                        )
                        st.plotly_chart(fig_ev_jog, use_container_width=True)



    if _eq_idx == 4:
        st.info("**Foster (1998):** Monotonia = CI média/DP. Strain = CI total × Monotonia. Monotonia>2.0 = variação insuficiente. Strain elevado + Monotonia alta = risco aumentado.")
        df_f = df_f_dia
        st.markdown("""
        > **Monotonia** mede se o treino é sempre igual — treinos muito repetitivos são prejudiciais mesmo com carga baixa.  
        > **Strain** combina a carga total com a monotonia — semanas intensas *e* monótonas são as mais arriscadas.
        """)

        LIMIAR_MONO = 2.0
        LIMIAR_MONO_ATENCAO = 1.5

        def calcular_mono_strain(df_base: pd.DataFrame):
            rows = []
            for jog in sorted(df_base["Jogador"].dropna().unique()):
                sub = df_base[df_base["Jogador"] == jog].dropna(subset=["Microciclo (Nr)", "Carga Interna"])
                for mc in sub["Microciclo (Nr)"].unique():
                    mc_sub = sub[sub["Microciclo (Nr)"] == mc]["Carga Interna"]
                    if len(mc_sub) < 2: continue
                    media = mc_sub.mean()
                    dp    = mc_sub.std()
                    total = mc_sub.sum()
                    mono  = media / dp if dp > 0 else 0
                    strain = total * mono
                    pos = df_base[df_base["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df_base.columns else "—"

                    if mono > LIMIAR_MONO:         estado_m, cor_m = "🔴 Excessiva",   "#e74c3c"
                    elif mono > LIMIAR_MONO_ATENCAO: estado_m, cor_m = "🟡 Atenção",    "#f39c12"
                    else:                            estado_m, cor_m = "🟢 Boa variação","#2ecc71"

                    rows.append({
                        "Jogador": jog, "Posição": pos, "Microciclo": int(mc),
                        "Carga Total": round(total, 0),
                        "Média Diária": round(media, 1),
                        "DP": round(dp, 1),
                        "Monotonia": round(mono, 2),
                        "Strain": round(strain, 0),
                        "Estado": estado_m,
                        "_cor": cor_m,
                    })
            return pd.DataFrame(rows)

        df_ms = calcular_mono_strain(df_f)

        if df_ms.empty:
            st.warning("Dados insuficientes para calcular Monotonia & Strain. Necessário pelo menos 2 sessões por microciclo.")

        tab_ms1, tab_ms2 = st.tabs(["🏟️ Vista de Equipa", "👤 Jogador Individual"])

        with tab_ms1:
            mc_ms = st.selectbox("Microciclo", sorted(df_ms["Microciclo"].unique(), reverse=True), key="ms_mc")
            df_ms_mc = df_ms[df_ms["Microciclo"] == mc_ms]

            # KPIs
            k1,k2,k3 = st.columns(3)
            k1.metric("Monotonia Média", f"{df_ms_mc['Monotonia'].mean():.2f}",
                      help="Ideal: <1.5 | Atenção: 1.5–2.0 | Excessivo: >2.0")
            k2.metric("Strain Médio",    f"{df_ms_mc['Strain'].mean():,.0f}",
                      help="Carga Total × Monotonia. Quanto maior, maior o risco acumulado.")
            k3.metric("Jogadores em risco de monotonia", f"{len(df_ms_mc[df_ms_mc['Monotonia'] > LIMIAR_MONO])}")

            st.divider()

            # Monotonia por jogador
            st.markdown('<p class="section-title">Monotonia por Jogador</p>', unsafe_allow_html=True)
            df_ms_sorted = df_ms_mc.sort_values("Monotonia", ascending=False)
            fig_mono = go.Figure(go.Bar(
                x=df_ms_sorted["Jogador"], y=df_ms_sorted["Monotonia"],
                marker_color=df_ms_sorted["_cor"].tolist(),
                text=df_ms_sorted["Monotonia"].round(2), textposition="outside",
            ))
            fig_mono.add_hline(y=LIMIAR_MONO,        line_dash="dash", line_color="#e74c3c",  annotation_text="Excessiva (2.0)")
            fig_mono.add_hline(y=LIMIAR_MONO_ATENCAO, line_dash="dot",  line_color="#f39c12", annotation_text="Atenção (1.5)")
            fig_mono.update_layout(
                yaxis_title="Monotonia", height=380,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
            )
            st.plotly_chart(fig_mono, use_container_width=True)

            # Scatter Strain vs Carga Total
            st.markdown('<p class="section-title">Strain vs Carga Total — Quadrantes de Risco</p>', unsafe_allow_html=True)
            st.caption("Ideal: carga alta com baixa monotonia (quadrante inferior direito)")

            if len(df_ms_mc) >= 2 and df_ms_mc["Carga Total"].nunique() > 1:
                fig_scatter = px.scatter(
                    df_ms_mc, x="Carga Total", y="Monotonia",
                    text="Jogador", color="Estado",
                    color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
                    size="Strain", size_max=40,
                    hover_data=["Strain", "Média Diária", "DP"],
                )
            else:
                fig_scatter = px.scatter(
                    df_ms_mc, x="Carga Total", y="Monotonia",
                    text="Jogador", color="Estado",
                    color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
                )
            fig_scatter.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c")
            fig_scatter.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12")
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(
                height=420, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            # Tabela
            st.dataframe(
                df_ms_mc[["Jogador","Posição","Carga Total","Média Diária","DP","Monotonia","Strain","Estado"]]
                .set_index("Jogador"), use_container_width=True
            )

            # Conclusões
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)
            risco_mono  = df_ms_mc[df_ms_mc["Monotonia"] > LIMIAR_MONO]["Jogador"].tolist()
            atenc_mono  = df_ms_mc[df_ms_mc["Monotonia"].between(LIMIAR_MONO_ATENCAO, LIMIAR_MONO)]["Jogador"].tolist()
            strain_top  = df_ms_mc.nlargest(3, "Strain")[["Jogador","Strain"]].values.tolist()

            if risco_mono:
                st.markdown(f"🔴 **Monotonia excessiva** (>2.0): {', '.join(risco_mono)} — variar a estrutura das sessões com urgência (intensidade, volume, tipo de exercício).")
            if atenc_mono:
                st.markdown(f"🟡 **Atenção à monotonia** (1.5–2.0): {', '.join(atenc_mono)} — introduzir mais variação nos próximos dias.")
            if not risco_mono and not atenc_mono:
                st.markdown("🟢 **Toda a equipa com boa variação de carga** neste microciclo.")
            ranking_top_list("💥", "Top 3 Strain — Microciclo", "#8b5cf6",
                              [(jog_s, strain_s) for jog_s, strain_s in strain_top], " UA")

        with tab_ms2:
            jog_ms = st.selectbox("Jogador", sorted(df_ms["Jogador"].unique()), key="ms_jog")
            df_ms_jog = df_ms[df_ms["Jogador"] == jog_ms].sort_values("Microciclo")

            fig_ms_ev = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       subplot_titles=["Monotonia", "Strain"],
                                       vertical_spacing=0.12)
            fig_ms_ev.add_trace(go.Scatter(
                x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Monotonia"],
                mode="lines+markers+text", text=df_ms_jog["Monotonia"].round(2),
                textposition="top center", line_color="#e63946", name="Monotonia",
            ), row=1, col=1)
            fig_ms_ev.add_trace(go.Bar(
                x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Strain"],
                marker_color="#457b9d", name="Strain",
            ), row=2, col=1)
            fig_ms_ev.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c",  row=1, col=1)
            fig_ms_ev.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12", row=1, col=1)
            fig_ms_ev.update_layout(
                height=480, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                showlegend=False, margin=dict(t=30),
                xaxis2_title="Microciclo",
            )
            st.plotly_chart(fig_ms_ev, use_container_width=True)

            # Detalhe das sessões do microciclo selecionado
            mc_ms_jog = st.selectbox("Ver detalhe do Microciclo", sorted(df_ms_jog["Microciclo"].unique(), reverse=True), key="ms_jog_mc")
            sessoes_mc = df_f[(df_f["Jogador"] == jog_ms) & (df_f["Microciclo (Nr)"] == mc_ms_jog) & (df_f["Carga Interna"].notna())]
            if not sessoes_mc.empty:
                fig_sess = go.Figure(go.Bar(
                    x=sessoes_mc["Dia MD"] if "Dia MD" in sessoes_mc.columns else sessoes_mc["Data"].dt.strftime("%d/%m"),
                    y=sessoes_mc["Carga Interna"],
                    marker_color="#e63946",
                    text=sessoes_mc["Carga Interna"].round(0), textposition="outside",
                ))
                fig_sess.add_hline(
                    y=sessoes_mc["Carga Interna"].mean(),
                    line_dash="dash", line_color="white",
                    annotation_text=f"Média: {sessoes_mc['Carga Interna'].mean():.0f}",
                )
                fig_sess.update_layout(
                    yaxis_title="Carga Interna (UA)", height=300,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                )
                st.plotly_chart(fig_sess, use_container_width=True)

