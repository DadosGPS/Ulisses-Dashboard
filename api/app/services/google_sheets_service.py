"""Google Sheets → PSE e PSE esperada, e wellness diário.

Duas fontes por equipa (tabela fontes_google_sheets, coluna tipo):

- «pse»: a folha de RPE (abaixo);
- «wellness»: as respostas do formulário diário dos jogadores — ver
  preparar_wellness.

Lê uma folha de RPE mantida pela equipa técnica no Google Drive (ex.: «P15 -
RPE» na pasta MALMÖ FF U15, colunas TEAM · DATE · NAME · WEEK · DURATION · RPE
· sRPE · expected RPE · expected sRPE · Training Type · In AVG? · Notes) e grava,
a partir da data de início configurada:

- a PSE real de cada jogador em `gps_sessions` (pse_sessao, duracao_min,
  carga_interna = sRPE). Só mexe nestes campos: se a sessão já tiver dados de
  GPS (ex.: STATSports), a distância, HSR, sprints… ficam como estavam;
- a PSE esperada de cada dia em `pse_planeado` (microciclo × Dia MD), que é o
  que o gráfico «PSE esperada vs real» compara com a média real;
- por jogador, a PSE/sRPE esperada e o tipo de treino da folha em
  `extra_metrics`, para comparar o real com o esperado jogador a jogador.

A leitura usa uma conta de serviço Google só de leitura (variável
GOOGLE_SERVICE_ACCOUNT_JSON): basta partilhar a folha com o email dela como
«Leitor». Sem conta de serviço, tenta a exportação pública (só funciona se a
folha estiver partilhada «qualquer pessoa com o link»).
"""
from __future__ import annotations

import base64
import csv
import io
import json
import logging
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

import psycopg2.extras

from utils.calculos import DIAS_MD_ORDEM

from app.core.config import get_settings
from app.core.db import get_conn
from app.services.dados_equipa import invalidar_cache_equipa
from app.services.ingest_service import _upsert_players, plano_por_dia

logger = logging.getLogger(__name__)

ORIGEM = "Google Sheets"
_ESCOPO = "https://www.googleapis.com/auth/spreadsheets.readonly"

# Coluna lógica → nomes aceites no cabeçalho (comparação sem acentos/maiúsculas).
_ALIASES = {
    "equipa": ["team", "equipa", "escalao", "lag"],
    "data": ["date", "data", "datum"],
    "jogador": ["name", "nome", "player", "jogador", "atleta", "namn"],
    "semana": ["week", "semana", "microciclo", "vecka"],
    "duracao": ["duration", "duracao", "duracao (min)", "minutes", "min", "minutos"],
    "pse": ["rpe", "pse", "pse sessao", "session rpe"],
    "srpe": ["srpe", "s-rpe", "carga interna", "spse", "session load"],
    "pse_esperada": ["expected rpe", "pse esperada", "rpe esperada", "planned rpe"],
    "srpe_esperada": ["expected srpe", "srpe esperada", "planned srpe"],
    "tipo_treino": ["training type", "tipo de treino", "tipo treino", "session type", "tipo"],
    "na_media": ["in avg?", "in avg", "na media?", "na media"],
    "notas": ["notes", "notas", "observacoes"],
}
_OBRIGATORIAS = ("data", "jogador", "pse")


class ErroGoogleSheets(Exception):
    """Erro com mensagem pronta a mostrar ao utilizador."""


# ── Utilitários de texto/números ─────────────────────────────────────────────
def _chave(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def extrair_spreadsheet_id(url_ou_id: str) -> str:
    """Aceita o link completo da folha ou só o ID."""
    s = (url_ou_id or "").strip()
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]{20,})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", s):
        return s
    raise ErroGoogleSheets("Link inválido — cola o link da folha do Google Sheets (docs.google.com/spreadsheets/d/…).")


