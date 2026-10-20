"""Planeamento por microciclos — linha temporal da época e plano das sessões.

Microciclo = semana (ou período) da equipa com datas, tipo, perfil, fase e um
FATOR SEMANAL por variável: o alvo da semana de treino em múltiplos da
referência de jogo da equipa (média por 90' dos últimos jogos completos — ver
referencia_jogo). Ex.: HSR 2,5 → a soma de HSR dos treinos da semana, por
jogador, deve chegar a 250 % de um jogo.

O "real" do microciclo usa a mesma conta que a Evolução semanal do separador
Treino vs jogo, mas pelas DATAS do microciclo (não pelo número importado):
só treinos (jogos fora), soma por jogador, média da equipa ÷ referência.

O plano das sessões é dia a dia, editado no Calendário (guardar_dia): cada data
recebe um dia MD e um tipo (Treino, Jogo, Folga); os valores planeados de cada
treino ficam em pse_planeado e
carga_externa_planeada (microciclo + dia MD), que o resto da app já usa
(Planeado vs realizado, alvo do dia no Centro de Controlo).
"""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from app.core.db import get_conn
from app.services.dados_equipa import carregar_df_equipa, invalidar_cache_equipa

MSG_MIGRACAO = (
    "O planeamento por microciclos precisa da migração "
    "supabase/migrations/0012_microciclos.sql — aplica-a no SQL Editor do Supabase."
)

# chave do fator → (coluna canónica, rótulo, unidade)
FATORES: dict[str, tuple[str, str, str]] = {
    "distancia": ("Distância Total (m)", "Distância total", "m"),
    "hsr": ("HSR (m)", "HSR", "m"),
    "sprint": ("Sprint (m)", "Sprint", "m"),
    "acc": ("Acc (n)", "Acelerações", "n"),
    "dcc": ("Dcc (n)", "Desacelerações", "n"),
}
TIPOS = ["Normal", "Duplo jogo", "Sem jogo", "Pré-época"]
PERFIS = ["Introdutório", "Carga", "Choque", "Competitivo", "Recuperação", "Taper"]
FASES = ["Pré-época", "1.ª volta", "2.ª volta", "Pausa competitiva", "Transição"]
TIPOS_DIA = ["Treino", "Jogo", "Folga"]

# Colunas do plano de cada sessão (chave no JSON → coluna na tabela).
PLANO_CARGA = ["distancia_m", "hsr_m", "sprint_m"]


def disponivel() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.microciclos') is not null")
                return bool(cur.fetchone()[0])
    except Exception:
        return False


# ── Regras puras (testáveis sem BD) ──────────────────────────────────────────
def dia_md_relativo(dia: date, jogo: date | None) -> str | None:
    """Dia MD a partir da data do jogo: 3 dias antes → MD-3; 1 depois → MD+1."""
    if jogo is None:
        return None
    d = (dia - jogo).days
    return "MD" if d == 0 else f"MD{d:+d}"


def datas_do_microciclo(inicio: date, fim: date) -> list[date]:
    return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def referencia_equipa(df: pd.DataFrame) -> dict[str, float]:
    """Referência de jogo da equipa por fator (chave → valor por jogo)."""
    from app.services.planeamento_service import _referencia_jogo
    from app.services.referencia_jogo import mascara_jogo

    if df.empty:
        return {}
    cols = [c for c, _, _ in FATORES.values() if c in df.columns and df[c].notna().any()]
    jogos = df[mascara_jogo(df)]
    if jogos.empty or not cols:
        return {}
    ref = _referencia_jogo(jogos, cols)
    return {k: ref[c] for k, (c, _, _) in FATORES.items() if c in ref and ref[c] > 0}


def fatores_reais(df: pd.DataFrame, inicio: date, fim: date, referencia: dict[str, float]) -> dict[str, float]:
    """Carga de treino da semana em múltiplos de um jogo, por fator."""
    from app.services.referencia_jogo import mascara_jogo

    if df.empty or not referencia:
        return {}
    dias = df["Data"].dt.date
    sem = df[(dias >= inicio) & (dias <= fim)]
    treinos = sem[~mascara_jogo(sem)]
    out = {}
    for k, (col, _, _) in FATORES.items():
        if k not in referencia or col not in treinos.columns:
            continue
        por_jogador = treinos.dropna(subset=[col]).groupby("Jogador")[col].sum()
        if por_jogador.empty:
            continue
        out[k] = round(float(por_jogador.mean()) / referencia[k], 2)
    return out


