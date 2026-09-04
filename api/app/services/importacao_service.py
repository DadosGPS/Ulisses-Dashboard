"""Importação robusta — passo de análise (detetar → mapear → validar → prever).

O fluxo antigo lia o ficheiro e gravava logo, às cegas. Aqui, antes de gravar,
o utilizador vê: que colunas foram detetadas, para que nome canónico cada uma
vai, o que ficou por reconhecer, o que falta, avisos, e uma pré-visualização
das primeiras linhas já normalizadas. A gravação só acontece depois, com o
mapeamento confirmado (ver `processar_upload_com_mapa` em ingest_service).
"""
import io

import pandas as pd

from utils.dados import (
    COL_ALIASES,
    auto_mapa,
    carregar_dados_com_mapa,
    ler_raw,
)

# Nomes canónicos que o utilizador pode escolher no menu de cada coluna.
CANONICAS_OBRIGATORIAS = ["Jogador", "Posição", "Tipo", "Dia MD", "Data", "Microciclo (Nr)"]
CANONICAS_METRICAS = [c for c in COL_ALIASES if c != "Microciclo (Nr)"]

# Sem estas não vale a pena importar.
CRITICAS = ["Jogador"]
# Muito recomendadas para a app funcionar bem (não bloqueiam).
RECOMENDADAS = ["Data", "Distância Total (m)", "HSR (m)", "Vel. Máx (km/h)"]

# Ordem preferida das colunas na pré-visualização.
PREVIEW_CONTEXTO = ["Jogador", "Posição", "Data", "Tipo", "Dia MD", "Microciclo (Nr)"]
PREVIEW_METRICAS = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)", "Carga Interna"]


def _tipo_canonico(canon: str) -> str:
    if canon in CANONICAS_OBRIGATORIAS:
        return "obrigatoria"
    if canon in COL_ALIASES:
        return "metrica"
    return "extra"


def _cell(v):
    if pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float):
        return round(v, 2)
    return v


def analisar_ficheiro(filename: str, conteudo: bytes) -> dict:
    """Lê o ficheiro sem gravar nada e devolve o diagnóstico de importação."""
    buffer = io.BytesIO(conteudo)
    buffer.name = filename
    try:
        raw = ler_raw(buffer)
    except Exception:
        return {"ok": False, "erro": "Não foi possível ler o ficheiro. Confirma que é um CSV ou Excel válido (folha 'BD_Carga' no caso de Excel)."}

    if raw is None or raw.empty or not len(raw.columns):
        return {"ok": False, "erro": "O ficheiro não tem colunas/linhas legíveis."}

    colunas_raw = [str(c) for c in raw.columns]
    mapa = auto_mapa(colunas_raw)  # {coluna_crua: nome_canónico}

    colunas = [
        {
            "raw": c,
            "canonica": mapa.get(c),
            "auto": c in mapa,
            "tipo": _tipo_canonico(mapa[c]) if c in mapa else "extra",
            "exemplos": _exemplos(raw[c]),
        }
        for c in colunas_raw
    ]

    canonicas_presentes = set(mapa.values())
    em_falta = {
        "criticas": [c for c in CRITICAS if c not in canonicas_presentes],
        "recomendadas": [c for c in RECOMENDADAS if c not in canonicas_presentes],
    }

    # Normalização de facto, para pré-visualização + resumo + avisos.
    buffer2 = io.BytesIO(conteudo)
    buffer2.name = filename
    try:
        norm = carregar_dados_com_mapa(buffer2, mapa)
    except Exception:
        norm = pd.DataFrame()

    resumo, preview = _resumo_e_preview(norm)
    avisos = _avisos(mapa, canonicas_presentes, raw, norm, em_falta)

    return {
        "ok": True,
        "ficheiro": filename,
        "n_linhas": int(len(raw)),
        "n_colunas": int(len(colunas_raw)),
        "colunas": colunas,
        "mapa_sugerido": mapa,
        "opcoes_canonicas": {
            "obrigatorias": CANONICAS_OBRIGATORIAS,
            "metricas": CANONICAS_METRICAS,
        },
        "em_falta": em_falta,
        "avisos": avisos,
        "resumo": resumo,
        "preview": preview,
        "pode_importar": not em_falta["criticas"] and not norm.empty,
    }


