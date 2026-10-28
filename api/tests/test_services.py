"""Testes dos serviços de cálculo — sem base de dados.

Cada teste substitui `carregar_df_equipa` do serviço em causa por um
DataFrame sintético, para validar a matemática (baseline, %HSR, benchmark,
quadrantes, limiares) de forma reprodutível.

Correr: cd api && pytest
"""
from datetime import date

import pandas as pd
import pytest


def _df(rows):
    df = pd.DataFrame(rows)
    df["Data"] = pd.to_datetime(df["Data"])
    return df


def _sessao(jogador, data, mc, dia, **kw):
    base = {
        "Jogador": jogador, "Posição": kw.get("pos", "CM"), "Data": data, "Tipo": kw.get("tipo", "Treino"),
        "Dia MD": dia, "Microciclo (Nr)": mc, "Distância Total (m)": kw.get("dist", 5000),
        "HSR (m)": kw.get("hsr", 500), "Sprint (m)": kw.get("sprint", 100), "Acc (n)": 30, "Dcc (n)": 28,
        "Vel. Máx (km/h)": kw.get("vmax", 30), "Carga Interna": kw.get("ci", 300),
        "PSE Sessão": kw.get("pse", 6), "Duração (min)": 90, "Hooper Index": kw.get("hooper", 10),
    }
    return base


# ── Carga externa ──────────────────────────────────────────────────────────
def test_carga_externa_kpis_e_filtro(monkeypatch):
    import app.services.carga_externa_service as ce
    rows = []
    for i, d in enumerate(["2026-08-01", "2026-08-03", "2026-08-05"]):
        for nome in ["Ana", "Rui"]:
            rows.append(_sessao(nome, d, 1, "MD-3", dist=5000 + i * 200, hsr=500 + i * 40))
    monkeypatch.setattr(ce, "carregar_df_equipa", lambda t: _df(rows))

    out = ce.obter_carga_externa("t")
    assert out["tem_dados"] is True
    assert out["sessao_recente"] == "2026-08-05"
    hsr = next(k for k in out["kpis"] if k["chave"] == "hsr_m")
    assert hsr["atual"] == 580 and hsr["baseline"] == 520  # (500,540) media=520

    # filtro por jogador
    so_ana = ce.obter_carga_externa("t", jogador="Ana")
    assert [j["jogador"] for j in so_ana["jogadores"]] == ["Ana"]


def test_carga_externa_pct_hsr(monkeypatch):
    import app.services.carga_externa_service as ce
    rows = [_sessao("Ana", "2026-08-05", 1, "MD-3", dist=10000, hsr=1000, sprint=200)]
    monkeypatch.setattr(ce, "carregar_df_equipa", lambda t: _df(rows))
    out = ce.obter_carga_externa("t")
    ana = out["jogadores"][0]
    assert ana["derivados"]["pct_hsr"] == 10.0   # 1000/10000
    assert ana["derivados"]["pct_sprint"] == 20.0  # 200/1000


def test_carga_externa_sessao_compara_com_o_mesmo_dia_md(monkeypatch):
    """A sessão mais recente (MD-4) é comparada com os MD-4 anteriores, não
    com tudo o que houve nos últimos 28 dias."""
    import app.services.carga_externa_service as ce
    rows = []
    for d, md, dist in [("2026-08-01", "MD-4", 6000), ("2026-08-03", "MD-2", 3000), ("2026-08-04", "MD-1", 2500),
                        ("2026-08-08", "MD-4", 7000), ("2026-08-10", "MD-2", 3500), ("2026-08-15", "MD-4", 8000)]:
        rows.append(_sessao("Ana", d, 1, md, dist=dist))
    monkeypatch.setattr(ce, "carregar_df_equipa", lambda t: _df(rows))
    out = ce.obter_carga_externa("t")
    dist = next(k for k in out["kpis"] if k["chave"] == "distancia_total_m")
    assert dist["atual"] == 8000 and dist["baseline"] == 6500 and dist["n_baseline"] == 2
    assert out["escopo"]["baseline_label"] == "média dos MD-4 anteriores"


def test_variacao_classificar():
    from app.services.variacao import classificar
    assert classificar(130, [100, 102, 98, 101])["estado"] == "alto"        # varia pouco → 130 é muito
    assert classificar(130, [70, 130, 100, 100])["estado"] == "normal"      # varia muito → 130 é normal
    c = classificar(120, [100, 100])
    assert c["metodo"] == "percentagem" and c["estado"] == "alto"
    assert classificar(120, [100])["estado"] == "insuficiente"


def test_alerta_sessao_fora_do_habitual():
    from app.services.alertas_service import sessao_fora_do_habitual
    # 4 sessões MD-3 de referência (mínimo para o z-score) e a última muito acima.
    rows = [_sessao("Ana", d, 1, "MD-3", hsr=h) for d, h in [("2026-07-25", 405), ("2026-08-01", 400), ("2026-08-08", 420), ("2026-08-15", 410), ("2026-08-22", 700)]]
    rows += [_sessao("Ana", "2026-08-20", 1, "MD-5", hsr=900)]
    sinais = sessao_fora_do_habitual(_df(rows))
    assert [s[1] for s in sinais] == ["habitual_hsr"] and sinais[0][4]["dia_md"] == "MD-3"
    # Com só 3 referências não há z-score fiável → sem aviso.
    assert sessao_fora_do_habitual(_df(rows[1:])) == []
    normal = [_sessao("Ana", d, 1, "MD-3", hsr=h) for d, h in [("2026-08-01", 400), ("2026-08-08", 600), ("2026-08-15", 450), ("2026-08-22", 500)]]
    assert sessao_fora_do_habitual(_df(normal)) == []


# ── Comparações ────────────────────────────────────────────────────────────
def test_comparacao_jogadores_benchmark(monkeypatch):
    import app.services.comparacoes_service as cs
    rows = []
    for nome, dist in [("Ana", 6000), ("Rui", 4000)]:
        for d in ["2026-08-01", "2026-08-03"]:
            rows.append(_sessao(nome, d, 1, "MD-3", dist=dist))
    monkeypatch.setattr(cs, "carregar_df_equipa", lambda t: _df(rows))
    out = cs.obter_comparacao_jogadores("t")
    assert out["benchmark"]["distancia_total_m"] == 5000  # media de 6000 e 4000


def test_comparacao_posicoes_agrega(monkeypatch):
    import app.services.comparacoes_service as cs
    rows = [
        _sessao("Ana", "2026-08-01", 1, "MD-3", pos="CB", dist=5000),
        _sessao("Nuno", "2026-08-01", 1, "MD-3", pos="CB", dist=5200),
        _sessao("Rui", "2026-08-01", 1, "MD-3", pos="CM", dist=4000),
    ]
    monkeypatch.setattr(cs, "carregar_df_equipa", lambda t: _df(rows))
    out = cs.obter_comparacao_posicoes("t")
    cb = next(p for p in out["posicoes"] if p["posicao"] == "CB")
    assert cb["n_jogadores"] == 2 and cb["valores"]["distancia_total_m"] == 5100


# ── Match benchmark ────────────────────────────────────────────────────────
def test_sessao_vs_equivalentes(monkeypatch):
    import app.services.sessao_service as ss
    rows = []
    for d, f in [("2026-08-01", 1.0), ("2026-08-08", 1.0), ("2026-08-15", 1.3)]:
        for nome in ["Ana", "Rui"]:
            rows.append(_sessao(nome, d, 1, "MD-1", dist=5000 * f))
    monkeypatch.setattr(ss, "carregar_df_equipa", lambda t: _df(rows))
    out = ss.obter_sessao("t", "2026-08-15", "Treino")
    dist = next(k for k in out["kpis"] if k["chave"] == "distancia_total_m")
    assert dist["atual"] == 6500 and dist["baseline"] == 5000 and dist["estado"] == "alto"


# ── Combinada ──────────────────────────────────────────────────────────────
def test_combinada_quadrantes(monkeypatch):
    import app.services.combinada_service as cb
    perfis = {"Ana": (6000, 450), "Rui": (4000, 450), "Ze": (6000, 250), "Nuno": (4000, 250)}
    rows = [_sessao(n, "2026-08-01", 1, "MD-1", dist=dist, ci=ci) for n, (dist, ci) in perfis.items()]
    monkeypatch.setattr(cb, "carregar_df_equipa", lambda t: _df(rows))
    out = cb.obter_combinada("t", eixo="distancia")
    flags = {j["jogador"]: j["flag"] for j in out["jogadores"]}
    assert flags["Ana"] == "Ext ↑ · Int ↑"
    assert flags["Nuno"] == "Ext ↓ · Int ↓"
    assert flags["Ze"].startswith("Ext ↑")


# ── Jogador / Vmax ─────────────────────────────────────────────────────────
def test_jogador_vmax_pct_recorde_da_epoca(monkeypatch):
    import app.services.jogador_service as js
    rows = []
    for mc, vmax in [(1, 28), (2, 32)]:
        for d in ["05", "07"]:
            rows.append(_sessao("Ana", f"2026-0{mc}-{d}", mc, "MD-3", vmax=vmax))
    monkeypatch.setattr(js, "carregar_df_equipa", lambda t: _df(rows))

    full = js.obter_jogador("t", "Ana")
    win = js.obter_jogador("t", "Ana", microciclo=1)
    assert full["vel_max_recorde"] == 32
    assert win["vel_max_recorde"] == 32  # recorde da época mantém-se na janela
    assert len(win["evolucao_vmax"]) == 2
    assert win["evolucao_vmax"][0]["pct"] == 88.0  # 28/32


# ── Importação robusta ──────────────────────────────────────────────────────
def _csv_bytes(cabecalho, linhas):
    import io
    buf = io.StringIO()
    buf.write(",".join(cabecalho) + "\n")
    for ln in linhas:
        buf.write(",".join(str(v) for v in ln) + "\n")
    return buf.getvalue().encode("utf-8")


def test_normalizar_tipo_reconhece_variantes_de_jogo():
    """A deteção de jogo tolera grafias diferentes; treino e outros tipos ficam
    tal como estão (contam como treino a jusante)."""
    from utils.dados import normalizar_tipo
    for v in ["Jogo", "jogo", "JOGO", "Match", "match day", "Competição", "COMPETICAO",
              "Jornada", "Amigável", "friendly", "Partida"]:
        assert normalizar_tipo(v) == "Jogo", v
    assert normalizar_tipo("Treino") == "Treino"
    assert normalizar_tipo("Recuperação") == "Recuperação"  # preservado
    assert normalizar_tipo("Ginásio") == "Ginásio"
    assert normalizar_tipo(None) is None


def test_auto_mapa_reconhece_aliases():
    from utils.dados import auto_mapa
    mapa = auto_mapa(["Nome", "Distance", "HSR", "Vmax", "Xpto"])
    assert mapa["Nome"] == "Jogador"
    assert mapa["Distance"] == "Distância Total (m)"
    assert mapa["HSR"] == "HSR (m)"
    assert mapa["Vmax"] == "Vel. Máx (km/h)"
    assert "Xpto" not in mapa  # coluna desconhecida não é mapeada


def test_auto_mapa_reconhece_cabecalhos_ja_canonicos():
    """Um ficheiro já bem formatado (cabeçalhos canónicos) tem de ser
    reconhecido sem mapeamento manual — inclui as obrigatórias e as métricas."""
    from utils.dados import auto_mapa
    cols = ["Jogador", "Posição", "Tipo", "Dia MD", "Data", "Microciclo (Nr)", "HSR (m)", "Vel. Máx (km/h)"]
    mapa = auto_mapa(cols)
    for c in cols:
        assert mapa.get(c) == c, c  # cada canónico mapeia para si próprio


def test_carregar_dados_com_mapa_usa_mapeamento_explicito():
    from utils.dados import carregar_dados_com_mapa
    import io
    dados = _csv_bytes(
        ["Atleta", "Fecha", "MinhaDist", "Tipo"],
        [["Ana", "2026-08-01", 5000, "Treino"], ["Rui", "2026-08-01", 4000, "Treino"]],
    )
    buf = io.BytesIO(dados); buf.name = "x.csv"
    mapa = {"Atleta": "Jogador", "Fecha": "Data", "MinhaDist": "Distância Total (m)", "Tipo": "Tipo"}
    df = carregar_dados_com_mapa(buf, mapa)
    assert set(["Jogador", "Data", "Distância Total (m)", "Tipo"]).issubset(df.columns)
    assert sorted(df["Jogador"].tolist()) == ["Ana", "Rui"]
    assert df[df["Jogador"] == "Ana"]["Distância Total (m)"].iloc[0] == 5000


def test_analisar_ficheiro_diagnostico():
    from app.services.importacao_service import analisar_ficheiro
    dados = _csv_bytes(
        ["Nome", "Data", "Distance", "HSR", "Sprint", "Vmax", "Tipo"],
        [["Ana", "2026-08-01", 5000, 500, 100, 30, "Treino"],
         ["Rui", "2026-08-01", 4000, 400, 80, 29, "Treino"]],
    )
    out = analisar_ficheiro("carga.csv", dados)
    assert out["ok"] is True
    assert out["n_linhas"] == 2
    assert out["pode_importar"] is True
    assert out["em_falta"]["criticas"] == []
    mapa = out["mapa_sugerido"]
    assert mapa["Nome"] == "Jogador"
    assert mapa["Distance"] == "Distância Total (m)"
    assert out["resumo"]["jogadores"] == 2
    assert len(out["preview"]["linhas"]) == 2


def test_analisar_ficheiro_sinaliza_falta_de_jogador():
    from app.services.importacao_service import analisar_ficheiro
    dados = _csv_bytes(
        ["Coluna1", "Data", "Distance"],
        [["x", "2026-08-01", 5000]],
    )
    out = analisar_ficheiro("carga.csv", dados)
    # Sem coluna reconhecível de jogador → crítica em falta, não importável.
    assert "Jogador" in out["em_falta"]["criticas"]
    assert out["pode_importar"] is False
    assert any(a["nivel"] == "erro" for a in out["avisos"])


