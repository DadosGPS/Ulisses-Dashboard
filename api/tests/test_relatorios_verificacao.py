"""Períodos (partes/exercícios), verificação de dados e relatórios de treino/jogo — sem BD."""
from datetime import date

import pandas as pd

from app.services import periodos as per
from app.services.relatorios_service import alvos_do_dia, banda, relatorio_jogo, relatorio_treino
from app.services.verificacao_service import verificar_df


def _linha(jog, data, **kw):
    return {
        "Jogador": jog, "Posição": kw.get("pos", "MC"), "Data": pd.Timestamp(data), "Tipo": kw.get("tipo", "Treino"),
        "Dia MD": kw.get("md", "MD-3"), "Microciclo (Nr)": 1, "Duração (min)": kw.get("dur", 60),
        "Distância Total (m)": kw.get("dist", 5000), "HSR (m)": kw.get("hsr", 300), "Sprint (m)": kw.get("sprint", 50),
        "Acc (n)": 30, "Dcc (n)": 30, "Vel. Máx (km/h)": kw.get("vmax", 28), **({"Período": kw["periodo"]} if "periodo" in kw else {}),
    }


# ── Períodos ─────────────────────────────────────────────────────────────────
def test_classificar_periodos():
    assert per.classificar("1st Half")[:2] == ("parte", "1.ª parte")
    assert per.classificar("2ª parte")[:2] == ("parte", "2.ª parte")
    assert per.classificar("Segunda Parte")[:2] == ("parte", "2.ª parte")
    assert per.classificar("H1")[:2] == ("parte", "1.ª parte")
    assert per.classificar("Session")[0] == "total"
    assert per.classificar("Jogo")[0] == "total"
    assert per.classificar("1v1 duelos") == ("exercicio", "1v1 duelos", 0)
    assert per.classificar("Jogo reduzido 4v4")[0] == "exercicio"
    assert per.classificar("Prolongamento 1ª parte")[1] == "Prolongamento 1"


def test_separar_usa_total_quando_existe_senao_soma():
    df = pd.DataFrame([
        _linha("Ana", "2026-08-03", periodo="Rondo", dist=1000),
        _linha("Ana", "2026-08-03", periodo="4v4", dist=2000),
        _linha("Ana", "2026-08-03", periodo="Session", dist=3300),   # total do ficheiro
        _linha("Rui", "2026-08-03", periodo="Rondo", dist=900),
        _linha("Rui", "2026-08-03", periodo="4v4", dist=1800),        # sem total → soma
    ])
    sess, perio = per.separar(df)
    assert sorted(sess[sess["Jogador"] == "Ana"]["Distância Total (m)"]) == [3300]
    assert sess[sess["Jogador"] == "Rui"]["Distância Total (m)"].sum() == 2700
    assert len(perio) == 4 and set(perio["_categoria"]) == {"exercicio"}
    assert list(perio[perio["Jogador"] == "Ana"].sort_values("_ordem")["_periodo"]) == ["Rondo", "4v4"]


def test_separar_sem_coluna_periodo_nao_muda_nada():
    df = pd.DataFrame([_linha("Ana", "2026-08-03")])
    sess, perio = per.separar(df)
    assert len(sess) == 1 and perio.empty


# ── Verificação ──────────────────────────────────────────────────────────────
def test_verificacao_erros_bloqueiam_e_avisos_nao():
    df = pd.DataFrame([
        _linha("Ana", "2026-08-03"),
        _linha("Rui", "2026-08-03", vmax=61),                 # impossível → erro
        _linha("Zé", "2026-08-03", hsr=6000),                  # HSR > distância → erro
        _linha("Tó", "2026-08-03", vmax=38),                   # pico → aviso
        _linha("Joao Seco", "2026-08-03"),                     # ≈ «João Seco» já existente → aviso
    ])
    r = verificar_df(df, ["João Seco"], hoje=date(2026, 8, 4))
    codigos = {p["codigo"]: p for p in r["problemas"]}
    assert codigos["vel_impossivel"]["nivel"] == "erro" and codigos["vel_impossivel"]["exemplos"][0]["jogador"] == "Rui"
    assert codigos["hsr_maior_dist"]["nivel"] == "erro"
    assert codigos["vel_pico"]["nivel"] == "aviso"
    assert codigos["nome_parecido"]["nivel"] == "aviso"
    assert sorted(r["linhas_erro"]) == [1, 2]
    assert r["resumo"]["erros"] == 2


