"""LoadMonitorSystem — Página Planeamento"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os
_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_dir not in sys.path: sys.path.insert(0, _app_dir)
from utils import (calcular_acwr, calcular_acwr_global, zscore_serie, cor_acwr,
                   calcular_monotonia_strain, lm_header, premium_layout,
                   botao_download_html, gerar_pdf_html, get_mets_gps,
                   metric_card, sem_dados_suficientes, carregar_exercicios)

def render(df, excel_path, **kwargs):
    _lm_user = kwargs.get("lm_user", {})
    _lm_plano = _lm_user.get("plano", "free")
    _lm_nome = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")
    lm_header("Planeamento", "Ferramentas de planeamento e comparação com jogo", "Planeamento")
    _vista_plan = st.selectbox(
        "Vista",
        ["📋 Planeado vs Realizado", "⚽ Jogo vs Treino", "📊 Treino vs Jogo %", "🧮 Calculadora de Exercícios", "📐 Espaço & Carga Externa"],
        key="sel_vista_plan", label_visibility="collapsed"
    )

    _PLAN_LABELS = ["📋 Planeado vs Realizado","⚽ Jogo vs Treino","📊 Treino vs Jogo %","🧮 Calculadora de Exercícios","📐 Espaço & Carga Externa"]
    _plan_idx = _PLAN_LABELS.index(_vista_plan) if _vista_plan in _PLAN_LABELS else 0

    if _plan_idx == 0:
            st.markdown('<p class="section-title">⚽ Carga de Jogo vs Carga de Treino</p>', unsafe_allow_html=True)
            st.caption("Percentagem da carga de jogo em relação ao total do microciclo")

            METRICAS_JOGO = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)",
                "Acc (n)", "Dcc (n)", "Carga Interna", "PSE Sessão",
            ]
            mets_jogo_disp = [m for m in METRICAS_JOGO if m in df.columns]

            # Separar treinos e jogos
            if "Tipo" not in df.columns:
                st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com valores 'Treino' e 'Jogo'.")

            df_jogos   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
            df_treinos = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

            if df_jogos.empty:
                st.warning("Nenhum registo com Tipo = 'Jogo' encontrado no Excel.")

            # Filtros de contexto
            col1, col2, col3 = st.columns(3)
            mc_jogo = col1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="jogo_mc")
            met_jogo = col2.selectbox("Métrica", mets_jogo_disp, key="jogo_met")
            modo_jogo = col3.radio("Modo de comparação", ["Por Jogador", "Equipa (média)"], key="jogo_modo")

            st.divider()

            # ── Dados do microciclo selecionado ───────────────────────────────────────
            jogos_mc   = df_jogos[df_jogos["Microciclo (Nr)"] == mc_jogo]
            treinos_mc = df_treinos[df_treinos["Microciclo (Nr)"] == mc_jogo]

            if jogos_mc.empty:
                st.warning(f"Sem registos de jogo para o Microciclo {int(mc_jogo)}.")

            if treinos_mc.empty:
                st.warning(f"Sem registos de treino para o Microciclo {int(mc_jogo)}.")

            # ── MODO: POR JOGADOR ─────────────────────────────────────────────────────
            if modo_jogo == "Por Jogador":
                jog_jogo = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="jogo_jog")

                jogo_jog   = jogos_mc[jogos_mc["Jogador"] == jog_jogo]
                treino_jog = treinos_mc[treinos_mc["Jogador"] == jog_jogo]

                if jogo_jog.empty or treino_jog.empty:
                    st.warning(f"Dados insuficientes para {jog_jogo} no MC {int(mc_jogo)}.")

                carga_jogo_val   = jogo_jog[met_jogo].sum()
                carga_treino_val = treino_jog[met_jogo].sum()
                carga_total      = carga_jogo_val + carga_treino_val
                pct_jogo         = (carga_jogo_val / carga_total * 100) if carga_total > 0 else 0
                pct_treino       = 100 - pct_jogo

                # KPIs
                k1, k2, k3, k4 = st.columns(4)
                k1.metric(f"Carga Jogo ({met_jogo})",   f"{carga_jogo_val:,.1f}")
                k2.metric(f"Carga Treino ({met_jogo})",  f"{carga_treino_val:,.1f}")
                k3.metric("Total Semanal",               f"{carga_total:,.1f}")
                k4.metric("% Jogo / Total",              f"{pct_jogo:.1f}%")

                st.divider()

                # Gráfico de rosca jogo vs treino
                col_pie, col_bar = st.columns(2)

                with col_pie:
                    st.markdown('<p class="section-title">Proporção Jogo vs Treino</p>', unsafe_allow_html=True)
                    fig_pie = go.Figure(go.Pie(
                        labels=["⚽ Jogo", "🏃 Treino"],
                        values=[carga_jogo_val, carga_treino_val],
                        hole=0.55,
                        marker_colors=["#e63946", "#457b9d"],
                        textinfo="label+percent",
                    ))
                    fig_pie.update_layout(
                        height=320, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                        margin=dict(t=20),
                        annotations=[dict(text=f"{pct_jogo:.0f}%<br>Jogo", x=0.5, y=0.5,
                                           font_size=18, showarrow=False, font_color="rgba(255,255,255,0.85)")],
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_bar:
                    st.markdown('<p class="section-title">Distribuição por Dia MD</p>', unsafe_allow_html=True)
                    # Carga por dia MD
                    treino_dia = treino_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in treino_jog.columns else pd.DataFrame()
                    jogo_dia   = jogo_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in jogo_jog.columns else pd.DataFrame()

                    ordem_dias = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1"]

                    if not treino_dia.empty or not jogo_dia.empty:
                        all_dias = pd.DataFrame({"Dia MD": ordem_dias})
                        treino_dia_full = all_dias.merge(treino_dia, on="Dia MD", how="left").fillna(0)
                        jogo_dia_full   = all_dias.merge(jogo_dia,   on="Dia MD", how="left").fillna(0)

                        fig_dias_bar = go.Figure()
                        fig_dias_bar.add_trace(go.Bar(
                            x=treino_dia_full["Dia MD"], y=treino_dia_full[met_jogo],
                            name="Treino", marker_color="#457b9d",
                        ))
                        fig_dias_bar.add_trace(go.Bar(
                            x=jogo_dia_full["Dia MD"], y=jogo_dia_full[met_jogo],
                            name="Jogo", marker_color="#e63946",
                        ))
                        fig_dias_bar.update_layout(
                            barmode="stack", height=320,
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", yaxis_title=met_jogo, margin=dict(t=10),
                        )
                        st.plotly_chart(fig_dias_bar, use_container_width=True)

                # Contexto histórico — % jogo ao longo dos microciclos
                st.divider()
                st.markdown('<p class="section-title">📈 Evolução da % de Carga de Jogo ao longo dos Microciclos</p>', unsafe_allow_html=True)

                rows_hist = []
                for mc in sorted(df["Microciclo (Nr)"].dropna().unique()):
                    j_mc = df_jogos[(df_jogos["Microciclo (Nr)"] == mc) & (df_jogos["Jogador"] == jog_jogo)]
                    t_mc = df_treinos[(df_treinos["Microciclo (Nr)"] == mc) & (df_treinos["Jogador"] == jog_jogo)]
                    if j_mc.empty or t_mc.empty:
                        continue
                    cj = j_mc[met_jogo].sum()
                    ct = t_mc[met_jogo].sum()
                    total = cj + ct
                    rows_hist.append({
                        "Microciclo": int(mc),
                        "Carga Jogo": round(cj, 1),
                        "Carga Treino": round(ct, 1),
                        "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
                    })

                if rows_hist:
                    df_hist = pd.DataFrame(rows_hist)
                    fig_hist_jogo = go.Figure()
                    fig_hist_jogo.add_trace(go.Scatter(
                        x=df_hist["Microciclo"], y=df_hist["% Jogo"],
                        mode="lines+markers+text",
                        text=[f"{v:.0f}%" for v in df_hist["% Jogo"]],
                        textposition="top center",
                        line_color="#e63946", line_width=2, marker_size=8, name="% Jogo",
                    ))
                    fig_hist_jogo.add_hline(y=30, line_dash="dash", line_color="#f39c12",
                                             annotation_text="30% referência")
                    fig_hist_jogo.update_layout(
                        yaxis=dict(title="% Carga de Jogo", range=[0, 100]),
                        xaxis_title="Microciclo",
                        height=320, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_hist_jogo, use_container_width=True)

            # ── MODO: EQUIPA ─────────────────────────────────────────────────────────
            else:
                st.markdown('<p class="section-title">% Carga de Jogo vs Treino por Jogador — Equipa</p>', unsafe_allow_html=True)

                rows_eq = []
                for jog in sorted(df["Jogador"].dropna().unique()):
                    j = jogos_mc[jogos_mc["Jogador"] == jog]
                    t = treinos_mc[treinos_mc["Jogador"] == jog]
                    if j.empty or t.empty or met_jogo not in j.columns:
                        continue
                    cj = j[met_jogo].sum()
                    ct = t[met_jogo].sum()
                    total = cj + ct
                    pos = j["Posição"].iloc[0] if "Posição" in j.columns else "—"
                    rows_eq.append({
                        "Jogador": jog,
                        "Posição": pos,
                        "Carga Jogo": round(cj, 1),
                        "Carga Treino": round(ct, 1),
                        "Total Semanal": round(total, 1),
                        "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
                    })

                if not rows_eq:
                    st.warning("Sem dados suficientes para a equipa neste microciclo.")

                df_eq = pd.DataFrame(rows_eq).sort_values("% Jogo", ascending=False)

                # KPIs equipa
                k1, k2, k3 = st.columns(3)
                k1.metric("% Jogo Média da Equipa", f"{df_eq['% Jogo'].mean():.1f}%")
                k2.metric("Carga Jogo Média",        f"{df_eq['Carga Jogo'].mean():,.1f}")
                k3.metric("Carga Treino Média",      f"{df_eq['Carga Treino'].mean():,.1f}")

                # Gráfico barras empilhadas
                cores_eq = ["#e74c3c" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]]
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["Carga Jogo"],
                    name="⚽ Jogo", marker_color="#e63946",
                ))
                fig_eq.add_trace(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["Carga Treino"],
                    name="🏃 Treino", marker_color="#457b9d",
                ))
                fig_eq.update_layout(
                    barmode="stack", height=380,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", yaxis_title=met_jogo,
                    legend=dict(orientation="h", y=1.05), margin=dict(t=30),
                )
                st.plotly_chart(fig_eq, use_container_width=True)

                # % Jogo por jogador
                fig_pct_eq = go.Figure(go.Bar(
                    x=df_eq["Jogador"], y=df_eq["% Jogo"],
                    marker_color=["#e63946" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]],
                    text=[f"{v:.1f}%" for v in df_eq["% Jogo"]],
                    textposition="outside",
                ))
                fig_pct_eq.add_hline(y=30, line_dash="dash", line_color="#f39c12", annotation_text="30% referência")
                fig_pct_eq.update_layout(
                    yaxis=dict(title="% Jogo / Total", range=[0, max(df_eq["% Jogo"]) + 15]),
                    height=340, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    showlegend=False, margin=dict(t=20),
                )
                st.plotly_chart(fig_pct_eq, use_container_width=True)

                # Tabela completa
                st.dataframe(df_eq.set_index("Jogador"), use_container_width=True)

                # Conclusões equipa
                st.divider()
                st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
                alto_jogo  = df_eq[df_eq["% Jogo"] > 40]["Jogador"].tolist()
                medio_jogo = df_eq[df_eq["% Jogo"].between(30, 40)]["Jogador"].tolist()
                baixo_jogo = df_eq[df_eq["% Jogo"] < 30]["Jogador"].tolist()

                if alto_jogo:
                    st.markdown(f"🔴 **Carga de jogo muito elevada** (>40%): {', '.join(alto_jogo)} — estes jogadores fizeram grande parte do esforço semanal no jogo. Atenção à recuperação.")
                if medio_jogo:
                    st.markdown(f"🟡 **Proporção equilibrada** (30-40%): {', '.join(medio_jogo)} — valores dentro do esperado.")
                if baixo_jogo:
                    st.markdown(f"🔵 **Pouca exposição em jogo** (<30%): {', '.join(baixo_jogo)} — baixo volume de jogo relativamente ao treino (lesão, banco, rotação?).")
                st.markdown(f"📊 **Média da equipa**: {df_eq['% Jogo'].mean():.1f}% da carga semanal correspondeu ao jogo.")




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: PERFIL DE REFERÊNCIA INDIVIDUAL (Z-Score pessoal)
        # ═══════════════════════════════════════════════════════════════════════════════

            METS_PERFIL = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
                "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
                "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
            ]
            mets_disp = [m for m in METS_PERFIL if m in df.columns]

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

            # Tentar ler folha de Lesões
            try:
                df_les = pd.read_excel(excel_path, sheet_name="Lesões", engine="openpyxl")
                # Normalizar coluna Jogador
                for _alias in ["Jogador","Player","Atleta","Nome","Name"]:
                    if _alias in df_les.columns:
                        if _alias != "Jogador":
                            df_les = df_les.rename(columns={_alias: "Jogador"})
                        break
                if "Jogador" not in df_les.columns and len(df_les.columns) > 0:
                    df_les["Jogador"] = "Desconhecido"
                df_les.columns = [str(c).strip() for c in df_les.columns]
                tem_folha_lesoes = True
            except Exception:
                tem_folha_lesoes = False
                df_les = pd.DataFrame()

            if not tem_folha_lesoes:
                st.warning("""
        ### ⚠️ Folha 'Lesões' não encontrada no Excel

        Para usar esta funcionalidade, adiciona uma folha chamada **Lesões** ao teu ficheiro Excel com estas colunas:

        | Jogador | Data Lesão | Data Retorno | Tipo de Lesão | Zona Corporal | Diagnóstico | Dias de Paragem | Estado |
        |---|---|---|---|---|---|---|---|
        | Paulino | 12/01/2025 | 25/01/2025 | Muscular | Isquiotibial | Elongação grau I | 13 | Recuperado |
        | ... | | | | | | | Ativo |

        O campo **Estado** deve ser: `Ativo` (ainda lesionado) ou `Recuperado`.

        Depois de criar a folha, clica em **🔄 Atualizar Dados**.
                """)

                # Mesmo sem folha de lesões, mostrar análise de ausências (sessões em falta)
                st.divider()
                st.markdown('<p class="section-title">📊 Análise de Participação nos Treinos</p>', unsafe_allow_html=True)
                st.caption("Jogadores com menos sessões que a média podem indicar períodos de indisponibilidade")

                if "Microciclo (Nr)" in df.columns:
                    mc_disp = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
                    mc_les = st.selectbox("Microciclo a analisar", mc_disp, key="les_mc")
                    df_mc_les = df[df["Microciclo (Nr)"] == mc_les]
                    todos_jogs = sorted(df["Jogador"].dropna().unique())

                    participacao = []
                    max_sess = df_mc_les.groupby("Jogador").size().max() if not df_mc_les.empty else 0
                    for jog in todos_jogs:
                        sess = len(df_mc_les[df_mc_les["Jogador"] == jog])
                        pos  = df[df["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df.columns and not df[df["Jogador"] == jog].empty else "—"
                        pct  = sess / max_sess * 100 if max_sess > 0 else 0
                        participacao.append({"Jogador": jog, "Posição": pos, "Sessões": sess,
                                              "% Participação": round(pct, 0),
                                              "Estado": "⚠️ Ausente/Indisponível" if pct < 50 else "✅ Presente"})

                    df_part = pd.DataFrame(participacao).sort_values("% Participação")
                    fig_part = go.Figure(go.Bar(
                        y=df_part["Jogador"], x=df_part["% Participação"],
                        orientation="h",
                        marker_color=["#e74c3c" if v < 50 else "#f39c12" if v < 80 else "#2ecc71"
                                       for v in df_part["% Participação"]],
                        text=[f"{int(v)}%" for v in df_part["% Participação"]],
                        textposition="outside",
                    ))
                    fig_part.add_vline(x=80, line_dash="dash", line_color="#f39c12", annotation_text="80%")
                    fig_part.add_vline(x=50, line_dash="dash", line_color="#e74c3c", annotation_text="50%")
                    fig_part.update_layout(
                        xaxis=dict(range=[0, 115], title="% Participação"),
                        height=max(300, len(df_part)*40),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_part, use_container_width=True)
                    ausentes = df_part[df_part["% Participação"] < 50]["Jogador"].tolist()
                    if ausentes:
                        st.warning(f"⚠️ **Possível indisponibilidade** no MC {int(mc_les)}: {', '.join(ausentes)} (menos de 50% das sessões)")

            # ── Com folha de Lesões ────────────────────────────────────────────────────
            # Normalizar colunas esperadas
            col_jog    = next((c for c in df_les.columns if "jogador" in c.lower()), None)
            col_data_l = next((c for c in df_les.columns if "data" in c.lower() and "lesão" in c.lower()), None) or                  next((c for c in df_les.columns if "data" in c.lower() and "inicio" in c.lower()), None)
            col_retorno = next((c for c in df_les.columns if "retorno" in c.lower() or "regresso" in c.lower()), None)
            col_dias    = next((c for c in df_les.columns if "dias" in c.lower()), None)
            col_tipo    = next((c for c in df_les.columns if "tipo" in c.lower()), None)
            col_zona    = next((c for c in df_les.columns if "zona" in c.lower() or "local" in c.lower()), None)
            col_estado  = next((c for c in df_les.columns if "estado" in c.lower() or "situação" in c.lower()), None)

            if col_jog is None:
                st.error("Coluna 'Jogador' não encontrada na folha Lesões.")

            if col_data_l:
                df_les[col_data_l] = pd.to_datetime(df_les[col_data_l], errors="coerce")
            if col_retorno:
                df_les[col_retorno] = pd.to_datetime(df_les[col_retorno], errors="coerce")

            tab_l1, tab_l2, tab_l3 = st.tabs(["📋 Registo de Lesões", "📈 Correlação com Carga", "📊 Epidemiologia"])

            with tab_l1:
                # Lesões ativas
                st.markdown('<p class="section-title">🩹 Lesões Ativas</p>', unsafe_allow_html=True)
                if col_estado:
                    ativas = df_les[df_les[col_estado].astype(str).str.lower().isin(["ativo","activo","sim","yes","1","true","ativa","activa"])]
                else:
                    ativas = df_les[df_les[col_retorno].isna()] if col_retorno else df_les

                if not ativas.empty:
                    for _, row in ativas.iterrows():
                        jog = row[col_jog]
                        tipo = row[col_tipo] if col_tipo else "—"
                        zona = row[col_zona] if col_zona else "—"
                        dias = row[col_dias] if col_dias else "—"
                        data_l = row[col_data_l].strftime("%d/%m/%Y") if col_data_l and pd.notna(row[col_data_l]) else "—"
                        st.markdown(
                            f'<div style="background:#7b1d1d33;border-left:4px solid #e74c3c;border-radius:8px;padding:12px;margin:6px 0">'
                            f'🩹 <b>{jog}</b> — {tipo} ({zona}) · desde {data_l} · {dias} dias de paragem'
                            f'</div>', unsafe_allow_html=True
                        )
                else:
                    st.success("✅ Sem lesões ativas no momento.")

                st.divider()
                st.markdown('<p class="section-title">📋 Histórico Completo</p>', unsafe_allow_html=True)
                st.dataframe(df_les, use_container_width=True)

                # Exportar
                linhas_les = "".join([
                    f'<tr>{"".join(f"<td>{row[c]}</td>" for c in df_les.columns)}</tr>'
                    for _, row in df_les.iterrows()
                ])
                headers_les = "".join([f"<th>{c}</th>" for c in df_les.columns])
                html_les = gerar_pdf_html(f"""
        <h1>Relatório de Lesões</h1>
        <table><tr>{headers_les}</tr>{linhas_les}</table>
        """, "Relatorio_Lesoes.html")
                botao_download_html(html_les, "Relatorio_Lesoes.html", "📥 Exportar Registo de Lesões")

            with tab_l2:
                st.markdown('<p class="section-title">⚡ Carga nas 4 Semanas Antes da Lesão</p>', unsafe_allow_html=True)
                if col_data_l is None:
                    st.warning("Coluna de data de lesão não encontrada.")
                else:
                    lesoes_com_data = df_les.dropna(subset=[col_data_l])
                    if lesoes_com_data.empty:
                        st.info("Sem lesões com data registada.")
                    else:
                        jog_sel_les = st.selectbox("Jogador", lesoes_com_data[col_jog].unique(), key="les_jog")
                        lesoes_jog = lesoes_com_data[lesoes_com_data[col_jog] == jog_sel_les]
                        data_les_sel = st.selectbox("Lesão (data)", lesoes_jog[col_data_l].dt.strftime("%d/%m/%Y").tolist(), key="les_data")
                        data_les_dt = pd.to_datetime(data_les_sel, format="%d/%m/%Y")

                        df_antes = df[
                            (df["Jogador"] == jog_sel_les) &
                            (df["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                            (df["Data"] < data_les_dt)
                        ].sort_values("Data")

                        if df_antes.empty:
                            st.info("Sem dados de carga nas 4 semanas anteriores à lesão.")
                        else:
                            fig_les_carga = go.Figure()
                            if "Carga Interna" in df_antes.columns:
                                fig_les_carga.add_trace(go.Bar(
                                    x=df_antes["Data"], y=df_antes["Carga Interna"],
                                    name="Carga Interna", marker_color="#e63946",
                                ))
                            if "ACWR" not in df_antes.columns:
                                df_jog_acwr = calcular_acwr(df[df["Jogador"] == jog_sel_les], jog_sel_les)
                                df_jog_acwr = df_jog_acwr[
                                    (df_jog_acwr["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                                    (df_jog_acwr["Data"] < data_les_dt)
                                ]
                                if "ACWR" in df_jog_acwr.columns:
                                    fig_les_carga.add_trace(go.Scatter(
                                        x=df_jog_acwr["Data"], y=df_jog_acwr["ACWR"] * 100,
                                        mode="lines+markers", name="ACWR ×100", line_color="#f39c12",
                                        yaxis="y2",
                                    ))
                            fig_les_carga.add_vline(x=data_les_dt, line_dash="dash", line_color="#e74c3c",
                                                     annotation_text="Lesão", annotation_position="top right")
                            fig_les_carga.update_layout(
                                height=360,
                                yaxis=dict(title="Carga Interna"),
                                yaxis2=dict(title="ACWR ×100", overlaying="y", side="right"),
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                            )
                            st.plotly_chart(fig_les_carga, use_container_width=True)

            with tab_l3:
                st.markdown('<p class="section-title">📊 Distribuição de Lesões por Tipo e Zona</p>', unsafe_allow_html=True)

                c1_e, c2_e = st.columns(2)
                if col_tipo and not df_les[col_tipo].isna().all():
                    with c1_e:
                        tipo_count = df_les[col_tipo].value_counts().reset_index()
                        tipo_count.columns = ["Tipo", "Nº"]
                        fig_tipo = px.pie(tipo_count, names="Tipo", values="Nº", hole=0.4,
                                           color_discrete_sequence=px.colors.qualitative.Bold)
                        fig_tipo.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=10))
                        st.plotly_chart(fig_tipo, use_container_width=True)

                if col_zona and not df_les[col_zona].isna().all():
                    with c2_e:
                        zona_count = df_les[col_zona].value_counts().reset_index()
                        zona_count.columns = ["Zona", "Nº"]
                        fig_zona = px.bar(zona_count, x="Nº", y="Zona", orientation="h",
                                           color="Nº", color_continuous_scale="Reds")
                        fig_zona.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                        st.plotly_chart(fig_zona, use_container_width=True)

                if col_dias and not df_les[col_dias].isna().all():
                    st.markdown('<p class="section-title">Dias de Paragem por Jogador</p>', unsafe_allow_html=True)
                    dias_jog = df_les.groupby(col_jog)[col_dias].sum().sort_values(ascending=False).reset_index()
                    dias_jog.columns = ["Jogador", "Total Dias"]
                    fig_dias_les = px.bar(dias_jog, x="Jogador", y="Total Dias",
                                           color="Total Dias", color_continuous_scale="Reds",
                                           text="Total Dias")
                    fig_dias_les.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                                paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                                                coloraxis_showscale=False, margin=dict(t=10))
                    st.plotly_chart(fig_dias_les, use_container_width=True)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: TREINO VS JOGO — % MÉTRICAS GPS
        # ═══════════════════════════════════════════════════════════════════════════════

    if _plan_idx == 1:

            METS_GPS = [
                "Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)",
                "Carga Interna", "PSE Sessão",
            ]
            mets_gps_disp = [m for m in METS_GPS if m in df.columns]

            if "Tipo" not in df.columns:
                st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com 'Treino' e 'Jogo'.")

            df_jogos_all   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
            df_treinos_all = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

            if df_jogos_all.empty:
                st.warning("Sem registos com Tipo = 'Jogo' encontrados.")

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)
            mc_tvj   = col_f1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="tvj_mc")
            modo_tvj = col_f2.radio("Modo", ["Por Jogador", "Equipa (média)"], key="tvj_modo")
            referencia_tvj = col_f3.radio("Referência de jogo", ["Média de todos os jogos", "Top 5 jogos mais exigentes", "Último jogo"], key="tvj_ref")

            st.divider()

            # Calcular referência de jogo
            def media_jogos(df_j, met, jogador=None):
                """Calcula a referência de jogo conforme opção selecionada."""
                sub = df_j if jogador is None else df_j[df_j["Jogador"] == jogador]
                if sub.empty or met not in sub.columns:
                    return np.nan
                if referencia_tvj == "Último jogo":
                    sub = sub.sort_values("Data").tail(1)
                elif referencia_tvj == "Top 5 jogos mais exigentes":
                    # Top 5 baseado na métrica selecionada (mais exigente = maior valor)
                    sub = sub.nlargest(5, met) if len(sub) >= 5 else sub
                # Média de todos os jogos: usa sub completo
                return sub[met].mean()

            df_treinos_mc = df_treinos_all[df_treinos_all["Microciclo (Nr)"] == mc_tvj]

            if df_treinos_mc.empty:
                st.warning(f"Sem sessões de treino no Microciclo {int(mc_tvj)}.")

            # ── MODO EQUIPA ───────────────────────────────────────────────────────────
            if modo_tvj == "Equipa (média)":

                # Média de cada métrica por dia MD nos treinos
                dias_md_ordem = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
                dias_presentes = [d for d in dias_md_ordem if d in df_treinos_mc["Dia MD"].values]                          if "Dia MD" in df_treinos_mc.columns else []

                # ── Cards de % total do microciclo vs jogo ────────────────────────────
                st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)

                n_cols = len(mets_gps_disp)
                cols_cards = st.columns(n_cols)
                for i, met in enumerate(mets_gps_disp):
                    # Média por sessão de treino (para comparar com um jogo individual)
                    media_treino = df_treinos_mc.groupby("Jogador")[met].mean().mean()
                    total_treino = df_treinos_mc[met].sum()
                    ref_jogo     = media_jogos(df_jogos_all, met)
                    if pd.isna(ref_jogo) or ref_jogo == 0:
                        pct = None
                    else:
                        pct = media_treino / ref_jogo * 100

                    if pct is None:
                        cor, emoji = "#555", "❓"
                    elif pct >= 150: cor, emoji = "#e74c3c", "🔴"
                    elif pct >= 100: cor, emoji = "#f39c12", "🟡"
                    elif pct >= 70:  cor, emoji = "#2ecc71", "🟢"
                    else:            cor, emoji = "#3498db", "🔵"

                    label = met.replace(" (m)","").replace(" (n)","")
                    # PSE: só faz sentido como média por sessão (não soma)
                    is_pse = met == "PSE Sessão"
                    agg_label = "Média/sessão" if is_pse else "Média treino"
                    cols_cards[i].markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#ccc;margin-bottom:4px">{label}</div>'
                        f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                        f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                        f'<div style="font-size:0.65rem;color:#aaa">{agg_label} / {"último jogo" if referencia_tvj=="Último jogo" else "top 5" if "Top 5" in referencia_tvj else "média jogos"}</div>'
                        f'<div style="font-size:0.75rem;color:#eee;margin-top:4px">'
                        f'Treino: {media_treino:,.1f if is_pse else f"{media_treino:,.0f}"} | Ref.: {ref_jogo:,.1f if is_pse else f"{ref_jogo:,.0f}"}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # ── Gráfico por Dia MD — todas as métricas ─────────────────────────────
                if dias_presentes:
                    st.markdown('<p class="section-title">% por Dia do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
                    met_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_eq_met")

                    ref_val = media_jogos(df_jogos_all, met_sel)
                    dias_vals, dias_pcts, dias_abs = [], [], []

                    for dia in dias_presentes:
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        # Média por jogador primeiro, depois média do grupo
                        val = sub_dia.groupby("Jogador")[met_sel].mean().mean()
                        dias_vals.append(dia)
                        dias_abs.append(round(val, 1))
                        dias_pcts.append(round(val / ref_val * 100, 1) if (ref_val and ref_val > 0) else 0)

                    cores_dias = []
                    for p in dias_pcts:
                        if p >= 300:   cores_dias.append("#e74c3c")
                        elif p >= 200: cores_dias.append("#f39c12")
                        elif p >= 100: cores_dias.append("#2ecc71")
                        else:          cores_dias.append("#3498db")

                    fig_dias_tvj = go.Figure()
                    fig_dias_tvj.add_trace(go.Bar(
                        x=dias_vals, y=dias_pcts,
                        marker_color=cores_dias,
                        text=[f"{p:.0f}%" for p in dias_pcts],
                        textposition="outside",
                        name="% vs Jogo",
                    ))
                    fig_dias_tvj.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                            annotation_text="100% = equivalente ao jogo")
                    fig_dias_tvj.add_hline(y=200, line_dash="dot", line_color="#f39c12",
                                            annotation_text="200%")
                    fig_dias_tvj.update_layout(
                        yaxis=dict(title="% vs Média de Jogos", range=[0, max(dias_pcts + [110]) * 1.15]),
                        xaxis_title="Dia MD", height=380,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                    )
                    st.plotly_chart(fig_dias_tvj, use_container_width=True)

                    # Tabela dia a dia
                    df_tabela_dias = pd.DataFrame({
                        "Dia MD": dias_vals,
                        met_sel: dias_abs,
                        "Ref. Jogo": [round(ref_val, 1)] * len(dias_vals),
                        "% vs Jogo": [f"{p:.0f}%" for p in dias_pcts],
                    })
                    st.dataframe(df_tabela_dias.set_index("Dia MD"), use_container_width=True)

                st.divider()

                # ── Radar — todas as métricas por dia MD ─────────────────────────────
                if dias_presentes and len(dias_presentes) >= 2:
                    st.markdown('<p class="section-title">Radar — % vs Jogo por Dia MD (todas as métricas)</p>', unsafe_allow_html=True)
                    dias_radar_sel = st.multiselect("Dias a comparar", dias_presentes,
                                                     default=dias_presentes[:min(3, len(dias_presentes))],
                                                     key="tvj_radar_dias")
                    fig_radar_tvj = go.Figure()
                    cores_r = ["#e63946","#457b9d","#2ecc71","#f39c12","#9b59b6","#1abc9c"]
                    labels_r = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]

                    for k, dia in enumerate(dias_radar_sel):
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        vals_r = []
                        for met in mets_gps_disp:
                            ref = media_jogos(df_jogos_all, met)
                            val = sub_dia.groupby("Jogador")[met].mean().mean()
                            vals_r.append(round(val / ref * 100, 1) if (ref and ref > 0 and pd.notna(val)) else 0)
                        vals_r_closed = vals_r + [vals_r[0]]
                        labels_closed = labels_r + [labels_r[0]]
                        fig_radar_tvj.add_trace(go.Scatterpolar(
                            r=vals_r_closed, theta=labels_closed,
                            fill="toself", name=dia,
                            line_color=cores_r[k % len(cores_r)], opacity=0.75,
                        ))
                    # Jogo = 100% linha de referência
                    fig_radar_tvj.add_trace(go.Scatterpolar(
                        r=[100] * (len(labels_r) + 1), theta=labels_r + [labels_r[0]],
                        mode="lines", name="⚽ Jogo (100%)",
                        line=dict(color="white", dash="dash", width=2),
                    ))
                    fig_radar_tvj.update_layout(
                        polar=dict(radialaxis=dict(visible=True, ticksuffix="%")),
                        height=460, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_tvj, use_container_width=True)

                st.divider()

                # ── Heatmap — dia MD × métrica ────────────────────────────────────────
                st.markdown('<p class="section-title">Heatmap — % vs Jogo (Dia MD × Métrica)</p>', unsafe_allow_html=True)
                if dias_presentes:
                    heat_data, heat_text = [], []
                    for dia in dias_presentes:
                        row_vals, row_text = [], []
                        sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                        for met in mets_gps_disp:
                            ref = media_jogos(df_jogos_all, met)
                            val = sub_dia.groupby("Jogador")[met].mean().mean()
                            p = round(val / ref * 100, 0) if (ref and ref > 0 and pd.notna(val)) else 0
                            row_vals.append(p)
                            row_text.append(f"{p:.0f}%")
                        heat_data.append(row_vals)
                        heat_text.append(row_text)

                    labels_heat = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]
                    fig_heat_tvj = go.Figure(go.Heatmap(
                        z=heat_data, x=labels_heat, y=dias_presentes,
                        text=heat_text, texttemplate="%{text}",
                        colorscale="RdYlGn", zmid=100,
                        colorbar=dict(title="% Jogo", ticksuffix="%"),
                    ))
                    fig_heat_tvj.update_layout(
                        height=max(250, len(dias_presentes)*65),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    )
                    st.plotly_chart(fig_heat_tvj, use_container_width=True)

                # ── Exportar ──────────────────────────────────────────────────────────
                st.divider()
                linhas_export = ""
                for met in mets_gps_disp:
                    total_t = df_treinos_mc[met].sum()
                    ref_j   = media_jogos(df_jogos_all, met)
                    pct_e   = f"{total_t/ref_j*100:.0f}%" if (ref_j and ref_j > 0) else "—"
                    linhas_export += f"<tr><td>{met}</td><td>{total_t:,.0f}</td><td>{ref_j:,.0f}</td><td><b>{pct_e}</b></td></tr>"
                html_tvj = gerar_pdf_html(f"""
        <h1>Treino vs Jogo — MC {int(mc_tvj)}</h1>
        <p><b>Referência:</b> {referencia_tvj}</p>
        <table><tr><th>Métrica</th><th>Total Treino</th><th>Ref. Jogo</th><th>% vs Jogo</th></tr>
        {linhas_export}</table>
        """, f"TreinoVsJogo_MC{int(mc_tvj)}.html")
                botao_download_html(html_tvj, f"TreinoVsJogo_MC{int(mc_tvj)}.html", "📥 Exportar Relatório (PDF)")

            # ── MODO JOGADOR ──────────────────────────────────────────────────────────
            else:
                jog_tvj = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="tvj_jog")

                df_t_jog = df_treinos_mc[df_treinos_mc["Jogador"] == jog_tvj]
                df_j_jog = df_jogos_all[df_jogos_all["Jogador"] == jog_tvj]

                if df_t_jog.empty:
                    st.warning(f"Sem treinos para {jog_tvj} no MC {int(mc_tvj)}.")

                # Cards
                st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
                cols_jog = st.columns(len(mets_gps_disp))
                for i, met in enumerate(mets_gps_disp):
                    total_t = df_t_jog[met].sum()
                    ref_j   = media_jogos(df_j_jog, met)
                    pct     = total_t / ref_j * 100 if (ref_j and ref_j > 0) else None

                    if pct is None: cor, emoji = "#555", "❓"
                    elif pct >= 300: cor, emoji = "#e74c3c", "🔴"
                    elif pct >= 200: cor, emoji = "#f39c12", "🟡"
                    elif pct >= 100: cor, emoji = "#2ecc71", "🟢"
                    else:            cor, emoji = "#3498db", "🔵"

                    label = met.replace(" (m)","").replace(" (n)","")
                    cols_jog[i].markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{label}</div>'
                        f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                        f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                        f'<div style="font-size:0.7rem;color:#aaa">treino / jogo</div>'
                        f'<div style="font-size:0.75rem;color:#eee;margin-top:2px">'
                        f'T: {total_t:,.0f} | J: {ref_j:,.0f}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # Por Dia MD
                if "Dia MD" in df_t_jog.columns:
                    st.markdown('<p class="section-title">% por Dia do Microciclo</p>', unsafe_allow_html=True)
                    met_jog_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_jog_met")
                    ref_jog_val = media_jogos(df_j_jog, met_jog_sel)

                    dias_jog_ord = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
                    dias_jog_pres = [d for d in dias_jog_ord if d in df_t_jog["Dia MD"].values]

                    pcts_jog, vals_jog = [], []
                    for dia in dias_jog_pres:
                        val = df_t_jog[df_t_jog["Dia MD"] == dia][met_jog_sel].mean()
                        vals_jog.append(round(val, 1))
                        pcts_jog.append(round(val / ref_jog_val * 100, 1) if (ref_jog_val and ref_jog_val > 0) else 0)

                    cores_jog_dias = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db" for p in pcts_jog]

                    fig_jog_dias = go.Figure(go.Bar(
                        x=dias_jog_pres, y=pcts_jog,
                        marker_color=cores_jog_dias,
                        text=[f"{p:.0f}%" for p in pcts_jog],
                        textposition="outside",
                    ))
                    fig_jog_dias.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                            annotation_text="100% = equivalente ao jogo")
                    fig_jog_dias.update_layout(
                        yaxis=dict(title="% vs Jogo", range=[0, max(pcts_jog + [110]) * 1.15]),
                        height=360, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                        showlegend=False, margin=dict(t=20),
                    )
                    st.plotly_chart(fig_jog_dias, use_container_width=True)

                # Comparação entre jogadores da mesma posição
                st.divider()
                st.markdown('<p class="section-title">Comparação com Jogadores da Mesma Posição</p>', unsafe_allow_html=True)
                met_pos_tvj = st.selectbox("Métrica", mets_gps_disp, key="tvj_pos_met")

                pos_jog_tvj = df[df["Jogador"] == jog_tvj]["Posição"].iloc[-1] if "Posição" in df.columns else None
                if pos_jog_tvj:
                    jogs_pos = df[df["Posição"] == pos_jog_tvj]["Jogador"].dropna().unique()
                    rows_pos_tvj = []
                    for jog_p in jogs_pos:
                        t_p = df_treinos_mc[df_treinos_mc["Jogador"] == jog_p]
                        j_p = df_jogos_all[df_jogos_all["Jogador"] == jog_p]
                        if t_p.empty: continue
                        total_p = t_p[met_pos_tvj].sum()
                        ref_p   = media_jogos(j_p, met_pos_tvj)
                        pct_p   = total_p / ref_p * 100 if (ref_p and ref_p > 0) else None
                        rows_pos_tvj.append({"Jogador": jog_p, met_pos_tvj: round(total_p,1),
                                              "Ref. Jogo": round(ref_p,1) if ref_p else 0,
                                              "% vs Jogo": round(pct_p,1) if pct_p else 0})

                    if rows_pos_tvj:
                        df_pos_tvj = pd.DataFrame(rows_pos_tvj).sort_values("% vs Jogo", ascending=True)
                        cores_pos_tvj = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db"
                                          for p in df_pos_tvj["% vs Jogo"]]
                        fig_pos_tvj = go.Figure(go.Bar(
                            y=df_pos_tvj["Jogador"], x=df_pos_tvj["% vs Jogo"],
                            orientation="h", marker_color=cores_pos_tvj,
                            text=[f"{p:.0f}%" for p in df_pos_tvj["% vs Jogo"]],
                            textposition="outside",
                        ))
                        fig_pos_tvj.add_vline(x=100, line_dash="dash", line_color="#2ecc71",
                                               annotation_text="100% = jogo")
                        fig_pos_tvj.update_layout(
                            xaxis_title="% vs Média de Jogos", height=max(250, len(df_pos_tvj)*50),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                            font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                        )
                        # Destaque o jogador selecionado
                        idx_jog = df_pos_tvj["Jogador"].tolist().index(jog_tvj) if jog_tvj in df_pos_tvj["Jogador"].tolist() else -1
                        if idx_jog >= 0:
                            cores_pos_tvj[idx_jog] = "#e63946"
                        st.plotly_chart(fig_pos_tvj, use_container_width=True)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: MONOTONIA & STRAIN (FOSTER)
        # ═══════════════════════════════════════════════════════════════════════════════

    if _plan_idx == 2:
        # Interpretação no topo
        st.info("📚 **Referência:** Borresen & Lambert (2009) · Clemente et al. (2014) — Distância: 70–90% do jogo/sessão · HSR: 30–60% · Sprint: 15–40% · CI: 60–90%")

        # ════════════════════════════════════════════════════════════════════
        # PLANEADO VS REALIZADO — Carga semanal como % do jogo de referência
        # ════════════════════════════════════════════════════════════════════
        st.markdown("""
        **Lógica:** defines a carga semanal planeada como percentagem de um jogo de referência.
        Por exemplo: CI = 300%, HSR = 250%, Sprint = 100%, Acc/Dcc = 350%.
        Compara depois com o que foi realmente executado no microciclo.
        """)
        st.caption("Baseado na lógica de periodização em relação à exigência do jogo (Borresen & Lambert, 2009)")

        # Planeado vs Realizado — apenas métricas de carga externa relevantes
        METS_PVR_FIXED = ["Carga Interna", "Distância Total (m)", "HSR (m)",
                           "Sprint (m)", "Acc (n)", "Dcc (n)"]
        mets_pvr_disp = [m for m in METS_PVR_FIXED if m in df.columns and df[m].notna().any()]
        # Se nenhuma das fixas existir, usar todas as numéricas como fallback
        if not mets_pvr_disp:
            mets_pvr_disp = get_mets_gps(df_treinos_pvr_all if "df_treinos_pvr_all" in dir() else df)

        if "Tipo" not in df.columns or "Microciclo (Nr)" not in df.columns:
            st.error("Colunas 'Tipo' e 'Microciclo (Nr)' necessárias.")

        if len(mets_pvr_disp) == 0:
            st.error("Nenhuma das métricas GPS encontrada no Excel.")

        # Separar jogos e treinos
        df_jogos_pvr   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy() if "Tipo" in df.columns else pd.DataFrame()
        df_treinos_pvr_all = df[df["Tipo"].str.strip().str.lower() == "treino"].copy() if "Tipo" in df.columns else df

        col_p1, col_p2, col_p3 = st.columns(3)
        mcs_pvr = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
        mc_pvr = col_p1.selectbox("Microciclo a analisar", mcs_pvr, key="pvr_mc")

        ref_pvr = col_p2.radio(
            "Jogo de referência",
            ["Média de todos os jogos", "Top 5 jogos mais exigentes", "Último jogo"],
            key="pvr_ref_jogo"
        )

        df_mc_treinos = df_treinos_pvr_all[df_treinos_pvr_all["Microciclo (Nr)"] == mc_pvr]

        if df_mc_treinos.empty:
            st.warning(f"Sem treinos no Microciclo {int(mc_pvr)}.")

        # ── Calcular referência do jogo ───────────────────────────────────
        def get_ref_jogo_pvr(met):
            if df_jogos_pvr.empty or met not in df_jogos_pvr.columns:
                return np.nan
            if ref_pvr == "Último jogo":
                sub = df_jogos_pvr.sort_values("Data").tail(1) if "Data" in df_jogos_pvr.columns else df_jogos_pvr
            elif ref_pvr == "Top 5 jogos mais exigentes":
                sub = df_jogos_pvr.nlargest(5, met) if len(df_jogos_pvr) >= 5 else df_jogos_pvr
            else:
                sub = df_jogos_pvr
            return sub[met].mean()

        # ── Totais reais do microciclo (soma por jogador, depois média) ───
        def get_real_mc(met):
            """Soma total do microciclo por jogador (média do grupo)."""
            if met not in df_mc_treinos.columns:
                return np.nan
            if met == "PSE Sessão":
                # PSE: média por sessão, não soma
                return df_mc_treinos[met].mean()
            return df_mc_treinos.groupby("Jogador")[met].sum().mean()

        st.divider()
        st.markdown('<p class="section-title">🎯 Definir Carga Planeada (% do Jogo de Referência)</p>', unsafe_allow_html=True)
        st.caption("Define a percentagem-alvo para cada métrica. Compara depois com o realizado.")

        # Cards de input — um por métrica
        cols_plan = st.columns(len(mets_pvr_disp))
        planeado_pct = {}
        defaults_pct = {
            "Carga Interna": 300.0, "Distância Total (m)": 280.0,
            "HSR (m)": 250.0, "Sprint (m)": 100.0,
            "Acc (n)": 350.0, "Dcc (n)": 350.0,
        }

        for i, met in enumerate(mets_pvr_disp):
            ref_val = get_ref_jogo_pvr(met)
            ref_str = f"Ref. jogo: {ref_val:,.0f}" if not pd.isna(ref_val) else "Ref. jogo: sem dados"
            default = defaults_pct.get(met, 200.0)
            pct_input = cols_plan[i].number_input(
                f"{met.split('(')[0].strip()} (%)",
                min_value=0.0, max_value=1000.0,
                value=default, step=10.0,
                key=f"pvr_pct_{i}",
                help=f"% do jogo de referência · {ref_str}"
            )
            planeado_pct[met] = pct_input
            # Show reference
            cols_plan[i].caption(ref_str)

        st.divider()

        # ── Gráfico principal: Planeado vs Realizado ──────────────────────
        st.markdown('<p class="section-title">📊 Planeado vs Realizado — Microciclo vs Jogo</p>', unsafe_allow_html=True)

        rows_pvr = []
        for met in mets_pvr_disp:
            ref_val    = get_ref_jogo_pvr(met)
            plan_abs   = ref_val * planeado_pct[met] / 100 if not pd.isna(ref_val) else np.nan
            real_val   = get_real_mc(met)
            pct_real   = (real_val / ref_val * 100) if (not pd.isna(ref_val) and ref_val > 0 and not pd.isna(real_val)) else np.nan
            exec_rate  = (real_val / plan_abs * 100) if (not pd.isna(plan_abs) and plan_abs > 0 and not pd.isna(real_val)) else np.nan

            rows_pvr.append({
                "Métrica": met.split("(")[0].strip(),
                "% Planeado": round(planeado_pct[met], 0),
                "% Real vs Jogo": round(pct_real, 1) if not pd.isna(pct_real) else np.nan,
                "% Execução": round(exec_rate, 1) if not pd.isna(exec_rate) else np.nan,
                "Valor Planeado": round(plan_abs, 0) if not pd.isna(plan_abs) else np.nan,
                "Valor Real": round(real_val, 0) if not pd.isna(real_val) else np.nan,
                "Ref. Jogo": round(ref_val, 0) if not pd.isna(ref_val) else np.nan,
                "_met": met,
            })

        if rows_pvr:
            df_pvr2 = pd.DataFrame(rows_pvr)

            # Cards de % execução por métrica
            cols_cards_pvr2 = st.columns(len(rows_pvr))
            for i, row in enumerate(rows_pvr):
                exec_p = row["% Execução"]
                plan_p = row["% Planeado"]
                real_p = row["% Real vs Jogo"]
                if pd.isna(exec_p):     cor2 = "#555"; badge = "—"
                elif exec_p >= 110:     cor2 = "#e74c3c"; badge = f"{exec_p:.0f}% 🔴"
                elif exec_p >= 95:      cor2 = "#2ecc71"; badge = f"{exec_p:.0f}% 🟢"
                elif exec_p >= 80:      cor2 = "#f39c12"; badge = f"{exec_p:.0f}% 🟡"
                else:                   cor2 = "#3498db"; badge = f"{exec_p:.0f}% 🔵"

                cols_cards_pvr2[i].markdown(
                    f'<div style="background:{cor2}18;border:2px solid {cor2};border-radius:12px;'
                    f'padding:12px 8px;text-align:center">'
                    f'<div style="font-size:0.72rem;font-weight:700;color:#ccc;margin-bottom:4px">{row["Métrica"]}</div>'
                    f'<div style="font-size:1.6rem;font-weight:900;color:{cor2}">{badge}</div>'
                    f'<div style="font-size:0.62rem;color:#888;margin-top:4px">Plan: {plan_p:.0f}% jogo</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                val_r_str = f"{int(row['Valor Real']):,}" if not pd.isna(row["Valor Real"]) else "—"
                val_p_str = f"{int(row['Valor Planeado']):,}" if not pd.isna(row["Valor Planeado"]) else "—"
                cols_cards_pvr2[i].caption(f"Real: {val_r_str} | Plan: {val_p_str}")
            st.divider()

            # Gráfico de barras — Plan vs Real como % do jogo
            fig_pvr2 = go.Figure()
            labels2 = df_pvr2["Métrica"].tolist()
            fig_pvr2.add_trace(go.Bar(
                x=labels2, y=df_pvr2["% Planeado"],
                name="🎯 Planeado (%)", marker_color="#457b9d", opacity=0.8,
            ))
            fig_pvr2.add_trace(go.Scatter(
                x=labels2, y=df_pvr2["% Real vs Jogo"],
                name="✅ Realizado (% do jogo)",
                mode="lines+markers+text",
                text=df_pvr2["% Real vs Jogo"].apply(lambda v: f"{v:.0f}%" if not pd.isna(v) else "—"),
                textposition="top center",
                textfont=dict(size=11, color="white"),
                line=dict(color="#e63946", width=3),
                marker=dict(size=12, color="#e63946", line=dict(width=2, color="white")),
            ))
            fig_pvr2.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                                annotation_text="= 1 Jogo (100%)")
            fig_pvr2.update_layout(
                height=420, yaxis_title="% do Jogo de Referência",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_pvr2, use_container_width=True)
            st.caption(f"Barras azuis = % planeada · Linha vermelha = % real atingida · Tudo expresso em % do jogo de referência ({ref_pvr})")

            st.divider()

            # ── Análise por jogador ───────────────────────────────────────
            st.markdown('<p class="section-title">👥 Carga Real por Jogador vs Jogo de Referência</p>', unsafe_allow_html=True)
            met_jog_pvr = st.selectbox("Métrica", mets_pvr_disp, key="pvr_met_jog")
            ref_jog_val = get_ref_jogo_pvr(met_jog_pvr)
            plan_pct_jog = planeado_pct.get(met_jog_pvr, 200)
            plan_abs_jog = ref_jog_val * plan_pct_jog / 100 if not pd.isna(ref_jog_val) else np.nan

            if met_jog_pvr in df_mc_treinos.columns:
                if met_jog_pvr == "PSE Sessão":
                    df_jog_pvr2 = df_mc_treinos.groupby("Jogador")[met_jog_pvr].mean().reset_index()
                else:
                    df_jog_pvr2 = df_mc_treinos.groupby("Jogador")[met_jog_pvr].sum().reset_index()
                df_jog_pvr2.columns = ["Jogador", "Real"]
                df_jog_pvr2["% vs Jogo"] = (df_jog_pvr2["Real"] / ref_jog_val * 100).round(1) if not pd.isna(ref_jog_val) else np.nan
                df_jog_pvr2["% Execução"] = (df_jog_pvr2["Real"] / plan_abs_jog * 100).round(1) if not pd.isna(plan_abs_jog) else np.nan
                df_jog_pvr2 = df_jog_pvr2.sort_values("% vs Jogo", ascending=False)

                cores_j2 = []
                for v in df_jog_pvr2["% Execução"].fillna(0):
                    if v >= 110:   cores_j2.append("#e74c3c")
                    elif v >= 95:  cores_j2.append("#2ecc71")
                    elif v >= 80:  cores_j2.append("#f39c12")
                    else:          cores_j2.append("#3498db")

                fig_jog_pvr2 = go.Figure()
                fig_jog_pvr2.add_trace(go.Bar(
                    x=df_jog_pvr2["Jogador"], y=df_jog_pvr2["% vs Jogo"],
                    marker_color=cores_j2,
                    text=df_jog_pvr2["% vs Jogo"].apply(lambda v: f"{v:.0f}%" if not pd.isna(v) else "—"),
                    textposition="outside", name="% vs Jogo",
                ))
                if not pd.isna(plan_pct_jog):
                    fig_jog_pvr2.add_hline(y=plan_pct_jog, line_dash="dash", line_color="#f39c12",
                                            annotation_text=f"Planeado {plan_pct_jog:.0f}%")
                fig_jog_pvr2.add_hline(y=100, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                                        annotation_text="100% = 1 Jogo")
                fig_jog_pvr2.update_layout(
                    height=360, yaxis_title="% do Jogo de Referência",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=20),
                )
                st.plotly_chart(fig_jog_pvr2, use_container_width=True)

                st.divider()
                # Tabela resumo
                if not pd.isna(ref_jog_val):
                    st.caption(f"Jogo de referência ({ref_pvr}): **{ref_jog_val:,.0f}** · Planeado: **{plan_pct_jog:.0f}%** = {plan_abs_jog:,.0f}")
                st.dataframe(df_jog_pvr2.set_index("Jogador").rename(columns={"Real": met_jog_pvr}), use_container_width=True)

            # ── Conclusões automáticas ─────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
            for row in rows_pvr:
                exec_p = row["% Execução"]
                if pd.isna(exec_p): continue
                if exec_p >= 110:
                    st.markdown(f"🔴 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — acima do objetivo. Reduzir neste microciclo.")
                elif exec_p >= 95:
                    st.markdown(f"🟢 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — dentro do objetivo.")
                elif exec_p >= 80:
                    st.markdown(f"🟡 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — ligeiramente abaixo.")
                else:
                    st.markdown(f"🔵 **{row['Métrica']}**: executado {exec_p:.0f}% do planeado — abaixo do objetivo. Verificar ausências ou gestão de carga.")


    if _plan_idx == 3:
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

    if _plan_idx == 4:
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
