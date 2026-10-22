from datetime import date

import pandas as pd

from app.services import referencias_service as ref


def _av(linhas):
    df = pd.DataFrame(linhas, columns=["atleta_id", "data", "metrica", "valor", "idade"])
    df["data"] = pd.to_datetime(df["data"])
    return df


def test_juntar_maturacao_usa_a_medicao_mais_proxima_dentro_da_janela():
    av = _av([
        ("a", "2026-09-01", "sprint_10m_s", 1.9, 14.2),
        ("a", "2026-03-01", "sprint_10m_s", 2.0, 13.7),   # > 120 dias da medição
        ("b", "2026-09-05", "sprint_10m_s", 1.8, 15.0),
    ])
    mats = pd.DataFrame([("a", pd.Timestamp("2026-08-20"), 88.0, "Início da puberdade")],
                        columns=["atleta_id", "data", "pct_pah", "categoria"])
    j = ref.juntar_maturacao(av, mats)
    assert list(j["categoria_mat"]) == ["Início da puberdade", None, None]
    assert list(j["valor"]) == [1.9, 2.0, 1.8]  # mantém a ordem original


def test_amostras_um_valor_por_atleta_e_percentil_por_idade_e_maturacao():
    linhas = []
    for i in range(6):
        linhas.append((f"a{i}", "2026-01-10", "cmj_cm", 20 + i, 13.5))
        linhas.append((f"a{i}", "2026-04-10", "cmj_cm", 22 + i, 13.8))  # mais recente conta
    av = _av(linhas)
    av["categoria_mat"] = "Meio da puberdade"
    am = ref.amostras(av)
    assert sorted(am["idade"][("cmj_cm", 13)]) == [22, 23, 24, 25, 26, 27]
    r = ref.anotar({"valor": 27.0, "idade": 13.9, "cat": "Meio da puberdade"}, "cmj_cm", am)
    assert r["p_idade"] >= 90 and r["p_mat"] >= 90
    assert r["ref_idade"]["n"] == 6 and r["ref_idade"]["p50"] == 24.5
    # tempos: menos é melhor
    r2 = ref.anotar({"valor": 1.70, "idade": 13.0}, "sprint_10m_s", {"idade": {("sprint_10m_s", 13): [1.7, 1.8, 1.9, 2.0, 2.1]}, "mat": {}})
    assert r2["p_idade"] >= 85
    # amostra pequena: sem percentil, só n
    r3 = ref.anotar({"valor": 30.0, "idade": 15.0}, "cmj_cm", {"idade": {("cmj_cm", 15): [20, 25]}, "mat": {}})
    assert r3["p_idade"] is None and r3["ref_idade"] == {"idade": 15, "n": 2}


def test_antropometria_sem_referencia_maturacional():
    am = {"idade": {}, "mat": {("altura_cm", "Fim da puberdade"): [170, 172, 175, 178, 180]}}
    r = ref.anotar({"valor": 175.0, "idade": None, "cat": "Fim da puberdade"}, "altura_cm", am)
    assert "p_mat" not in r and "p_idade" not in r


def test_estatisticas_e_valores_por_momento_ref():
    st = ref.estatisticas([1.8, 2.0, 1.9])
    assert st["n"] == 3 and st["media"] == 1.9 and st["mediana"] == 1.9 and st["dp"] == 0.1
    assert ref.estatisticas([]) is None
    av = _av([("a", "2026-09-10", "cmj_cm", 30, 14.1), ("a", "2026-11-10", "cmj_cm", 32, 14.3)])
    av["categoria_mat"] = [None, "Meio da puberdade"]
    v = ref.valores_por_momento_ref(av)
    assert v["cmj_cm"][1] == {"valor": 30.0, "data": "2026-09-10", "idade": 14.1, "cat": None}
    assert v["cmj_cm"][2]["cat"] == "Meio da puberdade"


def test_maturacoes_khamis_roche():
    av = _av([("a", "2026-09-01", "altura_cm", 160.0, 14.0), ("a", "2026-09-01", "peso_kg", 50.0, 14.0)])
    m = ref.maturacoes(av, {"a": (180.0, 165.0)})
    assert len(m) == 1 and m.iloc[0]["categoria"] in ref.CATEGORIAS_MAT
    assert ref.maturacoes(av, {}).empty