def test_verificacao_dados_limpos_sem_problemas():
    r = verificar_df(pd.DataFrame([_linha("Ana", "2026-08-03")]), hoje=date(2026, 8, 4))
    assert r["problemas"] == [] and r["linhas_erro"] == []


def test_verificacao_periodos_vs_total():
    df = pd.DataFrame([
        _linha("Ana", "2026-08-03", periodo="Rondo", dist=1000),
        _linha("Ana", "2026-08-03", periodo="Total", dist=2000),   # soma 1000 vs 2000
    ])
    r = verificar_df(df, hoje=date(2026, 8, 4))
    assert any(p["codigo"] == "periodos_vs_total" for p in r["problemas"])
    assert not any(p["codigo"] == "linhas_repetidas" for p in r["problemas"])


# ── Relatório de treino ──────────────────────────────────────────────────────
def test_banda():
    assert [banda(x) for x in (70, 85, 100, 115, 130, None)] == ["muito_abaixo", "abaixo", "dentro", "acima", "muito_acima", None]


def test_alvos_individuais_e_de_equipa():
    jog = {"Ana": "MC", "Rui": "DC"}
    refs = {"Ana": {"hsr": 600}, "Rui": {"hsr": 400}}
    alvos, fonte = alvos_do_dia(jog, refs, {"hsr": 2.0}, {"hsr": 25}, None)
    assert fonte == "individual" and alvos["Ana"]["hsr"] == 300 and alvos["Rui"]["hsr"] == 200
    alvos, fonte = alvos_do_dia(jog, {}, {}, None, {"hsr": 250, "distancia": None})
    assert fonte == "equipa" and alvos["Rui"] == {"hsr": 250}
    assert alvos_do_dia(jog, {}, {}, None, None)[1] is None


def test_relatorio_treino_alvo_habitual_e_exercicios():
    rows = [_linha("Ana", d, hsr=300) for d in ("2026-07-20", "2026-07-27", "2026-07-30", "2026-08-01")]
    rows += [_linha("Ana", "2026-08-03", hsr=450), _linha("Rui", "2026-08-03", hsr=190, vmax=31)]
    rows += [_linha("Ana", "2026-08-02", tipo="Jogo", md="MD", dur=80)]
    df = pd.DataFrame(rows)
    per_df = pd.DataFrame([
        {"Jogador": "Ana", "Posição": "MC", "Data": "2026-08-03", "Tipo": "Treino", "Período": "4v4", "Categoria": "exercicio", "Ordem": 100,
         "Duração (min)": 10, "Distância Total (m)": 1100, "HSR (m)": 80, "Sprint (m)": 10, "Acc (n)": 8, "Dcc (n)": 7, "Vel. Máx (km/h)": 26},
        {"Jogador": "Rui", "Posição": "MC", "Data": "2026-08-03", "Tipo": "Treino", "Período": "4v4", "Categoria": "exercicio", "Ordem": 100,
         "Duração (min)": 10, "Distância Total (m)": 900, "HSR (m)": 40, "Sprint (m)": 0, "Acc (n)": 6, "Dcc (n)": 6, "Vel. Máx (km/h)": 24},
        {"Jogador": "Ana", "Posição": "MC", "Data": "2026-07-30", "Tipo": "Treino", "Período": "4V4 ", "Categoria": "exercicio", "Ordem": 100,
         "Duração (min)": 10, "Distância Total (m)": 800, "HSR (m)": 50, "Sprint (m)": 0, "Acc (n)": 6, "Dcc (n)": 6, "Vel. Máx (km/h)": 24},
    ])
    out = relatorio_treino(df, date(2026, 8, 3), {"Ana": {"hsr": 300}, "Rui": {"hsr": 200}}, "individual", per_df)
    assert out["tem_dados"] and out["n_jogadores"] == 2 and out["n_habitual"] == 4
    ana = next(j for j in out["jogadores"] if j["jogador"] == "Ana")
    assert ana["valores"]["hsr"]["pct"] == 150 and ana["valores"]["hsr"]["banda"] == "muito_acima"
    assert ana["valores"]["hsr"]["vs_habitual"] == "alto"            # 450 vs 300 habitual em MD-3
    rui = next(j for j in out["jogadores"] if j["jogador"] == "Rui")
    assert rui["valores"]["hsr"]["banda"] == "dentro"
    assert out["resumo_alvo"] == {"abaixo": 0, "dentro": 1, "acima": 1}
    assert out["fonte_exercicios"] == "jogador"
    ex = out["exercicios"]["itens"][0]
    assert ex["distancia_min"] == 100 and ex["media_epoca_min"] == 80 and ex["vs_epoca_pct"] == 25
    assert {p["jogador"]: p["vs_equipa_pct"] for p in out["exercicios"]["por_jogador"]} == {"Ana": 10, "Rui": -10}


