from __future__ import annotations

from typing import Any


ALERT_STATUS_NORMAL = "normal"
ALERT_STATUS_ATTENTION = "attention"
ALERT_STATUS_HIGH_ATTENTION = "high-attention"

# ── Motor único de sinais ───────────────────────────────────────────────────
# construir_avisos_dashboard é a ÚNICA fonte dos avisos por jogador: o Centro
# de Controlo, o ecrã Hoje, a Análise e o relatório leem todos daqui, para o
# mesmo jogador não ter estados diferentes consoante a página. Sinais:
#   1. ACWR acima do limiar (limites.acwr_alto, por omissão 1.30);
#   2. Velocidade máxima que não atinge (100 − velocidade_queda_sustentada) %
#      do recorde nos últimos VMAX_JANELA_DIAS dias;
#   3. Rácio de exposição HSR/Sprint da SEMANA face à referência de jogo, com
#      zonas de Buchheit configuráveis (limites.hsr_semana_* / sprint_semana_*);
#   4. Última sessão muito acima do habitual do jogador no mesmo Dia MD;
#   5. Prontidão: CMJ e Hooper face ao próprio jogador;
#   6. Sem dados há limites.dias_sem_dados dias;
#   7. PSE e GPS em sentidos opostos na última sessão.
#
# As zonas são um modelo de risco, não valores ótimos universais: devem ser
# lidas no contexto do microciclo, posição, histórico e dias entre jogos.
VMAX_PCT_MIN = 90.0   # por omissão; o valor usado vem de limites.velocidade_queda_sustentada
VMAX_JANELA_DIAS = 7
# Limiar estatístico (z-score) da divergência PSE vs GPS — significância
# estatística, não um limiar fisiológico que o preparador físico configure.
DIVERGENCIA_Z = 1.0


def classificar_acwr(valor: Any, limites: dict[str, float] | None = None) -> tuple[int, str]:
    """Classifica um ACWR usando os limiares configuráveis (limites_service).

    Fonte única de verdade da classificação de ACWR, partilhada pelos avisos do
    dashboard (construir_avisos_dashboard) e pela página Análise
    (analise_service). Devolve (severidade, estado):
      - severidade: 0 (ok/sub-carga), 1 (atenção), 2 (risco);
      - estado: rótulo com emoji, idêntico ao de utils.calculos.cor_acwr quando
        os limiares estão nos valores por omissão (1.3 / 1.5).
    """
    from app.services.limites_service import DEFAULTS
    lim = {**DEFAULTS, **(limites or {})}
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0, "❓"
    if v != v:  # NaN
        return 0, "❓"
    if v >= lim["acwr_muito_alto"]:
        return 2, "🔴 MUITO ACIMA"
    if v >= lim["acwr_alto"]:
        return 1, "🟡 ACIMA"
    if v >= 0.8:
        return 0, "🟢 OK"
    return 0, "🔵 ABAIXO"


from app.services.referencia_jogo import mascara_jogo, referencias_jogo  # noqa: E402,F401


def progresso_microciclo(df, e_jogo, mc) -> dict:
    """Quanto da semana de treino do microciclo `mc` já foi feito, para comparar
    a exposição acumulada com o que é de esperar ATÉ HOJE (e não com a zona da
    semana inteira — à segunda-feira toda a gente estaria «baixo»).

    fracao = dias de treino já feitos ÷ dias de treino de um microciclo típico
    desta equipa (mediana dos microciclos anteriores), limitada a 1. O
    microciclo conta como completo quando já tem o jogo depois do último treino.
    Sem histórico não se sabe quantos treinos tem a semana → fracao 1 (como antes).
    """
    import pandas as pd

    out = {"fracao": 1.0, "treinos_feitos": None, "treinos_tipicos": None, "completo": True}
    if mc is None or "Microciclo (Nr)" not in df.columns or "Data" not in df.columns:
        return out
    datas = pd.to_datetime(df["Data"], errors="coerce").dt.normalize()
    treino = ~e_jogo.reindex(df.index, fill_value=False)
    no_mc = df["Microciclo (Nr)"] == mc
    dias_treino = datas[no_mc & treino].dropna().unique()
    dias_jogo = datas[no_mc & ~treino].dropna().unique()
    feitos = len(dias_treino)
    out["treinos_feitos"] = feitos
    if len(dias_jogo) and (not feitos or max(dias_jogo) >= max(dias_treino)):
        return out
    anteriores = df[treino & df["Microciclo (Nr)"].notna() & (df["Microciclo (Nr)"] < mc)]
    if anteriores.empty:
        return out
    por_mc = datas[anteriores.index].groupby(anteriores["Microciclo (Nr)"]).nunique()
    tipicos = float(por_mc.median()) if not por_mc.empty else 0.0
    if tipicos <= 0:
        return out
    out.update(treinos_tipicos=round(tipicos, 1), completo=False,
               fracao=round(min(1.0, feitos / tipicos), 2))
    return out


