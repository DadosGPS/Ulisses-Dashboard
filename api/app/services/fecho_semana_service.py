"""Fecho de semana para o treinador principal — 5 a 7 linhas, prontas a colar
numa mensagem. O treinador não abre quinze páginas: quer saber como correu a
semana, quem está disponível e o que muda na próxima.

Linhas (só as que têm dados):
  1. Semana: treinos e jogos do microciclo;
  2. Carga: carga interna média por jogador vs semana anterior, e monotonia;
  3. Exposição: HSR/Sprint da semana face ao jogo, e quem ficou abaixo;
  4. Disponibilidade: aptos e indisponíveis;
  5. Avisos e decisões: quantos jogadores com avisos e o que foi decidido;
  6. Próxima semana: quem compensar e quem vigiar.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from utils.calculos import calcular_monotonia_strain

MAX_NOMES = 5


def _nomes(lista: list[str]) -> str:
    lista = [str(x) for x in lista]
    if len(lista) <= MAX_NOMES:
        return ", ".join(lista)
    return ", ".join(lista[:MAX_NOMES]) + f" e mais {len(lista) - MAX_NOMES}"


def _pct(a: float, b: float) -> str:
    return f"{(a - b) / b * 100:+.0f}%" if b else "—"


def montar(df: pd.DataFrame, mc: int, exposicao: dict | None, estados: dict[str, str],
           avisos: list[dict], decisoes: list[dict], compensacao: dict | None, em_curso: bool = False) -> list[str]:
    """Parte pura: as linhas do fecho do microciclo `mc`."""
    from app.services.referencia_jogo import mascara_jogo

    linhas: list[str] = []
    sem = df[df["Microciclo (Nr)"] == mc] if "Microciclo (Nr)" in df.columns else df.iloc[0:0]
    if sem.empty:
        return [f"Microciclo {mc}: ainda sem sessões registadas."]
    e_jogo = mascara_jogo(sem)
    datas = pd.to_datetime(sem["Data"])
    n_treinos = int(datas[~e_jogo].dt.normalize().nunique())
    n_jogos = int(datas[e_jogo].dt.normalize().nunique())
    ini, fim = datas.min(), datas.max()
    linhas.append(f"Semana {mc} ({ini:%d/%m}–{fim:%d/%m}{', em curso' if em_curso else ''}): {n_treinos} treino(s) e {n_jogos} jogo(s).")

    if "Carga Interna" in sem.columns and sem["Carga Interna"].notna().any():
        media = float(sem.groupby("Jogador")["Carga Interna"].sum().mean())
        txt = f"Carga interna média por jogador{' até agora' if em_curso else ''}: {media:.0f} UA"
        anteriores = df[df["Microciclo (Nr)"] < mc] if "Microciclo (Nr)" in df.columns else df.iloc[0:0]
        if not em_curso and not anteriores.empty and anteriores["Carga Interna"].notna().any():
            mc_ant = anteriores["Microciclo (Nr)"].max()
            ant = df[df["Microciclo (Nr)"] == mc_ant]
            media_ant = float(ant.groupby("Jogador")["Carga Interna"].sum().mean())
            txt += f" ({_pct(media, media_ant)} vs semana {int(mc_ant)})"
        mono = calcular_monotonia_strain(sem)
        if not mono.empty:
            txt += f"; monotonia média {mono['Monotonia'].mean():.2f}"
        linhas.append(txt + ".")

    if exposicao and exposicao.get("tem_dados"):
        partes, abaixo = [], []
        for m in exposicao["metricas"]:
            partes.append(f"{m['label']} {m['ratio_equipa']:.2f}× (ref. {m['ref'][0]:.2f}–{m['ref'][1]:.2f})")
            abaixo += [j["jogador"] for j in m["jogadores"] if j["zona"] == "baixo"]
        txt = "Exposição da semana vs jogo: " + ", ".join(partes) + "."
        abaixo = sorted(set(abaixo))
        if abaixo:
            txt += f" Abaixo da zona: {_nomes(abaixo)}."
        linhas.append(txt)

    jogadores = sorted(set(sem["Jogador"].dropna()) | set(estados))
    indisp = sorted(n for n, e in estados.items() if e != "apto")
    if jogadores:
        txt = f"Disponibilidade: {len([j for j in jogadores if estados.get(j, 'apto') == 'apto'])} de {len(jogadores)} aptos"
        if indisp:
            rot = {"lesionado": "lesionado", "em_recuperacao": "em recuperação", "ausente": "ausente"}
            txt += " — fora: " + _nomes([f"{n} ({rot.get(estados[n], estados[n])})" for n in indisp])
        linhas.append(txt + ".")

    com_aviso = [a for a in avisos if a.get("status") != "normal"]
    if com_aviso or decisoes:
        txt = f"Avisos: {len(com_aviso)} jogador(es) com avisos."
        if decisoes:
            cont = pd.Series([d["decisao"] for d in decisoes]).value_counts()
            nomes = {"reduzir": "reduzir carga", "ajustar": "ajustar plano", "manter": "manter", "ignorar": "ignorar"}
            txt += f" Decisões registadas: {len(decisoes)} (" + ", ".join(f"{nomes.get(k, k)} {v}" for k, v in cont.items()) + ")."
        linhas.append(txt)

    proxima = []
    if compensacao and compensacao.get("jogadores"):
        proxima.append(f"compensar {_nomes([j['jogador'] for j in compensacao['jogadores']])} (menos de {compensacao['minimo_pct']:.0f}% dos minutos no último jogo)")
    vigiar = [a["player_name"] for a in com_aviso if a.get("status") == "high-attention"]
    if vigiar:
        proxima.append(f"vigiar {_nomes(vigiar)} (mais do que um aviso)")
    if proxima:
        linhas.append("Próxima semana: " + "; ".join(proxima) + ".")
    return linhas


def obter(team_id: str, user_id: str, microciclo: int | None = None) -> dict:
    from app.routers.dashboard import _build_alerts
    from app.services import decisoes_service, semana_jogadores_service
    from app.services.alertas_service import obter_exposicao_semana
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.estado_service import listar_estados
    from app.services.limites_service import obter_limites_equipa

    df = carregar_df_equipa(team_id)
    if df.empty or "Microciclo (Nr)" not in df.columns or not df["Microciclo (Nr)"].notna().any():
        return {"microciclo": None, "linhas": [], "texto": "", "motivo": "Ainda não há microciclos com dados."}
    df["Data"] = pd.to_datetime(df["Data"])
    disponiveis = sorted({int(m) for m in df["Microciclo (Nr)"].dropna()})
    mc = microciclo if microciclo in disponiveis else disponiveis[-1]
    lim = obter_limites_equipa(team_id, user_id)
    estados = {e["nome"]: e["estado"] for e in listar_estados(team_id) if e.get("ativo", True)}
    sem = df[df["Microciclo (Nr)"] == mc]
    ini, fim = sem["Data"].min().date(), sem["Data"].max().date()

    decisoes: list[dict] = []
    if decisoes_service.disponivel():
        try:
            decisoes = [d for d in decisoes_service.listar(team_id, ini.isoformat())["decisoes"] if d["data"] <= fim.isoformat()]
        except Exception:
            decisoes = []
    try:
        comp = semana_jogadores_service.obter(team_id, min(fim, date.today()), mc)["compensacao"]
    except Exception:
        comp = None
    try:
        avisos = _build_alerts(team_id, lim)
    except Exception:
        avisos = []
    from app.services.alertas_service import progresso_microciclo
    from app.services.referencia_jogo import mascara_jogo
    em_curso = not progresso_microciclo(df, mascara_jogo(df), mc).get("completo", True)
    linhas = montar(df, mc, obter_exposicao_semana(df, lim, mc), estados, avisos, decisoes, comp, em_curso=em_curso)
    return {"microciclo": mc, "microciclos": disponiveis, "linhas": linhas, "texto": "\n".join(linhas), "motivo": None}
