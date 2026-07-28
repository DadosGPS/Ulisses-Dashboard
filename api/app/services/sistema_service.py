"""Sistema — Fase 8 do plano de migração (validação de dados + histórico de uploads).

Porta o relatório de validação de app_pages/sistema.py, e acrescenta o
histórico de uploads (tabela `uploads`, criada na Fase 4 — não existia
na app Streamlit, onde os ficheiros nunca ficavam guardados).
"""
import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa

COLUNAS_VALIDAR = [
    "Carga Interna", "Distância Total (m)", "HSR (m)", "Sprint (m)",
    "Vel. Máx (km/h)", "Hooper Index", "Dia MD", "Posição",
]


def obter_sistema(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)

    validacao = {"tem_dados": False}
    if not df.empty:
        total = len(df)
        colunas_relatorio = []
        for col in COLUNAS_VALIDAR:
            if col not in df.columns:
                continue
            preenchidas = int(df[col].notna().sum())
            colunas_relatorio.append({
                "coluna": col,
                "preenchidas": preenchidas,
                "total": total,
                "pct": round(preenchidas / total * 100, 0) if total else 0,
            })

        validacao = {
            "tem_dados": True,
            "total_sessoes": total,
            "total_jogadores": int(df["Jogador"].nunique()) if "Jogador" in df.columns else 0,
            "data_inicio": df["Data"].min().date().isoformat() if "Data" in df.columns and df["Data"].notna().any() else None,
            "data_fim": df["Data"].max().date().isoformat() if "Data" in df.columns and df["Data"].notna().any() else None,
            "microciclos": int(df["Microciclo (Nr)"].nunique()) if "Microciclo (Nr)" in df.columns else 0,
            "colunas": colunas_relatorio,
        }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select filename, status, row_count, error, criado_em
                from uploads
                where team_id = %s
                order by criado_em desc
                limit 15
                """,
                (team_id,),
            )
            uploads = [
                {
                    "filename": row[0],
                    "status": row[1],
                    "row_count": row[2],
                    "error": row[3],
                    "criado_em": row[4].isoformat() if row[4] else None,
                }
                for row in cur.fetchall()
            ]

    return {"validacao": validacao, "uploads": uploads}
