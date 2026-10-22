from datetime import date

import pandas as pd
import pytest

from app.services import epoca_service as ep
from app.services import exercicios_service as ex
from app.services.microciclos_service import exercicios_validos


def test_fases_continuas_junta_microciclos_seguidos():
    mcs = [
        {"data_inicio": "2026-07-06", "data_fim": "2026-07-12", "fase": "Pré-época"},
        {"data_inicio": "2026-07-13", "data_fim": "2026-07-19", "fase": "Pré-época"},
        {"data_inicio": "2026-07-20", "data_fim": "2026-07-26", "fase": "1.ª volta"},
        {"data_inicio": "2026-07-27", "data_fim": "2026-08-02", "fase": None},
    ]
    f = ep.fases_continuas(mcs)
    assert f == [{"fase": "Pré-época", "inicio": "2026-07-06", "fim": "2026-07-19", "microciclos": 2},
                 {"fase": "1.ª volta", "inicio": "2026-07-20", "fim": "2026-07-26", "microciclos": 1}]


def test_carga_semana_media_por_jogador_e_variacao():
    df = pd.DataFrame({
        "Data": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-01", "2026-09-06"]),
        "Jogador": ["A", "A", "B", "A"],
        "Tipo": ["Treino", "Treino", "Treino", "Jogo"],
        "Distância Total (m)": [5000, 4000, 6000, 9000],
        "Carga Interna": [300, 200, 400, 600],
    })
    c = ep.carga_semana(df, date(2026, 8, 31), date(2026, 9, 6))
    assert c["treino"]["distancia"] == 7500.0          # A 9000, B 6000 → média
    assert c["carga_interna"] == 750                   # A 1100 (inclui jogo), B 400
    assert c["n_treinos"] == 2 and c["n_jogos"] == 1
    sem = [{"real": {"carga_interna": 1000}}, {"real": {"carga_interna": 1400}}, {"real": {"carga_interna": None}}, {"real": {"carga_interna": 1450}}]
    ep.variacoes(sem)
    assert sem[1]["variacao_pct"] == 40.0 and sem[1]["pico"]
    assert sem[3]["variacao_pct"] == pytest.approx(3.6) and not sem[3]["pico"]


def test_estatisticas_gps_e_previsao():
    regs = [{"data": date(2026, 9, 1), "duracao_min": 10, "distancia_total_m": 1100, "hsr_m": 50, "sprint_m": None, "acc_n": 8, "dcc_n": 7, "pse": 6},
            {"data": date(2026, 9, 8), "duracao_min": 12, "distancia_total_m": 1200, "hsr_m": 72, "sprint_m": 6, "acc_n": 12, "dcc_n": 9, "pse": 7},
            {"data": date(2026, 9, 9), "duracao_min": 0, "distancia_total_m": 999}]
    e = ex.estatisticas_gps(regs)
    assert e["n"] == 2 and e["ultima"] == "2026-09-08"
    assert e["por_min"]["distancia"] == 105.0 and e["por_min"]["sprint"] == 0.5
    pm, fonte = ex.por_minuto_efetivo(e, {"distancia": 90})
    assert fonte == "gps" and pm["distancia"] == 105.0
    pm2, fonte2 = ex.por_minuto_efetivo({"n": 0}, {"distancia": "90", "hsr": ""})
    assert fonte2 == "manual" and pm2 == {"distancia": 90.0}
    bib = {ex.chave_nome("Rondo 5v2"): {"por_min": {"distancia": 60, "hsr": 1}}, "x1": {"por_min": {"distancia": 100}}}
    p = ex.prever([{"nome": "rondo 5V2 ", "minutos": 10}, {"id": "x1", "nome": "Outro", "minutos": 15}, {"nome": "Novo", "minutos": 5}], bib)
    assert p["minutos"] == 30 and p["carga"]["distancia"] == 2100 and p["carga"]["hsr"] == 10
    assert p["sem_dados"] == ["Novo"]


def test_validacoes():
    assert exercicios_validos([{"nome": " Rondo ", "minutos": "12"}, {"nome": "", "minutos": 5}]) == [{"nome": "Rondo", "minutos": 12}]
    with pytest.raises(ValueError):
        exercicios_validos([{"nome": "X", "minutos": 0}])
    with pytest.raises(ValueError):
        ex._validar({"nome": "X", "categoria": "Inventada"})
    d = ex._validar({"nome": " Jogo 4v4 ", "categoria": "Jogo reduzido", "duracao_min": "16", "manual": {"distancia": "95", "xx": 3}})
    assert d["nome"] == "Jogo 4v4" and d["duracao_min"] == 16 and d["manual"] == {"distancia": 95.0}
