"""Jogos da equipa — minutos, contexto (campeonato, taça, torneio, amigável),
golos e assistências de cada atleta, e o resumo da época.

Também importa a folha que o departamento já usa (Excel/CSV), uma linha por
jogador e jogo: equipa, data, competição, ano, n.º, adversário, jogador,
posição, minutos, titular, golos, assistências. Aceita cabeçalhos em inglês,
português ou sueco; sem cabeçalho, usa essa ordem das colunas. A importação
pode repetir-se: atualiza os mesmos jogos e participações em vez de duplicar.
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import date

import pandas as pd

from app.core.db import get_conn

MSG_MIGRACAO = "O registo de jogos precisa da migração supabase/migrations/0015_jogos.sql — aplica-a no SQL Editor do Supabase."

COMPETICOES = ["Campeonato", "Taça", "Torneio", "Amigável"]
POSICOES = ["Guarda-redes", "Defesa central", "Lateral", "Médio", "Extremo", "Avançado"]

_COMP = {
    "campeonato": "Campeonato", "league": "Campeonato", "liga": "Campeonato", "serie": "Campeonato", "serien": "Campeonato",
    "allsvenskan": "Campeonato", "division": "Campeonato", "divisao": "Campeonato",
    "taca": "Taça", "cup": "Taça", "cupen": "Taça", "pokal": "Taça",
    "torneio": "Torneio", "tournament": "Torneio", "turnering": "Torneio",
    "amigavel": "Amigável", "friendly": "Amigável", "traningsmatch": "Amigável", "vanskapsmatch": "Amigável", "teste": "Amigável",
}
_POS = {
    "goalkeeper": "Guarda-redes", "gk": "Guarda-redes", "malvakt": "Guarda-redes", "guarda-redes": "Guarda-redes", "gr": "Guarda-redes",
    "centre back": "Defesa central", "center back": "Defesa central", "cb": "Defesa central", "mittback": "Defesa central", "defesa central": "Defesa central", "dc": "Defesa central",
    "fullback": "Lateral", "full back": "Lateral", "ytterback": "Lateral", "lateral": "Lateral", "wing back": "Lateral",
    "midfielder": "Médio", "mittfaltare": "Médio", "medio": "Médio", "mc": "Médio", "cm": "Médio", "dm": "Médio",
    "winger": "Extremo", "yttermittfaltare": "Extremo", "ytter": "Extremo", "extremo": "Extremo",
    "striker": "Avançado", "forward": "Avançado", "anfallare": "Avançado", "forward/striker": "Avançado", "avancado": "Avançado", "ponta de lanca": "Avançado",
}
_SIM = {"yes", "y", "sim", "s", "ja", "j", "true", "1", "x", "titular", "starter"}

# Cabeçalhos reconhecidos → campo.
_CABECALHOS = {
    "data": ["date", "data", "datum", "match date"],
    "competicao": ["competition", "competicao", "type", "tipo", "context", "contexto", "tavling", "serie", "match type"],
    "numero": ["nr", "no", "match", "jogo", "match nr", "game", "n", "numero", "matchnr"],
    "adversario": ["opponent", "adversario", "motstandare", "vs", "against"],
    "jogador": ["player", "jogador", "spelare", "name", "nome"],
    "posicao": ["position", "posicao", "pos"],
    "minutos": ["minutes", "minutos", "min", "minuter", "mins"],
    "titular": ["starter", "titular", "start", "starting", "starting xi", "startelvan"],
    "golos": ["goals", "golos", "gols", "mal", "goal"],
    "assistencias": ["assists", "assistencias", "assist", "assistance", "passningar"],
}
# Sem cabeçalho: ordem das colunas da folha do departamento.
_ORDEM = ["equipa", "data", "competicao", "ano", "numero", "adversario", "jogador", "posicao", "minutos", "titular", "golos", "assistencias"]


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)


def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.jogos') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


# ── Regras puras ─────────────────────────────────────────────────────────────
def competicao_de(v) -> str:
    n = _norm(v)
    for k, c in _COMP.items():
        if n == k or n.startswith(k):
            return c
    return "Campeonato" if not n else ("Amigável" if "friend" in n or "amig" in n else "Campeonato")


def posicao_de(v) -> str | None:
    n = _norm(v)
    if not n:
        return None
    return _POS.get(n) or next((p for p in POSICOES if _norm(p) == n), str(v).strip()[:30])


def _int(v) -> int:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
            return 0
        return max(0, int(round(float(str(v).replace(",", ".")))))
    except ValueError:
        return 0


def ler_folha(conteudo: bytes, nome: str) -> pd.DataFrame:
    """Lê Excel/CSV e devolve colunas canónicas (data, competicao, adversario,
    jogador, posicao, minutos, titular, golos, assistencias, numero)."""
    if nome.lower().endswith((".xlsx", ".xls")):
        bruto = pd.read_excel(io.BytesIO(conteudo), header=None, dtype=object)
    else:
        texto = conteudo.decode("utf-8-sig", errors="replace")
        sep = ";" if texto.count(";") > texto.count(",") else ("\t" if texto.count("\t") > texto.count(",") else ",")
        bruto = pd.read_csv(io.StringIO(texto), header=None, sep=sep, dtype=object)
    bruto = bruto.dropna(how="all").reset_index(drop=True)
    if bruto.empty:
        raise ValueError("A folha está vazia.")
    # Tem cabeçalho? (a primeira linha tem pelo menos 3 nomes conhecidos)
    primeira = [_norm(x) for x in bruto.iloc[0].tolist()]
    mapa = {}
    for i, h in enumerate(primeira):
        for campo, nomes in _CABECALHOS.items():
            if h in nomes and campo not in mapa.values():
                mapa[i] = campo
                break
    if len(mapa) >= 3:
        df = bruto.iloc[1:].rename(columns=mapa)[list(mapa.values())]
    else:
        if bruto.shape[1] < 9:
            raise ValueError("Não reconheci as colunas. Põe uma linha de cabeçalho (Date, Competition, Opponent, Player, Position, Minutes, Starter, Goals, Assists).")
        df = bruto.iloc[:, : len(_ORDEM)].copy()
        df.columns = _ORDEM[: df.shape[1]]
    for c in ["competicao", "adversario", "posicao", "titular", "golos", "assistencias", "numero"]:
        if c not in df.columns:
            df[c] = None
    falta = [c for c in ("data", "jogador", "minutos") if c not in df.columns]
    if falta:
        raise ValueError(f"Faltam colunas na folha: {', '.join(falta)}.")
    df = df[df["jogador"].notna() & (df["jogador"].astype(str).str.strip() != "")]
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce").dt.date
    df = df[df["data"].notna()]
    out = pd.DataFrame({
        "data": df["data"],
        "competicao": df["competicao"].map(competicao_de),
        "adversario": df["adversario"].fillna("—").astype(str).str.strip().replace("", "—"),
        "numero": df["numero"].map(lambda v: _int(v) or None),
        "jogador": df["jogador"].astype(str).str.strip(),
        "posicao": df["posicao"].map(posicao_de),
        "minutos": df["minutos"].map(_int).clip(upper=150),
        "titular": df["titular"].map(lambda v: _norm(v) in _SIM),
        "golos": df["golos"].map(_int),
        "assistencias": df["assistencias"].map(_int),
    })
    return out.reset_index(drop=True)


def resumo_jogadores(jogos: list[dict], part: list[dict]) -> list[dict]:
    """Por atleta: convocatórias, jogos utilizado, titularidades, minutos (total,
    % dos possíveis e por contexto), golos e assistências."""
    por_jogo = {j["id"]: j for j in jogos}
    possiveis = sum(j["duracao_min"] for j in jogos)
    out: dict[str, dict] = {}
    for p in part:
        j = por_jogo.get(p["jogo_id"])
        if not j:
            continue
        r = out.setdefault(p["atleta_id"], {
            "atleta_id": p["atleta_id"], "nome": p.get("nome"), "convocado": 0, "utilizado": 0, "titular": 0,
            "minutos": 0, "golos": 0, "assistencias": 0, "por_contexto": {c: 0 for c in COMPETICOES},
        })
        r["convocado"] += 1
        r["utilizado"] += 1 if p["minutos"] > 0 else 0
        r["titular"] += 1 if p["titular"] else 0
        r["minutos"] += p["minutos"]
        r["golos"] += p["golos"]
        r["assistencias"] += p["assistencias"]
        r["por_contexto"][j["competicao"]] += p["minutos"]
    for r in out.values():
        r["pct_minutos"] = round(100 * r["minutos"] / possiveis, 1) if possiveis else None
    return sorted(out.values(), key=lambda r: (-r["minutos"], r["nome"] or ""))


# ── Acesso à BD ──────────────────────────────────────────────────────────────
def _verificar_equipa(cur, user_id: str, team_id: str) -> tuple[str, str]:
    from app.services.ficha_atleta_service import _verificar_equipa as v
    return v(cur, user_id, team_id)


def _plantel(cur, team_id: str) -> list[tuple[str, str]]:
    cur.execute(
        """
        select a.id::text, a.nome from players p join atletas a on a.id = p.atleta_id
        where p.team_id = %s and p.ativo order by a.nome
        """,
        (team_id,),
    )
    return cur.fetchall()


def _jogos(cur, team_id: str) -> tuple[list[dict], list[dict]]:
    cur.execute(
        """
        select id::text, data, competicao, adversario, numero, duracao_min, golos_marcados, golos_sofridos, notas
        from jogos where team_id = %s order by data
        """,
        (team_id,),
    )
    jogos = [{"id": r[0], "data": r[1].isoformat(), "competicao": r[2], "adversario": r[3], "numero": r[4],
              "duracao_min": r[5], "golos_marcados": r[6], "golos_sofridos": r[7], "notas": r[8]} for r in cur.fetchall()]
    cur.execute(
        """
        select jp.jogo_id::text, jp.atleta_id::text, a.nome, jp.posicao, jp.minutos, jp.titular, jp.golos, jp.assistencias
        from jogo_participacoes jp join jogos j on j.id = jp.jogo_id join atletas a on a.id = jp.atleta_id
        where j.team_id = %s
        """,
        (team_id,),
    )
    part = [{"jogo_id": r[0], "atleta_id": r[1], "nome": r[2], "posicao": r[3], "minutos": r[4], "titular": r[5],
             "golos": r[6], "assistencias": r[7]} for r in cur.fetchall()]
    return jogos, part


def listar(user_id: str, team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            _, rotulo = _verificar_equipa(cur, user_id, team_id)
            plantel = _plantel(cur, team_id)
            jogos, part = _jogos(cur, team_id)
    n_por_jogo: dict[str, dict] = {}
    for p in part:
        e = n_por_jogo.setdefault(p["jogo_id"], {"convocados": 0, "golos": 0})
        e["convocados"] += 1
        e["golos"] += p["golos"]
    for j in jogos:
        j.update(n_por_jogo.get(j["id"], {"convocados": 0, "golos": 0}))
    return {
        "rotulo": rotulo, "competicoes": COMPETICOES, "posicoes": POSICOES,
        "plantel": [{"atleta_id": a, "nome": n} for a, n in plantel],
        "jogos": list(reversed(jogos)),
        "resumo": resumo_jogadores(jogos, part),
        "minutos_possiveis": sum(j["duracao_min"] for j in jogos),
        "por_contexto": {c: sum(1 for j in jogos if j["competicao"] == c) for c in COMPETICOES},
    }


def obter_jogo(user_id: str, team_id: str, jogo_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            _verificar_equipa(cur, user_id, team_id)
            jogos, part = _jogos(cur, team_id)
    jogo = next((j for j in jogos if j["id"] == jogo_id), None)
    if not jogo:
        raise ValueError("Jogo não encontrado.")
    return {"jogo": jogo, "participacoes": [p for p in part if p["jogo_id"] == jogo_id]}


def _validar_jogo(d: dict) -> dict:
    try:
        dia = date.fromisoformat(str(d.get("data")))
    except ValueError:
        raise ValueError("Indica a data do jogo.")
    comp = d.get("competicao") or "Campeonato"
    if comp not in COMPETICOES:
        raise ValueError("Contexto inválido.")
    adv = " ".join(str(d.get("adversario") or "").split())[:80]
    if not adv:
        raise ValueError("Indica o adversário.")
    dur = _int(d.get("duracao_min")) or 80
    if not 10 <= dur <= 150:
        raise ValueError("A duração do jogo vai de 10 a 150 minutos.")
    gm, gs = d.get("golos_marcados"), d.get("golos_sofridos")
    return {"data": dia, "competicao": comp, "adversario": adv, "numero": _int(d.get("numero")) or None, "duracao_min": dur,
            "golos_marcados": None if gm in (None, "") else _int(gm), "golos_sofridos": None if gs in (None, "") else _int(gs),
            "notas": (d.get("notas") or "").strip()[:300] or None}


def _gravar_participacoes(cur, jogo_id: str, participacoes: list[dict], dur: int, validos: set[str], substituir: bool) -> int:
    if substituir:
        cur.execute("delete from jogo_participacoes where jogo_id = %s", (jogo_id,))
    n = 0
    for p in participacoes:
        aid = p.get("atleta_id")
        if aid not in validos:
            raise PermissionError("Há jogadores que não são desta equipa.")
        minutos = min(_int(p.get("minutos")), dur + 20)  # tolera descontos
        cur.execute(
            """
            insert into jogo_participacoes (jogo_id, atleta_id, posicao, minutos, titular, golos, assistencias)
            values (%s, %s, %s, %s, %s, %s, %s)
            on conflict (jogo_id, atleta_id) do update set posicao = excluded.posicao, minutos = excluded.minutos,
                titular = excluded.titular, golos = excluded.golos, assistencias = excluded.assistencias
            """,
            (jogo_id, aid, posicao_de(p.get("posicao")), minutos, bool(p.get("titular")), _int(p.get("golos")), _int(p.get("assistencias"))),
        )
        n += 1
    return n


def guardar_jogo(user_id: str, team_id: str, dados: dict, participacoes: list[dict], jogo_id: str | None = None) -> dict:
    v = _validar_jogo(dados)
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, _ = _verificar_equipa(cur, user_id, team_id)
            validos = {a for a, _ in _plantel(cur, team_id)}
            if jogo_id:
                cur.execute(
                    """
                    update jogos set data = %s, competicao = %s, adversario = %s, numero = %s, duracao_min = %s,
                        golos_marcados = %s, golos_sofridos = %s, notas = %s
                    where id = %s and team_id = %s returning id::text
                    """,
                    (v["data"], v["competicao"], v["adversario"], v["numero"], v["duracao_min"], v["golos_marcados"],
                     v["golos_sofridos"], v["notas"], jogo_id, team_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Jogo não encontrado.")
            else:
                cur.execute("select 1 from jogos where team_id = %s and data = %s and adversario = %s", (team_id, v["data"], v["adversario"]))
                if cur.fetchone():
                    raise ValueError(f"Já existe o jogo de {v['data'].strftime('%d/%m/%Y')} contra {v['adversario']}.")
                cur.execute(
                    """
                    insert into jogos (academia_id, team_id, data, competicao, adversario, numero, duracao_min,
                                       golos_marcados, golos_sofridos, notas, criado_por)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id::text
                    """,
                    (academia_id, team_id, v["data"], v["competicao"], v["adversario"], v["numero"], v["duracao_min"],
                     v["golos_marcados"], v["golos_sofridos"], v["notas"], user_id),
                )
                row = cur.fetchone()
            n = _gravar_participacoes(cur, row[0], participacoes, v["duracao_min"], validos, substituir=True)
    return {"ok": True, "id": row[0], "participacoes": n}


def apagar_jogo(user_id: str, team_id: str, jogo_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            _verificar_equipa(cur, user_id, team_id)
            cur.execute("delete from jogos where id = %s and team_id = %s", (jogo_id, team_id))
            return {"ok": cur.rowcount > 0}


def importar(user_id: str, team_id: str, conteudo: bytes, nome_ficheiro: str, duracao_min: int = 80) -> dict:
    """Importa a folha de jogos. Jogadores identificados pelo nome (sem
    acentos/maiúsculas) entre os atletas da equipa; os que não existem são
    devolvidos para se adicionarem e voltar a importar."""
    df = ler_folha(conteudo, nome_ficheiro)
    if df.empty:
        raise ValueError("Não encontrei linhas com data, jogador e minutos.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            academia_id, _ = _verificar_equipa(cur, user_id, team_id)
            plantel = _plantel(cur, team_id)
            por_nome = {_norm(n): a for a, n in plantel}
            nao_encontrados = sorted({j for j in df["jogador"] if _norm(j) not in por_nome})
            jogos_n, part_n = 0, 0
            for (dia, adv), g in df.groupby(["data", "adversario"], sort=True):
                comp = g["competicao"].mode().iloc[0]
                numero = next((int(x) for x in g["numero"] if x), None)
                dur = max(duracao_min, int(g["minutos"].max()))
                cur.execute(
                    """
                    insert into jogos (academia_id, team_id, data, competicao, adversario, numero, duracao_min, criado_por)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (team_id, data, adversario) do update set competicao = excluded.competicao,
                        numero = coalesce(excluded.numero, jogos.numero)
                    returning id::text, (xmax = 0)
                    """,
                    (academia_id, team_id, dia, comp, adv, numero, min(dur, 150), user_id),
                )
                jogo_id, novo = cur.fetchone()
                jogos_n += 1 if novo else 0
                linhas = [{"atleta_id": por_nome[_norm(r.jogador)], "posicao": r.posicao, "minutos": r.minutos,
                           "titular": r.titular, "golos": r.golos, "assistencias": r.assistencias}
                          for r in g.itertuples() if _norm(r.jogador) in por_nome]
                part_n += _gravar_participacoes(cur, jogo_id, linhas, min(dur, 150), set(por_nome.values()), substituir=False)
    return {"ok": True, "linhas": int(len(df)), "jogos_novos": jogos_n, "jogos": int(df.groupby(["data", "adversario"]).ngroups),
            "participacoes": part_n, "nao_encontrados": nao_encontrados}


def resumo_epoca_atletas(cur, atleta_ids: list[str], inicio: date, fim: date) -> dict[str, dict]:
    """Para o relatório individual: minutos, jogos e contribuições de cada
    atleta na época, em todas as equipas onde jogou."""
    if not atleta_ids:
        return {}
    cur.execute("select to_regclass('public.jogos') is not null")
    if not cur.fetchone()[0]:
        return {}
    cur.execute(
        """
        select j.id::text, j.data, j.competicao, j.duracao_min, jp.atleta_id::text, jp.minutos, jp.titular, jp.golos, jp.assistencias
        from jogo_participacoes jp join jogos j on j.id = jp.jogo_id
        where jp.atleta_id = any(%s::uuid[]) and j.data between %s and %s
        """,
        (atleta_ids, inicio, fim),
    )
    linhas = cur.fetchall()
    jogos = {r[0]: {"id": r[0], "competicao": r[2], "duracao_min": r[3]} for r in linhas}
    part = [{"jogo_id": r[0], "atleta_id": r[4], "nome": None, "minutos": r[5], "titular": r[6], "golos": r[7], "assistencias": r[8]} for r in linhas]
    out = {}
    for aid in atleta_ids:
        mine = [p for p in part if p["atleta_id"] == aid]
        jogos_a = [jogos[p["jogo_id"]] for p in mine]
        r = resumo_jogadores(jogos_a, mine)
        if r:
            out[aid] = r[0]
    return out
