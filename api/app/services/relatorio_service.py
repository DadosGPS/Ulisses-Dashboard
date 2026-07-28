"""Relatório do Dia — Fase 9 do plano de migração (exportação PDF).

Duas partes pedidas pelo utilizador:
1. Texto narrativo gerado automaticamente, no mesmo espírito do exemplo
   trabalhado no curso "O Uso do GPS no Futebol" (S. Querido, Aula 20):
   um parágrafo corrido — não uma lista — que liga contexto, dados,
   comparação e ação, e que o treinador pode editar antes de exportar.
2. PDF com gráficos (barras HTML/CSS, renderizadas pelo WeasyPrint —
   não há execução de JS num PDF, por isso não dá para usar Plotly aqui)
   de Distância Total, Acc, Dcc, Vel. Máxima e HSR da sessão mais recente.

Reutiliza gerar_resumo_5w1h() para o contexto (Dia MD, comparação vs
histórico) — o texto narrativo é gerado a partir dos mesmos dados que já
alimentam o cartão 5W+1H do Dashboard.
"""
from datetime import datetime
from html import escape

import pandas as pd

from app.services.dados_equipa import carregar_df_equipa
from app.services.resumo_5w1h import PERFIL_DIA_MD, gerar_resumo_5w1h

try:
    from weasyprint import HTML
    WEASYPRINT_DISPONIVEL = True
except Exception:
    WEASYPRINT_DISPONIVEL = False

MESES_PT = {
    "January": "janeiro", "February": "fevereiro", "March": "março", "April": "abril",
    "May": "maio", "June": "junho", "July": "julho", "August": "agosto",
    "September": "setembro", "October": "outubro", "November": "novembro", "December": "dezembro",
}

METRICAS_GRAFICO = [
    {"col": "Distância Total (m)", "label": "Distância Total", "unidade": "m", "cor": "#2563eb", "casas": 0},
    {"col": "Acc (n)", "label": "Acelerações", "unidade": "", "cor": "#14b8a6", "casas": 0},
    {"col": "Dcc (n)", "label": "Desacelerações", "unidade": "", "cor": "#10b981", "casas": 0},
    {"col": "Vel. Máx (km/h)", "label": "Velocidade Máxima", "unidade": " km/h", "cor": "#8b5cf6", "casas": 1},
    {"col": "HSR (m)", "label": "HSR", "unidade": "m", "cor": "#f59e0b", "casas": 0},
]


def _primeiro_nome_metrica(nome_completo: str) -> str:
    return nome_completo.split(" (")[0]


