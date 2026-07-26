"""LoadMonitorSystem — Página Sistema"""
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from utils.dados import get_mets_gps
from utils.calculos import calcular_acwr_global, cor_acwr
from utils.ui_safe import lm_header


def render(df, excel_path):
    """Renderiza a página Sistema."""
    # ── Estado partilhado (vem do session_state, populado pelo router) ────────
    _lm_user  = st.session_state.get("lm_user", {})
    _lm_plano = _lm_user.get("plano", "free")
    _lm_nome  = _lm_user.get("nome", "Utilizador")
    _lm_clube = _lm_user.get("clube", "")

    H = st.session_state.get("lm_helpers", {})
    validar_dados        = H.get("validar_dados",        lambda d: ([], [], []))
    enviar_email_alertas = H.get("enviar_email_alertas", lambda *a, **k: (False, "Email não disponível"))
    GLOSSARIO            = H.get("GLOSSARIO", {})
    EXCEL_PATH           = H.get("EXCEL_PATH", "")
    IS_CLOUD             = H.get("IS_CLOUD", True)
    get_preferencia      = H.get("get_preferencia",      lambda u, k, default=None: default)
    set_preferencia      = H.get("set_preferencia",      lambda u, k, v: False)

    lm_header("Sistema", "Configurações e glossário", "Sistema")

    # ── Tabs principais ───────────────────────────────────────────────────────
    tab_sys = st.tabs(["✅ Validação de Dados", "🔔 Notificações", "📊 Métricas Preferidas"])

    # ── TAB 0: Validação de Dados ─────────────────────────────────────────────
    with tab_sys[0]:
        if st.button("🔍 Validar agora", type="primary"):
            with st.spinner("A analisar..."):
                erros, avisos, ok_list = validar_dados(df)

            total = len(erros) + len(avisos) + len(ok_list)
            score = int(len(ok_list) / total * 100) if total > 0 else 0
            cor_s = "#2ecc71" if score >= 80 else "#f39c12" if score >= 60 else "#e74c3c"

            col_sc, col_res = st.columns([1, 3])
            col_sc.markdown(
                f'<div style="background:{cor_s}22;border:3px solid {cor_s};border-radius:16px;'
                f'padding:20px;text-align:center"><div style="font-size:0.9rem;color:#aaa">Qualidade</div>'
                f'<div style="font-size:3rem;font-weight:900;color:{cor_s}">{score}%</div></div>',
                unsafe_allow_html=True
            )
            col_res.metric("❌ Erros críticos", len(erros))
            col_res.metric("⚠️ Avisos", len(avisos))
            col_res.metric("✅ OK", len(ok_list))

            st.divider()
            for e in erros:   st.error(e)
            for a in avisos:  st.warning(a)
            for o in ok_list: st.success(o)

            st.divider()
            st.markdown("### 🔍 Valores únicos por coluna crítica")
            for col in ["Tipo", "Dia MD", "Posição", "Microciclo (Nr)"]:
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

    # ── TAB 1: Notificações ───────────────────────────────────────────────────
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
            smtp_user     = col_e1.text_input("📧 Email Gmail", placeholder="preparadorfisico@gmail.com", key="smtp_user")
            smtp_pass     = col_e2.text_input("🔑 App Password", type="password", key="smtp_pass")
            destinatarios = st.text_input("📨 Destinatários (separar por vírgula)",
                                          placeholder="treinador@clube.pt, medico@clube.pt", key="smtp_dest")

            st.divider()
            acwr_dict_n = calcular_acwr_global(df)
            alertas_atuais = []
            for jog, dados in acwr_dict_n.items():
                v = dados["acwr"]; estado = cor_acwr(v)
                if "RISCO" in estado or "ATENÇÃO" in estado:
                    alertas_atuais.append({"jogador": jog, "tipo": "ACWR",
                                           "descricao": f"ACWR = {v:.2f} — {estado}", "valor": f"{v:.2f}"})
            ultima_n = df.sort_values("Data").groupby("Jogador").last().reset_index()
            for _, row in ultima_n.iterrows():
                hi = row.get("Hooper Index", np.nan)
                if pd.notna(hi) and hi >= 14:
                    alertas_atuais.append({"jogador": row["Jogador"], "tipo": "Wellness",
                                           "descricao": f"Hooper Index elevado ({hi:.0f}/20)", "valor": f"{hi:.0f}"})

            st.markdown(f"**{len(alertas_atuais)} alertas ativos:**")
            for a in alertas_atuais:
                cor_a = "#e74c3c" if a["tipo"] == "ACWR" else "#f39c12"
                st.markdown(
                    f'<div style="border-left:3px solid {cor_a};padding:6px 12px;margin:3px 0;'
                    f'background:{cor_a}15;border-radius:0 8px 8px 0;font-size:0.82rem">'
                    f'<b>{a["jogador"]}</b> — {a["descricao"]}</div>',
                    unsafe_allow_html=True
                )
            if not alertas_atuais:
                st.success("✅ Nenhum alerta ativo.")

            st.divider()
            if st.button("📧 Enviar Email Agora", type="primary",
                         disabled=not (smtp_user and smtp_pass and destinatarios)):
                dests = [d.strip() for d in destinatarios.split(",") if d.strip()]
                resultados = []
                with st.spinner("A enviar..."):
                    for dest in dests:
                        ok, msg = enviar_email_alertas(dest, smtp_user, smtp_pass, alertas_atuais)
                        resultados.append((dest, ok, msg))
                        st.caption(f"{dest}: {msg}")
                if any(ok for _, ok, _ in resultados):
                    st.success("✅ Email enviado!")

        with tab_n2:
            st.markdown("### Partilhar Alertas via WhatsApp")
            acwr_dict_wa = calcular_acwr_global(df)
            linhas_wa = [f"🚨 *Alertas de Carga — {datetime.now().strftime('%d/%m/%Y')}*\n"]
            for jog, dados in acwr_dict_wa.items():
                v = dados["acwr"]; estado = cor_acwr(v)
                if "RISCO" in estado:
                    linhas_wa.append(f"🔴 *{jog}* — ACWR {v:.2f} (RISCO)")
                elif "ATENÇÃO" in estado:
                    linhas_wa.append(f"🟡 *{jog}* — ACWR {v:.2f} (ATENÇÃO)")
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
            st.markdown(
                f'<a href="{wa_url}" target="_blank" '
                f'style="display:inline-block;padding:14px 28px;background:#25D366;color:white;'
                f'border-radius:10px;text-decoration:none;font-weight:bold;font-size:1rem">'
                f'📱 Abrir WhatsApp com os Alertas</a>',
                unsafe_allow_html=True
            )
            st.code(mensagem_wa, language=None)

    # ── TAB 2: Métricas Preferidas ────────────────────────────────────────────
    with tab_sys[2]:
        st.markdown('<p class="section-title">📊 Métricas Preferidas</p>', unsafe_allow_html=True)
        st.markdown("Selecciona as métricas que queres ver por defeito nas análises. "
                    "A app mostrará sempre todas as métricas disponíveis no teu Excel, "
                    "mas estas serão usadas como métricas principais.")

        _mets_disponiveis = get_mets_gps(df) if df is not None and not df.empty else []

        if not _mets_disponiveis:
            st.info("Carrega um ficheiro Excel para ver as métricas disponíveis.")
        else:
            st.markdown("**Métricas disponíveis no teu Excel:**")

            _user_id = _lm_user.get("id", 0)
            _pref_key = f"metricas_pref_{_user_id}"
            _pref_db = get_preferencia(_user_id, "metricas_default", None)
            _pref_atual = (_pref_db
                           if _pref_db is not None
                           else st.session_state.get(_pref_key, _mets_disponiveis[:6]))

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
                if set_preferencia(_user_id, "metricas_default", _selecao):
                    st.success(f"✅ Preferências guardadas — {len(_selecao)} métricas seleccionadas.")
                else:
                    st.warning(f"⚠️ Guardado nesta sessão ({len(_selecao)} métricas), "
                               "mas não foi possível persistir na base de dados.")

            st.divider()
            st.markdown("**Todas as métricas disponíveis no teu Excel:**")
            _cols_met = st.columns(3)
            for i, m in enumerate(_mets_disponiveis):
                _cols_met[i % 3].markdown(f"- `{m}`")

            st.caption("As métricas são detectadas automaticamente a partir do teu ficheiro Excel. "
                       "Compatível com Catapult, STATSports, Polar, FieldWiz e qualquer outro sistema GPS.")

    # ── Glossário ─────────────────────────────────────────────────────────────
    with st.expander("📖 Glossário", expanded=False):
        nivel = st.radio("Nível de explicação",
                         ["🟢 Simples (não-especialista)", "🔵 Técnico (especialista)"],
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

                if info.get("zonas"):
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

    # ── Rodapé ────────────────────────────────────────────────────────────────
    st.divider()
    st.caption("Dashboard de Monitorização de Carga · Gerado automaticamente a partir do ficheiro Excel · "
               "Para atualizar, clica em '🔄 Atualizar Dados' na barra lateral.")
