# LoadMonitorSystem — Utils package
import sys, os

# Adicionar directório utils ao path
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

# Importar directamente dos módulos
import dados as _dados
import calculos as _calculos
import ui as _ui

# Expor funções
carregar_dados        = _dados.carregar_dados
carregar_dados_safe   = _dados.carregar_dados_safe
carregar_exercicios   = _dados.carregar_exercicios
get_mets_gps          = _dados.get_mets_gps
normalizar_coluna     = _dados.normalizar_coluna
COL_ALIASES           = _dados.COL_ALIASES

calcular_acwr         = _calculos.calcular_acwr
calcular_acwr_global  = _calculos.calcular_acwr_global
zscore_serie          = _calculos.zscore_serie
cor_acwr              = _calculos.cor_acwr
calcular_monotonia_strain = _calculos.calcular_monotonia_strain

lm_header             = _ui.lm_header
premium_layout        = _ui.premium_layout
botao_download_html   = _ui.botao_download_html
gerar_pdf_html        = _ui.gerar_pdf_html
metric_card           = _ui.metric_card
sem_dados_suficientes = _ui.sem_dados_suficientes