def gerar_texto_narrativo(resumo: dict | None) -> str:
    """Parágrafo corrido — contexto, dados, comparação, julgamento e ação —
    em vez de uma lista de números soltos (ver DIKW / 5W+1H no material do
    curso). Devolvido como rascunho editável, não como texto final."""
    if not resumo:
        return "Ainda não há dados suficientes para gerar um resumo desta sessão."

    dia_md = resumo.get("dia_md")
    perfil = PERFIL_DIA_MD.get(dia_md, {})
    foco = perfil.get("foco", "monitorização de carga")
    n_jog = resumo["who"]["n_jogadores"]

    try:
        dt = datetime.fromisoformat(resumo["data"])
        mes_pt = MESES_PT.get(dt.strftime("%B"), dt.strftime("%B"))
        data_fmt = f"{dt.day} de {mes_pt} de {dt.year}"
    except Exception:
        data_fmt = resumo["data"]

    partes = []

    if dia_md == "MD":
        partes.append(f"Na sessão de {data_fmt}, dia de jogo, participaram {n_jog} jogadores.")
    elif dia_md:
        partes.append(
            f"Na sessão de {data_fmt} ({dia_md}), com foco em {foco}, participaram {n_jog} jogadores."
        )
    else:
        partes.append(f"Na sessão de {data_fmt} participaram {n_jog} jogadores.")

    what = resumo.get("what", [])
    desvios = [c for c in what if c["variacao_pct"] is not None and abs(c["variacao_pct"]) >= 10]
    if desvios:
        frases = []
        for c in desvios:
            sinal = "acima" if c["variacao_pct"] >= 0 else "abaixo"
            frases.append(f"{_primeiro_nome_metrica(c['metrica'])} {sinal} da média em {abs(c['variacao_pct']):.0f}%")
        ref = f"sessões {dia_md}" if dia_md else "sessões semelhantes"
        partes.append(f"Face à média histórica de {ref}, destacam-se: {', '.join(frases)}.")
    else:
        partes.append("Os valores registados mantiveram-se em linha com a média histórica de sessões semelhantes.")

    ci = next((c for c in what if c["metrica"] == "Carga Interna"), None)
    if ci and ci["variacao_pct"] is not None:
        if ci["variacao_pct"] >= 15:
            partes.append(
                "Esta exposição de carga acima do habitual pode favorecer estímulos de adaptação, "
                "mas justifica atenção redobrada aos sinais de fadiga nos próximos dias."
            )
        elif ci["variacao_pct"] <= -15:
            partes.append(
                "A carga interna ficou claramente abaixo do padrão habitual para este tipo de sessão — "
                "adequado em fases de recuperação, mas vale confirmar se foi intencional."
            )
        else:
            partes.append("A carga interna manteve-se dentro do intervalo esperado para este tipo de sessão.")

    if dia_md == "MD-1":
        partes.append("Com o jogo à porta, o foco deve manter-se na ativação e na preservação de energia.")
    elif dia_md in ("MD+1", "MD+2"):
        partes.append("Nos próximos dias, prioridade à recuperação individualizada dos jogadores com maior exposição.")
    elif dia_md == "MD":
        partes.append("Nas próximas 24 horas, foco na recuperação imediata pós-jogo.")
    else:
        partes.append("Recomenda-se monitorizar a resposta individual dos jogadores nas próximas 24 a 48 horas.")

    return " ".join(partes)


def obter_texto_narrativo(team_id: str) -> dict:
    df = carregar_df_equipa(team_id)
    resumo = gerar_resumo_5w1h(df)
    return {"texto": gerar_texto_narrativo(resumo), "data": resumo["data"] if resumo else None}


def _barras_html(titulo: str, cor: str, unidade: str, casas: int, dados: list[tuple[str, float]]) -> str:
    if not dados:
        return f'<div class="seccao"><h2>{escape(titulo)}</h2><p class="vazio">Sem dados para esta métrica nesta sessão.</p></div>'

    max_val = dados[0][1] or 1
    linhas = ""
    for jogador, valor in dados:
        largura = max(3, min(100, (valor / max_val) * 100))
        linhas += (
            f'<div class="barra-linha">'
            f'<div class="barra-nome">{escape(jogador)}</div>'
            f'<div class="barra-track"><div class="barra-fill" style="width:{largura:.0f}%;background:{cor}"></div></div>'
            f'<div class="barra-valor">{valor:,.{casas}f}{unidade}</div>'
            f'</div>'
        )
    return f'<div class="seccao"><h2>{escape(titulo)}</h2><div class="barras">{linhas}</div></div>'


def gerar_html_relatorio(team_id: str, texto: str) -> str:
    df = carregar_df_equipa(team_id)
    resumo = gerar_resumo_5w1h(df)

    data_str = resumo["data"] if resumo else "—"
    dia_md = resumo.get("dia_md") if resumo else None
    n_jog = resumo["who"]["n_jogadores"] if resumo else 0

    seccoes = ""
    if resumo and "Data" in df.columns:
        ultima_data = pd.to_datetime(resumo["data"]).date()
        sessao = df[df["Data"].dt.date == ultima_data]
        for cfg in METRICAS_GRAFICO:
            if cfg["col"] not in sessao.columns:
                continue
            serie = sessao.groupby("Jogador")[cfg["col"]].mean().dropna().sort_values(ascending=False)
            dados = [(j, float(v)) for j, v in serie.items()]
            seccoes += _barras_html(cfg["label"], cfg["cor"], cfg["unidade"], cfg["casas"], dados)

    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Relatório do Dia — {escape(data_str)}</title>