def _zona_ratio(r: float | None, ref: tuple[float, float]) -> str | None:
    """Classifica um rácio de exposição face à zona de referência (Buchheit)."""
    if r is None:
        return None
    baixo, alto = ref
    if r < baixo:
        return "baixo"
    if r > alto:
        return "alto"
    return "ok"


HABITUAL_METRICAS = (("HSR (m)", "HSR"), ("Sprint (m)", "Sprint"), ("Distância Total (m)", "Distância"))
HABITUAL_Z = 2.0
HABITUAL_JANELA_DIAS = 7


def sessao_fora_do_habitual(g, df_max=None, e_jogo=None) -> list[tuple]:
    """Sinais da última sessão de treino do jogador `g` que ficou muito acima
    da sua variação habitual nas sessões do mesmo Dia MD."""
    import pandas as pd
    from app.services.variacao import classificar

    if g.empty or "Dia MD" not in g.columns or "Data" not in g.columns:
        return []
    if e_jogo is not None:
        g = g[~e_jogo.reindex(g.index, fill_value=False)]
    g = g.dropna(subset=["Data"])
    if g.empty:
        return []
    ultima = g["Data"].max()
    if df_max is not None and pd.notna(df_max) and ultima < df_max - pd.Timedelta(days=HABITUAL_JANELA_DIAS):
        return []
    sessao = g[g["Data"] == ultima]
    md = sessao["Dia MD"].dropna()
    if md.empty:
        return []
    md = md.iloc[0]
    anteriores = g[(g["Data"] < ultima) & (g["Dia MD"] == md)]
    out = []
    for col, etiqueta in HABITUAL_METRICAS:
        if col not in g.columns or sessao[col].dropna().empty:
            continue
        atual = float(sessao[col].sum())
        refs = [float(v) for v in anteriores.groupby("Data")[col].sum(min_count=1).dropna()]
        c = classificar(atual, refs, limiar_z=HABITUAL_Z)
        if c["metodo"] == "variacao" and c["estado"] == "alto":
            media = sum(refs) / len(refs)
            out.append((1, f"habitual_{etiqueta.lower()}", f"{etiqueta} acima do habitual",
                        f"{atual:.0f} vs habitual {media:.0f} · +{c['delta_pct']:.0f}% (varia ±{c['tipico_pct']:.0f}%)",
                        {"valor": round(atual), "habitual": round(media), "delta_pct": c["delta_pct"],
                         "tipico_pct": c["tipico_pct"], "n": c["n"], "dia_md": md,
                         "acao": f"Confirmar se os {atual:.0f} de {etiqueta} (habitual {media:.0f} num {md}) foram planeados; "
                                 "vigiar o wellness e a PSE no dia seguinte."}))
    return out


SUBSCORES_WELLNESS = (("Sono (1-5)", "sono"), ("Dor Musc. (1-5)", "dor muscular"),
                      ("Stress (1-5)", "stress"), ("Humor (1-5)", "humor"))


def _acao_hooper(g) -> str:
    """Ação para o bem-estar baixo, apontando o pior item do último registo."""
    import pandas as pd

    base = "Falar com o jogador antes do treino e ajustar a sessão ao que ele reportar."
    cols = [c for c, _ in SUBSCORES_WELLNESS if c in g.columns]
    if not cols or "Data" not in g.columns:
        return base
    ult = g.dropna(subset=cols, how="all").sort_values("Data")
    if ult.empty:
        return base
    linha = ult.iloc[-1]
    piores = sorted(((float(linha[c]), nome) for c, nome in SUBSCORES_WELLNESS if c in cols and pd.notna(linha[c])))
    if not piores or piores[0][0] > 3:
        return base
    return f"Falar com o jogador antes do treino — pior item: {piores[0][1]} {piores[0][0]:.0f}/5 — e ajustar a sessão."


