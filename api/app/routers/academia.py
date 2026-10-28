"""Academia: estrutura escalões × épocas e equipas do utilizador."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.db import get_conn
from app.core.security import UtilizadorAtual, obter_utilizador_atual
from app.services import academia_service as acad

router = APIRouter()


def _equipas_simples(user_id: str) -> list[dict]:
    """Antes da migração 0009: só as equipas, para o seletor funcionar."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select t.id, t.nome from teams t join team_members tm on tm.team_id = t.id where tm.user_id = %s order by t.nome",
                (user_id,),
            )
            return [{"team_id": str(i), "nome": n, "rotulo": n, "escalao": None, "epoca": None,
                     "academia_id": None, "n_jogadores": None, "ultima_sessao": None} for i, n in cur.fetchall()]


@router.get("/api/academia")
def estrutura(utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        return {"disponivel": False, "motivo": acad.MSG_MIGRACAO, "academias": [],
                "equipas": _equipas_simples(utilizador.user_id), "escaloes": acad.ESCALOES, "epoca_atual": acad.epoca_atual()}
    return acad.obter_estrutura(utilizador.user_id)


class NovaEquipa(BaseModel):
    escalao: str
    epoca: str
    copiar_de: str | None = None


@router.post("/api/academia/{academia_id}/equipas")
def nova_equipa(academia_id: str, body: NovaEquipa, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, acad.MSG_MIGRACAO)
    try:
        return acad.criar_equipa(utilizador.user_id, academia_id, body.escalao, body.epoca, body.copiar_de)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class EditarEquipa(BaseModel):
    escalao: str | None = None
    epoca: str | None = None


@router.patch("/api/academia/equipas/{team_id}")
def editar_equipa(team_id: str, body: EditarEquipa, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not acad.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, acad.MSG_MIGRACAO)
    try:
        return acad.atualizar_equipa(utilizador.user_id, team_id, body.escalao, body.epoca)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


# ── Ficha longitudinal do atleta ─────────────────────────────────────────────
from app.services import ficha_atleta_service as ficha  # noqa: E402


def _ficha_disponivel():
    if not ficha.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, ficha.MSG_MIGRACAO)