<style>
  @page {{
    size: A4;
    margin: 20mm 18mm;
    @bottom-right {{ content: counter(page) " / " counter(pages); font-size: 8.5pt; color: #94a3b8; }}
    @bottom-left {{ content: "LoadMonitorSystem"; font-size: 8.5pt; color: #94a3b8; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", Arial, sans-serif;
    color: #0f172a;
    font-size: 10.5pt;
    line-height: 1.5;
    margin: 0;
  }}
  .cabecalho {{
    border-bottom: 3px solid #e63946;
    padding-bottom: 14px;
    margin-bottom: 20px;
  }}
  .cabecalho .eyebrow {{
    font-size: 8pt;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 4px;
  }}
  .cabecalho h1 {{
    font-size: 20pt;
    margin: 0 0 4px;
    color: #0f172a;
  }}
  .cabecalho .meta {{
    font-size: 9.5pt;
    color: #64748b;
  }}
  .badge {{
    display: inline-block;
    font-family: monospace;
    font-weight: 700;
    font-size: 9pt;
    color: #e63946;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
    padding: 2px 8px;
    margin-left: 8px;
  }}
  .resumo {{
    background: #f8fafc;
    border-left: 3px solid #e63946;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-bottom: 26px;
    font-size: 10.5pt;
    text-align: justify;
  }}
  .resumo h2 {{
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #e63946;
    margin: 0 0 8px;
  }}
  .seccao {{
    margin-bottom: 20px;
    page-break-inside: avoid;
  }}
  .seccao h2 {{
    font-size: 11.5pt;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 5px;
    margin: 0 0 10px;
  }}
  .vazio {{ color: #94a3b8; font-size: 9.5pt; font-style: italic; }}
  .barra-linha {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
  }}
  .barra-nome {{
    width: 110px;
    font-size: 8.5pt;
    color: #334155;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .barra-track {{
    flex: 1;
    background: #f1f5f9;
    border-radius: 4px;
    height: 13px;
    overflow: hidden;
  }}
  .barra-fill {{ height: 100%; border-radius: 4px; }}
  .barra-valor {{
    min-width: 56px;
    text-align: right;
    font-size: 8.5pt;
    font-weight: 700;
    color: #0f172a;
  }}
  .rodape {{
    margin-top: 30px;
    font-size: 8pt;
    color: #94a3b8;
    border-top: 1px solid #e2e8f0;
    padding-top: 8px;
  }}
</style>
</head>
<body>
  <div class="cabecalho">
    <div class="eyebrow">LoadMonitorSystem · Relatório do Dia</div>
    <h1>Resumo da Sessão{f'<span class="badge">{escape(dia_md)}</span>' if dia_md else ""}</h1>
    <div class="meta">{escape(data_str)} · {n_jog} jogadores</div>
  </div>

  <div class="resumo">
    <h2>Resumo — Modelo 5W+1H</h2>
    <p>{escape(texto)}</p>
  </div>

  {seccoes}

  <div class="rodape">Gerado pelo LoadMonitorSystem em {gerado_em}</div>
</body>
</html>"""


def gerar_pdf_relatorio(team_id: str, texto: str) -> bytes | None:
    if not WEASYPRINT_DISPONIVEL:
        return None
    try:
        html_str = gerar_html_relatorio(team_id, texto)
        return HTML(string=html_str).write_pdf()
    except Exception as e:
        print(f"[relatorio_service.gerar_pdf_relatorio] Falhou: {e}")
        return None
