"""
LoadMonitorSystem — Componentes de UI reutilizáveis

GERAÇÃO DE PDF:
  Esta versão usa WeasyPrint para gerar PDFs reais (em vez de HTML para
  imprimir). Se o WeasyPrint não estiver instalado ou falhar, faz fallback
  para HTML — a app nunca rebenta por causa disto.

  Fluxo:
    gerar_pdf_html(...)  → produz string HTML formatada (igual à versão antiga)
    gerar_pdf_bytes(...) → produz PDF em bytes (NOVO)
    botao_download_pdf(...) → tenta PDF, faz fallback para HTML se falhar (NOVO)

  Para compatibilidade, botao_download_html continua a existir mas agora
  usa PDF por baixo automaticamente.
"""
import streamlit as st
import pandas as pd
import base64

# ── WeasyPrint — importação tolerante ─────────────────────────────────────────
# Se não estiver instalado, a app não rebenta — apenas faz fallback para HTML.
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_DISPONIVEL = True
except Exception as _e:
    WEASYPRINT_DISPONIVEL = False
    _WEASYPRINT_ERRO = str(_e)


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


# ═══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DE HTML (continua igual — base para o PDF)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    """
    Encapsula conteúdo HTML num documento estilizado.
    Usado tanto para download HTML directo como para conversão a PDF.
    """
    timestamp = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<title>{titulo}</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-right {{
      content: counter(page) " / " counter(pages);
      font-family: Arial, sans-serif;
      font-size: 9pt;
      color: #888;
    }}
    @bottom-left {{
      content: "LoadMonitorSystem";
      font-family: Arial, sans-serif;
      font-size: 9pt;
      color: #888;
    }}
  }}
  body {{
    font-family: Arial, sans-serif;
    margin: 0;
    color: #1a1a2e;
    font-size: 10.5pt;
    line-height: 1.45;
  }}
  h1 {{
    color: #e63946;
    border-bottom: 3px solid #e63946;
    padding-bottom: 8px;
    font-size: 18pt;
    margin: 0 0 14px 0;
  }}
  h2 {{
    color: #457b9d;
    margin: 22px 0 10px 0;
    font-size: 13pt;
    border-bottom: 1px solid #e8e8ee;
    padding-bottom: 4px;
  }}
  h3 {{
    color: #1a1a2e;
    margin: 16px 0 8px 0;
    font-size: 11pt;
  }}
  p {{ margin: 6px 0 10px 0; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0 16px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
  }}
  th {{
    background: #e63946;
    color: white;
    padding: 6px 10px;
    text-align: left;
    font-weight: 600;
  }}
  td {{
    padding: 5px 10px;
    border-bottom: 1px solid #e0e0e6;
  }}
  tr:nth-child(even) td {{ background: #f8f9fa; }}
  ul, ol {{ margin: 8px 0 12px 24px; padding: 0; }}
  li {{ margin-bottom: 4px; }}
  .alerta-red    {{ color: #e74c3c; font-weight: bold; }}
  .alerta-yellow {{ color: #e67e22; font-weight: bold; }}
  .alerta-green  {{ color: #27ae60; font-weight: bold; }}
  .alerta-blue   {{ color: #2980b9; font-weight: bold; }}
  .footer {{
    margin-top: 24px;
    font-size: 8.5pt;
    color: #888;
    border-top: 1px solid #ddd;
    padding-top: 8px;
  }}
  /* Evitar quebras de página em sítios feios */
  h1, h2, h3 {{ page-break-after: avoid; }}
  table {{ page-break-inside: avoid; }}
  @media print {{
    button {{ display: none; }}
  }}
</style>
</head>
<body>
{conteudo_html}
<div class="footer">Gerado pelo LoadMonitorSystem · {timestamp}</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# GERAÇÃO DE PDF (NOVO — via WeasyPrint)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pdf_bytes(conteudo_html: str, titulo: str) -> bytes | None:
    """
    Converte HTML em PDF (bytes) via WeasyPrint.
    Retorna None se WeasyPrint não estiver disponível ou se a conversão falhar.
    O caller deve fazer fallback para HTML quando isto retornar None.
    """
    if not WEASYPRINT_DISPONIVEL:
        return None
    try:
        html_str = gerar_pdf_html(conteudo_html, titulo)
        pdf_bytes = HTML(string=html_str).write_pdf()
        return pdf_bytes
    except Exception as e:
        # Não rebentar — registar erro e fazer fallback
        print(f"[ui.gerar_pdf_bytes] Falhou conversão PDF: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# BOTÕES DE DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def botao_download_pdf(conteudo_html: str, nome_base: str,
                       label: str = "📥 Exportar PDF"):
    """
    Botão de download que gera PDF via WeasyPrint.
    Se WeasyPrint não estiver disponível ou falhar, faz fallback automático
    para HTML (com botão alternativo claro para o utilizador).

    Parâmetros:
      conteudo_html — HTML do corpo do relatório (sem <html>/<body>)
      nome_base     — nome do ficheiro sem extensão (ex: "Dashboard_20260505")
      label         — texto do botão
    """
    pdf_bytes = gerar_pdf_bytes(conteudo_html, nome_base)

    if pdf_bytes:
        # PDF gerado com sucesso — botão directo
        st.download_button(
            label=label,
            data=pdf_bytes,
            file_name=f"{nome_base}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        # Fallback — gerar HTML com botão e aviso discreto
        html_str = gerar_pdf_html(conteudo_html, nome_base)
        b64 = base64.b64encode(html_str.encode()).decode()
        href = (
            f'<a href="data:text/html;base64,{b64}" download="{nome_base}.html" '
            f'style="display:inline-block;padding:10px 20px;background:#e63946;'
            f'color:white;border-radius:8px;text-decoration:none;font-weight:bold;'
            f'margin:8px 0">{label.replace("PDF", "Relatório")}</a>'
        )
        st.markdown(href, unsafe_allow_html=True)
        st.caption("ℹ️ Geração de PDF temporariamente indisponível — exportado em HTML. Abre o ficheiro e usa Ctrl+P para gerar PDF.")


def botao_download_html(html_str: str, nome_ficheiro: str,
                        label: str = "📥 Exportar Relatório"):
    """
    LEGACY — mantido para não partir páginas que ainda chamem esta função.

    Esta função usava HTML antes. Agora redireciona automaticamente para PDF
    se possível. O parâmetro `html_str` é tratado como sendo já o resultado
    de gerar_pdf_html() (documento HTML completo).

    Para usos novos, prefere botao_download_pdf(conteudo, nome) que recebe
    apenas o conteúdo do corpo (sem <html>/<body>).
    """
    # Detectar se o html_str é um documento completo ou só conteúdo
    eh_doc_completo = html_str.lstrip().lower().startswith("<!doctype")

    # Limpar extensão do nome (esta função recebia .html no nome)
    nome_base = nome_ficheiro
    for ext in [".html", ".htm", ".pdf"]:
        if nome_base.lower().endswith(ext):
            nome_base = nome_base[:-len(ext)]
            break

    # Tentar gerar PDF
    if WEASYPRINT_DISPONIVEL:
        try:
            if eh_doc_completo:
                # Já é um documento completo — converter directamente
                pdf_bytes = HTML(string=html_str).write_pdf()
            else:
                # É só conteúdo — encapsular primeiro
                pdf_bytes = gerar_pdf_bytes(html_str, nome_base)

            if pdf_bytes:
                st.download_button(
                    label=label.replace("HTML", "PDF") if "HTML" in label else label,
                    data=pdf_bytes,
                    file_name=f"{nome_base}.pdf",
                    mime="application/pdf",
                    type="primary",
                )
                return
        except Exception as e:
            print(f"[ui.botao_download_html] Fallback para HTML: {e}")

    # Fallback — manter comportamento antigo (HTML para Ctrl+P)
    b64 = base64.b64encode(html_str.encode()).decode()
    href = (
        f'<a href="data:text/html;base64,{b64}" download="{nome_base}.html" '
        f'style="display:inline-block;padding:10px 20px;background:#e63946;'
        f'color:white;border-radius:8px;text-decoration:none;font-weight:bold;'
        f'margin:8px 0">{label}</a>'
    )
    st.markdown(href, unsafe_allow_html=True)
    st.caption("💡 Abre o ficheiro no browser e usa Ctrl+P → 'Guardar como PDF' para exportar.")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENTES VISUAIS
# ═══════════════════════════════════════════════════════════════════════════════

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
