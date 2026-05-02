import sys, os
_utils_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_utils_dir)
if _utils_dir not in sys.path: sys.path.insert(0, _utils_dir)
if _root_dir not in sys.path: sys.path.insert(0, _root_dir)

from utils.dados import carregar_dados, carregar_dados_safe, carregar_exercicios, get_mets_gps, normalizar_coluna, COL_ALIASES
from utils.calculos import calcular_acwr, calcular_acwr_global, zscore_serie, cor_acwr, calcular_monotonia_strain
from utils.ui import lm_header, premium_layout, botao_download_html, gerar_pdf_html, metric_card, sem_dados_suficientes