# ── Motor de alertas unificado ──────────────────────────────────────────────
def test_classificar_acwr_partilhado_e_configuravel():
    """O classificador de ACWR é a fonte única partilhada pelo dashboard e pela
    Análise: por omissão reproduz os limiares clássicos (1.3 / 1.5) e respeita
    limiares personalizados."""
    from app.services.alertas_service import classificar_acwr
    assert classificar_acwr(1.35)[0] == 1        # ≥ acwr_alto (1.3) → atenção
    assert "ACIMA" in classificar_acwr(1.35)[1] and "MUITO" not in classificar_acwr(1.35)[1]
    assert classificar_acwr(1.6)[0] == 2         # ≥ acwr_muito_alto (1.5) → risco
    assert "MUITO ACIMA" in classificar_acwr(1.6)[1]
    assert classificar_acwr(1.0)[0] == 0         # ok
    # Limiares personalizados sobem a fasquia → 1.35 deixa de ser alerta.
    assert classificar_acwr(1.35, {"acwr_alto": 1.5, "acwr_muito_alto": 1.8})[0] == 0
    assert classificar_acwr(None)[1] == "❓"


def test_analise_alertas_respeitam_limites(monkeypatch):
    """A página Análise deixou de ter limiares fixos no código: usa os mesmos
    limites configuráveis do dashboard. Subir o limiar de Hooper silencia o
    alerta de wellness sem tocar em mais nada."""
    import app.services.analise_service as an
    import app.services.prontidao_service as pr
    from datetime import date
    # Sessão de hoje: o Hooper só conta para hoje se for dos últimos 3 dias.
    rows = [_sessao("Ana", date.today().isoformat(), 1, "MD-3", hooper=15)]
    monkeypatch.setattr(an, "carregar_df_equipa", lambda t: _df(rows))
    monkeypatch.setattr(an, "listar_estados", lambda t: [])
    monkeypatch.setattr(pr, "_carregar_testes", lambda t: pd.DataFrame(columns=["nome", "data", "altura_salto_cm"]))

    # hooper_alto por omissão → Hooper 15 dispara alerta de wellness.
    tipos = {a["tipo"] for a in an.obter_analise("t")["alertas"]["prioritarios"]}
    assert "Wellness" in tipos

    # Subir o limiar para 20 → 15 já não dispara.
    tipos2 = {a["tipo"] for a in an.obter_analise("t", limites={"hooper_alto": 20})["alertas"]["prioritarios"]}
    assert "Wellness" not in tipos2


# ── Avisos do dashboard (exposição vs jogo) ─────────────────────────────────
def test_avisos_dashboard_exposicao_semanal_e_velocidade():
    """O dashboard usa a carga ACUMULADA da semana (soma do microciclo) ÷ jogo
    mais exigente, com zonas 0.60–0.90. Sinaliza exposição HSR baixa e pouco
    estímulo de velocidade; um jogador dentro das zonas fica «normal»."""
    from app.services.alertas_service import construir_avisos_dashboard
    rows = []
    # Ana: jogo (recorde Vmax 32, HSR jogo 1000, Sprint 200) + microciclo fraco:
    # HSR semana 250+250=500 → 0.50× jogo (< 0.60 → baixo); Vmax 27 = 84% (< 90%).
    rows.append(_sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=32))
    for d in ["2026-08-03", "2026-08-05"]:
        rows.append(_sessao("Ana", d, 5, "MD-1", tipo="Treino", hsr=250, sprint=75, vmax=27))
    # Rui: dentro das zonas — HSR semana 375+375=750 → 0.75×; Sprint 75+75=150 →
    # 0.75×; Vmax 31 = 97%.
    rows.append(_sessao("Rui", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=32))
    for d in ["2026-08-03", "2026-08-05"]:
        rows.append(_sessao("Rui", d, 5, "MD-1", tipo="Treino", hsr=375, sprint=75, vmax=31))

    # ACWR desligado: este teste isola a exposição (os dados saltam um mês).
    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}
    avisos = {a["player_name"]: a for a in construir_avisos_dashboard(_df(rows), sem_acwr)}
    assert avisos["Ana"]["status"] != "normal"
    assert avisos["Rui"]["status"] == "normal"


def test_avisos_dashboard_zonas_configuraveis():
    """Baixar o limiar «baixo» de HSR silencia o aviso de exposição HSR baixa."""
    from app.services.alertas_service import construir_avisos_dashboard
    rows = [_sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=32)]
    for d in ["2026-08-03", "2026-08-05"]:
        # HSR semana 500 → 0.50×; Vmax 32 (jogo) garante estímulo de velocidade.
        rows.append(_sessao("Ana", d, 5, "MD-1", tipo="Treino", hsr=250, sprint=75, vmax=32))
    df = _df(rows)

    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}  # isola a exposição
    padrao = {a["player_name"]: a for a in construir_avisos_dashboard(df, sem_acwr)}
    assert padrao["Ana"]["status"] != "normal"  # 0.50 < 0.60 → HSR baixa

    baixado = {a["player_name"]: a for a in construir_avisos_dashboard(df, {**sem_acwr, "hsr_semana_baixo": 0.40})}
    assert baixado["Ana"]["status"] == "normal"  # 0.50 ≥ 0.40 → sem aviso


def test_exposicao_semana_visivel_e_sem_jogos():
    """O painel de exposição mostra os rácios por jogador (mesmo dentro da zona)
    e explica-se quando não há jogo de referência."""
    from app.services.alertas_service import obter_exposicao_semana
    rows = [_sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, sprint=200)]
    for d in ["2026-08-03", "2026-08-05"]:
        rows.append(_sessao("Ana", d, 5, "MD-1", tipo="Treino", hsr=250, sprint=90))
    df = _df(rows)

    out = obter_exposicao_semana(df)
    assert out["tem_dados"] is True
    hsr = next(m for m in out["metricas"] if m["chave"] == "hsr")
    ana = next(j for j in hsr["jogadores"] if j["jogador"] == "Ana")
    assert ana["ratio"] == 0.50 and ana["zona"] == "baixo"  # (250+250)/1000
    assert "posicao" in ana  # cada jogador leva a posição
    assert any(p["posicao"] and "ratio" in p for p in hsr["posicoes"])  # agregado por posição

    # Sem jogos → estado explicado, não vazio silencioso.
    so_treinos = obter_exposicao_semana(df[df["Tipo"] != "Jogo"])
    assert so_treinos["tem_dados"] is False
    assert "jogo" in so_treinos["motivo"].lower()


def test_combinada_usa_pse_sem_carga_interna(monkeypatch):
    """Sem «Carga Interna» (equipas que só registam PSE), a Externa×Interna cai
    para a PSE em vez de aparecer vazia."""
    import app.services.combinada_service as cs
    rows = []
    for nome, dist, pse in [("Ana", 6000, 7.5), ("Rui", 4000, 5.0)]:
        for d in ["2026-08-01", "2026-08-03"]:
            rows.append({"Jogador": nome, "Posição": "CM", "Data": pd.to_datetime(d),
                         "Microciclo (Nr)": 1, "Dia MD": "MD-3", "Distância Total (m)": dist, "PSE Sessão": pse})
    monkeypatch.setattr(cs, "carregar_df_equipa", lambda t: pd.DataFrame(rows))

    out = cs.obter_combinada("t")
    assert out["tem_dados"] is True
    assert out["eixo_interno"]["label"] == "PSE"
    assert len(out["jogadores"]) == 2


def test_combinada_seletor_de_eixo(monkeypatch):
    import app.services.combinada_service as cs
    rows = []
    for nome, dist, acc, dcc, dur, pse in [("Ana", 6000, 40, 30, 60, 7), ("Rui", 4000, 20, 10, 40, 5), ("Ze", 5000, 30, 30, 90, 4)]:
        rows.append({"Jogador": nome, "Posição": "CM", "Data": pd.to_datetime("2026-08-01"), "Microciclo (Nr)": 1,
                     "Dia MD": "MD-3", "Distância Total (m)": dist, "Acc (n)": acc, "Dcc (n)": dcc,
                     "Duração (min)": dur, "PSE Sessão": pse, "Carga Interna": pse * dur})
    monkeypatch.setattr(cs, "carregar_df_equipa", lambda t: pd.DataFrame(rows))

    out = cs.obter_combinada("t")  # por defeito Acc + Dcc contra Carga Interna
    assert out["eixo"] == "accdcc" and out["eixo_interno"]["label"] == "Carga Interna"
    assert {j["jogador"]: j["externo"] for j in out["jogadores"]} == {"Ana": 70, "Rui": 30, "Ze": 60}
    assert {e["chave"] for e in out["eixos"]} == {"accdcc", "accdcc_min", "distancia", "distancia_min"}

    pm = cs.obter_combinada("t", eixo="accdcc_min")  # por minuto contra a PSE
    assert pm["eixo_interno"]["label"] == "PSE"
    assert {j["jogador"]: j["externo"] for j in pm["jogadores"]}["Ze"] == round(60 / 90, 2)
    assert cs.obter_combinada("t", eixo="hsr")["eixo"] == "accdcc"  # sem HSR → volta ao padrão


# ── Cache do dataframe de equipa ────────────────────────────────────────────
def test_cache_df_equipa_reutiliza_e_invalida(monkeypatch):
    """A leitura à BD é reutilizada dentro do TTL, cada chamada devolve uma
    cópia (mutar não corrompe o cache) e invalidar força nova leitura."""
    import app.services.dados_equipa as de
    de.invalidar_cache_equipa()
    chamadas = {"n": 0}

    def fake(team_id):
        chamadas["n"] += 1
        return pd.DataFrame({"Jogador": ["Ana"], "Tipo": ["Treino"]})

    monkeypatch.setattr(de, "_ler_df_equipa", fake)

    a = de.carregar_df_equipa("t")
    de.carregar_df_equipa("t")
    assert chamadas["n"] == 1  # segunda leitura veio do cache

    a.loc[0, "Jogador"] = "X"  # mutar a cópia não afeta o cache
    assert de.carregar_df_equipa("t").loc[0, "Jogador"] == "Ana"

    de.invalidar_cache_equipa("t")
    de.carregar_df_equipa("t")
    assert chamadas["n"] == 2  # após invalidar, relê da BD


# ── Wellness ─────────────────────────────────────────────────────────────────
def test_calcular_hooper_soma_deficits():
    """Hooper = Σ(5 − sub-score), com clamp a [1,5]; alto = pior bem-estar."""
    from app.services.wellness_service import calcular_hooper
    assert calcular_hooper(5, 5, 5, 5) == 0     # tudo ótimo → 0
    assert calcular_hooper(1, 1, 1, 1) == 16    # tudo péssimo → 16
    assert calcular_hooper(3, 3, 3, 3) == 8     # neutro
    assert calcular_hooper(9, 5, 5, 5) == 0     # clamp acima de 5
    assert calcular_hooper(0, 5, 5, 5) == 4     # clamp abaixo de 1 (=1 → 5-1=4)


# ── Assistente de IA (montagem do snapshot) ─────────────────────────────────
def test_alta_velocidade_relatorio_exclui_jogos():
    """A exposição a alta velocidade do relatório semanal usa só treinos: o jogo
    do microciclo escolhido não entra na soma nem no benchmark das outras semanas."""
    from app.services.relatorio_service import _alta_velocidade_html
    rows = [
        # Semana 26: 2 treinos de 300 m HSR (600) + jogo de 1000 m.
        _sessao("Ana", "2026-08-03", 26, "MD-3", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-05", 26, "MD-1", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-07", 26, "MD", tipo="Jogo", hsr=1000, sprint=200),
        # Semana 27: 2 treinos de 300 m HSR (600) + jogo de 1500 m.
        _sessao("Ana", "2026-08-10", 27, "MD-3", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-12", 27, "MD-1", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-14", 27, "MD", tipo="Jogo", hsr=1500, sprint=300),
    ]
    html = _alta_velocidade_html(_df(rows), 27)
    # Treinos iguais nas duas semanas → 100%; com jogos seria 2100/1600 = 131%.
    assert "<td>100%</td><td>100%</td>" in html


def test_exposicao_semana_escolhe_microciclo_e_exclui_jogos():
    """O painel calcula o microciclo pedido (não só o mais recente) e só soma
    treinos — um jogo registado com Tipo «Treino» mas dia MD também fica fora."""
    from app.services.alertas_service import obter_exposicao_semana
    rows = [
        _sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, sprint=200),
        # Microciclo 27: 2 treinos de 300 m + jogo mal etiquetado (Tipo Treino, dia MD).
        _sessao("Ana", "2026-08-03", 27, "MD-3", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-05", 27, "MD-1", hsr=300, sprint=50),
        _sessao("Ana", "2026-08-07", 27, "MD", tipo="Treino", hsr=900, sprint=150),
        # Microciclo 28 (mais recente): 1 treino de 800 m.
        _sessao("Ana", "2026-08-10", 28, "MD-2", hsr=800, sprint=50),
    ]
    df = _df(rows)

    out = obter_exposicao_semana(df, microciclo=27)
    assert out["microciclo"] == 27 and out["microciclos_disponiveis"] == [1, 27, 28]
    hsr = next(m for m in out["metricas"] if m["chave"] == "hsr")
    ana = hsr["jogadores"][0]
    # (300+300) ÷ média por 90' dos jogos (1000, 900) = 600/950 = 0.63 — o jogo
    # de dia MD não entra na soma dos treinos, mas conta como referência.
    assert ana["ratio"] == 0.63 and ana["n_treinos"] == 2
    assert ana["acumulado"] == 600 and ana["referencia"] == 950
    assert ana["em_falta"] == 0  # 0.63 ≥ 0.60 → já está na zona

    # Sem microciclo pedido → o mais recente.
    assert obter_exposicao_semana(df)["microciclo"] == 28


