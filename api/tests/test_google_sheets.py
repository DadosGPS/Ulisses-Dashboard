"""Leitura da folha de PSE do Google Sheets (sem rede nem BD)."""
from datetime import date

import pytest

from app.services import google_sheets_service as gs

CAB = ["TEAM", "DATE", "NAME", "WEEK", "DURATION", "RPE", "sRPE", "expected RPE", "expected sRPE",
       "Training Type", "In AVG?", "NAMEDATE", "Notes"]


def _l(d, nome, semana, dur, rpe, esp, tipo, equipa="P15", avg="Yes"):
    srpe = "" if rpe == "" or dur == "" else str(int(float(rpe.replace(",", ".")) * float(dur)))
    esp_s = "" if esp == "" or dur == "" else str(int(float(esp) * float(dur or 0)))
    return [equipa, d, nome, semana, dur, rpe, srpe, esp, esp_s, tipo, avg, nome + d, ""]


def _folha():
    return [CAB,
            _l("01/11/2026", "Ana", "44", "80", "8", "8", "MD"),            # jogo antes do início
            _l("02/11/2026", "Ana", "45", "75", "4", "5", "RECOVERY"),      # antes do início
            _l("03/11/2026", "Ana", "45", "90", "8", "8", "STRENGTH"),
            _l("03/11/2026", "Rui", "45", "90", "7,0", "8", "STRENGTH"),
            _l("03/11/2026", "Zé", "45", "90", "", "8", "STRENGTH"),         # não respondeu
            _l("03/11/2026", "Outro", "45", "90", "6", "8", "STRENGTH", equipa="P16"),
            _l("06/11/2026", "Ana", "45", "90", "5", "5", "REACTION"),
            _l("07/11/2026", "Ana", "45", "60", "9", "8", "MD"),
            _l("07/11/2026", "Rui", "45", "0", "", "8", "MD", avg="No"),
            _l("10/11/2026", "Ana", "46", "90", "12", "8", "STRENGTH")]      # PSE impossível


def test_cabecalho_e_filtros():
    registos = gs.ler_tabela([["Relatório PSE"], [], *_folha()])
    r = gs.preparar(registos, date(2026, 11, 3), "P15")
    por_chave = {(s["jogador"], s["data"].isoformat()): s for s in r["sessoes"]}

    assert set(por_chave) == {("Ana", "2026-11-03"), ("Rui", "2026-11-03"), ("Ana", "2026-11-06"), ("Ana", "2026-11-07")}
    assert r["resumo"]["ignoradas"] == {"antes_inicio": 2, "sem_pse": 2, "pse_invalida": 1}
    assert r["resumo"]["intervalo"] == ["2026-11-03", "2026-11-07"]

    rui = por_chave[("Rui", "2026-11-03")]
    assert rui["pse_sessao"] == 7.0 and rui["carga_interna"] == 630 and rui["duracao_min"] == 90
    assert rui["extra"]["PSE esperada"] == 8 and rui["extra"]["Origem"] == "Google Sheets"
    assert rui["microciclo_nr"] == 45 and rui["tipo"] == "Treino"


def test_dia_md_a_partir_dos_jogos():
    r = gs.preparar(gs.ler_tabela(_folha()), date(2026, 11, 3), "P15")
    dias = {s["data"].isoformat(): (s["tipo"], s["dia_md"]) for s in r["sessoes"]}
    assert dias["2026-11-03"] == ("Treino", "MD+2")   # 2 dias depois do jogo de 1/11
    assert dias["2026-11-06"] == ("Treino", "MD-1")
    assert dias["2026-11-07"] == ("Jogo", "MD")


def test_pse_esperada_por_dia():
    r = gs.preparar(gs.ler_tabela(_folha()), date(2026, 11, 3), "P15")
    esperada = {(p["microciclo"], p["dia_md"]): p["pse_esperada"] for p in r["pse_esperada"]}
    assert esperada[(45, "MD+2")] == 8
    assert esperada[(45, "MD-1")] == 5
    assert esperada[(45, "MD")] == 8
    duracao = {(p["microciclo"], p["dia_md"]): p["duracao_min"] for p in r["pse_esperada"]}
    assert duracao[(45, "MD+2")] == 90 and duracao[(45, "MD")] == 60


def test_jogo_de_domingo_fica_na_semana_dos_treinos():
    # Na folha (WEEKNUM do Excel) o domingo já é a semana seguinte.
    folha = [CAB, _l("13/11/2026", "Ana", "46", "90", "7", "7", "SPEED"),
             _l("15/11/2026", "Ana", "47", "60", "8", "8", "MD")]
    r = gs.preparar(gs.ler_tabela(folha), date(2026, 11, 3))
    assert {s["microciclo_nr"] for s in r["sessoes"]} == {46}
    assert r["sessoes"][1]["extra"]["Semana (folha)"] == 47


def test_plano_da_app_tem_prioridade():
    plano = {"2026-11-03": {"microciclo": 12, "dia_md": "MD-4", "tipo": "Treino"}}
    r = gs.preparar(gs.ler_tabela(_folha()), date(2026, 11, 3), "P15", plano)
    s = next(s for s in r["sessoes"] if s["data"] == date(2026, 11, 3))
    assert (s["microciclo_nr"], s["dia_md"]) == (12, "MD-4")


@pytest.mark.parametrize("tipo,jogo", [
    ("MD", True), ("MD (AGF)", True), ("MD - Bjärreds", True), ("Match Day (HJK)", True), ("Randers GAME", True),
    ("MD-1", False), ("MD - 4", False), ("MD+2/MD-1", False), ("Training - Internal Game", False),
    ("STRENGTH", False), ("MD/2 (Speed)", False),
])
def test_e_jogo(tipo, jogo):
    assert gs.e_jogo(tipo) is jogo


def test_dia_md_da_folha():
    assert gs.dia_md_da_folha("MD + 1") == "MD+1"
    assert gs.dia_md_da_folha("MD-4 Strength") == "MD-4"
    assert gs.dia_md_da_folha("STRENGTH") is None


def test_link_da_folha():
    sid = "1wTW75RfER1q0f7Zv6FZcwcC7oUAvOmPITS7SWQMaj6k"
    assert gs.extrair_spreadsheet_id(f"https://docs.google.com/spreadsheets/d/{sid}/edit?gid=0") == sid
    assert gs.extrair_spreadsheet_id(sid) == sid
    with pytest.raises(gs.ErroGoogleSheets):
        gs.extrair_spreadsheet_id("https://example.com")


def test_sem_cabecalho():
    with pytest.raises(gs.ErroGoogleSheets):
        gs.ler_tabela([["a", "b"], ["1", "2"]])