def gerar_semanas(inicio: date, semanas: int, numero_inicial: int, ocupados: set[int]) -> list[tuple[int, date, date]]:
    """Microciclos de 7 dias seguidos a partir de `inicio`, saltando números já usados."""
    out, n = [], numero_inicial
    for i in range(semanas):
        while n in ocupados:
            n += 1
        ini = inicio + timedelta(days=7 * i)
        out.append((n, ini, ini + timedelta(days=6)))
        ocupados = ocupados | {n}
        n += 1
    return out


# ── Validação ────────────────────────────────────────────────────────────────
def _validar(dados: dict) -> dict:
    numero = int(dados.get("numero") or 0)
    if numero < 1 or numero > 99:
        raise ValueError("O número do microciclo tem de estar entre 1 e 99.")
    try:
        ini = date.fromisoformat(str(dados.get("data_inicio")))
        fim = date.fromisoformat(str(dados.get("data_fim")))
    except ValueError:
        raise ValueError("Indica a data de início e a de fim.")
    if fim < ini:
        raise ValueError("A data de fim é anterior à de início.")
    if (fim - ini).days > 20:
        raise ValueError("Um microciclo não pode ter mais de 21 dias.")
    tipo = dados.get("tipo") or "Normal"
    if tipo not in TIPOS:
        raise ValueError("Tipo inválido.")
    perfil = dados.get("perfil") or None
    if perfil and perfil not in PERFIS:
        raise ValueError("Perfil inválido.")
    fase = dados.get("fase") or None
    if fase and fase not in FASES:
        raise ValueError("Fase da época inválida.")
    fatores = {}
    for k, v in (dados.get("fatores") or {}).items():
        if k in FATORES and v not in (None, ""):
            f = float(v)
            if not 0 <= f <= 10:
                raise ValueError("Cada fator semanal tem de estar entre 0 e 10 (× jogo).")
            fatores[k] = round(f, 2)
    nome = (dados.get("nome") or "").strip() or f"MC {numero:02d}"
    return {"numero": numero, "nome": nome, "tipo": tipo, "perfil": perfil, "fase": fase,
            "data_inicio": ini, "data_fim": fim, "fatores": fatores, "notas": (dados.get("notas") or "").strip() or None}


def _sobreposicao(cur, team_id: str, ini: date, fim: date, excluir: str | None) -> None:
    cur.execute(
        """
        select numero from microciclos where team_id = %s and data_inicio <= %s and data_fim >= %s
          and (%s::uuid is null or id <> %s::uuid)
        """,
        (team_id, fim, ini, excluir, excluir),
    )
    row = cur.fetchone()
    if row:
        raise ValueError(f"As datas sobrepõem-se ao MC {row[0]:02d}.")


# ── Leitura ──────────────────────────────────────────────────────────────────
_COLS = "id::text, numero, nome, tipo, perfil, fase, data_inicio, data_fim, fatores, dias, notas"


def _linha(r) -> dict:
    fatores = r[8] if isinstance(r[8], dict) else json.loads(r[8] or "{}")
    dias = r[9] if isinstance(r[9], dict) else json.loads(r[9] or "{}")
    return {"id": r[0], "numero": r[1], "nome": r[2], "tipo": r[3], "perfil": r[4], "fase": r[5],
            "data_inicio": r[6].isoformat(), "data_fim": r[7].isoformat(),
            "fatores": {k: float(v) for k, v in fatores.items()}, "dias": dias, "notas": r[10]}


def listar(team_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"select {_COLS} from microciclos where team_id = %s order by data_inicio", (team_id,))
            mcs = [_linha(r) for r in cur.fetchall()]
    df = carregar_df_equipa(team_id)
    ref = referencia_equipa(df)
    for m in mcs:
        m["reais"] = fatores_reais(df, date.fromisoformat(m["data_inicio"]), date.fromisoformat(m["data_fim"]), ref)
        m["n_treinos"] = sum(1 for d in m["dias"].values() if d.get("tipo") == "Treino")
    return {
        "disponivel": True,
        "referencia": ref,
        "fatores": [{"chave": k, "label": l, "unidade": u} for k, (_, l, u) in FATORES.items()],
        "tipos": TIPOS, "perfis": PERFIS, "fases": FASES,
        "microciclos": mcs,
    }


