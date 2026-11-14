"""Exportação CSV do STATSports Sonra → formato da app.

O Sonra exporta um CSV por sessão com dezenas de colunas (o modelo de
exportação é escolhido no Sonra). Este módulo reconhece esse ficheiro e
converte-o, antes do mapeamento de colunas da importação, para:

- as colunas canónicas da app (Jogador, Data, Tipo, Dia MD, Distância Total,
  HSR, Sprint, Acc, Dcc, Vel. Máx, Duração);
- métricas extra com nomes fixos em português — zonas de velocidade RELATIVAS
  (à Vmáx de cada jogador), acelerações/desacelerações por zona, máximos —,
  que alimentam o Perfil individual.

Decisões (verificadas no export de exemplo publicado pela STATSports,
github.com/statsports/Custom-Data-Handling):

- Uma linha por jogador e sessão: com exercícios («Show Individual Drills»)
  fica só a linha «Full Session» — a sessão completa NÃO é a soma dos
  exercícios (há tempo fora deles). Sem essa linha, somam-se os exercícios.
- Velocidades e acelerações vêm em m/s e m/s²; a app guarda km/h.
- O «Sprint Distance» do Sonra usa o limiar de sprint do perfil do jogador
  (por omissão 5,5 m/s = 19,8 km/h, o mesmo do HSR). O Sprint da app é
  > 25,2 km/h, que no Sonra é a zona 6 absoluta (> 7 m/s) — é essa que entra
  como «Sprint (m)». O sprint do Sonra fica como extra.
- A data vem no formato regional do computador (1/9/2020 pode ser 1 de
  setembro ou 9 de janeiro); desempata-se com «Session Day of Week».
- A posição do Sonra (DEF/MID/FWD) não entra: substituiria a posição mais
  precisa que a equipa definiu na app.
"""
from __future__ import annotations

import re

import pandas as pd

# Colunas que, juntas, identificam um export do Sonra.
_ASSINATURA = ({"Player Name", "Player Display Name"}, {"Session Date", "Drill Date"},
               {"Total Distance"}, {"High Speed Running (Absolute)", "Max Speed", "Sprint Distance"})
_NOMES_SESSAO_COMPLETA = ("full session", "session total", "total session", "sessão completa")

ZONAS = range(1, 7)

# Métricas extra (nomes estáveis: o Perfil individual lê-os).
EXTRA_VMAX_JOGADOR = "Vmáx do jogador (km/h)"
EXTRA_PCT_VMAX = "% Vmáx atingida"
EXTRA_HSR_REL = "HSR relativo (m)"
EXTRA_SPRINT_SONRA = "Sprint Sonra (m)"
EXTRA_SPRINTS_SONRA = "Sprints Sonra (n)"
EXTRA_LIMIAR_SPRINT = "Limiar de sprint Sonra (km/h)"
EXTRA_ACC_MAX = "Acc máx (m/s²)"
EXTRA_DCC_MAX = "Dcc máx (m/s²)"
EXTRA_HMLD = "HMLD (m)"


def extra_dist_rel(z: int) -> str:
    return f"Dist. Z{z} relativa (m)"


def extra_entradas_rel(z: int) -> str:
    return f"Entradas Z{z} relativa (n)"


def extra_acc(z: int) -> str:
    return f"Acc Z{z} (n)"


def extra_dcc(z: int) -> str:
    return f"Dcc Z{z} (n)"


def nomes_extra() -> set[str]:
    """Todas as métricas extra que o Sonra pode trazer (para a importação as
    reconhecer como suas e não como colunas desconhecidas)."""
    fixos = {EXTRA_VMAX_JOGADOR, EXTRA_PCT_VMAX, EXTRA_HSR_REL, EXTRA_SPRINT_SONRA, EXTRA_SPRINTS_SONRA,
             EXTRA_LIMIAR_SPRINT, EXTRA_ACC_MAX, EXTRA_DCC_MAX, EXTRA_HMLD}
    return fixos | {f(z) for z in ZONAS for f in (extra_dist_rel, extra_entradas_rel, extra_acc, extra_dcc)}


def e_sonra(colunas) -> bool:
    cols = {str(c).strip() for c in colunas}
    return all(cols & grupo for grupo in _ASSINATURA)