# ── Referência de jogo (normalizada por minutos) ─────────────────────────────
def test_referencia_jogo_por_jogo_completo_ultimos_jogos_completos():
    """Usa a média por jogo completo dos últimos 5 jogos com ≥ 75 % dos
    minutos; jogos curtos não contam."""
    from app.services.referencia_jogo import referencias_jogo
    rows = []
    # 6 jogos completos de 90' (HSR 600..1100) + 1 jogo de 20' com 300 m.
    for i, hsr in enumerate([600, 700, 800, 900, 1000, 1100]):
        r = _sessao("Ana", f"2026-08-{i + 1:02d}", i + 1, "MD", tipo="Jogo", hsr=hsr)
        rows.append(r)
    curto = _sessao("Ana", "2026-08-20", 9, "MD", tipo="Jogo", hsr=300)
    curto["Duração (min)"] = 20
    rows.append(curto)
    refs = referencias_jogo(_df(rows), "HSR (m)")
    # últimos 5 completos: 700..1100 → média 900; o jogo de 20' fica de fora.
    assert refs["Ana"]["valor"] == 900 and refs["Ana"]["fonte"] == "media_jogo"
    assert refs["Ana"]["n_jogos"] == 5 and refs["Ana"]["duracao_ref"] == 90


def test_referencia_jogo_normaliza_minutos_e_suplente_usa_posicao():
    """Num escalão com jogos de 60' a referência é o jogo de 60' (não 90');
    quem só jogou minutos curtos recebe a mediana da sua posição em vez de uma
    referência artificialmente baixa."""
    from app.services.referencia_jogo import referencias_jogo
    rui = _sessao("Rui", "2026-08-01", 1, "MD", tipo="Jogo", hsr=600, pos="EX")
    rui["Duração (min)"] = 60  # jogo de sub-13: 60' é o jogo inteiro
    suplente = _sessao("Zé", "2026-08-01", 1, "MD", tipo="Jogo", hsr=150, pos="EX")
    suplente["Duração (min)"] = 15
    refs = referencias_jogo(_df([rui, suplente]), "HSR (m)", jogadores={"Novo": "EX"})
    assert refs["Rui"]["valor"] == 600 and refs["Rui"]["duracao_ref"] == 60
    assert refs["Zé"]["valor"] == 600 and refs["Zé"]["fonte"] == "posicao"
    assert refs["Novo"]["fonte"] == "posicao"  # sem jogos → referência da posição


def test_referencia_jogo_pico_para_velocidade():
    """Métricas de pico (Vmax) não se normalizam: referência = pico em jogo."""
    from app.services.referencia_jogo import referencias_jogo
    a = _sessao("Ana", "2026-08-01", 1, "MD", tipo="Jogo", vmax=31)
    a["Duração (min)"] = 30
    b = _sessao("Ana", "2026-08-08", 2, "MD", tipo="Jogo", vmax=33)
    refs = referencias_jogo(_df([a, b]), "Vel. Máx (km/h)", peak=True)
    assert refs["Ana"]["valor"] == 33 and refs["Ana"]["fonte"] == "pico"


# ── Planeado vs realizado ────────────────────────────────────────────────────
def test_planeado_vs_realizado_ultima_sessao():
    """Compara a média real da sessão de treino mais recente com o planeado do
    seu microciclo/dia MD; o jogo posterior não conta como sessão de treino."""
    from app.services.planeado_realizado_service import comparar_sessao
    rows = [
        _sessao("Ana", "2026-08-03", 27, "MD-3", hsr=500, pse=7),
        _sessao("Rui", "2026-08-03", 27, "MD-3", hsr=300, pse=7),
        _sessao("Ana", "2026-08-01", 27, "MD-5", hsr=900),
        _sessao("Ana", "2026-08-07", 27, "MD", tipo="Jogo", hsr=1000),
    ]
    planeado = {(27, "MD-3"): {"pse": 7.0, "hsr_m": 500.0}}
    out = comparar_sessao(_df(rows), planeado)
    assert out["data"] == "2026-08-03" and out["dia_md"] == "MD-3" and out["microciclo"] == 27
    m = {x["chave"]: x for x in out["metricas"]}
    assert m["pse"]["estado"] == "ok" and m["pse"]["desvio_pct"] == 0
    assert m["hsr_m"]["real"] == 400 and m["hsr_m"]["desvio_pct"] == -20 and m["hsr_m"]["estado"] == "atencao"
    assert m["distancia_m"]["estado"] == "sem_plano"
    assert [j["jogador"] for j in out["jogadores_fora"]] == ["Rui"]  # 300 vs 500 = −40%


# ── Importação: qualidade dos dados ──────────────────────────────────────────
def test_importacao_avisos_qualidade():
    from app.services.importacao_service import avisos_qualidade
    rows = [
        _sessao("Ana", "2026-08-03", 27, "MD-3", hsr=300),
        _sessao("Ana", "2026-08-03", 27, "MD-3", hsr=200),   # bloco repetido
        _sessao("Rui", "2026-08-03", 27, "MD-3", vmax=52),   # Vmax impossível
        _sessao("Zé", "2026-08-03", None, "MD-3", hsr=6000),  # HSR > distância, sem microciclo
    ]
    textos = " | ".join(a["texto"] for a in avisos_qualidade(_df(rows)))
    assert "várias linhas no mesmo dia" in textos and "Ana" in textos
    assert "Vel. Máx (km/h)" in textos and "Rui" in textos
    assert "HSR maior do que a distância" in textos
    assert "sem «Microciclo (Nr)»" in textos
    # Dados limpos → nenhum aviso.
    assert avisos_qualidade(_df([_sessao("Ana", "2026-08-03", 27, "MD-3")])) == []


# ── ACWR diário ──────────────────────────────────────────────────────────────
def test_acwr_diario_conta_dias_de_descanso():
    """O EWMA corre sobre dias de calendário: descanso = carga 0 e duas sessões
    no mesmo dia somam-se."""
    from utils.calculos import serie_acwr_diaria, calcular_acwr_global
    rows = [_sessao("Ana", "2026-08-01", 1, "MD-3", ci=300), _sessao("Ana", "2026-08-04", 1, "MD-1", ci=300)]
    duplo = _sessao("Ana", "2026-08-04", 1, "MD-1", ci=100)
    duplo["Tipo"] = "Ginásio"
    rows.append(duplo)
    serie = serie_acwr_diaria(_df(rows))
    assert len(serie) == 4  # 1, 2, 3 e 4 de agosto (2 e 3 de descanso)
    assert list(serie["Carga Interna"]) == [300, 0, 0, 400]
    # O descanso faz a carga aguda (λ=0.25) cair mais do que a crónica.
    rel = serie["Carga Aguda"] / serie["Carga Crónica"]
    assert rel.iloc[2] < rel.iloc[0]
    # Período de arranque: com menos de 28 dias de série o ACWR fica vazio.
    assert serie["ACWR"].isna().all()
    assert calcular_acwr_global(_df(rows)) == {}


def test_acwr_so_aparece_depois_do_periodo_de_arranque():
    """Ao 28.º dia de série o ACWR passa a existir; antes disso é vazio."""
    from utils.calculos import MIN_DIAS_ACWR, serie_acwr_diaria, calcular_acwr_global
    datas = pd.date_range("2026-08-01", periods=40, freq="2D")
    rows = [_sessao("Ana", d.strftime("%Y-%m-%d"), 1, "MD-3", ci=300) for d in datas]
    serie = serie_acwr_diaria(_df(rows))
    assert serie["ACWR"].iloc[: MIN_DIAS_ACWR - 1].isna().all()
    assert serie["ACWR"].iloc[MIN_DIAS_ACWR - 1:].notna().all()
    assert calcular_acwr_global(_df(rows))["Ana"]["data"] == datas[-1]


def test_recorde_vmax_ignora_picos_isolados():
    """Um valor mais de 5 % acima do segundo melhor é pico de GPS; um recorde
    repetido (ou perto do seguinte) conta."""
    from utils.calculos import recorde_vmax
    assert recorde_vmax([28.0, 27.6, 33.5]) == 28.0       # 33,5 isolado = pico
    assert recorde_vmax([28.0, 27.6, 28.9]) == 28.9       # +3 % = recorde real
    assert recorde_vmax([30.0]) == 30.0
    assert recorde_vmax([None, float("nan")]) is None


# ── Prontidão ────────────────────────────────────────────────────────────────
def test_prontidao_cmj_hooper_e_estado():
    """CMJ abaixo da média própria + Hooper acima da média própria → reduzir;
    sem sinais → pronto; jogador lesionado → indisponível."""
    from app.services.prontidao_service import calcular_prontidao
    rows = []
    for d in ["2026-08-01", "2026-08-05", "2026-08-10"]:
        for nome in ("Ana", "Rui", "Zé"):
            rows.append(_sessao(nome, d, 1, "MD-3", ci=300, hooper=5))
    rows.append(_sessao("Ana", "2026-08-12", 1, "MD-3", ci=300, hooper=11))  # +6 vs média 5
    rows.append(_sessao("Rui", "2026-08-12", 1, "MD-3", ci=300, hooper=5))
    testes = pd.DataFrame([
        {"nome": "Ana", "data": "2026-07-20", "altura_salto_cm": 40},
        {"nome": "Ana", "data": "2026-07-27", "altura_salto_cm": 40},
        {"nome": "Ana", "data": "2026-08-11", "altura_salto_cm": 35},   # −12.5%
        {"nome": "Rui", "data": "2026-07-27", "altura_salto_cm": 38},
        {"nome": "Rui", "data": "2026-08-11", "altura_salto_cm": 38.5},
    ])
    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}
    out = calcular_prontidao(_df(rows), testes, {"Zé": "lesionado"}, sem_acwr)
    j = {x["jogador"]: x for x in out["jogadores"]}
    assert j["Ana"]["estado"] == "reduzir" and j["Ana"]["pontuacao"] == 4
    assert {s["componente"] for s in j["Ana"]["sinais"]} == {"cmj", "hooper"}
    assert j["Rui"]["estado"] == "pronto"
    assert j["Zé"]["estado"] == "indisponivel"
    assert out["jogadores"][0]["jogador"] == "Ana"  # pior primeiro
    assert out["cobertura"]["cmj"] == 2
    # 12 dias de dados: ainda no período de arranque do ACWR.
    assert j["Ana"]["acwr"] is None


# ── Regresso ao jogo ─────────────────────────────────────────────────────────
def test_rtp_avanca_etapas_com_referencia_pre_lesao():
    """As metas são % da referência de jogo ANTES do plano; cada etapa precisa
    de N sessões a cumprir todas as metas, e só depois conta a etapa seguinte."""
    from app.services.rtp_service import avaliar_plano
    rows = [
        # Pré-lesão: jogos de 90' com HSR 1000 e distância 10000; recorde Vmax 32.
        _sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, dist=10000, vmax=32),
        _sessao("Ana", "2026-07-08", 2, "MD", tipo="Jogo", hsr=1000, dist=10000, vmax=31),
        # Depois do início do plano (2026-08-01):
        _sessao("Ana", "2026-08-02", 5, "MD-3", hsr=320, dist=5200, vmax=24),  # E1 ✓
        _sessao("Ana", "2026-08-04", 5, "MD-1", hsr=550, dist=8000, vmax=27),  # E1 ✓ (E2 também, mas conta para E1)
        _sessao("Ana", "2026-08-06", 6, "MD-3", hsr=520, dist=7600, vmax=26),  # E2 ✓ (vmax 81%)
        _sessao("Ana", "2026-08-08", 6, "MD-1", hsr=200, dist=4000, vmax=22),  # nada
    ]
    etapas = [
        {"nome": "E1", "pct_distancia": 50, "pct_hsr": 30},
        {"nome": "E2", "pct_distancia": 75, "pct_hsr": 50, "pct_vmax": 80},
        {"nome": "E3", "pct_hsr": 100},
    ]
    out = avaliar_plano(_df(rows), "Ana", "2026-08-01", etapas, sessoes_por_etapa=2)
    assert out["referencias"]["pct_hsr"]["valor"] == 1000 and out["referencias"]["pct_vmax"]["valor"] == 32
    e1, e2, e3 = out["etapas"]
    assert e1["estado"] == "concluida" and e1["data_conclusao"] == "2026-08-04"
    assert e2["estado"] == "atual" and e2["sessoes_cumpridas"] == 1
    assert e3["estado"] == "pendente"
    assert out["etapa_atual"] == 2 and not out["concluido"]
    assert out["progresso_pct"] == 50  # (1 etapa + 1/2) ÷ 3
    assert out["sessoes"][0]["data"] == "2026-08-08"  # mais recente primeiro


# ── Mensagens (WhatsApp) ─────────────────────────────────────────────────────
class _CursorFalso:
    def __init__(self, respostas, registo):
        self.respostas, self.registo, self._ultimo = respostas, registo, None
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.registo.append((" ".join(sql.split()), params))
        for chave, resp in self.respostas.items():
            if chave in sql:
                self._ultimo = resp(params) if callable(resp) else resp
                return
        self._ultimo = None

    def fetchone(self):
        return self._ultimo[0] if isinstance(self._ultimo, list) and self._ultimo else self._ultimo

    def fetchall(self):
        return self._ultimo or []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _conn_falsa(respostas, registo):
    from contextlib import contextmanager

    class _Conn:
        def cursor(self):
            return _CursorFalso(respostas, registo)

    @contextmanager
    def get_conn():
        yield _Conn()
    return get_conn


def test_normalizar_telefone():
    from app.services.whatsapp_service import normalizar_telefone
    assert normalizar_telefone("912 345 678") == "+351912345678"
    assert normalizar_telefone("00351 912-345-678") == "+351912345678"
    assert normalizar_telefone("+44 7700 900123") == "+447700900123"
    assert normalizar_telefone("12345") is None and normalizar_telefone(None) is None


