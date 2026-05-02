"""LoadMonitorSystem — Página Jogadores"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.dados import get_mets_gps, carregar_exercicios, COL_ALIASES
from utils.calculos import calcular_acwr, calcular_acwr_global, zscore_serie, cor_acwr, calcular_monotonia_strain
from utils.ui import lm_header, premium_layout, botao_download_html, gerar_pdf_html, metric_card, sem_dados_suficientes

def render(df, excel_path, **kwargs):
    _lm_user = kwargs.get("lm_user", {})
    _lm_plano = _lm_user.get("plano", "free")
    _lm_nome = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")
    lm_header("Jogadores", "Análise individual — perfil, historial e performance por jogador", "Jogadores")
    tab_jog = st.tabs(["👤 Individual", "📏 Perfil de Referência"])

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
    validar_dados = H.get("validar_dados", lambda d: ([], [], []))

    with tab_jog[0]:
        df_f = df_f_dia

        df_jog = df[df["Jogador"] == jogador_sel].sort_values("Data")
        df_jog_f = df_f[df_f["Jogador"] == jogador_sel].sort_values("Data")

        if df_jog_f.empty:
            st.warning("Sem dados para este jogador nos filtros selecionados.")

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sessões",          f"{len(df_jog_f)}")
        c2.metric("Dist. Média (m)",  f"{df_jog_f['Distância Total (m)'].mean():,.0f}")
        c3.metric("PSE Média",        f"{df_jog_f['PSE Sessão'].mean():.1f}")
        c4.metric("CI Médio",         f"{df_jog_f['Carga Interna'].mean():,.0f}")

        st.divider()

        # ACWR ao longo do tempo
        st.markdown('<p class="section-title">📉 ACWR ao Longo do Tempo</p>', unsafe_allow_html=True)
        df_acwr_jog = calcular_acwr(df_jog, jogador_sel)
        if "ACWR" in df_acwr_jog.columns:
            fig_acwr_t = go.Figure()
            fig_acwr_t.add_trace(go.Scatter(x=df_acwr_jog["Data"], y=df_acwr_jog["ACWR"],
                                             mode="lines+markers", name="ACWR", line_color="#e63946"))
            fig_acwr_t.add_hrect(y0=0.8, y1=1.3, fillcolor="green",   opacity=0.08, line_width=0)
            fig_acwr_t.add_hrect(y0=1.3, y1=1.5, fillcolor="orange",  opacity=0.1,  line_width=0)
            fig_acwr_t.add_hrect(y0=1.5, y1=3.0, fillcolor="red",     opacity=0.1,  line_width=0)
            fig_acwr_t.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c", annotation_text="1.5")
            fig_acwr_t.add_hline(y=0.8, line_dash="dash", line_color="#3498db", annotation_text="0.8")
            fig_acwr_t.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                       paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                       yaxis_title="ACWR", margin=dict(t=10))
            st.plotly_chart(fig_acwr_t, use_container_width=True)

        # Carga Interna por sessão
        st.divider()
        st.markdown('<p class="section-title">⚡ Carga Interna por Sessão</p>', unsafe_allow_html=True)
        fig_ci_j = px.bar(df_jog_f, x="Data", y="Carga Interna",
                           color="Dia MD" if "Dia MD" in df_jog_f.columns else None,
                           labels={"Carga Interna": "CI", "Data": "Data"})
        fig_ci_j.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                 paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
        st.plotly_chart(fig_ci_j, use_container_width=True)

        # GPS ao longo do tempo
        st.divider()
        st.markdown('<p class="section-title">🏃 Evolução GPS</p>', unsafe_allow_html=True)
        metricas_gps = get_mets_gps(df_jog)
        metricas_gps_disp = [m for m in metricas_gps if m in df_jog_f.columns]

        fig_gps_j = make_subplots(rows=2, cols=2,
                                   subplot_titles=metricas_gps_disp,
                                   vertical_spacing=0.18, horizontal_spacing=0.1)
        posicoes_grid = [(1,1),(1,2),(2,1),(2,2)]
        cores_gps = ["#e63946","#457b9d","#2ecc71","#f39c12"]

        for i, met in enumerate(metricas_gps_disp[:4]):
            r, c = posicoes_grid[i]
            fig_gps_j.add_trace(
                go.Scatter(x=df_jog_f["Data"], y=df_jog_f[met],
                           mode="lines+markers", name=met,
                           line_color=cores_gps[i], showlegend=False),
                row=r, col=c
            )

        fig_gps_j.update_layout(height=460, plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=30))
        st.plotly_chart(fig_gps_j, use_container_width=True)

        # Wellness
        st.divider()
        st.markdown('<p class="section-title">💤 Wellness (Hooper Index)</p>', unsafe_allow_html=True)
        w_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
        w_disp = [c for c in w_cols if c in df_jog_f.columns]
        if w_disp:
            fig_w_j = px.line(df_jog_f, x="Data", y=w_disp, markers=True)
            fig_w_j.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                   legend_title="", margin=dict(t=10))
            st.plotly_chart(fig_w_j, use_container_width=True)

        # Tabela de dados brutos
        st.divider()
        with st.expander("📋 Ver todos os registos"):
            st.dataframe(df_jog_f.sort_values("Data", ascending=False), use_container_width=True)

        # Conclusões individuais
        st.divider()
        st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)

        df_acwr_all = calcular_acwr(df_jog, jogador_sel)
        if "ACWR" in df_acwr_all.columns and df_acwr_all["ACWR"].notna().any():
            acwr_last = df_acwr_all.dropna(subset=["ACWR"]).iloc[-1]["ACWR"]
            estado = cor_acwr(acwr_last)
            st.markdown(f"- **Último ACWR**: `{acwr_last:.2f}` → {estado}")

        if "Hooper Index" in df_jog_f.columns:
            h = df_jog_f["Hooper Index"].mean()
            if h >= 14:
                st.markdown(f"- 😟 **Hooper Index elevado** ({h:.1f}) — possível acumulação de stress/fadiga.")
            elif h <= 8:
                st.markdown(f"- 😃 **Hooper Index excelente** ({h:.1f}) — jogador em ótimo estado.")
            else:
                st.markdown(f"- 😐 **Hooper Index normal** ({h:.1f}).")

        if "Vel. Máx (km/h)" in df_jog_f.columns:
            vmax = df_jog_f["Vel. Máx (km/h)"].max()
            vmax_mean = df_jog_f["Vel. Máx (km/h)"].mean()
            st.markdown(f"- **Velocidade máxima registada**: {vmax:.1f} km/h (média: {vmax_mean:.1f} km/h).")

        # ── Conclusões automáticas ────────────────────────────────────────────────
        st.divider()
        st.markdown('<p class="section-title">🧠 Análise Automática</p>', unsafe_allow_html=True)

        conclusoes_jog = []

        # ACWR
        df_acwr_jog = calcular_acwr(df, jogador_sel)
        if not df_acwr_jog.empty and "ACWR" in df_acwr_jog.columns and df_acwr_jog["ACWR"].notna().any():
            av = df_acwr_jog["ACWR"].dropna().iloc[-1]
            if av > 1.5:    conclusoes_jog.append(("#e74c3c", f"🔴 ACWR elevado ({av:.2f}) — carga aguda muito superior à crónica. Reduzir volume e intensidade nos próximos treinos."))
            elif av > 1.3:  conclusoes_jog.append(("#f39c12", f"🟡 ACWR em zona de atenção ({av:.2f}) — monitorizar nas próximas 48h."))
            elif av < 0.8:  conclusoes_jog.append(("#3498db", f"🔵 ACWR baixo ({av:.2f}) — sub-estimulação crónica. Considerar aumentar a carga progressivamente."))
            else:            conclusoes_jog.append(("#2ecc71", f"🟢 ACWR dentro da zona segura ({av:.2f}) — continuar o plano atual."))

        # Hooper Index
        if "Hooper Index" in df_jog_f.columns and df_jog_f["Hooper Index"].notna().any():
            hi = df_jog_f["Hooper Index"].dropna()
            hi_last = hi.iloc[-1]; hi_media = hi.mean()
            trend = "a melhorar ↓" if hi.diff().mean() < -0.5 else "a piorar ↑" if hi.diff().mean() > 0.5 else "estável"
            if hi_last >= 14:   conclusoes_jog.append(("#e74c3c", f"🔴 Hooper elevado ({hi_last:.0f}/16) — má recuperação. Avaliar contexto extra-desportivo."))
            elif hi_last >= 10: conclusoes_jog.append(("#f39c12", f"🟡 Hooper moderado ({hi_last:.0f}/16) — tendência {trend}. Média histórica: {hi_media:.1f}."))
            else:                conclusoes_jog.append(("#2ecc71", f"🟢 Hooper baixo ({hi_last:.0f}/16) — boa recuperação. Média histórica: {hi_media:.1f}."))

        # Carga Interna vs histórico
        if "Carga Interna" in df_jog_f.columns and df_jog_f["Carga Interna"].notna().any():
            ci_h = df_jog_f["Carga Interna"].dropna()
            if len(ci_h) >= 3:
                ci_last = ci_h.iloc[-1]; ci_med = ci_h.mean()
                diff_p = (ci_last - ci_med) / ci_med * 100 if ci_med > 0 else 0
                conclusoes_jog.append(("#9b59b6", f"📊 Última sessão: {ci_last:.0f} UA ({diff_p:+.0f}% vs média histórica de {ci_med:.0f} UA)."))

        # Vmáx exposição
        if "Vel. Máx (km/h)" in df_jog_f.columns and df_jog_f["Vel. Máx (km/h)"].notna().any():
            vmax_rec = df_jog_f["Vel. Máx (km/h)"].max()
            vmax_90 = vmax_rec * 0.90
            acima_90 = df_jog_f[df_jog_f["Vel. Máx (km/h)"] >= vmax_90].sort_values("Data")
            if acima_90.empty:
                conclusoes_jog.append(("#e74c3c", f"🔴 Sem registo de exposição a ≥90% Vmáx (recorde: {vmax_rec:.1f} km/h). Incluir exercícios de sprint."))
            else:
                dias_v = int((df_jog_f["Data"].max() - acima_90["Data"].max()).days) if "Data" in df_jog_f.columns else 0
                if dias_v > 7:    conclusoes_jog.append(("#e74c3c", f"🔴 Sem sprint ≥90% Vmáx há {dias_v} dias. Recorde: {vmax_rec:.1f} km/h."))
                elif dias_v >= 5: conclusoes_jog.append(("#f39c12", f"🟡 Última exposição a alta velocidade há {dias_v} dias."))
                else:              conclusoes_jog.append(("#2ecc71", f"🟢 Exposição recente a alta velocidade (≥{vmax_90:.1f} km/h há {dias_v} dias)."))

        if not conclusoes_jog:
            st.info("Sem dados suficientes para análise automática.")
        else:
            for cor_c, texto in conclusoes_jog:
                st.markdown(
                    f'<div style="border-left:3px solid {cor_c};padding:10px 16px;margin:4px 0;'
                    f'background:{cor_c}15;border-radius:0 8px 8px 0;font-size:0.85rem;line-height:1.5">{texto}</div>',
                    unsafe_allow_html=True
                )

        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: COMPARAÇÃO POR POSIÇÃO
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_jog[1]:

        METS_PERFIL_DEFAULT = [
            "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
            "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
            "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
        ]
        _mp = st.session_state.get("lm_helpers", {}).get("metricas_personalizaveis")
        if _mp:
            mets_disp = _mp(df, METS_PERFIL_DEFAULT, "jogadores_perfil", "Personalizar métricas — Perfil")
        else:
            mets_disp = [m for m in METS_PERFIL_DEFAULT if m in df.columns]

        tab_p1, tab_p2 = st.tabs(["👤 Análise Individual", "🏟️ Semáforo da Equipa"])

        # ── TAB 1: Individual ────────────────────────────────────────────────────
        with tab_p1:
            col_a, col_b = st.columns(2)
            jog_p = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="perf_jog")
            n_semanas = col_b.slider("Semanas de histórico como referência", 4, 20, 8, key="perf_sem")

            df_jog_p = df[df["Jogador"] == jog_p].dropna(subset=["Data"]).sort_values("Data").copy()
            if df_jog_p.empty:
                st.warning("Sem dados para este jogador.")

            # Referência = primeiras n_semanas × 7 dias de dados
            data_corte = df_jog_p["Data"].min() + pd.Timedelta(weeks=n_semanas)
            df_ref  = df_jog_p[df_jog_p["Data"] <= data_corte]
            df_recente = df_jog_p[df_jog_p["Data"] > data_corte]

            if df_ref.empty or df_recente.empty:
                st.warning("Histórico insuficiente. Tenta reduzir o número de semanas de referência.")
            else:
                st.info(f"📐 Referência baseada em **{len(df_ref)} sessões** ({df_ref['Data'].min().strftime('%d/%m/%y')} – {df_ref['Data'].max().strftime('%d/%m/%y')})")

                # Calcular perfil de referência
                perfil_rows = []
                for met in mets_disp:
                    if df_ref[met].notna().sum() < 3:
                        continue
                    mu  = df_ref[met].mean()
                    sig = df_ref[met].std()
                    ult = df_recente[met].dropna()
                    if ult.empty: continue
                    ult_val = ult.iloc[-1]
                    z = (ult_val - mu) / sig if sig > 0 else 0
                    if z > 2:    estado = "🔴 Muito Acima"; cor = "#e74c3c"
                    elif z > 1:  estado = "🟡 Acima";       cor = "#f39c12"
                    elif z >= -1: estado = "🟢 Normal";      cor = "#2ecc71"
                    elif z >= -2: estado = "🔵 Abaixo";      cor = "#3498db"
                    else:         estado = "🟣 Muito Abaixo"; cor = "#9b59b6"
                    perfil_rows.append({
                        "Métrica": met,
                        "Ref. Média": round(mu, 1),
                        "Ref. ±DP": round(sig, 1),
                        "Último Valor": round(ult_val, 1),
                        "Z-Score": round(z, 2),
                        "Estado": estado,
                        "_cor": cor,
                    })

                if perfil_rows:
                    df_perf = pd.DataFrame(perfil_rows)

                    # Cards de semáforo
                    st.markdown('<p class="section-title">Semáforo — Última Sessão vs Perfil Pessoal</p>', unsafe_allow_html=True)
                    n_cols = 4
                    cols_p = st.columns(n_cols)
                    for i, row in df_perf.iterrows():
                        cols_p[i % n_cols].markdown(
                            f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                            f'padding:10px;text-align:center;margin:4px">'
                            f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{row["Métrica"]}</div>'
                            f'<div style="font-size:1.4rem;font-weight:900;color:{row["_cor"]}">{row["Último Valor"]}</div>'
                            f'<div style="font-size:0.7rem;color:#aaa">Ref: {row["Ref. Média"]} ± {row["Ref. ±DP"]}</div>'
                            f'<div style="font-size:0.85rem;color:{row["_cor"]}">{row["Estado"]} (z={row["Z-Score"]})</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                    st.divider()

                    # Gráfico de barras Z-Score
                    st.markdown('<p class="section-title">Z-Score vs Perfil de Referência</p>', unsafe_allow_html=True)
                    fig_perf = go.Figure(go.Bar(
                        y=df_perf["Métrica"],
                        x=df_perf["Z-Score"],
                        orientation="h",
                        marker_color=df_perf["_cor"].tolist(),
                        text=df_perf["Z-Score"].round(2),
                        textposition="outside",
                    ))
                    fig_perf.add_vline(x=0,  line_color="white", line_width=1)
                    fig_perf.add_vline(x=1,  line_dash="dot", line_color="#f39c12", annotation_text="+1σ")
                    fig_perf.add_vline(x=-1, line_dash="dot", line_color="#3498db", annotation_text="-1σ")
                    fig_perf.add_vline(x=2,  line_dash="dash", line_color="#e74c3c", annotation_text="+2σ")
                    fig_perf.add_vline(x=-2, line_dash="dash", line_color="#9b59b6", annotation_text="-2σ")
                    fig_perf.update_layout(
                        height=max(300, len(df_perf)*50),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", xaxis_title="Z-Score", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_perf, use_container_width=True)

                    # Evolução histórica de uma métrica
                    st.divider()
                    st.markdown('<p class="section-title">Evolução Histórica com Bandas de Referência</p>', unsafe_allow_html=True)
                    met_ev = st.selectbox("Métrica", df_perf["Métrica"].tolist(), key="perf_ev")
                    mu_ev  = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. Média"].iloc[0])
                    sig_ev = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. ±DP"].iloc[0])

                    fig_ev = go.Figure()
                    fig_ev.add_hrect(y0=mu_ev-sig_ev, y1=mu_ev+sig_ev,   fillcolor="#2ecc71", opacity=0.08, line_width=0)
                    fig_ev.add_hrect(y0=mu_ev+sig_ev, y1=mu_ev+2*sig_ev, fillcolor="#f39c12", opacity=0.08, line_width=0)
                    fig_ev.add_hrect(y0=mu_ev-2*sig_ev, y1=mu_ev-sig_ev, fillcolor="#3498db", opacity=0.08, line_width=0)
                    fig_ev.add_trace(go.Scatter(
                        x=df_jog_p["Data"], y=df_jog_p[met_ev],
                        mode="lines+markers", line_color="#e63946", line_width=2, marker_size=6,
                        name=met_ev,
                    ))
                    fig_ev.add_hline(y=mu_ev, line_dash="dash", line_color="white", line_width=1, annotation_text="Média ref.")
                    fig_ev.add_hline(y=mu_ev+sig_ev,   line_dash="dot", line_color="#f39c12")
                    fig_ev.add_hline(y=mu_ev-sig_ev,   line_dash="dot", line_color="#3498db")
                    try:
                        fig_ev.add_vline(x=data_corte.timestamp()*1000, line_dash="dash", line_color="#888",
                                          annotation_text="Fim período ref.")
                    except Exception:
                        pass
                    fig_ev.update_layout(
                        height=360, yaxis_title=met_ev,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                    )
                    st.plotly_chart(fig_ev, use_container_width=True)

                    # Exportar relatório
                    st.divider()
                    linhas_tab = "".join([
                        f'<tr><td>{r["Métrica"]}</td><td>{r["Ref. Média"]} ± {r["Ref. ±DP"]}</td>'
                        f'<td>{r["Último Valor"]}</td><td>{r["Z-Score"]}</td><td>{r["Estado"]}</td></tr>'
                        for _, r in df_perf.iterrows()
                    ])
                    html_perf = gerar_pdf_html(f"""
        <h1>Perfil de Referência — {jog_p}</h1>
        <p>Referência: {df_ref["Data"].min().strftime("%d/%m/%Y")} a {df_ref["Data"].max().strftime("%d/%m/%Y")} ({len(df_ref)} sessões)</p>
        <table><tr><th>Métrica</th><th>Ref. Média ± DP</th><th>Último Valor</th><th>Z-Score</th><th>Estado</th></tr>
        {linhas_tab}</table>
        """, f"Perfil_{jog_p}.html")
                    botao_download_html(html_perf, f"Perfil_{jog_p.replace(' ','_')}.html", f"📥 Exportar Perfil de {jog_p}")

        # ── TAB 2: Semáforo da equipa ─────────────────────────────────────────────
        with tab_p2:
            st.markdown('<p class="section-title">Semáforo de Z-Score Pessoal — Última Sessão vs Perfil Próprio</p>', unsafe_allow_html=True)
            met_eq_p = st.selectbox("Métrica", mets_disp, key="perf_eq_met")
            semanas_ref = st.slider("Semanas de referência", 4, 20, 8, key="perf_eq_sem")

            equipa_perfil = []
            for jog in sorted(df["Jogador"].dropna().unique()):
                df_j = df[df["Jogador"] == jog].dropna(subset=["Data", met_eq_p]).sort_values("Data")
                if len(df_j) < 5: continue
                corte = df_j["Data"].min() + pd.Timedelta(weeks=semanas_ref)
                ref = df_j[df_j["Data"] <= corte][met_eq_p]
                rec = df_j[df_j["Data"] > corte][met_eq_p]
                if ref.empty or rec.empty: continue
                mu, sig = ref.mean(), ref.std()
                if sig == 0: continue
                ult = rec.iloc[-1]
                z = (ult - mu) / sig
                if z > 2:     estado, cor = "🔴 Muito Acima", "#e74c3c"
                elif z > 1:   estado, cor = "🟡 Acima",       "#f39c12"
                elif z >= -1: estado, cor = "🟢 Normal",      "#2ecc71"
                elif z >= -2: estado, cor = "🔵 Abaixo",      "#3498db"
                else:         estado, cor = "🟣 Muito Abaixo","#9b59b6"
                pos = df_j["Posição"].iloc[-1] if "Posição" in df_j.columns else "—"
                equipa_perfil.append({"Jogador": jog, "Posição": pos, "Ref. Média": round(mu,1),
                                       "Último": round(ult,1), "Z-Score": round(z,2),
                                       "Estado": estado, "_cor": cor})

            if equipa_perfil:
                df_ep = pd.DataFrame(equipa_perfil).sort_values("Z-Score", ascending=False)
                cols_sem = st.columns(min(len(df_ep), 5))
                for i, (_, row) in enumerate(df_ep.iterrows()):
                    cols_sem[i % 5].markdown(
                        f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                        f'padding:10px;text-align:center;margin:4px">'
                        f'<b style="font-size:0.9rem">{row["Jogador"]}</b><br>'
                        f'<span style="font-size:0.75rem;color:#aaa">{row["Posição"]}</span><br>'
                        f'<b style="font-size:1.3rem;color:{row["_cor"]}">{row["Z-Score"]:+.2f}</b><br>'
                        f'<span style="font-size:0.7rem">{row["Estado"]}</span></div>',
                        unsafe_allow_html=True
                    )

                st.divider()
                fig_eq_perf = go.Figure(go.Bar(
                    x=df_ep["Jogador"], y=df_ep["Z-Score"],
                    marker_color=df_ep["_cor"].tolist(),
                    text=df_ep["Z-Score"].round(2), textposition="outside",
                ))
                fig_eq_perf.add_hline(y=1,  line_dash="dot", line_color="#f39c12")
                fig_eq_perf.add_hline(y=-1, line_dash="dot", line_color="#3498db")
                fig_eq_perf.add_hline(y=0,  line_color="white", line_width=1)
                fig_eq_perf.update_layout(
                    yaxis_title=f"Z-Score ({met_eq_p})", height=380,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=20), showlegend=False,
                )
                st.plotly_chart(fig_eq_perf, use_container_width=True)
            else:
                st.warning("Dados insuficientes para calcular perfis individuais.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: LESÕES & DISPONIBILIDADE
        # ═══════════════════════════════════════════════════════════════════════════════

    with st.expander("🦵 Testes Neuromusculares", expanded=False):

            try:
                df_cmj = pd.read_excel(excel_path, sheet_name="Testes_Neuromusculares", engine="openpyxl")
                df_cmj.columns = [str(c).strip() for c in df_cmj.columns]
                tem_dados = not df_cmj.empty and len(df_cmj) > 1
            except Exception:
                df_cmj = pd.DataFrame(); tem_dados = False

            if not tem_dados:
                st.info("""
        ### Folha 'Testes_Neuromusculares' não encontrada

        Adiciona uma folha ao Excel com estas colunas:
        **Data · Jogador · Posição · Tipo Teste · Altura Salto (cm) · Potência Relativa (W/kg) · RSI (m/s) · Assimetria (%) · Fase Excêntrica (s) · Fase Concêntrica (s) · RFD (N/s) · Microciclo (Nr) · Observações**
                """)
                # Dados de exemplo
                np.random.seed(42)
                jogs_ex = ["Paulino","Rafael","André","Diogo","Miguel","Carlos","João","Pedro","Tiago","Luís"]
                pos_ex  = ["GR","DC","DC","DD","DE","MC","MC","MD","AV","AV"]
                df_cmj = pd.DataFrame({
                    "Jogador": jogs_ex, "Posição": pos_ex,
                    "Altura Salto (cm)": np.random.normal(35,5,10).clip(22,50).round(1),
                    "Potência Relativa (W/kg)": np.random.normal(40,6,10).clip(26,56).round(1),
                    "Assimetria (%)": np.random.exponential(4,10).clip(0,18).round(1),
                    "RSI (m/s)": np.random.normal(1.8,0.3,10).clip(1.0,2.8).round(2),
                    "Tipo Teste": ["CMJ"]*10, "Data": [pd.Timestamp("2025-01-15")]*10,
                })
                st.caption("⚠️ Dados de exemplo — adiciona a folha 'Testes_Neuromusculares' para ver os teus dados")

            for col in ["Altura Salto (cm)","Potência Relativa (W/kg)","Assimetria (%)","RSI (m/s)","RFD (N/s)"]:
                if col in df_cmj.columns:
                    df_cmj[col] = pd.to_numeric(df_cmj[col], errors="coerce")

            df_latest = df_cmj.groupby("Jogador").last().reset_index() if "Jogador" in df_cmj.columns else df_cmj

            tab_nm1, tab_nm2, tab_nm3 = st.tabs(["🎯 Perfil Neuromuscular", "🏆 Rankings", "⚖️ Assimetria"])

            with tab_nm1:
                if "Altura Salto (cm)" in df_latest.columns and "RSI (m/s)" in df_latest.columns:
                    df_sc_nm = df_latest.dropna(subset=["Altura Salto (cm)","RSI (m/s)"]).copy()
                    if not df_sc_nm.empty:
                        x_mean_nm = df_sc_nm["Altura Salto (cm)"].mean()
                        y_mean_nm = df_sc_nm["RSI (m/s)"].mean()
                        CORES_POS_NM = {"GR":"#3498db","DC":"#2ecc71","DD":"#2ecc71","DE":"#2ecc71","MC":"#f39c12","MD":"#f39c12","AV":"#e63946"}
                        fig_nm = go.Figure()
                        fig_nm.add_hline(y=y_mean_nm, line_dash="dot", line_color="rgba(255,255,255,0.2)")
                        fig_nm.add_vline(x=x_mean_nm, line_dash="dot", line_color="rgba(255,255,255,0.2)")
                        for lbl, xp, yp, cor_q in [
                            ("EXPLOSIVE", df_sc_nm["Altura Salto (cm)"].max(), df_sc_nm["RSI (m/s)"].max(), "#2ecc71"),
                            ("POWER",     df_sc_nm["Altura Salto (cm)"].max(), df_sc_nm["RSI (m/s)"].min(), "#3498db"),
                            ("REACTIVE",  df_sc_nm["Altura Salto (cm)"].min(), df_sc_nm["RSI (m/s)"].max(), "#f39c12"),
                            ("UNDERPOWERED", df_sc_nm["Altura Salto (cm)"].min(), df_sc_nm["RSI (m/s)"].min(), "#e74c3c"),
                        ]:
                            fig_nm.add_annotation(x=xp, y=yp, text=lbl, font=dict(size=9, color=cor_q), showarrow=False, opacity=0.5)
                        for pos in df_sc_nm["Posição"].dropna().unique() if "Posição" in df_sc_nm.columns else [None]:
                            sub = df_sc_nm[df_sc_nm["Posição"]==pos] if pos else df_sc_nm
                            cor = CORES_POS_NM.get(str(pos), "#9b59b6") if pos else "#00d4ff"
                            fig_nm.add_trace(go.Scatter(
                                x=sub["Altura Salto (cm)"], y=sub["RSI (m/s)"],
                                mode="markers+text",
                                text=sub["Jogador"].apply(lambda n: n.split()[0] if isinstance(n,str) else n),
                                textposition="top center", textfont=dict(size=9, color="white"),
                                marker=dict(size=18, color=cor, opacity=0.85, line=dict(width=2, color="white")),
                                name=str(pos) if pos else "Todos",
                            ))
                        fig_nm.update_layout(height=520, xaxis_title="Altura Salto CMJ (cm)", yaxis_title="RSI (m/s)",
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=20))
                        st.plotly_chart(fig_nm, use_container_width=True)

            with tab_nm2:
                mets_rank_nm = get_mets_gps(df_latest)
                if mets_rank_nm:
                    met_nm = st.selectbox("Métrica", mets_rank_nm, key="nm_rank")
                    df_rk_nm = df_latest.dropna(subset=[met_nm]).sort_values(met_nm, ascending=True)
                    fig_rk_nm = go.Figure(go.Bar(y=df_rk_nm["Jogador"], x=df_rk_nm[met_nm], orientation="h",
                        marker_color="#e63946", text=df_rk_nm[met_nm].round(1), textposition="outside"))
                    fig_rk_nm.add_vline(x=df_rk_nm[met_nm].mean(), line_dash="dash", line_color="white",
                                          annotation_text=f"Média: {df_rk_nm[met_nm].mean():.1f}")
                    fig_rk_nm.update_layout(height=max(300,len(df_rk_nm)*42), xaxis_title=met_nm,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=5))
                    st.plotly_chart(fig_rk_nm, use_container_width=True)

            with tab_nm3:
                if "Assimetria (%)" in df_latest.columns and df_latest["Assimetria (%)"].notna().any():
                    df_asy = df_latest.dropna(subset=["Assimetria (%)"]).sort_values("Assimetria (%)", ascending=False)
                    cores_asy = ["#e74c3c" if v>15 else "#f39c12" if v>10 else "#2ecc71" for v in df_asy["Assimetria (%)"]]
                    fig_asy = go.Figure(go.Bar(x=df_asy["Jogador"], y=df_asy["Assimetria (%)"],
                        marker_color=cores_asy, text=df_asy["Assimetria (%)"].apply(lambda v: f"{v:.1f}%"), textposition="outside"))
                    fig_asy.add_hline(y=15, line_dash="dash", line_color="#e74c3c", annotation_text="Crítico 15%")
                    fig_asy.add_hline(y=10, line_dash="dot",  line_color="#f39c12", annotation_text="Atenção 10%")
                    fig_asy.update_layout(height=340, yaxis_title="Assimetria (%)",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                    st.plotly_chart(fig_asy, use_container_width=True)
                    criticos = df_asy[df_asy["Assimetria (%)"]>15]["Jogador"].tolist()
                    if criticos: st.error(f"🔴 Assimetria crítica (>15%): {', '.join(criticos)}")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🏃 NORMALIZAÇÃO HSR/SPRINT
        # ═══════════════════════════════════════════════════════════════════════════════

            st.markdown("> Ref.: **Pimenta et al.** — *Sprint and High-Speed Running: Should We Use Absolute or Normalized Thresholds?* · Journal of Human Kinetics")

            if "Vel. Máx (km/h)" not in df.columns:
                st.error("Coluna 'Vel. Máx (km/h)' necessária.")

            vmaxes = df.groupby("Jogador")["Vel. Máx (km/h)"].max().reset_index()
            vmaxes.columns = ["Jogador","Vmáx Record (km/h)"]
            for pct in [85,90,95]:
                vmaxes[f"Lim {pct}% (km/h)"] = (vmaxes["Vmáx Record (km/h)"] * pct/100).round(1)
            if "Posição" in df.columns:
                vmaxes["Posição"] = vmaxes["Jogador"].map(df.groupby("Jogador")["Posição"].last())

            tab_nh1, tab_nh2 = st.tabs(["📊 Limiares Individuais", "📐 Absoluto vs Normalizado"])

            with tab_nh1:
                df_vs = vmaxes.sort_values("Vmáx Record (km/h)", ascending=True)
                fig_vn = go.Figure()
                fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Vmáx Record (km/h)"],
                    orientation="h", marker_color="#e63946", name="Vmáx Record",
                    text=df_vs["Vmáx Record (km/h)"].round(1), textposition="outside"))
                fig_vn.add_trace(go.Bar(y=df_vs["Jogador"], x=df_vs["Lim 90% (km/h)"],
                    orientation="h", marker_color="rgba(255,255,255,0.15)", name="Limiar 90%"))
                fig_vn.update_layout(barmode="overlay", height=max(300,len(df_vs)*42),
                    xaxis_title="km/h", yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=5))
                st.plotly_chart(fig_vn, use_container_width=True)
                st.dataframe(vmaxes.set_index("Jogador"), use_container_width=True)

            with tab_nh2:
                if "Posição" in vmaxes.columns:
                    pos_vmax = vmaxes.groupby("Posição").agg(
                        Vmáx_media=("Vmáx Record (km/h)","mean"),
                        Vmáx_max=("Vmáx Record (km/h)","max"),
                        Vmáx_min=("Vmáx Record (km/h)","min"),
                        n=("Jogador","count"),
                    ).reset_index().sort_values("Vmáx_media", ascending=False)
                    fig_pos_vn = go.Figure()
                    fig_pos_vn.add_trace(go.Bar(x=pos_vmax["Posição"], y=pos_vmax["Vmáx_media"],
                        name="Vmáx Média", marker_color="#e63946",
                        text=pos_vmax["Vmáx_media"].round(1), textposition="outside",
                        error_y=dict(type="data",
                            array=(pos_vmax["Vmáx_max"]-pos_vmax["Vmáx_media"]).tolist(),
                            arrayminus=(pos_vmax["Vmáx_media"]-pos_vmax["Vmáx_min"]).tolist(),
                            visible=True, color="rgba(255,255,255,0.4)"),
                    ))
                    fig_pos_vn.add_hline(y=25, line_dash="dash", line_color="#f39c12", annotation_text="Limiar absoluto 25 km/h")
                    fig_pos_vn.add_hline(y=19.8, line_dash="dot", line_color="#3498db", annotation_text="Limiar absoluto 19.8 km/h")
                    fig_pos_vn.update_layout(height=380, yaxis_title="Velocidade Máxima (km/h)",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20))
                    st.plotly_chart(fig_pos_vn, use_container_width=True)
                    st.caption("Barras de erro = min–max · Linhas = limiares absolutos standard")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🧮 CALCULADORA DE EXERCÍCIOS
        # ═══════════════════════════════════════════════════════════════════════════════
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · **Owen et al. (2011)**")

            EXERCICIOS_REF = {
                "Rondo / Posse fechada":           {"dist_min":82,  "acc_min":1.8, "frac_hsr":0.015,"frac_spr":0.003,"frac_dcc":0.85,"vmax_ref":23,"metabolico":"Aeróbia lática mista","neuro":"Força-Velocidade"},
                "Jogo Posicional (5-8v5-8)":       {"dist_min":110, "acc_min":2.4, "frac_hsr":0.060,"frac_spr":0.010,"frac_dcc":0.82,"vmax_ref":26,"metabolico":"Aeróbia-Anaeróbia","neuro":"Potência"},
                "Jogo Reduzido Pequeno (3-4v)":    {"dist_min":130, "acc_min":3.6, "frac_hsr":0.035,"frac_spr":0.008,"frac_dcc":0.88,"vmax_ref":25,"metabolico":"Anaeróbia lática","neuro":"Força-Velocidade"},
                "Jogo Reduzido Médio (5-7v)":      {"dist_min":118, "acc_min":2.8, "frac_hsr":0.065,"frac_spr":0.018,"frac_dcc":0.85,"vmax_ref":27,"metabolico":"Aeróbia-Anaeróbia mista","neuro":"Potência-Velocidade"},
                "Jogo Reduzido Grande (8-10v)":    {"dist_min":108, "acc_min":2.0, "frac_hsr":0.090,"frac_spr":0.030,"frac_dcc":0.80,"vmax_ref":29,"metabolico":"Predominantemente aeróbia","neuro":"Resistência"},
                "Jogo Formal (11v11)":             {"dist_min":115, "acc_min":1.6, "frac_hsr":0.110,"frac_spr":0.038,"frac_dcc":0.80,"vmax_ref":31,"metabolico":"Aeróbia com picos","neuro":"Velocidade-Resistência"},
                "Sprint / Velocidade":             {"dist_min":145, "acc_min":4.5, "frac_hsr":0.280,"frac_spr":0.180,"frac_dcc":0.88,"vmax_ref":32,"metabolico":"Anaeróbia alática","neuro":"Velocidade máxima"},
                "Físico / Resistência":            {"dist_min":185, "acc_min":0.8, "frac_hsr":0.020,"frac_spr":0.002,"frac_dcc":0.80,"vmax_ref":20,"metabolico":"Aeróbia extensiva","neuro":"Resistência"},
                "Técnico-Tático":                  {"dist_min":70,  "acc_min":1.2, "frac_hsr":0.010,"frac_spr":0.002,"frac_dcc":0.82,"vmax_ref":22,"metabolico":"Aeróbia leve","neuro":"Coordenação"},
                "Ativação / Aquecimento":          {"dist_min":55,  "acc_min":0.6, "frac_hsr":0.005,"frac_spr":0.001,"frac_dcc":0.80,"vmax_ref":19,"metabolico":"Aeróbia leve","neuro":"Ativação"},
                "Retorno à Calma":                 {"dist_min":30,  "acc_min":0.2, "frac_hsr":0.002,"frac_spr":0.000,"frac_dcc":0.80,"vmax_ref":14,"metabolico":"Recuperação","neuro":"Recuperação"},
            }

            tab_c1, tab_c2 = st.tabs(["🧮 Calculadora", "📋 Tabela de Referência"])

            with tab_c1:
                col_c1, col_c2 = st.columns(2)
                tipo_ex = col_c1.selectbox("Tipo de Exercício", list(EXERCICIOS_REF.keys()), key="calc_tipo")
                n_jog   = col_c2.number_input("Nº de Jogadores", 2, 22, 8, key="calc_njog")
                duracao = col_c1.number_input("Duração (min)", 1, 60, 15, key="calc_dur")
                espaco  = col_c2.number_input("Espaço total (m²)", 50, 10000, 800, key="calc_esp")

                ref = EXERCICIOS_REF[tipo_ex]
                esp_jog = espaco / n_jog if n_jog > 0 else 100
                fator_esp = max(0.6, min(1.0 + (esp_jog - 100)/100 * 0.18, 1.6))
                fator_acc = max(0.5, min(1.0 + (100 - esp_jog)/100 * 0.25, 1.5))

                dist_jog   = ref["dist_min"] * duracao * fator_esp
                hsr_jog    = dist_jog * ref["frac_hsr"]
                sprint_jog = dist_jog * ref["frac_spr"]
                acc_jog    = ref["acc_min"] * fator_acc * duracao
                dcc_jog    = acc_jog * ref["frac_dcc"]
                vmax_ref   = ref["vmax_ref"]

                st.divider()
                st.markdown('<p class="section-title">📊 Previsão por Jogador</p>', unsafe_allow_html=True)
                k1,k2,k3,k4,k5,k6 = st.columns(6)
                for col_k, lbl, val, unit, hlp in [
                    (k1,"Distância",      f"{dist_jog:,.0f}","m",   "Distância total estimada"),
                    (k2,"HSR",            f"{hsr_jog:,.0f}", "m",   "Alta Velocidade"),
                    (k3,"Sprint",         f"{sprint_jog:,.0f}","m", "Velocidade máxima"),
                    (k4,"Acc (n)",        f"{acc_jog:.0f}",  "",    "Acelerações estimadas"),
                    (k5,"Dcc (n)",        f"{dcc_jog:.0f}",  "",    "Desacelerações estimadas"),
                    (k6,"Vmáx esperada",  f"{vmax_ref}",     "km/h","Velocidade máxima de referência"),
                ]:
                    col_k.metric(f"{lbl} {unit}".strip(), val, help=hlp)

                st.markdown('<p class="section-title">📦 Total da Equipa</p>', unsafe_allow_html=True)
                te1,te2,te3,te4,te5 = st.columns(5)
                te1.metric("Distância Total", f"{dist_jog*n_jog/1000:.2f} km")
                te2.metric("HSR Total",       f"{hsr_jog*n_jog:,.0f} m")
                te3.metric("Sprint Total",    f"{sprint_jog*n_jog:,.0f} m")
                te4.metric("Acc Total",       f"{acc_jog*n_jog:.0f}")
                te5.metric("Dcc Total",       f"{dcc_jog*n_jog:.0f}")

                col_i1,col_i2,col_i3 = st.columns(3)
                col_i1.info(f"⚗️ **Perfil Metabólico:** {ref['metabolico']}")
                col_i2.info(f"💪 **Perfil Neuromuscular:** {ref['neuro']}")
                col_i3.info(f"📐 **m²/jog:** {esp_jog:.0f} · Fator: {fator_esp:.2f}×")

            with tab_c2:
                df_ref_tab = pd.DataFrame([{
                    "Tipo": k, "Dist/min (m)": v["dist_min"],
                    "Acc/min": v["acc_min"], "Frac. HSR": f"{v['frac_hsr']*100:.1f}%",
                    "Frac. Sprint": f"{v['frac_spr']*100:.1f}%",
                    "Vmáx Ref (km/h)": v["vmax_ref"],
                    "Perfil Metabólico": v["metabolico"], "Perfil Neuro": v["neuro"],
                } for k,v in EXERCICIOS_REF.items()])
                st.dataframe(df_ref_tab.set_index("Tipo"), use_container_width=True)
                st.caption("Fonte: Casamichana & Castellano (2010) · Dellal et al. (2012) · Hill-Haas et al. (2011)")


        # ═══════════════════════════════════════════════════════════════════════════════
        # 📐 ESPAÇO & CARGA EXTERNA
        # ═══════════════════════════════════════════════════════════════════════════════
            st.markdown("> **Casamichana & Castellano (2010)** · **Dellal et al. (2012)** · **Hill-Haas et al. (2011)** · *'Duplicar o espaço → +15–25% distância'* (r=0.76)")

            ZONAS_ESP = [
                {"zona":"ZONA 1 — < 30 m²/jog",    "esp_min":0,   "esp_max":30,  "dist":"70–90 m/min",  "hsr":"<1%",    "sprint":"<0.3%",  "acc":"4–6/min",    "exemplos":"Rondos, posses fechadas","cor":"#2ecc71"},
                {"zona":"ZONA 2 — 30–100 m²/jog",  "esp_min":30,  "esp_max":100, "dist":"90–115 m/min", "hsr":"3–7%",   "sprint":"0.5–1%", "acc":"2–4/min",    "exemplos":"Jogos reduzidos 4v4–7v7","cor":"#f39c12"},
                {"zona":"ZONA 3 — 100–200 m²/jog", "esp_min":100, "esp_max":200, "dist":"110–130 m/min","hsr":"7–12%",  "sprint":"1.5–3%", "acc":"1–2/min",    "exemplos":"Jogos 8v8–10v10",        "cor":"#e67e22"},
                {"zona":"ZONA 4 — > 200 m²/jog",   "esp_min":200, "esp_max":999, "dist":">130 m/min",   "hsr":">12%",   "sprint":">3%",    "acc":"<1/min",     "exemplos":"Jogo formal",            "cor":"#e74c3c"},
            ]

            tab_esp1, tab_esp2 = st.tabs(["📊 Matriz de Referência", "🧮 Simulador"])

            with tab_esp1:
                cols_z = st.columns(4)
                for i, zona in enumerate(ZONAS_ESP):
                    cor_z = zona["cor"]
                    cols_z[i].markdown(
                        f'<div style="background:{cor_z}18;border:1px solid {cor_z}44;border-top:3px solid {cor_z};border-radius:10px;padding:14px;margin:4px">'
                        f'<div style="font-size:0.72rem;font-weight:700;color:{cor_z};margin-bottom:10px">{zona["zona"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Distância:</b> {zona["dist"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>HSR:</b> {zona["hsr"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Sprint:</b> {zona["sprint"]}</div>'
                        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.8);margin:5px 0"><b>Acc/Dcc:</b> {zona["acc"]}</div>'
                        f'<div style="font-size:0.62rem;color:rgba(255,255,255,0.4);margin-top:8px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.06)">{zona["exemplos"]}</div>'
                        f'</div>', unsafe_allow_html=True)

            with tab_esp2:
                col_s1,col_s2,col_s3 = st.columns(3)
                s_x    = col_s1.number_input("Comprimento (m)", 10, 120, 40, key="esp_x")
                s_y    = col_s2.number_input("Largura (m)", 5, 80, 30, key="esp_y")
                s_njog = col_s3.number_input("Nº Jogadores em campo", 4, 22, 10, key="esp_njog_total")
                s_dur  = col_s1.number_input("Duração (min)", 1, 60, 12, key="esp_dur")
                s_tipo = col_s2.selectbox("Tipo", ["Jogo Reduzido","Jogo Posicional","Jogo Formal","Sprint"], key="esp_tipo")

                area_total = s_x * s_y
                area_jog   = area_total / s_njog if s_njog > 0 else 100
                base_dist  = {"Jogo Reduzido":100,"Jogo Posicional":110,"Jogo Formal":115,"Sprint":145}.get(s_tipo,110)
                fator_s    = max(0.6, min(1.0 + (area_jog - 100)/100 * 0.18, 1.6))
                fator_a    = max(0.5, min(1.0 + (100 - area_jog)/100 * 0.25, 1.5))
                frac_hsr   = {"Jogo Reduzido":0.065,"Jogo Posicional":0.060,"Jogo Formal":0.110,"Sprint":0.280}.get(s_tipo,0.065)
                frac_spr   = {"Jogo Reduzido":0.018,"Jogo Posicional":0.010,"Jogo Formal":0.038,"Sprint":0.180}.get(s_tipo,0.018)
                acc_min    = {"Jogo Reduzido":2.8,"Jogo Posicional":2.4,"Jogo Formal":1.6,"Sprint":4.5}.get(s_tipo,2.8)

                dist_s = base_dist * fator_s * s_dur
                hsr_s  = dist_s * frac_hsr
                spr_s  = dist_s * frac_spr
                acc_s  = acc_min * fator_a * s_dur
                dcc_s  = acc_s * 0.85

                zona_id = next((z for z in ZONAS_ESP if z["esp_min"] <= area_jog < z["esp_max"]), ZONAS_ESP[-1])
                cor_z2 = zona_id["cor"]
                st.markdown(f'<div style="background:{cor_z2}18;border:2px solid {cor_z2}55;border-radius:12px;padding:14px;margin:10px 0"><div style="font-size:0.75rem;font-weight:700;color:{cor_z2}">{zona_id["zona"]} — {area_jog:.0f} m²/jogador</div><div style="font-size:0.78rem;color:rgba(255,255,255,0.7);margin-top:4px">{s_x}×{s_y}m = {area_total} m² · {s_njog} jogadores</div></div>', unsafe_allow_html=True)

                k1e,k2e,k3e,k4e,k5e,k6e = st.columns(6)
                for col_ke, lbl_e, val_e in [
                    (k1e,"Distância/jog",f"{dist_s:,.0f} m"),
                    (k2e,"HSR/jog",      f"{hsr_s:,.0f} m"),
                    (k3e,"Sprint/jog",   f"{spr_s:,.0f} m"),
                    (k4e,"Acc/jog",      f"{acc_s:.0f}"),
                    (k5e,"Dcc/jog",      f"{dcc_s:.0f}"),
                    (k6e,"Fator Espaço", f"{fator_s:.2f}×"),
                ]:
                    col_ke.metric(lbl_e, val_e)


        # ═══════════════════════════════════════════════════════════════════════════════
        # ✅ VALIDAÇÃO DE DADOS
        # ═══════════════════════════════════════════════════════════════════════════════

            if st.button("🔍 Validar agora", type="primary"):
                with st.spinner("A analisar..."):
                    erros, avisos, ok_list = validar_dados(df)

                total = len(erros) + len(avisos) + len(ok_list)
                score = int(len(ok_list)/total*100) if total > 0 else 0
                cor_s = "#2ecc71" if score>=80 else "#f39c12" if score>=60 else "#e74c3c"

                col_sc, col_res = st.columns([1,3])
                col_sc.markdown(f'<div style="background:{cor_s}22;border:3px solid {cor_s};border-radius:16px;padding:20px;text-align:center"><div style="font-size:0.9rem;color:#aaa">Qualidade</div><div style="font-size:3rem;font-weight:900;color:{cor_s}">{score}%</div></div>', unsafe_allow_html=True)
                col_res.metric("❌ Erros críticos", len(erros))
                col_res.metric("⚠️ Avisos", len(avisos))
                col_res.metric("✅ OK", len(ok_list))

                st.divider()
                for e in erros:   st.error(e)
                for a in avisos:  st.warning(a)
                for o in ok_list: st.success(o)

                st.divider()
                st.markdown("### 🔍 Valores únicos por coluna crítica")
                for col in ["Tipo","Dia MD","Posição","Microciclo (Nr)"]:
                    if col in df.columns:
                        vals = df[col].dropna().unique()
                        with st.expander(f"**{col}** — {len(vals)} valores únicos"):
                            st.write(sorted([str(v) for v in vals]))

                cols_crit = get_mets_gps(df)
                df_nulos = df[df[cols_crit].isna().any(axis=1)][cols_crit]
                if df_nulos.empty:
                    st.success("✅ Nenhum registo com campos críticos em falta!")
                else:
                    st.warning(f"{len(df_nulos)} registos com campos críticos em falta:")
                    st.dataframe(df_nulos, use_container_width=True)
            else:
                st.info("Clica em **🔍 Validar agora** para analisar a qualidade dos dados.")