def _col(df: pd.DataFrame, *nomes: str) -> pd.Series | None:
    for n in nomes:
        if n in df.columns:
            return pd.to_numeric(df[n], errors="coerce")
    return None


def _minutos(serie: pd.Series) -> pd.Series:
    """«1:03:49» / «63:49» / número de minutos → minutos (float)."""
    def conv(v):
        if pd.isna(v):
            return None
        if isinstance(v, (int, float)):
            return float(v)
        partes = str(v).strip().split(":")
        try:
            nums = [float(p) for p in partes]
        except ValueError:
            return None
        if len(nums) == 3:
            return nums[0] * 60 + nums[1] + nums[2] / 60
        if len(nums) == 2:
            return nums[0] + nums[1] / 60
        return nums[0]
    return serie.map(conv).astype(float)


_DIAS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
         "segunda-feira": 0, "terça-feira": 1, "quarta-feira": 2, "quinta-feira": 3, "sexta-feira": 4, "sábado": 5, "domingo": 6,
         "måndag": 0, "tisdag": 1, "onsdag": 2, "torsdag": 3, "fredag": 4, "lördag": 5, "söndag": 6}


def _datas(datas: pd.Series, dia_semana: pd.Series | None) -> pd.Series:
    """Converte as datas desempatando dia/mês pelo dia da semana (se houver).
    Sem dia da semana, assume dia primeiro (formato europeu)."""
    def conv(v, dsem):
        if pd.isna(v):
            return pd.NaT
        texto = str(v).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", texto):
            return pd.to_datetime(texto, errors="coerce")
        dia_pri = pd.to_datetime(texto, errors="coerce", dayfirst=True)
        mes_pri = pd.to_datetime(texto, errors="coerce", dayfirst=False)
        alvo = _DIAS.get(str(dsem).strip().lower()) if dsem is not None and not pd.isna(dsem) else None
        if alvo is not None:
            for d in (dia_pri, mes_pri):
                if pd.notna(d) and d.weekday() == alvo:
                    return d
        return dia_pri if pd.notna(dia_pri) else mes_pri
    sem = dia_semana if dia_semana is not None else pd.Series([None] * len(datas), index=datas.index)
    return pd.Series([conv(v, s) for v, s in zip(datas, sem)], index=datas.index)


def _dia_md(tipo, titulo) -> str | None:
    """«Match Day -2» / «MD-2 (11 v 11)» / «Match Day» → «MD-2» / «MD»."""
    for texto in (tipo, titulo):
        if texto is None or pd.isna(texto):
            continue
        t = str(texto)
        m = re.search(r"match\s*day\s*([+-]\s*\d+)?", t, re.I) or re.search(r"\bMD\s*([+-]\s*\d+)?\b", t)
        if m:
            return "MD" + (m.group(1).replace(" ", "") if m.group(1) else "")
    return None


def _tipo(dia_md: str | None, tipo, titulo) -> str | None:
    texto = " ".join(str(x) for x in (tipo, titulo) if x is not None and not pd.isna(x)).lower()
    if dia_md == "MD" or re.search(r"\b(match|game|jogo|matcher?|friendly)\b", texto) and not re.search(r"[+-]\s*\d", texto):
        return "Jogo"
    if dia_md or "train" in texto or "trän" in texto or "treino" in texto:
        return "Treino"
    return None


def _velocidade_kmh(serie: pd.Series | None) -> pd.Series | None:
    """m/s → km/h. Se a coluna já parecer estar em km/h (mediana > 15), fica."""
    if serie is None:
        return None
    validos = serie.dropna()
    if not validos.empty and float(validos.median()) > 15:
        return serie
    return serie * 3.6