def test_relatorio_treino_dia_sem_treino():
    assert relatorio_treino(pd.DataFrame([_linha("Ana", "2026-08-03")]), date(2026, 8, 4), {}, None)["tem_dados"] is False


# ── Relatório de jogo ────────────────────────────────────────────────────────
def test_relatorio_jogo_por_minuto_e_partes():
    rows = []
    for i, d in enumerate(["2026-07-05", "2026-07-12", "2026-07-19", "2026-07-26"]):
        rows += [_linha("Ana", d, tipo="Jogo", md="MD", dur=80, dist=8000 + i * 10, hsr=400 + i * 5),
                 _linha("Rui", d, tipo="Jogo", md="MD", dur=80, dist=7800, hsr=350, pos="DC")]
    # Hoje: Ana joga 40' (metade) mas com a mesma intensidade → não pode sair «baixo».
    rows += [_linha("Ana", "2026-08-02", tipo="Jogo", md="MD", dur=40, dist=4010, hsr=205),
             _linha("Rui", "2026-08-02", tipo="Jogo", md="MD", dur=80, dist=9500, hsr=600, pos="DC")]
    per_df = pd.DataFrame([
        {"Jogador": "Rui", "Posição": "DC", "Data": "2026-08-02", "Tipo": "Jogo", "Período": "1.ª parte", "Categoria": "parte", "Ordem": 1,
         "Duração (min)": 40, "Distância Total (m)": 5000, "HSR (m)": 350, "Sprint (m)": 30, "Acc (n)": 15, "Dcc (n)": 15, "Vel. Máx (km/h)": 29},
        {"Jogador": "Rui", "Posição": "DC", "Data": "2026-08-02", "Tipo": "Jogo", "Período": "2.ª parte", "Categoria": "parte", "Ordem": 2,
         "Duração (min)": 40, "Distância Total (m)": 4500, "HSR (m)": 250, "Sprint (m)": 20, "Acc (n)": 15, "Dcc (n)": 15, "Vel. Máx (km/h)": 28},
    ])
    out = relatorio_jogo(pd.DataFrame(rows), date(2026, 8, 2), per_df, jogador="Ana", adversarios={"2026-08-02": "Rival"})
    assert out["tem_dados"] and out["adversario"] == "Rival" and out["n_jogos_epoca"] == 4
    assert out["n_completos"] == 1   # só o Rui fez ≥ 75 % dos minutos
    ana = next(j for j in out["jogadores"] if j["jogador"] == "Ana")
    assert ana["valores"]["distancia"]["estado"] == "normal"
    rui = next(j for j in out["jogadores"] if j["jogador"] == "Rui")
    assert rui["valores"]["hsr"]["estado"] == "alto"
    assert out["partes"]["nomes"] == ["1.ª parte", "2.ª parte"]
    assert out["partes"]["variacao_pct"]["distancia"] == -10
    ind = out["individual"]
    assert ind["jogos"][0]["atual"] and ind["recordes"]["distancia"]["valor"] == 8030 and ind["n_validos"] == 5
