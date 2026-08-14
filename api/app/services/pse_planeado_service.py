"""PSE esperada vs real — permite planear a intensidade (PSE) de cada dia do
microciclo antes do treino, e comparar depois com a PSE média realmente
registada, cruzando com a monotonia de cada jogador nessa semana.
"""
from utils.calculos import DIAS_MD_ORDEM, calcular_monotonia_strain

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa


def guardar_pse_planeada(team_id: str, microciclo: int, dia_md: str, pse_esperada: float) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into pse_planeado (team_id, microciclo_nr, dia_md, pse_esperada)
                values (%s, %s, %s, %s)
                on conflict (team_id, microciclo_nr, dia_md)
                do update set pse_esperada = excluded.pse_esperada, atualizado_em = now()
                returning microciclo_nr, dia_md, pse_esperada
                """,
                (team_id, microciclo, dia_md, pse_esperada),
            )
            row = cur.fetchone()
    return {"microciclo": row[0], "dia_md": row[1], "pse_esperada": float(row[2])}


def obter_pse_semana(team_id: str, microciclo: int | None) -> dict:
    df = carregar_df_equipa(team_id)
    if df.empty or "Microciclo (Nr)" not in df.columns or not df["Microciclo (Nr)"].notna().any():
        return {"tem_dados": False, "microciclo": None, "microciclos_disponiveis": [], "dias": [], "monotonia_jogadores": []}

    microciclos_disponiveis = sorted(df["Microciclo (Nr)"].dropna().astype(int).unique().tolist())
    mc = microciclo if (microciclo is not None and microciclo in microciclos_disponiveis) else microciclos_disponiveis[-1]
    df_semana = df[df["Microciclo (Nr)"] == mc]

    # Mostra sempre a semana completa (MD-5 a MD+2), não só os dias que já
    # têm sessões registadas — o preparador físico precisa de conseguir
    # planear a PSE esperada de um dia (ex: MD-5, em microciclos mais
    # longos) ANTES de esse dia acontecer, não só depois.
    dias_presentes = list(DIAS_MD_ORDEM)

    pse_real = {}
    if "PSE Sessão" in df_semana.columns and "Dia MD" in df_semana.columns:
        media = df_semana.dropna(subset=["PSE Sessão", "Dia MD"]).groupby("Dia MD")["PSE Sessão"].mean()
        pse_real = {d: round(float(media[d]), 1) for d in dias_presentes if d in media.index}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select dia_md, pse_esperada from pse_planeado where team_id = %s and microciclo_nr = %s",
                (team_id, mc),
            )
            pse_planeada = {row[0]: float(row[1]) for row in cur.fetchall()}

    dias = [
        {"dia_md": d, "pse_esperada": pse_planeada.get(d), "pse_real": pse_real.get(d)}
        for d in dias_presentes
    ]

    monotonia_jogadores = []
    mono = calcular_monotonia_strain(df_semana)
    if not mono.empty:
        monotonia_jogadores = [
            {"jogador": row["Jogador"], "monotonia": float(row["Monotonia"])}
            for _, row in mono.sort_values("Monotonia", ascending=False).iterrows()
        ]

    return {
        "tem_dados": True,
        "microciclo": mc,
        "microciclos_disponiveis": microciclos_disponiveis,
        "dias": dias,
        "monotonia_jogadores": monotonia_jogadores,
    }