def converter(raw: pd.DataFrame) -> pd.DataFrame:
    """Export do Sonra → colunas da app + extras. Assume e_sonra(raw)."""
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Uma linha por jogador e sessão.
    if "Drill Title" in df.columns:
        titulo = df["Drill Title"].astype(str).str.strip().str.lower()
        completa = titulo.isin(_NOMES_SESSAO_COMPLETA)
        if completa.any():
            df = df[completa]
        else:
            df = _somar_exercicios(df)
    df = df.reset_index(drop=True)

    jogador = df["Player Name"] if "Player Name" in df.columns else df["Player Display Name"]
    col_data = "Session Date" if "Session Date" in df.columns else "Drill Date"
    out = pd.DataFrame({
        "Jogador": jogador.astype(str).str.strip(),
        "Data": _datas(df[col_data], df.get("Session Day of Week")),
    })

    tipo_sessao = df.get("Session Type", pd.Series([None] * len(df)))
    titulo_sessao = df.get("Session Title", pd.Series([None] * len(df)))
    out["Dia MD"] = [_dia_md(t, s) for t, s in zip(tipo_sessao, titulo_sessao)]
    out["Tipo"] = [_tipo(d, t, s) for d, t, s in zip(out["Dia MD"], tipo_sessao, titulo_sessao)]

    def pôr(nome, serie):
        if serie is not None:
            out[nome] = serie.values

    pôr("Distância Total (m)", _col(df, "Total Distance"))
    pôr("HSR (m)", _col(df, "High Speed Running (Absolute)", "High Speed Running"))
    pôr("Sprint (m)", _col(df, "Distance Zone 6 (Absolute)"))
    pôr("Acc (n)", _col(df, "Accelerations"))
    pôr("Dcc (n)", _col(df, "Decelerations"))
    vmax = _velocidade_kmh(_col(df, "Max Speed"))
    pôr("Vel. Máx (km/h)", vmax.round(2) if vmax is not None else None)
    if "Total Time" in df.columns:
        out["Duração (min)"] = _minutos(df["Total Time"]).round(1).values

    # Extras — individualização.
    vmax_jog = _velocidade_kmh(_col(df, "Player Max Speed"))
    if vmax_jog is not None:
        out[EXTRA_VMAX_JOGADOR] = vmax_jog.round(2).values
        if vmax is not None:
            out[EXTRA_PCT_VMAX] = (vmax / vmax_jog.where(vmax_jog > 0) * 100).round(1).values
    pôr(EXTRA_HSR_REL, _col(df, "High Speed Running (Relative)"))
    pôr(EXTRA_SPRINT_SONRA, _col(df, "Sprint Distance"))
    pôr(EXTRA_SPRINTS_SONRA, _col(df, "Sprints"))
    limiar = _velocidade_kmh(_col(df, "Player Sprint Threshold"))
    pôr(EXTRA_LIMIAR_SPRINT, limiar.round(2) if limiar is not None else None)
    for z in ZONAS:
        pôr(extra_dist_rel(z), _col(df, f"Distance Zone {z} (Relative)"))
        pôr(extra_entradas_rel(z), _col(df, f"Entries Zone {z} (Relative)"))
        pôr(extra_acc(z), _col(df, f"Accelerations Zone {z}"))
        pôr(extra_dcc(z), _col(df, f"Decelerations Zone {z}"))
    pôr(EXTRA_ACC_MAX, _col(df, "Max Acceleration"))
    dcc_max = _col(df, "Max Deceleration")
    pôr(EXTRA_DCC_MAX, dcc_max.abs() if dcc_max is not None else None)
    pôr(EXTRA_HMLD, _col(df, "HML Distance"))

    # Colunas sem nenhum valor (métrica não incluída no modelo de exportação) saem.
    return out.dropna(axis=1, how="all")


# Ao somar exercícios: métricas de pico/rácio ficam com o máximo, o resto soma.
_PICO = re.compile(r"max|threshold|per min|average|intensity|ratio|acute|chronic|index|balance|satellites|quality|%", re.I)
_TEMPO = re.compile(r"\btime\b", re.I)


def _somar_exercicios(df: pd.DataFrame) -> pd.DataFrame:
    jog = "Player Name" if "Player Name" in df.columns else "Player Display Name"
    data = "Session Date" if "Session Date" in df.columns else "Drill Date"
    chave = [c for c in (jog, data) if c in df.columns]
    texto = [c for c in df.columns if c not in chave and not pd.api.types.is_numeric_dtype(df[c]) and not _TEMPO.search(c)]
    agg: dict[str, str] = {c: "first" for c in texto}
    for c in df.columns:
        if c in chave or c in agg:
            continue
        if _TEMPO.search(c):
            continue
        agg[c] = "max" if _PICO.search(c) else "sum"
    soma = df.groupby(chave, sort=False).agg(agg).reset_index()
    if "Total Time" in df.columns:
        soma["Total Time"] = _minutos(df["Total Time"]).groupby([df[c] for c in chave], sort=False).sum().values
    return soma
