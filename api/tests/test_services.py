"""Testes dos serviços de cálculo — sem base de dados.

Cada teste substitui `carregar_df_equipa` do serviço em causa por um
DataFrame sintético, para validar a matemática (baseline, %HSR, benchmark,
quadrantes, limiares) de forma reprodutível.

Correr: cd api && pytest
"""
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
def test_match_benchmark_usa_jogo_mais_exigente(monkeypatch):
    import app.services.match_benchmark_service as mb
    rows = [
        _sessao("Ana", "2026-08-01", 1, "MD", tipo="Jogo", dist=9000),
        _sessao("Ana", "2026-08-08", 1, "MD", tipo="Jogo", dist=11000),  # mais exigente
        _sessao("Ana", "2026-08-11", 1, "MD-3", tipo="Treino", dist=7000),
    ]
    monkeypatch.setattr(mb, "carregar_df_equipa", lambda t: _df(rows))
    out = mb.obter_match_benchmark("t")
    dist = next(e for e in out["equipa"] if e["chave"] == "distancia_total_m")
    assert dist["benchmark"] == 11000  # pico, não média
    assert dist["pct"] == 64.0  # 7000/11000


# ── Sessão ─────────────────────────────────────────────────────────────────
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
    out = cb.obter_combinada("t")
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


def test_auto_mapa_reconhece_aliases():
    from utils.dados import auto_mapa
    mapa = auto_mapa(["Nome", "Distance", "HSR", "Vmax", "Xpto"])
    assert mapa["Nome"] == "Jogador"
    assert mapa["Distance"] == "Distância Total (m)"
    assert mapa["HSR"] == "HSR (m)"
    assert mapa["Vmax"] == "Vel. Máx (km/h)"
    assert "Xpto" not in mapa  # coluna desconhecida não é mapeada


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


# ── Limiares de alerta ─────────────────────────────────────────────────────
def test_limiares_configuraveis():
    from app.services.alertas_service import evaluate_player_alert
    a = evaluate_player_alert({"player_id": "1", "player_name": "X", "acwr": 1.35})
    b = evaluate_player_alert({"player_id": "1", "player_name": "X", "acwr": 1.35},
                              {"acwr_alto": 1.5, "acwr_muito_alto": 1.8})
    assert a.status == "attention"
    assert b.status == "normal"


# ── Motor de alertas unificado ──────────────────────────────────────────────
def test_classificar_acwr_partilhado_e_configuravel():
    """O classificador de ACWR é a fonte única partilhada pelo dashboard e pela
    Análise: por omissão reproduz os limiares clássicos (1.3 / 1.5) e respeita
    limiares personalizados."""
    from app.services.alertas_service import classificar_acwr
    assert classificar_acwr(1.35)[0] == 1        # ≥ acwr_alto (1.3) → atenção
    assert "ATENÇÃO" in classificar_acwr(1.35)[1]
    assert classificar_acwr(1.6)[0] == 2         # ≥ acwr_muito_alto (1.5) → risco
    assert "RISCO" in classificar_acwr(1.6)[1]
    assert classificar_acwr(1.0)[0] == 0         # ok
    # Limiares personalizados sobem a fasquia → 1.35 deixa de ser alerta.
    assert classificar_acwr(1.35, {"acwr_alto": 1.5, "acwr_muito_alto": 1.8})[0] == 0
    assert classificar_acwr(None)[1] == "❓"


def test_analise_alertas_respeitam_limites(monkeypatch):
    """A página Análise deixou de ter limiares fixos no código: usa os mesmos
    limites configuráveis do dashboard. Subir o limiar de Hooper silencia o
    alerta de wellness sem tocar em mais nada."""
    import app.services.analise_service as an
    rows = [_sessao("Ana", "2026-08-05", 1, "MD-3", hooper=15)]
    monkeypatch.setattr(an, "carregar_df_equipa", lambda t: _df(rows))
    monkeypatch.setattr(an, "listar_estados", lambda t: [])

    # hooper_alto por omissão = 14 → Hooper 15 dispara alerta de wellness.
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

    avisos = {a["player_name"]: a for a in construir_avisos_dashboard(_df(rows))}
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

    padrao = {a["player_name"]: a for a in construir_avisos_dashboard(df)}
    assert padrao["Ana"]["status"] != "normal"  # 0.50 < 0.60 → HSR baixa

    baixado = {a["player_name"]: a for a in construir_avisos_dashboard(df, {"hsr_semana_baixo": 0.40})}
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
