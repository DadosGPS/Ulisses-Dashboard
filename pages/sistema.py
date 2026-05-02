"""LoadMonitorSystem — Página Sistema"""
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
    lm_header("Sistema", "Configurações, histórico de alertas e glossário", "Sistema")
    tab_sys = st.tabs(["✅ Validação de Dados", "🔔 Notificações", "📊 Métricas Preferidas"])

    with st.expander("🕓 Histórico de Alertas", expanded=False):

            log = carregar_log()

            col_l1, col_l2 = st.columns([3,1])
            with col_l2:
                if st.button("🗑️ Limpar todo o histórico", type="secondary"):
                    if not os.path.exists(EXCEL_PATH):
                        st.session_state["alertas_log"] = []
                    else:
                        LOG_PATH.write_text("[]", encoding="utf-8")
                    st.rerun()
                if st.button("📥 Exportar histórico", type="secondary"):
                    if log:
                        df_log_exp = pd.DataFrame(log)
                        linhas_log = "".join([
                            f'<tr><td>{r["data"]}</td><td>{r["jogador"]}</td>'
                            f'<td>{r["tipo"]}</td><td>{r["descricao"]}</td><td>{r["valor"]}</td></tr>'
                            for r in log
                        ])
                        html_log = gerar_pdf_html(f"""
        <h1>Histórico de Alertas</h1>
        <table><tr><th>Data</th><th>Jogador</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr>
        {linhas_log}</table>""", "Historico_Alertas.html")
                        botao_download_html(html_log, "Historico_Alertas.html", "📥 Exportar (PDF)")

            if not log:
                st.info("Ainda não há alertas registados. Abre a página **🚨 Alertas do Dia** para gerar os primeiros alertas.")

            df_log = pd.DataFrame(log)
            df_log["data"] = pd.to_datetime(df_log["data"])
            df_log = df_log.sort_values("data", ascending=False)

            # ── Filtros ───────────────────────────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns(3)
            tipos_log  = ["Todos"] + sorted(df_log["tipo"].unique().tolist())
            jogs_log   = ["Todos"] + sorted(df_log["jogador"].unique().tolist())
            tipo_sel_l = col_f1.selectbox("Tipo de alerta", tipos_log, key="log_tipo")
            jog_sel_l  = col_f2.selectbox("Jogador",        jogs_log,  key="log_jog")

            df_log_f = df_log.copy()
            if tipo_sel_l != "Todos": df_log_f = df_log_f[df_log_f["tipo"] == tipo_sel_l]
            if jog_sel_l  != "Todos": df_log_f = df_log_f[df_log_f["jogador"] == jog_sel_l]

            # ── KPIs ─────────────────────────────────────────────────────────────────
            k1,k2,k3,k4 = st.columns(4)
            k1.metric("Total de alertas",        len(df_log_f))
            k2.metric("Jogadores com alertas",   df_log_f["jogador"].nunique())
            k3.metric("Alertas hoje",
                      len(df_log_f[df_log_f["data"].dt.date == date.today()]))
            k4.metric("Alerta mais recente",
                      df_log_f["data"].max().strftime("%d/%m %H:%M") if not df_log_f.empty else "—")

            st.divider()

            # ── Gráfico de frequência de alertas no tempo ────────────────────────────
            st.markdown('<p class="section-title">Frequência de Alertas ao Longo do Tempo</p>', unsafe_allow_html=True)
            df_log_f["dia"] = df_log_f["data"].dt.date
            freq = df_log_f.groupby(["dia","tipo"]).size().reset_index(name="n")
            if not freq.empty:
                fig_freq = px.bar(freq, x="dia", y="n", color="tipo",
                                  color_discrete_sequence=px.colors.qualitative.Bold,
                                  labels={"dia":"Data","n":"Nº Alertas","tipo":"Tipo"})
                fig_freq.update_layout(
                    height=300, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="rgba(255,255,255,0.85)",
                    margin=dict(t=10), legend_title="",
                )
                st.plotly_chart(fig_freq, use_container_width=True)

            # ── Alertas por jogador ───────────────────────────────────────────────────
            st.markdown('<p class="section-title">Alertas por Jogador</p>', unsafe_allow_html=True)
            jog_count = df_log_f.groupby("jogador").size().sort_values(ascending=True).reset_index(name="n")
            fig_jog_log = go.Figure(go.Bar(
                y=jog_count["jogador"], x=jog_count["n"],
                orientation="h", marker_color="#e63946",
                text=jog_count["n"], textposition="outside",
            ))
            fig_jog_log.update_layout(
                height=max(200, len(jog_count)*40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="rgba(255,255,255,0.85)", xaxis_title="Nº de alertas", margin=dict(t=10),
            )
            st.plotly_chart(fig_jog_log, use_container_width=True)

            # ── Timeline de alertas ───────────────────────────────────────────────────
            st.divider()
            st.markdown('<p class="section-title">📋 Registo Detalhado</p>', unsafe_allow_html=True)

            COR_TIPO = {"ACWR": "#e74c3c", "Wellness": "#f39c12", "Vmáx": "#3498db"}
            for _, row in df_log_f.head(100).iterrows():
                cor_t = COR_TIPO.get(row["tipo"], "#888")
                st.markdown(
                    f'<div style="border-left:4px solid {cor_t};padding:8px 12px;margin:4px 0;'
                    f'background:{cor_t}15;border-radius:0 8px 8px 0">'
                    f'<span style="font-size:0.75rem;color:#aaa">{row["data"].strftime("%d/%m/%Y %H:%M")}</span> '
                    f'<span style="background:{cor_t};color:white;padding:2px 8px;border-radius:4px;'
                    f'font-size:0.75rem;font-weight:700;margin:0 6px">{row["tipo"]}</span>'
                    f'<b>{row["jogador"]}</b> — {row["descricao"]} '
                    f'<span style="color:{cor_t};font-weight:700">({row["valor"]})</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            if len(df_log_f) > 100:
                st.caption(f"A mostrar os 100 alertas mais recentes de {len(df_log_f)} total.")


        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: GLOSSÁRIO
        # ═══════════════════════════════════════════════════════════════════════════════

    with tab_sys[0]:

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






    with tab_sys[1]:

            tab_n1, tab_n2 = st.tabs(["📧 Email", "📱 WhatsApp"])

            with tab_n1:
                st.markdown("### Configuração de Email (Gmail)")
                with st.expander("ℹ️ Como criar uma App Password no Gmail"):
                    st.markdown("""
        1. Vai a **https://myaccount.google.com**
        2. Clica em **Segurança** → **Palavras-passe para apps**
        3. Seleciona **Outra (nome personalizado)** → escreve "LoadMonitor"
        4. Copia a password de 16 caracteres e usa-a abaixo
                    """)
                col_e1, col_e2 = st.columns(2)
                smtp_user = col_e1.text_input("📧 Email Gmail", placeholder="preparadorfisico@gmail.com", key="smtp_user")
                smtp_pass = col_e2.text_input("🔑 App Password", type="password", key="smtp_pass")
                destinatarios = st.text_input("📨 Destinatários (separar por vírgula)", placeholder="treinador@clube.pt, medico@clube.pt", key="smtp_dest")

                st.divider()
                acwr_dict_n = calcular_acwr_global(df)
                alertas_atuais = []
                for jog, dados in acwr_dict_n.items():
                    v = dados["acwr"]; estado = cor_acwr(v)
                    if "RISCO" in estado or "ATENÇÃO" in estado:
                        alertas_atuais.append({"jogador": jog, "tipo": "ACWR", "descricao": f"ACWR = {v:.2f} — {estado}", "valor": f"{v:.2f}"})
                ultima_n = df.sort_values("Data").groupby("Jogador").last().reset_index()
                for _, row in ultima_n.iterrows():
                    hi = row.get("Hooper Index", np.nan)
                    if pd.notna(hi) and hi >= 14:
                        alertas_atuais.append({"jogador": row["Jogador"], "tipo": "Wellness", "descricao": f"Hooper Index elevado ({hi:.0f}/20)", "valor": f"{hi:.0f}"})

                st.markdown(f"**{len(alertas_atuais)} alertas ativos:**")
                for a in alertas_atuais:
                    cor_a = "#e74c3c" if a["tipo"] == "ACWR" else "#f39c12"
                    st.markdown(f'<div style="border-left:3px solid {cor_a};padding:6px 12px;margin:3px 0;background:{cor_a}15;border-radius:0 8px 8px 0;font-size:0.82rem"><b>{a["jogador"]}</b> — {a["descricao"]}</div>', unsafe_allow_html=True)
                if not alertas_atuais:
                    st.success("✅ Nenhum alerta ativo.")

                st.divider()
                if st.button("📧 Enviar Email Agora", type="primary", disabled=not (smtp_user and smtp_pass and destinatarios)):
                    dests = [d.strip() for d in destinatarios.split(",") if d.strip()]
                    with st.spinner("A enviar..."):
                        for dest in dests:
                            ok, msg = enviar_email_alertas(dest, smtp_user, smtp_pass, alertas_atuais)
                            st.caption(f"{dest}: {msg}")
                    if any(ok for ok, _ in [enviar_email_alertas(d.strip(), smtp_user, smtp_pass, alertas_atuais) for d in dests]):
                        st.success("✅ Email enviado!")

            with tab_n2:
                st.markdown("### Partilhar Alertas via WhatsApp")
                acwr_dict_wa = calcular_acwr_global(df)
                linhas_wa = [f"🚨 *Alertas de Carga — {datetime.now().strftime('%d/%m/%Y')}*\n"]
                for jog, dados in acwr_dict_wa.items():
                    v = dados["acwr"]; estado = cor_acwr(v)
                    if "RISCO" in estado: linhas_wa.append(f"🔴 *{jog}* — ACWR {v:.2f} (RISCO)")
                    elif "ATENÇÃO" in estado: linhas_wa.append(f"🟡 *{jog}* — ACWR {v:.2f} (ATENÇÃO)")
                ultima_wa = df.sort_values("Data").groupby("Jogador").last().reset_index()
                for _, row in ultima_wa.iterrows():
                    hi = row.get("Hooper Index", np.nan)
                    if pd.notna(hi) and hi >= 14:
                        linhas_wa.append(f"⚠️ *{row['Jogador']}* — Hooper {hi:.0f}/20")
                if len(linhas_wa) == 1:
                    linhas_wa.append("✅ Sem alertas ativos — equipa OK!")
                import urllib.parse
                mensagem_wa = "\n".join(linhas_wa)
                wa_url = f"https://wa.me/?text={urllib.parse.quote(mensagem_wa)}"
                st.markdown(f'<a href="{wa_url}" target="_blank" style="display:inline-block;padding:14px 28px;background:#25D366;color:white;border-radius:10px;text-decoration:none;font-weight:bold;font-size:1rem">📱 Abrir WhatsApp com os Alertas</a>', unsafe_allow_html=True)
                st.code(mensagem_wa, language=None)


        # ═══════════════════════════════════════════════════════════════════════════════
        # 🦵 TESTES NEUROMUSCULARES
        # ═══════════════════════════════════════════════════════════════════════════════


    with tab_sys[2]:
        st.markdown('<p class="section-title">📊 Métricas Preferidas</p>', unsafe_allow_html=True)
        st.markdown("Selecciona as métricas que queres ver por defeito nas análises. "
                    "A app mostrará sempre todas as métricas disponíveis no teu Excel, "
                    "mas estas serão usadas como métricas principais.")

        _mets_disponiveis = get_mets_gps(df) if "df" in dir() and df is not None else []

        if not _mets_disponiveis:
            st.info("Carrega um ficheiro Excel para ver as métricas disponíveis.")
        else:
            st.markdown("**Métricas disponíveis no teu Excel:**")

            # Métricas por categoria
            _cats = {
                "🏃 Volume": [m for m in _mets_disponiveis if any(k in m.lower() for k in ["distância","distance","dist","hsr","sprint"])],
                "⚡ Intensidade": [m for m in _mets_disponiveis if any(k in m.lower() for k in ["acc","dcc","vel","vmax","speed","sprint"])],
                "💪 Carga": [m for m in _mets_disponiveis if any(k in m.lower() for k in ["carga","load","pse","rpe","duração","duration"])],
                "💤 Wellness": [m for m in _mets_disponiveis if any(k in m.lower() for k in ["hooper","sono","dor","stress","humor","wellness"])],
                "📐 Outros": [m for m in _mets_disponiveis],
            }

            _pref_key = f"metricas_pref_{st.session_state.get('lm_user',{}).get('id',0)}"
            _pref_atual = st.session_state.get(_pref_key, _mets_disponiveis[:6])

            _selecao = st.multiselect(
                "Métricas principais (aparecem por defeito nos gráficos e tabelas):",
                options=_mets_disponiveis,
                default=[m for m in _pref_atual if m in _mets_disponiveis],
                help="Podes seleccionar até 8 métricas. A ordem importa — a primeira é a mais importante.",
                max_selections=8,
                key="sel_mets_pref"
            )

            if st.button("💾 Guardar preferências", type="primary", key="btn_guardar_pref"):
                st.session_state[_pref_key] = _selecao
                st.success(f"✅ Preferências guardadas — {len(_selecao)} métricas seleccionadas.")

            st.divider()
            st.markdown("**Todas as métricas disponíveis no teu Excel:**")
            _cols_met = st.columns(3)
            for i, m in enumerate(_mets_disponiveis):
                _cols_met[i % 3].markdown(f"- `{m}`")

            st.caption("As métricas são detectadas automaticamente a partir do teu ficheiro Excel. "
                      "Compatível com Catapult, STATSports, Polar, FieldWiz e qualquer outro sistema GPS.")


    with st.expander("📖 Glossário", expanded=False):

            nivel = st.radio("Nível de explicação", ["🟢 Simples (não-especialista)", "🔵 Técnico (especialista)"],
                             horizontal=True, key="gloss_nivel")
            simples = nivel.startswith("🟢")

            pesquisa = st.text_input("🔍 Pesquisar métrica...", key="gloss_pesq").lower()

            st.divider()

            for nome, info in GLOSSARIO.items():
                if pesquisa and pesquisa not in nome.lower() and pesquisa not in info["simples"].lower():
                    continue
                with st.expander(f"**{nome}**"):
                    if simples:
                        st.markdown(f"📌 {info['simples']}")
                    else:
                        st.markdown(f"🔬 **Definição técnica:** {info['tecnico']}")
                        st.markdown(f"📌 **Em linguagem simples:** {info['simples']}")

                    if info["zonas"]:
                        st.markdown("**Zonas de referência:**")
                        cols_z = st.columns(len(info["zonas"]))
                        for i, (zona, valor) in enumerate(info["zonas"].items()):
                            cols_z[i].markdown(
                                f'<div style="background:#1e2330;border-radius:8px;padding:8px;text-align:center">'
                                f'<div style="font-size:0.85rem;font-weight:700">{zona}</div>'
                                f'<div style="font-size:0.8rem;color:#aaa">{valor}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

            st.divider()
            st.markdown("""
            ### 📚 Referências Bibliográficas
            - **Foster et al. (2001)** — A New Approach to Monitoring Exercise Training. *Journal of Strength and Conditioning Research.*
            - **Gabbett (2016)** — The training-injury prevention paradox. *British Journal of Sports Medicine.*
            - **Malone et al. (2017)** — High chronic training loads and exposure to bouts of maximal velocity running. *Journal of Science and Medicine in Sport.*
            - **Hooper & Mackinnon (1995)** — Monitoring overtraining in athletes. *Sports Medicine.*
            """)




        # ═══════════════════════════════════════════════════════════════════════════════
        # VISTA: RESUMO DO DIA
        # ═══════════════════════════════════════════════════════════════════════════════

    # ── Rodapé ────────────────────────────────────────────────────────────────────
    st.divider()
    st.caption("Dashboard de Monitorização de Carga · Belenenses · Gerado automaticamente a partir do ficheiro Excel · Para atualizar, clica em '🔄 Atualizar Dados' na barra lateral.")