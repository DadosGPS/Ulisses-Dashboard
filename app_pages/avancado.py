"""LoadMonitorSystem — Página Avancado"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.dados import get_mets_gps, carregar_exercicios
from utils.calculos import calcular_acwr, zscore_serie
from utils.ui import lm_header, botao_download_html, gerar_pdf_html

def render(df, excel_path, **kwargs):
    _lm_user = kwargs.get("lm_user", {})
    _lm_plano = _lm_user.get("plano", "free")
    _lm_nome = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")
    lm_header("Análise Avançada", "Z-Score e outras análises", "Avançado")
    tab_av = st.tabs(["📐 Z-Score e Outras Análises"])

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

    with tab_av[0]:

        METRICAS_ZSCORE_DEFAULT = [
            "Distância Total (m)", "HSR (m)", "Sprint (m)",
            "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
            "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
        ]
        _mp = st.session_state.get("lm_helpers", {}).get("metricas_personalizaveis")
        if _mp:
            metricas_disp = _mp(df, METRICAS_ZSCORE_DEFAULT, "zscore", "Personalizar métricas — Z-Score")
        else:
            metricas_disp = [m for m in METRICAS_ZSCORE_DEFAULT if m in df.columns]

        def zscore_serie(serie: pd.Series) -> pd.Series:
            mu, sigma = serie.mean(), serie.std()
            if sigma == 0:
                return pd.Series([0.0] * len(serie), index=serie.index)
            return (serie - mu) / sigma

        def cor_zscore(z):
            if z > 2:    return "#e74c3c"
            if z > 1:    return "#f39c12"
            if z >= -1:  return "#2ecc71"
            if z >= -2:  return "#3498db"
            return "#9b59b6"

        # ── Tabs ─────────────────────────────────────────────────────────────────
        tab1, tab2 = st.tabs(["👤 Jogador ao longo dos Microciclos", "📊 Comparação entre Jogadores da mesma Posição"])

        # ── TAB 1: Jogador ao longo dos microciclos ───────────────────────────────
        with tab1:
            st.markdown('<p class="section-title">Evolução do Z-Score do Jogador por Microciclo</p>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            jog_z  = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="z_jog")
            met_z  = col_b.selectbox("Métrica", metricas_disp, key="z_met1")

            df_jog_z = df[df["Jogador"] == jog_z].copy()
            # Dia MD já filtrado via df_f_dia na sidebar

            if met_z in df_jog_z.columns and df_jog_z[met_z].notna().sum() > 1:
                # Z-Score calculado sobre todos os dados do jogador
                df_jog_z = df_jog_z.dropna(subset=[met_z, "Microciclo (Nr)"]).copy()
                df_jog_z["Z-Score"] = zscore_serie(df_jog_z[met_z])

                # Média por microciclo
                mc_z = df_jog_z.groupby("Microciclo (Nr)").agg(
                    Z_medio=("Z-Score", "mean"),
                    Valor_medio=(met_z, "mean"),
                    n=("Z-Score", "count"),
                ).reset_index()
                mc_z.columns = ["Microciclo (Nr)", "Z-Score Médio", f"{met_z} Médio", "Sessões"]
                mc_z = mc_z.sort_values("Microciclo (Nr)")

                cores_z = [cor_zscore(z) for z in mc_z["Z-Score Médio"]]

                fig_z1 = go.Figure()
                fig_z1.add_trace(go.Bar(
                    x=mc_z["Microciclo (Nr)"].astype(str),
                    y=mc_z["Z-Score Médio"],
                    marker_color=cores_z,
                    text=mc_z["Z-Score Médio"].round(2),
                    textposition="outside",
                    name="Z-Score",
                ))
                fig_z1.add_hline(y=2,  line_dash="dash", line_color="#e74c3c",  annotation_text="+2σ")
                fig_z1.add_hline(y=1,  line_dash="dot",  line_color="#f39c12",  annotation_text="+1σ")
                fig_z1.add_hline(y=0,  line_dash="solid",line_color="white",    line_width=1)
                fig_z1.add_hline(y=-1, line_dash="dot",  line_color="#3498db",  annotation_text="-1σ")
                fig_z1.add_hline(y=-2, line_dash="dash", line_color="#9b59b6",  annotation_text="-2σ")
                fig_z1.update_layout(
                    xaxis_title="Microciclo", yaxis_title="Z-Score",
                    height=400, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)", margin=dict(t=30),
                )
                st.plotly_chart(fig_z1, use_container_width=True)

                # Interpretação automática
                z_ultimo = mc_z.iloc[-1]["Z-Score Médio"]
                mc_ultimo = int(mc_z.iloc[-1]["Microciclo (Nr)"])
                if z_ultimo > 2:
                    st.markdown(f"🔴 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito acima** da média do jogador (>+2σ). Risco de sobrecarga.")
                elif z_ultimo > 1:
                    st.markdown(f"🟡 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **acima** da média (+1σ a +2σ). Monitorizar.")
                elif z_ultimo >= -1:
                    st.markdown(f"🟢 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **dentro da média** (±1σ). Normal.")
                elif z_ultimo >= -2:
                    st.markdown(f"🔵 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **abaixo** da média (-1σ a -2σ). Sub-estimulação.")
                else:
                    st.markdown(f"🟣 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito abaixo** da média (<-2σ). Possível recuperação/lesão.")

                # Tabela detalhada
                with st.expander("📋 Ver tabela completa de Z-Scores por Microciclo"):
                    st.dataframe(mc_z.set_index("Microciclo (Nr)"), use_container_width=True)

                # Múltiplas métricas — radar por microciclo
                st.divider()
                st.markdown('<p class="section-title">Radar de Z-Scores — Múltiplas Métricas (último vs penúltimo MC)</p>', unsafe_allow_html=True)
                mcs_disponiveis = sorted(df_jog_z["Microciclo (Nr)"].unique(), reverse=True)
                if len(mcs_disponiveis) >= 2:
                    mc_A = st.selectbox("Microciclo A", mcs_disponiveis, index=0, key="radar_mcA")
                    mc_B = st.selectbox("Microciclo B", mcs_disponiveis, index=1, key="radar_mcB")

                    # Métricas disponíveis — apenas as que existem em df_radar
                    # e que não são colunas calculadas como "Z-Score"
                    EXCLUIR_RADAR = {"Z-Score","Z-Score Médio","Microciclo (Nr)",
                                      "Jogador","Posição","Tipo","Dia MD","Data"}
                    radar_mets = [m for m in get_mets_gps(df_jog_z)
                                  if m not in EXCLUIR_RADAR]

                    df_radar = df[df["Jogador"] == jog_z].copy()
                    if "Dia MD" in df_radar.columns and dia_md_sel:
                        df_radar = df_radar[df_radar["Dia MD"].isin(dia_md_sel)]

                    # Filtrar radar_mets para só incluir colunas que existem em df_radar
                    radar_mets = [m for m in radar_mets if m in df_radar.columns]

                    # Z-score calculado sobre toda a série do jogador
                    zscores_A, zscores_B = [], []
                    for m in radar_mets:
                        if m in df_radar.columns and df_radar[m].notna().sum() > 1:
                            z_all = zscore_serie(df_radar[m])
                            sub_A = z_all[df_radar["Microciclo (Nr)"] == mc_A]
                            sub_B = z_all[df_radar["Microciclo (Nr)"] == mc_B]
                            zscores_A.append(round(sub_A.mean(), 2) if not sub_A.empty else 0)
                            zscores_B.append(round(sub_B.mean(), 2) if not sub_B.empty else 0)
                        else:
                            zscores_A.append(0); zscores_B.append(0)

                    fig_radar_z = go.Figure()
                    fig_radar_z.add_trace(go.Scatterpolar(
                        r=zscores_A + [zscores_A[0]], theta=radar_mets + [radar_mets[0]],
                        fill="toself", name=f"MC {mc_A}", line_color="#e63946", opacity=0.8,
                    ))
                    fig_radar_z.add_trace(go.Scatterpolar(
                        r=zscores_B + [zscores_B[0]], theta=radar_mets + [radar_mets[0]],
                        fill="toself", name=f"MC {mc_B}", line_color="#457b9d", opacity=0.8,
                    ))
                    fig_radar_z.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        height=420, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_z, use_container_width=True)
            else:
                st.warning(f"Dados insuficientes para calcular Z-Score de '{met_z}' para {jog_z}.")

        # ── TAB 2: Comparação entre jogadores da mesma posição ────────────────────
        with tab2:
            st.markdown('<p class="section-title">Z-Score por Posição — Onde se posiciona cada jogador?</p>', unsafe_allow_html=True)
            col_c, col_d = st.columns(2)
            pos_z  = col_c.selectbox("Posição", posicoes if posicoes else ["—"], key="z_pos")
            met_z2 = col_d.selectbox("Métrica", metricas_disp, key="z_met2")
            mc_z2  = col_c.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="z_mc2")

            df_pos_z = df[
                (df["Posição"] == pos_z) &
                (df["Microciclo (Nr)"] == mc_z2)
            ].copy()
            # Dia MD já filtrado via df_f_dia

            if met_z2 in df_pos_z.columns and df_pos_z[met_z2].notna().sum() > 1:
                # Z-Score calculado dentro do grupo da posição
                df_pos_z["Z-Score"] = zscore_serie(df_pos_z[met_z2])
                df_pos_z_mc = df_pos_z.groupby("Jogador").agg(
                    Z_medio=("Z-Score", "mean"),
                    Valor_medio=(met_z2, "mean"),
                ).reset_index().sort_values("Z_medio", ascending=True)
                df_pos_z_mc.columns = ["Jogador", "Z-Score", f"Média {met_z2}"]

                cores_pos = [cor_zscore(z) for z in df_pos_z_mc["Z-Score"]]

                fig_pos_z = go.Figure(go.Bar(
                    y=df_pos_z_mc["Jogador"],
                    x=df_pos_z_mc["Z-Score"],
                    orientation="h",
                    marker_color=cores_pos,
                    text=df_pos_z_mc["Z-Score"].round(2),
                    textposition="outside",
                ))
                fig_pos_z.add_vline(x=0,  line_dash="solid", line_color="white", line_width=1)
                fig_pos_z.add_vline(x=1,  line_dash="dot",   line_color="#f39c12", annotation_text="+1σ")
                fig_pos_z.add_vline(x=-1, line_dash="dot",   line_color="#3498db", annotation_text="-1σ")
                fig_pos_z.update_layout(
                    xaxis_title="Z-Score", height=max(280, len(df_pos_z_mc)*55),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=20),
                )
                st.plotly_chart(fig_pos_z, use_container_width=True)

                st.markdown(f"**Referência do grupo ({pos_z}) — MC {int(mc_z2)}:**")
                st.dataframe(df_pos_z_mc.set_index("Jogador"), use_container_width=True)

                # Conclusões por posição
                st.divider()
                st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
                acima = df_pos_z_mc[df_pos_z_mc["Z-Score"] > 1]["Jogador"].tolist()
                abaixo = df_pos_z_mc[df_pos_z_mc["Z-Score"] < -1]["Jogador"].tolist()
                normal = df_pos_z_mc[df_pos_z_mc["Z-Score"].between(-1, 1)]["Jogador"].tolist()
                media_val = df_pos_z[met_z2].mean()

                if acima:
                    st.markdown(f"🟡 **Acima da média do grupo** (>+1σ): {', '.join(acima)}")
                if abaixo:
                    st.markdown(f"🔵 **Abaixo da média do grupo** (<-1σ): {', '.join(abaixo)}")
                if normal:
                    st.markdown(f"🟢 **Dentro da média** (±1σ): {', '.join(normal)}")
                st.markdown(f"📊 **Média do grupo** para {met_z2} no MC {int(mc_z2)}: **{media_val:.1f}**")

                # Heatmap — todos os microciclos × jogadores da posição
                st.divider()
                st.markdown('<p class="section-title">🗺️ Heatmap Z-Score — Todos os Microciclos</p>', unsafe_allow_html=True)
                df_heat = df[df["Posição"] == pos_z].copy()
                # Dia MD já filtrado via df_f_dia

                if met_z2 in df_heat.columns:
                    df_heat = df_heat.dropna(subset=[met_z2, "Microciclo (Nr)", "Jogador"])
                    pivot = df_heat.groupby(["Jogador", "Microciclo (Nr)"])[met_z2].mean(numeric_only=True).unstack()
                    # Z-score por coluna (microciclo) dentro da posição
                    pivot_z = pivot.apply(
                        lambda col: (col - col.mean()) / col.std() if col.std() > 0 and col.notna().sum() > 1 else col * 0,
                        axis=0
                    )

                    fig_heat = go.Figure(go.Heatmap(
                        z=pivot_z.values,
                        x=[f"MC {int(c)}" for c in pivot_z.columns],
                        y=pivot_z.index.tolist(),
                        colorscale="RdYlGn",
                        zmid=0,
                        text=pivot_z.round(1).values,
                        texttemplate="%{text}",
                        colorbar=dict(title="Z-Score"),
                    ))
                    fig_heat.update_layout(
                        height=max(280, len(pivot_z)*50),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                        xaxis_title="Microciclo", yaxis_title="Jogador",
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.warning(f"Dados insuficientes para '{met_z2}' na posição '{pos_z}' no MC {int(mc_z2)}.")


    with st.expander("🏋️ Análise de Exercícios GPS", expanded=False):

            df_ex = carregar_exercicios(excel_path)

            METS_EX = get_mets_gps(df_ex) if not df_ex.empty else []

            if df_ex.empty:
                st.info("""
        ### 📋 Folha de Exercícios vazia

        Abre o Excel e preenche a folha **Exercícios** com os dados de cada exercício.
        As linhas a azul claro são exemplos — podes apagá-las e começar a preencher a partir da linha 10.

        **Colunas a preencher:**
        - **Data** — data do treino
        - **Microciclo (Nr)** — número do microciclo
        - **Dia MD** — ex: MD-3, MD-2, MD-1
        - **Nome do Exercício** — ex: "Joguinho posicional 4x4"
        - **Categoria** — ex: Jogo Reduzido, Físico, Técnico-Tático
        - **Duração (min)** — duração do exercício
        - **Nº Jogadores** — número de jogadores
        - **Distância Total, HSR, Sprint, Acc, Dcc, Vel. Máx** — médias por jogador no exercício

        Depois guarda o Excel e clica em **🔄 Atualizar Dados**.
                """)

            mets_ex_disp = [m for m in METS_EX if m in df_ex.columns and df_ex[m].notna().any()]

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)

            datas_ex = sorted(df_ex["Data"].dropna().dt.date.unique(), reverse=True) if "Data" in df_ex.columns else []
            mcs_ex   = sorted(df_ex["Microciclo (Nr)"].dropna().unique(), reverse=True) if "Microciclo (Nr)" in df_ex.columns else []
            cats_ex  = sorted(df_ex["Categoria"].dropna().unique()) if "Categoria" in df_ex.columns else []

            modo_ex = col_f1.radio("Modo de análise", ["📅 Por sessão (dia)", "📆 Por microciclo", "📊 Geral"], horizontal=True)

            if modo_ex == "📅 Por sessão (dia)":
                if not datas_ex:
                    st.warning("Sem datas disponíveis nos dados de exercícios.")
                    data_ex_sel = None
                else:
                    data_ex_sel = col_f2.selectbox(
                        "Data", datas_ex,
                        format_func=lambda d: d.strftime("%d/%m/%Y"),
                        key="ex_data"
                    )
                df_ex_f = df_ex[df_ex["Data"].dt.date == data_ex_sel] if ("Data" in df_ex.columns and data_ex_sel) else df_ex
                titulo_ctx = f"Treino de {data_ex_sel.strftime('%d/%m/%Y')}" if data_ex_sel else "Sem dados"

            elif modo_ex == "📆 Por microciclo":
                mc_ex_sel = col_f2.selectbox("Microciclo", mcs_ex, key="ex_mc")
                df_ex_f = df_ex[df_ex["Microciclo (Nr)"] == mc_ex_sel] if "Microciclo (Nr)" in df_ex.columns else df_ex
                titulo_ctx = f"Microciclo {int(mc_ex_sel)}"
            else:
                df_ex_f = df_ex.copy()
                titulo_ctx = "Todos os exercícios"

            cat_sel = col_f3.multiselect("Categoria", cats_ex, default=cats_ex, key="ex_cat")
            if cat_sel and "Categoria" in df_ex_f.columns:
                df_ex_f = df_ex_f[df_ex_f["Categoria"].isin(cat_sel)]

            if df_ex_f.empty:
                st.warning("Sem exercícios para os filtros selecionados.")

            if not mets_ex_disp:
                st.warning("Sem métricas numéricas na folha 'Exercícios'. Verifica o formato do Excel.")
                met_ex = None
            else:
                met_ex = st.selectbox("Métrica de análise", mets_ex_disp, key="ex_met",
                                       help="Métrica usada para ordenar e comparar exercícios")

            st.divider()

            # ── Exercício mais exigente ────────────────────────────────────────────────
            st.markdown(f'<p class="section-title">🏆 Exercício Mais Exigente — {titulo_ctx}</p>', unsafe_allow_html=True)

            df_ex_rank = df_ex_f.dropna(subset=[met_ex]).sort_values(met_ex, ascending=False).copy() if (mets_ex_disp and met_ex and met_ex in df_ex_f.columns) else pd.DataFrame()

            if not df_ex_rank.empty:
                top = df_ex_rank.iloc[0]
                segundo = df_ex_rank.iloc[1] if len(df_ex_rank) > 1 else None
                terceiro = df_ex_rank.iloc[2] if len(df_ex_rank) > 2 else None

                c1, c2, c3 = st.columns(3)
                def card_ex(col, row, medal, cor):
                    nome = str(row["Exercício"])[:30] if "Exercício" in df_ex_rank.columns else "—"
                    cat  = row.get("Categoria","—")
                    dur  = row.get("Duração (min)","—")
                    val  = row[met_ex]
                    col.markdown(
                        f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                        f'padding:14px;text-align:center;margin:4px">'
                        f'<div style="font-size:1.4rem">{medal}</div>'
                        f'<div style="font-size:1rem;font-weight:700;color:{cor}">{nome}</div>'
                        f'<div style="font-size:0.75rem;color:#aaa">{cat} · {dur} min</div>'
                        f'<div style="font-size:1.6rem;font-weight:900;color:{cor};margin:6px 0">{val:,.1f}</div>'
                        f'<div style="font-size:0.7rem;color:#888">{met_ex}</div>'
                        f'</div>', unsafe_allow_html=True
                    )

                card_ex(c1, top,      "🥇", "#f39c12")
                if segundo  is not None: card_ex(c2, segundo,  "🥈", "#95a5a6")
                if terceiro is not None: card_ex(c3, terceiro, "🥉", "#cd7f32")

                st.markdown("")

                # Gráfico ranking completo
                cores_ex = []
                max_v = df_ex_rank[met_ex].max()
                for v in df_ex_rank[met_ex]:
                    pct = v / max_v if max_v > 0 else 0
                    if pct >= 0.85:   cores_ex.append("#f39c12")
                    elif pct >= 0.65: cores_ex.append("#e63946")
                    else:             cores_ex.append("#457b9d")

                nomes = df_ex_rank["Exercício"].astype(str) if "Exercício" in df_ex_rank.columns else df_ex_rank.index.astype(str)
                fig_rank_ex = go.Figure(go.Bar(
                    y=nomes, x=df_ex_rank[met_ex],
                    orientation="h",
                    marker_color=cores_ex,
                    text=df_ex_rank[met_ex].round(1),
                    textposition="outside",
                ))
                fig_rank_ex.add_vline(x=df_ex_rank[met_ex].mean(), line_dash="dash", line_color="white",
                                       annotation_text=f"Média: {df_ex_rank[met_ex].mean():.1f}")
                fig_rank_ex.update_layout(
                    height=max(300, len(df_ex_rank)*50),
                    xaxis_title=met_ex, yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                )
                st.plotly_chart(fig_rank_ex, use_container_width=True)

            st.divider()

            # ── Heatmap exercícios × métricas ─────────────────────────────────────────
            st.markdown('<p class="section-title">🗺️ Perfil de Exigência — Todos os Exercícios</p>', unsafe_allow_html=True)
            st.caption("Valores normalizados 0–100% (100% = exercício com valor máximo nessa métrica)")

            if "Exercício" in df_ex_f.columns and len(mets_ex_disp) >= 2:
                df_heat_ex = df_ex_f.groupby("Exercício")[mets_ex_disp].mean()
                # Normalizar 0–100 por coluna
                df_heat_norm = df_heat_ex.apply(
                    lambda col: (col / col.max() * 100).round(0) if col.max() > 0 else col * 0, axis=0
                )
                labels_heat_ex = [m.replace(" (m)","").replace(" (n)","").replace(" (km/h)","").replace(" Ex.","") for m in mets_ex_disp]
                df_heat_norm.columns = labels_heat_ex

                fig_heat_ex = go.Figure(go.Heatmap(
                    z=df_heat_norm.values,
                    x=df_heat_norm.columns.tolist(),
                    y=df_heat_norm.index.tolist(),
                    text=df_heat_ex.round(1).values,
                    texttemplate="%{text}",
                    colorscale="YlOrRd",
                    zmin=0, zmax=100,
                    colorbar=dict(title="% do máx", ticksuffix="%"),
                ))
                fig_heat_ex.update_layout(
                    height=max(280, len(df_heat_norm)*55),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", margin=dict(t=10),
                    xaxis_title="Métrica GPS", yaxis_title="Exercício",
                )
                st.plotly_chart(fig_heat_ex, use_container_width=True)
                st.caption("Valores reais dentro de cada célula · Cor = % do máximo nessa métrica")

            st.divider()

            # ── Comparação por categoria ──────────────────────────────────────────────
            if "Categoria" in df_ex_f.columns and df_ex_f["Categoria"].notna().any():
                st.markdown('<p class="section-title">📊 Comparação por Categoria</p>', unsafe_allow_html=True)

                df_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean().reset_index()
                fig_cat = px.bar(
                    df_cat.melt(id_vars="Categoria", value_vars=mets_ex_disp[:5]),
                    x="variable", y="value", color="Categoria",
                    barmode="group",
                    labels={"variable": "Métrica", "value": "Média", "Categoria": "Categoria"},
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                fig_cat.update_layout(
                    height=380, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10), legend_title="",
                )
                st.plotly_chart(fig_cat, use_container_width=True)

                # Radar por categoria
                st.markdown('<p class="section-title">📡 Radar de Perfil por Categoria</p>', unsafe_allow_html=True)
                if len(mets_ex_disp) >= 3:
                    df_radar_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean()
                    # Normalizar
                    df_radar_norm = df_radar_cat.apply(
                        lambda col: col / col.max() * 100 if col.max() > 0 else col * 0, axis=0
                    )
                    labels_r = [m.replace(" (m)","").replace(" (n)","").replace(" Ex.","") for m in mets_ex_disp]
                    fig_radar_cat = go.Figure()
                    cores_r = px.colors.qualitative.Bold
                    for i, (cat, row) in enumerate(df_radar_norm.iterrows()):
                        vals = list(row.values) + [row.values[0]]
                        labs = labels_r + [labels_r[0]]
                        fig_radar_cat.add_trace(go.Scatterpolar(
                            r=vals, theta=labs, fill="toself",
                            name=cat, line_color=cores_r[i % len(cores_r)], opacity=0.75,
                        ))
                    fig_radar_cat.update_layout(
                        polar=dict(radialaxis=dict(visible=True, ticksuffix="%", range=[0,100])),
                        height=440, plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    )
                    st.plotly_chart(fig_radar_cat, use_container_width=True)

            st.divider()

            # ── Evolução ao longo da sessão (ordem dos exercícios) ────────────────────
            if modo_ex == "📅 Por sessão (dia)" and "Exercício" in df_ex_f.columns:
                st.markdown('<p class="section-title">📈 Curva de Intensidade ao Longo da Sessão</p>', unsafe_allow_html=True)
                st.caption("Ordem dos exercícios tal como foram registados no Excel")

                met_ev_ex = st.selectbox("Métrica", mets_ex_disp, key="ex_ev_met")
                df_ev_ex = df_ex_f.reset_index(drop=True)
                df_ev_ex["Ordem"] = range(1, len(df_ev_ex)+1)
                df_ev_ex["Label"] = df_ev_ex["Exercício"].astype(str).str[:20]

                cores_ev = []
                max_ev = df_ev_ex[met_ev_ex].max() if df_ev_ex[met_ev_ex].notna().any() else 1
                for v in df_ev_ex[met_ev_ex]:
                    pct = v / max_ev if max_ev > 0 and pd.notna(v) else 0
                    if pct >= 0.85:   cores_ev.append("#f39c12")
                    elif pct >= 0.65: cores_ev.append("#e63946")
                    else:              cores_ev.append("#457b9d")

                fig_ev_ex = go.Figure()
                fig_ev_ex.add_trace(go.Bar(
                    x=df_ev_ex["Label"], y=df_ev_ex[met_ev_ex],
                    marker_color=cores_ev,
                    text=df_ev_ex[met_ev_ex].round(1), textposition="outside",
                    customdata=df_ev_ex[["Categoria","Duração (min)"]].values if "Categoria" in df_ev_ex.columns else None,
                    hovertemplate="<b>%{x}</b><br>%{y:.1f}<br>%{customdata[0]} · %{customdata[1]} min<extra></extra>"
                    if "Categoria" in df_ev_ex.columns else None,
                ))
                fig_ev_ex.add_hline(y=df_ev_ex[met_ev_ex].mean(), line_dash="dash", line_color="white",
                                     annotation_text=f"Média: {df_ev_ex[met_ev_ex].mean():.1f}")
                fig_ev_ex.update_layout(
                    height=360, yaxis_title=met_ev_ex,
                    xaxis_title="Exercício (por ordem da sessão)",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="rgba(255,255,255,0.85)", showlegend=False, margin=dict(t=10),
                )
                st.plotly_chart(fig_ev_ex, use_container_width=True)

            st.divider()

            # ── Tabela completa ───────────────────────────────────────────────────────
            with st.expander("📋 Ver todos os registos"):
                cols_show = ["Exercício","Categoria","Duração (min)","Nº Jogadores"] + mets_ex_disp
                cols_show = [c for c in cols_show if c in df_ex_f.columns]
                sort_col = met_ex if (mets_ex_disp and "met_ex" in dir() and met_ex and met_ex in df_ex_f.columns) else (cols_show[0] if cols_show else None)
                st.dataframe(
                    df_ex_f[cols_show].sort_values(sort_col, ascending=False).reset_index(drop=True) if sort_col else df_ex_f[cols_show],
                    use_container_width=True
                )

            # ── Exportar relatório ────────────────────────────────────────────────────
            st.divider()
            if not df_ex_rank.empty:
                cols_exp = ["Exercício","Categoria","Duração (min)"] + mets_ex_disp
                cols_exp = [c for c in cols_exp if c in df_ex_f.columns]
                headers_e = "".join(f"<th>{c}</th>" for c in cols_exp)
                linhas_e  = "".join(
                    f'<tr>{"".join(f"<td>{round(row[c],1) if isinstance(row[c], float) else row[c]}</td>" for c in cols_exp)}</tr>'
                    for _, row in df_ex_f[cols_exp].sort_values(met_ex, ascending=False).iterrows()
                )
                html_ex = gerar_pdf_html(f"""
        <h1>Análise de Exercícios — {titulo_ctx}</h1>
        <h2>🥇 Exercício mais exigente ({met_ex}): {str(top["Exercício"])}</h2>
        <p>Valor: {top[met_ex]:,.1f} | Categoria: {top.get("Categoria","—")} | Duração: {top.get("Duração (min)","—")} min</p>
        <h2>Ranking Completo</h2>
        <table><tr>{headers_e}</tr>{linhas_e}</table>
        """, f"Exercicios_{titulo_ctx.replace(' ','_')}.html")
                botao_download_html(html_ex, f"Exercicios_{titulo_ctx.replace(' ','_')}.html",
                                    "📥 Exportar Relatório de Exercícios")




    with st.expander("🩺 Lesões & Disponibilidade", expanded=False):

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
