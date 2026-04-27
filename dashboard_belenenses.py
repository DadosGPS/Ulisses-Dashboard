"""
Dashboard de Monitorização de Carga — Belenenses
Abre o browser automaticamente. Atualiza ao clicar em "Atualizar Dados".
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import io
import base64
import json
from pathlib import Path
from datetime import datetime, date

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Carga de Treino | Belenenses",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: #1e2330;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #e63946;
        margin-bottom: 8px;
    }
    .risk-green  { color: #2ecc71; font-weight: 700; }
    .risk-yellow { color: #f39c12; font-weight: 700; }
    .risk-red    { color: #e74c3c; font-weight: 700; }
    .risk-blue   { color: #3498db; font-weight: 700; }
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e63946;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Caminho do ficheiro Excel ─────────────────────────────────────────────────
EXCEL_PATH = "Excel_carga_de_treino_profissional_final_2.xlsx"

# ── Funções de carregamento ───────────────────────────────────────────────────
@st.cache_data(ttl=0)
def carregar_dados(path: str):
    """Lê a folha BD_Carga e faz limpeza básica."""
    # Detetar automaticamente a linha de cabeçalho (procura a linha com "Jogador")
    raw = pd.read_excel(path, sheet_name="BD_Carga", header=None, engine="openpyxl")
    header_row = 2  # default
    for i, row in raw.iterrows():
        if "Jogador" in [str(v).strip() for v in row.values]:
            header_row = i
            break
    df = pd.read_excel(path, sheet_name="BD_Carga", header=header_row, engine="openpyxl")

    # Normalizar nomes de colunas
    df.columns = [str(c).strip() for c in df.columns]

    # Converter Data — suporta número de série do Excel ou datas normais
    if "Data" in df.columns:
        def converter_data(v):
            if pd.isna(v): return pd.NaT
            try:
                n = float(v)
                return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
            except (ValueError, TypeError):
                return pd.to_datetime(v, errors="coerce")
        df["Data"] = df["Data"].apply(converter_data)

    # Colunas numéricas
    numericas = [
        "Duração (min)", "Distância Total (m)", "HSR (m)", "Sprint (m)",
        "Acc (n)", "Dcc (n)", "PSE Sessão", "Vel. Máx (km/h)",
        "Microciclo (Nr)", "Fadiga (1-5)", "Min Jogo",
        "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index",
    ]
    for col in numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Carga Interna = PSE × Duração
    if "PSE Sessão" in df.columns and "Duração (min)" in df.columns:
        df["Carga Interna"] = df["PSE Sessão"] * df["Duração (min)"]

    # Remover linhas completamente vazias
    df = df.dropna(how="all")
    df = df[df["Jogador"].notna()]

    return df


@st.cache_data(ttl=0)
def carregar_exercicios(path: str):
    """Lê a folha Exercícios se existir."""
    try:
        raw = pd.read_excel(path, sheet_name="Exercícios", header=None, engine="openpyxl")
        # Encontrar linha de cabeçalho (procura "Data" ou "Nome")
        header_row = 2
        for i, row in raw.iterrows():
            vals = [str(v).strip().lower() for v in row.values if v is not None]
            if any(v in ["data","nome do exercicio","nome","exercicio"] for v in vals):
                header_row = i
                break
        df_ex = pd.read_excel(path, sheet_name="Exercícios", header=header_row, engine="openpyxl")
        df_ex.columns = [str(c).strip().replace("\n"," ") for c in df_ex.columns]
        # Normalizar nomes de colunas
        rename = {}
        for col in df_ex.columns:
            cl = col.lower()
            if "data" in cl:                   rename[col] = "Data"
            elif "microciclo" in cl:           rename[col] = "Microciclo (Nr)"
            elif "dia" in cl and "md" in cl:   rename[col] = "Dia MD"
            elif "nome" in cl or "exerc" in cl and "categ" not in cl: rename[col] = "Exercício"
            elif "categ" in cl:                rename[col] = "Categoria"
            elif "duração" in cl or "duracao" in cl: rename[col] = "Duração (min)"
            elif "jogadores" in cl or "nº" in cl: rename[col] = "Nº Jogadores"
            elif "distância" in cl or "distancia" in cl: rename[col] = "Distância Total (m)"
            elif "hsr" in cl:                  rename[col] = "HSR (m)"
            elif "sprint" in cl:               rename[col] = "Sprint (m)"
            elif "acc" in cl and "dcc" not in cl: rename[col] = "Acc (n)"
            elif "dcc" in cl:                  rename[col] = "Dcc (n)"
            elif "vel" in cl or "vmáx" in cl or "vmax" in cl: rename[col] = "Vel. Máx (km/h)"
            elif "pse" in cl:                  rename[col] = "PSE Exercício"
            elif "nota" in cl:                 rename[col] = "Notas"
        df_ex = df_ex.rename(columns=rename)
        # Converter data
        if "Data" in df_ex.columns:
            def conv(v):
                if pd.isna(v): return pd.NaT
                try:
                    n = float(v)
                    return pd.Timestamp("1899-12-30") + pd.Timedelta(days=n)
                except (ValueError, TypeError):
                    return pd.to_datetime(v, errors="coerce")
            df_ex["Data"] = df_ex["Data"].apply(conv)
        # Carga Interna por exercício
        if "PSE Exercício" in df_ex.columns and "Duração (min)" in df_ex.columns:
            df_ex["Carga Interna Ex."] = pd.to_numeric(df_ex["PSE Exercício"], errors="coerce") *                                           pd.to_numeric(df_ex["Duração (min)"], errors="coerce")
        # Limpar linhas vazias e linhas de exemplo
        df_ex = df_ex.dropna(how="all")
        if "Exercício" in df_ex.columns:
            df_ex = df_ex[df_ex["Exercício"].notna()]
        # Colunas numéricas
        for col in ["Microciclo (Nr)","Duração (min)","Nº Jogadores","Distância Total (m)",
                    "HSR (m)","Sprint (m)","Acc (n)","Dcc (n)","Vel. Máx (km/h)","PSE Exercício"]:
            if col in df_ex.columns:
                df_ex[col] = pd.to_numeric(df_ex[col], errors="coerce")
        return df_ex
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=0)
def calcular_acwr(df: pd.DataFrame, jogador: str):
    """EWMA ACWR por jogador — λ aguda=0.25, λ crónica=0.069."""
    sub = df[df["Jogador"] == jogador].sort_values("Data").copy()
    if sub.empty or "Carga Interna" not in sub.columns:
        return sub
    λa, λc = 0.25, 2 / 29
    sub["EWMA_Aguda"]   = sub["Carga Interna"].ewm(alpha=λa, adjust=False).mean()
    sub["EWMA_Crónica"] = sub["Carga Interna"].ewm(alpha=λc, adjust=False).mean()
    sub["ACWR"] = sub["EWMA_Aguda"] / sub["EWMA_Crónica"].replace(0, np.nan)
    return sub


# (cor_acwr definida globalmente acima)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/pt/thumb/3/3a/C.F._Os_Belenenses.svg/120px-C.F._Os_Belenenses.svg.png", width=80)
    st.title("⚽ Carga de Treino")
    st.markdown("**Belenenses**")
    st.divider()

    # Ficheiro Excel
    excel_dir = st.text_input("📁 Pasta do ficheiro Excel", value=".", help="Caminho da pasta onde está o ficheiro .xlsx")
    excel_file = st.text_input("📄 Nome do ficheiro", value=EXCEL_PATH)
    excel_path = os.path.join(excel_dir, excel_file)

    if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # Verificar se o ficheiro existe
    if not os.path.exists(excel_path):
        st.error(f"Ficheiro não encontrado:\n`{excel_path}`\n\nVerifica o caminho acima.")
        st.stop()

    mod_time = os.path.getmtime(excel_path)
    st.caption(f"📅 Última modificação:\n{datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')}")

    st.divider()

    # Carregar dados
    try:
        df = carregar_dados(excel_path)
    except Exception as e:
        st.error(f"Erro ao ler o Excel:\n{e}")
        st.stop()

    jogadores  = sorted(df["Jogador"].dropna().unique().tolist())
    microciclos = sorted(df["Microciclo (Nr)"].dropna().unique().tolist(), reverse=True)
    posicoes   = sorted(df["Posição"].dropna().unique().tolist()) if "Posição" in df.columns else []

    st.markdown("### 🔍 Filtros")
    st.caption("💡 Os filtros aplicam-se a todas as vistas")
    mc_sel      = st.multiselect("Microciclo(s)", microciclos, default=microciclos[:3] if len(microciclos) >= 3 else microciclos,
                                  help="Seleciona um ou mais microciclos para analisar")
    dias_md_ops = sorted(df["Dia MD"].dropna().unique().tolist()) if "Dia MD" in df.columns else []
    dia_md_sel  = st.multiselect("Dia do Microciclo (Dia MD)", dias_md_ops, default=dias_md_ops)
    pos_sel     = st.multiselect("Posição", posicoes, default=posicoes)
    jogador_sel = st.selectbox("Jogador (análise individual)", jogadores)

    pagina = st.radio("📋 Vista", [
        "🚨 Alertas do Dia",
        "🏟️ Equipa",
        "👤 Jogador Individual",
        "📊 Comparação por Posição",
        "🏃 Vmáx Monitor",
        "📐 Z-Score",
        "📏 Perfil de Referência",
        "🩺 Lesões & Disponibilidade",
        "⚽ Carga Jogo vs Treino",
        "📊 Treino vs Jogo (% Métricas)",
        "⚡ Monotonia & Strain",
        "🕓 Log de Alertas",
        "📖 Glossário",
        "📅 Resumo do Dia",
        "🏋️ Análise de Exercícios",
    ])


# ── Filtro global (sem Dia MD — aplicado por página onde relevante) ───────────
df_f = df.copy()
if mc_sel:
    df_f = df_f[df_f["Microciclo (Nr)"].isin(mc_sel)]
if pos_sel and "Posição" in df_f.columns:
    df_f = df_f[df_f["Posição"].isin(pos_sel)]

# df_f_dia inclui também o filtro de Dia MD (para páginas de treino/análise diária)
df_f_dia = df_f.copy()
if dia_md_sel and "Dia MD" in df_f_dia.columns:
    df_f_dia = df_f_dia[df_f_dia["Dia MD"].isin(dia_md_sel)]


# ═══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES GLOBAIS
# ═══════════════════════════════════════════════════════════════════════════════

def zscore_serie(serie: pd.Series) -> pd.Series:
    mu, sigma = serie.mean(), serie.std()
    if sigma == 0:
        return pd.Series([0.0] * len(serie), index=serie.index)
    return (serie - mu) / sigma

def cor_acwr(v):
    if pd.isna(v):      return "❓"
    if v > 1.5:         return "🔴 RISCO"
    if v > 1.3:         return "🟡 ATENÇÃO"
    if v >= 0.8:        return "🟢 OK"
    return "🔵 SUB-CARGA"

def calcular_acwr_global(df_base: pd.DataFrame):
    """Calcula ACWR para todos os jogadores usando calcular_acwr. Retorna dict jogador→último ACWR."""
    resultados = {}
    for jog in df_base["Jogador"].dropna().unique():
        sub = calcular_acwr(df_base, jog)
        if sub.empty or "ACWR" not in sub.columns:
            continue
        validos = sub.dropna(subset=["ACWR"])
        if not validos.empty:
            last = validos.iloc[-1]
            resultados[jog] = {
                "acwr": last["ACWR"],
                "posicao": last.get("Posição", "—"),
                "data": last["Data"],
                "ci_agudo": last.get("EWMA_Aguda", 0),
                "ci_cronico": last.get("EWMA_Crónica", 0),
            }
    return resultados

def gerar_pdf_html(conteudo_html: str, titulo: str) -> str:
    """Encapsula conteúdo HTML num documento imprimível."""
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
<div class="footer">Gerado automaticamente pelo Dashboard de Carga — Belenenses · {datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
</body>
</html>"""

def botao_download_html(html_str: str, nome_ficheiro: str, label: str = "📥 Exportar Relatório PDF"):
    b64 = base64.b64encode(html_str.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{nome_ficheiro}" style="display:inline-block;padding:10px 20px;background:#e63946;color:white;border-radius:8px;text-decoration:none;font-weight:bold;margin:8px 0">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)
    st.caption("💡 Abre o ficheiro no browser e usa Ctrl+P → 'Guardar como PDF' para exportar.")


# ── Log de alertas (ficheiro JSON local) ─────────────────────────────────────
LOG_PATH = Path("alertas_log.json")

def carregar_log():
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def guardar_alerta(jogador: str, tipo: str, descricao: str, valor: str):
    log = carregar_log()
    log.append({
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "jogador": jogador,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
    })
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

def registar_alertas_automaticos(acwr_dict: dict, df_base: pd.DataFrame):
    """Regista no log todos os alertas ativos neste momento."""
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]
        estado = cor_acwr(v)
        if "RISCO" in estado:
            guardar_alerta(jog, "ACWR", "ACWR acima de 1.5 — risco de lesão elevado", f"{v:.2f}")
        elif "ATENÇÃO" in estado:
            guardar_alerta(jog, "ACWR", "ACWR entre 1.3 e 1.5 — monitorizar", f"{v:.2f}")

    # Wellness
    wcols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
    ultima = df_base.sort_values("Data").groupby("Jogador").last().reset_index()
    for _, row in ultima.iterrows():
        jog = row["Jogador"]
        hi = row.get("Hooper Index", np.nan)
        if pd.notna(hi) and hi >= 14:
            guardar_alerta(jog, "Wellness", f"Hooper Index elevado ({hi:.0f}/20)", f"{hi:.0f}")

    # Vmáx
    if "Vel. Máx (km/h)" in df_base.columns:
        for jog in df_base["Jogador"].dropna().unique():
            sub = df_base[df_base["Jogador"] == jog].dropna(subset=["Data","Vel. Máx (km/h)"]).sort_values("Data")
            if sub.empty: continue
            rec = sub["Vel. Máx (km/h)"].max()
            lim = rec * 0.90
            acima = sub[sub["Vel. Máx (km/h)"] >= lim]
            if acima.empty:
                guardar_alerta(jog, "Vmáx", "Nunca atingiu ≥90% do recorde", "—")
                continue
            dias = (sub["Data"].max() - acima["Data"].max()).days
            if dias > 14:
                guardar_alerta(jog, "Vmáx", f"{dias} dias sem ≥90% Vmáx — risco de desadaptação", f"{dias}d")


# ── Glossário ─────────────────────────────────────────────────────────────────
GLOSSARIO = {
    "ACWR (Acute:Chronic Workload Ratio)": {
        "simples": "Compara a carga da semana atual com a média das últimas 4 semanas. É um indicador de risco de lesão.",
        "tecnico": "Rácio entre a carga aguda (EWMA 7 dias, λ=0.25) e a carga crónica (EWMA 28 dias, λ=2/29). Zona segura: 0.8–1.3.",
        "zonas": {"🟢 OK": "0.8 – 1.3", "🟡 Atenção": "1.3 – 1.5", "🔴 Risco": "> 1.5", "🔵 Sub-carga": "< 0.8"},
    },
    "Carga Interna (UA)": {
        "simples": "Mede o esforço percebido pelo jogador. Calculada multiplicando a duração da sessão pelo valor de PSE.",
        "tecnico": "Session-RPE method (Foster et al.): Carga Interna = PSE × Duração (min). Unidade arbitrária (UA).",
        "zonas": {},
    },
    "PSE (Perceção Subjetiva de Esforço)": {
        "simples": "Escala de 0 a 10 onde o jogador avalia o quão difícil foi a sessão. 10 = esforço máximo.",
        "tecnico": "Escala CR-10 de Borg modificada. Recolhida 20–30 min após o treino para evitar viés imediato.",
        "zonas": {"1–2": "Muito fácil", "3–4": "Fácil/Moderado", "5–6": "Difícil", "7–8": "Muito difícil", "9–10": "Máximo"},
    },
    "HSR (High Speed Running)": {
        "simples": "Distância percorrida a alta velocidade. Mede a exigência das corridas intensas numa sessão.",
        "tecnico": "Distância acumulada acima de um determinado limiar de velocidade (normalmente >19.8 km/h ou >21 km/h, dependendo do GPS).",
        "zonas": {},
    },
    "Sprint": {
        "simples": "Distância percorrida a velocidade máxima (sprints). Indica a exigência neuromuscular de alta intensidade.",
        "tecnico": "Distância acumulada acima do limiar de sprint (normalmente >25 km/h). Indicador de exposição a velocidades máximas.",
        "zonas": {},
    },
    "Z-Score": {
        "simples": "Indica se um valor está acima ou abaixo da média. 0 = na média. +2 = muito acima. -2 = muito abaixo.",
        "tecnico": "Z = (X − μ) / σ. Permite comparar métricas em escalas diferentes. Assume distribuição normal.",
        "zonas": {"🟢 Normal": "−1 a +1σ", "🟡 Acima": "+1 a +2σ", "🔴 Muito acima": "> +2σ", "🔵 Abaixo": "−1 a −2σ", "🟣 Muito abaixo": "< −2σ"},
    },
    "Monotonia (Foster)": {
        "simples": "Mede se o treino é sempre igual. Treinos muito repetitivos são prejudiciais mesmo com carga baixa.",
        "tecnico": "Monotonia = Média semanal CI / Desvio Padrão CI. Valores >2.0 indicam falta de variação na carga.",
        "zonas": {"🟢 Boa variação": "< 1.5", "🟡 Atenção": "1.5 – 2.0", "🔴 Excessiva": "> 2.0"},
    },
    "Strain (Foster)": {
        "simples": "Combina a carga total da semana com a repetição dos treinos. Alto strain = semana intensa E monótona.",
        "tecnico": "Strain = Carga Semanal Total × Monotonia. Elevado strain crónico associado a overtraining e lesão.",
        "zonas": {},
    },
    "Hooper Index": {
        "simples": "Questionário de bem-estar preenchido pelo jogador antes do treino. Soma de 4 fatores (sono, stress, dor muscular, humor). Quanto mais alto, pior.",
        "tecnico": "Soma de 4 itens numa escala de 1–5 cada (Sono, Stress, Dor Muscular, Humor). Range: 4–20. Valores ≥14 indicam acumulação de fadiga.",
        "zonas": {"🟢 Excelente": "4 – 8", "🟡 Normal": "9 – 13", "🔴 Preocupante": "≥ 14"},
    },
    "Vmáx (Velocidade Máxima)": {
        "simples": "A velocidade mais alta atingida pelo jogador. Importante expô-lo regularmente a ≥90% deste valor para manter a capacidade de sprint.",
        "tecnico": "Pico de velocidade registado pelo GPS. A exposição regular a ≥90% Vmáx é crítica para prevenção de lesões musculares (Malone et al., 2017).",
        "zonas": {"🟢 OK": "< 7 dias sem ≥90%", "🟡 Atenção": "7–14 dias", "🔴 Risco": "> 14 dias"},
    },
    "Acc / Dcc (Acelerações / Desacelerações)": {
        "simples": "Número de mudanças bruscas de velocidade. Elevado número indica sessão com muita intensidade neuromuscular.",
        "tecnico": "Contagem de eventos acima de um limiar (normalmente ≥3 m/s²). Alto impacto nos tecidos musculotendinosos.",
        "zonas": {},
    },
}



# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: ALERTAS DO DIA
# ═══════════════════════════════════════════════════════════════════════════════
if pagina == "🚨 Alertas do Dia":
    hoje = datetime.now()
    st.title(f"🚨 Alertas do Dia — {hoje.strftime('%d/%m/%Y')}")
    st.caption("Painel de semáforo para decisão rápida no treino")

    acwr_dict = calcular_acwr_global(df)
    registar_alertas_automaticos(acwr_dict, df)

    # ── Bloco 1: ACWR ─────────────────────────────────────────────────────────
    st.markdown('<p class="section-title">🔴 ACWR — Estado de Cada Jogador</p>', unsafe_allow_html=True)

    risco, atencao, ok_list, sub = [], [], [], []
    for jog, dados in acwr_dict.items():
        v = dados["acwr"]
        estado = cor_acwr(v)
        if "RISCO"    in estado: risco.append((jog, v, dados["posicao"]))
        elif "ATENÇÃO" in estado: atencao.append((jog, v, dados["posicao"]))
        elif "OK"      in estado: ok_list.append((jog, v, dados["posicao"]))
        else:                      sub.append((jog, v, dados["posicao"]))

    def card_jogadores(lista, emoji, cor_bg, titulo):
        if not lista:
            return
        st.markdown(f"**{emoji} {titulo}**")
        cols = st.columns(min(len(lista), 5))
        for i, (jog, v, pos) in enumerate(lista):
            cols[i % 5].markdown(
                f'<div style="background:{cor_bg};border-radius:10px;padding:10px;text-align:center;margin:4px">'
                f'<b style="font-size:1rem">{jog}</b><br>'
                f'<span style="font-size:0.8rem;color:#eee">{pos}</span><br>'
                f'<b style="font-size:1.3rem">{v:.2f}</b></div>',
                unsafe_allow_html=True
            )

    card_jogadores(risco,   "🔴", "#7b1d1d", "RISCO — Reduzir Carga")
    card_jogadores(atencao, "🟡", "#7b5b00", "ATENÇÃO — Monitorizar")
    card_jogadores(ok_list, "🟢", "#1a4731", "OK — Treino Normal")
    card_jogadores(sub,     "🔵", "#0d3b5e", "SUB-CARGA — Aumentar Estímulo")

    st.divider()

    # ── Bloco 2: Wellness de hoje / última sessão ─────────────────────────────
    st.markdown('<p class="section-title">💤 Wellness — Última Sessão Registada</p>', unsafe_allow_html=True)

    wcols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
    wcols_disp = [c for c in wcols if c in df.columns]

    if wcols_disp:
        ultima_por_jog = df.sort_values("Data").groupby("Jogador").last().reset_index()
        alertas_wellness = []
        for _, row in ultima_por_jog.iterrows():
            hi = row.get("Hooper Index", np.nan)
            sono = row.get("Sono (1-5)", np.nan)
            stress = row.get("Stress (1-5)", np.nan)
            dor = row.get("Dor Musc. (1-5)", np.nan)
            problemas = []
            if pd.notna(hi) and hi >= 14:    problemas.append(f"Hooper {hi:.0f}/20 🔴")
            if pd.notna(sono) and sono <= 2:  problemas.append(f"Sono {sono:.0f}/5 🔴")
            if pd.notna(stress) and stress >= 4: problemas.append(f"Stress {stress:.0f}/5 🔴")
            if pd.notna(dor) and dor >= 4:    problemas.append(f"Dor {dor:.0f}/5 🔴")
            if problemas:
                alertas_wellness.append((row["Jogador"], problemas))

        if alertas_wellness:
            for jog, probs in alertas_wellness:
                st.markdown(f"⚠️ **{jog}**: {' · '.join(probs)}")
        else:
            st.success("✅ Nenhum alerta de Wellness — todos os jogadores dentro dos parâmetros normais.")

    st.divider()

    # ── Bloco 3: Vmáx — quem não atinge ≥90% há mais de 7 dias ──────────────
    st.markdown('<p class="section-title">🏃 Vmáx — Exposição a Alta Velocidade</p>', unsafe_allow_html=True)

    if "Vel. Máx (km/h)" in df.columns:
        alertas_vmax = []
        for jog in df["Jogador"].dropna().unique():
            sub_v = df[df["Jogador"] == jog].dropna(subset=["Data", "Vel. Máx (km/h)"]).sort_values("Data")
            if sub_v.empty: continue
            rec = sub_v["Vel. Máx (km/h)"].max()
            lim90 = rec * 0.90
            acima = sub_v[sub_v["Vel. Máx (km/h)"] >= lim90]
            if acima.empty:
                alertas_vmax.append((jog, 999, rec))
                continue
            dias = (sub_v["Data"].max() - acima["Data"].max()).days
            if dias > 7:
                alertas_vmax.append((jog, dias, rec))

        if alertas_vmax:
            alertas_vmax.sort(key=lambda x: -x[1])
            for jog, dias, rec in alertas_vmax:
                d_str = f"{dias} dias" if dias < 999 else "nunca registado"
                emoji = "🔴" if dias > 14 else "🟡"
                st.markdown(f"{emoji} **{jog}** — {d_str} sem ≥90% Vmáx (recorde: {rec:.1f} km/h)")
        else:
            st.success("✅ Todos os jogadores atingiram ≥90% Vmáx nos últimos 7 dias.")

    st.divider()

    # ── Bloco 4: Lesões ativas ────────────────────────────────────────────────
    st.markdown('<p class="section-title">🩺 Lesões & Indisponibilidades Ativas</p>', unsafe_allow_html=True)

    try:
        df_les = pd.read_excel(excel_path, sheet_name="Lesões", engine="openpyxl")
        df_les.columns = [str(c).strip() for c in df_les.columns]
        col_estado = next((c for c in df_les.columns if "estado" in c.lower() or "ativo" in c.lower() or "situação" in c.lower()), None)
        col_jog    = next((c for c in df_les.columns if "jogador" in c.lower()), None)

        if col_jog:
            if col_estado:
                ativos = df_les[df_les[col_estado].astype(str).str.lower().isin(["ativo", "activo", "sim", "yes", "1", "true"])]
            else:
                ativos = df_les
            if not ativos.empty:
                for _, row in ativos.iterrows():
                    info = " · ".join([f"{col}: {row[col]}" for col in ativos.columns if col != col_jog and pd.notna(row[col])])
                    st.markdown(f"🩹 **{row[col_jog]}** — {info}")
            else:
                st.success("✅ Sem lesões ativas registadas.")
        else:
            st.info("Folha 'Lesões' encontrada mas sem coluna 'Jogador' reconhecida.")
    except Exception:
        st.info("ℹ️ Ainda sem folha 'Lesões' no Excel. Adiciona uma folha chamada **Lesões** para ver os alertas aqui.")

    st.divider()

    # ── Exportar relatório diário ─────────────────────────────────────────────
    st.markdown('<p class="section-title">📥 Exportar Relatório do Dia</p>', unsafe_allow_html=True)

    linhas_risco = "".join([
        f'<tr><td>{j}</td><td>{p}</td><td class="alerta-red">{v:.2f} — RISCO</td></tr>'
        for j, v, p in risco
    ])
    linhas_atencao = "".join([
        f'<tr><td>{j}</td><td>{p}</td><td class="alerta-yellow">{v:.2f} — ATENÇÃO</td></tr>'
        for j, v, p in atencao
    ])
    linhas_ok = "".join([
        f'<tr><td>{j}</td><td>{p}</td><td class="alerta-green">{v:.2f} — OK</td></tr>'
        for j, v, p in ok_list
    ])
    linhas_sub = "".join([
        f'<tr><td>{j}</td><td>{p}</td><td class="alerta-blue">{v:.2f} — SUB-CARGA</td></tr>'
        for j, v, p in sub
    ])

    linhas_wellness = "".join([
        f'<tr><td>{j}</td><td>{"<br>".join(p)}</td></tr>'
        for j, p in (alertas_wellness if wcols_disp else [])
    ])

    linhas_vmax = "".join([
        f'<tr><td>{j}</td><td>{"🔴" if d>14 else "🟡"} {d} dias s/ ≥90% (rec: {r:.1f} km/h)</td></tr>'
        for j, d, r in (alertas_vmax if "Vel. Máx (km/h)" in df.columns else [])
        if d > 7
    ])

    html_rel = gerar_pdf_html(f"""
<h1>Relatório Diário — {hoje.strftime("%d/%m/%Y")}</h1>
<h2>ACWR — Estado dos Jogadores</h2>
<table><tr><th>Jogador</th><th>Posição</th><th>Estado</th></tr>
{linhas_risco}{linhas_atencao}{linhas_ok}{linhas_sub}
</table>
{"<h2>Alertas de Wellness</h2><table><tr><th>Jogador</th><th>Alertas</th></tr>" + linhas_wellness + "</table>" if linhas_wellness else "<p>✅ Wellness sem alertas.</p>"}
{"<h2>Alertas Vmáx</h2><table><tr><th>Jogador</th><th>Estado</th></tr>" + linhas_vmax + "</table>" if linhas_vmax else "<p>✅ Vmáx sem alertas.</p>"}
""", f"Relatorio_Diario_{hoje.strftime('%Y%m%d')}.html")

    botao_download_html(html_rel, f"Relatorio_Diario_{hoje.strftime('%Y%m%d')}.html", "📥 Exportar Relatório Diário (PDF)")



# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: EQUIPA
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏟️ Equipa":
    df_f = df_f_dia  # aplica filtro Dia MD
    st.title("🏟️ Resumo da Equipa")
    st.caption(f"{len(df_f)} registos · {df_f['Jogador'].nunique()} jogadores · {len(mc_sel)} microciclo(s) selecionado(s)")

    # ── KPIs globais ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Sessões Totais",   f"{len(df_f):,}")
    c2.metric("Dist. Média (m)",  f"{df_f['Distância Total (m)'].mean():,.0f}" if "Distância Total (m)" in df_f else "—")
    c3.metric("PSE Média",        f"{df_f['PSE Sessão'].mean():.1f}" if "PSE Sessão" in df_f else "—")
    c4.metric("CI Médio",         f"{df_f['Carga Interna'].mean():,.0f}" if "Carga Interna" in df_f else "—")
    c5.metric("Hooper Médio",     f"{df_f['Hooper Index'].mean():.1f}" if "Hooper Index" in df_f else "—")

    st.divider()

    # ── ACWR por jogador (último valor) ───────────────────────────────────────
    st.markdown('<p class="section-title">🚦 ACWR — Risco por Jogador (última sessão)</p>', unsafe_allow_html=True)

    acwr_rows = []
    for jog in jogadores:
        sub = calcular_acwr(df[df["Microciclo (Nr)"].isin(mc_sel)] if mc_sel else df, jog)
        if not sub.empty and "ACWR" in sub.columns and sub["ACWR"].notna().any():
            last = sub.dropna(subset=["ACWR"]).iloc[-1]
            acwr_rows.append({
                "Jogador": jog,
                "Posição": last.get("Posição", ""),
                "ACWR": round(last["ACWR"], 2),
                "CI Agudo": round(last.get("EWMA_Aguda", 0)),
                "CI Crónico": round(last.get("EWMA_Crónica", 0)),
                "Estado": cor_acwr(last["ACWR"]),
            })

    if acwr_rows:
        df_acwr = pd.DataFrame(acwr_rows).sort_values("ACWR", ascending=False)
        df_acwr["ACWR"] = pd.to_numeric(df_acwr["ACWR"], errors="coerce").fillna(0)

        fig_acwr = go.Figure()
        cores = []
        for _, row in df_acwr.iterrows():
            v = row["ACWR"]
            if v > 1.5:    cor = "#e74c3c"
            elif v > 1.3:  cor = "#f39c12"
            elif v >= 0.8: cor = "#2ecc71"
            else:           cor = "#3498db"
            cores.append(cor)

        fig_acwr.add_trace(go.Bar(
            x=df_acwr["Jogador"], y=df_acwr["ACWR"],
            marker_color=cores, text=df_acwr["ACWR"].round(2), textposition="outside",
        ))
        fig_acwr.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c",  annotation_text="Risco (1.5)")
        fig_acwr.add_hline(y=1.3, line_dash="dash", line_color="#f39c12",  annotation_text="Atenção (1.3)")
        fig_acwr.add_hline(y=0.8, line_dash="dash", line_color="#3498db",  annotation_text="Sub-carga (0.8)")
        fig_acwr.update_layout(
            yaxis_title="ACWR", height=380, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            showlegend=False, margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig_acwr, use_container_width=True)

        # tabela resumo
        st.dataframe(
            df_acwr.set_index("Jogador")[["Posição", "ACWR", "CI Agudo", "CI Crónico", "Estado"]],
            use_container_width=True,
        )

    st.divider()

    # ── Carga Interna por microciclo ──────────────────────────────────────────
    st.markdown('<p class="section-title">📈 Carga Interna Média por Microciclo</p>', unsafe_allow_html=True)

    if "Carga Interna" in df_f and "Microciclo (Nr)" in df_f:
        ci_mc = df_f.groupby(["Microciclo (Nr)", "Jogador"])["Carga Interna"].mean().reset_index()
        ci_mc_mean = df_f.groupby("Microciclo (Nr)")["Carga Interna"].mean().reset_index()
        fig_ci = px.line(ci_mc_mean, x="Microciclo (Nr)", y="Carga Interna",
                         markers=True, labels={"Carga Interna": "CI Médio", "Microciclo (Nr)": "Microciclo"})
        fig_ci.update_traces(line_color="#e63946", line_width=3, marker_size=8)
        fig_ci.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=20))
        st.plotly_chart(fig_ci, use_container_width=True)

    # ── Distribuição GPS ──────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-title">🏃 Métricas GPS — Distribuição por Jogador</p>', unsafe_allow_html=True)

    metrica_gps = st.selectbox("Métrica", ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)", "Acc (n)", "Dcc (n)"])
    if metrica_gps in df_f.columns:
        df_gps = df_f.groupby("Jogador")[metrica_gps].mean().reset_index().sort_values(metrica_gps, ascending=True)
        fig_gps = px.bar(df_gps, x=metrica_gps, y="Jogador", orientation="h",
                         color=metrica_gps, color_continuous_scale="Reds",
                         labels={metrica_gps: metrica_gps, "Jogador": ""})
        fig_gps.update_layout(height=max(300, len(df_gps)*35), plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                               coloraxis_showscale=False, margin=dict(t=10))
        st.plotly_chart(fig_gps, use_container_width=True)

    # ── Wellness da equipa ────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-title">💤 Wellness da Equipa (médias)</p>', unsafe_allow_html=True)

    wellness_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
    wellness_disp = [c for c in wellness_cols if c in df_f.columns]

    if wellness_disp:
        w_mean = df_f[wellness_disp].mean().reset_index()
        w_mean.columns = ["Métrica", "Média"]
        fig_w = px.bar(w_mean, x="Métrica", y="Média", color="Métrica",
                       color_discrete_sequence=px.colors.qualitative.Pastel,
                       text=w_mean["Média"].round(1))
        fig_w.update_traces(textposition="outside")
        fig_w.update_layout(height=320, showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10))
        st.plotly_chart(fig_w, use_container_width=True)

    # ── Conclusões automáticas ────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)

    insights = []

    if acwr_rows:
        em_risco    = [r["Jogador"] for r in acwr_rows if "RISCO"    in r["Estado"]]
        em_atencao  = [r["Jogador"] for r in acwr_rows if "ATENÇÃO"  in r["Estado"]]
        sub_carga   = [r["Jogador"] for r in acwr_rows if "SUB-CARGA" in r["Estado"]]

        if em_risco:
            insights.append(f"🔴 **Risco de lesão elevado**: {', '.join(em_risco)} — ACWR > 1.5. Reduzir carga imediatamente.")
        if em_atencao:
            insights.append(f"🟡 **Monitorizar de perto**: {', '.join(em_atencao)} — ACWR entre 1.3 e 1.5.")
        if sub_carga:
            insights.append(f"🔵 **Sub-carga**: {', '.join(sub_carga)} — ACWR < 0.8. Avaliar razão (lesão/recuperação?).")
        if not em_risco and not em_atencao:
            insights.append("🟢 **Toda a equipa dentro do intervalo seguro de ACWR (0.8–1.3).**")

    if "Hooper Index" in df_f.columns:
        h_mean = df_f["Hooper Index"].mean()
        if h_mean >= 14:
            insights.append(f"⚠️ **Hooper Index médio elevado** ({h_mean:.1f}/20) — equipa com sinais de fadiga/stress acumulado.")
        elif h_mean <= 8:
            insights.append(f"✅ **Hooper Index médio excelente** ({h_mean:.1f}/20) — bem-estar geral muito positivo.")
        else:
            insights.append(f"ℹ️ **Hooper Index médio** ({h_mean:.1f}/20) — bem-estar dentro dos parâmetros normais.")

    if "PSE Sessão" in df_f.columns:
        pse_mean = df_f["PSE Sessão"].mean()
        insights.append(f"📊 **PSE média da equipa**: {pse_mean:.1f}/10 nos microciclos selecionados.")

    if "Distância Total (m)" in df_f.columns:
        dist_mean = df_f["Distância Total (m)"].mean()
        insights.append(f"📏 **Distância média por sessão**: {dist_mean:,.0f} m.")

    for ins in insights:
        st.markdown(ins)


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: JOGADOR INDIVIDUAL
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "👤 Jogador Individual":
    df_f = df_f_dia
    st.title(f"👤 {jogador_sel}")

    df_jog = df[df["Jogador"] == jogador_sel].sort_values("Data")
    df_jog_f = df_f[df_f["Jogador"] == jogador_sel].sort_values("Data")

    if df_jog_f.empty:
        st.warning("Sem dados para este jogador nos filtros selecionados.")
        st.stop()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sessões",          f"{len(df_jog_f)}")
    c2.metric("Dist. Média (m)",  f"{df_jog_f['Distância Total (m)'].mean():,.0f}")
    c3.metric("PSE Média",        f"{df_jog_f['PSE Sessão'].mean():.1f}")
    c4.metric("CI Médio",         f"{df_jog_f['Carga Interna'].mean():,.0f}")

    st.divider()

    # ACWR ao longo do tempo
    st.markdown('<p class="section-title">📉 ACWR ao Longo do Tempo</p>', unsafe_allow_html=True)
    df_acwr_jog = calcular_acwr(df_jog, jogador_sel)
    if "ACWR" in df_acwr_jog.columns:
        fig_acwr_t = go.Figure()
        fig_acwr_t.add_trace(go.Scatter(x=df_acwr_jog["Data"], y=df_acwr_jog["ACWR"],
                                         mode="lines+markers", name="ACWR", line_color="#e63946"))
        fig_acwr_t.add_hrect(y0=0.8, y1=1.3, fillcolor="green",   opacity=0.08, line_width=0)
        fig_acwr_t.add_hrect(y0=1.3, y1=1.5, fillcolor="orange",  opacity=0.1,  line_width=0)
        fig_acwr_t.add_hrect(y0=1.5, y1=3.0, fillcolor="red",     opacity=0.1,  line_width=0)
        fig_acwr_t.add_hline(y=1.5, line_dash="dash", line_color="#e74c3c", annotation_text="1.5")
        fig_acwr_t.add_hline(y=0.8, line_dash="dash", line_color="#3498db", annotation_text="0.8")
        fig_acwr_t.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                                   yaxis_title="ACWR", margin=dict(t=10))
        st.plotly_chart(fig_acwr_t, use_container_width=True)

    # Carga Interna por sessão
    st.divider()
    st.markdown('<p class="section-title">⚡ Carga Interna por Sessão</p>', unsafe_allow_html=True)
    fig_ci_j = px.bar(df_jog_f, x="Data", y="Carga Interna",
                       color="Dia MD" if "Dia MD" in df_jog_f.columns else None,
                       labels={"Carga Interna": "CI", "Data": "Data"})
    fig_ci_j.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                             paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10))
    st.plotly_chart(fig_ci_j, use_container_width=True)

    # GPS ao longo do tempo
    st.divider()
    st.markdown('<p class="section-title">🏃 Evolução GPS</p>', unsafe_allow_html=True)
    metricas_gps = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)"]
    metricas_gps_disp = [m for m in metricas_gps if m in df_jog_f.columns]

    fig_gps_j = make_subplots(rows=2, cols=2,
                               subplot_titles=metricas_gps_disp,
                               vertical_spacing=0.18, horizontal_spacing=0.1)
    posicoes_grid = [(1,1),(1,2),(2,1),(2,2)]
    cores_gps = ["#e63946","#457b9d","#2ecc71","#f39c12"]

    for i, met in enumerate(metricas_gps_disp[:4]):
        r, c = posicoes_grid[i]
        fig_gps_j.add_trace(
            go.Scatter(x=df_jog_f["Data"], y=df_jog_f[met],
                       mode="lines+markers", name=met,
                       line_color=cores_gps[i], showlegend=False),
            row=r, col=c
        )

    fig_gps_j.update_layout(height=460, plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30))
    st.plotly_chart(fig_gps_j, use_container_width=True)

    # Wellness
    st.divider()
    st.markdown('<p class="section-title">💤 Wellness (Hooper Index)</p>', unsafe_allow_html=True)
    w_cols = ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"]
    w_disp = [c for c in w_cols if c in df_jog_f.columns]
    if w_disp:
        fig_w_j = px.line(df_jog_f, x="Data", y=w_disp, markers=True)
        fig_w_j.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                               legend_title="", margin=dict(t=10))
        st.plotly_chart(fig_w_j, use_container_width=True)

    # Tabela de dados brutos
    st.divider()
    with st.expander("📋 Ver todos os registos"):
        st.dataframe(df_jog_f.sort_values("Data", ascending=False), use_container_width=True)

    # Conclusões individuais
    st.divider()
    st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)

    df_acwr_all = calcular_acwr(df_jog, jogador_sel)
    if "ACWR" in df_acwr_all.columns and df_acwr_all["ACWR"].notna().any():
        acwr_last = df_acwr_all.dropna(subset=["ACWR"]).iloc[-1]["ACWR"]
        estado = cor_acwr(acwr_last)
        st.markdown(f"- **Último ACWR**: `{acwr_last:.2f}` → {estado}")

    if "Hooper Index" in df_jog_f.columns:
        h = df_jog_f["Hooper Index"].mean()
        if h >= 14:
            st.markdown(f"- 😟 **Hooper Index elevado** ({h:.1f}) — possível acumulação de stress/fadiga.")
        elif h <= 8:
            st.markdown(f"- 😃 **Hooper Index excelente** ({h:.1f}) — jogador em ótimo estado.")
        else:
            st.markdown(f"- 😐 **Hooper Index normal** ({h:.1f}).")

    if "Vel. Máx (km/h)" in df_jog_f.columns:
        vmax = df_jog_f["Vel. Máx (km/h)"].max()
        vmax_mean = df_jog_f["Vel. Máx (km/h)"].mean()
        st.markdown(f"- **Velocidade máxima registada**: {vmax:.1f} km/h (média: {vmax_mean:.1f} km/h).")


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: COMPARAÇÃO POR POSIÇÃO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📊 Comparação por Posição":
    df_f = df_f_dia
    st.title("📊 Comparação por Posição")

    if "Posição" not in df_f.columns or df_f["Posição"].isna().all():
        st.warning("Coluna 'Posição' não encontrada nos dados.")
        st.stop()

    metrica_pos = st.selectbox("Métrica a comparar", [
        "Distância Total (m)", "HSR (m)", "Sprint (m)",
        "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)", "Hooper Index"
    ])

    if metrica_pos in df_f.columns:
        # Box plot por posição
        fig_box = px.box(df_f, x="Posição", y=metrica_pos,
                         color="Posição", points="all",
                         hover_data=["Jogador", "Data"] if "Data" in df_f.columns else ["Jogador"],
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig_box.update_layout(height=420, plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                               showlegend=False, margin=dict(t=20))
        st.plotly_chart(fig_box, use_container_width=True)

        # Médias por posição e jogador
        st.markdown('<p class="section-title">Médias por Posição e Jogador</p>', unsafe_allow_html=True)
        df_pos = df_f.groupby(["Posição", "Jogador"])[metrica_pos].mean().reset_index()
        df_pos.columns = ["Posição", "Jogador", metrica_pos]
        df_pos = df_pos.sort_values([metrica_pos], ascending=False)

        fig_jog_pos = px.bar(df_pos, x="Jogador", y=metrica_pos,
                              color="Posição", barmode="group",
                              color_discrete_sequence=px.colors.qualitative.Bold,
                              labels={metrica_pos: metrica_pos, "Jogador": ""})
        fig_jog_pos.update_layout(height=360, plot_bgcolor="rgba(0,0,0,0)",
                                   paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10))
        st.plotly_chart(fig_jog_pos, use_container_width=True)

    # Radar por posição
    st.divider()
    st.markdown('<p class="section-title">📡 Radar de Perfil por Posição</p>', unsafe_allow_html=True)

    radar_cols = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "PSE Sessão"]
    radar_disp = [c for c in radar_cols if c in df_f.columns]

    if radar_disp:
        pos_means = df_f.groupby("Posição")[radar_disp].mean().reset_index()
        # Normalizar 0-100
        for col in radar_disp:
            max_v = pos_means[col].max()
            pos_means[col] = pos_means[col] / max_v * 100 if max_v > 0 else 0

        fig_radar = go.Figure()
        cores_radar = px.colors.qualitative.Bold
        for i, (_, row) in enumerate(pos_means.iterrows()):
            vals = list(row[radar_disp]) + [row[radar_disp[0]]]
            cats = radar_disp + [radar_disp[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=cats, fill="toself",
                name=row["Posição"],
                line_color=cores_radar[i % len(cores_radar)],
                opacity=0.75,
            ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=440, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
        )
        st.plotly_chart(fig_radar, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: VMÁX MONITOR
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏃 Vmáx Monitor":
    st.title("🏃 Monitorização de Velocidade Máxima")
    st.caption("Recordes · Exposição a altas velocidades · Alertas de inatividade")

    # ── Calcular métricas de Vmáx a partir de BD_Carga ───────────────────────
    def calcular_vmax_monitor(df_base: pd.DataFrame):
        """Calcula perfil de Vmáx para todos os jogadores."""
        if "Vel. Máx (km/h)" not in df_base.columns or "Data" not in df_base.columns:
            return pd.DataFrame()

        rows = []
        for jog in sorted(df_base["Jogador"].dropna().unique()):
            sub = df_base[df_base["Jogador"] == jog].copy()
            sub = sub.dropna(subset=["Data", "Vel. Máx (km/h)"])
            if sub.empty:
                continue

            sub = sub.sort_values("Data")
            vmax_record = sub["Vel. Máx (km/h)"].max()
            posicao = sub["Posição"].iloc[-1] if "Posição" in sub.columns else "—"

            # Limiar 90% do recorde
            lim_90 = vmax_record * 0.90
            lim_85 = vmax_record * 0.85
            lim_95 = vmax_record * 0.95

            # Última sessão com Vmáx ≥ 90% do recorde
            sub_90 = sub[sub["Vel. Máx (km/h)"] >= lim_90]
            if not sub_90.empty:
                ultima_data_90 = sub_90["Data"].max()
                dias_sem_90 = (sub["Data"].max() - ultima_data_90).days
            else:
                ultima_data_90 = pd.NaT
                dias_sem_90 = 999

            # Última sessão com Vmáx ≥ 95%
            sub_95 = sub[sub["Vel. Máx (km/h)"] >= lim_95]
            if not sub_95.empty:
                ultima_data_95 = sub_95["Data"].max()
                dias_sem_95 = (sub["Data"].max() - ultima_data_95).days
            else:
                ultima_data_95 = pd.NaT
                dias_sem_95 = 999

            # Total sessões ≥90%
            total_sess_90 = len(sub_90)
            total_sess = len(sub)
            pct_sess_90 = total_sess_90 / total_sess if total_sess > 0 else 0

            # Vmáx mais recente
            vmax_ultima = sub.iloc[-1]["Vel. Máx (km/h)"]
            pct_record = vmax_ultima / vmax_record if vmax_record > 0 else 0

            # Alerta
            if dias_sem_90 > 14:
                alerta = "🔴 RISCO"
                alerta_cor = "#e74c3c"
            elif dias_sem_90 > 7:
                alerta = "🟡 ATENÇÃO"
                alerta_cor = "#f39c12"
            else:
                alerta = "🟢 OK"
                alerta_cor = "#2ecc71"

            rows.append({
                "Jogador": jog,
                "Posição": posicao,
                "Vmáx Record (km/h)": round(vmax_record, 1),
                "Última Vmáx (km/h)": round(vmax_ultima, 1),
                "% do Recorde": round(pct_record * 100, 1),
                "Última Data ≥90%": ultima_data_90,
                "Dias s/ ≥90% Vmáx": int(dias_sem_90) if dias_sem_90 < 999 else "Nunca",
                "Última Data ≥95%": ultima_data_95,
                "Dias s/ ≥95% Vmáx": int(dias_sem_95) if dias_sem_95 < 999 else "Nunca",
                "Sessões ≥90%": total_sess_90,
                "% Sessões ≥90%": round(pct_sess_90 * 100, 1),
                "Alerta": alerta,
                "_alerta_cor": alerta_cor,
                "_lim_90": round(lim_90, 1),
                "_lim_85": round(lim_85, 1),
                "_lim_95": round(lim_95, 1),
            })

        return pd.DataFrame(rows)

    df_vmax = calcular_vmax_monitor(df)

    if df_vmax.empty:
        st.warning("Dados de Vmáx não encontrados. Certifica-te que a folha BD_Carga tem a coluna 'Vel. Máx (km/h)'.")
        st.stop()

    # ── SECÇÃO A — Perfil geral da equipa ────────────────────────────────────
    st.markdown('<p class="section-title">A — Perfil de Velocidade & Alerta de Inatividade</p>', unsafe_allow_html=True)

    # KPIs rápidos
    c1, c2, c3, c4 = st.columns(4)
    em_risco_v   = df_vmax[df_vmax["Alerta"] == "🔴 RISCO"]
    em_atencao_v = df_vmax[df_vmax["Alerta"] == "🟡 ATENÇÃO"]
    em_ok_v      = df_vmax[df_vmax["Alerta"] == "🟢 OK"]
    c1.metric("🔴 Em Risco (>14 dias s/ ≥90%)",   len(em_risco_v))
    c2.metric("🟡 Em Atenção (8-14 dias)",          len(em_atencao_v))
    c3.metric("🟢 OK (<7 dias)",                    len(em_ok_v))
    c4.metric("Vmáx Record da Equipa",              f"{df_vmax['Vmáx Record (km/h)'].max():.1f} km/h")

    st.divider()

    # Gráfico de barras — Vmáx Record vs Última Vmáx
    st.markdown('<p class="section-title">Vmáx Record vs Última Vmáx por Jogador</p>', unsafe_allow_html=True)

    df_vmax_sorted = df_vmax.sort_values("Vmáx Record (km/h)", ascending=True)

    fig_vmax_bars = go.Figure()
    fig_vmax_bars.add_trace(go.Bar(
        y=df_vmax_sorted["Jogador"],
        x=df_vmax_sorted["Vmáx Record (km/h)"],
        name="Vmáx Record",
        orientation="h",
        marker_color="#e63946",
        opacity=0.85,
    ))
    fig_vmax_bars.add_trace(go.Bar(
        y=df_vmax_sorted["Jogador"],
        x=df_vmax_sorted["Última Vmáx (km/h)"],
        name="Última Vmáx",
        orientation="h",
        marker_color="#457b9d",
        opacity=0.85,
    ))
    fig_vmax_bars.update_layout(
        barmode="overlay",
        height=max(320, len(df_vmax_sorted) * 42),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis_title="km/h",
        legend=dict(orientation="h", y=1.05),
        margin=dict(t=30, b=10),
    )
    st.plotly_chart(fig_vmax_bars, use_container_width=True)

    # Gráfico de dias sem ≥90% Vmáx
    st.markdown('<p class="section-title">Dias sem Atingir ≥90% Vmáx Record</p>', unsafe_allow_html=True)

    df_dias = df_vmax.copy()
    df_dias["Dias_num"] = pd.to_numeric(df_dias["Dias s/ ≥90% Vmáx"], errors="coerce").fillna(999)
    df_dias = df_dias.sort_values("Dias_num", ascending=False)

    cores_dias = []
    for _, row in df_dias.iterrows():
        d = row["Dias_num"]
        if d > 14:   cores_dias.append("#e74c3c")
        elif d > 7:  cores_dias.append("#f39c12")
        else:        cores_dias.append("#2ecc71")

    fig_dias = go.Figure(go.Bar(
        x=df_dias["Jogador"],
        y=df_dias["Dias_num"],
        marker_color=cores_dias,
        text=[f"{int(d)}d" if d < 999 else "—" for d in df_dias["Dias_num"]],
        textposition="outside",
    ))
    fig_dias.add_hline(y=14, line_dash="dash", line_color="#e74c3c", annotation_text="Risco >14 dias")
    fig_dias.add_hline(y=7,  line_dash="dash", line_color="#f39c12", annotation_text="Atenção >7 dias")
    fig_dias.update_layout(
        yaxis_title="Dias",
        height=360,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(fig_dias, use_container_width=True)

    # % do Recorde — gauge style bar
    st.markdown('<p class="section-title">% do Recorde Pessoal (Última Sessão)</p>', unsafe_allow_html=True)

    df_pct = df_vmax.sort_values("% do Recorde", ascending=True)
    cores_pct = []
    for v in df_pct["% do Recorde"]:
        if v >= 95:   cores_pct.append("#2ecc71")
        elif v >= 90: cores_pct.append("#f39c12")
        else:         cores_pct.append("#e74c3c")

    fig_pct = go.Figure(go.Bar(
        y=df_pct["Jogador"],
        x=df_pct["% do Recorde"],
        orientation="h",
        marker_color=cores_pct,
        text=[f"{v:.1f}%" for v in df_pct["% do Recorde"]],
        textposition="outside",
    ))
    fig_pct.add_vline(x=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
    fig_pct.add_vline(x=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
    fig_pct.update_layout(
        xaxis=dict(title="% do Recorde", range=[70, 105]),
        height=max(300, len(df_pct) * 40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        margin=dict(t=10, b=10),
    )
    st.plotly_chart(fig_pct, use_container_width=True)

    # Tabela resumo Secção A
    st.markdown('<p class="section-title">Tabela Resumo — Todos os Jogadores</p>', unsafe_allow_html=True)
    cols_tabela = ["Jogador", "Posição", "Vmáx Record (km/h)", "Última Vmáx (km/h)",
                   "% do Recorde", "Dias s/ ≥90% Vmáx", "Dias s/ ≥95% Vmáx",
                   "Sessões ≥90%", "% Sessões ≥90%", "Alerta"]
    st.dataframe(df_vmax[cols_tabela].set_index("Jogador"), use_container_width=True)

    st.divider()

    # ── SECÇÃO B — Histórico individual ──────────────────────────────────────
    st.markdown('<p class="section-title">B — Histórico de Velocidade Individual</p>', unsafe_allow_html=True)

    jog_vmax = st.selectbox("Seleciona o Jogador", sorted(df["Jogador"].dropna().unique()), key="vmax_jog")

    sub_hist = df[df["Jogador"] == jog_vmax].dropna(subset=["Data", "Vel. Máx (km/h)"]).sort_values("Data")

    if not sub_hist.empty:
        vmax_rec = sub_hist["Vel. Máx (km/h)"].max()
        lim_90 = vmax_rec * 0.90
        lim_85 = vmax_rec * 0.85
        lim_95 = vmax_rec * 0.95

        # % do recorde por sessão
        sub_hist = sub_hist.copy()
        sub_hist["% Record"] = (sub_hist["Vel. Máx (km/h)"] / vmax_rec * 100).round(1)

        # KPIs do jogador
        info_jog = df_vmax[df_vmax["Jogador"] == jog_vmax]
        if not info_jog.empty:
            r = info_jog.iloc[0]
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Vmáx Record", f"{r['Vmáx Record (km/h)']} km/h")
            k2.metric("Limiar 90%",  f"{r['_lim_90']} km/h")
            k3.metric("Limiar 95%",  f"{r['_lim_95']} km/h")
            k4.metric("Alerta",      r["Alerta"])

        # Gráfico histórico Vmáx
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=sub_hist["Data"], y=sub_hist["Vel. Máx (km/h)"],
            mode="lines+markers", name="Vmáx Sessão",
            line_color="#e63946", line_width=2, marker_size=7,
        ))
        fig_hist.add_hline(y=vmax_rec, line_dash="solid",  line_color="#f39c12", line_width=2,
                            annotation_text=f"Recorde {vmax_rec:.1f} km/h", annotation_position="top left")
        fig_hist.add_hline(y=lim_95,   line_dash="dash",   line_color="#2ecc71",
                            annotation_text=f"≥95% ({lim_95:.1f})", annotation_position="bottom right")
        fig_hist.add_hline(y=lim_90,   line_dash="dash",   line_color="#f39c12",
                            annotation_text=f"≥90% ({lim_90:.1f})", annotation_position="bottom right")
        fig_hist.add_hline(y=lim_85,   line_dash="dot",    line_color="#3498db",
                            annotation_text=f"≥85% ({lim_85:.1f})", annotation_position="bottom right")

        # Colorir pontos por zona
        cores_pts = []
        for v in sub_hist["Vel. Máx (km/h)"]:
            if v >= lim_95:   cores_pts.append("#2ecc71")
            elif v >= lim_90: cores_pts.append("#f39c12")
            elif v >= lim_85: cores_pts.append("#3498db")
            else:             cores_pts.append("#e74c3c")
        fig_hist.update_traces(marker_color=cores_pts, selector=dict(name="Vmáx Sessão"))

        fig_hist.update_layout(
            height=400,
            yaxis_title="Vel. Máx (km/h)",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
            margin=dict(t=20),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # Gráfico % do Recorde ao longo do tempo
        st.markdown('<p class="section-title">% do Recorde por Sessão</p>', unsafe_allow_html=True)
        fig_pct_hist = go.Figure()
        fig_pct_hist.add_trace(go.Bar(
            x=sub_hist["Data"], y=sub_hist["% Record"],
            marker_color=[
                "#2ecc71" if v >= 95 else "#f39c12" if v >= 90 else "#3498db" if v >= 85 else "#e74c3c"
                for v in sub_hist["% Record"]
            ],
            text=sub_hist["% Record"].astype(str) + "%",
            textposition="outside",
        ))
        fig_pct_hist.add_hline(y=95, line_dash="dash", line_color="#2ecc71", annotation_text="95%")
        fig_pct_hist.add_hline(y=90, line_dash="dash", line_color="#f39c12", annotation_text="90%")
        fig_pct_hist.update_layout(
            yaxis=dict(title="% do Recorde", range=[60, 108]),
            height=320,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            margin=dict(t=10),
        )
        st.plotly_chart(fig_pct_hist, use_container_width=True)

        # Exposição por zonas — Nº sprints ≥85/90/95%
        cols_sprints = ["Nº ≥85% Vmáx", "Nº ≥90% Vmáx", "Nº ≥95% Vmáx"]
        cols_sprints_disp = [c for c in cols_sprints if c in sub_hist.columns]
        if cols_sprints_disp:
            st.markdown('<p class="section-title">Nº de Ações por Zona de Velocidade</p>', unsafe_allow_html=True)
            fig_sprints = px.line(sub_hist, x="Data", y=cols_sprints_disp,
                                   markers=True,
                                   color_discrete_map={
                                       "Nº ≥85% Vmáx": "#3498db",
                                       "Nº ≥90% Vmáx": "#f39c12",
                                       "Nº ≥95% Vmáx": "#e74c3c",
                                   })
            fig_sprints.update_layout(
                height=300,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                legend_title="Zona",
                margin=dict(t=10),
            )
            st.plotly_chart(fig_sprints, use_container_width=True)

        # Tabela de dados brutos
        with st.expander("📋 Ver histórico completo de Vmáx"):
            colunas_hist = ["Data", "Microciclo (Nr)", "Dia MD", "Vel. Máx (km/h)", "% Record"] + cols_sprints_disp
            colunas_hist_disp = [c for c in colunas_hist if c in sub_hist.columns]
            st.dataframe(sub_hist[colunas_hist_disp].sort_values("Data", ascending=False), use_container_width=True)

    # ── Conclusões Vmáx ───────────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-title">🧠 Conclusões — Vmáx Monitor</p>', unsafe_allow_html=True)

    if not df_vmax.empty:
        criticos = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce") > 14]["Jogador"].tolist()
        atencao_v = df_vmax[pd.to_numeric(df_vmax["Dias s/ ≥90% Vmáx"], errors="coerce").between(8, 14)]["Jogador"].tolist()
        baixo_pct = df_vmax[df_vmax["% do Recorde"] < 90]["Jogador"].tolist()

        if criticos:
            st.markdown(f"🔴 **Risco de desadaptação neural** — {', '.join(criticos)}: mais de 14 dias sem atingir ≥90% do recorde. Expor a estímulos de alta velocidade com urgência.")
        if atencao_v:
            st.markdown(f"🟡 **Monitorizar** — {', '.join(atencao_v)}: entre 8-14 dias sem ≥90% Vmáx.")
        if baixo_pct:
            st.markdown(f"📉 **Abaixo de 90% do recorde** na última sessão — {', '.join(baixo_pct)}. Verificar se é recuperação intencional ou sinal de fadiga.")
        if not criticos and not atencao_v:
            st.markdown("🟢 **Toda a equipa em dia** com exposição a alta velocidade (<7 dias).")

        melhor = df_vmax.loc[df_vmax["Vmáx Record (km/h)"].idxmax()]
        st.markdown(f"⚡ **Jogador mais rápido**: {melhor['Jogador']} com recorde de **{melhor['Vmáx Record (km/h)']} km/h**.")



# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: Z-SCORE
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📐 Z-Score":
    st.title("📐 Análise Z-Score")
    st.caption("Comparação normalizada do jogador ao longo dos microciclos e entre jogadores da mesma posição")

    METRICAS_ZSCORE = [
        "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
        "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
        "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
    ]
    metricas_disp = [m for m in METRICAS_ZSCORE if m in df.columns]

    def zscore_serie(serie: pd.Series) -> pd.Series:
        mu, sigma = serie.mean(), serie.std()
        if sigma == 0:
            return pd.Series([0.0] * len(serie), index=serie.index)
        return (serie - mu) / sigma

    def cor_zscore(z):
        if z > 2:    return "#e74c3c"
        if z > 1:    return "#f39c12"
        if z >= -1:  return "#2ecc71"
        if z >= -2:  return "#3498db"
        return "#9b59b6"

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["👤 Jogador ao longo dos Microciclos", "📊 Comparação entre Jogadores da mesma Posição"])

    # ── TAB 1: Jogador ao longo dos microciclos ───────────────────────────────
    with tab1:
        st.markdown('<p class="section-title">Evolução do Z-Score do Jogador por Microciclo</p>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        jog_z  = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="z_jog")
        met_z  = col_b.selectbox("Métrica", metricas_disp, key="z_met1")

        df_jog_z = df[df["Jogador"] == jog_z].copy()
        # Dia MD já filtrado via df_f_dia na sidebar

        if met_z in df_jog_z.columns and df_jog_z[met_z].notna().sum() > 1:
            # Z-Score calculado sobre todos os dados do jogador
            df_jog_z = df_jog_z.dropna(subset=[met_z, "Microciclo (Nr)"]).copy()
            df_jog_z["Z-Score"] = zscore_serie(df_jog_z[met_z])

            # Média por microciclo
            mc_z = df_jog_z.groupby("Microciclo (Nr)").agg(
                Z_medio=("Z-Score", "mean"),
                Valor_medio=(met_z, "mean"),
                n=("Z-Score", "count"),
            ).reset_index()
            mc_z.columns = ["Microciclo (Nr)", "Z-Score Médio", f"{met_z} Médio", "Sessões"]
            mc_z = mc_z.sort_values("Microciclo (Nr)")

            cores_z = [cor_zscore(z) for z in mc_z["Z-Score Médio"]]

            fig_z1 = go.Figure()
            fig_z1.add_trace(go.Bar(
                x=mc_z["Microciclo (Nr)"].astype(str),
                y=mc_z["Z-Score Médio"],
                marker_color=cores_z,
                text=mc_z["Z-Score Médio"].round(2),
                textposition="outside",
                name="Z-Score",
            ))
            fig_z1.add_hline(y=2,  line_dash="dash", line_color="#e74c3c",  annotation_text="+2σ")
            fig_z1.add_hline(y=1,  line_dash="dot",  line_color="#f39c12",  annotation_text="+1σ")
            fig_z1.add_hline(y=0,  line_dash="solid",line_color="white",    line_width=1)
            fig_z1.add_hline(y=-1, line_dash="dot",  line_color="#3498db",  annotation_text="-1σ")
            fig_z1.add_hline(y=-2, line_dash="dash", line_color="#9b59b6",  annotation_text="-2σ")
            fig_z1.update_layout(
                xaxis_title="Microciclo", yaxis_title="Z-Score",
                height=400, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=30),
            )
            st.plotly_chart(fig_z1, use_container_width=True)

            # Interpretação automática
            z_ultimo = mc_z.iloc[-1]["Z-Score Médio"]
            mc_ultimo = int(mc_z.iloc[-1]["Microciclo (Nr)"])
            if z_ultimo > 2:
                st.markdown(f"🔴 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito acima** da média do jogador (>+2σ). Risco de sobrecarga.")
            elif z_ultimo > 1:
                st.markdown(f"🟡 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **acima** da média (+1σ a +2σ). Monitorizar.")
            elif z_ultimo >= -1:
                st.markdown(f"🟢 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **dentro da média** (±1σ). Normal.")
            elif z_ultimo >= -2:
                st.markdown(f"🔵 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **abaixo** da média (-1σ a -2σ). Sub-estimulação.")
            else:
                st.markdown(f"🟣 **MC {mc_ultimo}**: Z-Score de **{z_ultimo:.2f}** — valor **muito abaixo** da média (<-2σ). Possível recuperação/lesão.")

            # Tabela detalhada
            with st.expander("📋 Ver tabela completa de Z-Scores por Microciclo"):
                st.dataframe(mc_z.set_index("Microciclo (Nr)"), use_container_width=True)

            # Múltiplas métricas — radar por microciclo
            st.divider()
            st.markdown('<p class="section-title">Radar de Z-Scores — Múltiplas Métricas (último vs penúltimo MC)</p>', unsafe_allow_html=True)
            mcs_disponiveis = sorted(df_jog_z["Microciclo (Nr)"].unique(), reverse=True)
            if len(mcs_disponiveis) >= 2:
                mc_A = st.selectbox("Microciclo A", mcs_disponiveis, index=0, key="radar_mcA")
                mc_B = st.selectbox("Microciclo B", mcs_disponiveis, index=1, key="radar_mcB")

                radar_mets = [m for m in ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)"] if m in df_jog_z.columns]

                df_radar = df[df["Jogador"] == jog_z].copy()
                if "Dia MD" in df_radar.columns and dia_md_sel:
                    df_radar = df_radar[df_radar["Dia MD"].isin(dia_md_sel)]

                # Z-score calculado sobre toda a série do jogador
                zscores_A, zscores_B = [], []
                for m in radar_mets:
                    if df_radar[m].notna().sum() > 1:
                        z_all = zscore_serie(df_radar[m])
                        sub_A = z_all[df_radar["Microciclo (Nr)"] == mc_A]
                        sub_B = z_all[df_radar["Microciclo (Nr)"] == mc_B]
                        zscores_A.append(round(sub_A.mean(), 2) if not sub_A.empty else 0)
                        zscores_B.append(round(sub_B.mean(), 2) if not sub_B.empty else 0)
                    else:
                        zscores_A.append(0); zscores_B.append(0)

                fig_radar_z = go.Figure()
                fig_radar_z.add_trace(go.Scatterpolar(
                    r=zscores_A + [zscores_A[0]], theta=radar_mets + [radar_mets[0]],
                    fill="toself", name=f"MC {mc_A}", line_color="#e63946", opacity=0.8,
                ))
                fig_radar_z.add_trace(go.Scatterpolar(
                    r=zscores_B + [zscores_B[0]], theta=radar_mets + [radar_mets[0]],
                    fill="toself", name=f"MC {mc_B}", line_color="#457b9d", opacity=0.8,
                ))
                fig_radar_z.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    height=420, plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                )
                st.plotly_chart(fig_radar_z, use_container_width=True)
        else:
            st.warning(f"Dados insuficientes para calcular Z-Score de '{met_z}' para {jog_z}.")

    # ── TAB 2: Comparação entre jogadores da mesma posição ────────────────────
    with tab2:
        st.markdown('<p class="section-title">Z-Score por Posição — Onde se posiciona cada jogador?</p>', unsafe_allow_html=True)
        col_c, col_d = st.columns(2)
        pos_z  = col_c.selectbox("Posição", posicoes if posicoes else ["—"], key="z_pos")
        met_z2 = col_d.selectbox("Métrica", metricas_disp, key="z_met2")
        mc_z2  = col_c.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="z_mc2")

        df_pos_z = df[
            (df["Posição"] == pos_z) &
            (df["Microciclo (Nr)"] == mc_z2)
        ].copy()
        # Dia MD já filtrado via df_f_dia

        if met_z2 in df_pos_z.columns and df_pos_z[met_z2].notna().sum() > 1:
            # Z-Score calculado dentro do grupo da posição
            df_pos_z["Z-Score"] = zscore_serie(df_pos_z[met_z2])
            df_pos_z_mc = df_pos_z.groupby("Jogador").agg(
                Z_medio=("Z-Score", "mean"),
                Valor_medio=(met_z2, "mean"),
            ).reset_index().sort_values("Z_medio", ascending=True)
            df_pos_z_mc.columns = ["Jogador", "Z-Score", f"Média {met_z2}"]

            cores_pos = [cor_zscore(z) for z in df_pos_z_mc["Z-Score"]]

            fig_pos_z = go.Figure(go.Bar(
                y=df_pos_z_mc["Jogador"],
                x=df_pos_z_mc["Z-Score"],
                orientation="h",
                marker_color=cores_pos,
                text=df_pos_z_mc["Z-Score"].round(2),
                textposition="outside",
            ))
            fig_pos_z.add_vline(x=0,  line_dash="solid", line_color="white", line_width=1)
            fig_pos_z.add_vline(x=1,  line_dash="dot",   line_color="#f39c12", annotation_text="+1σ")
            fig_pos_z.add_vline(x=-1, line_dash="dot",   line_color="#3498db", annotation_text="-1σ")
            fig_pos_z.update_layout(
                xaxis_title="Z-Score", height=max(280, len(df_pos_z_mc)*55),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", margin=dict(t=20),
            )
            st.plotly_chart(fig_pos_z, use_container_width=True)

            st.markdown(f"**Referência do grupo ({pos_z}) — MC {int(mc_z2)}:**")
            st.dataframe(df_pos_z_mc.set_index("Jogador"), use_container_width=True)

            # Conclusões por posição
            st.divider()
            st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
            acima = df_pos_z_mc[df_pos_z_mc["Z-Score"] > 1]["Jogador"].tolist()
            abaixo = df_pos_z_mc[df_pos_z_mc["Z-Score"] < -1]["Jogador"].tolist()
            normal = df_pos_z_mc[df_pos_z_mc["Z-Score"].between(-1, 1)]["Jogador"].tolist()
            media_val = df_pos_z[met_z2].mean()

            if acima:
                st.markdown(f"🟡 **Acima da média do grupo** (>+1σ): {', '.join(acima)}")
            if abaixo:
                st.markdown(f"🔵 **Abaixo da média do grupo** (<-1σ): {', '.join(abaixo)}")
            if normal:
                st.markdown(f"🟢 **Dentro da média** (±1σ): {', '.join(normal)}")
            st.markdown(f"📊 **Média do grupo** para {met_z2} no MC {int(mc_z2)}: **{media_val:.1f}**")

            # Heatmap — todos os microciclos × jogadores da posição
            st.divider()
            st.markdown('<p class="section-title">🗺️ Heatmap Z-Score — Todos os Microciclos</p>', unsafe_allow_html=True)
            df_heat = df[df["Posição"] == pos_z].copy()
            # Dia MD já filtrado via df_f_dia

            if met_z2 in df_heat.columns:
                df_heat = df_heat.dropna(subset=[met_z2, "Microciclo (Nr)", "Jogador"])
                pivot = df_heat.groupby(["Jogador", "Microciclo (Nr)"])[met_z2].mean().unstack()
                # Z-score por coluna (microciclo) dentro da posição
                pivot_z = pivot.apply(
                    lambda col: (col - col.mean()) / col.std() if col.std() > 0 and col.notna().sum() > 1 else col * 0,
                    axis=0
                )

                fig_heat = go.Figure(go.Heatmap(
                    z=pivot_z.values,
                    x=[f"MC {int(c)}" for c in pivot_z.columns],
                    y=pivot_z.index.tolist(),
                    colorscale="RdYlGn",
                    zmid=0,
                    text=pivot_z.round(1).values,
                    texttemplate="%{text}",
                    colorbar=dict(title="Z-Score"),
                ))
                fig_heat.update_layout(
                    height=max(280, len(pivot_z)*50),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white", margin=dict(t=10),
                    xaxis_title="Microciclo", yaxis_title="Jogador",
                )
                st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.warning(f"Dados insuficientes para '{met_z2}' na posição '{pos_z}' no MC {int(mc_z2)}.")


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: CARGA JOGO VS TREINO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚽ Carga Jogo vs Treino":
    st.title("⚽ Carga de Jogo vs Carga de Treino")
    st.caption("Percentagem da carga de jogo em relação ao total do microciclo")

    METRICAS_JOGO = [
        "Distância Total (m)", "HSR (m)", "Sprint (m)",
        "Acc (n)", "Dcc (n)", "Carga Interna", "PSE Sessão",
    ]
    mets_jogo_disp = [m for m in METRICAS_JOGO if m in df.columns]

    # Separar treinos e jogos
    if "Tipo" not in df.columns:
        st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com valores 'Treino' e 'Jogo'.")
        st.stop()

    df_jogos   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
    df_treinos = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

    if df_jogos.empty:
        st.warning("Nenhum registo com Tipo = 'Jogo' encontrado no Excel.")
        st.stop()

    # Filtros de contexto
    col1, col2, col3 = st.columns(3)
    mc_jogo = col1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="jogo_mc")
    met_jogo = col2.selectbox("Métrica", mets_jogo_disp, key="jogo_met")
    modo_jogo = col3.radio("Modo de comparação", ["Por Jogador", "Equipa (média)"], key="jogo_modo")

    st.divider()

    # ── Dados do microciclo selecionado ───────────────────────────────────────
    jogos_mc   = df_jogos[df_jogos["Microciclo (Nr)"] == mc_jogo]
    treinos_mc = df_treinos[df_treinos["Microciclo (Nr)"] == mc_jogo]

    if jogos_mc.empty:
        st.warning(f"Sem registos de jogo para o Microciclo {int(mc_jogo)}.")
        st.stop()

    if treinos_mc.empty:
        st.warning(f"Sem registos de treino para o Microciclo {int(mc_jogo)}.")
        st.stop()

    # ── MODO: POR JOGADOR ─────────────────────────────────────────────────────
    if modo_jogo == "Por Jogador":
        jog_jogo = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="jogo_jog")

        jogo_jog   = jogos_mc[jogos_mc["Jogador"] == jog_jogo]
        treino_jog = treinos_mc[treinos_mc["Jogador"] == jog_jogo]

        if jogo_jog.empty or treino_jog.empty:
            st.warning(f"Dados insuficientes para {jog_jogo} no MC {int(mc_jogo)}.")
            st.stop()

        carga_jogo_val   = jogo_jog[met_jogo].sum()
        carga_treino_val = treino_jog[met_jogo].sum()
        carga_total      = carga_jogo_val + carga_treino_val
        pct_jogo         = (carga_jogo_val / carga_total * 100) if carga_total > 0 else 0
        pct_treino       = 100 - pct_jogo

        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(f"Carga Jogo ({met_jogo})",   f"{carga_jogo_val:,.1f}")
        k2.metric(f"Carga Treino ({met_jogo})",  f"{carga_treino_val:,.1f}")
        k3.metric("Total Semanal",               f"{carga_total:,.1f}")
        k4.metric("% Jogo / Total",              f"{pct_jogo:.1f}%")

        st.divider()

        # Gráfico de rosca jogo vs treino
        col_pie, col_bar = st.columns(2)

        with col_pie:
            st.markdown('<p class="section-title">Proporção Jogo vs Treino</p>', unsafe_allow_html=True)
            fig_pie = go.Figure(go.Pie(
                labels=["⚽ Jogo", "🏃 Treino"],
                values=[carga_jogo_val, carga_treino_val],
                hole=0.55,
                marker_colors=["#e63946", "#457b9d"],
                textinfo="label+percent",
            ))
            fig_pie.update_layout(
                height=320, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                margin=dict(t=20),
                annotations=[dict(text=f"{pct_jogo:.0f}%<br>Jogo", x=0.5, y=0.5,
                                   font_size=18, showarrow=False, font_color="white")],
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_bar:
            st.markdown('<p class="section-title">Distribuição por Dia MD</p>', unsafe_allow_html=True)
            # Carga por dia MD
            treino_dia = treino_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in treino_jog.columns else pd.DataFrame()
            jogo_dia   = jogo_jog.groupby("Dia MD")[met_jogo].sum().reset_index() if "Dia MD" in jogo_jog.columns else pd.DataFrame()

            ordem_dias = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD","MD+1"]

            if not treino_dia.empty or not jogo_dia.empty:
                all_dias = pd.DataFrame({"Dia MD": ordem_dias})
                treino_dia_full = all_dias.merge(treino_dia, on="Dia MD", how="left").fillna(0)
                jogo_dia_full   = all_dias.merge(jogo_dia,   on="Dia MD", how="left").fillna(0)

                fig_dias_bar = go.Figure()
                fig_dias_bar.add_trace(go.Bar(
                    x=treino_dia_full["Dia MD"], y=treino_dia_full[met_jogo],
                    name="Treino", marker_color="#457b9d",
                ))
                fig_dias_bar.add_trace(go.Bar(
                    x=jogo_dia_full["Dia MD"], y=jogo_dia_full[met_jogo],
                    name="Jogo", marker_color="#e63946",
                ))
                fig_dias_bar.update_layout(
                    barmode="stack", height=320,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white", yaxis_title=met_jogo, margin=dict(t=10),
                )
                st.plotly_chart(fig_dias_bar, use_container_width=True)

        # Contexto histórico — % jogo ao longo dos microciclos
        st.divider()
        st.markdown('<p class="section-title">📈 Evolução da % de Carga de Jogo ao longo dos Microciclos</p>', unsafe_allow_html=True)

        rows_hist = []
        for mc in sorted(df["Microciclo (Nr)"].dropna().unique()):
            j_mc = df_jogos[(df_jogos["Microciclo (Nr)"] == mc) & (df_jogos["Jogador"] == jog_jogo)]
            t_mc = df_treinos[(df_treinos["Microciclo (Nr)"] == mc) & (df_treinos["Jogador"] == jog_jogo)]
            if j_mc.empty or t_mc.empty:
                continue
            cj = j_mc[met_jogo].sum()
            ct = t_mc[met_jogo].sum()
            total = cj + ct
            rows_hist.append({
                "Microciclo": int(mc),
                "Carga Jogo": round(cj, 1),
                "Carga Treino": round(ct, 1),
                "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
            })

        if rows_hist:
            df_hist = pd.DataFrame(rows_hist)
            fig_hist_jogo = go.Figure()
            fig_hist_jogo.add_trace(go.Scatter(
                x=df_hist["Microciclo"], y=df_hist["% Jogo"],
                mode="lines+markers+text",
                text=[f"{v:.0f}%" for v in df_hist["% Jogo"]],
                textposition="top center",
                line_color="#e63946", line_width=2, marker_size=8, name="% Jogo",
            ))
            fig_hist_jogo.add_hline(y=30, line_dash="dash", line_color="#f39c12",
                                     annotation_text="30% referência")
            fig_hist_jogo.update_layout(
                yaxis=dict(title="% Carga de Jogo", range=[0, 100]),
                xaxis_title="Microciclo",
                height=320, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10),
            )
            st.plotly_chart(fig_hist_jogo, use_container_width=True)

    # ── MODO: EQUIPA ─────────────────────────────────────────────────────────
    else:
        st.markdown('<p class="section-title">% Carga de Jogo vs Treino por Jogador — Equipa</p>', unsafe_allow_html=True)

        rows_eq = []
        for jog in sorted(df["Jogador"].dropna().unique()):
            j = jogos_mc[jogos_mc["Jogador"] == jog]
            t = treinos_mc[treinos_mc["Jogador"] == jog]
            if j.empty or t.empty or met_jogo not in j.columns:
                continue
            cj = j[met_jogo].sum()
            ct = t[met_jogo].sum()
            total = cj + ct
            pos = j["Posição"].iloc[0] if "Posição" in j.columns else "—"
            rows_eq.append({
                "Jogador": jog,
                "Posição": pos,
                "Carga Jogo": round(cj, 1),
                "Carga Treino": round(ct, 1),
                "Total Semanal": round(total, 1),
                "% Jogo": round(cj / total * 100, 1) if total > 0 else 0,
            })

        if not rows_eq:
            st.warning("Sem dados suficientes para a equipa neste microciclo.")
            st.stop()

        df_eq = pd.DataFrame(rows_eq).sort_values("% Jogo", ascending=False)

        # KPIs equipa
        k1, k2, k3 = st.columns(3)
        k1.metric("% Jogo Média da Equipa", f"{df_eq['% Jogo'].mean():.1f}%")
        k2.metric("Carga Jogo Média",        f"{df_eq['Carga Jogo'].mean():,.1f}")
        k3.metric("Carga Treino Média",      f"{df_eq['Carga Treino'].mean():,.1f}")

        # Gráfico barras empilhadas
        cores_eq = ["#e74c3c" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]]
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Bar(
            x=df_eq["Jogador"], y=df_eq["Carga Jogo"],
            name="⚽ Jogo", marker_color="#e63946",
        ))
        fig_eq.add_trace(go.Bar(
            x=df_eq["Jogador"], y=df_eq["Carga Treino"],
            name="🏃 Treino", marker_color="#457b9d",
        ))
        fig_eq.update_layout(
            barmode="stack", height=380,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", yaxis_title=met_jogo,
            legend=dict(orientation="h", y=1.05), margin=dict(t=30),
        )
        st.plotly_chart(fig_eq, use_container_width=True)

        # % Jogo por jogador
        fig_pct_eq = go.Figure(go.Bar(
            x=df_eq["Jogador"], y=df_eq["% Jogo"],
            marker_color=["#e63946" if v > 40 else "#f39c12" if v > 30 else "#2ecc71" for v in df_eq["% Jogo"]],
            text=[f"{v:.1f}%" for v in df_eq["% Jogo"]],
            textposition="outside",
        ))
        fig_pct_eq.add_hline(y=30, line_dash="dash", line_color="#f39c12", annotation_text="30% referência")
        fig_pct_eq.update_layout(
            yaxis=dict(title="% Jogo / Total", range=[0, max(df_eq["% Jogo"]) + 15]),
            height=340, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            showlegend=False, margin=dict(t=20),
        )
        st.plotly_chart(fig_pct_eq, use_container_width=True)

        # Tabela completa
        st.dataframe(df_eq.set_index("Jogador"), use_container_width=True)

        # Conclusões equipa
        st.divider()
        st.markdown('<p class="section-title">🧠 Conclusões</p>', unsafe_allow_html=True)
        alto_jogo  = df_eq[df_eq["% Jogo"] > 40]["Jogador"].tolist()
        medio_jogo = df_eq[df_eq["% Jogo"].between(30, 40)]["Jogador"].tolist()
        baixo_jogo = df_eq[df_eq["% Jogo"] < 30]["Jogador"].tolist()

        if alto_jogo:
            st.markdown(f"🔴 **Carga de jogo muito elevada** (>40%): {', '.join(alto_jogo)} — estes jogadores fizeram grande parte do esforço semanal no jogo. Atenção à recuperação.")
        if medio_jogo:
            st.markdown(f"🟡 **Proporção equilibrada** (30-40%): {', '.join(medio_jogo)} — valores dentro do esperado.")
        if baixo_jogo:
            st.markdown(f"🔵 **Pouca exposição em jogo** (<30%): {', '.join(baixo_jogo)} — baixo volume de jogo relativamente ao treino (lesão, banco, rotação?).")
        st.markdown(f"📊 **Média da equipa**: {df_eq['% Jogo'].mean():.1f}% da carga semanal correspondeu ao jogo.")




# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: PERFIL DE REFERÊNCIA INDIVIDUAL (Z-Score pessoal)
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📏 Perfil de Referência":
    st.title("📏 Perfil de Referência Individual")
    st.caption("Semáforo baseado no historial pessoal de cada jogador — não na média da equipa")

    METS_PERFIL = [
        "Distância Total (m)", "HSR (m)", "Sprint (m)", "Vel. Máx (km/h)",
        "Acc (n)", "Dcc (n)", "PSE Sessão", "Carga Interna",
        "Hooper Index", "Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)",
    ]
    mets_disp = [m for m in METS_PERFIL if m in df.columns]

    tab_p1, tab_p2 = st.tabs(["👤 Análise Individual", "🏟️ Semáforo da Equipa"])

    # ── TAB 1: Individual ────────────────────────────────────────────────────
    with tab_p1:
        col_a, col_b = st.columns(2)
        jog_p = col_a.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="perf_jog")
        n_semanas = col_b.slider("Semanas de histórico como referência", 4, 20, 8, key="perf_sem")

        df_jog_p = df[df["Jogador"] == jog_p].dropna(subset=["Data"]).sort_values("Data").copy()
        if df_jog_p.empty:
            st.warning("Sem dados para este jogador.")
            st.stop()

        # Referência = primeiras n_semanas × 7 dias de dados
        data_corte = df_jog_p["Data"].min() + pd.Timedelta(weeks=n_semanas)
        df_ref  = df_jog_p[df_jog_p["Data"] <= data_corte]
        df_recente = df_jog_p[df_jog_p["Data"] > data_corte]

        if df_ref.empty or df_recente.empty:
            st.warning("Histórico insuficiente. Tenta reduzir o número de semanas de referência.")
        else:
            st.info(f"📐 Referência baseada em **{len(df_ref)} sessões** ({df_ref['Data'].min().strftime('%d/%m/%y')} – {df_ref['Data'].max().strftime('%d/%m/%y')})")

            # Calcular perfil de referência
            perfil_rows = []
            for met in mets_disp:
                if df_ref[met].notna().sum() < 3:
                    continue
                mu  = df_ref[met].mean()
                sig = df_ref[met].std()
                ult = df_recente[met].dropna()
                if ult.empty: continue
                ult_val = ult.iloc[-1]
                z = (ult_val - mu) / sig if sig > 0 else 0
                if z > 2:    estado = "🔴 Muito Acima"; cor = "#e74c3c"
                elif z > 1:  estado = "🟡 Acima";       cor = "#f39c12"
                elif z >= -1: estado = "🟢 Normal";      cor = "#2ecc71"
                elif z >= -2: estado = "🔵 Abaixo";      cor = "#3498db"
                else:         estado = "🟣 Muito Abaixo"; cor = "#9b59b6"
                perfil_rows.append({
                    "Métrica": met,
                    "Ref. Média": round(mu, 1),
                    "Ref. ±DP": round(sig, 1),
                    "Último Valor": round(ult_val, 1),
                    "Z-Score": round(z, 2),
                    "Estado": estado,
                    "_cor": cor,
                })

            if perfil_rows:
                df_perf = pd.DataFrame(perfil_rows)

                # Cards de semáforo
                st.markdown('<p class="section-title">Semáforo — Última Sessão vs Perfil Pessoal</p>', unsafe_allow_html=True)
                n_cols = 4
                cols_p = st.columns(n_cols)
                for i, row in df_perf.iterrows():
                    cols_p[i % n_cols].markdown(
                        f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                        f'padding:10px;text-align:center;margin:4px">'
                        f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{row["Métrica"]}</div>'
                        f'<div style="font-size:1.4rem;font-weight:900;color:{row["_cor"]}">{row["Último Valor"]}</div>'
                        f'<div style="font-size:0.7rem;color:#aaa">Ref: {row["Ref. Média"]} ± {row["Ref. ±DP"]}</div>'
                        f'<div style="font-size:0.85rem;color:{row["_cor"]}">{row["Estado"]} (z={row["Z-Score"]})</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # Gráfico de barras Z-Score
                st.markdown('<p class="section-title">Z-Score vs Perfil de Referência</p>', unsafe_allow_html=True)
                fig_perf = go.Figure(go.Bar(
                    y=df_perf["Métrica"],
                    x=df_perf["Z-Score"],
                    orientation="h",
                    marker_color=df_perf["_cor"].tolist(),
                    text=df_perf["Z-Score"].round(2),
                    textposition="outside",
                ))
                fig_perf.add_vline(x=0,  line_color="white", line_width=1)
                fig_perf.add_vline(x=1,  line_dash="dot", line_color="#f39c12", annotation_text="+1σ")
                fig_perf.add_vline(x=-1, line_dash="dot", line_color="#3498db", annotation_text="-1σ")
                fig_perf.add_vline(x=2,  line_dash="dash", line_color="#e74c3c", annotation_text="+2σ")
                fig_perf.add_vline(x=-2, line_dash="dash", line_color="#9b59b6", annotation_text="-2σ")
                fig_perf.update_layout(
                    height=max(300, len(df_perf)*50),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white", xaxis_title="Z-Score", margin=dict(t=10),
                )
                st.plotly_chart(fig_perf, use_container_width=True)

                # Evolução histórica de uma métrica
                st.divider()
                st.markdown('<p class="section-title">Evolução Histórica com Bandas de Referência</p>', unsafe_allow_html=True)
                met_ev = st.selectbox("Métrica", df_perf["Métrica"].tolist(), key="perf_ev")
                mu_ev  = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. Média"].iloc[0])
                sig_ev = float(df_perf[df_perf["Métrica"] == met_ev]["Ref. ±DP"].iloc[0])

                fig_ev = go.Figure()
                fig_ev.add_hrect(y0=mu_ev-sig_ev, y1=mu_ev+sig_ev,   fillcolor="#2ecc71", opacity=0.08, line_width=0)
                fig_ev.add_hrect(y0=mu_ev+sig_ev, y1=mu_ev+2*sig_ev, fillcolor="#f39c12", opacity=0.08, line_width=0)
                fig_ev.add_hrect(y0=mu_ev-2*sig_ev, y1=mu_ev-sig_ev, fillcolor="#3498db", opacity=0.08, line_width=0)
                fig_ev.add_trace(go.Scatter(
                    x=df_jog_p["Data"], y=df_jog_p[met_ev],
                    mode="lines+markers", line_color="#e63946", line_width=2, marker_size=6,
                    name=met_ev,
                ))
                fig_ev.add_hline(y=mu_ev, line_dash="dash", line_color="white", line_width=1, annotation_text="Média ref.")
                fig_ev.add_hline(y=mu_ev+sig_ev,   line_dash="dot", line_color="#f39c12")
                fig_ev.add_hline(y=mu_ev-sig_ev,   line_dash="dot", line_color="#3498db")
                try:
                    fig_ev.add_vline(x=data_corte.timestamp()*1000, line_dash="dash", line_color="#888",
                                      annotation_text="Fim período ref.")
                except Exception:
                    pass
                fig_ev.update_layout(
                    height=360, yaxis_title=met_ev,
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white", margin=dict(t=20), showlegend=False,
                )
                st.plotly_chart(fig_ev, use_container_width=True)

                # Exportar relatório
                st.divider()
                linhas_tab = "".join([
                    f'<tr><td>{r["Métrica"]}</td><td>{r["Ref. Média"]} ± {r["Ref. ±DP"]}</td>'
                    f'<td>{r["Último Valor"]}</td><td>{r["Z-Score"]}</td><td>{r["Estado"]}</td></tr>'
                    for _, r in df_perf.iterrows()
                ])
                html_perf = gerar_pdf_html(f"""
<h1>Perfil de Referência — {jog_p}</h1>
<p>Referência: {df_ref["Data"].min().strftime("%d/%m/%Y")} a {df_ref["Data"].max().strftime("%d/%m/%Y")} ({len(df_ref)} sessões)</p>
<table><tr><th>Métrica</th><th>Ref. Média ± DP</th><th>Último Valor</th><th>Z-Score</th><th>Estado</th></tr>
{linhas_tab}</table>
""", f"Perfil_{jog_p}.html")
                botao_download_html(html_perf, f"Perfil_{jog_p.replace(' ','_')}.html", f"📥 Exportar Perfil de {jog_p}")

    # ── TAB 2: Semáforo da equipa ─────────────────────────────────────────────
    with tab_p2:
        st.markdown('<p class="section-title">Semáforo de Z-Score Pessoal — Última Sessão vs Perfil Próprio</p>', unsafe_allow_html=True)
        met_eq_p = st.selectbox("Métrica", mets_disp, key="perf_eq_met")
        semanas_ref = st.slider("Semanas de referência", 4, 20, 8, key="perf_eq_sem")

        equipa_perfil = []
        for jog in sorted(df["Jogador"].dropna().unique()):
            df_j = df[df["Jogador"] == jog].dropna(subset=["Data", met_eq_p]).sort_values("Data")
            if len(df_j) < 5: continue
            corte = df_j["Data"].min() + pd.Timedelta(weeks=semanas_ref)
            ref = df_j[df_j["Data"] <= corte][met_eq_p]
            rec = df_j[df_j["Data"] > corte][met_eq_p]
            if ref.empty or rec.empty: continue
            mu, sig = ref.mean(), ref.std()
            if sig == 0: continue
            ult = rec.iloc[-1]
            z = (ult - mu) / sig
            if z > 2:     estado, cor = "🔴 Muito Acima", "#e74c3c"
            elif z > 1:   estado, cor = "🟡 Acima",       "#f39c12"
            elif z >= -1: estado, cor = "🟢 Normal",      "#2ecc71"
            elif z >= -2: estado, cor = "🔵 Abaixo",      "#3498db"
            else:         estado, cor = "🟣 Muito Abaixo","#9b59b6"
            pos = df_j["Posição"].iloc[-1] if "Posição" in df_j.columns else "—"
            equipa_perfil.append({"Jogador": jog, "Posição": pos, "Ref. Média": round(mu,1),
                                   "Último": round(ult,1), "Z-Score": round(z,2),
                                   "Estado": estado, "_cor": cor})

        if equipa_perfil:
            df_ep = pd.DataFrame(equipa_perfil).sort_values("Z-Score", ascending=False)
            cols_sem = st.columns(min(len(df_ep), 5))
            for i, (_, row) in enumerate(df_ep.iterrows()):
                cols_sem[i % 5].markdown(
                    f'<div style="background:{row["_cor"]}22;border:2px solid {row["_cor"]};border-radius:10px;'
                    f'padding:10px;text-align:center;margin:4px">'
                    f'<b style="font-size:0.9rem">{row["Jogador"]}</b><br>'
                    f'<span style="font-size:0.75rem;color:#aaa">{row["Posição"]}</span><br>'
                    f'<b style="font-size:1.3rem;color:{row["_cor"]}">{row["Z-Score"]:+.2f}</b><br>'
                    f'<span style="font-size:0.7rem">{row["Estado"]}</span></div>',
                    unsafe_allow_html=True
                )

            st.divider()
            fig_eq_perf = go.Figure(go.Bar(
                x=df_ep["Jogador"], y=df_ep["Z-Score"],
                marker_color=df_ep["_cor"].tolist(),
                text=df_ep["Z-Score"].round(2), textposition="outside",
            ))
            fig_eq_perf.add_hline(y=1,  line_dash="dot", line_color="#f39c12")
            fig_eq_perf.add_hline(y=-1, line_dash="dot", line_color="#3498db")
            fig_eq_perf.add_hline(y=0,  line_color="white", line_width=1)
            fig_eq_perf.update_layout(
                yaxis_title=f"Z-Score ({met_eq_p})", height=380,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", margin=dict(t=20), showlegend=False,
            )
            st.plotly_chart(fig_eq_perf, use_container_width=True)
        else:
            st.warning("Dados insuficientes para calcular perfis individuais.")


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: LESÕES & DISPONIBILIDADE
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🩺 Lesões & Disponibilidade":
    st.title("🩺 Lesões & Disponibilidade")
    st.caption("Registo de lesões, correlação com carga e disponibilidade do plantel")

    # Tentar ler folha de Lesões
    try:
        df_les = pd.read_excel(excel_path, sheet_name="Lesões", engine="openpyxl")
        df_les.columns = [str(c).strip() for c in df_les.columns]
        tem_folha_lesoes = True
    except Exception:
        tem_folha_lesoes = False
        df_les = pd.DataFrame()

    if not tem_folha_lesoes:
        st.warning("""
### ⚠️ Folha 'Lesões' não encontrada no Excel

Para usar esta funcionalidade, adiciona uma folha chamada **Lesões** ao teu ficheiro Excel com estas colunas:

| Jogador | Data Lesão | Data Retorno | Tipo de Lesão | Zona Corporal | Diagnóstico | Dias de Paragem | Estado |
|---|---|---|---|---|---|---|---|
| Paulino | 12/01/2025 | 25/01/2025 | Muscular | Isquiotibial | Elongação grau I | 13 | Recuperado |
| ... | | | | | | | Ativo |

O campo **Estado** deve ser: `Ativo` (ainda lesionado) ou `Recuperado`.

Depois de criar a folha, clica em **🔄 Atualizar Dados**.
        """)

        # Mesmo sem folha de lesões, mostrar análise de ausências (sessões em falta)
        st.divider()
        st.markdown('<p class="section-title">📊 Análise de Participação nos Treinos</p>', unsafe_allow_html=True)
        st.caption("Jogadores com menos sessões que a média podem indicar períodos de indisponibilidade")

        if "Microciclo (Nr)" in df.columns:
            mc_disp = sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True)
            mc_les = st.selectbox("Microciclo a analisar", mc_disp, key="les_mc")
            df_mc_les = df[df["Microciclo (Nr)"] == mc_les]
            todos_jogs = sorted(df["Jogador"].dropna().unique())

            participacao = []
            max_sess = df_mc_les.groupby("Jogador").size().max() if not df_mc_les.empty else 0
            for jog in todos_jogs:
                sess = len(df_mc_les[df_mc_les["Jogador"] == jog])
                pos  = df[df["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df.columns and not df[df["Jogador"] == jog].empty else "—"
                pct  = sess / max_sess * 100 if max_sess > 0 else 0
                participacao.append({"Jogador": jog, "Posição": pos, "Sessões": sess,
                                      "% Participação": round(pct, 0),
                                      "Estado": "⚠️ Ausente/Indisponível" if pct < 50 else "✅ Presente"})

            df_part = pd.DataFrame(participacao).sort_values("% Participação")
            fig_part = go.Figure(go.Bar(
                y=df_part["Jogador"], x=df_part["% Participação"],
                orientation="h",
                marker_color=["#e74c3c" if v < 50 else "#f39c12" if v < 80 else "#2ecc71"
                               for v in df_part["% Participação"]],
                text=[f"{int(v)}%" for v in df_part["% Participação"]],
                textposition="outside",
            ))
            fig_part.add_vline(x=80, line_dash="dash", line_color="#f39c12", annotation_text="80%")
            fig_part.add_vline(x=50, line_dash="dash", line_color="#e74c3c", annotation_text="50%")
            fig_part.update_layout(
                xaxis=dict(range=[0, 115], title="% Participação"),
                height=max(300, len(df_part)*40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", margin=dict(t=10),
            )
            st.plotly_chart(fig_part, use_container_width=True)
            ausentes = df_part[df_part["% Participação"] < 50]["Jogador"].tolist()
            if ausentes:
                st.warning(f"⚠️ **Possível indisponibilidade** no MC {int(mc_les)}: {', '.join(ausentes)} (menos de 50% das sessões)")
        st.stop()

    # ── Com folha de Lesões ────────────────────────────────────────────────────
    # Normalizar colunas esperadas
    col_jog    = next((c for c in df_les.columns if "jogador" in c.lower()), None)
    col_data_l = next((c for c in df_les.columns if "data" in c.lower() and "lesão" in c.lower()), None) or                  next((c for c in df_les.columns if "data" in c.lower() and "inicio" in c.lower()), None)
    col_retorno = next((c for c in df_les.columns if "retorno" in c.lower() or "regresso" in c.lower()), None)
    col_dias    = next((c for c in df_les.columns if "dias" in c.lower()), None)
    col_tipo    = next((c for c in df_les.columns if "tipo" in c.lower()), None)
    col_zona    = next((c for c in df_les.columns if "zona" in c.lower() or "local" in c.lower()), None)
    col_estado  = next((c for c in df_les.columns if "estado" in c.lower() or "situação" in c.lower()), None)

    if col_jog is None:
        st.error("Coluna 'Jogador' não encontrada na folha Lesões.")
        st.stop()

    if col_data_l:
        df_les[col_data_l] = pd.to_datetime(df_les[col_data_l], errors="coerce")
    if col_retorno:
        df_les[col_retorno] = pd.to_datetime(df_les[col_retorno], errors="coerce")

    tab_l1, tab_l2, tab_l3 = st.tabs(["📋 Registo de Lesões", "📈 Correlação com Carga", "📊 Epidemiologia"])

    with tab_l1:
        # Lesões ativas
        st.markdown('<p class="section-title">🩹 Lesões Ativas</p>', unsafe_allow_html=True)
        if col_estado:
            ativas = df_les[df_les[col_estado].astype(str).str.lower().isin(["ativo","activo","sim","yes","1","true","ativa","activa"])]
        else:
            ativas = df_les[df_les[col_retorno].isna()] if col_retorno else df_les

        if not ativas.empty:
            for _, row in ativas.iterrows():
                jog = row[col_jog]
                tipo = row[col_tipo] if col_tipo else "—"
                zona = row[col_zona] if col_zona else "—"
                dias = row[col_dias] if col_dias else "—"
                data_l = row[col_data_l].strftime("%d/%m/%Y") if col_data_l and pd.notna(row[col_data_l]) else "—"
                st.markdown(
                    f'<div style="background:#7b1d1d33;border-left:4px solid #e74c3c;border-radius:8px;padding:12px;margin:6px 0">'
                    f'🩹 <b>{jog}</b> — {tipo} ({zona}) · desde {data_l} · {dias} dias de paragem'
                    f'</div>', unsafe_allow_html=True
                )
        else:
            st.success("✅ Sem lesões ativas no momento.")

        st.divider()
        st.markdown('<p class="section-title">📋 Histórico Completo</p>', unsafe_allow_html=True)
        st.dataframe(df_les, use_container_width=True)

        # Exportar
        linhas_les = "".join([
            f'<tr>{"".join(f"<td>{row[c]}</td>" for c in df_les.columns)}</tr>'
            for _, row in df_les.iterrows()
        ])
        headers_les = "".join([f"<th>{c}</th>" for c in df_les.columns])
        html_les = gerar_pdf_html(f"""
<h1>Relatório de Lesões</h1>
<table><tr>{headers_les}</tr>{linhas_les}</table>
""", "Relatorio_Lesoes.html")
        botao_download_html(html_les, "Relatorio_Lesoes.html", "📥 Exportar Registo de Lesões")

    with tab_l2:
        st.markdown('<p class="section-title">⚡ Carga nas 4 Semanas Antes da Lesão</p>', unsafe_allow_html=True)
        if col_data_l is None:
            st.warning("Coluna de data de lesão não encontrada.")
        else:
            lesoes_com_data = df_les.dropna(subset=[col_data_l])
            if lesoes_com_data.empty:
                st.info("Sem lesões com data registada.")
            else:
                jog_sel_les = st.selectbox("Jogador", lesoes_com_data[col_jog].unique(), key="les_jog")
                lesoes_jog = lesoes_com_data[lesoes_com_data[col_jog] == jog_sel_les]
                data_les_sel = st.selectbox("Lesão (data)", lesoes_jog[col_data_l].dt.strftime("%d/%m/%Y").tolist(), key="les_data")
                data_les_dt = pd.to_datetime(data_les_sel, format="%d/%m/%Y")

                df_antes = df[
                    (df["Jogador"] == jog_sel_les) &
                    (df["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                    (df["Data"] < data_les_dt)
                ].sort_values("Data")

                if df_antes.empty:
                    st.info("Sem dados de carga nas 4 semanas anteriores à lesão.")
                else:
                    fig_les_carga = go.Figure()
                    if "Carga Interna" in df_antes.columns:
                        fig_les_carga.add_trace(go.Bar(
                            x=df_antes["Data"], y=df_antes["Carga Interna"],
                            name="Carga Interna", marker_color="#e63946",
                        ))
                    if "ACWR" not in df_antes.columns:
                        df_jog_acwr = calcular_acwr(df[df["Jogador"] == jog_sel_les], jog_sel_les)
                        df_jog_acwr = df_jog_acwr[
                            (df_jog_acwr["Data"] >= data_les_dt - pd.Timedelta(weeks=4)) &
                            (df_jog_acwr["Data"] < data_les_dt)
                        ]
                        if "ACWR" in df_jog_acwr.columns:
                            fig_les_carga.add_trace(go.Scatter(
                                x=df_jog_acwr["Data"], y=df_jog_acwr["ACWR"] * 100,
                                mode="lines+markers", name="ACWR ×100", line_color="#f39c12",
                                yaxis="y2",
                            ))
                    fig_les_carga.add_vline(x=data_les_dt, line_dash="dash", line_color="#e74c3c",
                                             annotation_text="Lesão", annotation_position="top right")
                    fig_les_carga.update_layout(
                        height=360,
                        yaxis=dict(title="Carga Interna"),
                        yaxis2=dict(title="ACWR ×100", overlaying="y", side="right"),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font_color="white", margin=dict(t=30),
                    )
                    st.plotly_chart(fig_les_carga, use_container_width=True)

    with tab_l3:
        st.markdown('<p class="section-title">📊 Distribuição de Lesões por Tipo e Zona</p>', unsafe_allow_html=True)

        c1_e, c2_e = st.columns(2)
        if col_tipo and not df_les[col_tipo].isna().all():
            with c1_e:
                tipo_count = df_les[col_tipo].value_counts().reset_index()
                tipo_count.columns = ["Tipo", "Nº"]
                fig_tipo = px.pie(tipo_count, names="Tipo", values="Nº", hole=0.4,
                                   color_discrete_sequence=px.colors.qualitative.Bold)
                fig_tipo.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                        paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=10))
                st.plotly_chart(fig_tipo, use_container_width=True)

        if col_zona and not df_les[col_zona].isna().all():
            with c2_e:
                zona_count = df_les[col_zona].value_counts().reset_index()
                zona_count.columns = ["Zona", "Nº"]
                fig_zona = px.bar(zona_count, x="Nº", y="Zona", orientation="h",
                                   color="Nº", color_continuous_scale="Reds")
                fig_zona.update_layout(height=300, plot_bgcolor="rgba(0,0,0,0)",
                                        paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                                        coloraxis_showscale=False, margin=dict(t=10))
                st.plotly_chart(fig_zona, use_container_width=True)

        if col_dias and not df_les[col_dias].isna().all():
            st.markdown('<p class="section-title">Dias de Paragem por Jogador</p>', unsafe_allow_html=True)
            dias_jog = df_les.groupby(col_jog)[col_dias].sum().sort_values(ascending=False).reset_index()
            dias_jog.columns = ["Jogador", "Total Dias"]
            fig_dias_les = px.bar(dias_jog, x="Jogador", y="Total Dias",
                                   color="Total Dias", color_continuous_scale="Reds",
                                   text="Total Dias")
            fig_dias_les.update_layout(height=320, plot_bgcolor="rgba(0,0,0,0)",
                                        paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                                        coloraxis_showscale=False, margin=dict(t=10))
            st.plotly_chart(fig_dias_les, use_container_width=True)




# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: TREINO VS JOGO — % MÉTRICAS GPS
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📊 Treino vs Jogo (% Métricas)":
    st.title("📊 Treino vs Jogo — % das Métricas GPS")
    st.caption("Quanto representam as sessões de treino do microciclo em relação à média dos jogos?")

    METS_GPS = [
        "Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)",
        "Carga Interna", "PSE Sessão",
    ]
    mets_gps_disp = [m for m in METS_GPS if m in df.columns]

    if "Tipo" not in df.columns:
        st.error("Coluna 'Tipo' não encontrada. Certifica-te que o Excel tem a coluna 'Tipo' com 'Treino' e 'Jogo'.")
        st.stop()

    df_jogos_all   = df[df["Tipo"].str.strip().str.lower() == "jogo"].copy()
    df_treinos_all = df[df["Tipo"].str.strip().str.lower() == "treino"].copy()

    if df_jogos_all.empty:
        st.warning("Sem registos com Tipo = 'Jogo' encontrados.")
        st.stop()

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    mc_tvj   = col_f1.selectbox("Microciclo", sorted(df["Microciclo (Nr)"].dropna().unique(), reverse=True), key="tvj_mc")
    modo_tvj = col_f2.radio("Modo", ["Por Jogador", "Equipa (média)"], key="tvj_modo")
    referencia_tvj = col_f3.radio("Referência de jogo", ["Média de todos os jogos", "Último jogo"], key="tvj_ref")

    st.divider()

    # Calcular referência de jogo
    def media_jogos(df_j, met, jogador=None):
        sub = df_j if jogador is None else df_j[df_j["Jogador"] == jogador]
        if referencia_tvj == "Último jogo":
            sub = sub.sort_values("Data").tail(1)
        return sub[met].mean() if not sub.empty and met in sub.columns else np.nan

    df_treinos_mc = df_treinos_all[df_treinos_all["Microciclo (Nr)"] == mc_tvj]

    if df_treinos_mc.empty:
        st.warning(f"Sem sessões de treino no Microciclo {int(mc_tvj)}.")
        st.stop()

    # ── MODO EQUIPA ───────────────────────────────────────────────────────────
    if modo_tvj == "Equipa (média)":

        # Média de cada métrica por dia MD nos treinos
        dias_md_ordem = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
        dias_presentes = [d for d in dias_md_ordem if d in df_treinos_mc["Dia MD"].values]                          if "Dia MD" in df_treinos_mc.columns else []

        # ── Cards de % total do microciclo vs jogo ────────────────────────────
        st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)

        n_cols = len(mets_gps_disp)
        cols_cards = st.columns(n_cols)
        for i, met in enumerate(mets_gps_disp):
            # Média por sessão de treino (para comparar com um jogo individual)
            media_treino = df_treinos_mc.groupby("Jogador")[met].mean().mean()
            total_treino = df_treinos_mc[met].sum()
            ref_jogo     = media_jogos(df_jogos_all, met)
            if pd.isna(ref_jogo) or ref_jogo == 0:
                pct = None
            else:
                pct = media_treino / ref_jogo * 100

            if pct is None:
                cor, emoji = "#555", "❓"
            elif pct >= 150: cor, emoji = "#e74c3c", "🔴"
            elif pct >= 100: cor, emoji = "#f39c12", "🟡"
            elif pct >= 70:  cor, emoji = "#2ecc71", "🟢"
            else:            cor, emoji = "#3498db", "🔵"

            label = met.replace(" (m)","").replace(" (n)","")
            cols_cards[i].markdown(
                f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                f'padding:14px;text-align:center;margin:4px">'
                f'<div style="font-size:0.75rem;font-weight:700;color:#ccc;margin-bottom:4px">{label}</div>'
                f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                f'<div style="font-size:0.65rem;color:#aaa">média sessão treino / {"último jogo" if referencia_tvj=="Último jogo" else "média jogos"}</div>'
                f'<div style="font-size:0.75rem;color:#eee;margin-top:4px">'
                f'Média treino: {media_treino:,.0f} | Ref. jogo: {ref_jogo:,.0f}</div>'
                f'<div style="font-size:0.65rem;color:#777">Total semana: {total_treino:,.0f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # ── Gráfico por Dia MD — todas as métricas ─────────────────────────────
        if dias_presentes:
            st.markdown('<p class="section-title">% por Dia do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
            met_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_eq_met")

            ref_val = media_jogos(df_jogos_all, met_sel)
            dias_vals, dias_pcts, dias_abs = [], [], []

            for dia in dias_presentes:
                sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                # Média por jogador primeiro, depois média do grupo
                val = sub_dia.groupby("Jogador")[met_sel].mean().mean()
                dias_vals.append(dia)
                dias_abs.append(round(val, 1))
                dias_pcts.append(round(val / ref_val * 100, 1) if (ref_val and ref_val > 0) else 0)

            cores_dias = []
            for p in dias_pcts:
                if p >= 300:   cores_dias.append("#e74c3c")
                elif p >= 200: cores_dias.append("#f39c12")
                elif p >= 100: cores_dias.append("#2ecc71")
                else:          cores_dias.append("#3498db")

            fig_dias_tvj = go.Figure()
            fig_dias_tvj.add_trace(go.Bar(
                x=dias_vals, y=dias_pcts,
                marker_color=cores_dias,
                text=[f"{p:.0f}%" for p in dias_pcts],
                textposition="outside",
                name="% vs Jogo",
            ))
            fig_dias_tvj.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                    annotation_text="100% = equivalente ao jogo")
            fig_dias_tvj.add_hline(y=200, line_dash="dot", line_color="#f39c12",
                                    annotation_text="200%")
            fig_dias_tvj.update_layout(
                yaxis=dict(title="% vs Média de Jogos", range=[0, max(dias_pcts + [110]) * 1.15]),
                xaxis_title="Dia MD", height=380,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", showlegend=False, margin=dict(t=20),
            )
            st.plotly_chart(fig_dias_tvj, use_container_width=True)

            # Tabela dia a dia
            df_tabela_dias = pd.DataFrame({
                "Dia MD": dias_vals,
                met_sel: dias_abs,
                "Ref. Jogo": [round(ref_val, 1)] * len(dias_vals),
                "% vs Jogo": [f"{p:.0f}%" for p in dias_pcts],
            })
            st.dataframe(df_tabela_dias.set_index("Dia MD"), use_container_width=True)

        st.divider()

        # ── Radar — todas as métricas por dia MD ─────────────────────────────
        if dias_presentes and len(dias_presentes) >= 2:
            st.markdown('<p class="section-title">Radar — % vs Jogo por Dia MD (todas as métricas)</p>', unsafe_allow_html=True)
            dias_radar_sel = st.multiselect("Dias a comparar", dias_presentes,
                                             default=dias_presentes[:min(3, len(dias_presentes))],
                                             key="tvj_radar_dias")
            fig_radar_tvj = go.Figure()
            cores_r = ["#e63946","#457b9d","#2ecc71","#f39c12","#9b59b6","#1abc9c"]
            labels_r = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]

            for k, dia in enumerate(dias_radar_sel):
                sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                vals_r = []
                for met in mets_gps_disp:
                    ref = media_jogos(df_jogos_all, met)
                    val = sub_dia.groupby("Jogador")[met].mean().mean()
                    vals_r.append(round(val / ref * 100, 1) if (ref and ref > 0 and pd.notna(val)) else 0)
                vals_r_closed = vals_r + [vals_r[0]]
                labels_closed = labels_r + [labels_r[0]]
                fig_radar_tvj.add_trace(go.Scatterpolar(
                    r=vals_r_closed, theta=labels_closed,
                    fill="toself", name=dia,
                    line_color=cores_r[k % len(cores_r)], opacity=0.75,
                ))
            # Jogo = 100% linha de referência
            fig_radar_tvj.add_trace(go.Scatterpolar(
                r=[100] * (len(labels_r) + 1), theta=labels_r + [labels_r[0]],
                mode="lines", name="⚽ Jogo (100%)",
                line=dict(color="white", dash="dash", width=2),
            ))
            fig_radar_tvj.update_layout(
                polar=dict(radialaxis=dict(visible=True, ticksuffix="%")),
                height=460, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            )
            st.plotly_chart(fig_radar_tvj, use_container_width=True)

        st.divider()

        # ── Heatmap — dia MD × métrica ────────────────────────────────────────
        st.markdown('<p class="section-title">Heatmap — % vs Jogo (Dia MD × Métrica)</p>', unsafe_allow_html=True)
        if dias_presentes:
            heat_data, heat_text = [], []
            for dia in dias_presentes:
                row_vals, row_text = [], []
                sub_dia = df_treinos_mc[df_treinos_mc["Dia MD"] == dia]
                for met in mets_gps_disp:
                    ref = media_jogos(df_jogos_all, met)
                    val = sub_dia.groupby("Jogador")[met].mean().mean()
                    p = round(val / ref * 100, 0) if (ref and ref > 0 and pd.notna(val)) else 0
                    row_vals.append(p)
                    row_text.append(f"{p:.0f}%")
                heat_data.append(row_vals)
                heat_text.append(row_text)

            labels_heat = [m.replace(" (m)","").replace(" (n)","") for m in mets_gps_disp]
            fig_heat_tvj = go.Figure(go.Heatmap(
                z=heat_data, x=labels_heat, y=dias_presentes,
                text=heat_text, texttemplate="%{text}",
                colorscale="RdYlGn", zmid=100,
                colorbar=dict(title="% Jogo", ticksuffix="%"),
            ))
            fig_heat_tvj.update_layout(
                height=max(250, len(dias_presentes)*65),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", margin=dict(t=10),
            )
            st.plotly_chart(fig_heat_tvj, use_container_width=True)

        # ── Exportar ──────────────────────────────────────────────────────────
        st.divider()
        linhas_export = ""
        for met in mets_gps_disp:
            total_t = df_treinos_mc[met].sum()
            ref_j   = media_jogos(df_jogos_all, met)
            pct_e   = f"{total_t/ref_j*100:.0f}%" if (ref_j and ref_j > 0) else "—"
            linhas_export += f"<tr><td>{met}</td><td>{total_t:,.0f}</td><td>{ref_j:,.0f}</td><td><b>{pct_e}</b></td></tr>"
        html_tvj = gerar_pdf_html(f"""
<h1>Treino vs Jogo — MC {int(mc_tvj)}</h1>
<p>Referência: {referencia_tvj}</p>
<table><tr><th>Métrica</th><th>Total Treino</th><th>Ref. Jogo</th><th>% vs Jogo</th></tr>
{linhas_export}</table>
""", f"TreinoVsJogo_MC{int(mc_tvj)}.html")
        botao_download_html(html_tvj, f"TreinoVsJogo_MC{int(mc_tvj)}.html", "📥 Exportar Relatório (PDF)")

    # ── MODO JOGADOR ──────────────────────────────────────────────────────────
    else:
        jog_tvj = st.selectbox("Jogador", sorted(df["Jogador"].dropna().unique()), key="tvj_jog")

        df_t_jog = df_treinos_mc[df_treinos_mc["Jogador"] == jog_tvj]
        df_j_jog = df_jogos_all[df_jogos_all["Jogador"] == jog_tvj]

        if df_t_jog.empty:
            st.warning(f"Sem treinos para {jog_tvj} no MC {int(mc_tvj)}.")
            st.stop()

        # Cards
        st.markdown('<p class="section-title">% Total do Microciclo vs Média de Jogos</p>', unsafe_allow_html=True)
        cols_jog = st.columns(len(mets_gps_disp))
        for i, met in enumerate(mets_gps_disp):
            total_t = df_t_jog[met].sum()
            ref_j   = media_jogos(df_j_jog, met)
            pct     = total_t / ref_j * 100 if (ref_j and ref_j > 0) else None

            if pct is None: cor, emoji = "#555", "❓"
            elif pct >= 300: cor, emoji = "#e74c3c", "🔴"
            elif pct >= 200: cor, emoji = "#f39c12", "🟡"
            elif pct >= 100: cor, emoji = "#2ecc71", "🟢"
            else:            cor, emoji = "#3498db", "🔵"

            label = met.replace(" (m)","").replace(" (n)","")
            cols_jog[i].markdown(
                f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                f'padding:14px;text-align:center;margin:4px">'
                f'<div style="font-size:0.75rem;font-weight:700;color:#ccc">{label}</div>'
                f'<div style="font-size:2rem;font-weight:900;color:{cor}">'
                f'{"—" if pct is None else f"{pct:.0f}%"}</div>'
                f'<div style="font-size:0.7rem;color:#aaa">treino / jogo</div>'
                f'<div style="font-size:0.75rem;color:#eee;margin-top:2px">'
                f'T: {total_t:,.0f} | J: {ref_j:,.0f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # Por Dia MD
        if "Dia MD" in df_t_jog.columns:
            st.markdown('<p class="section-title">% por Dia do Microciclo</p>', unsafe_allow_html=True)
            met_jog_sel = st.selectbox("Métrica", mets_gps_disp, key="tvj_jog_met")
            ref_jog_val = media_jogos(df_j_jog, met_jog_sel)

            dias_jog_ord = ["MD-5","MD-4","MD-3","MD-2","MD-1","MD+1","MD+2"]
            dias_jog_pres = [d for d in dias_jog_ord if d in df_t_jog["Dia MD"].values]

            pcts_jog, vals_jog = [], []
            for dia in dias_jog_pres:
                val = df_t_jog[df_t_jog["Dia MD"] == dia][met_jog_sel].mean()
                vals_jog.append(round(val, 1))
                pcts_jog.append(round(val / ref_jog_val * 100, 1) if (ref_jog_val and ref_jog_val > 0) else 0)

            cores_jog_dias = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db" for p in pcts_jog]

            fig_jog_dias = go.Figure(go.Bar(
                x=dias_jog_pres, y=pcts_jog,
                marker_color=cores_jog_dias,
                text=[f"{p:.0f}%" for p in pcts_jog],
                textposition="outside",
            ))
            fig_jog_dias.add_hline(y=100, line_dash="dash", line_color="#2ecc71",
                                    annotation_text="100% = equivalente ao jogo")
            fig_jog_dias.update_layout(
                yaxis=dict(title="% vs Jogo", range=[0, max(pcts_jog + [110]) * 1.15]),
                height=360, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white",
                showlegend=False, margin=dict(t=20),
            )
            st.plotly_chart(fig_jog_dias, use_container_width=True)

        # Comparação entre jogadores da mesma posição
        st.divider()
        st.markdown('<p class="section-title">Comparação com Jogadores da Mesma Posição</p>', unsafe_allow_html=True)
        met_pos_tvj = st.selectbox("Métrica", mets_gps_disp, key="tvj_pos_met")

        pos_jog_tvj = df[df["Jogador"] == jog_tvj]["Posição"].iloc[-1] if "Posição" in df.columns else None
        if pos_jog_tvj:
            jogs_pos = df[df["Posição"] == pos_jog_tvj]["Jogador"].dropna().unique()
            rows_pos_tvj = []
            for jog_p in jogs_pos:
                t_p = df_treinos_mc[df_treinos_mc["Jogador"] == jog_p]
                j_p = df_jogos_all[df_jogos_all["Jogador"] == jog_p]
                if t_p.empty: continue
                total_p = t_p[met_pos_tvj].sum()
                ref_p   = media_jogos(j_p, met_pos_tvj)
                pct_p   = total_p / ref_p * 100 if (ref_p and ref_p > 0) else None
                rows_pos_tvj.append({"Jogador": jog_p, met_pos_tvj: round(total_p,1),
                                      "Ref. Jogo": round(ref_p,1) if ref_p else 0,
                                      "% vs Jogo": round(pct_p,1) if pct_p else 0})

            if rows_pos_tvj:
                df_pos_tvj = pd.DataFrame(rows_pos_tvj).sort_values("% vs Jogo", ascending=True)
                cores_pos_tvj = ["#e74c3c" if p>=300 else "#f39c12" if p>=200 else "#2ecc71" if p>=100 else "#3498db"
                                  for p in df_pos_tvj["% vs Jogo"]]
                fig_pos_tvj = go.Figure(go.Bar(
                    y=df_pos_tvj["Jogador"], x=df_pos_tvj["% vs Jogo"],
                    orientation="h", marker_color=cores_pos_tvj,
                    text=[f"{p:.0f}%" for p in df_pos_tvj["% vs Jogo"]],
                    textposition="outside",
                ))
                fig_pos_tvj.add_vline(x=100, line_dash="dash", line_color="#2ecc71",
                                       annotation_text="100% = jogo")
                fig_pos_tvj.update_layout(
                    xaxis_title="% vs Média de Jogos", height=max(250, len(df_pos_tvj)*50),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white", showlegend=False, margin=dict(t=10),
                )
                # Destaque o jogador selecionado
                idx_jog = df_pos_tvj["Jogador"].tolist().index(jog_tvj) if jog_tvj in df_pos_tvj["Jogador"].tolist() else -1
                if idx_jog >= 0:
                    cores_pos_tvj[idx_jog] = "#e63946"
                st.plotly_chart(fig_pos_tvj, use_container_width=True)




# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: MONOTONIA & STRAIN (FOSTER)
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "⚡ Monotonia & Strain":
    df_f = df_f_dia
    st.title("⚡ Monotonia & Strain (Foster)")
    st.markdown("""
    > **Monotonia** mede se o treino é sempre igual — treinos muito repetitivos são prejudiciais mesmo com carga baixa.  
    > **Strain** combina a carga total com a monotonia — semanas intensas *e* monótonas são as mais arriscadas.
    """)

    LIMIAR_MONO = 2.0
    LIMIAR_MONO_ATENCAO = 1.5

    def calcular_mono_strain(df_base: pd.DataFrame):
        rows = []
        for jog in sorted(df_base["Jogador"].dropna().unique()):
            sub = df_base[df_base["Jogador"] == jog].dropna(subset=["Microciclo (Nr)", "Carga Interna"])
            for mc in sub["Microciclo (Nr)"].unique():
                mc_sub = sub[sub["Microciclo (Nr)"] == mc]["Carga Interna"]
                if len(mc_sub) < 2: continue
                media = mc_sub.mean()
                dp    = mc_sub.std()
                total = mc_sub.sum()
                mono  = media / dp if dp > 0 else 0
                strain = total * mono
                pos = df_base[df_base["Jogador"] == jog]["Posição"].iloc[-1] if "Posição" in df_base.columns else "—"

                if mono > LIMIAR_MONO:         estado_m, cor_m = "🔴 Excessiva",   "#e74c3c"
                elif mono > LIMIAR_MONO_ATENCAO: estado_m, cor_m = "🟡 Atenção",    "#f39c12"
                else:                            estado_m, cor_m = "🟢 Boa variação","#2ecc71"

                rows.append({
                    "Jogador": jog, "Posição": pos, "Microciclo": int(mc),
                    "Carga Total": round(total, 0),
                    "Média Diária": round(media, 1),
                    "DP": round(dp, 1),
                    "Monotonia": round(mono, 2),
                    "Strain": round(strain, 0),
                    "Estado": estado_m,
                    "_cor": cor_m,
                })
        return pd.DataFrame(rows)

    df_ms = calcular_mono_strain(df_f)

    if df_ms.empty:
        st.warning("Dados insuficientes para calcular Monotonia & Strain. Necessário pelo menos 2 sessões por microciclo.")
        st.stop()

    tab_ms1, tab_ms2 = st.tabs(["🏟️ Vista de Equipa", "👤 Jogador Individual"])

    with tab_ms1:
        mc_ms = st.selectbox("Microciclo", sorted(df_ms["Microciclo"].unique(), reverse=True), key="ms_mc")
        df_ms_mc = df_ms[df_ms["Microciclo"] == mc_ms]

        # KPIs
        k1,k2,k3 = st.columns(3)
        k1.metric("Monotonia Média", f"{df_ms_mc['Monotonia'].mean():.2f}",
                  help="Ideal: <1.5 | Atenção: 1.5–2.0 | Excessivo: >2.0")
        k2.metric("Strain Médio",    f"{df_ms_mc['Strain'].mean():,.0f}",
                  help="Carga Total × Monotonia. Quanto maior, maior o risco acumulado.")
        k3.metric("Jogadores em risco de monotonia", f"{len(df_ms_mc[df_ms_mc['Monotonia'] > LIMIAR_MONO])}")

        st.divider()

        # Monotonia por jogador
        st.markdown('<p class="section-title">Monotonia por Jogador</p>', unsafe_allow_html=True)
        df_ms_sorted = df_ms_mc.sort_values("Monotonia", ascending=False)
        fig_mono = go.Figure(go.Bar(
            x=df_ms_sorted["Jogador"], y=df_ms_sorted["Monotonia"],
            marker_color=df_ms_sorted["_cor"].tolist(),
            text=df_ms_sorted["Monotonia"].round(2), textposition="outside",
        ))
        fig_mono.add_hline(y=LIMIAR_MONO,        line_dash="dash", line_color="#e74c3c",  annotation_text="Excessiva (2.0)")
        fig_mono.add_hline(y=LIMIAR_MONO_ATENCAO, line_dash="dot",  line_color="#f39c12", annotation_text="Atenção (1.5)")
        fig_mono.update_layout(
            yaxis_title="Monotonia", height=380,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False, margin=dict(t=20),
        )
        st.plotly_chart(fig_mono, use_container_width=True)

        # Scatter Strain vs Carga Total
        st.markdown('<p class="section-title">Strain vs Carga Total — Quadrantes de Risco</p>', unsafe_allow_html=True)
        st.caption("Ideal: carga alta com baixa monotonia (quadrante inferior direito)")

        if len(df_ms_mc) >= 2 and df_ms_mc["Carga Total"].nunique() > 1:
            fig_scatter = px.scatter(
                df_ms_mc, x="Carga Total", y="Monotonia",
                text="Jogador", color="Estado",
                color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
                size="Strain", size_max=40,
                hover_data=["Strain", "Média Diária", "DP"],
            )
        else:
            fig_scatter = px.scatter(
                df_ms_mc, x="Carga Total", y="Monotonia",
                text="Jogador", color="Estado",
                color_discrete_map={"🔴 Excessiva": "#e74c3c", "🟡 Atenção": "#f39c12", "🟢 Boa variação": "#2ecc71"},
            )
        fig_scatter.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c")
        fig_scatter.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12")
        fig_scatter.update_traces(textposition="top center")
        fig_scatter.update_layout(
            height=420, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(t=20),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Tabela
        st.dataframe(
            df_ms_mc[["Jogador","Posição","Carga Total","Média Diária","DP","Monotonia","Strain","Estado"]]
            .set_index("Jogador"), use_container_width=True
        )

        # Conclusões
        st.divider()
        st.markdown('<p class="section-title">🧠 Conclusões Automáticas</p>', unsafe_allow_html=True)
        risco_mono  = df_ms_mc[df_ms_mc["Monotonia"] > LIMIAR_MONO]["Jogador"].tolist()
        atenc_mono  = df_ms_mc[df_ms_mc["Monotonia"].between(LIMIAR_MONO_ATENCAO, LIMIAR_MONO)]["Jogador"].tolist()
        strain_top  = df_ms_mc.nlargest(3, "Strain")[["Jogador","Strain"]].values.tolist()

        if risco_mono:
            st.markdown(f"🔴 **Monotonia excessiva** (>2.0): {', '.join(risco_mono)} — variar a estrutura das sessões com urgência (intensidade, volume, tipo de exercício).")
        if atenc_mono:
            st.markdown(f"🟡 **Atenção à monotonia** (1.5–2.0): {', '.join(atenc_mono)} — introduzir mais variação nos próximos dias.")
        if not risco_mono and not atenc_mono:
            st.markdown("🟢 **Toda a equipa com boa variação de carga** neste microciclo.")
        st.markdown("**Top 3 Strain** neste microciclo:")
        for jog_s, strain_s in strain_top:
            st.markdown(f"  ▸ **{jog_s}**: {strain_s:,.0f} UA")

    with tab_ms2:
        jog_ms = st.selectbox("Jogador", sorted(df_ms["Jogador"].unique()), key="ms_jog")
        df_ms_jog = df_ms[df_ms["Jogador"] == jog_ms].sort_values("Microciclo")

        fig_ms_ev = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                   subplot_titles=["Monotonia", "Strain"],
                                   vertical_spacing=0.12)
        fig_ms_ev.add_trace(go.Scatter(
            x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Monotonia"],
            mode="lines+markers+text", text=df_ms_jog["Monotonia"].round(2),
            textposition="top center", line_color="#e63946", name="Monotonia",
        ), row=1, col=1)
        fig_ms_ev.add_trace(go.Bar(
            x=df_ms_jog["Microciclo"].astype(str), y=df_ms_jog["Strain"],
            marker_color="#457b9d", name="Strain",
        ), row=2, col=1)
        fig_ms_ev.add_hline(y=LIMIAR_MONO,         line_dash="dash", line_color="#e74c3c",  row=1, col=1)
        fig_ms_ev.add_hline(y=LIMIAR_MONO_ATENCAO,  line_dash="dot",  line_color="#f39c12", row=1, col=1)
        fig_ms_ev.update_layout(
            height=480, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            showlegend=False, margin=dict(t=30),
            xaxis2_title="Microciclo",
        )
        st.plotly_chart(fig_ms_ev, use_container_width=True)

        # Detalhe das sessões do microciclo selecionado
        mc_ms_jog = st.selectbox("Ver detalhe do Microciclo", sorted(df_ms_jog["Microciclo"].unique(), reverse=True), key="ms_jog_mc")
        sessoes_mc = df_f[(df_f["Jogador"] == jog_ms) & (df_f["Microciclo (Nr)"] == mc_ms_jog) & (df_f["Carga Interna"].notna())]
        if not sessoes_mc.empty:
            fig_sess = go.Figure(go.Bar(
                x=sessoes_mc["Dia MD"] if "Dia MD" in sessoes_mc.columns else sessoes_mc["Data"].dt.strftime("%d/%m"),
                y=sessoes_mc["Carga Interna"],
                marker_color="#e63946",
                text=sessoes_mc["Carga Interna"].round(0), textposition="outside",
            ))
            fig_sess.add_hline(
                y=sessoes_mc["Carga Interna"].mean(),
                line_dash="dash", line_color="white",
                annotation_text=f"Média: {sessoes_mc['Carga Interna'].mean():.0f}",
            )
            fig_sess.update_layout(
                yaxis_title="Carga Interna (UA)", height=300,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="white", margin=dict(t=10),
            )
            st.plotly_chart(fig_sess, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: LOG DE ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🕓 Log de Alertas":
    st.title("🕓 Histórico de Alertas")
    st.caption("Registo automático de todos os alertas gerados ao longo do tempo")

    log = carregar_log()

    col_l1, col_l2 = st.columns([3,1])
    with col_l2:
        if st.button("🗑️ Limpar todo o histórico", type="secondary"):
            LOG_PATH.write_text("[]", encoding="utf-8")
            st.rerun()
        if st.button("📥 Exportar histórico", type="secondary"):
            if log:
                df_log_exp = pd.DataFrame(log)
                linhas_log = "".join([
                    f'<tr><td>{r["data"]}</td><td>{r["jogador"]}</td>'
                    f'<td>{r["tipo"]}</td><td>{r["descricao"]}</td><td>{r["valor"]}</td></tr>'
                    for r in log
                ])
                html_log = gerar_pdf_html(f"""
<h1>Histórico de Alertas</h1>
<table><tr><th>Data</th><th>Jogador</th><th>Tipo</th><th>Descrição</th><th>Valor</th></tr>
{linhas_log}</table>""", "Historico_Alertas.html")
                botao_download_html(html_log, "Historico_Alertas.html", "📥 Exportar (PDF)")

    if not log:
        st.info("Ainda não há alertas registados. Abre a página **🚨 Alertas do Dia** para gerar os primeiros alertas.")
        st.stop()

    df_log = pd.DataFrame(log)
    df_log["data"] = pd.to_datetime(df_log["data"])
    df_log = df_log.sort_values("data", ascending=False)

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    tipos_log  = ["Todos"] + sorted(df_log["tipo"].unique().tolist())
    jogs_log   = ["Todos"] + sorted(df_log["jogador"].unique().tolist())
    tipo_sel_l = col_f1.selectbox("Tipo de alerta", tipos_log, key="log_tipo")
    jog_sel_l  = col_f2.selectbox("Jogador",        jogs_log,  key="log_jog")

    df_log_f = df_log.copy()
    if tipo_sel_l != "Todos": df_log_f = df_log_f[df_log_f["tipo"] == tipo_sel_l]
    if jog_sel_l  != "Todos": df_log_f = df_log_f[df_log_f["jogador"] == jog_sel_l]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total de alertas",        len(df_log_f))
    k2.metric("Jogadores com alertas",   df_log_f["jogador"].nunique())
    k3.metric("Alertas hoje",
              len(df_log_f[df_log_f["data"].dt.date == date.today()]))
    k4.metric("Alerta mais recente",
              df_log_f["data"].max().strftime("%d/%m %H:%M") if not df_log_f.empty else "—")

    st.divider()

    # ── Gráfico de frequência de alertas no tempo ────────────────────────────
    st.markdown('<p class="section-title">Frequência de Alertas ao Longo do Tempo</p>', unsafe_allow_html=True)
    df_log_f["dia"] = df_log_f["data"].dt.date
    freq = df_log_f.groupby(["dia","tipo"]).size().reset_index(name="n")
    if not freq.empty:
        fig_freq = px.bar(freq, x="dia", y="n", color="tipo",
                          color_discrete_sequence=px.colors.qualitative.Bold,
                          labels={"dia":"Data","n":"Nº Alertas","tipo":"Tipo"})
        fig_freq.update_layout(
            height=300, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            margin=dict(t=10), legend_title="",
        )
        st.plotly_chart(fig_freq, use_container_width=True)

    # ── Alertas por jogador ───────────────────────────────────────────────────
    st.markdown('<p class="section-title">Alertas por Jogador</p>', unsafe_allow_html=True)
    jog_count = df_log_f.groupby("jogador").size().sort_values(ascending=True).reset_index(name="n")
    fig_jog_log = go.Figure(go.Bar(
        y=jog_count["jogador"], x=jog_count["n"],
        orientation="h", marker_color="#e63946",
        text=jog_count["n"], textposition="outside",
    ))
    fig_jog_log.update_layout(
        height=max(200, len(jog_count)*40),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", xaxis_title="Nº de alertas", margin=dict(t=10),
    )
    st.plotly_chart(fig_jog_log, use_container_width=True)

    # ── Timeline de alertas ───────────────────────────────────────────────────
    st.divider()
    st.markdown('<p class="section-title">📋 Registo Detalhado</p>', unsafe_allow_html=True)

    COR_TIPO = {"ACWR": "#e74c3c", "Wellness": "#f39c12", "Vmáx": "#3498db"}
    for _, row in df_log_f.head(100).iterrows():
        cor_t = COR_TIPO.get(row["tipo"], "#888")
        st.markdown(
            f'<div style="border-left:4px solid {cor_t};padding:8px 12px;margin:4px 0;'
            f'background:{cor_t}15;border-radius:0 8px 8px 0">'
            f'<span style="font-size:0.75rem;color:#aaa">{row["data"].strftime("%d/%m/%Y %H:%M")}</span> '
            f'<span style="background:{cor_t};color:white;padding:2px 8px;border-radius:4px;'
            f'font-size:0.75rem;font-weight:700;margin:0 6px">{row["tipo"]}</span>'
            f'<b>{row["jogador"]}</b> — {row["descricao"]} '
            f'<span style="color:{cor_t};font-weight:700">({row["valor"]})</span>'
            f'</div>',
            unsafe_allow_html=True
        )
    if len(df_log_f) > 100:
        st.caption(f"A mostrar os 100 alertas mais recentes de {len(df_log_f)} total.")


# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: GLOSSÁRIO
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📖 Glossário":
    st.title("📖 Glossário")
    st.caption("Explicação simples e técnica de cada métrica e conceito utilizado no dashboard")

    nivel = st.radio("Nível de explicação", ["🟢 Simples (não-especialista)", "🔵 Técnico (especialista)"],
                     horizontal=True, key="gloss_nivel")
    simples = nivel.startswith("🟢")

    pesquisa = st.text_input("🔍 Pesquisar métrica...", key="gloss_pesq").lower()

    st.divider()

    for nome, info in GLOSSARIO.items():
        if pesquisa and pesquisa not in nome.lower() and pesquisa not in info["simples"].lower():
            continue
        with st.expander(f"**{nome}**"):
            if simples:
                st.markdown(f"📌 {info['simples']}")
            else:
                st.markdown(f"🔬 **Definição técnica:** {info['tecnico']}")
                st.markdown(f"📌 **Em linguagem simples:** {info['simples']}")

            if info["zonas"]:
                st.markdown("**Zonas de referência:**")
                cols_z = st.columns(len(info["zonas"]))
                for i, (zona, valor) in enumerate(info["zonas"].items()):
                    cols_z[i].markdown(
                        f'<div style="background:#1e2330;border-radius:8px;padding:8px;text-align:center">'
                        f'<div style="font-size:0.85rem;font-weight:700">{zona}</div>'
                        f'<div style="font-size:0.8rem;color:#aaa">{valor}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

    st.divider()
    st.markdown("""
    ### 📚 Referências Bibliográficas
    - **Foster et al. (2001)** — A New Approach to Monitoring Exercise Training. *Journal of Strength and Conditioning Research.*
    - **Gabbett (2016)** — The training-injury prevention paradox. *British Journal of Sports Medicine.*
    - **Malone et al. (2017)** — High chronic training loads and exposure to bouts of maximal velocity running. *Journal of Science and Medicine in Sport.*
    - **Hooper & Mackinnon (1995)** — Monitoring overtraining in athletes. *Sports Medicine.*
    """)




# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: RESUMO DO DIA
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "📅 Resumo do Dia":
    st.title("📅 Resumo do Dia de Treino")
    st.caption("Seleciona uma data e vê tudo o que aconteceu nesse treino — ideal para a reunião pós-sessão")

    METS_DIA = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)",
                "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)", "Duração (min)"]
    mets_dia_disp = [m for m in METS_DIA if m in df.columns]

    # ── Seletor de data ───────────────────────────────────────────────────────
    datas_disponiveis = sorted(df["Data"].dropna().dt.date.unique(), reverse=True)
    if not datas_disponiveis:
        st.warning("Sem datas disponíveis nos dados.")
        st.stop()

    col_d1, col_d2 = st.columns([2, 3])
    data_sel = col_d1.selectbox(
        "📆 Data do treino",
        datas_disponiveis,
        format_func=lambda d: d.strftime("%d/%m/%Y — %A").replace(
            "Monday","Segunda").replace("Tuesday","Terça").replace("Wednesday","Quarta")
            .replace("Thursday","Quinta").replace("Friday","Sexta")
            .replace("Saturday","Sábado").replace("Sunday","Domingo"),
        key="dia_data"
    )

    df_dia = df[df["Data"].dt.date == data_sel].copy()

    if df_dia.empty:
        st.warning(f"Sem dados para {data_sel.strftime('%d/%m/%Y')}.")
        st.stop()

    tipo_dia = df_dia["Tipo"].iloc[0] if "Tipo" in df_dia.columns else "Treino"
    dia_md   = df_dia["Dia MD"].iloc[0] if "Dia MD" in df_dia.columns else "—"
    mc_dia   = int(df_dia["Microciclo (Nr)"].iloc[0]) if "Microciclo (Nr)" in df_dia.columns else "—"
    n_jogs   = df_dia["Jogador"].nunique()

    col_d2.markdown(f"""
    | | |
    |---|---|
    | **Tipo** | {tipo_dia} |
    | **Dia MD** | {dia_md} |
    | **Microciclo** | {mc_dia} |
    | **Jogadores presentes** | {n_jogs} |
    """)

    st.divider()

    # ── KPIs do dia (médias da equipa) ────────────────────────────────────────
    st.markdown('<p class="section-title">📊 Médias da Equipa no Treino</p>', unsafe_allow_html=True)

    kpi_mets = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Carga Interna", "PSE Sessão", "Vel. Máx (km/h)"]
    kpi_disp = [m for m in kpi_mets if m in df_dia.columns]
    cols_kpi = st.columns(len(kpi_disp))
    for i, met in enumerate(kpi_disp):
        val = df_dia[met].mean()
        label = met.replace(" (m)","").replace(" (n)","").replace(" (min)","")

        # Comparar com média histórica do mesmo Dia MD
        if dia_md != "—" and "Dia MD" in df.columns:
            hist = df[df["Dia MD"] == dia_md][met].mean()
            delta = val - hist
            delta_str = f"{delta:+.1f} vs média {dia_md}"
        else:
            delta_str = None

        cols_kpi[i].metric(label, f"{val:,.1f}", delta=delta_str,
                            help=f"Média da equipa em {met} neste treino")

    st.divider()

    # ── Quem foi o mais exigente? ─────────────────────────────────────────────
    st.markdown('<p class="section-title">🏆 Ranking de Exigência — Quem fez mais?</p>', unsafe_allow_html=True)

    met_rank = st.selectbox("Métrica para ranking", mets_dia_disp, key="dia_rank_met")
    df_rank = df_dia.dropna(subset=[met_rank]).sort_values(met_rank, ascending=False).copy()
    df_rank["Rank"] = range(1, len(df_rank)+1)

    if not df_rank.empty:
        top1 = df_rank.iloc[0]
        media_eq = df_rank[met_rank].mean()

        col_top1, col_top2, col_top3 = st.columns(3)
        col_top1.markdown(
            f'<div style="background:#f39c1222;border:2px solid #f39c12;border-radius:12px;padding:16px;text-align:center">'
            f'<div style="font-size:0.8rem;color:#aaa">🥇 Maior {met_rank.split("(")[0].strip()}</div>'
            f'<div style="font-size:1.5rem;font-weight:900;color:#f39c12">{top1["Jogador"]}</div>'
            f'<div style="font-size:1.1rem;color:#eee">{top1[met_rank]:,.1f}</div>'
            f'</div>', unsafe_allow_html=True
        )
        if len(df_rank) >= 2:
            top2 = df_rank.iloc[1]
            col_top2.markdown(
                f'<div style="background:#ffffff11;border:2px solid #888;border-radius:12px;padding:16px;text-align:center">'
                f'<div style="font-size:0.8rem;color:#aaa">🥈 2º lugar</div>'
                f'<div style="font-size:1.4rem;font-weight:700;color:#ccc">{top2["Jogador"]}</div>'
                f'<div style="font-size:1.1rem;color:#eee">{top2[met_rank]:,.1f}</div>'
                f'</div>', unsafe_allow_html=True
            )
        if len(df_rank) >= 3:
            top3 = df_rank.iloc[2]
            col_top3.markdown(
                f'<div style="background:#cd7f3222;border:2px solid #cd7f32;border-radius:12px;padding:16px;text-align:center">'
                f'<div style="font-size:0.8rem;color:#aaa">🥉 3º lugar</div>'
                f'<div style="font-size:1.4rem;font-weight:700;color:#cd7f32">{top3["Jogador"]}</div>'
                f'<div style="font-size:1.1rem;color:#eee">{top3[met_rank]:,.1f}</div>'
                f'</div>', unsafe_allow_html=True
            )

        st.markdown("")

        # Gráfico ranking horizontal
        cores_rank = []
        for v in df_rank[met_rank]:
            pct = v / df_rank[met_rank].max() if df_rank[met_rank].max() > 0 else 0
            if pct >= 0.9:   cores_rank.append("#f39c12")
            elif pct >= 0.7: cores_rank.append("#e63946")
            else:            cores_rank.append("#457b9d")

        fig_rank = go.Figure(go.Bar(
            y=df_rank["Jogador"], x=df_rank[met_rank],
            orientation="h", marker_color=cores_rank,
            text=df_rank[met_rank].round(1), textposition="outside",
        ))
        fig_rank.add_vline(x=media_eq, line_dash="dash", line_color="white",
                            annotation_text=f"Média: {media_eq:,.1f}")
        fig_rank.update_layout(
            height=max(300, len(df_rank)*45),
            xaxis_title=met_rank, yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False, margin=dict(t=10),
        )
        st.plotly_chart(fig_rank, use_container_width=True)

    st.divider()

    # ── Distribuição por posição ───────────────────────────────────────────────
    if "Posição" in df_dia.columns and df_dia["Posição"].notna().any():
        st.markdown('<p class="section-title">📐 Comparação por Posição</p>', unsafe_allow_html=True)
        met_pos_dia = st.selectbox("Métrica", mets_dia_disp, key="dia_pos_met")

        df_pos_dia = df_dia.dropna(subset=[met_pos_dia, "Posição"])
        fig_pos_dia = px.box(
            df_pos_dia, x="Posição", y=met_pos_dia,
            color="Posição", points="all",
            hover_data=["Jogador"],
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_pos_dia.update_layout(
            height=380, showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", margin=dict(t=10),
        )
        st.plotly_chart(fig_pos_dia, use_container_width=True)
        st.divider()

    # ── Painel completo por jogador ────────────────────────────────────────────
    st.markdown('<p class="section-title">👥 Painel Completo — Todos os Jogadores</p>', unsafe_allow_html=True)

    # Heatmap todas as métricas × jogadores (Z-Score do dia)
    df_heat_dia = df_dia.set_index("Jogador")[mets_dia_disp].copy()
    df_heat_dia_z = df_heat_dia.apply(
        lambda col: (col - col.mean()) / col.std() if col.std() > 0 else col * 0, axis=0
    )
    labels_heat = [m.replace(" (m)","").replace(" (n)","").replace(" (min)","") for m in mets_dia_disp]
    df_heat_dia_z.columns = labels_heat

    fig_heat_dia = go.Figure(go.Heatmap(
        z=df_heat_dia_z.values,
        x=df_heat_dia_z.columns.tolist(),
        y=df_heat_dia_z.index.tolist(),
        text=df_heat_dia.round(1).values,
        texttemplate="%{text}",
        colorscale="RdYlGn",
        zmid=0,
        colorbar=dict(title="Z-Score"),
    ))
    fig_heat_dia.update_layout(
        height=max(300, len(df_heat_dia)*45),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="white", margin=dict(t=10),
        xaxis_title="Métrica", yaxis_title="Jogador",
    )
    st.plotly_chart(fig_heat_dia, use_container_width=True)
    st.caption("🟢 Verde = acima da média do grupo neste treino | 🔴 Vermelho = abaixo | Valores = dados reais")

    # Tabela completa
    with st.expander("📋 Ver tabela completa de valores"):
        cols_tabela_dia = ["Jogador"] + [c for c in ["Posição", "Dia MD", "Duração (min)"] if c in df_dia.columns] +                           [m for m in mets_dia_disp if m != "Duração (min)"]
        st.dataframe(
            df_dia[[c for c in cols_tabela_dia if c in df_dia.columns]]
            .sort_values("Carga Interna" if "Carga Interna" in df_dia.columns else "Jogador", ascending=False)
            .set_index("Jogador"),
            use_container_width=True
        )

    st.divider()

    # ── Wellness do dia ────────────────────────────────────────────────────────
    w_cols_dia = [c for c in ["Sono (1-5)", "Dor Musc. (1-5)", "Stress (1-5)", "Humor (1-5)", "Hooper Index"] if c in df_dia.columns]
    if w_cols_dia and df_dia[w_cols_dia].notna().any().any():
        st.markdown('<p class="section-title">💤 Wellness — Estado dos Jogadores Neste Dia</p>', unsafe_allow_html=True)

        df_well_dia = df_dia.dropna(subset=w_cols_dia, how="all").copy()
        if not df_well_dia.empty:
            for _, row in df_well_dia.iterrows():
                alertas_w = []
                hi = row.get("Hooper Index", np.nan)
                sono = row.get("Sono (1-5)", np.nan)
                stress = row.get("Stress (1-5)", np.nan)
                dor = row.get("Dor Musc. (1-5)", np.nan)
                if pd.notna(hi) and hi >= 14:   alertas_w.append(f"Hooper {hi:.0f} 🔴")
                if pd.notna(sono) and sono <= 2: alertas_w.append(f"Sono {sono:.0f}/5 🔴")
                if pd.notna(stress) and stress >= 4: alertas_w.append(f"Stress {stress:.0f}/5 🔴")
                if pd.notna(dor) and dor >= 4:   alertas_w.append(f"Dor {dor:.0f}/5 🔴")

                cor_w = "#e74c3c" if alertas_w else "#2ecc71"
                msg_w = " · ".join(alertas_w) if alertas_w else "✅ Sem alertas"
                st.markdown(
                    f'<div style="border-left:4px solid {cor_w};padding:6px 12px;margin:3px 0;'
                    f'background:{cor_w}15;border-radius:0 8px 8px 0">'
                    f'<b>{row["Jogador"]}</b> — {msg_w}</div>',
                    unsafe_allow_html=True
                )

    st.divider()

    # ── Exportar relatório do dia ─────────────────────────────────────────────
    st.markdown('<p class="section-title">📥 Exportar Relatório do Treino</p>', unsafe_allow_html=True)

    rows_exp = df_dia[["Jogador"] + [m for m in mets_dia_disp if m in df_dia.columns]].copy()
    if "Posição" in df_dia.columns:
        rows_exp.insert(1, "Posição", df_dia["Posição"].values)
    rows_exp = rows_exp.sort_values("Carga Interna" if "Carga Interna" in rows_exp.columns else "Jogador", ascending=False)

    headers_exp = "".join([f"<th>{c}</th>" for c in rows_exp.columns])
    linhas_exp  = "".join([
        f'<tr>{"".join(f"<td>{round(row[c],1) if isinstance(row[c], float) else row[c]}</td>" for c in rows_exp.columns)}</tr>'
        for _, row in rows_exp.iterrows()
    ])
    html_dia = gerar_pdf_html(f"""
<h1>Relatório de Treino — {data_sel.strftime("%d/%m/%Y")} ({dia_md} | MC {mc_dia})</h1>
<p><b>Jogadores presentes:</b> {n_jogs} | <b>Tipo:</b> {tipo_dia}</p>
<h2>Dados GPS & Carga</h2>
<table><tr>{headers_exp}</tr>{linhas_exp}</table>
<h2>Destaques</h2>
<ul>
{"".join(f"<li>🏆 Maior {m.split('(')[0].strip()}: <b>{df_dia.loc[df_dia[m].idxmax(),'Jogador']}</b> ({df_dia[m].max():.1f})</li>" for m in mets_dia_disp if df_dia[m].notna().any())}
</ul>
""", f"Treino_{data_sel.strftime('%Y%m%d')}.html")

    botao_download_html(html_dia, f"Treino_{data_sel.strftime('%Y%m%d')}.html",
                        f"📥 Exportar Relatório — {data_sel.strftime('%d/%m/%Y')}")




# ═══════════════════════════════════════════════════════════════════════════════
# VISTA: ANÁLISE DE EXERCÍCIOS
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏋️ Análise de Exercícios":
    st.title("🏋️ Análise de Exercícios")
    st.caption("Qual foi o exercício mais exigente? Como se comparam por categoria e dia?")

    METS_EX = ["Distância Total (m)", "HSR (m)", "Sprint (m)", "Acc (n)", "Dcc (n)",
               "Vel. Máx (km/h)", "Carga Interna Ex."]

    df_ex = carregar_exercicios(excel_path)

    if df_ex.empty:
        st.info("""
### 📋 Folha de Exercícios vazia

Abre o Excel e preenche a folha **Exercícios** com os dados de cada exercício.
As linhas a azul claro são exemplos — podes apagá-las e começar a preencher a partir da linha 10.

**Colunas a preencher:**
- **Data** — data do treino
- **Microciclo (Nr)** — número do microciclo
- **Dia MD** — ex: MD-3, MD-2, MD-1
- **Nome do Exercício** — ex: "Joguinho posicional 4x4"
- **Categoria** — ex: Jogo Reduzido, Físico, Técnico-Tático
- **Duração (min)** — duração do exercício
- **Nº Jogadores** — número de jogadores
- **Distância Total, HSR, Sprint, Acc, Dcc, Vel. Máx** — médias por jogador no exercício

Depois guarda o Excel e clica em **🔄 Atualizar Dados**.
        """)
        st.stop()

    mets_ex_disp = [m for m in METS_EX if m in df_ex.columns and df_ex[m].notna().any()]

    # ── Filtros ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)

    datas_ex = sorted(df_ex["Data"].dropna().dt.date.unique(), reverse=True) if "Data" in df_ex.columns else []
    mcs_ex   = sorted(df_ex["Microciclo (Nr)"].dropna().unique(), reverse=True) if "Microciclo (Nr)" in df_ex.columns else []
    cats_ex  = sorted(df_ex["Categoria"].dropna().unique()) if "Categoria" in df_ex.columns else []

    modo_ex = col_f1.radio("Modo de análise", ["📅 Por sessão (dia)", "📆 Por microciclo", "📊 Geral"], horizontal=True)

    if modo_ex == "📅 Por sessão (dia)":
        data_ex_sel = col_f2.selectbox(
            "Data", datas_ex,
            format_func=lambda d: d.strftime("%d/%m/%Y"),
            key="ex_data"
        )
        df_ex_f = df_ex[df_ex["Data"].dt.date == data_ex_sel] if "Data" in df_ex.columns else df_ex
        titulo_ctx = f"Treino de {data_ex_sel.strftime('%d/%m/%Y')}"

    elif modo_ex == "📆 Por microciclo":
        mc_ex_sel = col_f2.selectbox("Microciclo", mcs_ex, key="ex_mc")
        df_ex_f = df_ex[df_ex["Microciclo (Nr)"] == mc_ex_sel] if "Microciclo (Nr)" in df_ex.columns else df_ex
        titulo_ctx = f"Microciclo {int(mc_ex_sel)}"
    else:
        df_ex_f = df_ex.copy()
        titulo_ctx = "Todos os exercícios"

    cat_sel = col_f3.multiselect("Categoria", cats_ex, default=cats_ex, key="ex_cat")
    if cat_sel and "Categoria" in df_ex_f.columns:
        df_ex_f = df_ex_f[df_ex_f["Categoria"].isin(cat_sel)]

    if df_ex_f.empty:
        st.warning("Sem exercícios para os filtros selecionados.")
        st.stop()

    met_ex = st.selectbox("Métrica de análise", mets_ex_disp, key="ex_met",
                           help="Métrica usada para ordenar e comparar exercícios")

    st.divider()

    # ── Exercício mais exigente ────────────────────────────────────────────────
    st.markdown(f'<p class="section-title">🏆 Exercício Mais Exigente — {titulo_ctx}</p>', unsafe_allow_html=True)

    df_ex_rank = df_ex_f.dropna(subset=[met_ex]).sort_values(met_ex, ascending=False).copy()

    if not df_ex_rank.empty:
        top = df_ex_rank.iloc[0]
        segundo = df_ex_rank.iloc[1] if len(df_ex_rank) > 1 else None
        terceiro = df_ex_rank.iloc[2] if len(df_ex_rank) > 2 else None

        c1, c2, c3 = st.columns(3)
        def card_ex(col, row, medal, cor):
            nome = str(row["Exercício"])[:30] if "Exercício" in df_ex_rank.columns else "—"
            cat  = row.get("Categoria","—")
            dur  = row.get("Duração (min)","—")
            val  = row[met_ex]
            col.markdown(
                f'<div style="background:{cor}22;border:2px solid {cor};border-radius:12px;'
                f'padding:14px;text-align:center;margin:4px">'
                f'<div style="font-size:1.4rem">{medal}</div>'
                f'<div style="font-size:1rem;font-weight:700;color:{cor}">{nome}</div>'
                f'<div style="font-size:0.75rem;color:#aaa">{cat} · {dur} min</div>'
                f'<div style="font-size:1.6rem;font-weight:900;color:{cor};margin:6px 0">{val:,.1f}</div>'
                f'<div style="font-size:0.7rem;color:#888">{met_ex}</div>'
                f'</div>', unsafe_allow_html=True
            )

        card_ex(c1, top,      "🥇", "#f39c12")
        if segundo  is not None: card_ex(c2, segundo,  "🥈", "#95a5a6")
        if terceiro is not None: card_ex(c3, terceiro, "🥉", "#cd7f32")

        st.markdown("")

        # Gráfico ranking completo
        cores_ex = []
        max_v = df_ex_rank[met_ex].max()
        for v in df_ex_rank[met_ex]:
            pct = v / max_v if max_v > 0 else 0
            if pct >= 0.85:   cores_ex.append("#f39c12")
            elif pct >= 0.65: cores_ex.append("#e63946")
            else:             cores_ex.append("#457b9d")

        nomes = df_ex_rank["Exercício"].astype(str) if "Exercício" in df_ex_rank.columns else df_ex_rank.index.astype(str)
        fig_rank_ex = go.Figure(go.Bar(
            y=nomes, x=df_ex_rank[met_ex],
            orientation="h",
            marker_color=cores_ex,
            text=df_ex_rank[met_ex].round(1),
            textposition="outside",
        ))
        fig_rank_ex.add_vline(x=df_ex_rank[met_ex].mean(), line_dash="dash", line_color="white",
                               annotation_text=f"Média: {df_ex_rank[met_ex].mean():.1f}")
        fig_rank_ex.update_layout(
            height=max(300, len(df_ex_rank)*50),
            xaxis_title=met_ex, yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False, margin=dict(t=10),
        )
        st.plotly_chart(fig_rank_ex, use_container_width=True)

    st.divider()

    # ── Heatmap exercícios × métricas ─────────────────────────────────────────
    st.markdown('<p class="section-title">🗺️ Perfil de Exigência — Todos os Exercícios</p>', unsafe_allow_html=True)
    st.caption("Valores normalizados 0–100% (100% = exercício com valor máximo nessa métrica)")

    if "Exercício" in df_ex_f.columns and len(mets_ex_disp) >= 2:
        df_heat_ex = df_ex_f.groupby("Exercício")[mets_ex_disp].mean()
        # Normalizar 0–100 por coluna
        df_heat_norm = df_heat_ex.apply(
            lambda col: (col / col.max() * 100).round(0) if col.max() > 0 else col * 0, axis=0
        )
        labels_heat_ex = [m.replace(" (m)","").replace(" (n)","").replace(" (km/h)","").replace(" Ex.","") for m in mets_ex_disp]
        df_heat_norm.columns = labels_heat_ex

        fig_heat_ex = go.Figure(go.Heatmap(
            z=df_heat_norm.values,
            x=df_heat_norm.columns.tolist(),
            y=df_heat_norm.index.tolist(),
            text=df_heat_ex.round(1).values,
            texttemplate="%{text}",
            colorscale="YlOrRd",
            zmin=0, zmax=100,
            colorbar=dict(title="% do máx", ticksuffix="%"),
        ))
        fig_heat_ex.update_layout(
            height=max(280, len(df_heat_norm)*55),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", margin=dict(t=10),
            xaxis_title="Métrica GPS", yaxis_title="Exercício",
        )
        st.plotly_chart(fig_heat_ex, use_container_width=True)
        st.caption("Valores reais dentro de cada célula · Cor = % do máximo nessa métrica")

    st.divider()

    # ── Comparação por categoria ──────────────────────────────────────────────
    if "Categoria" in df_ex_f.columns and df_ex_f["Categoria"].notna().any():
        st.markdown('<p class="section-title">📊 Comparação por Categoria</p>', unsafe_allow_html=True)

        df_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean().reset_index()
        fig_cat = px.bar(
            df_cat.melt(id_vars="Categoria", value_vars=mets_ex_disp[:5]),
            x="variable", y="value", color="Categoria",
            barmode="group",
            labels={"variable": "Métrica", "value": "Média", "Categoria": "Categoria"},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_cat.update_layout(
            height=380, plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            margin=dict(t=10), legend_title="",
        )
        st.plotly_chart(fig_cat, use_container_width=True)

        # Radar por categoria
        st.markdown('<p class="section-title">📡 Radar de Perfil por Categoria</p>', unsafe_allow_html=True)
        if len(mets_ex_disp) >= 3:
            df_radar_cat = df_ex_f.groupby("Categoria")[mets_ex_disp].mean()
            # Normalizar
            df_radar_norm = df_radar_cat.apply(
                lambda col: col / col.max() * 100 if col.max() > 0 else col * 0, axis=0
            )
            labels_r = [m.replace(" (m)","").replace(" (n)","").replace(" Ex.","") for m in mets_ex_disp]
            fig_radar_cat = go.Figure()
            cores_r = px.colors.qualitative.Bold
            for i, (cat, row) in enumerate(df_radar_norm.iterrows()):
                vals = list(row.values) + [row.values[0]]
                labs = labels_r + [labels_r[0]]
                fig_radar_cat.add_trace(go.Scatterpolar(
                    r=vals, theta=labs, fill="toself",
                    name=cat, line_color=cores_r[i % len(cores_r)], opacity=0.75,
                ))
            fig_radar_cat.update_layout(
                polar=dict(radialaxis=dict(visible=True, ticksuffix="%", range=[0,100])),
                height=440, plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", font_color="white",
            )
            st.plotly_chart(fig_radar_cat, use_container_width=True)

    st.divider()

    # ── Evolução ao longo da sessão (ordem dos exercícios) ────────────────────
    if modo_ex == "📅 Por sessão (dia)" and "Exercício" in df_ex_f.columns:
        st.markdown('<p class="section-title">📈 Curva de Intensidade ao Longo da Sessão</p>', unsafe_allow_html=True)
        st.caption("Ordem dos exercícios tal como foram registados no Excel")

        met_ev_ex = st.selectbox("Métrica", mets_ex_disp, key="ex_ev_met")
        df_ev_ex = df_ex_f.reset_index(drop=True)
        df_ev_ex["Ordem"] = range(1, len(df_ev_ex)+1)
        df_ev_ex["Label"] = df_ev_ex["Exercício"].astype(str).str[:20]

        cores_ev = []
        max_ev = df_ev_ex[met_ev_ex].max() if df_ev_ex[met_ev_ex].notna().any() else 1
        for v in df_ev_ex[met_ev_ex]:
            pct = v / max_ev if max_ev > 0 and pd.notna(v) else 0
            if pct >= 0.85:   cores_ev.append("#f39c12")
            elif pct >= 0.65: cores_ev.append("#e63946")
            else:              cores_ev.append("#457b9d")

        fig_ev_ex = go.Figure()
        fig_ev_ex.add_trace(go.Bar(
            x=df_ev_ex["Label"], y=df_ev_ex[met_ev_ex],
            marker_color=cores_ev,
            text=df_ev_ex[met_ev_ex].round(1), textposition="outside",
            customdata=df_ev_ex[["Categoria","Duração (min)"]].values if "Categoria" in df_ev_ex.columns else None,
            hovertemplate="<b>%{x}</b><br>%{y:.1f}<br>%{customdata[0]} · %{customdata[1]} min<extra></extra>"
            if "Categoria" in df_ev_ex.columns else None,
        ))
        fig_ev_ex.add_hline(y=df_ev_ex[met_ev_ex].mean(), line_dash="dash", line_color="white",
                             annotation_text=f"Média: {df_ev_ex[met_ev_ex].mean():.1f}")
        fig_ev_ex.update_layout(
            height=360, yaxis_title=met_ev_ex,
            xaxis_title="Exercício (por ordem da sessão)",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="white", showlegend=False, margin=dict(t=10),
        )
        st.plotly_chart(fig_ev_ex, use_container_width=True)

    st.divider()

    # ── Tabela completa ───────────────────────────────────────────────────────
    with st.expander("📋 Ver todos os registos"):
        cols_show = ["Exercício","Categoria","Duração (min)","Nº Jogadores"] + mets_ex_disp
        cols_show = [c for c in cols_show if c in df_ex_f.columns]
        st.dataframe(
            df_ex_f[cols_show].sort_values(met_ex, ascending=False).reset_index(drop=True),
            use_container_width=True
        )

    # ── Exportar relatório ────────────────────────────────────────────────────
    st.divider()
    if not df_ex_rank.empty:
        cols_exp = ["Exercício","Categoria","Duração (min)"] + mets_ex_disp
        cols_exp = [c for c in cols_exp if c in df_ex_f.columns]
        headers_e = "".join(f"<th>{c}</th>" for c in cols_exp)
        linhas_e  = "".join(
            f'<tr>{"".join(f"<td>{round(row[c],1) if isinstance(row[c], float) else row[c]}</td>" for c in cols_exp)}</tr>'
            for _, row in df_ex_f[cols_exp].sort_values(met_ex, ascending=False).iterrows()
        )
        html_ex = gerar_pdf_html(f"""
<h1>Análise de Exercícios — {titulo_ctx}</h1>
<h2>🥇 Exercício mais exigente ({met_ex}): {str(top["Exercício"])}</h2>
<p>Valor: {top[met_ex]:,.1f} | Categoria: {top.get("Categoria","—")} | Duração: {top.get("Duração (min)","—")} min</p>
<h2>Ranking Completo</h2>
<table><tr>{headers_e}</tr>{linhas_e}</table>
""", f"Exercicios_{titulo_ctx.replace(' ','_')}.html")
        botao_download_html(html_ex, f"Exercicios_{titulo_ctx.replace(' ','_')}.html",
                            "📥 Exportar Relatório de Exercícios")



# ── Rodapé ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Dashboard de Monitorização de Carga · Belenenses · Gerado automaticamente a partir do ficheiro Excel · Para atualizar, clica em '🔄 Atualizar Dados' na barra lateral.")