def _num(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(" ", "").replace(" ", "")
    if not s or s in ("-", "—", "#N/A", "#VALUE!", "#REF!", "#DIV/0!"):
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _data(v: Any) -> date | None:
    """Datas como a folha as mostra (dd/mm/aaaa) ou número de série do Sheets."""
    if v is None:
        return None
    s = str(v).strip().split(" ")[0].split("T")[0]
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    n = _num(s)
    if n is not None and 20000 < n < 80000:  # série do Sheets/Excel (dias desde 30/12/1899)
        return date(1899, 12, 30) + timedelta(days=int(n))
    return None


# ── Tipo de sessão e Dia MD ──────────────────────────────────────────────────
_RE_MD_RELATIVO = re.compile(r"^MD\s*([+\-−–])\s*(\d)")


def e_jogo(tipo_treino: str | None) -> bool:
    """«MD», «MD (AGF)», «MD - Bjärreds», «Match Day», «GAME», «Randers GAME»…
    são jogos; «MD-1», «MD - 4», «Training - Internal Game» não são."""
    u = _chave(tipo_treino).upper()
    if not u:
        return False
    if _RE_MD_RELATIVO.match(u) or u.startswith("MD/"):
        return False
    if u == "MD" or u.startswith("MD (") or u.startswith("MD(") or re.match(r"^MD\s*-\s*[A-Z]", u):
        return True
    if "MATCH" in u or "JOGO" in u:
        return True
    return "GAME" in u and "TRAINING" not in u


def dia_md_da_folha(tipo_treino: str | None) -> str | None:
    """«MD-1», «MD + 2», «MD - 4 Strength» → Dia MD indicado na própria folha."""
    m = _RE_MD_RELATIVO.match(_chave(tipo_treino).upper())
    if not m:
        return None
    dia = f"MD{'+' if m.group(1) == '+' else '-'}{m.group(2)}"
    return dia if dia in DIAS_MD_ORDEM else None


def dia_md_por_jogos(d: date, jogos: list[date]) -> str | None:
    """Dia MD a partir dos jogos da folha: 1–2 dias depois de um jogo → MD+n;
    senão, até 5 dias antes do jogo seguinte → MD-n."""
    if d in jogos:
        return "MD"
    anteriores = [j for j in jogos if j < d]
    seguintes = [j for j in jogos if j > d]
    if anteriores and (d - max(anteriores)).days <= 2:
        return f"MD+{(d - max(anteriores)).days}"
    if seguintes and (min(seguintes) - d).days <= 5:
        return f"MD-{(min(seguintes) - d).days}"
    return None


# ── Leitura da tabela ────────────────────────────────────────────────────────
def ler_tabela(linhas: list[list[Any]], aliases: dict[str, list[str]] | None = None,
               obrigatorias: tuple[str, ...] = _OBRIGATORIAS, multiplas: dict[str, str] | None = None,
               erro: str = "Não encontrei o cabeçalho na folha — são precisas pelo menos as colunas DATE, NAME e RPE.") -> list[dict]:
    """Encontra o cabeçalho (primeira linha com as colunas obrigatórias) e
    devolve uma lista de registos {coluna lógica: valor cru}. `multiplas`
    junta numa lista todas as colunas que começam por um prefixo (ex.: as
    várias «Pain location [...]» de um formulário com grelha)."""
    aliases = aliases or _ALIASES
    multiplas = multiplas or {}
    for i, linha in enumerate(linhas[:30]):
        chaves = [_chave(c) for c in linha]
        indices: dict[str, int] = {}
        for logica, nomes in aliases.items():
            for j, k in enumerate(chaves):
                if k in nomes and j not in indices.values():
                    indices[logica] = j
                    break
        if all(c in indices for c in obrigatorias):
            grupos = {logica: [j for j, k in enumerate(chaves) if k.startswith(prefixo)]
                      for logica, prefixo in multiplas.items()}
            registos = []
            for linha_dados in linhas[i + 1:]:
                if not any(str(c).strip() for c in linha_dados):
                    continue
                r = {logica: (linha_dados[j] if j < len(linha_dados) else None) for logica, j in indices.items()}
                for logica, js in grupos.items():
                    r[logica] = [linha_dados[j] for j in js if j < len(linha_dados) and str(linha_dados[j]).strip()]
                registos.append(r)
            return registos
    raise ErroGoogleSheets(erro)


def preparar(registos: list[dict], data_inicio: date, filtro_equipa: str | None = None,
             plano: dict[str, dict] | None = None) -> dict:
    """Converte os registos da folha em sessões a gravar e na PSE esperada de
    cada dia. Função pura (sem BD) — testada em tests/test_google_sheets.py.

    - Só entram linhas com data ≥ data_inicio (e da equipa `filtro_equipa`, se indicada).
    - Microciclo e Dia MD vêm do planeamento da app quando existe para esse
      dia; senão, a semana ISO da data (segunda a domingo) e o Dia MD indicado
      no tipo de treino ou calculado a partir dos jogos da folha.
    - Jogadores sem PSE nesse dia (não treinaram / não responderam) não
      geram sessão, mas contam para a PSE esperada do dia.
    """
    plano = plano or {}
    filtro = _chave(filtro_equipa) if filtro_equipa else None

    validos = []
    for r in registos:
        d = _data(r.get("data"))
        nome = " ".join(str(r.get("jogador") or "").split())
        if d is None or not nome:
            continue
        if filtro and "equipa" in r and _chave(r.get("equipa")) != filtro:
            continue
        validos.append((d, nome, r))

    # Jogos de toda a folha (também antes da data de início): o Dia MD dos
    # primeiros dias importados depende do jogo anterior.
    jogos = sorted({d for d, _, r in validos if e_jogo(r.get("tipo_treino"))})

    agregados: dict[tuple, dict] = {}
    esperada_por_dia: dict[tuple, list[float]] = {}
    duracao_por_dia: dict[tuple, list[float]] = {}
    jogo_por_dia: dict[tuple, bool] = {}
    ignoradas = {"antes_inicio": 0, "sem_pse": 0, "pse_invalida": 0}
    datas: set[date] = set()

    for d, nome, r in validos:
        if d < data_inicio:
            ignoradas["antes_inicio"] += 1
            continue
        tipo_treino = str(r.get("tipo_treino") or "").strip() or None
        jogo = e_jogo(tipo_treino)
        p = plano.get(d.isoformat()) or {}
        # Semana ISO (segunda a domingo): a coluna WEEK da folha começa ao
        # domingo (WEEKNUM do Excel) e punha o jogo de domingo na semana
        # seguinte, separado dos treinos que o prepararam.
        microciclo = p.get("microciclo") if p.get("microciclo") is not None else d.isocalendar()[1]
        dia_md = p.get("dia_md") or ("MD" if jogo else (dia_md_da_folha(tipo_treino) or dia_md_por_jogos(d, jogos)))
        tipo = "Jogo" if jogo else (p.get("tipo") if p.get("tipo") in ("Treino", "Jogo") else "Treino")

        pse_esp = _num(r.get("pse_esperada"))
        if pse_esp is not None and 0 <= pse_esp <= 10 and microciclo is not None and dia_md:
            esperada_por_dia.setdefault((int(microciclo), dia_md), []).append(pse_esp)
            dur_plano = _num(r.get("duracao"))
            if dur_plano and 0 < dur_plano <= 300:
                duracao_por_dia.setdefault((int(microciclo), dia_md), []).append(dur_plano)
            jogo_por_dia[(int(microciclo), dia_md)] = jogo

        pse = _num(r.get("pse"))
        if pse is None:
            ignoradas["sem_pse"] += 1
            continue
        if not 0 <= pse <= 10:
            ignoradas["pse_invalida"] += 1
            continue
        dur = _num(r.get("duracao"))
        if dur is not None and not 0 < dur <= 300:
            dur = None
        srpe = _num(r.get("srpe"))
        if srpe is None or srpe < 0:
            srpe = pse * dur if dur else None
        srpe_esp = _num(r.get("srpe_esperada"))
        na_media = _chave(r.get("na_media"))

        chave = (nome, d, tipo)
        if chave in agregados:  # duas sessões no mesmo dia: soma carga e duração
            a = agregados[chave]
            a["duracao_min"] = (a["duracao_min"] or 0) + (dur or 0) or None
            a["carga_interna"] = (a["carga_interna"] or 0) + (srpe or 0) or None
            a["pse_sessao"] = round(a["carga_interna"] / a["duracao_min"], 1) if a["carga_interna"] and a["duracao_min"] else max(a["pse_sessao"], pse)
            continue
        datas.add(d)
        semana = _num(r.get("semana"))
        extra = {"Origem": ORIGEM, "Semana (folha)": int(semana) if semana else None, "PSE esperada": pse_esp, "sRPE esperada": srpe_esp,
                 "Tipo de treino": tipo_treino,
                 "Na média da equipa": (na_media == "yes" or na_media == "sim") if na_media else None,
                 "Notas": (str(r.get("notas")).strip() or None) if r.get("notas") else None}
        agregados[chave] = {
            "jogador": nome, "data": d, "tipo": tipo, "dia_md": dia_md,
            "microciclo_nr": int(microciclo) if microciclo is not None else None,
            "pse_sessao": pse, "duracao_min": dur, "carga_interna": srpe,
            "extra": {k: v for k, v in extra.items() if v is not None},
        }

    pse_esperada = []
    for (mc, dia), valores in sorted(esperada_por_dia.items()):
        valor, _ = Counter(valores).most_common(1)[0]  # o valor planeado do dia (moda)
        # Duração planeada: a do treino (moda); no jogo, a do jogo inteiro (máximo).
        duracoes = duracao_por_dia.get((mc, dia)) or []
        duracao = (max(duracoes) if jogo_por_dia.get((mc, dia)) else Counter(duracoes).most_common(1)[0][0]) if duracoes else None
        pse_esperada.append({"microciclo": mc, "dia_md": dia, "pse_esperada": valor, "duracao_min": duracao})

    sessoes = list(agregados.values())
    return {
        "sessoes": sessoes,
        "pse_esperada": pse_esperada,
        "resumo": {
            "sessoes": len(sessoes),
            "jogadores": len({s["jogador"] for s in sessoes}),
            "dias": len(datas),
            "intervalo": [min(datas).isoformat(), max(datas).isoformat()] if datas else None,
            "dias_pse_esperada": len(pse_esperada),
            "ignoradas": ignoradas,
        },
    }


# ── Wellness (respostas do formulário diário) ───────────────────────────────
_ALIASES_WELLNESS = {
    "equipa": ["team", "equipa", "lag"],
    "data": ["carimbo de data/hora", "timestamp", "marca temporal", "date", "data", "datum"],
    "jogador": ["player", "name", "nome", "jogador", "atleta", "namn"],
    "energia": ["energy level", "energy", "energia", "nivel de energia"],
    "dor_musc": ["muscle soreness", "soreness", "dor muscular", "dores musculares"],
    "sono": ["sleep quality", "sleep", "sono", "qualidade do sono"],
    "prontidao": ["readiness to train", "readiness", "prontidao", "prontidao para treinar"],
    "stress": ["mental stress level", "mental stress", "stress", "stress mental", "nivel de stress"],
    "pode_treinar": ["are you able to train today?", "are you able to train today", "able to train",
                     "podes treinar hoje?", "consegues treinar hoje?"],
    "dor": ["pain perception", "pain", "dor", "percecao de dor"],
}
_MULTIPLAS_WELLNESS = {"local_dor": "pain location"}


def _escala(v: Any) -> int | None:
    """Resposta de escala 1–5 (inteira). Fora disso → sem resposta."""
    n = _num(v)
    if n is None or n != int(n) or not 1 <= n <= 5:
        return None
    return int(n)


def preparar_wellness(registos: list[dict], data_inicio: date, filtro_equipa: str | None = None) -> dict:
    """Converte as respostas do formulário no wellness diário de cada jogador.
    Função pura (sem BD) — testada em tests/test_google_sheets.py.

    Na app, cada item vai de 1 (mau) a 5 (ótimo). O formulário tem escalas em
    que 5 é mau (dor muscular, stress), por isso essas são invertidas (6 − x):
      sono    ← Sleep quality           dor_musc ← 6 − Muscle soreness
      stress  ← 6 − Mental stress level fadiga   ← Energy level
    O Hooper Index é o original (sono, stress, fadiga e dor muscular):
    Σ (5 − item), 0 = ótimo … 16 = péssimo; só é calculado com os quatro.
    Prontidão, «pode treinar?», dor e local da dor ficam em extra_metrics.
    Se o mesmo jogador responder duas vezes no mesmo dia, conta a última.
    """
    filtro = _chave(filtro_equipa) if filtro_equipa else None
    por_dia: dict[tuple, dict] = {}
    ignoradas = {"antes_inicio": 0, "sem_jogador": 0, "sem_respostas": 0}

    for r in registos:
        d = _data(r.get("data"))
        nome = " ".join(str(r.get("jogador") or "").split())
        if d is None:
            continue
        if filtro and "equipa" in r and _chave(r.get("equipa")) != filtro:
            continue
        if d < data_inicio:
            ignoradas["antes_inicio"] += 1
            continue
        if not nome:
            ignoradas["sem_jogador"] += 1
            continue
        sono, energia = _escala(r.get("sono")), _escala(r.get("energia"))
        dor_musc_f, stress_f = _escala(r.get("dor_musc")), _escala(r.get("stress"))
        if all(v is None for v in (sono, energia, dor_musc_f, stress_f)):
            ignoradas["sem_respostas"] += 1
            continue
        dor_musc = 6 - dor_musc_f if dor_musc_f else None
        stress = 6 - stress_f if stress_f else None
        itens = (sono, dor_musc, stress, energia)
        hooper = sum(5 - v for v in itens) if all(v is not None for v in itens) else None

        pode = _chave(r.get("pode_treinar"))
        locais = [str(x).strip() for x in (r.get("local_dor") or []) if str(x).strip()]
        locais = [x for x in dict.fromkeys(", ".join(locais).split(", ")) if x and _chave(x) not in ("none", "nenhum", "nada")]
        extra = {
            "Origem": ORIGEM,
            "Prontidão para treinar (1-5)": _escala(r.get("prontidao")),
            "Pode treinar hoje": (pode in ("yes", "sim", "ja")) if pode else None,
            "Dor (1-5)": _escala(r.get("dor")),
            "Local da dor": ", ".join(locais) or None,
        }
        por_dia[(_chave(nome), d)] = {
            "jogador": nome, "data": d, "sono": sono, "dor_musc": dor_musc, "stress": stress,
            "fadiga": energia, "hooper_index": hooper,
            "extra": {k: v for k, v in extra.items() if v is not None},
        }

    respostas = list(por_dia.values())
    datas = {x["data"] for x in respostas}
    return {
        "respostas": respostas,
        "resumo": {
            "respostas": len(respostas),
            "jogadores": len({x["jogador"] for x in respostas}),
            "dias": len(datas),
            "intervalo": [min(datas).isoformat(), max(datas).isoformat()] if datas else None,
            "nao_podem_treinar": sum(1 for x in respostas if x["extra"].get("Pode treinar hoje") is False),
            "ignoradas": ignoradas,
        },
    }


# ── Acesso ao Google ─────────────────────────────────────────────────────────
def _info_conta_servico() -> dict | None:
    bruto = (get_settings().google_service_account_json or "").strip()
    if not bruto:
        return None
    try:
        if not bruto.startswith("{"):
            bruto = base64.b64decode(bruto).decode()
        info = json.loads(bruto)
        return info if info.get("client_email") and info.get("private_key") else None
    except Exception:
        logger.exception("GOOGLE_SERVICE_ACCOUNT_JSON inválido")
        return None


def email_conta_servico() -> str | None:
    info = _info_conta_servico()
    return info.get("client_email") if info else None


def ler_folha(spreadsheet_id: str, folha: str) -> list[list[Any]]:
    """Valores da folha (como aparecem no Sheets)."""
    import requests

    info = _info_conta_servico()
    if info:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        cred = service_account.Credentials.from_service_account_info(info, scopes=[_ESCOPO])
        intervalo = quote(f"'{folha}'" if folha else "A:ZZ", safe="")  # sem separador → o primeiro
        try:
            r = AuthorizedSession(cred).get(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{intervalo}",
                params={"valueRenderOption": "FORMATTED_VALUE", "dateTimeRenderOption": "FORMATTED_STRING"},
                timeout=30,
            )
        except requests.RequestException:
            raise ErroGoogleSheets("Não foi possível ligar ao Google. Tenta outra vez daqui a pouco.")
        if r.status_code == 403:
            raise ErroGoogleSheets(f"A folha ainda não está partilhada com a app. No Google Sheets: Partilhar → "
                                   f"adiciona {info['client_email']} como Leitor.")
        if r.status_code == 404:
            raise ErroGoogleSheets("Folha não encontrada — confirma o link.")
        if r.status_code == 400:
            raise ErroGoogleSheets(f"Não existe nenhum separador chamado «{folha}» nesta folha.")
        if not r.ok:
            raise ErroGoogleSheets(f"O Google recusou o pedido ({r.status_code}).")
        return r.json().get("values", [])

    # Sem conta de serviço: exportação pública (folha partilhada por link).
    try:
        r = requests.get(
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq",
            params={"tqx": "out:csv", "sheet": folha}, timeout=30,
        )
    except requests.RequestException:
        raise ErroGoogleSheets("Não foi possível ligar ao Google. Tenta outra vez daqui a pouco.")
    if not r.ok or "text/csv" not in r.headers.get("content-type", ""):
        raise ErroGoogleSheets("A folha é privada e a app ainda não tem conta de serviço Google configurada "
                               "(variável GOOGLE_SERVICE_ACCOUNT_JSON na API).")
    return list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))


