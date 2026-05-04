"""LoadMonitorSystem — Componentes de UI reutilizáveis"""
import streamlit as st
import pandas as pd
import base64

def lm_header(title: str, subtitle: str = "", badge: str = ""):
    badge_html = f'<div class="lm-page-badge">{badge}</div>' if badge else ""
    sub_html   = f'<div class="lm-page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="lm-page-header">{badge_html}'
        f'<div class="lm-page-title">{title}</div>{sub_html}</div>',
        unsafe_allow_html=True
    )

def premium_layout(height=380, title="", margin=None):
    return dict(
        height=height,
        title=dict(text=title, font=dict(size=13, color="rgba(255,255,255,0.7)"), x=0) if title else None,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Calibri, sans-serif", color="rgba(255,255,255,0.75)", size=11),
        margin=margin or dict(t=20 if not title else 40, b=30, l=50, r=20),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(size=10), showgrid=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)", tickfont=dict(size=10), showgrid=True),
        legend=dict(bgcolor="rgba(0,0,0,0.4)", bordercolor="rgba(255,255,255,0.08)", borderwidth=1, font=dict(size=10)),
        hoverlabel=dict(bgcolor="#1a2535", bordercolor="#e63946", font=dict(size=11, color="white")),
    )

def botao_download_html(html_str: str, nome_ficheiro: str, label: str = "📥 Exportar Relatório PDF"):
    """Botão de download para HTML estilizado (utilizador abre depois e usa Ctrl+P)."""
    b64 = base64.b64encode(html_str.encode()).decode()
    href = (
        f'<a href="data:text/html;base64,{b64}" download="{nome_ficheiro}" '
        f'style="display:inline-block;padding:10px 20px;background:#e63946;'
        f'color:white;border-radius:8px;text-decoration:none;font-weight:bold;'
        f'margin:8px 0">{label}</a>'
    )
    st.markdown(href, unsafe_allow_html=True)
    st.caption("💡 Abre o ficheiro no browser e usa Ctrl+P → 'Guardar como PDF' para exportar.")

def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    """Encapsula conteúdo HTML num documento imprimível com estilos LoadMonitor."""
    timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>{titulo}</title>
<style>
  body {{ font-family: Arial, sans-serif; margin: 30px; color: #1a1a2e; }}
  h1 {{ color: #e63946; border-bottom: 3px solid #e63946; padding-bottom: 8px; }}
  h2 {{ color: #457b9d; margin-top: 24px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th {{ background: #e63946; color: white; padding: 8px 12px; text-align: left; }}
  td {{ padding: 7px 12px; border-bottom: 1px solid #ddd; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  .alerta-red    {{ color: #e74c3c; font-weight: bold; }}
  .alerta-yellow {{ color: #e67e22; font-weight: bold; }}
  .alerta-green  {{ color: #27ae60; font-weight: bold; }}
  .alerta-blue   {{ color: #2980b9; font-weight: bold; }}
  .footer {{ margin-top: 40px; font-size: 0.8em; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
  @media print {{ button {{ display: none; }} }}
</style>
</head>
<body>
{conteudo_html}
<div class="footer">Gerado automaticamente pelo LoadMonitorSystem · {timestamp}</div>
</body>
</html>"""

def metric_card(label: str, value: str, delta: str = "", cor: str = "#e63946"):
    delta_html = f'<div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:2px">{delta}</div>' if delta else ""
    st.markdown(
        f'<div style="background:{cor}10;border:1px solid {cor}30;border-top:3px solid {cor};'
        f'border-radius:10px;padding:14px;text-align:center">'
        f'<div style="font-size:0.68rem;color:rgba(255,255,255,0.5);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">{label}</div>'
        f'<div style="font-size:1.6rem;font-weight:700;color:white">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True
    )

def sem_dados_suficientes(minimo: int = 4, atual: int = 0, metrica: str = "ACWR"):
    st.info(
        f"**Dados insuficientes para {metrica}** - "
        f"sao necessarias pelo menos **{minimo} semanas** de dados. "
        f"Actualmente tens **{atual}** sessao(oes) registada(s)."
    )