def _acao_falta(etiqueta: str, falta: float, progresso: dict) -> str:
    """Ação para a exposição baixa: metros em falta para a zona da semana,
    repartidos pelos treinos que costumam faltar neste microciclo."""
    feitos, tipicos = progresso.get("treinos_feitos"), progresso.get("treinos_tipicos")
    if progresso.get("completo", True) or not tipicos or feitos is None:
        return f"Faltaram {falta:.0f} m de {etiqueta} esta semana: incluir na próxima semana ou num treino compensatório."
    restantes = max(1, round(tipicos - feitos))
    return (f"Faltam {falta:.0f} m de {etiqueta} para a zona da semana: "
            f"~{falta / restantes:.0f} m em cada um dos {restantes} treino(s) que costumam faltar.")


def divergencia_pse_gps(g) -> float | None:
    """Δz da última sessão do jogador quando a PSE e a distância se afastam do
    padrão habitual DELE em sentidos opostos (|z| > DIVERGENCIA_Z cada) — muitas
    vezes o primeiro sinal de fadiga não visível na carga, ou de doença."""
    if not {"PSE Sessão", "Distância Total (m)", "Data"}.issubset(g.columns):
        return None
    ambos = g.sort_values("Data").dropna(subset=["PSE Sessão", "Distância Total (m)"])
    if len(ambos) < 4:
        return None
    ultima, historico = ambos.iloc[-1], ambos.iloc[:-1]
    dp_pse, dp_dist = historico["PSE Sessão"].std(), historico["Distância Total (m)"].std()
    if not dp_pse or not dp_dist:
        return None
    z_pse = (ultima["PSE Sessão"] - historico["PSE Sessão"].mean()) / dp_pse
    z_dist = (ultima["Distância Total (m)"] - historico["Distância Total (m)"].mean()) / dp_dist
    if z_pse * z_dist < 0 and abs(z_pse) > DIVERGENCIA_Z and abs(z_dist) > DIVERGENCIA_Z:
        return round(float(z_pse - z_dist), 1)
    return None


