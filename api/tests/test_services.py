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
def test_match_benchmark_usa_referencia_por_90(monkeypatch):
    """Referência = média por 90' dos últimos jogos completos (não o pico)."""
    import app.services.match_benchmark_service as mb
    rows = [
        _sessao("Ana", "2026-08-01", 1, "MD", tipo="Jogo", dist=9000),
        _sessao("Ana", "2026-08-08", 1, "MD", tipo="Jogo", dist=11000),  # mais exigente
        _sessao("Ana", "2026-08-11", 1, "MD-3", tipo="Treino", dist=7000),
    ]
    monkeypatch.setattr(mb, "carregar_df_equipa", lambda t: _df(rows))
    out = mb.obter_match_benchmark("t")
    dist = next(e for e in out["equipa"] if e["chave"] == "distancia_total_m")
    assert dist["benchmark"] == 10000  # média dos dois jogos de 90'
    assert dist["pct"] == 70.0  # 7000/10000
    # Agregado por posição presente (Ana é CM).
    assert any(p["posicao"] == "CM" and p["metricas"]["distancia_total_m"]["pct"] == 70.0 for p in out["posicoes"])


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
def test_ia_snapshot_estrutura(monkeypatch):
    """O snapshot reúne estado do plantel, avisos e análise a partir dos serviços."""
    import app.services.ia_service as ia
    monkeypatch.setattr("app.services.dados_equipa.carregar_df_equipa", lambda t: pd.DataFrame({"Jogador": ["Ana"]}))
    monkeypatch.setattr("app.services.alertas_service.construir_avisos_dashboard",
                        lambda df, lim=None: [{"player_name": "Ana", "status": "attention", "reason_text": "x", "metric_value": "y", "primary_reason": "acwr"}])
    monkeypatch.setattr("app.services.alertas_service.obter_exposicao_semana", lambda df, lim=None: {"tem_dados": True, "metricas": []})
    monkeypatch.setattr("app.services.carga_externa_service.obter_carga_externa", lambda t: {"tem_dados": True, "sessao_recente": "2026-08-05", "kpis": []})
    monkeypatch.setattr("app.services.match_benchmark_service.obter_match_benchmark", lambda t: {"tem_dados": False})
    monkeypatch.setattr("app.services.analise_service.obter_analise",
                        lambda t, **kw: {"tem_dados": True, "microciclo_selecionado": 5, "carga_interna_media": 500,
                                         "monotonia_media": 1.5, "strain_medio": 750, "carga_por_dia": [], "ranking_carga": [], "alertas": {}})

    snap = ia.montar_snapshot("t")
    assert snap["tem_dados"] is True
    assert snap["estado_plantel"]["attention"] == 1
    assert len(snap["avisos"]) == 1
    assert snap["analise_microciclo"]["microciclo"] == 5


def test_ia_sem_dados_nao_chama_modelo(monkeypatch):
    """Com chave mas sem dados, responde com mensagem clara e não chama o modelo."""
    import app.services.ia_service as ia
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste")
    monkeypatch.setattr("app.services.dados_equipa.carregar_df_equipa", lambda t: pd.DataFrame())
    r = ia.perguntar("t", "Resume a semana")
    assert r["ok"] is True and "dados" in r["resposta"].lower()


def test_ia_sem_chave_avisa(monkeypatch):
    """Sem ANTHROPIC_API_KEY, a assistente avisa claramente e não tenta o modelo."""
    import app.services.ia_service as ia
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    r = ia.perguntar("t", "Resume a semana")
    assert r["ok"] is False and "ANTHROPIC_API_KEY" in r["erro"]


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
def test_referencia_jogo_por_90_ultimos_jogos_completos():
    """Usa a média por 90' dos últimos 5 jogos com ≥60'; jogos curtos não contam."""
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
    assert refs["Ana"]["valor"] == 900 and refs["Ana"]["fonte"] == "media_90"
    assert refs["Ana"]["n_jogos"] == 5


def test_referencia_jogo_normaliza_minutos_e_suplente_usa_posicao():
    """Um jogo de 60' é escalado a 90'; quem só jogou minutos curtos recebe a
    mediana da sua posição em vez de uma referência artificialmente baixa."""
    from app.services.referencia_jogo import referencias_jogo
    rui = _sessao("Rui", "2026-08-01", 1, "MD", tipo="Jogo", hsr=600, pos="EX")
    rui["Duração (min)"] = 60  # 600 m em 60' → 900 m por 90'
    suplente = _sessao("Zé", "2026-08-01", 1, "MD", tipo="Jogo", hsr=150, pos="EX")
    suplente["Duração (min)"] = 15
    refs = referencias_jogo(_df([rui, suplente]), "HSR (m)", jogadores={"Novo": "EX"})
    assert refs["Rui"]["valor"] == 900
    assert refs["Zé"]["valor"] == 900 and refs["Zé"]["fonte"] == "posicao"
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
    assert serie.iloc[2]["ACWR"] < serie.iloc[0]["ACWR"]
    assert calcular_acwr_global(_df(rows))["Ana"]["data"] == pd.Timestamp("2026-08-04")


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
    assert j["Ana"]["acwr"]["serie"]  # série para a tendência


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
    monkeypatch.setattr(ms, "get_conn", _conn_falsa({"from config_mensagens": [("eq1", "08:00", [1, 2, 3, 4, 5]), ("eq2", "09:30", [1, 2])]}, []))
    terca_0815 = datetime(2026, 10, 20, 8, 15, tzinfo=ms.FUSO)
    ms.envio_automatico(terca_0815)
    assert chamadas == [("eq1", "wellness", date(2026, 10, 20))]  # eq2 só depois das 09:30
    chamadas.clear()
    ms.envio_automatico(datetime(2026, 10, 24, 9, 0, tzinfo=ms.FUSO))  # sábado
    assert chamadas == []


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


# ── Ficha longitudinal ───────────────────────────────────────────────────────
def test_maturacao_moore():
    """Moore et al. 2015 (rapazes): offset e idade do PHV."""
    from app.services.ficha_atleta_service import maturacao
    m = maturacao(13.0, 158.0, 80.0)  # usa a altura sentado
    assert m["equacao"] == "altura sentado"
    assert m["offset"] == round(-8.128741 + 0.0070346 * 13.0 * 80.0, 2)  # −0.81
    assert m["estado"] == "circum-PHV" and m["idade_phv"] == round(13.0 - m["offset"], 2)
    so_altura = maturacao(12.0, 150.0, None)
    assert so_altura["equacao"] == "altura" and so_altura["estado"] == "pré-PHV"
    assert maturacao(None, 150, 80) is None and maturacao(12.0, None, None) is None
    assert maturacao(21.0, 180.0, 92.0)["fora_do_intervalo"] is True


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
