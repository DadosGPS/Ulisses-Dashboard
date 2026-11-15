"""Verificação de dados — corre em cada importação, ANTES de gravar.

Três níveis:
  · erro  → valor impossível (negativo, HSR maior do que a distância, 60 km/h…).
            Bloqueia a importação: os números a jusante (ACWR, exposição,
            referências de jogo) ficariam errados sem ninguém dar por isso.
            O PF corrige a origem, ou importa sem essas linhas (explicitamente);
  · aviso → plausível mas suspeito (pico de GPS, sessão sem dados de GPS,
            nome quase igual a um jogador já existente…). Grava, mas fica listado;
  · info  → contexto útil (períodos detetados, jogos sem minutos…).

Depois de gravar, a importação ainda reconta o que ficou na base de dados e
compara com o ficheiro (ver recontar) — se não bater certo, desfaz tudo.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from datetime import date, timedelta

import pandas as pd

from app.services import periodos as per

logger = logging.getLogger(__name__)

ERRO, AVISO, INFO = "erro", "aviso", "info"

# (mínimo de erro, máximo de aviso, máximo de erro) — por linha (um jogador num período/sessão).
VEL_AVISO, VEL_ERRO = 36.0, 45.0
DIST_AVISO, DIST_ERRO = 16000.0, 30000.0
DURACAO_ERRO = 300.0

METRICAS_NAO_NEGATIVAS = [
    "Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)", "Vel. Máx (km/h)",
    "Duração (min)", "PSE Sessão", "Carga Interna",
]
WELLNESS = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)"]
GPS = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)"]
N_EXEMPLOS = 4


def _sem_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _chave_nome(nome) -> str:
    return " ".join(str(nome).split()).lower()


def _data_txt(v) -> str | None:
    if v is None or pd.isna(v):
        return None
    try:
        return pd.Timestamp(v).date().isoformat()
    except Exception:
        return str(v)


def _exemplos(df: pd.DataFrame, idx, col: str | None = None) -> list[dict]:
    out = []
    for i in list(idx)[:N_EXEMPLOS]:
        r = df.loc[i]
        ex = {"linha": int(i) + 2, "jogador": str(r.get("Jogador", "—")), "data": _data_txt(r.get("Data"))}
        if per.COL in df.columns and not per.vazio(r.get(per.COL)):
            ex["periodo"] = str(r.get(per.COL))
        if col is not None:
            v = r.get(col)
            ex["valor"] = None if v is None or pd.isna(v) else round(float(v), 1)
        out.append(ex)
    return out


def _txt_exemplos(ex: list[dict], n_total: int) -> str:
    partes = [f"{e['jogador']}{' em ' + e['data'] if e.get('data') else ''}{' (' + str(e['valor']) + ')' if e.get('valor') is not None else ''}" for e in ex]
    return "; ".join(partes) + ("…" if n_total > len(ex) else "")


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(float("nan"), index=df.index)


def verificar_df(df: pd.DataFrame, jogadores_existentes: list[str] | None = None, hoje: date | None = None) -> dict:
    """Verifica um DataFrame já normalizado (nomes canónicos). Puro: sem BD.

    Devolve {"problemas": [...], "resumo": {...}, "linhas_erro": [índices]}.
    Cada problema: {codigo, nivel, texto, n, exemplos: [{linha, jogador, data, valor}]}."""
    hoje = hoje or date.today()
    problemas: list[dict] = []
    linhas_erro: set = set()
    if df is None or df.empty or "Jogador" not in df.columns:
        return {"problemas": [], "resumo": resumo([], df), "linhas_erro": []}

    def junta(codigo: str, nivel: str, mascara: pd.Series, texto: str, col: str | None = None):
        idx = df.index[mascara.fillna(False).astype(bool)]
        if not len(idx):
            return
        if nivel == ERRO:
            linhas_erro.update(idx)
        ex = _exemplos(df, idx, col)
        problemas.append({"codigo": codigo, "nivel": nivel, "n": int(len(idx)), "exemplos": ex,
                          "texto": texto.format(n=len(idx), ex=_txt_exemplos(ex, len(idx)))})

    # ── Erros: valores impossíveis ──────────────────────────────────────────
    if "Data" in df.columns:
        junta("data_invalida", ERRO, df["Data"].isna(),
              "{n} linha(s) sem data válida: {ex}. Sem data não se sabe a que sessão pertencem.")
    for col in METRICAS_NAO_NEGATIVAS:
        if col in df.columns:
            junta(f"negativo:{col}", ERRO, _num(df, col) < 0, f"{{n}} linha(s) com «{col}» negativo: {{ex}}.", col)
    vel = _num(df, "Vel. Máx (km/h)")
    junta("vel_impossivel", ERRO, vel > VEL_ERRO,
          f"{{n}} linha(s) com velocidade máxima acima de {VEL_ERRO:.0f} km/h: {{ex}}. É um erro do GPS ou de unidades (m/s?).", "Vel. Máx (km/h)")
    dist = _num(df, "Distância Total (m)")
    junta("dist_impossivel", ERRO, dist > DIST_ERRO,
          f"{{n}} linha(s) com mais de {DIST_ERRO:.0f} m numa sessão: {{ex}}. Confirma as unidades do export.", "Distância Total (m)")
    junta("hsr_maior_dist", ERRO, (_num(df, "HSR (m)") > dist + 1) & (dist > 0),
          "{n} linha(s) com HSR maior do que a distância total: {ex}. Colunas trocadas no mapeamento?", "HSR (m)")
    junta("sprint_maior_dist", ERRO, (_num(df, "Sprint (m)") > dist + 1) & (dist > 0),
          "{n} linha(s) com sprint maior do que a distância total: {ex}.", "Sprint (m)")
    junta("duracao_impossivel", ERRO, _num(df, "Duração (min)") > DURACAO_ERRO,
          f"{{n}} linha(s) com mais de {DURACAO_ERRO:.0f} minutos: {{ex}}. A duração está em segundos?", "Duração (min)")
    junta("pse_fora", ERRO, _num(df, "PSE Sessão") > 10, "{n} linha(s) com PSE acima de 10: {ex}.", "PSE Sessão")
    for col in WELLNESS:
        if col in df.columns:
            v = _num(df, col)
            junta(f"wellness_fora:{col}", ERRO, (v < 1) | (v > 5), f"{{n}} linha(s) com «{col}» fora de 1–5: {{ex}}.", col)

    # ── Avisos: plausível mas suspeito ──────────────────────────────────────
    junta("vel_pico", AVISO, (vel > VEL_AVISO) & (vel <= VEL_ERRO),
          f"{{n}} linha(s) com velocidade máxima acima de {VEL_AVISO:.0f} km/h: {{ex}}. Pode ser um pico do GPS — confirma antes de virar recorde.", "Vel. Máx (km/h)")
    junta("dist_alta", AVISO, (dist > DIST_AVISO) & (dist <= DIST_ERRO),
          f"{{n}} linha(s) com mais de {DIST_AVISO:.0f} m: {{ex}}.", "Distância Total (m)")

    gps_cols = [c for c in GPS if c in df.columns]
    if gps_cols and "Duração (min)" in df.columns:
        soma_gps = sum(_num(df, c).fillna(0) for c in gps_cols)
        tem_gps = pd.concat([_num(df, c) for c in gps_cols], axis=1).notna().any(axis=1)
        junta("sem_gps", AVISO, (_num(df, "Duração (min)") > 10) & tem_gps & (soma_gps == 0),
              "{n} linha(s) com duração mas zero em todas as métricas de GPS: {ex}. Unidade desligada ou não usada?")

    if "Data" in df.columns:
        datas = pd.to_datetime(df["Data"], errors="coerce")
        junta("data_futura", AVISO, datas.dt.date > (hoje + timedelta(days=1)),
              "{n} linha(s) com data no futuro: {ex}. Formato da data trocado (dia/mês)?")

    tem_periodo = per.COL in df.columns and not df[per.COL].map(per.vazio).all()
    chave = [c for c in ("Jogador", "Data", "Tipo") if c in df.columns]
    if "Data" in chave and not tem_periodo:
        dup = df.duplicated(subset=chave, keep=False)
        junta("linhas_repetidas", AVISO, dup & ~df.duplicated(subset=chave, keep="first"),
              "{n} caso(s) de um jogador com várias linhas no mesmo dia: {ex}. Vão ser somadas numa só sessão — "
              "se forem partes ou exercícios, mapeia a coluna do nome do período para «Período» e o detalhe fica guardado.")
    if tem_periodo:
        dif = per.diferenca_total(df, GPS)
        if dif:
            m = pd.Series(False, index=df.index)
            m.loc[[d["indice"] for d in dif]] = True
            junta("periodos_vs_total", AVISO, m,
                  "{n} sessão(ões) em que a soma das partes/exercícios difere do total do ficheiro em mais de 5 %: {ex}. "
                  "É o total que conta para a carga do dia.")
        cats = df[per.COL].map(lambda v: per.classificar(v)[0] if not per.vazio(v) else None)
        n_partes = int((cats == "parte").sum())
        n_ex = int((cats == "exercicio").sum())
        problemas.append({"codigo": "periodos", "nivel": INFO, "n": n_partes + n_ex, "exemplos": [],
                          "texto": f"Períodos detetados: {n_partes} linha(s) de partes do jogo e {n_ex} de exercícios — ficam guardados para os relatórios de jogo e de treino."})

    for col, efeito in (
        ("Tipo", "não dá para separar jogo de treino (exposição, benchmark)"),
        ("Dia MD", "o planeamento por dia e a deteção de jogo ficam incompletos"),
        ("Microciclo (Nr)", "a leitura semanal (exposição, relatórios, mapa de calor) não as inclui"),
    ):
        if col in df.columns:
            v = df[col]
            junta(f"sem:{col}", AVISO, v.isna() | (v.astype(str).str.strip() == ""), f"{{n}} linha(s) sem «{col}»: {efeito}.")

    if jogadores_existentes:
        existentes = {_chave_nome(n): n for n in jogadores_existentes}
        sem_acento = {_sem_acentos(k): n for k, n in existentes.items()}
        parecidos = {}
        for nome in df["Jogador"].dropna().unique():
            k = _chave_nome(nome)
            if k in existentes:
                continue
            igual = sem_acento.get(_sem_acentos(k))
            if igual:
                parecidos[nome] = igual
        if parecidos:
            m = df["Jogador"].isin(parecidos) & ~df["Jogador"].duplicated()
            amostra = "; ".join(f"«{a}» ≈ «{b}»" for a, b in list(parecidos.items())[:N_EXEMPLOS])
            idx = df.index[m]
            problemas.append({"codigo": "nome_parecido", "nivel": AVISO, "n": len(parecidos), "exemplos": _exemplos(df, idx),
                              "texto": f"{len(parecidos)} nome(s) quase iguais a jogadores que já existem ({amostra}). Vão ser criados como jogadores novos — "
                                       "corrige a grafia no ficheiro se for o mesmo jogador."})

    # ── Informação ──────────────────────────────────────────────────────────
    if "Tipo" in df.columns:
        jogos = df["Tipo"].astype(str).str.lower().str.startswith(("jogo", "match"))
        if jogos.any() and ("Duração (min)" not in df.columns or _num(df, "Duração (min)")[jogos].isna().all()):
            problemas.append({"codigo": "jogo_sem_minutos", "nivel": INFO, "n": int(jogos.sum()), "exemplos": [],
                              "texto": "Os jogos não têm minutos jogados («Duração»). Sem eles, a referência de jogo usa o pico em vez da média por jogo completo."})

    ordem = {ERRO: 0, AVISO: 1, INFO: 2}
    problemas.sort(key=lambda p: (ordem[p["nivel"]], -p["n"]))
    return {"problemas": problemas, "resumo": resumo(problemas, df), "linhas_erro": sorted(int(i) for i in linhas_erro)}


def resumo(problemas: list[dict], df: pd.DataFrame | None) -> dict:
    n = lambda nivel: sum(1 for p in problemas if p["nivel"] == nivel)
    tem = df is not None and not df.empty
    return {
        "erros": n(ERRO), "avisos": n(AVISO), "info": n(INFO),
        "linhas": int(len(df)) if tem else 0,
        "jogadores": int(df["Jogador"].nunique()) if tem and "Jogador" in df.columns else 0,
        "datas": ([_data_txt(df["Data"].min()), _data_txt(df["Data"].max())]
                  if tem and "Data" in df.columns and df["Data"].notna().any() else None),
    }


def avisos_simples(resultado: dict) -> list[dict]:
    """Formato {nivel, texto} usado pelo ecrã de importação."""
    return [{"nivel": p["nivel"], "texto": p["texto"], "codigo": p["codigo"], "n": p["n"]} for p in resultado["problemas"]]


def publico(resultado: dict) -> dict:
    """Sem os índices internos — o que vai para a API e para a BD."""
    return {"problemas": resultado["problemas"], "resumo": resultado["resumo"],
            "n_linhas_erro": len(resultado.get("linhas_erro") or []), **({"recontagem": resultado["recontagem"]} if "recontagem" in resultado else {})}


# ── Recontagem depois de gravar ──────────────────────────────────────────────
COLS_RECONTAGEM = ["distancia_total_m", "hsr_m", "sprint_m", "acc_n", "dcc_n", "vel_max_kmh", "duracao_min"]


class RecontagemFalhou(Exception):
    pass


def recontar(cur, tabela: str, upload_id, esperado: list[dict]) -> dict:
    """Lê de volta da BD as linhas gravadas por este upload e compara com o que
    o ficheiro tinha (linha a linha, coluna a coluna). Lança RecontagemFalhou à
    primeira diferença — a importação corre numa transação e é desfeita."""
    cols = ", ".join(COLS_RECONTAGEM)
    if tabela == "gps_sessions":
        cur.execute(f"select player_id::text, data::text, coalesce(tipo, ''), {cols} from gps_sessions where upload_id = %s", (upload_id,))
        lidos = {(r[0], r[1], r[2]): r[3:] for r in cur.fetchall()}
        chave = lambda e: (str(e["player_id"]), str(e["data"])[:10], e.get("tipo") or "")
    else:
        cur.execute(f"select player_id::text, data::text, coalesce(tipo, ''), periodo, {cols} from gps_periodos where upload_id = %s", (upload_id,))
        lidos = {(r[0], r[1], r[2], r[3]): r[4:] for r in cur.fetchall()}
        chave = lambda e: (str(e["player_id"]), str(e["data"])[:10], e.get("tipo") or "", e["periodo"])
    if len(lidos) != len(esperado):
        raise RecontagemFalhou(f"{tabela}: {len(esperado)} linhas no ficheiro, {len(lidos)} gravadas.")
    n_valores = 0
    for e in esperado:
        r = lidos.get(chave(e))
        if r is None:
            raise RecontagemFalhou(f"{tabela}: linha em falta ({chave(e)}).")
        for col, v in zip(COLS_RECONTAGEM, r):
            ev = e.get(col)
            if ev is None:
                continue
            n_valores += 1
            if v is None or abs(float(v) - float(ev)) > 1e-6 * max(1.0, abs(float(ev))):
                raise RecontagemFalhou(f"{tabela}: {col} gravado {v}, ficheiro {ev} ({chave(e)}).")
    return {"linhas": len(esperado), "valores": n_valores}


# ── Persistência e leitura ───────────────────────────────────────────────────
def registar(team_id: str, resultado: dict, *, upload_id=None, ficheiro: str | None = None,
             origem: str = "importacao", bloqueou: bool = False, criado_por: str | None = None) -> None:
    """Guarda o resultado (falha em silêncio se a migração 0026 não estiver aplicada)."""
    from app.core.db import get_conn
    p = publico(resultado)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """insert into verificacoes_dados (team_id, upload_id, ficheiro, origem, bloqueou, resumo, problemas, criado_por)
                       values (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (team_id, upload_id, ficheiro, origem, bloqueou,
                     json.dumps({**p["resumo"], "n_linhas_erro": p["n_linhas_erro"], **({"recontagem": p["recontagem"]} if "recontagem" in p else {})}),
                     json.dumps(p["problemas"]), criado_por),
                )
    except Exception:
        logger.warning("Não foi possível registar a verificação de dados (team_id=%s)", team_id, exc_info=True)


