"""AI Performance Assistant — orquestração.

Monta um retrato estruturado (JSON) da equipa a partir dos serviços que já
calculam tudo (avisos, exposição, carga externa, match benchmark, análise do
microciclo) e envia-o à Claude API com o system prompt do assistente. Só dados
agregados/estruturados + primeiros nomes são enviados — nunca credenciais nem o
email do utilizador.
"""
from __future__ import annotations

import json
import os

from app.services.ia_prompt import SYSTEM_PROMPT

# Modelo por omissão: Claude Haiku 4.5 — simples, rápido e barato, adequado a
# uma ferramenta interativa. Configurável por ANTHROPIC_MODEL (ex.:
# claude-sonnet-5 ou claude-opus-5 para respostas mais elaboradas).
MODELO = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

_PEDIDO_RESUMO = (
    "Gera um RESUMO PARA O TREINADOR (COACHING STAFF SUMMARY MODE): estado da "
    "equipa (🟢/🟡/🟠/🔴) e os 3–5 pontos mais importantes, terminando com o "
    "ponto principal a merecer atenção do staff. Sê conciso e prático."
)


def montar_snapshot(team_id: str, limites: dict | None = None) -> dict:
    """Retrato estruturado da equipa para o assistente. Reutiliza os serviços de
    cálculo existentes; falha graciosamente por secção."""
    from app.services.alertas_service import construir_avisos_dashboard, obter_exposicao_semana
    from app.services.analise_service import obter_analise
    from app.services.carga_externa_service import obter_carga_externa
    from app.services.dados_equipa import carregar_df_equipa
    from app.services.match_benchmark_service import obter_match_benchmark

    def _tenta(fn, default):
        try:
            return fn()
        except Exception:
            return default

    df = _tenta(lambda: carregar_df_equipa(team_id), None)
    if df is None or df.empty:
        return {"tem_dados": False}

    avisos = _tenta(lambda: construir_avisos_dashboard(df, limites), [])
    exposicao = _tenta(lambda: obter_exposicao_semana(df, limites), {})
    carga = _tenta(lambda: obter_carga_externa(team_id), {})
    match = _tenta(lambda: obter_match_benchmark(team_id), {})
    analise = _tenta(lambda: obter_analise(team_id, limites=limites), {})

    # Só o que interessa para a interpretação — mantém o payload compacto.
    avisos_relevantes = [a for a in avisos if a.get("status") != "normal"]
    contagem = {"normal": 0, "attention": 0, "high-attention": 0}
    for a in avisos:
        contagem[a.get("status", "normal")] = contagem.get(a.get("status", "normal"), 0) + 1

    return {
        "tem_dados": True,
        "estado_plantel": contagem,
        "avisos": avisos_relevantes,
        "exposicao_semana": exposicao if exposicao.get("tem_dados") else {"tem_dados": False, "motivo": exposicao.get("motivo")},
        "carga_externa": {
            "sessao_recente": carga.get("sessao_recente"),
            "kpis": carga.get("kpis", []),
        } if carga.get("tem_dados") else {"tem_dados": False},
        "match_benchmark": {
            "data_treino": match.get("data_treino"),
            "n_jogos": match.get("n_jogos"),
            "equipa": match.get("equipa", []),
            "posicoes": match.get("posicoes", []),
        } if match.get("tem_dados") else {"tem_dados": False, "motivo": "sem jogos ou sem treinos de referência"},
        "analise_microciclo": {
            "microciclo": analise.get("microciclo_selecionado"),
            "carga_interna_media": analise.get("carga_interna_media"),
            "monotonia_media": analise.get("monotonia_media"),
            "strain_medio": analise.get("strain_medio"),
            "carga_por_dia": analise.get("carga_por_dia", []),
            "ranking_carga": analise.get("ranking_carga", [])[:8],
            "alertas": analise.get("alertas", {}),
        } if analise.get("tem_dados") else {"tem_dados": False},
        "limiares_ativos": limites or {},
    }


def _chamar_claude(pergunta: str, snapshot: dict, historico: list[dict] | None = None) -> str:
    import anthropic

    client = anthropic.Anthropic()
    contexto = json.dumps(snapshot, ensure_ascii=False, default=str)
    mensagens: list[dict] = list(historico or [])
    mensagens.append({
        "role": "user",
        "content": f"DADOS ESTRUTURADOS DA EQUIPA (JSON):\n{contexto}\n\nPEDIDO:\n{pergunta}",
    })
    # Sem output_config.effort: o Haiku 4.5 (modelo por omissão) não o suporta.
    resposta = client.messages.create(
        model=MODELO,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=mensagens,
    )
    return next((b.text for b in resposta.content if b.type == "text"), "").strip()


_SEM_CHAVE = (
    "A assistente de IA não está configurada no servidor: falta a variável "
    "ANTHROPIC_API_KEY. Define-a no serviço da API (Render → Environment) e faz "
    "um redeploy. A página funciona, mas não consegue falar com o modelo sem a chave."
)


def _tem_credencial() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _erro_amigavel(exc: Exception) -> str | None:
    """Traduz erros da SDK num aviso legível; devolve None se não for reconhecido."""
    try:
        import anthropic
    except Exception:
        return "A assistente de IA não está instalada no servidor (pacote 'anthropic' em falta). Confirma o deploy da API."

    if isinstance(exc, anthropic.AuthenticationError):
        return "A chave da API (ANTHROPIC_API_KEY) é inválida ou a conta não tem créditos. Verifica a chave e o saldo em console.anthropic.com."
    if isinstance(exc, anthropic.RateLimitError):
        return "A assistente está temporariamente sem capacidade (limite de pedidos). Tenta novamente daqui a pouco."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Não foi possível ligar ao serviço de IA a partir do servidor. Verifica a ligação de rede."
    # Erro base da SDK — inclui o caso de a chave estar em falta na construção do cliente.
    if isinstance(exc, anthropic.AnthropicError):
        return _SEM_CHAVE
    return None


def perguntar(team_id: str, pergunta: str, historico: list[dict] | None = None, limites: dict | None = None) -> dict:
    if not _tem_credencial():
        return {"ok": False, "erro": _SEM_CHAVE}

    snapshot = montar_snapshot(team_id, limites)
    if not snapshot.get("tem_dados"):
        return {"ok": True, "resposta": "Ainda não há dados carregados para esta equipa, por isso não há nada para analisar. Importa sessões de GPS primeiro."}
    try:
        texto = _chamar_claude(pergunta, snapshot, historico)
        return {"ok": True, "resposta": texto}
    except Exception as exc:  # noqa: BLE001 — queremos devolver mensagem amigável
        amigavel = _erro_amigavel(exc)
        if amigavel:
            return {"ok": False, "erro": amigavel}
        raise


def resumo_staff(team_id: str, limites: dict | None = None) -> dict:
    return perguntar(team_id, _PEDIDO_RESUMO, historico=None, limites=limites)
