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

from utils.calculos import DIAS_MD_ORDEM, calcular_acwr_global, calcular_monotonia_strain

from app.services.analise_service import obter_analise
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


# ── Relatório Semanal — complementa o Relatório do Dia acima ────────────────
# O Relatório do Dia cobre uma sessão (Distância/Acc/Dcc/VelMáx/HSR); a
# página Análise passou a ser semanal (carga, monotonia, strain, ranking),
# por isso fazia sentido também um PDF que espelhasse essa vista, não só a
# diária — pedido explícito do preparador físico.

def _texto_narrativo_semanal(analise: dict) -> str:
    if not analise.get("tem_dados") or analise.get("carga_interna_media") is None:
        return "Ainda não há dados suficientes para gerar um resumo desta semana."

    mc = analise.get("microciclo_selecionado")
    carga = analise["carga_interna_media"]
    mono = analise.get("monotonia_media")
    strain = analise.get("strain_medio")

    partes = [f"No microciclo {mc}, a carga interna semanal total média por atleta foi de {carga:.0f} UA."]

    if mono is not None:
        if mono > 2:
            partes.append(
                f"A monotonia da equipa ({mono:.2f}) está na zona de risco (>2, Foster 1998) — a carga diária "
                "variou pouco ao longo da semana, o que aumenta o risco de lesão mesmo sem um pico de carga isolado."
            )
        elif mono > 1.5:
            partes.append(
                f"A monotonia da equipa ({mono:.2f}) está num nível de atenção — vale a pena introduzir mais "
                "variabilidade entre dias de treino nas próximas semanas."
            )
        else:
            partes.append(f"A monotonia da equipa ({mono:.2f}) está dentro de um intervalo saudável, com boa variabilidade entre dias.")

    if strain is not None:
        partes.append(f"O strain médio (carga × monotonia) foi de {strain:.0f}.")

    maximo, minimo = analise.get("carga_maxima"), analise.get("carga_minima")
    if maximo and minimo and maximo["jogador"] != minimo["jogador"]:
        partes.append(
            f"{maximo['jogador']} teve a maior carga semanal ({maximo['valor']:.0f} UA), "
            f"e {minimo['jogador']} a menor ({minimo['valor']:.0f} UA)."
        )

    return " ".join(partes)


def obter_texto_narrativo_semanal(team_id: str, microciclo: int | None) -> dict:
    analise = obter_analise(team_id, microciclo)
    return {"texto": _texto_narrativo_semanal(analise), "microciclo": analise.get("microciclo_selecionado")}


def _analise_geral_semana(df: pd.DataFrame, microciclo: int | None) -> dict:
    """Destaques da semana pedidos pelo utilizador: por dia, quem teve mais
    e menos carga; e para a semana toda, quem termina com o ACWR e a
    monotonia mais altos/baixos — os quatro extremos que mais interessam
    ao preparador físico ao rever uma semana."""
    vazio = {"por_dia": [], "acwr_maior": None, "acwr_menor": None, "monotonia_maior": None, "monotonia_menor": None}
    if df.empty or "Microciclo (Nr)" not in df.columns:
        return vazio

    df_semana = df[df["Microciclo (Nr)"] == microciclo] if microciclo is not None else df
    if df_semana.empty:
        return vazio

    por_dia = []
    if {"Dia MD", "Carga Interna", "Jogador"}.issubset(df_semana.columns):
        for dia in DIAS_MD_ORDEM:
            sub = df_semana[df_semana["Dia MD"] == dia].dropna(subset=["Carga Interna", "Jogador"])
            if sub.empty:
                continue
            por_jogador = sub.groupby("Jogador")["Carga Interna"].sum()
            por_dia.append({
                "dia_md": dia,
                "maior": {"jogador": por_jogador.idxmax(), "valor": round(float(por_jogador.max()), 0)},
                "menor": {"jogador": por_jogador.idxmin(), "valor": round(float(por_jogador.min()), 0)},
            })

    # ACWR "no fim dessa semana" — recalcula com o histórico só até à
    # última data dessa semana (não a mais recente da equipa toda), para
    # que ao rever uma semana passada o ACWR mostrado seja o de então.
    acwr_maior = acwr_menor = None
    if "Data" in df_semana.columns and df_semana["Data"].notna().any():
        data_fim = df_semana["Data"].max()
        jogadores_semana = set(df_semana["Jogador"].dropna().unique())
        acwr_dict = calcular_acwr_global(df[df["Data"] <= data_fim])
        validos = {j: d["acwr"] for j, d in acwr_dict.items() if j in jogadores_semana and pd.notna(d["acwr"])}
        if validos:
            j_max, j_min = max(validos, key=validos.get), min(validos, key=validos.get)
            acwr_maior = {"jogador": j_max, "valor": round(float(validos[j_max]), 2)}
            acwr_menor = {"jogador": j_min, "valor": round(float(validos[j_min]), 2)}

    monotonia_maior = monotonia_menor = None
    mono = calcular_monotonia_strain(df_semana)
    if not mono.empty:
        i_max, i_min = mono["Monotonia"].idxmax(), mono["Monotonia"].idxmin()
        monotonia_maior = {"jogador": mono.loc[i_max, "Jogador"], "valor": round(float(mono.loc[i_max, "Monotonia"]), 2)}
        monotonia_menor = {"jogador": mono.loc[i_min, "Jogador"], "valor": round(float(mono.loc[i_min, "Monotonia"]), 2)}

    return {
        "por_dia": por_dia,
        "acwr_maior": acwr_maior, "acwr_menor": acwr_menor,
        "monotonia_maior": monotonia_maior, "monotonia_menor": monotonia_menor,
    }