# ── Escrita ──────────────────────────────────────────────────────────────────
def criar(team_id: str, dados: dict) -> dict:
    v = _validar(dados)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from microciclos where team_id = %s and numero = %s", (team_id, v["numero"]))
            if cur.fetchone():
                raise ValueError(f"Já existe o MC {v['numero']:02d}.")
            _sobreposicao(cur, team_id, v["data_inicio"], v["data_fim"], None)
            cur.execute(
                """
                insert into microciclos (team_id, numero, nome, tipo, perfil, fase, data_inicio, data_fim, fatores, notas)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) returning id::text
                """,
                (team_id, v["numero"], v["nome"], v["tipo"], v["perfil"], v["fase"],
                 v["data_inicio"], v["data_fim"], json.dumps(v["fatores"]), v["notas"]),
            )
            return {"ok": True, "id": cur.fetchone()[0], "numero": v["numero"]}


def atualizar(team_id: str, mc_id: str, dados: dict) -> dict:
    v = _validar(dados)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select numero from microciclos where id = %s and team_id = %s", (mc_id, team_id))
            row = cur.fetchone()
            if not row:
                raise ValueError("Microciclo não encontrado.")
            antigo = row[0]
            if v["numero"] != antigo:
                cur.execute("select 1 from microciclos where team_id = %s and numero = %s", (team_id, v["numero"]))
                if cur.fetchone():
                    raise ValueError(f"Já existe o MC {v['numero']:02d}.")
            _sobreposicao(cur, team_id, v["data_inicio"], v["data_fim"], mc_id)
            cur.execute(
                """
                update microciclos set numero = %s, nome = %s, tipo = %s, perfil = %s, fase = %s,
                    data_inicio = %s, data_fim = %s, fatores = %s::jsonb, notas = %s, atualizado_em = now()
                where id = %s and team_id = %s
                """,
                (v["numero"], v["nome"], v["tipo"], v["perfil"], v["fase"], v["data_inicio"], v["data_fim"],
                 json.dumps(v["fatores"]), v["notas"], mc_id, team_id),
            )
            if v["numero"] != antigo:  # o plano das sessões acompanha a renumeração
                for tabela in ("pse_planeado", "carga_externa_planeada"):
                    cur.execute(f"update {tabela} set microciclo_nr = %s where team_id = %s and microciclo_nr = %s",
                                (v["numero"], team_id, antigo))
    return {"ok": True}