def _exemplos(serie: pd.Series, n: int = 3) -> list:
    vals = [v for v in serie.dropna().tolist()[:n]]
    return [_cell(v) for v in vals]


def _resumo_e_preview(norm: pd.DataFrame):
    if norm is None or norm.empty:
        return {"jogadores": 0, "sessoes": 0, "intervalo_datas": None}, {"colunas": [], "linhas": []}

    jogadores = int(norm["Jogador"].nunique()) if "Jogador" in norm.columns else 0
    sessoes = int(len(norm))
    intervalo = None
    if "Data" in norm.columns and norm["Data"].notna().any():
        dmin, dmax = norm["Data"].min(), norm["Data"].max()
        intervalo = [_cell(dmin), _cell(dmax)]
    resumo = {"jogadores": jogadores, "sessoes": sessoes, "intervalo_datas": intervalo}

    cols_ctx = [c for c in PREVIEW_CONTEXTO if c in norm.columns]
    cols_met = [c for c in PREVIEW_METRICAS if c in norm.columns]
    # Se sobrarem métricas mapeadas fora da lista preferida, mostra algumas.
    outras = [c for c in norm.columns if c not in cols_ctx and c not in cols_met][:3]
    cols = cols_ctx + cols_met + outras
    head = norm.head(8)
    linhas = [[_cell(head.iloc[i][c]) for c in cols] for i in range(len(head))]
    return resumo, {"colunas": cols, "linhas": linhas}


def _avisos(mapa: dict, presentes: set, raw: pd.DataFrame, norm: pd.DataFrame, em_falta: dict) -> list:
    avisos: list[dict] = []

    if em_falta["criticas"]:
        avisos.append({
            "nivel": "erro",
            "texto": "Falta a coluna do nome do jogador. Escolhe qual das colunas corresponde a «Jogador» — sem isso não é possível importar.",
        })

    if "Data" not in presentes and "Microciclo (Nr)" not in presentes:
        avisos.append({
            "nivel": "aviso",
            "texto": "Sem coluna de data nem de microciclo, a ordem cronológica das sessões pode ficar incorreta (afeta ACWR e evoluções).",
        })
    elif "Data" not in presentes and "Microciclo (Nr)" in presentes:
        avisos.append({
            "nivel": "info",
            "texto": "Sem data de calendário: a ordem das sessões será inferida a partir do microciclo.",
        })

    metricas_mapeadas = [c for c in presentes if c in COL_ALIASES and c != "Microciclo (Nr)"]
    if not metricas_mapeadas:
        avisos.append({
            "nivel": "aviso",
            "texto": "Nenhuma métrica de carga externa foi reconhecida (distância, HSR, sprint, velocidade máxima…). Verifica o mapeamento.",
        })

    # Carga interna derivada?
    if norm is not None and not norm.empty and "Carga Interna" in norm.columns and "Carga Interna" not in presentes:
        avisos.append({
            "nivel": "info",
            "texto": "«Carga Interna» não existia no ficheiro — foi calculada a partir de PSE × Duração.",
        })

    # Linhas que serão descartadas (sem jogador ou sem data após normalização).
    if norm is not None and not norm.empty:
        n_raw = len(raw)
        n_norm = len(norm)
        if n_norm < n_raw:
            avisos.append({
                "nivel": "info",
                "texto": f"{n_raw - n_norm} de {n_raw} linhas serão ignoradas por não terem nome de jogador ou dados válidos.",
            })

    nao_reconhecidas = [str(c) for c in raw.columns if str(c) not in mapa]
    if nao_reconhecidas:
        amostra = ", ".join(nao_reconhecidas[:6]) + ("…" if len(nao_reconhecidas) > 6 else "")
        avisos.append({
            "nivel": "info",
            "texto": f"{len(nao_reconhecidas)} coluna(s) não reconhecida(s) ({amostra}). Serão guardadas como métricas extra ou podes mapeá-las manualmente.",
        })

    return avisos