# ── Configuração por equipa ──────────────────────────────────────────────────
def _publico(row) -> dict | None:
    if not row:
        return None
    spreadsheet_id, folha, data_inicio, filtro, ativo, ultima, resultado = row
    return {
        "spreadsheet_id": spreadsheet_id,
        "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit",
        "folha": folha,
        "data_inicio": data_inicio.isoformat() if data_inicio else None,
        "filtro_equipa": filtro,
        "ativo": ativo,
        "ultima_sincronizacao": ultima.isoformat() if ultima else None,
        "ultimo_resultado": resultado,
    }


_COLS = "spreadsheet_id, folha, data_inicio, filtro_equipa, ativo, ultima_sincronizacao, ultimo_resultado"


TIPOS = ("pse", "wellness")
_FOLHA_PADRAO = {"pse": "RPE", "wellness": ""}


def obter_config(team_id: str, tipo: str = "pse") -> dict:
    fonte = None
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"select {_COLS} from fontes_google_sheets where team_id = %s and tipo = %s", (team_id, tipo))
                fonte = _publico(cur.fetchone())
        disponivel = True
    except Exception:
        disponivel = False  # migração 0028/0029 por aplicar
    return {"disponivel": disponivel, "email_conta_servico": email_conta_servico(), "fonte": fonte}