def verificar_equipa(team_id: str) -> dict:
    """Corre as mesmas regras sobre os dados já guardados da equipa (sessões e
    períodos) — para encontrar o que entrou antes de haver verificação."""
    from app.core.db import get_conn
    from app.services.dados_equipa import DB_TO_CANONICAL

    cols_db = list(DB_TO_CANONICAL)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""select p.nome, gs.data, {', '.join('gs.' + c for c in cols_db)}
                            from gps_sessions gs join players p on p.id = gs.player_id
                            where gs.team_id = %s and p.ativo order by gs.data""", (team_id,))
            linhas = cur.fetchall()
    df = pd.DataFrame(linhas, columns=["Jogador", "Data", *[DB_TO_CANONICAL[c] for c in cols_db]])
    if not df.empty:
        df["Data"] = pd.to_datetime(df["Data"])
        for c in df.columns:
            if c not in ("Jogador", "Data", "Tipo", "Dia MD"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
    r = verificar_df(df)
    # Na BD já há uma linha por jogador/dia/tipo; e Tipo/Dia MD vazios em dados
    # antigos não são acionáveis aqui — ficam só os problemas nos valores.
    r["problemas"] = [p for p in r["problemas"] if not p["codigo"].startswith("sem:") and p["codigo"] != "linhas_repetidas"]
    r["resumo"] = resumo(r["problemas"], df)
    return r


def obter(team_id: str) -> dict:
    """Última verificação de cada importação (até 20) + estado atual dos dados."""
    from app.core.db import get_conn
    historico, disponivel = [], True
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """select id::text, ficheiro, origem, bloqueou, resumo, problemas, criado_em
                       from verificacoes_dados where team_id = %s order by criado_em desc limit 20""", (team_id,))
                for i, f, o, b, rs, pr, em in cur.fetchall():
                    historico.append({"id": i, "ficheiro": f, "origem": o, "bloqueou": b,
                                      "resumo": rs if isinstance(rs, dict) else json.loads(rs or "{}"),
                                      "problemas": pr if isinstance(pr, list) else json.loads(pr or "[]"),
                                      "criado_em": em.isoformat()})
    except Exception:
        disponivel = False
    atual = verificar_equipa(team_id)
    return {"disponivel": disponivel, "historico": historico, "dados_atuais": publico(atual)}