def construir_avisos_dashboard(df, limites: dict[str, float] | None = None, estados: dict[str, str] | None = None,
                               testes=None, hoje=None) -> list[dict]:
    """Avisos do dashboard — apenas três sinais (ver constantes no topo):

      1. ACWR > limites.acwr_alto (por omissão 1.30);
      2. Vmax que não atinge VMAX_PCT_MIN% do recorde nos últimos
         VMAX_JANELA_DIAS dias;
      3. Rácio de exposição HSR/Sprint do microciclo mais recente face ao jogo
         mais exigente do jogador, fora da zona de referência.

      5. Prontidão: queda do CMJ e subida do Hooper face ao próprio jogador
         (as MESMAS regras e limiares da página Prontidão — prontidao_service),
         para o Centro de Controlo e a Prontidão não darem respostas diferentes.

    `estados` = {jogador: estado}: quem não está «apto» (lesionado, em
    recuperação, ausente) não entra — um ACWR baixo num lesionado não é um
    aviso novo, e a Análise já os excluía. `testes` = testes de CMJ (nome,
    data, altura_salto_cm); `hoje` = dia real para a validade do CMJ/Hooper.

    Devolve um item por jogador (status "normal" quando não há sinais), na mesma
    forma que o frontend do dashboard já consome.
    """
    import pandas as pd

    from app.services.limites_service import DEFAULTS
    from utils.calculos import calcular_acwr_global, recorde_vmax

    lim = {**DEFAULTS, **(limites or {})}
    if df is None or df.empty or "Jogador" not in df.columns:
        return []

    df = df.copy()
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    acwr_dict = calcular_acwr_global(df)
    data_max = df["Data"].max() if "Data" in df.columns else None
    estados = estados or {}

    # Sinais de prontidão (mesmas funções da página Prontidão).
    from app.services.prontidao_service import _cmj, _hooper, _sev, sev_cmj
    dia_ref = pd.Timestamp(hoje).normalize() if hoje is not None else data_max
    cmj = _cmj(testes, dia_ref) if testes is not None and dia_ref is not None else {}
    hooper = _hooper(df, dia_ref) if dia_ref is not None and pd.notna(dia_ref) else {}

    # Janela recente para a exposição HSR/Sprint: microciclo mais recente se
    # existir, senão últimos 7 dias. Só treinos (o jogo é a referência).
    e_jogo = mascara_jogo(df)
    progresso = {"fracao": 1.0}
    if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any():
        mc_atual = df["Microciclo (Nr)"].dropna().max()
        recente = df[df["Microciclo (Nr)"] == mc_atual]
        progresso = progresso_microciclo(df, e_jogo, mc_atual)
    elif "Data" in df.columns and df["Data"].notna().any():
        ref = df["Data"].max()
        recente = df[df["Data"] >= ref - pd.Timedelta(days=VMAX_JANELA_DIAS)]
    else:
        recente = df
    treinos_recentes = recente[~e_jogo.loc[recente.index]]
    jogos = df[e_jogo]

    # Janela de 7 dias para o estímulo de velocidade (independente do microciclo).
    vmax_janela = df
    if "Data" in df.columns and df["Data"].notna().any():
        refv = df["Data"].max()
        vmax_janela = df[df["Data"] >= refv - pd.Timedelta(days=VMAX_JANELA_DIAS)]

    # Referência de jogo por jogador (média por 90' dos últimos jogos completos;
    # ver referencia_jogo) — calculada uma vez por métrica.
    posicoes_todos = (
        df.dropna(subset=["Jogador", "Posição"]).groupby("Jogador")["Posição"].last().to_dict()
        if "Posição" in df.columns else {}
    )
    refs_jogo = {
        col: referencias_jogo(jogos, col, jogadores={j: posicoes_todos.get(j, "") for j in df["Jogador"].dropna().unique()})
        for col in ("HSR (m)", "Sprint (m)") if col in df.columns
    }

    avisos: list[dict] = []
    for jog in sorted(df["Jogador"].dropna().unique().tolist()):
        if estados.get(jog, "apto") != "apto":
            continue
        gfull = df[df["Jogador"] == jog]
        player_id = (
            str(gfull["player_id"].dropna().iloc[0])
            if "player_id" in gfull.columns and gfull["player_id"].notna().any()
            else str(jog)
        )
        # sinais: (severidade, chave, texto, valor, detalhe numérico p/ a web)
        sinais: list[tuple[int, str, str, str, dict]] = []

        # 1) ACWR
        v_acwr = acwr_dict.get(jog, {}).get("acwr")
        sev_acwr, _ = classificar_acwr(v_acwr, lim)
        if sev_acwr >= 1 and v_acwr is not None and pd.notna(v_acwr):
            ag = acwr_dict.get(jog, {}).get("ci_agudo")
            cr = acwr_dict.get(jog, {}).get("ci_cronico")
            acao = "Baixar o volume ou a intensidade das próximas sessões até a carga recente voltar à habitual."
            if ag and cr:
                acao = (f"Carga recente {float(ag):.0f} UA/dia vs habitual {float(cr):.0f} UA/dia: "
                        f"manter as próximas sessões abaixo do habitual até o rácio descer de {lim['acwr_alto']:.2f}.")
            sinais.append((sev_acwr, "acwr", "ACWR elevado",
                           f"ACWR {float(v_acwr):.2f} · limite {lim['acwr_alto']:.2f}",
                           {"valor": round(float(v_acwr), 2), "limite": round(float(lim["acwr_alto"]), 2), "acao": acao}))

        # 2) Vmax abaixo de (100 − velocidade_queda_sustentada) % do recorde
        #    nos últimos 7 dias (o melhor dos 7 dias, não a média: MD+1/MD-1
        #    não têm sprint por desenho).
        vmax_min = 100.0 - float(lim["velocidade_queda_sustentada"])
        if "Vel. Máx (km/h)" in gfull.columns and gfull["Vel. Máx (km/h)"].notna().any():
            recorde = recorde_vmax(gfull["Vel. Máx (km/h)"]) or 0.0
            g7 = vmax_janela[vmax_janela["Jogador"] == jog]
            if recorde > 0 and "Vel. Máx (km/h)" in g7.columns and g7["Vel. Máx (km/h)"].notna().any():
                pct7 = float(g7["Vel. Máx (km/h)"].max()) / recorde * 100.0
                if pct7 < vmax_min:
                    sinais.append((1, "vmax", "Pouco estímulo de velocidade",
                                   f"{pct7:.0f}% do recorde em {VMAX_JANELA_DIAS} dias · mín {vmax_min:.0f}%",
                                   {"valor": round(pct7), "janela": VMAX_JANELA_DIAS, "minimo": vmax_min,
                                    "acao": f"Incluir sprint a pelo menos {recorde * vmax_min / 100:.1f} km/h ({vmax_min:.0f}% do recorde "
                                            f"de {recorde:.1f}) na próxima sessão sem jogo no dia seguinte."}))

        # 3) Exposição HSR / Sprint da SEMANA (carga acumulada do microciclo)
        #    vs jogo mais exigente.
        gt = treinos_recentes[treinos_recentes["Jogador"] == jog]
        for col, chaves, etiqueta in (
            ("HSR (m)", ("hsr_semana_baixo", "hsr_semana_alto"), "HSR"),
            ("Sprint (m)", ("sprint_semana_baixo", "sprint_semana_alto"), "Sprint"),
        ):
            # Limite inferior proporcional à parte da semana já feita; o
            # superior não: passar o máximo da semana a meio dela já é alto.
            ref = (lim[chaves[0]] * progresso["fracao"], lim[chaves[1]])
            if ref[1] <= 0:  # zonas desligadas → sem aviso para esta métrica
                continue
            if col not in df.columns or gt.empty or gt[col].dropna().empty:
                continue
            ref_jog = refs_jogo.get(col, {}).get(jog)
            if not ref_jog or ref_jog["valor"] <= 0:
                continue
            match_val = ref_jog["valor"]
            treino_val = float(gt[col].sum())  # carga ACUMULADA da semana (microciclo)
            r = treino_val / match_val
            zona = _zona_ratio(r, ref)
            if zona == "baixo":
                falta = max(0.0, lim[chaves[0]] * match_val - treino_val)
                sinais.append((1, f"{etiqueta.lower()}_baixo", f"Exposição {etiqueta} baixa",
                               f"{etiqueta} semana {r:.2f}× jogo · ref {ref[0]:.2f}–{ref[1]:.2f}",
                               {"valor": round(r, 2), "ref": [ref[0], ref[1]], "em_falta": round(falta),
                                "acao": _acao_falta(etiqueta, falta, progresso)}))
            elif zona == "alto":
                sinais.append((1, f"{etiqueta.lower()}_alto", f"Exposição {etiqueta} elevada",
                               f"{etiqueta} semana {r:.2f}× jogo · ref {ref[0]:.2f}–{ref[1]:.2f}",
                               {"valor": round(r, 2), "ref": [ref[0], ref[1]],
                                "acao": f"A semana já vai em {r:.2f}× o jogo (máx. {ref[1]:.2f}×): "
                                        f"retirar {etiqueta} das sessões que faltam ({treino_val - ref[1] * match_val:.0f} m acima)."}))

        # 4) Última sessão muito acima do habitual DESTE jogador no mesmo Dia MD
        #    (z ≥ 2 face às suas sessões equivalentes; precisa de ≥ 3).
        for sinal in sessao_fora_do_habitual(gfull, df_max=data_max, e_jogo=e_jogo):
            sinais.append(sinal)

        # 5) Prontidão: CMJ e Hooper face ao próprio jogador.
        c = cmj.get(jog)
        if c and c["valido"]:
            sev = sev_cmj(c, lim)
            if sev:
                sinais.append((sev, "cmj", "Queda do CMJ",
                               f"CMJ {c['variacao_pct']:+.1f}% vs média própria ({c['ultimo']:.1f} vs {c['media_base']:.1f} cm)",
                               {"valor": c["variacao_pct"], "limite": -lim["cmj_queda_alto"],
                                "acao": "Retirar o volume de alta intensidade hoje (sprints, saltos, mudanças de direção) "
                                        "e repetir o CMJ antes da próxima sessão exigente."}))
        # 6) Sem sessões registadas há vários dias (lesão por marcar, ausência
        #    ou esquecimento no registo — de qualquer forma, o PF deve saber).
        if data_max is not None and pd.notna(data_max) and gfull["Data"].notna().any():
            dias = int((data_max - gfull["Data"].max()).days)
            if dias >= float(lim["dias_sem_dados"]):
                sinais.append((1, "sem_dados", "Sem dados recentes", f"{dias} dias sem sessão registada",
                               {"valor": dias, "limite": lim["dias_sem_dados"],
                                "acao": "Confirmar o estado do jogador (lesão ou ausência por marcar?) ou importar as sessões em falta."}))

        # 7) PSE e GPS em sentidos opostos na última sessão.
        dz = divergencia_pse_gps(gfull)
        if dz is not None:
            sinais.append((1, "pse_gps", "PSE e GPS em sentidos opostos",
                           f"Δz {dz:+.1f} na última sessão",
                           {"valor": dz, "acao": "Confirmar a PSE com o jogador e verificar o registo GPS da última sessão; "
                                                 "se ambos estiverem certos, tratar como possível fadiga."}))

        h = hooper.get(jog)
        if h and h["valido"]:
            sev = _sev(h["diferenca"], lim["hooper_subida_alto"], lim["hooper_subida_muito_alto"])
            if h["ultimo"] >= lim["hooper_alto"]:
                sev = 2
            if sev:
                dif = f" ({h['diferenca']:+.0f} vs média)" if h["diferenca"] is not None else ""
                sinais.append((sev, "hooper", "Bem-estar abaixo do habitual", f"Hooper {h['ultimo']:.0f}{dif}",
                               {"valor": h["ultimo"], "limite": lim["hooper_alto"], "acao": _acao_hooper(gfull)}))

        if not sinais:
            avisos.append({"player_id": player_id, "player_name": str(jog), "status": ALERT_STATUS_NORMAL,
                           "primary_reason": "ok", "reason_text": "Sem sinais", "metric_value": "", "sinais": []})
            continue

        sinais.sort(key=lambda s: -s[0])
        total_sev = sum(s[0] for s in sinais)
        topo = sinais[0]
        status = ALERT_STATUS_HIGH_ATTENTION if total_sev >= 2 else ALERT_STATUS_ATTENTION
        avisos.append({"player_id": player_id, "player_name": str(jog), "status": status,
                       "primary_reason": topo[1], "reason_text": topo[2], "metric_value": topo[3],
                       # Todos os sinais, para a web agrupar por motivo.
                       "sinais": [{"chave": c, "texto": t, "detalhe": d, "severidade": sev, "acao": d.get("acao")}
                                  for sev, c, t, _, d in sinais]})

    ordem = {ALERT_STATUS_HIGH_ATTENTION: 0, ALERT_STATUS_ATTENTION: 1, ALERT_STATUS_NORMAL: 2}
    avisos.sort(key=lambda a: ordem.get(a["status"], 3))
    return avisos