def guardar_config(team_id: str, user_id: str, url_ou_id: str, folha: str, data_inicio: date,
                   filtro_equipa: str | None, ativo: bool = True, tipo: str = "pse") -> dict:
    spreadsheet_id = extrair_spreadsheet_id(url_ou_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""insert into fontes_google_sheets (team_id, tipo, spreadsheet_id, folha, data_inicio, filtro_equipa, ativo, criado_por)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (team_id, tipo) do update set spreadsheet_id = excluded.spreadsheet_id, folha = excluded.folha,
                        data_inicio = excluded.data_inicio, filtro_equipa = excluded.filtro_equipa,
                        ativo = excluded.ativo, atualizado_em = now()
                    returning {_COLS}""",
                (team_id, tipo, spreadsheet_id, (folha or "").strip() or _FOLHA_PADRAO[tipo], data_inicio,
                 (filtro_equipa or "").strip() or None, ativo, user_id),
            )
            return _publico(cur.fetchone())


def remover_config(team_id: str, tipo: str = "pse") -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from fontes_google_sheets where team_id = %s and tipo = %s", (team_id, tipo))


# ── Sincronização ────────────────────────────────────────────────────────────
def _registar_resultado(team_id: str, resultado: dict, tipo: str = "pse") -> None:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "update fontes_google_sheets set ultima_sincronizacao = now(), ultimo_resultado = %s "
                    "where team_id = %s and tipo = %s",
                    (json.dumps(resultado), team_id, tipo),
                )
    except Exception:
        logger.exception("Falha a registar o resultado da sincronização (team_id=%s)", team_id)


# Impressão digital do conteúdo lido da última vez, por (equipa, tipo): a
# leitura automática frequente (ao abrir/voltar à app) só grava e limpa o
# cache quando a folha mudou. Em memória: depois de um reinício grava uma vez.
_ultima_leitura: dict[tuple[str, str], str] = {}


def sincronizar(team_id: str, user_id: str | None = None, tipo: str = "pse", so_se_mudou: bool = False) -> dict:
    """Lê a folha configurada e grava, desde a data de início, a PSE e a PSE
    esperada (tipo «pse») ou o wellness diário (tipo «wellness»). Com
    `so_se_mudou`, se o conteúdo for igual ao da última leitura não grava nada
    e devolve `sem_alteracoes`."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select spreadsheet_id, folha, data_inicio, filtro_equipa from fontes_google_sheets "
                        "where team_id = %s and tipo = %s", (team_id, tipo))
            cfg = cur.fetchone()
    if not cfg:
        raise ErroGoogleSheets("Ainda não ligaste nenhuma folha do Google Sheets a esta equipa.")
    spreadsheet_id, folha, data_inicio, filtro_equipa = cfg

    try:
        valores = ler_folha(spreadsheet_id, folha)
        import hashlib
        impressao = hashlib.sha1(
            json.dumps([valores, str(data_inicio), filtro_equipa], default=str).encode()
        ).hexdigest()
        if so_se_mudou and _ultima_leitura.get((team_id, tipo)) == impressao:
            _marcar_leitura(team_id, tipo)
            return {"ok": True, "sem_alteracoes": True}
        if tipo == "wellness":
            registos = ler_tabela(valores, _ALIASES_WELLNESS, ("data", "jogador"), _MULTIPLAS_WELLNESS,
                                  "Não encontrei o cabeçalho na folha — são precisas pelo menos as colunas da data "
                                  "(Timestamp / Carimbo de data/hora) e do jogador (Player).")
            resultado = _gravar_wellness(team_id, user_id, folha, registos, data_inicio, filtro_equipa)
        else:
            registos = ler_tabela(valores)
            resultado = _gravar(team_id, user_id, folha, registos, data_inicio, filtro_equipa)
    except ErroGoogleSheets as e:
        _registar_resultado(team_id, {"ok": False, "erro": str(e)}, tipo)
        raise
    except Exception:
        logger.exception("Falha na sincronização Google Sheets (team_id=%s, tipo=%s)", team_id, tipo)
        _registar_resultado(team_id, {"ok": False, "erro": "Erro inesperado ao gravar os dados da folha."}, tipo)
        raise ErroGoogleSheets("Erro inesperado ao gravar os dados da folha — nada foi alterado.")

    _registar_resultado(team_id, resultado, tipo)
    _ultima_leitura[(team_id, tipo)] = impressao
    invalidar_cache_equipa(team_id)
    return resultado