def gerar_html_relatorio_semanal(team_id: str, microciclo: int | None, texto: str | None = None) -> str:
    analise = obter_analise(team_id, microciclo)
    if texto is None:
        texto = _texto_narrativo_semanal(analise)

    mc = analise.get("microciclo_selecionado")
    geral = _analise_geral_semana(carregar_df_equipa(team_id), mc)

    seccoes = _barras_html(
        "Carga Média por Dia (UA)", "#e63946", "", 0,
        [(d["dia_md"], d["carga_media"]) for d in analise.get("carga_por_dia", [])],
    )
    seccoes += _barras_html(
        "Ranking de Atletas por Carga Semanal (UA)", "#2563eb", "", 0,
        [(r["jogador"], r["valor"]) for r in analise.get("ranking_carga", [])],
    )

    def _fmt(v, casas=0):
        return f"{v:,.{casas}f}".replace(",", " ") if v is not None else "—"

    kpis_html = f"""
    <div class="kpis">
      <div class="kpi"><div class="kpi-label">Carga Semanal Média</div><div class="kpi-valor">{_fmt(analise.get('carga_interna_media'))} <span class="kpi-unidade">UA</span></div></div>
      <div class="kpi"><div class="kpi-label">Monotonia</div><div class="kpi-valor">{_fmt(analise.get('monotonia_media'), 2)}</div></div>
      <div class="kpi"><div class="kpi-label">Strain</div><div class="kpi-valor">{_fmt(analise.get('strain_medio'))}</div></div>
    </div>"""

    def _destaque(label: str, item: dict | None, casas=0) -> str:
        if item is None:
            return f'<div class="destaque"><div class="destaque-label">{escape(label)}</div><div class="vazio">Sem dados</div></div>'
        return (
            f'<div class="destaque"><div class="destaque-label">{escape(label)}</div>'
            f'<div class="destaque-jogador">{escape(item["jogador"])}</div>'
            f'<div class="destaque-valor">{_fmt(item["valor"], casas)}</div></div>'
        )

    destaques_html = f"""
    <div class="seccao">
      <h2>Destaques da Semana</h2>
      <div class="destaques">
        {_destaque("ACWR mais alto", geral["acwr_maior"], 2)}
        {_destaque("ACWR mais baixo", geral["acwr_menor"], 2)}
        {_destaque("Monotonia mais alta", geral["monotonia_maior"], 2)}
        {_destaque("Monotonia mais baixa", geral["monotonia_menor"], 2)}
      </div>
    </div>"""

    linhas_dias = "".join(
        f'<tr><td>{escape(d["dia_md"])}</td>'
        f'<td>{escape(d["maior"]["jogador"])} <span class="tabela-valor">({_fmt(d["maior"]["valor"])} UA)</span></td>'
        f'<td>{escape(d["menor"]["jogador"])} <span class="tabela-valor">({_fmt(d["menor"]["valor"])} UA)</span></td></tr>'
        for d in geral["por_dia"]
    )
    analise_dia_html = (
        f"""
    <div class="seccao">
      <h2>Análise por Dia — Maior e Menor Carga</h2>
      <table class="tabela-dias">
        <thead><tr><th>Dia</th><th>Maior carga</th><th>Menor carga</th></tr></thead>
        <tbody>{linhas_dias}</tbody>
      </table>
    </div>"""
        if geral["por_dia"]
        else ""
    )

    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>Relatório Semanal — Microciclo {mc if mc is not None else "—"}</title>
