"""Carga externa planeada vs real — planear distância/HSR/sprint por dia do
microciclo e comparar com a média real registada nos uploads.

Espelha pse_planeado_service, mas para a carga externa.
"""
from utils.calculos import DIAS_MD_ORDEM

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa

# Métricas planeáveis (coluna canónica → chave da tabela/JSON).
_METRICAS = [
    ("Distância Total (m)", "distancia_m"),
    ("HSR (m)", "hsr_m"),
    ("Sprint (m)", "sprint_m"),
]


def guardar_carga_planeada(team_id: str, microciclo: int, dia_md: str,
                           distancia_m: float | None, hsr_m: float | None, sprint_m: float | None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into carga_externa_planeada (team_id, microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (team_id, microciclo_nr, dia_md)
                do update set distancia_m = excluded.distancia_m, hsr_m = excluded.hsr_m,
                              sprint_m = excluded.sprint_m, atualizado_em = now()
                returning microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m
                """,
                (team_id, microciclo, dia_md, distancia_m, hsr_m, sprint_m),
            )
            row = cur.fetchone()
    return {
        "microciclo": row[0], "dia_md": row[1],
        "distancia_m": float(row[2]) if row[2] is not None else None,
        "hsr_m": float(row[3]) if row[3] is not None else None,
        "sprint_m": float(row[4]) if row[4] is not None else None,
    }


def obter_carga_planeada_semana(team_id: str, microciclo: int | None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Microciclo (Nr)" not in df.columns or not df["Microciclo (Nr)"].notna().any():
        return {"tem_dados": False, "microciclo": None, "microciclos_disponiveis": [], "dias": []}

    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist())
    mc = microciclo if (microciclo is not None and microciclo in microciclos_disponiveis) else microciclos_disponiveis[-1]
    df_semana = df[df["Microciclo (Nr)"] == mc]

    dias_presentes = list(DIAS_MD_ORDEM)

    # Real: média por sessão (só treinos) por dia — comparável a um alvo por dia.
    treinos = df_semana[df_semana["Tipo"] != "Jogo"] if "Tipo" in df_semana.columns else df_semana
    real: dict[str, dict] = {}
    if "Dia MD" in treinos.columns:
        for col, chave in _METRICAS:
            if col in treinos.columns:
                media = treinos.dropna(subset=[col, "Dia MD"]).groupby("Dia MD")[col].mean()
                for d in dias_presentes:
                    if d in media.index:
                        real.setdefault(d, {})[chave] = round(float(media[d]), 0)

    # Planeado: da tabela. Resiliente a a migração ainda não ter sido aplicada
    # (nesse caso mostra só o real, sem planeado, em vez de falhar).
    planeado: dict[str, dict] = {}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select dia_md, distancia_m, hsr_m, sprint_m from carga_externa_planeada where team_id = %s and microciclo_nr = %s",
                    (team_id, mc),
                )
                planeado = {
                    r[0]: {
                        "distancia_m": float(r[1]) if r[1] is not None else None,
                        "hsr_m": float(r[2]) if r[2] is not None else None,
                        "sprint_m": float(r[3]) if r[3] is not None else None,
                    }
                    for r in cur.fetchall()
                }
    except Exception:
        planeado = {}

    dias = [
        {
            "dia_md": d,
            "planeado": planeado.get(d, {"distancia_m": None, "hsr_m": None, "sprint_m": None}),
            "real": {
                "distancia_m": real.get(d, {}).get("distancia_m"),
                "hsr_m": real.get(d, {}).get("hsr_m"),
                "sprint_m": real.get(d, {}).get("sprint_m"),
            },
        }
        for d in dias_presentes
    ]

    return {
        "tem_dados": True,
        "microciclo": mc,
        "microciclos_disponiveis": microciclos_disponiveis,
        "dias": dias,
    }