def _marcar_leitura(team_id: str, tipo: str) -> None:
    """Folha lida e igual à anterior: só atualiza a hora da última leitura."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("update fontes_google_sheets set ultima_sincronizacao = now() "
                            "where team_id = %s and tipo = %s", (team_id, tipo))
    except Exception:
        logger.exception("Falha a marcar a leitura (team_id=%s)", team_id)


def _gravar(team_id: str, user_id: str | None, folha: str, registos: list[dict], data_inicio: date,
            filtro_equipa: str | None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            preparado = preparar(registos, data_inicio, filtro_equipa, plano_por_dia(cur, team_id))
            sessoes = preparado["sessoes"]

            if user_id is None:  # agendador: atribui o registo a quem criou a equipa
                cur.execute("select criado_por from teams where id = %s", (team_id,))
                user_id = cur.fetchone()[0]
            cur.execute(
                "insert into uploads (team_id, uploaded_by, filename, status) values (%s, %s, %s, 'processing') returning id",
                (team_id, user_id, f"{ORIGEM}: {folha}"),
            )
            upload_id = cur.fetchone()[0]

            mapa = _upsert_players(cur, team_id, {s["jogador"]: None for s in sessoes})
            linhas = [
                (team_id, mapa[s["jogador"]], upload_id, s["data"], s["tipo"], s["dia_md"], s["microciclo_nr"],
                 s["pse_sessao"], s["duracao_min"], s["carga_interna"], json.dumps(s["extra"]))
                for s in sessoes if s["jogador"] in mapa
            ]
            if linhas:
                # Só a PSE (e a carga interna/duração que vêm com ela) é da
                # folha: o GPS da mesma sessão, se existir, não é tocado.
                psycopg2.extras.execute_values(
                    cur,
                    """
                    insert into gps_sessions (team_id, player_id, upload_id, data, tipo, dia_md, microciclo_nr,
                                              pse_sessao, duracao_min, carga_interna, extra_metrics)
                    values %s
                    on conflict (team_id, player_id, data, tipo) do update set
                        pse_sessao = excluded.pse_sessao,
                        carga_interna = coalesce(excluded.carga_interna,
                                                 excluded.pse_sessao * coalesce(gps_sessions.duracao_min, excluded.duracao_min),
                                                 gps_sessions.carga_interna),
                        duracao_min = coalesce(gps_sessions.duracao_min, excluded.duracao_min),
                        dia_md = coalesce(gps_sessions.dia_md, excluded.dia_md),
                        microciclo_nr = coalesce(gps_sessions.microciclo_nr, excluded.microciclo_nr),
                        extra_metrics = gps_sessions.extra_metrics || excluded.extra_metrics
                    """,
                    linhas,
                )
            if preparado["pse_esperada"]:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    insert into pse_planeado (team_id, microciclo_nr, dia_md, pse_esperada, duracao_min) values %s
                    on conflict (team_id, microciclo_nr, dia_md)
                    do update set pse_esperada = excluded.pse_esperada,
                                  duracao_min = coalesce(excluded.duracao_min, pse_planeado.duracao_min),
                                  atualizado_em = now()
                    """,
                    [(team_id, p["microciclo"], p["dia_md"], p["pse_esperada"], p["duracao_min"])
                     for p in preparado["pse_esperada"]],
                )
            cur.execute("update uploads set status = 'done', row_count = %s where id = %s", (len(linhas), upload_id))

    return {"ok": True, "folha": folha, "data_inicio": data_inicio.isoformat(), **preparado["resumo"]}


