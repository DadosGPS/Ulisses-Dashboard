"""LoadMonitorSystem — Componentes de UI reutilizáveis"""
import streamlit as st
import pandas as pd
import numpy as np
import base64, io

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

def botao_download_html(html_str: str, nome_ficheiro: str, label: str = "Exportar"):
    b64 = base64.b64encode(html_str.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{nome_ficheiro}" style="text-decoration:none">'
    href += f'<button style="background:#e63946;color:white;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-size:0.85rem;font-weight:600">{label}</button></a>'
    st.markdown(href, unsafe_allow_html=True)

def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>{titulo}</title>
<style>
body{{font-family:Calibri,sans-serif;background:#fff;color:#222;margin:20px}}
h1{{color:#e63946;border-bottom:2px solid #e63946;padding-bottom:8px}}
h2{{color:#1a2535;margin-top:20px}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th{{background:#1a2535;color:white;padding:8px;text-align:left}}
td{{padding:6px 8px;border-bottom:1px solid #eee}}
.alerta-red{{background:#fce;border-left:4px solid #e63946;padding:8px}}
.alerta-green{{background:#efe;border-left:4px solid #2ecc71;padding:8px}}
@media print{{body{{margin:0}}}}
</style></head><body>
<h1>LoadMonitorSystem - {titulo}</h1>
<p style="color:#888;font-size:0.85em">Gerado automaticamente - {timestamp}</p>
{conteudo_html}
</body></html>"""

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
