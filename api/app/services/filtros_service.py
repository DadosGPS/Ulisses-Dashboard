"""Opções de filtro global — jogadores, microciclos e dias MD disponíveis na
equipa. Alimenta a barra de filtros partilhada de todas as páginas de análise.
"""
from app.services.dados_equipa import carregar_df_equipa

try:
    from utils.calculos import DIAS_MD_ORDEM
except Exception:  # pragma: no cover - fallback defensivo
    DIAS_MD_ORDEM = ["MD-6", "MD-5", "MD-4", "MD-3", "MD-2", "MD-1", "MD", "MD+1", "MD+2"]


def obter_filtros(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty:
        return {"jogadores": [], "microciclos": [], "dias_md": []}

    jogadores = sorted(df["Jogador"].dropna().unique().tolist()) if "Jogador" in df.columns else []
    microciclos = (
        sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist())
        if "Microciclo (Nr)" in df.columns else []
    )
    dias_md = []
    if "Dia MD" in df.columns:
        presentes = set(df["Dia MD"].dropna().unique().tolist())
        dias_md = [d for d in DIAS_MD_ORDEM if d in presentes]

    return {"jogadores": jogadores, "microciclos": microciclos, "dias_md": dias_md}