def _gravar_wellness(team_id: str, user_id: str | None, folha: str, registos: list[dict], data_inicio: date,
                     filtro_equipa: str | None) -> dict:
    preparado = preparar_wellness(registos, data_inicio, filtro_equipa)
    respostas = preparado["respostas"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            mapa = _upsert_players(cur, team_id, {x["jogador"]: None for x in respostas})
            linhas = [
                (team_id, mapa[x["jogador"]], x["data"], x["sono"], x["dor_musc"], x["stress"], x["fadiga"],
                 x["hooper_index"], json.dumps(x["extra"]))
                for x in respostas if x["jogador"] in mapa
            ]
            if linhas:
                # Igual ao questionário da app (wellness_service): o wellness
                # junta-se à sessão de treino do dia ou cria uma linha só com ele.
                # Só os campos de wellness são tocados.
                psycopg2.extras.execute_values(
                    cur,
                    """
                    insert into gps_sessions (team_id, player_id, data, tipo, sono, dor_musc, stress, fadiga,
                                              hooper_index, extra_metrics)
                    values %s
                    on conflict (team_id, player_id, data, tipo) do update set
                        sono = excluded.sono,
                        dor_musc = excluded.dor_musc,
                        stress = excluded.stress,
                        fadiga = excluded.fadiga,
                        hooper_index = excluded.hooper_index,
                        extra_metrics = gps_sessions.extra_metrics || excluded.extra_metrics
                    """,
                    linhas,
                    template="(%s, %s, %s, 'Treino', %s, %s, %s, %s, %s, %s::jsonb)",
                )
    return {"ok": True, "folha": folha, "data_inicio": data_inicio.isoformat(), **preparado["resumo"]}


def sincronizar_todas() -> dict:
    """Agendador: sincroniza todas as folhas ativas (PSE e wellness)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select team_id, tipo from fontes_google_sheets where ativo")
            fontes = [(str(r[0]), r[1]) for r in cur.fetchall()]
    ok, erros = 0, 0
    for team_id, tipo in fontes:
        try:
            sincronizar(team_id, tipo=tipo, so_se_mudou=True)
            ok += 1
        except Exception:
            erros += 1
    return {"fontes": len(fontes), "ok": ok, "erros": erros}


def sincronizar_se_preciso(team_id: str, user_id: str | None = None, minutos: int = 2) -> dict:
    """Ao abrir a app (e ao voltar a ela): volta a ler as folhas ativas da
    equipa cuja última leitura tem mais de `minutos`; só conta (e a app só
    recarrega a página) as que mudaram. Não depende do agendamento do GitHub, que
    em repositórios com pouca atividade chega a falhar horas seguidas."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select tipo from fontes_google_sheets
                    where team_id = %s and ativo
                      and (ultima_sincronizacao is null or ultima_sincronizacao < now() - make_interval(mins => %s))
                    """,
                    (team_id, minutos),
                )
                tipos = [r[0] for r in cur.fetchall()]
    except Exception:
        return {"sincronizadas": 0}
    feitas = 0
    for tipo in tipos:
        try:
            r = sincronizar(team_id, user_id, tipo, so_se_mudou=True)
            if not r.get("sem_alteracoes"):
                feitas += 1
        except Exception:
            pass  # o erro fica registado no cartão da página Importar
    return {"sincronizadas": feitas}