def apagar(team_id: str, mc_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from microciclos where id = %s and team_id = %s returning numero", (mc_id, team_id))
            row = cur.fetchone()
            if row:
                for tabela in ("pse_planeado", "carga_externa_planeada"):
                    cur.execute(f"delete from {tabela} where team_id = %s and microciclo_nr = %s", (team_id, row[0]))
    return {"ok": bool(row)}


def duplicar(team_id: str, mc_id: str) -> dict:
    """Cópia para a semana a seguir ao último microciclo, com o próximo número
    livre — mesmo tipo, perfil, fatores e plano das sessões (dias deslocados)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"select {_COLS} from microciclos where id = %s and team_id = %s", (mc_id, team_id))
            r = cur.fetchone()
            if not r:
                raise ValueError("Microciclo não encontrado.")
            m = _linha(r)
            cur.execute("select coalesce(max(numero), 0), max(data_fim) from microciclos where team_id = %s", (team_id,))
            max_n, ultimo_fim = cur.fetchone()
            ini0, fim0 = date.fromisoformat(m["data_inicio"]), date.fromisoformat(m["data_fim"])
            novo_ini = ultimo_fim + timedelta(days=1)
            desloc = (novo_ini - ini0).days
            novo_fim = fim0 + timedelta(days=desloc)
            numero = int(max_n) + 1
            dias = {(date.fromisoformat(d) + timedelta(days=desloc)).isoformat(): v for d, v in m["dias"].items()}
            cur.execute(
                """
                insert into microciclos (team_id, numero, nome, tipo, perfil, fase, data_inicio, data_fim, fatores, dias, notas)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s) returning id::text
                """,
                (team_id, numero, f"MC {numero:02d}", m["tipo"], m["perfil"], m["fase"], novo_ini, novo_fim,
                 json.dumps(m["fatores"]), json.dumps(dias), m["notas"]),
            )
            novo_id = cur.fetchone()[0]
            cur.execute(
                """
                insert into pse_planeado (team_id, microciclo_nr, dia_md, pse_esperada)
                select team_id, %s, dia_md, pse_esperada from pse_planeado where team_id = %s and microciclo_nr = %s
                on conflict do nothing
                """,
                (numero, team_id, m["numero"]),
            )
            if _tem_duracao(cur):
                cur.execute(
                    """
                    update pse_planeado n set duracao_min = o.duracao_min from pse_planeado o
                    where n.team_id = %s and n.microciclo_nr = %s and o.team_id = n.team_id
                      and o.microciclo_nr = %s and o.dia_md = n.dia_md
                    """,
                    (team_id, numero, m["numero"]),
                )
            cur.execute(
                """
                insert into carga_externa_planeada (team_id, microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m)
                select team_id, %s, dia_md, distancia_m, hsr_m, sprint_m from carga_externa_planeada
                where team_id = %s and microciclo_nr = %s
                on conflict do nothing
                """,
                (numero, team_id, m["numero"]),
            )
    return {"ok": True, "id": novo_id, "numero": numero}


def gerar(team_id: str, inicio: str, semanas: int, numero_inicial: int | None, perfil: str | None) -> dict:
    ini = date.fromisoformat(inicio)
    if not 1 <= semanas <= 52:
        raise ValueError("Escolhe entre 1 e 52 semanas.")
    if perfil and perfil not in PERFIS:
        raise ValueError("Perfil inválido.")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select numero, data_inicio, data_fim from microciclos where team_id = %s", (team_id,))
            existentes = cur.fetchall()
            ocupados = {r[0] for r in existentes}
            n0 = numero_inicial or (max(ocupados) + 1 if ocupados else 1)
            criados = 0
            for n, a, b in gerar_semanas(ini, semanas, n0, ocupados):
                if any(e_ini <= b and e_fim >= a for _, e_ini, e_fim in existentes):
                    continue  # não pisa microciclos já planeados
                cur.execute(
                    """
                    insert into microciclos (team_id, numero, nome, tipo, perfil, data_inicio, data_fim)
                    values (%s, %s, %s, 'Normal', %s, %s, %s)
                    """,
                    (team_id, n, f"MC {n:02d}", perfil, a, b),
                )
                criados += 1
    return {"ok": True, "criados": criados}


# ── Plano das sessões ────────────────────────────────────────────────────────
def _tem_duracao(cur) -> bool:
    cur.execute(
        "select exists (select 1 from information_schema.columns where table_name = 'pse_planeado' and column_name = 'duracao_min')"
    )
    return bool(cur.fetchone()[0])


# ── Um dia de cada vez (editado no Calendário) ───────────────────────────────
def _upsert_plano(cur, team_id: str, numero: int, md: str, planeado: dict) -> None:
    pse_v, dur_v = planeado.get("pse"), planeado.get("duracao_min")
    if pse_v is not None and not 0 <= float(pse_v) <= 10:
        raise ValueError("A PSE planeada vai de 0 a 10.")
    if dur_v is not None and not 0 <= float(dur_v) <= 300:
        raise ValueError("A duração planeada vai de 0 a 300 minutos.")
    if pse_v is not None:
        cur.execute(
            """
            insert into pse_planeado (team_id, microciclo_nr, dia_md, pse_esperada) values (%s, %s, %s, %s)
            on conflict (team_id, microciclo_nr, dia_md) do update set pse_esperada = excluded.pse_esperada, atualizado_em = now()
            """,
            (team_id, numero, md, pse_v),
        )
        if _tem_duracao(cur):
            cur.execute("update pse_planeado set duracao_min = %s where team_id = %s and microciclo_nr = %s and dia_md = %s",
                        (dur_v, team_id, numero, md))
    else:
        cur.execute("delete from pse_planeado where team_id = %s and microciclo_nr = %s and dia_md = %s", (team_id, numero, md))
    valores = [planeado.get(k) for k in PLANO_CARGA]
    if any(v is not None for v in valores):
        cur.execute(
            """
            insert into carga_externa_planeada (team_id, microciclo_nr, dia_md, distancia_m, hsr_m, sprint_m)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (team_id, microciclo_nr, dia_md) do update set distancia_m = excluded.distancia_m,
                hsr_m = excluded.hsr_m, sprint_m = excluded.sprint_m, atualizado_em = now()
            """,
            (team_id, numero, md, *valores),
        )
    else:
        cur.execute("delete from carga_externa_planeada where team_id = %s and microciclo_nr = %s and dia_md = %s",
                    (team_id, numero, md))


def _apagar_plano(cur, team_id: str, numero: int, md: str) -> None:
    for tabela in ("pse_planeado", "carga_externa_planeada"):
        cur.execute(f"delete from {tabela} where team_id = %s and microciclo_nr = %s and dia_md = %s", (team_id, numero, md))


def guardar_dia(team_id: str, data: str, tipo: str, dia_md: str | None, objetivo: str | None,
                planeado: dict | None, propagar_md: bool = False) -> dict:
    """Plano de UM dia: tipo, dia MD, objetivo e valores planeados do treino.
    Com `propagar_md` num dia de jogo, os dias MD do microciclo inteiro passam
    a contar a partir deste jogo."""
    dia = date.fromisoformat(data)
    if tipo not in TIPOS_DIA:
        raise ValueError("Tipo de dia inválido.")
    md = (dia_md or "").strip().upper() or None
    if tipo == "Jogo":
        md = "MD"
    if tipo == "Folga":
        md = None
    planeado = {k: (None if v in (None, "") else float(v)) for k, v in (planeado or {}).items()}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id::text, numero, data_inicio, data_fim, dias from microciclos where team_id = %s and data_inicio <= %s and data_fim >= %s",
                (team_id, dia, dia),
            )
            r = cur.fetchone()
            if not r:
                raise ValueError("Este dia não pertence a nenhum microciclo — cria primeiro o microciclo no Planeamento.")
            mc_id, numero, ini, fim, dias = r
            dias = dias if isinstance(dias, dict) else json.loads(dias or "{}")
            antes = {k: dict(v) for k, v in dias.items()}

            if propagar_md and tipo == "Jogo":
                for d in datas_do_microciclo(ini, fim):
                    k = d.isoformat()
                    atual = dias.get(k, {})
                    t = atual.get("tipo") or "Treino"
                    if t == "Jogo" and d != dia:
                        t = "Treino"
                    dias[k] = {**atual, "tipo": t, "dia_md": None if t == "Folga" else dia_md_relativo(d, dia)}
            dias[dia.isoformat()] = {"tipo": tipo, "dia_md": md, "objetivo": (objetivo or "").strip()[:200]}

            usados: dict[str, str] = {}
            for k, v in sorted(dias.items()):
                m = v.get("dia_md")
                if v.get("tipo") != "Folga" and m:
                    if m in usados:
                        raise ValueError(f"O dia {m} já está em {usados[m][8:10]}/{usados[m][5:7]} neste microciclo.")
                    usados[m] = k

            # Planeado: só treinos guardam valores; dias MD que deixaram de
            # ser treino neste microciclo perdem o planeado.
            treinos_md = {v["dia_md"] for v in dias.values() if v.get("tipo") == "Treino" and v.get("dia_md")}
            antigos_md = {v.get("dia_md") for v in antes.values() if v.get("tipo", "Treino") == "Treino" and v.get("dia_md")}
            for m in antigos_md - treinos_md:
                _apagar_plano(cur, team_id, numero, m)
            if tipo == "Treino" and md and planeado is not None:
                _upsert_plano(cur, team_id, numero, md, planeado)

            cur.execute("update microciclos set dias = %s::jsonb, atualizado_em = now() where id = %s", (json.dumps(dias), mc_id))
    invalidar_cache_equipa(team_id)
    return {"ok": True, "microciclo": numero}