def test_enviar_pedidos_so_com_consentimento_e_sem_duplicar(monkeypatch):
    """Só envia a quem tem telefone + consentimento; um pedido já enviado hoje
    não é reenviado; sem Twilio o envio fica «simulado»."""
    import app.services.mensagens_service as ms
    monkeypatch.setattr(ms, "listar_contactos", lambda t: [
        {"player_id": "a", "nome": "Ana Silva", "telefone": "+351912345678", "pode_receber": True, "motivo": None},
        {"player_id": "b", "nome": "Rui", "telefone": None, "pode_receber": False, "motivo": "sem telefone"},
        {"player_id": "c", "nome": "Zé", "telefone": "+351913333333", "pode_receber": True, "motivo": None},
    ])
    monkeypatch.setattr(ms.whatsapp_service, "configurado", lambda: False)
    registo = []
    # Ana: pedido novo; Zé: já enviado hoje (não é novo).
    insert = lambda p: [("id-" + p[1], "tok" * 8, "pendente", None, True)] if p[1] == "a" else [("id-c", "tok" * 8, "enviado", None, False)]
    monkeypatch.setattr(ms, "get_conn", _conn_falsa({"insert into pedidos_resposta": insert}, registo))
    out = ms.enviar_pedidos("t", "wellness", date(2026, 10, 21))
    assert out["simulados"] == 1 and out["ja_enviados"] == 1 and out["modo"] == "simulacao"
    assert out["ignorados"] == [{"nome": "Rui", "motivo": "sem telefone"}]
    assert any("update pedidos_resposta set estado_envio" in sql and p[0] == "simulado" for sql, p in registo)


def test_envio_automatico_respeita_dia_e_hora(monkeypatch):
    import app.services.mensagens_service as ms
    from datetime import datetime
    chamadas = []
    monkeypatch.setattr(ms, "enviar_pedidos", lambda t, tipo, d, *a, **k: chamadas.append((t, tipo, d)) or {"enviados": 1})
    monkeypatch.setattr(ms, "get_conn", _conn_falsa({"from config_mensagens": [("eq1", True, "08:00", [1, 2, 3, 4, 5]), ("eq2", True, "09:30", [1, 2])]}, []))
    terca_0815 = datetime(2026, 10, 20, 8, 15, tzinfo=ms.FUSO)
    ms.envio_automatico(terca_0815)
    assert chamadas == [("eq1", "wellness", date(2026, 10, 20))]  # eq2 só depois das 09:30
    chamadas.clear()
    ms.envio_automatico(datetime(2026, 10, 24, 9, 0, tzinfo=ms.FUSO))  # sábado
    assert chamadas == []


def test_envio_automatico_pse_lembrete_e_fuso(monkeypatch):
    """PSE só nos dias com sessão e depois da hora; lembrete a quem não
    respondeu (só com WhatsApp real); horas no fuso da equipa."""
    import app.services.mensagens_service as ms
    from datetime import datetime
    from zoneinfo import ZoneInfo
    chamadas, lembretes = [], []
    monkeypatch.setattr(ms, "enviar_pedidos", lambda t, tipo, d, ids=None, *a, **k: chamadas.append((t, tipo, ids)) or {"enviados": len(ids or [1])})
    monkeypatch.setattr(ms, "sessao_do_dia", lambda t, d: {"tipo": "Treino", "origem": "plano"} if t == "eq1" else None)
    monkeypatch.setattr(ms, "pendentes_para_lembrete", lambda t, d, apos, m: {"wellness": ["p1", "p2"]} if t == "eq1" else {})
    monkeypatch.setattr(ms, "_marcar_lembrete", lambda t, d, tipo, ids: lembretes.append((t, tipo, ids)))
    monkeypatch.setattr(ms.whatsapp_service, "configurado", lambda: True)
    linhas = [
        # team, wellness_auto, hora, dias, pse_auto, pse_hora, lembrete_auto, lembrete_min, fuso
        ("eq1", False, "08:00", [1, 2, 3, 4, 5], True, "19:30", True, 120, "Europe/Stockholm"),
        ("eq2", False, "08:00", [1, 2, 3, 4, 5], True, "19:30", False, 120, "Europe/Lisbon"),
    ]
    monkeypatch.setattr(ms, "get_conn", _conn_falsa({"information_schema.columns": [(True,)], "from config_mensagens": linhas}, []))

    # 18:45 em Lisboa = 19:45 em Estocolmo: eq1 já passou das 19:30, eq2 ainda não (e não tem sessão).
    ms.envio_automatico(datetime(2026, 10, 20, 18, 45, tzinfo=ZoneInfo("Europe/Lisbon")))
    assert ("eq1", "pse", None) in chamadas and not any(c[0] == "eq2" for c in chamadas)
    assert ("eq1", "wellness", ["p1", "p2"]) in chamadas and lembretes == [("eq1", "wellness", ["p1", "p2"])]

    # Sem WhatsApp configurado não há lembretes automáticos (os links ficam na página Hoje).
    chamadas.clear(); lembretes.clear()
    monkeypatch.setattr(ms.whatsapp_service, "configurado", lambda: False)
    ms.envio_automatico(datetime(2026, 10, 20, 18, 45, tzinfo=ZoneInfo("Europe/Lisbon")))
    assert lembretes == [] and ("eq1", "pse", None) in chamadas


def test_decidir_envios():
    import app.services.mensagens_service as ms
    from datetime import datetime
    cfg = {**ms.CONFIG_PADRAO, "wellness_auto": True, "pse_auto": True}
    m = datetime(2026, 10, 20, 19, 40)  # terça
    assert ms.decidir_envios(cfg, m, True) == ["wellness", "pse"]
    assert ms.decidir_envios(cfg, m, False) == ["wellness"]
    assert ms.decidir_envios(cfg, datetime(2026, 10, 20, 7, 0), True) == []


def test_link_whatsapp_um_toque():
    """O link gratuito do WhatsApp abre a conversa com o número certo e a
    mensagem (com o link pessoal) já escrita."""
    from urllib.parse import parse_qs, urlparse
    from app.services.mensagens_service import link_whatsapp, texto_mensagem
    texto = texto_mensagem("pse", "Ivo Teixeira", "https://app.test/r/abc")
    url = link_whatsapp("912 345 678", texto)
    partes = urlparse(url)
    assert partes.netloc == "wa.me" and partes.path == "/351912345678"
    msg = parse_qs(partes.query)["text"][0]
    assert msg.startswith("Ivo,") and "https://app.test/r/abc" in msg
    assert link_whatsapp(None, texto) is None


# ── Academia ─────────────────────────────────────────────────────────────────
def test_epocas():
    from app.services.academia_service import epoca_atual, epoca_seguinte, validar_epoca
    assert epoca_atual(date(2026, 10, 20)) == "2026/27"
    assert epoca_atual(date(2027, 3, 1)) == "2026/27"
    assert epoca_atual(date(2027, 7, 1)) == "2027/28"
    assert epoca_seguinte("2026/27") == "2027/28" and epoca_seguinte("1999/00") == "2000/01"
    assert validar_epoca(" 2026/27 ") == "2026/27"
    for mau in ["2026", "2026/28", "26/27", ""]:
        with pytest.raises(ValueError):
            validar_epoca(mau)


def test_criar_equipa_copia_plantel(monkeypatch):
    """Criar a época seguinte com o plantel copiado: verifica a academia, cria a
    equipa, junta o utilizador como membro e copia os jogadores com a ficha de atleta."""
    import app.services.academia_service as acad
    registo = []
    respostas = {
        "select papel from academia_membros": [("head",)],
        "select 1 from teams where academia_id": None,
        "insert into teams": [("novo-team",)],
        "select 1 from teams t join team_members": [(1,)],
        "select academia_id from teams": [("acad",)],
    }
    monkeypatch.setattr(acad, "get_conn", _conn_falsa(respostas, registo))
    out = acad.criar_equipa("u1", "acad", "Sub-16", "2027/28", copiar_de="team-velho")
    assert out["ok"] and out["rotulo"] == "Sub-16 · 2027/28"
    sqls = [s for s, _ in registo]
    assert any(s.startswith("insert into team_members") for s in sqls)
    assert any(s.startswith("insert into players") and "atleta_id" in s for s in sqls)
    with pytest.raises(ValueError):
        acad.criar_equipa("u1", "acad", "Sub-16", "2027-28")


def test_escaloes_so_sub15_a_sub19():
    import app.services.academia_service as acad
    assert acad.ESCALOES == ["Sub-15", "Sub-16", "Sub-17", "Sub-19"]
    assert acad.validar_escalao("sub-17") == "Sub-17"
    with pytest.raises(ValueError):
        acad.validar_escalao("Seniores")


def _respostas_atleta(papel="staff", membro=True):
    return {
        "select t.academia_id,": [("acad", membro, papel)],
        "select 1 from atletas where academia_id": None,
        "insert into atletas": [("atl-1",)],
        "select nome, data_nascimento, posicao_principal from atletas": [("João Silva", None, "MC")],
    }


def test_adicionar_atleta_em_duas_equipas(monkeypatch):
    """Um jogador adicionado a sub-16 e sub-17 fica com uma linha em cada equipa, com a mesma ficha."""
    import app.services.academia_service as acad
    import app.services.dados_equipa as de
    registo = []
    monkeypatch.setattr(acad, "get_conn", _conn_falsa(_respostas_atleta(), registo))
    monkeypatch.setattr(de, "invalidar_cache_equipa", lambda t=None: None)
    out = acad.adicionar_atleta("u1", "acad", "  João   Silva ", "2011-03-02", "MC", "direito", ["t16", "t17"])
    assert out == {"ok": True, "atleta_id": "atl-1"}
    ins = [p for sql, p in registo if sql.startswith("insert into players")]
    assert [p[0] for p in ins] == ["t16", "t17"] and all(p[3] == "atl-1" for p in ins)
    with pytest.raises(ValueError):
        acad.adicionar_atleta("u1", "acad", "João", None, None, None, [])


def test_adicionar_atleta_so_pf_da_equipa_ou_head(monkeypatch):
    import app.services.academia_service as acad
    monkeypatch.setattr(acad, "get_conn", _conn_falsa(_respostas_atleta(papel="staff", membro=False), []))
    with pytest.raises(PermissionError):
        acad.adicionar_atleta("u1", "acad", "João", None, None, None, ["t17"])
    monkeypatch.setattr(acad, "get_conn", _conn_falsa(_respostas_atleta(papel="head", membro=False), []))
    import app.services.dados_equipa as de
    monkeypatch.setattr(de, "invalidar_cache_equipa", lambda t=None: None)
    assert acad.adicionar_atleta("u1", "acad", "João", None, None, None, ["t17"])["ok"]


def test_sessoes_partilhadas_no_referencial_local():
    """PSE de um sub-16 num treino dos sub-17: entra nos sub-16 com o player_id
    local e o microciclo/dia MD dos sub-16; um jogo mantém-se MD."""
    from app.services.dados_equipa import alinhar_partilhadas
    d = lambda s: date.fromisoformat(s)
    df = pd.DataFrame([
        {"data": d("2026-10-05"), "player_id": "p16", "team_id": "t16", "tipo": "Treino", "dia_md": "MD-4", "microciclo_nr": 7, "jogador_local_id": "p16", "equipa_origem": None},
        {"data": d("2026-10-08"), "player_id": "p16", "team_id": "t16", "tipo": "Treino", "dia_md": "MD-1", "microciclo_nr": 7, "jogador_local_id": "p16", "equipa_origem": None},
        {"data": d("2026-10-08"), "player_id": "p17", "team_id": "t17", "tipo": "Treino", "dia_md": "MD-3", "microciclo_nr": 30, "jogador_local_id": "p16", "equipa_origem": "Sub-17"},
        {"data": d("2026-10-06"), "player_id": "p17", "team_id": "t17", "tipo": "Jogo", "dia_md": "MD", "microciclo_nr": 30, "jogador_local_id": "p16", "equipa_origem": "Sub-17"},
    ])
    out = alinhar_partilhadas(df, "t16")
    treino, jogo = out.iloc[2], out.iloc[3]
    assert treino["player_id"] == "p16" and treino["team_id"] == "t16"
    assert treino["microciclo_nr"] == 7 and treino["dia_md"] == "MD-1"
    assert jogo["microciclo_nr"] == 7 and jogo["dia_md"] == "MD"   # sem sessão local no dia: microciclo que contém a data
    assert out.iloc[0]["dia_md"] == "MD-4"                          # sessões locais intocadas


# ── Ficha longitudinal ───────────────────────────────────────────────────────
def test_khamis_roche():
    """Khamis-Roche (rapazes, tabela com errata) + categorias de Cumming."""
    from app.services.khamis_roche import estatura_adulta_prevista, idade_tabela
    m = estatura_adulta_prevista(13.0, 160.0, 50.0, 180.0, 165.0)
    pol = -7.8632 + 0.60818 * 160 / 2.54 - 0.013895 * 50 * 2.20462 + 0.62407 * 172.5 / 2.54
    assert m["estatura_prevista_cm"] == round(pol * 2.54, 1)
    assert 178 < m["estatura_prevista_cm"] < 184
    assert m["categoria"] == "Início da puberdade" and 85 <= m["pct_estatura_adulta"] < 90
    assert idade_tabela(13.2) == 13.0 and idade_tabela(13.3) == 13.5 and idade_tabela(18.5) is None
    assert estatura_adulta_prevista(13.0, 160.0, None, 180.0, 165.0) is None
    tardio = estatura_adulta_prevista(17.5, 178.0, 70.0, 180.0, 165.0)
    assert tardio["categoria"] == "Fim da puberdade"


def test_serie_maturacao_precisa_de_pais_e_peso():
    import pandas as pd
    from app.services.ficha_atleta_service import serie_maturacao
    serie = pd.DataFrame([
        {"data": pd.Timestamp("2026-09-01"), "metrica": "altura_cm", "valor": 160.0, "idade": 13.0},
        {"data": pd.Timestamp("2026-09-01"), "metrica": "peso_kg", "valor": 50.0, "idade": 13.0},
        {"data": pd.Timestamp("2026-10-01"), "metrica": "altura_cm", "valor": 161.0, "idade": 13.1},  # sem peso
    ])
    assert serie_maturacao(serie, None, 165.0) == []
    out = serie_maturacao(serie, 180.0, 165.0)
    assert len(out) == 1 and out[0]["data"] == "2026-09-01" and out[0]["categoria"] == "Início da puberdade"


def test_catalogo_resistencia_1km():
    from app.services.ficha_atleta_service import CATALOGO
    chaves = {m["chave"]: m for m in CATALOGO}
    assert "yoyo_ir1_m" not in chaves and "vift_kmh" not in chaves
    assert chaves["corrida_1km_s"]["maior_melhor"] is False and chaves["corrida_1km_s"]["grupo"] == "Resistência"


