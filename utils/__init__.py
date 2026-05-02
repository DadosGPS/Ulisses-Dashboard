import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dados import carregar_dados, carregar_dados_safe, carregar_exercicios, get_mets_gps, normalizar_coluna, COL_ALIASES
from calculos import calcular_acwr, calcular_acwr_global, zscore_serie, cor_acwr, calcular_monotonia_strain
from ui import lm_header, premium_layout, botao_download_html, gerar_pdf_html, metric_card, sem_dados_suficientes
