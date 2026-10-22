import pandas as pd

from app.services import jogador_semanas_service as js


def _df():
    linhas = []
    for mc, dist in zip(range(1, 8), [20000, 22000, 24000, 21000, 23000, 30000, 25000]):
        for k in range(2):
            linhas.append({"Data": pd.Timestamp(2026, 9, 1) + pd.Timedelta(days=7 * mc + k), "Microciclo (Nr)": mc,
                           "Distância Total (m)": dist / 2, "HSR (m)": 400.0, "Vel. Máx (km/h)": 28 + mc * 0.5 if k == 0 else 25})
    return pd.DataFrame(linhas)


def test_semanas_e_intervalo_padrao():
    ev = js.evolucao(_df(), None, None)
    assert ev["de"] == 3 and ev["ate"] == 7 and [s["microciclo"] for s in ev["semanas"]] == [3, 4, 5, 6, 7]
    assert ev["semanas"][0]["distancia"] == 24000 and ev["semanas"][0]["sessoes"] == 2
    assert ev["medias"]["distancia"] == 24600.0
    z6 = ev["semanas"][3]["z_distancia"]
    assert z6 > 1.5  # a semana de 30 km destaca-se
    assert ev["semanas"][-1]["pct_recorde"] == 100 and ev["recorde_vmax"] == 31.5


def test_acwr_variacao_e_zscore_constante():
    ev = js.evolucao(_df(), 2, 7)
    # MC 7 = 25000 ÷ média de MC 3–6 (24000, 21000, 23000, 30000 = 24500)
    assert ev["acwr"]["distancia"] == round(25000 / 24500, 2)
    assert ev["variacao_2_semanas"]["distancia"] == round((25000 - 30000) / 30000 * 100, 1)
    assert all(s["z_hsr"] == 0.0 for s in ev["semanas"])  # HSR igual todas as semanas
    assert js.zscores([1.0, 2.0])[0] == [None, None]
    assert js.variacao(0, 5) is None


def test_semana_incompleta():
    df = _df()
    assert js.evolucao(df, None, None)["referencia_incompleta"] is False
    df = df.drop(df.index[-1])  # MC 7 só com 1 das 2 sessões
    assert js.evolucao(df, None, None)["referencia_incompleta"] is True
    assert js.evolucao(df, 2, 6)["referencia_incompleta"] is False