def test_percentil_direcao():
    from app.services.ficha_atleta_service import percentil
    amostra = [4.4, 4.5, 4.6, 4.7, 4.8, 4.9]
    assert percentil(4.4, amostra, False) > 90   # sprint mais rápido = melhor
    assert percentil(4.9, amostra, False) < 10
    assert percentil(4.9, amostra, True) > 90
    assert percentil(4.6, amostra[:3], True) is None  # amostra pequena demais


def test_entrada_vs_ultima_e_percentil_por_idade():
    from app.services.ficha_atleta_service import entrada_vs_ultima
    serie = pd.DataFrame([
        {"metrica": "sprint_30m_s", "data": pd.Timestamp("2023-09-01"), "valor": 5.10, "idade": 12.4},
        {"metrica": "sprint_30m_s", "data": pd.Timestamp("2026-09-01"), "valor": 4.40, "idade": 15.4},
        {"metrica": "altura_cm", "data": pd.Timestamp("2023-09-01"), "valor": 150.0, "idade": 12.4},
    ])
    coorte = pd.DataFrame(
        [{"metrica": "sprint_30m_s", "idade": 12.5, "valor": v} for v in (4.9, 5.0, 5.2, 5.3, 5.4)]
        + [{"metrica": "sprint_30m_s", "idade": 15.1, "valor": v} for v in (4.3, 4.5, 4.6, 4.7, 4.8)]
    )
    out = {x["metrica"]: x for x in entrada_vs_ultima(serie, coorte)}
    s = out["sprint_30m_s"]
    assert s["entrada"]["valor"] == 5.1 and s["ultima"]["valor"] == 4.4
    assert s["melhorou"] is True and s["variacao_pct"] == round(-0.7 / 5.1 * 100, 1)
    assert s["entrada"]["percentil"] == 60   # 5.10 entre os de 12 anos (2 mais rápidos de 5)
    assert s["ultima"]["percentil"] == 80    # 4.40 entre os de 15 anos
    assert out["altura_cm"]["melhorou"] is None  # antropometria: sem "melhor"


def test_carga_jogo_por_epoca():
    from app.services.ficha_atleta_service import carga_jogo_por_epoca
    rows = [
        _sessao("Ana", "2025-10-04", 1, "MD", tipo="Jogo", hsr=600),
        _sessao("Ana", "2026-10-03", 1, "MD", tipo="Jogo", hsr=800),
        _sessao("Ana", "2026-10-10", 2, "MD", tipo="Jogo", hsr=1000),
    ]
    df = _df(rows)
    df["Época"] = ["2025/26", "2026/27", "2026/27"]
    df["Escalão"] = ["Sub-14", "Sub-15", "Sub-15"]
    out = {e["epoca"]: e for e in carga_jogo_por_epoca(df)}
    assert out["2025/26"]["hsr_90"] == 600 and out["2026/27"]["hsr_90"] == 900
    assert out["2026/27"]["jogos"] == 2 and out["2026/27"]["escalao"] == "Sub-15"


# ── Microciclos ──────────────────────────────────────────────────────────────
def test_dia_md_relativo_e_semanas():
    from app.services.microciclos_service import dia_md_relativo, gerar_semanas
    jogo = date(2026, 10, 11)
    assert dia_md_relativo(date(2026, 10, 8), jogo) == "MD-3"
    assert dia_md_relativo(jogo, jogo) == "MD"
    assert dia_md_relativo(date(2026, 10, 12), jogo) == "MD+1"
    assert dia_md_relativo(jogo, None) is None
    sem = gerar_semanas(date(2026, 8, 24), 3, 1, {2})
    assert [n for n, _, _ in sem] == [1, 3, 4]
    assert sem[1][1] == date(2026, 8, 31) and sem[1][2] == date(2026, 9, 6)


def test_fatores_reais_so_treinos_em_multiplos_de_jogo():
    from app.services.microciclos_service import fatores_reais
    df = pd.DataFrame([
        {"Data": pd.Timestamp("2026-10-06"), "Jogador": "A", "Tipo": "Treino", "Dia MD": "MD-4", "HSR (m)": 300.0},
        {"Data": pd.Timestamp("2026-10-08"), "Jogador": "A", "Tipo": "Treino", "Dia MD": "MD-2", "HSR (m)": 200.0},
        {"Data": pd.Timestamp("2026-10-08"), "Jogador": "B", "Tipo": "Treino", "Dia MD": "MD-2", "HSR (m)": 300.0},
        {"Data": pd.Timestamp("2026-10-11"), "Jogador": "A", "Tipo": "Jogo", "Dia MD": "MD", "HSR (m)": 900.0},
        {"Data": pd.Timestamp("2026-10-14"), "Jogador": "A", "Tipo": "Treino", "Dia MD": "MD-4", "HSR (m)": 999.0},
    ])
    out = fatores_reais(df, date(2026, 10, 5), date(2026, 10, 11), {"hsr": 400.0})
    assert out == {"hsr": round(((500 + 300) / 2) / 400, 2)}   # A=500, B=300 → 400 → ×1.0


def test_validar_microciclo():
    from app.services.microciclos_service import _validar
    v = _validar({"numero": 7, "data_inicio": "2026-10-05", "data_fim": "2026-10-11", "fatores": {"hsr": "2.5", "xx": 3}, "perfil": "Carga"})
    assert v["nome"] == "MC 07" and v["fatores"] == {"hsr": 2.5}
    for mau in ({"numero": 7, "data_inicio": "2026-10-11", "data_fim": "2026-10-05"},
                {"numero": 7, "data_inicio": "2026-10-05", "data_fim": "2026-10-11", "perfil": "Xpto"},
                {"numero": 7, "data_inicio": "2026-10-05", "data_fim": "2026-10-11", "fatores": {"hsr": 12}}):
        with pytest.raises(ValueError):
            _validar(mau)


def test_guardar_dia_no_calendario(monkeypatch):
    import json as _j
    import app.services.microciclos_service as mcs
    registo = []
    dias = {"2026-10-06": {"tipo": "Treino", "dia_md": "MD-4"}, "2026-10-07": {"tipo": "Treino", "dia_md": "MD-3"}}
    resp = {"select id::text, numero, data_inicio, data_fim, dias, fatores from microciclos":
                [("mc", 7, date(2026, 10, 5), date(2026, 10, 11), _j.dumps(dias), _j.dumps({"hsr": 2.5}))],
            "information_schema": [(True,)]}
    monkeypatch.setattr(mcs, "get_conn", _conn_falsa(resp, registo))
    monkeypatch.setattr(mcs, "invalidar_cache_equipa", lambda t=None: None)
    # MD-3 já está a 07/10 → recusa repetir noutro dia
    with pytest.raises(ValueError):
        mcs.guardar_dia("t", "2026-10-08", "Treino", "MD-3", "Força", {"pse": 6})
    # Treino com valores → grava planeado
    registo.clear()
    import pandas as _pd
    monkeypatch.setattr(mcs, "carregar_df_equipa", lambda t: _pd.DataFrame())
    monkeypatch.setattr(mcs, "referencia_equipa", lambda df: {"hsr": 600.0})
    mcs.guardar_dia("t", "2026-10-08", "Treino", "MD-2", "Força", {"pse": 6, "duracao_min": 75, "pct": {"hsr": 20}})
    sqls = [(s, p) for s, p in registo]
    assert any(s.startswith("insert into pse_planeado") for s, _ in sqls)
    carga = [p for s, p in sqls if s.startswith("insert into carga_externa_planeada")][0]
    assert 300.0 in carga   # 20 % de (2,5 × 600 m)
    final = _j.loads([p for s, p in registo if s.startswith("update microciclos set dias")][0][0])
    assert final["2026-10-08"]["pct"] == {"hsr": 20.0}
    # Jogo a propagar os dias MD por todo o microciclo
    registo.clear()
    mcs.guardar_dia("t", "2026-10-10", "Jogo", None, "vs Ribeiras", None, propagar_md=True)
    final = _j.loads([p for s, p in registo if s.startswith("update microciclos set dias")][0][0])
    assert final["2026-10-10"] == {"tipo": "Jogo", "dia_md": "MD", "objetivo": "vs Ribeiras"}
    assert final["2026-10-06"]["dia_md"] == "MD-4" and final["2026-10-07"]["dia_md"] == "MD-3" and final["2026-10-11"]["dia_md"] == "MD+1"
    # Dia fora de qualquer microciclo
    monkeypatch.setattr(mcs, "get_conn", _conn_falsa({}, []))
    with pytest.raises(ValueError):
        mcs.guardar_dia("t", "2026-12-01", "Folga", None, None, None)


# ── Calendário ───────────────────────────────────────────────────────────────
def test_calendario_realizado_por_dia():
    from app.services.calendario_service import realizado_por_dia
    df = pd.DataFrame([
        {"Data": pd.Timestamp("2026-10-08"), "Jogador": "A", "Tipo": "Treino", "Dia MD": "MD-3", "Duração (min)": 80.0, "Distância Total (m)": 6000.0, "PSE Sessão": 6.0, "Hooper Index": 12.0},
        {"Data": pd.Timestamp("2026-10-08"), "Jogador": "B", "Tipo": "Treino", "Dia MD": "MD-3", "Duração (min)": 70.0, "Distância Total (m)": 5000.0, "PSE Sessão": None, "Hooper Index": 14.0},
        {"Data": pd.Timestamp("2026-10-11"), "Jogador": "A", "Tipo": "Jogo", "Dia MD": "MD", "Duração (min)": 90.0, "Distância Total (m)": 10000.0, "PSE Sessão": 8.0, "Hooper Index": None},
        {"Data": pd.Timestamp("2026-10-12"), "Jogador": "A", "Tipo": None, "Dia MD": None, "Duração (min)": None, "Distância Total (m)": None, "PSE Sessão": None, "Hooper Index": 10.0},
    ])
    out = realizado_por_dia(df, date(2026, 10, 5), date(2026, 10, 12))
    d8 = out[date(2026, 10, 8)]
    assert d8["tipo"] == "Treino" and d8["dia_md"] == "MD-3" and d8["jogadores"] == 2
    assert d8["pse_respostas"] == 1 and d8["wellness_respostas"] == 2 and d8["pse_media"] == 6.0
    assert out[date(2026, 10, 11)]["tipo"] == "Jogo"
    assert out[date(2026, 10, 12)]["tipo"] is None   # só bem-estar, sem sessão


def test_calendario_evento_valida():
    from app.services.calendario_service import criar_evento
    with pytest.raises(ValueError):
        criar_evento("t", "u", "2026-10-08", "   ", "Viagem")
    with pytest.raises(ValueError):
        criar_evento("t", "u", "2026-10-08", "Viagem a Braga", "Xpto")



# ── Testes por equipa ────────────────────────────────────────────────────────
def test_rsi_e_ultimos_por_metrica():
    from app.services.ficha_atleta_service import BATERIAS, POR_CHAVE, rsi_drop_jump, ultimos_por_metrica
    assert rsi_drop_jump(30.0, 200.0) == 1.5 and rsi_drop_jump(None, 200) is None
    assert all(k in POR_CHAVE for b in BATERIAS.values() for k in b["metricas"])
    assert BATERIAS["velocidade"]["metricas"] == ["sprint_5m_s", "sprint_10m_s", "sprint_20m_s", "sprint_30m_s"]
    serie = pd.DataFrame([
        {"data": pd.Timestamp("2026-09-01"), "metrica": "sprint_10m_s", "valor": 1.95},
        {"data": pd.Timestamp("2026-10-01"), "metrica": "sprint_10m_s", "valor": 1.90},
        {"data": pd.Timestamp("2026-10-01"), "metrica": "cmj_cm", "valor": 31.0},
    ])
    u = ultimos_por_metrica(serie)
    assert u["sprint_10m_s"] == {"valor": 1.9, "data": "2026-10-01", "anterior": 1.95, "data_anterior": "2026-09-01"}
    assert u["cmj_cm"]["anterior"] is None


def test_registar_testes_equipa_calcula_rsi(monkeypatch):
    import app.services.ficha_atleta_service as f
    import app.core.db as db
    registo = []
    resp = {"from teams t join academia_membros": [("acad", "Sub-15 · 2026/27")],
            "select atleta_id::text from players": [("a1",)],
            "information_schema": [(True,)]}
    monkeypatch.setattr(db, "get_conn", _conn_falsa(resp, registo))
    out = f.registar_testes_equipa("u", "t15", "2026-10-15", [
        {"atleta_id": "a1", "valores": {"sprint_5m_s": "1.12", "dj_altura_cm": 30, "dj_contacto_ms": 200, "cmj_cm": ""}},
    ])
    metricas = {p[4]: p[5] for s, p in registo if s.startswith("insert into avaliacoes")}
    assert metricas == {"sprint_5m_s": 1.12, "dj_altura_cm": 30.0, "dj_contacto_ms": 200.0, "rsi": 1.5}
    assert out["registadas"] == 4
    with pytest.raises(PermissionError):
        f.registar_testes_equipa("u", "t15", "2026-10-15", [{"atleta_id": "intruso", "valores": {"cmj_cm": 30}}])



# ── Relatórios T1–T4 ─────────────────────────────────────────────────────────
def test_momentos_e_epoca():
    from app.services.ficha_atleta_service import limites_epoca, momento_por_data
    assert [momento_por_data(date(2026, m, 1)) for m in (7, 9, 10, 12)] == [1, 1, 2, 2]
    assert [momento_por_data(date(2027, m, 1)) for m in (1, 3, 4, 6)] == [3, 3, 4, 4]
    assert limites_epoca("2026/27") == (date(2026, 7, 1), date(2027, 6, 30))