def obter_exposicao_semana(df, limites: dict[str, float] | None = None, microciclo: int | None = None) -> dict:
    """Exposição HSR/Sprint da SEMANA (carga acumulada do microciclo mais
    recente) ÷ jogo mais exigente, por jogador — para um painel SEMPRE VISÍVEL
    no dashboard.

    Ao contrário dos avisos (que só surgem fora da zona de referência), isto
    mostra os rácios mesmo quando estão dentro da zona, e explica porque está
    vazio (sem jogos, sem HSR/Sprint…) em vez de simplesmente não aparecer.
    """
    import pandas as pd

    from app.services.limites_service import DEFAULTS

    lim = {**DEFAULTS, **(limites or {})}
    vazio = {"tem_dados": False, "motivo": None, "microciclo": None, "microciclos_disponiveis": [], "metricas": []}

    if df is None or df.empty or "Jogador" not in df.columns:
        return {**vazio, "motivo": "Ainda não há dados carregados."}
    if "Tipo" not in df.columns and "Dia MD" not in df.columns:
        return {**vazio, "motivo": "Os dados não têm a coluna «Tipo» nem «Dia MD» (treino/jogo)."}

    df = df.copy()
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")

    e_jogo = mascara_jogo(df)
    jogos = df[e_jogo]
    if jogos.empty:
        return {**vazio, "motivo": "Sem jogos registados — o rácio precisa de pelo menos um jogo como referência."}

    disponiveis: list[int] = []
    if "Microciclo (Nr)" in df.columns and df["Microciclo (Nr)"].notna().any():
        disponiveis = sorted({int(m) for m in df["Microciclo (Nr)"].dropna().unique()})
        vazio = {**vazio, "microciclos_disponiveis": disponiveis}
        mc = microciclo if microciclo is not None and microciclo in disponiveis else disponiveis[-1]
        recente = df[df["Microciclo (Nr)"] == mc]
        microciclo = int(mc)
    elif "Data" in df.columns and df["Data"].notna().any():
        ref = df["Data"].max()
        recente = df[df["Data"] >= ref - pd.Timedelta(days=VMAX_JANELA_DIAS)]
        microciclo = None
    else:
        recente = df
        microciclo = None
    treinos = recente[~e_jogo.loc[recente.index]]
    if treinos.empty:
        return {**vazio, "motivo": "Este microciclo ainda não tem treinos.", "microciclo": microciclo}
    progresso = progresso_microciclo(df, e_jogo, microciclo)

    # Posição por jogador (última registada) — para a leitura por posição.
    if "Posição" in treinos.columns:
        pos_map = treinos.dropna(subset=["Jogador"]).groupby("Jogador")["Posição"].last().to_dict()
    else:
        pos_map = {}

    metricas_def = [
        ("HSR (m)", ("hsr_semana_baixo", "hsr_semana_alto"), "hsr", "HSR"),
        ("Sprint (m)", ("sprint_semana_baixo", "sprint_semana_alto"), "sprint", "Sprint"),
    ]
    metricas = []
    for col, chaves, chave, label in metricas_def:
        if col not in df.columns or jogos[col].dropna().empty:
            continue
        ref_semana = (lim[chaves[0]], lim[chaves[1]])
        ref = (ref_semana[0] * progresso["fracao"], ref_semana[1])  # zona até hoje
        refs = referencias_jogo(
            jogos, col, jogadores={j: pos_map.get(j, "") for j in treinos["Jogador"].dropna().unique()},
        )
        jogadores = []
        for jog in sorted(treinos["Jogador"].dropna().unique().tolist()):
            gt = treinos[treinos["Jogador"] == jog]
            ref_jog = refs.get(jog)
            if gt[col].dropna().empty or not ref_jog or ref_jog["valor"] <= 0:
                continue
            match_val = ref_jog["valor"]
            soma = float(gt[col].sum())
            r = soma / match_val
            posicao = pos_map.get(jog) if isinstance(pos_map.get(jog), str) else "—"
            # Alvo: metros em falta para chegar ao limite inferior da zona da
            # SEMANA (o que ainda falta fazer até ao fim do microciclo).
            minimo = ref_semana[0] * match_val
            jogadores.append({
                "jogador": jog, "posicao": posicao, "ratio": round(r, 2), "zona": _zona_ratio(r, ref),
                "n_treinos": int(gt[col].notna().sum()),
                "acumulado": round(soma, 0),
                "referencia": round(match_val, 0),
                "fonte_referencia": ref_jog["fonte"],
                "em_falta": round(max(0.0, minimo - soma), 0),
            })
        if not jogadores:
            continue
        jogadores.sort(key=lambda x: x["ratio"])
        ratios = [j["ratio"] for j in jogadores]
        ratio_equipa = round(sum(ratios) / len(ratios), 2)

        # Agregado por posição: rácio médio de cada posição.
        grupos: dict[str, list] = {}
        for j in jogadores:
            grupos.setdefault(j["posicao"], []).append(j["ratio"])
        posicoes = [
            {
                "posicao": pos,
                "n_jogadores": len(rs),
                "ratio": round(sum(rs) / len(rs), 2),
                "zona": _zona_ratio(round(sum(rs) / len(rs), 2), ref),
            }
            for pos, rs in grupos.items()
        ]
        posicoes.sort(key=lambda p: str(p["posicao"]))

        metricas.append({
            "chave": chave, "label": label, "ref": [ref_semana[0], ref_semana[1]],
            "ref_ate_hoje": [round(ref[0], 2), ref[1]],
            "ratio_equipa": ratio_equipa, "zona_equipa": _zona_ratio(ratio_equipa, ref),
            "posicoes": posicoes,
            "jogadores": jogadores,
        })

    if not metricas:
        return {**vazio, "motivo": "Sem HSR/Sprint suficientes no microciclo e nos jogos.", "microciclo": microciclo}
    return {"tem_dados": True, "motivo": None, "microciclo": microciclo,
            "microciclos_disponiveis": disponiveis, "progresso": progresso, "metricas": metricas}
