"""Perfil do jogador a partir dos testes neuromusculares, com STEN scores.

Converte cada teste num STEN (1–10) para pôr tudo na mesma escala e ser
legível de imediato pelo staff. STEN = 5.5 + 2·z, limitado a [1, 10], com o
z-score calculado VS A POSIÇÃO do jogador (fallback ao plantel quando a
posição tem poucos jogadores). Métricas onde "menos é melhor" (tempo de
contacto, assimetria) têm o z invertido, para STEN alto = sempre melhor.
"""
import math

import pandas as pd

from app.core.db import get_conn

# maior_melhor=False → menos é melhor (inverte o z para STEN alto = melhor).
METRICAS_TESTE = [
    {"chave": "altura_salto_cm", "col": "altura_salto_cm", "label": "Altura de Salto", "unidade": "cm", "grupo": "Potência", "maior_melhor": True, "casas": 1},
    {"chave": "potencia_rel_wkg", "col": "potencia_rel_wkg", "label": "Potência Rel.", "unidade": "W/kg", "grupo": "Potência", "maior_melhor": True, "casas": 1},
    {"chave": "rfd", "col": "rfd", "label": "RFD (força explosiva)", "unidade": "N/s", "grupo": "Força", "maior_melhor": True, "casas": 0},
    {"chave": "rsi", "col": "rsi", "label": "RSI (reatividade)", "unidade": "", "grupo": "Reatividade", "maior_melhor": True, "casas": 2},
    {"chave": "tempo_contacto_ms", "col": "tempo_contacto_ms", "label": "T. Contacto", "unidade": "ms", "grupo": "Reatividade", "maior_melhor": False, "casas": 0},
    {"chave": "assimetria_pct", "col": "assimetria_pct", "label": "Assimetria", "unidade": "%", "grupo": "Equilíbrio", "maior_melhor": False, "casas": 1},
]
_MIN_POSICAO = 3  # nº mínimo de jogadores na posição para usar a posição como referência


def _sten(valor: float, media: float, desvio: float, maior_melhor: bool) -> int | None:
    if desvio is None or desvio == 0 or media is None:
        return None
    z = (valor - media) / desvio
    if not maior_melhor:
        z = -z
    return int(max(1, min(10, round(5.5 + 2 * z))))


def obter_perfis(team_id: str) -> dict:
    vazio = {"tem_dados": False, "metricas": [], "jogadores": []}
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select p.nome, coalesce(p.posicao, '—') as posicao, t.data,
                           t.altura_salto_cm, t.potencia_rel_wkg, t.rfd, t.rsi,
                           t.tempo_contacto_ms, t.assimetria_pct
                    from testes_neuromusculares t
                    join players p on p.id = t.player_id
                    where t.team_id = %s
                    """,
                    (team_id,),
                )
                rows = cur.fetchall()
    except Exception:
        return vazio

    if not rows:
        return vazio

    cols = ["nome", "posicao", "data", "altura_salto_cm", "potencia_rel_wkg", "rfd", "rsi", "tempo_contacto_ms", "assimetria_pct"]
    df = pd.DataFrame(rows, columns=cols)
    for m in METRICAS_TESTE:
        df[m["col"]] = pd.to_numeric(df[m["col"]], errors="coerce")

    # Teste mais recente por jogador.
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.sort_values("data").groupby("nome", as_index=False).last()

    metricas_presentes = [m for m in METRICAS_TESTE if df[m["col"]].notna().any()]
    if not metricas_presentes:
        return vazio

    # Estatísticas por posição e globais (plantel), por métrica.
    stats_pos: dict[tuple, tuple] = {}
    stats_global: dict[str, tuple] = {}
    contagem_pos = df.groupby("posicao")["nome"].count().to_dict()
    for m in metricas_presentes:
        col = m["col"]
        s = df[col].dropna()
        stats_global[col] = (float(s.mean()), float(s.std(ddof=0))) if len(s) >= 2 else (None, None)
        for pos, g in df.groupby("posicao"):
            sv = g[col].dropna()
            stats_pos[(pos, col)] = (float(sv.mean()), float(sv.std(ddof=0))) if len(sv) >= 2 else (None, None)

    jogadores = []
    for _, row in df.iterrows():
        pos = row["posicao"]
        usa_posicao = contagem_pos.get(pos, 0) >= _MIN_POSICAO
        testes = {}
        stens = []
        for m in metricas_presentes:
            col = m["col"]
            valor = row[col]
            if valor is None or (isinstance(valor, float) and math.isnan(valor)):
                continue
            media, desvio = stats_pos.get((pos, col), (None, None)) if usa_posicao else stats_global.get(col, (None, None))
            if media is None or desvio is None or desvio == 0:
                media, desvio = stats_global.get(col, (None, None))  # fallback ao plantel
            sten = _sten(float(valor), media, desvio, m["maior_melhor"]) if media is not None else None
            testes[m["chave"]] = {"valor": round(float(valor), m["casas"]), "sten": sten}
            if sten is not None:
                stens.append(sten)
        jogadores.append({
            "jogador": row["nome"],
            "posicao": pos,
            "data": row["data"].strftime("%Y-%m-%d") if pd.notna(row["data"]) else None,
            "referencia": "posição" if usa_posicao else "plantel",
            "sten_medio": round(sum(stens) / len(stens), 1) if stens else None,
            "testes": testes,
        })
    jogadores.sort(key=lambda j: (j["sten_medio"] is None, -(j["sten_medio"] or 0)))

    return {
        "tem_dados": True,
        "metricas": [{"chave": m["chave"], "label": m["label"], "unidade": m["unidade"], "grupo": m["grupo"], "maior_melhor": m["maior_melhor"]} for m in metricas_presentes],
        "jogadores": jogadores,
    }