def test_valores_e_maturacao_por_momento():
    from app.services.ficha_atleta_service import maturacao_por_momento, valores_por_momento
    serie = pd.DataFrame([
        {"data": pd.Timestamp("2026-09-10"), "metrica": "sprint_10m_s", "valor": 1.95, "momento": None},
        {"data": pd.Timestamp("2026-09-20"), "metrica": "sprint_10m_s", "valor": 1.93, "momento": None},  # mesmo T1 → fica o último
        {"data": pd.Timestamp("2026-10-02"), "metrica": "sprint_10m_s", "valor": 1.91, "momento": 1},     # explícito: T1
        {"data": pd.Timestamp("2027-05-10"), "metrica": "sprint_10m_s", "valor": 1.85, "momento": None},
        {"data": pd.Timestamp("2026-09-10"), "metrica": "altura_cm", "valor": 160.0, "momento": None},
        {"data": pd.Timestamp("2026-09-10"), "metrica": "peso_kg", "valor": 50.0, "momento": None},
    ])
    v = valores_por_momento(serie)
    assert v["sprint_10m_s"][1]["valor"] == 1.91 and v["sprint_10m_s"][4]["valor"] == 1.85 and 2 not in v["sprint_10m_s"]
    mat = maturacao_por_momento(v, date(2013, 9, 10), 180.0, 165.0)
    assert mat[1]["categoria"] == "Início da puberdade" and mat[1]["pct_estatura_adulta"] == 88.3


def test_calculo_em_cache_reutiliza_e_invalida():
    from app.services import dados_equipa as de
    chamadas = []
    def f():
        chamadas.append(1)
        return [1, 2]
    de.invalidar_cache_equipa(None)
    assert de.calculo_em_cache("t1", "avisos", f) == [1, 2]
    assert de.calculo_em_cache("t1", "avisos", f) == [1, 2] and len(chamadas) == 1
    de.invalidar_cache_equipa("t1")
    de.calculo_em_cache("t1", "avisos", f)
    assert len(chamadas) == 2



# ── Jogos ────────────────────────────────────────────────────────────────────
def test_ler_folha_sem_cabecalho_como_a_do_departamento():
    from app.services.jogos_service import ler_folha
    csv = (
        "P15,16/08/2026,League,2026,53,Bjärreds FF,Albin Ambuhm,Striker,80,Yes,3,\n"
        "P15,16/08/2026,League,2026,53,Bjärreds FF,Alim Spahiu,Fullback,40,No,,1\n"
        "P15,16/08/2026,League,2026,53,Bjärreds FF,Adis Ascic,Goalkeeper,0,No,,\n"
        "P15,23/08/2026,Friendly,2026,54,Lunds BK,Albin Ambuhm,Striker,60,Yes,,\n"
    ).encode()
    df = ler_folha(csv, "jogos.csv")
    assert len(df) == 4
    a = df.iloc[0]
    assert str(a["data"]) == "2026-08-16" and a["competicao"] == "Campeonato" and a["adversario"] == "Bjärreds FF"
    assert a["posicao"] == "Avançado" and a["minutos"] == 80 and a["titular"] and a["golos"] == 3 and a["assistencias"] == 0
    assert df.iloc[1]["posicao"] == "Lateral" and df.iloc[1]["assistencias"] == 1 and not df.iloc[1]["titular"]
    assert df.iloc[3]["competicao"] == "Amigável"


def test_ler_folha_com_cabecalho():
    from app.services.jogos_service import ler_folha
    csv = "Date;Competition;Opponent;Player;Position;Minutes;Starter;Goals;Assists\n03/09/2026;Cup;Malmö City;Kalle Beyer;Midfielder;80;Yes;1;2\n".encode()
    df = ler_folha(csv, "x.csv")
    assert df.iloc[0]["competicao"] == "Taça" and df.iloc[0]["posicao"] == "Médio" and df.iloc[0]["assistencias"] == 2


def test_resumo_jogadores_minutos_por_contexto():
    from app.services.jogos_service import resumo_jogadores
    jogos = [{"id": "j1", "competicao": "Campeonato", "duracao_min": 80}, {"id": "j2", "competicao": "Torneio", "duracao_min": 40}]
    part = [
        {"jogo_id": "j1", "atleta_id": "a", "nome": "A", "minutos": 80, "titular": True, "golos": 2, "assistencias": 0},
        {"jogo_id": "j2", "atleta_id": "a", "nome": "A", "minutos": 20, "titular": False, "golos": 0, "assistencias": 1},
        {"jogo_id": "j1", "atleta_id": "b", "nome": "B", "minutos": 0, "titular": False, "golos": 0, "assistencias": 0},
    ]
    r = {x["atleta_id"]: x for x in resumo_jogadores(jogos, part)}
    assert r["a"]["minutos"] == 100 and r["a"]["pct_minutos"] == round(100 * 100 / 120, 1)
    assert r["a"]["por_contexto"] == {"Campeonato": 80, "Taça": 0, "Torneio": 20, "Amigável": 0}
    assert r["a"]["titular"] == 1 and r["a"]["golos"] == 2 and r["a"]["assistencias"] == 1
    assert r["b"]["convocado"] == 1 and r["b"]["utilizado"] == 0



def test_plano_do_dia_em_percentagem_do_objetivo_semanal():
    from app.services.microciclos_service import absolutos_de_pct, alvos_semanais
    alvos = alvos_semanais({"hsr": 2.5, "acc": 3, "distancia": 2}, {"hsr": 600.0, "acc": 50.0, "sprint": 200.0})
    assert alvos == {"hsr": 1500.0, "acc": 150.0}   # distância sem referência, sprint sem fator
    out = absolutos_de_pct({"hsr": 20, "acc": 30, "sprint": 25}, alvos)
    assert out == {"distancia_m": None, "hsr_m": 300.0, "sprint_m": None, "acc_n": 45.0, "dcc_n": None}



# ── Equipa técnica ───────────────────────────────────────────────────────────
def test_papeis_e_bloqueio_so_consulta():
    from app.services.equipa_tecnica_service import motivo_bloqueio, papel_de
    assert papel_de("head", []) == "head" and papel_de("leitura", []) == "treinador"
    assert papel_de("staff", ["treinador", "treinador"]) == "treinador" and papel_de("staff", ["pf"]) == "pf"
    T = "11111111-2222-3333-4444-555555555555"
    def cur_com(respostas):
        return _CursorFalso(respostas, [])
    treinador = cur_com({"from team_members": [("treinador",)]})
    assert motivo_bloqueio(treinador, "u", "POST", f"/api/teams/{T}/wellness")
    assert motivo_bloqueio(treinador, "u", "GET", f"/api/teams/{T}/dashboard") is None
    assert motivo_bloqueio(treinador, "u", "PUT", f"/api/academia/equipas/{T}/jogos/x")
    assert motivo_bloqueio(cur_com({"from team_members": [("pf",)]}), "u", "POST", f"/api/teams/{T}/x") is None
    leitura = _CursorFalso({"from academia_membros": [("leitura",)]}, [])
    leitura.fetchall = lambda: [("leitura",)]
    assert motivo_bloqueio(leitura, "u", "POST", "/api/academia/atletas/abc/avaliacoes")
    assert motivo_bloqueio(leitura, "u", "POST", "/api/convites/tok/aceitar") is None


def test_estado_convite():
    from datetime import datetime, timedelta, timezone
    from app.services.equipa_tecnica_service import estado_convite
    agora = datetime(2026, 10, 21, tzinfo=timezone.utc)
    assert estado_convite(agora + timedelta(days=1), None, False, agora) == "valido"
    assert estado_convite(agora - timedelta(days=1), None, False, agora) == "expirado"
    assert estado_convite(agora + timedelta(days=1), agora, False, agora) == "aceite"
    assert estado_convite(agora + timedelta(days=1), None, True, agora) == "revogado"



def test_consentimento_valida():
    from app.services.ficha_atleta_service import registar_consentimento
    with pytest.raises(ValueError):
        registar_consentimento("u", "a", "2999-01-01", "encarregado", None)
    with pytest.raises(ValueError):
        registar_consentimento("u", "a", "2026-09-01", "vizinho", None)


def test_jogos_csv_com_numero_incompleto_nao_rebenta():
    """N.º do jogo preenchido só em algumas linhas: os vazios ficavam NaN e o
    import rebentava com «cannot convert float NaN to integer»."""
    from app.services import jogos_service as jg
    csv = ("Date;Competition;Opponent;Player;Position;Minutes;Starter;Goals;Assists;Match\n"
           "12/10/2026;Liga;Malmö FF;Ana Silva;MC;70;sim;1;;3\n"
           "12/10/2026;Liga;Malmö FF;Rui Costa;DC;;não;;;\n"
           "19/10/2026;Liga;Lund;Rui Costa;DC;60;sim;;;\n").encode()
    df = jg.ler_folha(csv, "jogos.csv")
    assert len(df) == 3 and df["minutos"].tolist() == [70, 0, 60]
    numeros = {adv: jg.numero_do_jogo(g["numero"]) for (_, adv), g in df.groupby(["data", "adversario"])}
    assert numeros == {"Malmö FF": 3, "Lund": None}
    assert jg.numero_do_jogo(pd.Series([float("nan"), 7.0])) == 7
    assert jg._int(float("inf")) == 0


# ── Importação GPS: mapeamento lembrado e plano ──────────────────────────────
def test_juntar_mapa_lembrado():
    from app.services.importacao_service import juntar_mapa_lembrado
    auto = {"Player": "Jogador", "Date": "Data", "Dist": "Distância Total (m)"}
    lembrado = {"mapa": {"HSR>19": "HSR (m)", "Player": "Jogador"}, "ignoradas": ["Dist"]}
    mapa, lembradas = juntar_mapa_lembrado(["Player", "Date", "Dist", "HSR>19", "Novo"], auto, lembrado)
    assert mapa == {"Player": "Jogador", "Date": "Data", "HSR>19": "HSR (m)"}
    assert lembradas == {"Player", "Dist", "HSR>19"}
    assert juntar_mapa_lembrado(["A"], {"A": "Data"}, None) == ({"A": "Data"}, set())


def test_completar_com_plano_so_preenche_vazios():
    from app.services.ingest_service import completar_com_plano
    df = pd.DataFrame({
        "Jogador": ["Ana", "Ana", "Rui"],
        "Data": pd.to_datetime(["2026-10-20", "2026-10-22", "2026-10-22"]),
        "Dia MD": [None, None, "MD-1"],
        "Tipo": [None, None, None],
    })
    plano = {"2026-10-20": {"microciclo": 7, "dia_md": "MD-4", "tipo": "Treino"},
             "2026-10-22": {"microciclo": 7, "dia_md": "MD-2", "tipo": "Treino"}}
    out, n = completar_com_plano(df, plano)
    assert out["Dia MD"].tolist() == ["MD-4", "MD-2", "MD-1"]  # o do ficheiro fica
    assert out["Microciclo (Nr)"].tolist() == [7, 7, 7] and out["Tipo"].tolist() == ["Treino"] * 3
    assert n == 3
    assert completar_com_plano(df, {})[1] == 0


# ── Hoje ─────────────────────────────────────────────────────────────────────
def _resumo_hoje(**k):
    base = {
        "sessao": {"tipo": "Treino", "origem": "plano"}, "e_passado": False,
        "plantel": {"total": 16, "disponiveis": 15, "ausentes": [{"nome": "Zé", "estado": "lesionado", "motivo": None}]},
        "gps": {"jogadores": 0, "ultimo_dia": "2026-10-21"},
        "bem_estar": {"respostas": 15, "pedidos": 15, "falta": []},
        "pse": {"respostas": 0, "pedidos": 0, "falta": [{"nome": "Ana"}]},
        "alertas": {"n": 2, "jogadores": [{"nome": "Rui"}, {"nome": "Ivo"}]},
        "plano": {"proximos_sem_plano": []},
    }
    base.update(k)
    return base


def test_hoje_tarefas():
    from app.services.hoje_service import tarefas
    t = {x["chave"]: x for x in tarefas(_resumo_hoje())}
    assert t["bem_estar"]["estado"] == "feito" and t["bem_estar"]["acao"] is None
    assert t["gps"]["estado"] == "pendente" and t["gps"]["acao"] == "importar"
    assert t["pse"]["acao"] == "pedir"
    assert t["alertas"]["estado"] == "aviso" and "plano" not in t

    # Dia sem sessão: não pede GPS nem PSE.
    t2 = {x["chave"] for x in tarefas(_resumo_hoje(sessao=None, bem_estar={"respostas": 0, "pedidos": 0, "falta": []},
                                                   plano={"proximos_sem_plano": ["2026-10-24"]}))}
    assert t2 == {"alertas", "plano"}

    # PSE pedida a 15, 12 responderam → lembrar.
    t3 = {x["chave"]: x for x in tarefas(_resumo_hoje(gps={"jogadores": 15, "ultimo_dia": "2026-10-22"},
                                                     pse={"respostas": 12, "pedidos": 15, "falta": [{}, {}, {}]}))}
    assert t3["gps"]["estado"] == "feito" and t3["pse"]["acao"] == "lembrar" and t3["pse"]["detalhe"]["total"] == 15


# ── Perfil com os testes da academia ─────────────────────────────────────────
def test_perfis_de_relatorio_sten_e_momentos():
    from app.services.testes_service import perfis_de_relatorio
    def v(x, d="2026-09-23"): return {"valor": x, "data": d}
    rel = {"rotulo": "Sub-15 · 2026/27", "momentos": {1: {}, 2: {}}, "atletas": [
        {"atleta_id": "a", "nome": "Ana", "posicao": "MC", "valores": {"sprint_10m_s": {1: v(1.80), 2: v(1.75, "2026-12-01")}, "cmj_cm": {1: v(38)}}},
        {"atleta_id": "b", "nome": "Rui", "posicao": "DC", "valores": {"sprint_10m_s": {1: v(2.00)}, "cmj_cm": {1: v(30)}}},
        {"atleta_id": "c", "nome": "Ze", "posicao": None, "valores": {}},
    ]}
    t1 = perfis_de_relatorio(rel, 1)
    assert len(t1["metricas"]) == 9 and t1["metricas"][0]["chave"] == "sprint_5m_s"
    ana = next(j for j in t1["jogadores"] if j["jogador"] == "Ana")
    rui = next(j for j in t1["jogadores"] if j["jogador"] == "Rui")
    # Mais rápido (tempo menor) e salta mais → STEN maior.
    assert ana["testes"]["sprint_10m_s"]["sten"] > rui["testes"]["sprint_10m_s"]["sten"]
    assert ana["sten_medio"] > rui["sten_medio"] and t1["jogadores"][0]["jogador"] == "Ana"
    assert t1["sem_testes"] == ["Ze"] and t1["momentos"] == [1, 2]
    # Sem momento: o valor mais recente de cada teste.
    ult = perfis_de_relatorio(rel, None)
    assert next(j for j in ult["jogadores"] if j["jogador"] == "Ana")["testes"]["sprint_10m_s"]["valor"] == 1.75