<style>
  @page {{
    size: A4;
    margin: 20mm 18mm;
    @bottom-right {{ content: counter(page) " / " counter(pages); font-size: 8.5pt; color: #94a3b8; }}
    @bottom-left {{ content: "LoadMonitorSystem"; font-size: 8.5pt; color: #94a3b8; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Segoe UI", Arial, sans-serif; color: #0f172a; font-size: 10.5pt; line-height: 1.5; margin: 0; }}
  .cabecalho {{ border-bottom: 3px solid #2563eb; padding-bottom: 14px; margin-bottom: 20px; }}
  .cabecalho .eyebrow {{ font-size: 8pt; letter-spacing: 2px; text-transform: uppercase; color: #94a3b8; margin-bottom: 4px; }}
  .cabecalho h1 {{ font-size: 20pt; margin: 0 0 4px; color: #0f172a; }}
  .cabecalho .meta {{ font-size: 9.5pt; color: #64748b; }}
  .resumo {{ background: #f8fafc; border-left: 3px solid #2563eb; border-radius: 0 8px 8px 0; padding: 14px 18px; margin-bottom: 22px; font-size: 10.5pt; text-align: justify; }}
  .resumo h2 {{ font-size: 10pt; text-transform: uppercase; letter-spacing: 1px; color: #2563eb; margin: 0 0 8px; }}
  .kpis {{ display: flex; gap: 14px; margin-bottom: 26px; }}
  .kpi {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; }}
  .kpi-label {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 4px; }}
  .kpi-valor {{ font-size: 15pt; font-weight: 700; color: #0f172a; }}
  .kpi-unidade {{ font-size: 9pt; font-weight: 500; color: #64748b; }}
  .seccao {{ margin-bottom: 20px; page-break-inside: avoid; }}
  .seccao h2 {{ font-size: 11.5pt; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; margin: 0 0 10px; }}
  .vazio {{ color: #94a3b8; font-size: 9.5pt; font-style: italic; }}
  .barra-linha {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
  .barra-nome {{ width: 110px; font-size: 8.5pt; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .barra-track {{ flex: 1; background: #f1f5f9; border-radius: 4px; height: 13px; overflow: hidden; }}
  .barra-fill {{ height: 100%; border-radius: 4px; }}
  .barra-valor {{ min-width: 56px; text-align: right; font-size: 8.5pt; font-weight: 700; color: #0f172a; }}
  .destaques {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .destaque {{ flex: 1; min-width: 130px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }}
  .destaque-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 4px; }}
  .destaque-jogador {{ font-size: 9.5pt; font-weight: 700; color: #0f172a; }}
  .destaque-valor {{ font-size: 8.5pt; color: #64748b; }}
  .tabela-dias {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
  .tabela-dias th {{ text-align: left; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; padding: 6px 8px; border-bottom: 1px solid #e2e8f0; }}
  .tabela-dias td {{ padding: 7px 8px; border-bottom: 1px solid #f1f5f9; color: #0f172a; }}
  .tabela-valor {{ color: #64748b; }}
  .rodape {{ margin-top: 30px; font-size: 8pt; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }}
</style>
</head>
<body>
  <div class="cabecalho">
    <div class="eyebrow">LoadMonitorSystem · Relatório Semanal</div>
    <h1>Microciclo {mc if mc is not None else "—"}</h1>
    <div class="meta">Gerado em {gerado_em}</div>
  </div>

  <div class="resumo">
    <h2>Resumo da Semana</h2>
    <p>{escape(texto)}</p>
  </div>

  {kpis_html}

  {destaques_html}

  {analise_dia_html}

  {seccoes}

  <div class="rodape">Gerado pelo LoadMonitorSystem em {gerado_em}</div>
</body>
</html>"""


def gerar_pdf_relatorio_semanal(team_id: str, microciclo: int | None, texto: str) -> bytes | None:
    if not WEASYPRINT_DISPONIVEL:
        return None
    try:
        html_str = gerar_html_relatorio_semanal(team_id, microciclo, texto)
        return HTML(string=html_str).write_pdf()
    except Exception as e:
        print(f"[relatorio_service.gerar_pdf_relatorio_semanal] Falhou: {e}")
        return None