@router.get("/api/academia/atletas")
def atletas(utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not ficha.disponivel():
        return {"disponivel": False, "motivo": ficha.MSG_MIGRACAO, "atletas": [], "catalogo": ficha.CATALOGO}
    return {"disponivel": True, **ficha.listar_atletas(utilizador.user_id)}


@router.get("/api/academia/atletas/{atleta_id}")
def ficha_atleta(atleta_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _ficha_disponivel()
    try:
        return ficha.obter_ficha(utilizador.user_id, atleta_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


class AtletaBody(BaseModel):
    data_nascimento: str | None = None
    posicao: str | None = None
    pe_dominante: str | None = None
    altura_pai_cm: float | None = None
    altura_mae_cm: float | None = None
    altura_pais_medida: bool | None = None


@router.patch("/api/academia/atletas/{atleta_id}")
def editar_atleta(atleta_id: str, body: AtletaBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _ficha_disponivel()
    try:
        return ficha.atualizar_atleta(utilizador.user_id, atleta_id, body.data_nascimento, body.posicao, body.pe_dominante,
                                      body.altura_pai_cm, body.altura_mae_cm, body.altura_pais_medida)
    except PermissionError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


class AvaliacaoBody(BaseModel):
    data: str
    valores: dict
    team_id: str | None = None
    notas: str | None = None


@router.post("/api/academia/atletas/{atleta_id}/avaliacoes")
def nova_avaliacao(atleta_id: str, body: AvaliacaoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _ficha_disponivel()
    try:
        return ficha.registar_avaliacao(utilizador.user_id, atleta_id, body.data, body.valores, body.team_id, body.notas)
    except PermissionError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.delete("/api/academia/avaliacoes/{avaliacao_id}")
def apagar_avaliacao(avaliacao_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _ficha_disponivel()
    return ficha.apagar_avaliacao(utilizador.user_id, avaliacao_id)


# ── Plantel: atletas adicionados um a um, em uma ou várias equipas ───────────
def _executar(fn, *args):
    import psycopg2
    _ficha_disponivel()
    try:
        return fn(*args)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except psycopg2.Error as e:
        # Mostra a causa (ex.: migração por aplicar) em vez de um erro genérico.
        detalhe = (getattr(e, "pgerror", None) or str(e)).strip().splitlines()[0]
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Erro na base de dados: {detalhe}")


class NovoAtleta(BaseModel):
    nome: str
    data_nascimento: str | None = None
    posicao: str | None = None
    pe_dominante: str | None = None
    equipas: list[str]


@router.post("/api/academia/{academia_id}/atletas")
def novo_atleta(academia_id: str, body: NovoAtleta, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _executar(acad.adicionar_atleta, utilizador.user_id, academia_id, body.nome, body.data_nascimento,
                     body.posicao, body.pe_dominante, body.equipas)


class EquipaBody(BaseModel):
    team_id: str


@router.post("/api/academia/atletas/{atleta_id}/equipas")
def atleta_em_equipa(atleta_id: str, body: EquipaBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _executar(acad.adicionar_a_equipa, utilizador.user_id, atleta_id, body.team_id)


@router.delete("/api/academia/atletas/{atleta_id}/equipas/{team_id}")
def atleta_sai_equipa(atleta_id: str, team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _executar(acad.remover_de_equipa, utilizador.user_id, atleta_id, team_id)


@router.delete("/api/academia/atletas/{atleta_id}")
def apagar_atleta(atleta_id: str, tudo: bool = False, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """tudo=true: apagamento total (RGPD) — sessões, testes, lesões, jogos…"""
    return _executar(acad.apagar_atleta, utilizador.user_id, atleta_id, tudo)



# ── Separador de equipa: testes do plantel ───────────────────────────────────
@router.get("/api/academia/equipas/{team_id}/testes")
def testes_equipa(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    _ficha_disponivel()
    try:
        return ficha.obter_testes_equipa(utilizador.user_id, team_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


class TestesEquipaBody(BaseModel):
    data: str
    linhas: list[dict]
    momento: int | None = None


@router.post("/api/academia/equipas/{team_id}/testes")
def registar_testes_equipa(team_id: str, body: TestesEquipaBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _executar(ficha.registar_testes_equipa, utilizador.user_id, team_id, body.data, body.linhas, body.momento)


@router.get("/api/academia/equipas/{team_id}/relatorio")
def relatorio_equipa(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Testes da época por momento (T1–T4): base dos relatórios por teste e individual."""
    return _executar(ficha.relatorio_epoca, utilizador.user_id, team_id)


# ── Biblioteca de exercícios ─────────────────────────────────────────────────
class ExercicioBody(BaseModel):
    nome: str
    categoria: str | None = None
    descricao: str | None = None
    formato: str | None = None
    espaco: str | None = None
    duracao_min: int | None = None
    manual: dict = {}


def _ex(fn, *args):
    from app.services import exercicios_service as exs
    if not exs.disponivel():
        if fn == "listar":
            return {"disponivel": False, "motivo": exs.MSG_MIGRACAO, "exercicios": [], "categorias": exs.CATEGORIAS, "metricas": []}
        raise HTTPException(status.HTTP_409_CONFLICT, exs.MSG_MIGRACAO)
    return _executar(getattr(exs, fn), *args)


@router.get("/api/academia/exercicios")
def exercicios(team_id: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Biblioteca de exercícios + exercícios vistos no GPS, com a carga típica por minuto."""
    return _ex("listar", utilizador.user_id, team_id)


@router.post("/api/academia/exercicios")
def novo_exercicio(body: ExercicioBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _ex("criar", utilizador.user_id, body.model_dump())


@router.put("/api/academia/exercicios/{ex_id}")
def editar_exercicio(ex_id: str, body: ExercicioBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _ex("atualizar", utilizador.user_id, ex_id, body.model_dump())


@router.delete("/api/academia/exercicios/{ex_id}")
def apagar_exercicio(ex_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _ex("apagar", utilizador.user_id, ex_id)


@router.get("/api/academia/comparacao")
def comparacao_equipas(epoca: str | None = None, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Escalões da mesma época lado a lado nos mesmos testes, com o estado
    maturacional e as referências por idade e por maturação de cada atleta."""
    from app.services.referencias_service import comparar_equipas
    return _executar(comparar_equipas, utilizador.user_id, epoca)



# ── Jogos da equipa (minutos, contexto, golos, assistências) ─────────────────
from fastapi import File, Form, UploadFile  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402

from app.services import jogos_service as jogos  # noqa: E402


def _jogos(fn, *args):
    if not jogos.disponivel():
        raise HTTPException(status.HTTP_409_CONFLICT, jogos.MSG_MIGRACAO)
    return _executar(fn, *args)


@router.get("/api/academia/equipas/{team_id}/jogos")
def jogos_equipa(team_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    if not jogos.disponivel():
        return {"disponivel": False, "motivo": jogos.MSG_MIGRACAO}
    return {"disponivel": True, **_executar(jogos.listar, utilizador.user_id, team_id)}


@router.get("/api/academia/equipas/{team_id}/jogos/{jogo_id}")
def jogo(team_id: str, jogo_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _jogos(jogos.obter_jogo, utilizador.user_id, team_id, jogo_id)


class JogoBody(BaseModel):
    jogo: dict
    participacoes: list[dict] = []


@router.post("/api/academia/equipas/{team_id}/jogos")
def novo_jogo(team_id: str, body: JogoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _jogos(jogos.guardar_jogo, utilizador.user_id, team_id, body.jogo, body.participacoes, None)


@router.put("/api/academia/equipas/{team_id}/jogos/{jogo_id}")
def editar_jogo(team_id: str, jogo_id: str, body: JogoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _jogos(jogos.guardar_jogo, utilizador.user_id, team_id, body.jogo, body.participacoes, jogo_id)


@router.delete("/api/academia/equipas/{team_id}/jogos/{jogo_id}")
def apagar_jogo(team_id: str, jogo_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _jogos(jogos.apagar_jogo, utilizador.user_id, team_id, jogo_id)


@router.post("/api/academia/equipas/{team_id}/jogos-importar")
async def importar_jogos(team_id: str, ficheiro: UploadFile = File(...), duracao_min: int = Form(80),
                         utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    conteudo = await ficheiro.read()
    if len(conteudo) > 5_000_000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ficheiro demasiado grande (máx. 5 MB).")
    return await run_in_threadpool(_jogos, jogos.importar, utilizador.user_id, team_id, conteudo, ficheiro.filename or "", duracao_min)



# ── Proteção de dados (RGPD) ─────────────────────────────────────────────────
class ConsentimentoBody(BaseModel):
    data: str | None = None
    por: str | None = None
    notas: str | None = None


@router.put("/api/academia/atletas/{atleta_id}/consentimento")
def consentimento(atleta_id: str, body: ConsentimentoBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    return _executar(ficha.registar_consentimento, utilizador.user_id, atleta_id, body.data, body.por, body.notas)


@router.get("/api/academia/atletas/{atleta_id}/exportar")
def exportar(atleta_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """Todos os dados do atleta num JSON (direito de acesso e portabilidade)."""
    import json as _json

    from fastapi.responses import Response
    dados = _executar(ficha.exportar_atleta, utilizador.user_id, atleta_id)
    nome = "".join(ch for ch in str(dados["atleta"].get("nome", "atleta")) if ch.isalnum() or ch in " -_").strip().replace(" ", "_")
    return Response(_json.dumps(dados, default=str, ensure_ascii=False, indent=1), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="dados_{nome}.json"'})


# ── Protocolo de limites da academia ────────────────────────────────────────
class ProtocoloBody(BaseModel):
    ativo: bool
    limpar_escalao: str | None = None


@router.get("/api/academia/{academia_id}/protocolo")
def ver_protocolo(academia_id: str, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    from app.services.limites_service import obter_protocolo
    try:
        return obter_protocolo(academia_id, utilizador.user_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))


@router.put("/api/academia/{academia_id}/protocolo")
def mudar_protocolo(academia_id: str, body: ProtocoloBody, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    from app.services.limites_service import definir_protocolo
    try:
        return definir_protocolo(academia_id, utilizador.user_id, body.ativo, body.limpar_escalao)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))


@router.get("/api/academia/{academia_id}/qualidade-dados")
def qualidade_dados(academia_id: str, meses: int = 3, utilizador: UtilizadorAtual = Depends(obter_utilizador_atual)):
    """% de wellness, PSE e GPS registados por equipa e por mês."""
    from app.services.qualidade_dados_service import obter
    try:
        return obter(academia_id, utilizador.user_id, meses)
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