# ── Semana por jogador: objetivo e compensação ───────────────────────────────
def _jogo(jog, data, minutos, dist, hsr, sprint):
    r = _sessao(jog, data, 1, "MD", tipo="Jogo", dist=dist, hsr=hsr, sprint=sprint)
    r["Duração (min)"] = minutos
    return r


def test_objetivo_semanal_por_jogador():
    from datetime import date
    from app.services.semana_jogadores_service import objetivo_semanal
    rows = [_jogo("Ana", "2026-08-02", 90, 9000, 900, 200), _jogo("Rui", "2026-08-02", 90, 9000, 600, 150)]
    rows += [_sessao("Ana", "2026-08-04", 2, "MD-4", hsr=600), _sessao("Rui", "2026-08-04", 2, "MD-4", hsr=100)]
    df = _df(rows)
    out = objetivo_semanal(df, {"Ana": "MC", "Rui": "DC"}, {"hsr": 2.0}, date(2026, 8, 3), date(2026, 8, 9),
                           ["2026-08-04", "2026-08-05", "2026-08-06"], date(2026, 8, 4))
    ana = next(j for j in out["jogadores"] if j["jogador"] == "Ana")["valores"]["hsr"]
    rui = next(j for j in out["jogadores"] if j["jogador"] == "Rui")["valores"]["hsr"]
    assert ana["alvo"] == 1800 and ana["feito"] == 600 and ana["falta"] == 1200 and ana["por_sessao"] == 600  # 2 sessões restantes
    assert out["sessoes_restantes"] == ["2026-08-05", "2026-08-06"] and out["esperado_pct"] == 33.3
    assert rui["alvo"] == 1200 and rui["estado"] == "atras" and ana["estado"] == "ok"


def test_compensacao_pos_jogo():
    from datetime import date
    from app.services.semana_jogadores_service import compensacao
    rows = [_jogo("Ana", "2026-08-01", 80, 8000, 800, 160), _jogo("Ana", "2026-08-08", 80, 8000, 800, 160),
            _jogo("Rui", "2026-08-01", 80, 8000, 600, 120), _jogo("Rui", "2026-08-08", 20, 2000, 150, 30),
            _sessao("Rui", "2026-08-09", 2, "MD+1", hsr=300)]
    out = compensacao(_df(rows), {"Ana": "MC", "Rui": "DC", "Ivo": "AV", "Zé": "GR"}, date(2026, 8, 9), ausentes={"Zé"})
    assert out["data"] == "2026-08-08" and out["dias_desde"] == 1
    nomes = [j["jogador"] for j in out["jogadores"]]
    assert "Ana" not in nomes and "Zé" not in nomes and nomes[0] == "Ivo"  # Ivo não jogou (0')
    rui = next(j for j in out["jogadores"] if j["jogador"] == "Rui")
    assert rui["minutos"] == 20 and rui["pct_minutos"] == 25
    # Ref. HSR do Rui por 90' = média(600/80, 150/20 só conta jogos ≥60') = 675 → esperado em 80' = 600; fez 150 → falta 450.
    assert rui["falta"]["hsr"] == 450 and rui["compensado_pct"]["hsr"] == 67


def test_referencia_jogo_completo_relativo_a_duracao_do_jogo():
    """Num jogo de 70', 55' (≥ 75 %) já é jogo completo e é escalado a 70';
    50' (< 75 %) não conta."""
    from app.services.referencia_jogo import duracao_jogo, referencias_jogo
    rows = []
    for i, (ana, rui) in enumerate([(70, 70), (55, 70), (50, 70)]):
        a = _sessao("Ana", f"2026-09-0{i + 1}", i + 1, "MD", tipo="Jogo", hsr=550 if ana == 55 else 700)
        a["Duração (min)"] = ana
        r = _sessao("Rui", f"2026-09-0{i + 1}", i + 1, "MD", tipo="Jogo", hsr=700)
        r["Duração (min)"] = rui
        rows += [a, r]
    df = _df(rows)
    assert duracao_jogo(df) == 70
    refs = referencias_jogo(df, "HSR (m)")
    # Ana: jogo 1 (700 em 70') e jogo 2 (550 em 55' → 700 por 70'); o de 50' fica de fora.
    assert refs["Ana"]["n_jogos"] == 2 and round(refs["Ana"]["valor"]) == 700


def test_exposicao_a_meio_da_semana_compara_com_o_esperado_ate_hoje():
    """Microciclo típico = 4 treinos. Com 1 treino feito, 0,20× o jogo não é
    «baixo» (esperado até hoje ≈ 0,60 × 1/4); com a semana fechada pelo jogo, é."""
    from app.services.alertas_service import construir_avisos_dashboard, obter_exposicao_semana, progresso_microciclo
    from app.services.referencia_jogo import mascara_jogo
    rows = []
    # Microciclo 4 completo: 4 treinos + jogo (HSR jogo 1000, Vmax 30).
    for d in ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]:
        rows.append(_sessao("Ana", d, 4, "MD-3", hsr=200, vmax=30))
    rows.append(_sessao("Ana", "2026-09-05", 4, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=30))
    # Microciclo 5: só a segunda-feira feita, HSR 200 → 0,20× o jogo.
    rows.append(_sessao("Ana", "2026-09-07", 5, "MD-5", hsr=200, sprint=40, vmax=30))
    df = _df(rows)
    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}

    p = progresso_microciclo(df, mascara_jogo(df), 5)
    assert p["treinos_feitos"] == 1 and p["treinos_tipicos"] == 4 and p["fracao"] == 0.25
    chaves = [s["chave"] for s in construir_avisos_dashboard(df, sem_acwr)[0]["sinais"]]
    assert "hsr_baixo" not in chaves

    painel = obter_exposicao_semana(df, sem_acwr)
    hsr = next(m for m in painel["metricas"] if m["chave"] == "hsr")
    assert hsr["ref_ate_hoje"][0] == 0.15 and hsr["jogadores"][0]["zona"] == "ok"
    assert hsr["jogadores"][0]["em_falta"] == 400  # para a zona da semana: 0,60 × 1000 − 200

    # O jogo fecha o microciclo 5 → compara com a semana inteira → baixo.
    df2 = _df(rows + [_sessao("Ana", "2026-09-12", 5, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=30)])
    chaves2 = [s["chave"] for s in construir_avisos_dashboard(df2, sem_acwr)[0]["sinais"]]
    assert "hsr_baixo" in chaves2


def test_prontidao_usa_a_data_real_e_avisa_dados_parados():
    """Com «hoje» 10 dias depois do último dado, o Hooper de então já não vale
    para hoje e a resposta diz há quantos dias não há dados."""
    from app.services.prontidao_service import calcular_prontidao
    rows = [_sessao("Ana", d, 1, "MD-3", ci=300, hooper=5) for d in ["2026-08-01", "2026-08-05"]]
    rows.append(_sessao("Ana", "2026-08-10", 1, "MD-3", ci=300, hooper=12))  # +7 vs média
    df = _df(rows)
    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}
    no_dia = calcular_prontidao(df, None, {}, sem_acwr, hoje=pd.Timestamp("2026-08-10"))
    assert no_dia["jogadores"][0]["estado"] == "vigiar" and no_dia["dias_sem_dados"] == 0
    depois = calcular_prontidao(df, None, {}, sem_acwr, hoje=pd.Timestamp("2026-08-20"))
    assert depois["dias_sem_dados"] == 10
    assert depois["jogadores"][0]["hooper"]["valido"] is False
    assert depois["jogadores"][0]["estado"] == "pronto"


def test_avisos_dashboard_excluem_indisponiveis_e_juntam_prontidao():
    """O Centro de Controlo usa os mesmos sinais de CMJ/Hooper da Prontidão e
    deixa de fora quem não está apto."""
    from app.services.alertas_service import construir_avisos_dashboard
    rows = []
    for nome in ("Ana", "Rui", "Zé"):
        for d in ["2026-08-01", "2026-08-05"]:
            rows.append(_sessao(nome, d, 1, "MD-3", hooper=5, vmax=30))
    rows.append(_sessao("Ana", "2026-08-10", 1, "MD-3", hooper=11, vmax=30))  # +6 vs média
    rows.append(_sessao("Rui", "2026-08-10", 1, "MD-3", hooper=5, vmax=30))
    rows.append(_sessao("Zé", "2026-08-10", 1, "MD-3", hooper=12, vmax=30))
    testes = pd.DataFrame([
        {"nome": "Rui", "data": "2026-07-27", "altura_salto_cm": 40},
        {"nome": "Rui", "data": "2026-08-09", "altura_salto_cm": 35},  # −12,5 %
    ])
    sem_acwr = {"acwr_alto": 99, "acwr_muito_alto": 99}
    avisos = {a["player_name"]: a for a in construir_avisos_dashboard(
        _df(rows), sem_acwr, estados={"Zé": "lesionado"}, testes=testes, hoje=pd.Timestamp("2026-08-10"))}
    assert "Zé" not in avisos
    assert [s["chave"] for s in avisos["Ana"]["sinais"]] == ["hooper"]
    assert [s["chave"] for s in avisos["Rui"]["sinais"]] == ["cmj"]
    assert avisos["Rui"]["status"] == "high-attention"  # queda ≥ 10 % → severidade 2


def test_wellness_recusa_resposta_em_falta():
    """Um sub-score em falta ou fora de 1–5 é recusado (antes virava 3)."""
    import pytest
    from app.services.wellness_service import _validar
    assert _validar("sono", 4) == 4
    for mau in (None, "", 0, 6, 2.5):
        with pytest.raises(ValueError):
            _validar("sono", mau)


def test_cmj_dentro_da_variacao_propria_nao_e_queda():
    """−6 % num atleta que varia ±7 % entre testes não é sinal; o mesmo −6 %
    num atleta muito estável é."""
    from app.services.limites_service import DEFAULTS
    from app.services.prontidao_service import _cmj, sev_cmj
    hoje = pd.Timestamp("2026-09-30")
    def testes(nome, base, ultimo):
        datas = pd.date_range("2026-08-01", periods=len(base), freq="7D")
        linhas = [{"nome": nome, "data": d, "altura_salto_cm": v} for d, v in zip(datas, base)]
        return linhas + [{"nome": nome, "data": hoje - pd.Timedelta(days=1), "altura_salto_cm": ultimo}]
    df = pd.DataFrame(testes("Variável", [40, 37, 43, 38, 42], 37.6) + testes("Estável", [40, 40.2, 39.8, 40.1, 39.9], 37.6))
    c = _cmj(df, hoje)
    assert sev_cmj(c["Variável"], DEFAULTS) == 0
    assert sev_cmj(c["Estável"], DEFAULTS) == 1


def test_cada_sinal_traz_acao_sugerida_com_numeros():
    """Exposição baixa a meio da semana diz quanto falta e por sessão; o
    bem-estar baixo aponta o pior item; Vmax diz a velocidade-alvo."""
    from app.services.alertas_service import construir_avisos_dashboard
    rows = []
    for d in ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]:
        rows.append(_sessao("Ana", d, 4, "MD-3", hsr=200, vmax=30, hooper=5))
    rows.append(_sessao("Ana", "2026-09-05", 4, "MD", tipo="Jogo", hsr=1000, sprint=200, vmax=30, hooper=5))
    # Semana 5: 2 treinos feitos (de ~4), HSR 50+50 = 100 → 0,10× (esperado até hoje 0,30×).
    # (mais de 7 dias depois do jogo, para o melhor Vmax da janela ser 25).
    for d in ["2026-09-14", "2026-09-15"]:
        rows.append(_sessao("Ana", d, 5, "MD-5", hsr=50, sprint=40, vmax=25, hooper=5))
    rows[-1].update({"Hooper Index": 12, "Sono (1-5)": 4, "Dor Musc. (1-5)": 1, "Stress (1-5)": 3, "Humor (1-5)": 4})
    df = _df(rows)
    sinais = {s["chave"]: s for s in construir_avisos_dashboard(df, {"acwr_alto": 99, "acwr_muito_alto": 99},
                                                               hoje=pd.Timestamp("2026-09-15"))[0]["sinais"]}
    # 0,60 × 1000 − 100 = 500 m em falta, por 2 treinos restantes → 250 m cada.
    assert sinais["hsr_baixo"]["detalhe"]["em_falta"] == 500
    assert "500 m" in sinais["hsr_baixo"]["acao"] and "250 m" in sinais["hsr_baixo"]["acao"]
    assert "dor muscular 1/5" in sinais["hooper"]["acao"]
    assert "27.0 km/h" in sinais["vmax"]["acao"]  # 90 % de 30


def test_resumo_decisoes_seguimento_a_14_dias():
    """Por sinal: decisões por tipo, lesão nos 14 dias seguintes e sinal
    repetido; decisões com menos de 14 dias ficam «em seguimento»."""
    from datetime import date
    from app.services.decisoes_service import resumir
    dec = pd.DataFrame([
        {"jogador": "Ana", "data": "2026-09-01", "sinal": "acwr", "decisao": "ignorar"},
        {"jogador": "Ana", "data": "2026-09-05", "sinal": "acwr", "decisao": "reduzir"},   # repetido 4 dias depois
        {"jogador": "Rui", "data": "2026-09-02", "sinal": "acwr", "decisao": "reduzir"},
        {"jogador": "Rui", "data": "2026-09-25", "sinal": "hooper", "decisao": "manter"},  # ainda em seguimento
    ])
    les = pd.DataFrame([{"jogador": "Ana", "data_inicio": "2026-09-10"}])
    r = resumir(dec, les, date(2026, 9, 30))
    acwr = next(x for x in r["sinais"] if x["sinal"] == "acwr")
    assert acwr["n"] == 3 and acwr["por_decisao"]["reduzir"] == 2 and acwr["fechadas"] == 3
    assert acwr["lesao_seguinte"] == 2  # as duas decisões da Ana têm a lesão de 10/09 nos 14 dias
    assert acwr["lesao_por_decisao"] == {"reduzir": 1, "ajustar": 0, "manter": 0, "ignorar": 1}
    assert acwr["repetido"] == 1
    hooper = next(x for x in r["sinais"] if x["sinal"] == "hooper")
    assert hooper["em_seguimento"] == 1 and hooper["fechadas"] == 0
    assert resumir(pd.DataFrame(), None, date(2026, 9, 30))["total"] == 0


