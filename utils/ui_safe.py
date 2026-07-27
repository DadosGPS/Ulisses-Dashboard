"""Versão segura e simples do módulo UI para o dashboard."""
import base64
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

try:
    from weasyprint import HTML
    WEASYPRINT_DISPONIVEL = True
except Exception:
    WEASYPRINT_DISPONIVEL = False


def aplicar_tema_graficos():
    """Aplica um tema escuro simples e estável aos gráficos — consistente com o resto da app."""
    st.markdown(
        """
        <style>
        div[data-testid="stPlotlyChart"] > div {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.02);
            padding: 4px;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.02);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "lm_professional" not in pio.templates:
        pio.templates["lm_professional"] = go.layout.Template(
            layout=go.Layout(
                font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="rgba(255,255,255,0.85)"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=50, r=20, t=55, b=40),
                title=dict(font=dict(size=18, color="white"), x=0.05),
                hovermode="x unified",
                hoverlabel=dict(bgcolor="#1a2535", bordercolor="rgba(255,255,255,0.15)", font=dict(color="white", size=12)),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="rgba(255,255,255,0.75)")),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False, linecolor="rgba(255,255,255,0.16)", tickfont=dict(size=10, color="rgba(255,255,255,0.7)")),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False, linecolor="rgba(255,255,255,0.16)", tickfont=dict(size=10, color="rgba(255,255,255,0.7)")),
                colorway=["#e63946", "#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#14b8a6", "#64748b"],
            )
        )

    pio.templates.default = "lm_professional"


def lm_header(title: str, subtitle: str = "", badge: str = ""):
    badge_html = f'<div class="lm-page-badge">{badge}</div>' if badge else ""
    sub_html = f'<div class="lm-page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="lm-page-header">{badge_html}<div class="lm-page-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def premium_layout(height=380, title="", margin=None):
    return dict(
        height=height,
        title=dict(text=title, font=dict(size=13, color="rgba(255,255,255,0.7)"), x=0) if title else None,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Calibri, sans-serif", color="rgba(255,255,255,0.75)", size=11),
        margin=margin or dict(t=20 if not title else 40, b=30, l=50, r=20),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(size=10), showgrid=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(size=10), showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor="rgba(255,255,255,0.08)", borderwidth=1, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#1a2535", bordercolor="#e63946", font=dict(size=11, color="white")),
    )


def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    return f"<!DOCTYPE html><html lang=\"pt\"><head><meta charset=\"UTF-8\"><title>{titulo}</title></head><body><h1>{titulo}</h1><p>Gerado em {timestamp}</p>{conteudo_html}</body></html>"


def botao_download_html(conteudo_html: str, nome_base: str, label: str = "Download HTML"):
    html_bytes = gerar_pdf_html(conteudo_html, nome_base).encode("utf-8")
    b64 = base64.b64encode(html_bytes).decode("utf-8")
    href = f"data:text/html;charset=utf-8;base64,{b64}"
    st.markdown(f'<a href="{href}" download="{nome_base}.html">{label}</a>', unsafe_allow_html=True)


def botao_download_pdf(conteudo_html: str, nome_base: str, label: str = "Download PDF"):
    if WEASYPRINT_DISPONIVEL:
        html_bytes = gerar_pdf_html(conteudo_html, nome_base).encode("utf-8")
        pdf_bytes = HTML(string=html_bytes.decode("utf-8")).write_pdf()
        st.download_button(label=label, data=pdf_bytes, file_name=f"{nome_base}.pdf", mime="application/pdf")
    else:
        botao_download_html(conteudo_html, nome_base, label)


def metric_card(label: str, value: str, delta: str = "", cor: str = "#e63946"):
    delta_html = f'<div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:2px">{delta}</div>' if delta else ""
    st.markdown(
        f'<div style="background:{cor}10;border:1px solid {cor}30;border-top:3px solid {cor};border-radius:10px;padding:14px;text-align:center">'
        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.5);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:1.6rem;font-weight:700;color:white">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def team_kpi_tile(label: str, valor: float, unit: str, sub_label: str, cor: str):
    """Tile de KPI de equipa — estilo 'TEAM TOTAL DISTANCE' do ranking de performance."""
    st.markdown(
        f'<div style="background:{cor}14;border:1px solid {cor}38;border-radius:12px;'
        f'padding:14px 16px;height:100%">'
        f'<div style="font-size:0.64rem;color:rgba(255,255,255,0.5);letter-spacing:1.2px;'
        f'text-transform:uppercase;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:white;line-height:1.1">'
        f'{valor:,.0f} <span style="font-size:0.8rem;font-weight:600;color:rgba(255,255,255,0.5)">{unit}</span></div>'
        f'<div style="font-size:0.68rem;color:{cor};margin-top:4px;font-weight:600">{sub_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _ranking_bar_row(rank: int, nome: str, valor: float, unit: str, pct: float, cor: str, subida: bool) -> str:
    seta = "▲" if subida else "▼"
    seta_cor = "#22c55e" if subida else "#ef4444"
    largura = max(4, min(100, pct))
    nome_curto = nome if len(nome) <= 13 else nome[:12] + "…"
    return (
        f'<div style="display:flex;align-items:center;gap:8px;margin:5px 0">'
        f'<div style="width:20px;height:20px;border-radius:50%;background:{cor};color:white;'
        f'font-size:0.64rem;font-weight:800;display:flex;align-items:center;justify-content:center;'
        f'flex-shrink:0">{rank}</div>'
        f'<div style="width:76px;font-size:0.72rem;color:rgba(255,255,255,0.85);font-weight:600;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0" title="{nome}">{nome_curto}</div>'
        f'<div style="flex:1;background:rgba(255,255,255,0.06);border-radius:6px;height:20px;'
        f'position:relative;overflow:hidden">'
        f'<div style="width:{largura:.0f}%;height:100%;background:{cor};border-radius:6px"></div>'
        f'<span style="position:absolute;right:7px;top:50%;transform:translateY(-50%);'
        f'font-size:0.65rem;font-weight:700;color:white;text-shadow:0 1px 2px rgba(0,0,0,0.45)">'
        f'{valor:,.0f}{unit}</span>'
        f'</div>'
        f'<div style="min-width:48px;text-align:right;font-size:0.65rem;font-weight:800;'
        f'color:{seta_cor}">{pct:.0f}% {seta}</div>'
        f'</div>'
    )


def ranking_metric_card(icon: str, titulo: str, cor: str, top_items, bottom_items, unit: str = "m"):
    """
    Card 'Top 3 / Bottom 3' com barras horizontais — estilo Match Player Performance Ranking.
    top_items / bottom_items: listas de tuplos (jogador, valor), já ordenadas.
    """
    if not top_items:
        return
    max_val = top_items[0][1] or 1

    linhas_top = "".join(
        _ranking_bar_row(i + 1, nome, val, unit, (val / max_val * 100) if max_val else 0, cor, True)
        for i, (nome, val) in enumerate(top_items)
    )
    cor_bottom = f"{cor}75"  # tom mais suave (alpha hex) para o grupo Bottom 3
    linhas_bottom = "".join(
        _ranking_bar_row(i + 1, nome, val, unit, (val / max_val * 100) if max_val else 0, cor_bottom, False)
        for i, (nome, val) in enumerate(bottom_items)
    )

    st.markdown(
        f'<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);'
        f'border-left:3px solid {cor};border-radius:12px;padding:16px 18px;margin-bottom:14px">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">'
        f'<span style="font-size:1.1rem">{icon}</span>'
        f'<span style="font-weight:700;color:white;font-size:0.88rem">{titulo}</span>'
        f'</div>'
        f'<div style="font-size:0.64rem;color:{cor};font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;margin-bottom:6px">🥇 Top 3</div>'
        f'{linhas_top}'
        f'<div style="font-size:0.64rem;color:rgba(255,255,255,0.4);font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;margin:12px 0 6px">🔻 Bottom 3</div>'
        f'{linhas_bottom}'
        f'</div>',
        unsafe_allow_html=True,
    )


def ranking_top_list(icon: str, titulo: str, cor: str, items, unit: str = ""):
    """Lista compacta Top-N com barras — para destaques de uma única métrica (sem Bottom 3)."""
    if not items:
        return
    max_val = items[0][1] or 1
    linhas = "".join(
        _ranking_bar_row(i + 1, nome, val, unit, (val / max_val * 100) if max_val else 0, cor, True)
        for i, (nome, val) in enumerate(items)
    )
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);'
        f'border-left:3px solid {cor};border-radius:12px;padding:16px 18px;margin-bottom:14px">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">'
        f'<span style="font-size:1.1rem">{icon}</span>'
        f'<span style="font-weight:700;color:white;font-size:0.88rem">{titulo}</span>'
        f'</div>'
        f'{linhas}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _alpha_hex(alpha: float) -> str:
    """Converte 0..1 num sufixo hex de 2 dígitos, para compor cores #RRGGBBAA."""
    return format(max(0, min(255, int(round(alpha * 255)))), "02x")


def tabela_carga_colorida(df_tabela, jogador_col: str, colunas: list):
    """
    Tabela 'Perfil de Carga Externa' — cada célula é uma pill colorida por métrica,
    com intensidade proporcional ao valor (heatmap), estilo Predicted External Load Profile.

    colunas: lista de dicts {"col": nome_coluna, "label": cabeçalho, "cor": hex, "casas": nº decimais}
    """
    if df_tabela.empty or not colunas:
        return

    ranges = {}
    for c in colunas:
        serie = df_tabela[c["col"]].dropna()
        ranges[c["col"]] = (serie.min(), serie.max()) if not serie.empty else (0, 1)

    header_cells = "".join(
        f'<th style="padding:10px 12px;font-size:0.64rem;letter-spacing:0.6px;'
        f'text-transform:uppercase;color:rgba(255,255,255,0.55);text-align:center;'
        f'white-space:nowrap">{c["label"]}</th>'
        for c in colunas
    )

    linhas_html = []
    for _, row in df_tabela.iterrows():
        celulas = ""
        for c in colunas:
            val = row.get(c["col"])
            if pd.isna(val):
                celulas += '<td style="padding:6px 8px;text-align:center;color:rgba(255,255,255,0.3)">—</td>'
                continue
            lo, hi = ranges[c["col"]]
            pct = (val - lo) / (hi - lo) if hi > lo else 0.5
            alpha = 0.18 + pct * 0.55
            casas = c.get("casas", 0)
            val_fmt = f"{val:,.{casas}f}"
            celulas += (
                f'<td style="padding:6px 8px;text-align:center">'
                f'<span style="display:inline-block;min-width:58px;padding:5px 10px;'
                f'border-radius:14px;background:{c["cor"]}{_alpha_hex(alpha)};'
                f'color:white;font-weight:700;font-size:0.75rem">{val_fmt}</span>'
                f'</td>'
            )
        linhas_html.append(
            f'<tr><td style="padding:8px 14px;font-size:0.8rem;font-weight:600;'
            f'color:rgba(255,255,255,0.9);white-space:nowrap">{row[jogador_col]}</td>{celulas}</tr>'
        )

    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid rgba(255,255,255,0.08);border-radius:14px;'
        f'background:rgba(255,255,255,0.02)">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="background:rgba(255,255,255,0.04)">'
        f'<th style="padding:10px 14px;font-size:0.64rem;letter-spacing:0.6px;'
        f'text-transform:uppercase;color:rgba(255,255,255,0.55);text-align:left">Jogador</th>'
        f'{header_cells}</tr></thead>'
        f'<tbody>{"".join(linhas_html)}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )


def tabela_semaforo(linhas: list, colunas_labels: list, matriz: list, tiers: list, unit: str = "%", casas: int = 0):
    """
    Tabela heatmap com células coloridas por níveis (semáforo) — estilo Match Day Benchmarks.

    linhas: nomes das linhas (ex: Dias MD)
    colunas_labels: nomes das colunas (ex: métricas)
    matriz: lista de listas [linha][coluna] com os valores numéricos
    tiers: lista de tuplos (limite_inferior, cor) do mais alto para o mais baixo,
           ex: [(300, "#e74c3c"), (200, "#f39c12"), (100, "#2ecc71"), (0, "#3498db")]
    """
    if not linhas or not colunas_labels:
        return

    def _cor_para(v):
        for limite, cor in tiers:
            if v >= limite:
                return cor
        return tiers[-1][1]

    header_cells = "".join(
        f'<th style="padding:10px 12px;font-size:0.64rem;letter-spacing:0.6px;'
        f'text-transform:uppercase;color:rgba(255,255,255,0.55);text-align:center;'
        f'white-space:nowrap">{c}</th>'
        for c in colunas_labels
    )

    linhas_html = []
    for nome_linha, valores in zip(linhas, matriz):
        celulas = ""
        for v in valores:
            cor = _cor_para(v)
            val_fmt = f"{v:,.{casas}f}{unit}"
            celulas += (
                f'<td style="padding:4px 6px;text-align:center">'
                f'<div style="padding:7px 4px;border-radius:8px;background:{cor}2e;'
                f'border:1px solid {cor}55;color:{cor};font-weight:800;font-size:0.78rem">{val_fmt}</div>'
                f'</td>'
            )
        linhas_html.append(
            f'<tr><td style="padding:8px 14px;font-size:0.8rem;font-weight:600;'
            f'color:rgba(255,255,255,0.9);white-space:nowrap">{nome_linha}</td>{celulas}</tr>'
        )

    st.markdown(
        f'<div style="overflow-x:auto;border:1px solid rgba(255,255,255,0.08);border-radius:14px;'
        f'background:rgba(255,255,255,0.02)">'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="background:rgba(255,255,255,0.04)">'
        f'<th style="padding:10px 14px;font-size:0.64rem;letter-spacing:0.6px;'
        f'text-transform:uppercase;color:rgba(255,255,255,0.55);text-align:left"></th>'
        f'{header_cells}</tr></thead>'
        f'<tbody>{"".join(linhas_html)}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )


def grafico_barras_limpo(categorias: list, valores: list, cor: str, orientation: str = "v",
                          altura: int = 260, casas: int = 0, titulo: str = None):
    """Gráfico de barras minimalista — sem grelha, valores no topo, estilo Daily GPS Report."""
    textos = [f"{v:,.{casas}f}" for v in valores]
    if orientation == "h":
        fig = go.Figure(go.Bar(
            y=categorias, x=valores, orientation="h", marker_color=cor,
            text=textos, textposition="outside",
            textfont=dict(size=11, color="rgba(255,255,255,0.85)"),
        ))
        fig.update_xaxes(showgrid=False, zeroline=False, visible=False)
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="rgba(255,255,255,0.65)"))
    else:
        fig = go.Figure(go.Bar(
            x=categorias, y=valores, marker_color=cor,
            text=textos, textposition="outside",
            textfont=dict(size=11, color="rgba(255,255,255,0.85)"),
        ))
        fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=10, color="rgba(255,255,255,0.65)"))
        fig.update_yaxes(showgrid=False, zeroline=False, visible=False)

    fig.update_layout(
        height=altura,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(t=32 if titulo else 20, b=40, l=10, r=20),
        bargap=0.28,
        title=dict(text=titulo, font=dict(size=13, color="rgba(255,255,255,0.8)"), x=0.02) if titulo else None,
    )
    return fig


def sem_dados_suficientes(minimo: int = 4, atual: int = 0, metrica: str = "ACWR"):
    st.info(
        f"**Dados insuficientes para {metrica}** - "
        f"sao necessarias pelo menos **{minimo} semanas** de dados. "
        f"Actualmente tens **{atual}** sessao(oes) registada(s)."
    )