def test_decisao_invalida_e_recusada():
    import pytest
    from app.services.decisoes_service import registar
    with pytest.raises(ValueError):
        registar("t", None, "Ana", None, "2026-09-01", "acwr", "talvez")


def test_protocolo_da_academia_sobrepoe_limites_pessoais():
    """Com o protocolo ativo, todas as equipas usam a base (com exceção por
    escalão); sem protocolo, valem os limites pessoais."""
    from app.services.limites_service import DEFAULTS, resolver
    pessoais = {"acwr_alto": 1.2}
    prot = {"ativo": True, "base": {"acwr_alto": 1.4, "lixo": 9}, "escaloes": {"Sub-13": {"hooper_alto": 10}}}
    lim, origem = resolver(pessoais, prot, "Sub-15")
    assert lim["acwr_alto"] == 1.4 and lim["hooper_alto"] == DEFAULTS["hooper_alto"] and "lixo" not in lim
    assert origem == {"tipo": "academia", "escalao": "Sub-15", "excecao_escalao": False}
    lim13, origem13 = resolver(pessoais, prot, "Sub-13")
    assert lim13["hooper_alto"] == 10 and lim13["acwr_alto"] == 1.4 and origem13["excecao_escalao"]
    lim_off, origem_off = resolver(pessoais, {**prot, "ativo": False}, "Sub-13")
    assert lim_off["acwr_alto"] == 1.2 and origem_off["tipo"] == "pessoal"


def test_qualidade_dos_dados_por_equipa_e_mes():
    """% de wellness/PSE/GPS sobre os jogador-dias com sessão; dias só com
    wellness não contam como sessão."""
    from app.services.qualidade_dados_service import calcular
    linhas = pd.DataFrame([
        {"team_id": "A", "player_id": 1, "data": "2026-10-01", "tem_gps": True, "tem_pse": True, "tem_wellness": True},
        {"team_id": "A", "player_id": 2, "data": "2026-10-01", "tem_gps": True, "tem_pse": False, "tem_wellness": False},
        {"team_id": "A", "player_id": 1, "data": "2026-10-02", "tem_gps": False, "tem_pse": True, "tem_wellness": True},
        {"team_id": "A", "player_id": 2, "data": "2026-10-02", "tem_gps": True, "tem_pse": True, "tem_wellness": True},
        {"team_id": "A", "player_id": 2, "data": "2026-10-03", "tem_gps": False, "tem_pse": False, "tem_wellness": True},  # só wellness
        {"team_id": "A", "player_id": 1, "data": "2026-09-20", "tem_gps": True, "tem_pse": True, "tem_wellness": False},
    ])
    out = calcular(linhas)
    out_m = out[0]["meses"]
    assert [m["mes"] for m in out_m] == ["2026-10", "2026-09"]
    out10 = out_m[0]
    assert out10["jogador_dias"] == 4 and out10["dias_sessao"] == 2
    assert out10["wellness_pct"] == 75 and out10["pse_pct"] == 75 and out10["gps_pct"] == 75
    assert out10["wellness_nivel"] == "medio" and out_m[1]["wellness_nivel"] == "fraco"


def test_velocidade_crescimento_e_sinal_de_pico():
    """cm/ano entre medições com ≥ 60 dias; ≥ 7 cm/ano = pico, e vira aviso."""
    from app.services.alertas_service import construir_avisos_dashboard
    from app.services.ficha_atleta_service import velocidade_crescimento
    serie = pd.DataFrame([
        {"metrica": "altura_cm", "data": "2026-01-10", "valor": 150.0},
        {"metrica": "altura_cm", "data": "2026-02-01", "valor": 150.5},   # só 22 dias da anterior
        {"metrica": "altura_cm", "data": "2026-07-10", "valor": 154.5},   # +4,0 cm desde 1/2 (159 dias) → ~9,2 cm/ano
        {"metrica": "peso_kg", "data": "2026-07-10", "valor": 45.0},
    ])
    v = velocidade_crescimento(serie)
    assert [x["data"] for x in v] == ["2026-07-10"]
    assert v[0]["desde"] == "2026-02-01" and v[0]["cm_ano"] == 9.2 and v[0]["pico"] is True
    rows = [_sessao("Ana", "2026-07-10", 1, "MD-3")]
    avisos = construir_avisos_dashboard(_df(rows), {"acwr_alto": 99, "acwr_muito_alto": 99}, crescimento={"Ana": v[0]})
    assert [s["chave"] for s in avisos[0]["sinais"]] == ["crescimento"]


def test_fecho_de_semana_linhas_para_o_treinador():
    """Semana, carga vs anterior, exposição, disponibilidade, avisos/decisões e
    próxima semana — só com dados que existem."""
    from app.services.fecho_semana_service import montar
    rows = [_sessao(n, d, 4, "MD-3", ci=300) for n in ("Ana", "Rui") for d in ["2026-09-01", "2026-09-02"]]
    rows += [_sessao(n, d, 5, "MD-3", ci=360) for n in ("Ana", "Rui") for d in ["2026-09-08", "2026-09-09"]]
    rows += [_sessao("Ana", "2026-09-12", 5, "MD", tipo="Jogo", ci=500)]
    df = _df(rows)
    expo = {"tem_dados": True, "metricas": [{"label": "HSR", "ratio_equipa": 0.55, "ref": [0.6, 0.9],
                                             "jogadores": [{"jogador": "Rui", "zona": "baixo"}, {"jogador": "Ana", "zona": "ok"}]}]}
    avisos = [{"player_name": "Rui", "status": "high-attention"}, {"player_name": "Ana", "status": "normal"}]
    decisoes = [{"decisao": "reduzir"}, {"decisao": "reduzir"}, {"decisao": "manter"}]
    comp = {"minimo_pct": 60, "jogadores": [{"jogador": "Rui"}]}
    linhas = montar(df, 5, expo, {"Ana": "apto", "Rui": "apto", "Zé": "lesionado"}, avisos, decisoes, comp)
    texto = "\n".join(linhas)
    assert linhas[0].startswith("Semana 5 (08/09–12/09): 2 treino(s) e 1 jogo(s).")
    # Ana 360+360+500 = 1220 e Rui 720 → média 970 UA, vs 600 na semana 4 → +62 %.
    assert "Carga interna média por jogador: 970 UA (+62% vs semana 4)" in texto
    assert "HSR 0.55× (ref. 0.60–0.90). Abaixo da zona: Rui." in texto
    assert "Disponibilidade: 2 de 3 aptos — fora: Zé (lesionado)." in texto
    assert "Decisões registadas: 3 (reduzir carga 2, manter 1)." in texto
    assert linhas[-1] == "Próxima semana: compensar Rui (menos de 60% dos minutos no último jogo); vigiar Rui (mais do que um aviso)."


def test_forca_tonelagem_e1rm_e_progressao():
    from datetime import date
    import pytest
    from app.services.forca_service import e1rm, limpar_linhas, progressao, tonelagem
    assert tonelagem(4, 6, 50) == 1200
    assert e1rm(50, 6) == 60.0      # 50 × (1 + 6/30)
    assert e1rm(50, 15) is None     # demasiadas repetições para estimar
    assert e1rm(80, 1) == 80.0
    assert limpar_linhas([{"exercicio": " Agachamento ", "series": "4", "repeticoes": 6, "carga_kg": 50},
                          {"exercicio": ""}]) == [{"ordem": 0, "exercicio": "Agachamento", "series": 4, "repeticoes": 6, "carga_kg": 50.0, "feito": True}]
    with pytest.raises(ValueError):
        limpar_linhas([{"exercicio": "Agachamento", "series": 50}])
    regs = pd.DataFrame([
        {"data": "2026-10-05", "exercicio": "Agachamento", "series": 4, "repeticoes": 6, "carga_kg": 50, "feito": True},
        {"data": "2026-10-12", "exercicio": "Agachamento", "series": 4, "repeticoes": 6, "carga_kg": 55, "feito": True},
        {"data": "2026-10-12", "exercicio": "Nordic", "series": 3, "repeticoes": 5, "carga_kg": None, "feito": True},
        {"data": "2026-10-13", "exercicio": "Agachamento", "series": 4, "repeticoes": 6, "carga_kg": 90, "feito": False},  # não feito
    ])
    p = progressao(regs, date(2026, 10, 20))
    assert [s["tonelagem"] for s in p["semanas"]] == [1200, 1320]
    ag = next(e for e in p["exercicios"] if e["exercicio"] == "Agachamento")
    assert ag["atual"] == 66.0 and ag["variacao_pct"] == 10.0


def test_ginasio_nao_conta_como_treino_de_campo_na_exposicao():
    """Uma sessão de ginásio no microciclo não aumenta os treinos feitos."""
    from app.services.alertas_service import progresso_microciclo
    from app.services.referencia_jogo import mascara_jogo
    rows = [_sessao("Ana", d, 4, "MD-3") for d in ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]]
    rows.append(_sessao("Ana", "2026-09-05", 4, "MD", tipo="Jogo"))
    rows.append(_sessao("Ana", "2026-09-07", 5, "MD-5"))
    gin = _sessao("Ana", "2026-09-08", 5, "MD-4", tipo="Ginásio")
    rows.append(gin)
    df = _df(rows)
    assert progresso_microciclo(df, mascara_jogo(df), 5)["treinos_feitos"] == 1


def test_epidemiologia_lesoes_por_1000_horas():
    """Incidência e carga por 1000 h, separadas em treino e jogo, e
    disponibilidade com os dias perdidos dentro do período."""
    from datetime import date
    from app.services.lesoes_service import epidemiologia
    sess = []
    for i in range(20):  # 20 treinos de 90' para 10 jogadores = 300 h
        for j in range(10):
            sess.append({"Jogador": f"J{j}", "Data": f"2026-09-{i + 1:02d}", "Tipo": "Treino", "Dia MD": "MD-3", "Duração (min)": 90})
    for j in range(10):  # 1 jogo de 60' = 10 h
        sess.append({"Jogador": f"J{j}", "Data": "2026-09-25", "Tipo": "Jogo", "Dia MD": "MD", "Duração (min)": 60})
    les = pd.DataFrame([
        {"jogador": "J1", "data_inicio": "2026-09-05", "data_fim": "2026-09-15", "contexto": "treino", "zona": "coxa_post"},
        {"jogador": "J2", "data_inicio": "2026-09-25", "data_fim": None, "contexto": "jogo", "zona": "tornozelo"},
        {"jogador": "J3", "data_inicio": "2026-08-25", "data_fim": "2026-09-03", "contexto": None, "zona": "joelho"},  # começou antes
    ])
    e = epidemiologia(les, pd.DataFrame(sess), date(2026, 9, 1), date(2026, 9, 30), 10)
    assert e["horas_treino"] == 300 and e["horas_jogo"] == 10 and e["horas"] == 310
    assert e["n_lesoes"] == 2                    # a de agosto não é nova no período
    assert e["incidencia_treino"] == round(1 / 300 * 1000, 1) and e["incidencia_jogo"] == 100.0
    assert e["dias_perdidos"] == 10 + 5 + 2      # 5–15, 25–30, 1–3
    assert e["disponibilidade_pct"] == round((1 - 17 / 300) * 100, 1)
    assert e["estimativa_instavel"] is True


def test_rtp_criterios_clinicos_e_resposta_no_dia_seguinte():
    """Com o GPS cumprido mas um critério por marcar, a etapa fica «aguarda
    critérios»; uma sessão seguida de Hooper muito acima da média não conta."""
    from app.services.rtp_service import avaliar_plano
    rows = [
        _sessao("Ana", "2026-07-01", 1, "MD", tipo="Jogo", hsr=1000, dist=10000, vmax=32, hooper=5),
        _sessao("Ana", "2026-07-20", 2, "MD-3", hsr=100, dist=2000, vmax=20, hooper=5),
        _sessao("Ana", "2026-08-02", 5, "MD-3", hsr=320, dist=5200, vmax=24, hooper=5),   # ✓
        _sessao("Ana", "2026-08-03", 5, "MD-2", hsr=330, dist=5300, vmax=24, hooper=6),   # ✓ (mas amanhã Hooper 9)
        _sessao("Ana", "2026-08-04", 5, "MD-1", hsr=50, dist=1000, vmax=18, hooper=9),    # nada; Hooper +4 vs média 5
        _sessao("Ana", "2026-08-06", 6, "MD-3", hsr=340, dist=5400, vmax=24, hooper=5),   # ✓
    ]
    etapas = [{"nome": "E1", "pct_distancia": 50, "pct_hsr": 30,
               "criterios": [{"texto": "Sem dor", "cumprido": True}, {"texto": "Força ≥ 80 %", "cumprido": False}]},
              {"nome": "E2", "pct_hsr": 100}]
    out = avaliar_plano(_df(rows), "Ana", "2026-08-01", etapas, sessoes_por_etapa=2)
    resp = {s["data"]: s for s in out["sessoes"]}
    assert resp["2026-08-03"]["resposta"] == "negativa" and resp["2026-08-03"]["conta_para_etapa"] is None
    e1 = out["etapas"][0]
    assert e1["gps_cumprido"] and e1["estado"] == "aguarda_criterios" and out["etapa_atual"] == 1
    etapas[0]["criterios"][1]["cumprido"] = True
    out2 = avaliar_plano(_df(rows), "Ana", "2026-08-01", etapas, sessoes_por_etapa=2)
    assert out2["etapas"][0]["estado"] == "concluida" and out2["etapa_atual"] == 2
