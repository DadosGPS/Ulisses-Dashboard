"""LoadMonitorSystem — Carregamento e processamento de dados"""
import pandas as pd
import streamlit as st

# ── Aliases de colunas GPS ────────────────────────────────────────────────────
COL_ALIASES = {
    "Distância Total (m)":  ["distance","dist","distancia","distância","total distance","distance total","dist total","dist. total","total dist","distance (m)","dist (m)","meters","metros"],
    "HSR (m)":              ["hsr","high speed running","high speed distance","hsd","alta velocidade","high intensity distance","hid","speed zone 4","zona 4","z4 dist"],
    "Sprint (m)":           ["sprint","sprint distance","sprinting","zona 5","z5","speed zone 5","max speed distance","sprint dist"],
    "Acc (n)":              ["acc","accelerations","aceleração","aceleracoes","acelerações","accel","accelerations count","n acc","num acc","ima acc","number of accelerations"],
    "Dcc (n)":              ["dcc","decel","decelerations","desaceleração","desaceleracoes","desacelerações","deceleration count","n dcc","ima dec"],
    "Vel. Máx (km/h)":      ["vmax","vel max","velocidade max","velocidade máxima","max speed","max velocity","peak speed","top speed","maximum speed","vmax (km/h)","speed max"],
    "PSE Sessão":           ["pse","rpe","perceived exertion","percepcao","perceção","sessão rpe","session rpe","rpe session"],
    "Duração (min)":        ["duracao","duração","duration","tempo","time","minutes","minutos","session duration","dur"],
    "Microciclo (Nr)":      ["microciclo","mc","week","semana","microcycle","gameweek","matchweek","gw"],
    "Carga Interna":        ["carga interna","internal load","session load","training load","load","tl","session tl"],
    "Hooper Index":         ["hooper","hooper index","hi","wellness score","wellness","bem estar","bem-estar"],
    "Sono (1-5)":           ["sono","sleep","sleep quality","qualidade sono"],
    "Dor Musc. (1-5)":      ["dor muscular","dor musc","muscle soreness","soreness","doms"],
    "Stress (1-5)":         ["stress","strain","tensao","tensão"],
    "Humor (1-5)":          ["humor","mood","estado humor","estado de humor"],
    "PlayerLoad":           ["playerload","player load","pl","player_load"],
    "Mechanical Power":     ["mechanical power","mec power","mech power","potencia mecanica","potência mecânica"],
    "Metabolic Power":      ["metabolic power","met power","potencia metabolica","potência metabólica","mp"],
    "Distância/min (m/min)":["dist/min","distance/min","relative distance","distância relativa","dist relativa","m/min","meters per minute"],
    "HSR%":                 ["hsr%","hsr percent","% hsr","high speed %","% alta velocidade"],
}

def normalizar_coluna(nome: str) -> str:
    """Normaliza nome de coluna usando aliases. Aceita variantes com espaços OU underscores
    (ex: 'high_speed_running' e 'high speed running' ambos → 'HSR (m)')."""
    nome_lower = nome.lower().strip()
    # Versão "limpa": sem espaços nem underscores (para comparar com aliases)
    nome_limpo = nome_lower.replace(" ", "").replace("_", "")
    for standard, aliases in COL_ALIASES.items():
        if nome_lower == standard.lower(): return standard
        for a in aliases:
            a_lower = a.lower()
            a_limpo = a_lower.replace(" ", "").replace("_", "")
            if nome_lower == a_lower or nome_limpo == a_limpo:
                return standard
    return nome

def get_mets_gps(df: pd.DataFrame) -> list:
    excluir = {"Jogador","Posição","Tipo","Dia MD","Data","Observações",
               "Microciclo (Nr)","Exercício","Categoria"}
    return [c for c in df.columns if c not in excluir
            and pd.api.types.is_numeric_dtype(df[c])
            and df[c].notna().any()]

@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados(path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="BD_Carga", header=None, engine="openpyxl")
    header_row = 0
    for i, row in raw.iterrows():
        row_vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip()]
        if any(v in ["jogador","player","atleta","athlete","name","nome"] for v in row_vals):
            header_row = i
            break
    df = pd.read_excel(path, sheet_name="BD_Carga", header=header_row, engine="openpyxl")
    df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    rename_map = {col: normalizar_coluna(col) for col in df.columns if normalizar_coluna(col) != col and normalizar_coluna(col) not in df.columns}
    if rename_map: df = df.rename(columns=rename_map)

    for standard, aliases in [
        ("Jogador", ["player","atleta","athlete","name","nome"]),
        ("Posição",  ["position","pos","posicion"]),
        ("Tipo",     ["type","session type","sessao"]),
        ("Dia MD",   ["matchday","match day","dia jogo","game day"]),
    ]:
        if standard not in df.columns:
            match = next((c for c in df.columns if c.lower().strip() in aliases), None)
            if match: df = df.rename(columns={match: standard})

    col_data = next((c for c in df.columns if c.lower().strip() in ["data","date","fecha"]), None)
    if col_data:
        if col_data != "Data": df = df.rename(columns={col_data: "Data"})
        def conv(v):
            if pd.isna(v): return pd.NaT
            try: return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
            except: return pd.to_datetime(v, errors="coerce")
        df["Data"] = df["Data"].apply(conv)

    TEXTO = {"Jogador","Posição","Tipo","Dia MD","Observações","Exercício","Categoria","Data","Hora","Clube"}
    for col in list(df.columns):
        if col in TEXTO: continue
        serie = df[col]
        if isinstance(serie, pd.DataFrame): serie = serie.iloc[:, 0]; df = df.drop(columns=[col]); df[col] = serie
        df[col] = pd.to_numeric(serie, errors="coerce")

    if "Carga Interna" not in df.columns:
        col_pse = next((c for c in df.columns if "pse" in c.lower() or "rpe" in c.lower()), None)
        col_dur = next((c for c in df.columns if "dura" in c.lower() or "duration" in c.lower() or c.lower() in ["min","minutes","minutos"]), None)
        if col_pse and col_dur:
            df["Carga Interna"] = pd.to_numeric(df[col_pse], errors="coerce") * pd.to_numeric(df[col_dur], errors="coerce")

    if "Hooper Index" not in df.columns:
        keywords = ["sono","sleep","dor musc","soreness","stress","humor","mood","fadiga"]
        cols_h = [c for c in df.columns if any(k in c.lower() for k in keywords) and pd.api.types.is_numeric_dtype(df[c])]
        if len(cols_h) >= 3:
            acc = pd.Series(0.0, index=df.index)
            for c in cols_h[:4]: acc = acc + (5 - pd.to_numeric(df[c], errors="coerce").fillna(0))
            df["Hooper Index"] = acc

    df = df.dropna(how="all")
    if "Jogador" in df.columns:
        df = df[df["Jogador"].notna() & (df["Jogador"].astype(str).str.strip() != "")]
    return df

@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados_safe(path):
    """Carrega Excel com tratamento de erros amigável para o utilizador."""
    try:
        df = carregar_dados(path)
        if df is None or df.empty:
            return None, "O ficheiro Excel parece estar vazio ou não contém dados na folha BD_Carga."
        return df, None
    except FileNotFoundError:
        return None, "Ficheiro Excel não encontrado. Verifica que carregaste o ficheiro correctamente."
    except Exception as e:
        msg_tecnica = str(e)
        # Traduzir erros técnicos comuns em mensagens amigáveis
        if "Worksheet named" in msg_tecnica or "BD_Carga" in msg_tecnica:
            return None, "O Excel não tem a folha 'BD_Carga'. Usa o template oficial ou renomeia a tua folha para 'BD_Carga'."
        if "str accessor" in msg_tecnica or "string values" in msg_tecnica:
            return None, "O Excel parece estar vazio ou tem formato inválido. Verifica que tem dados na folha BD_Carga."
        if "openpyxl" in msg_tecnica.lower() or "xlrd" in msg_tecnica.lower():
            return None, "Formato de ficheiro não suportado. Usa Excel (.xlsx) — não .xls antigo nem outros formatos."
        # Erro genérico — esconder detalhes técnicos
        return None, f"Não foi possível ler o ficheiro Excel. Verifica que segue o formato esperado (folha BD_Carga com colunas standard)."

@st.cache_data(ttl=300, show_spinner=False)
def carregar_exercicios(path) -> pd.DataFrame:
    try:
        raw = pd.read_excel(path, sheet_name="Exercícios", header=None, engine="openpyxl")
        header_row = 2
        for i, row in raw.iterrows():
            vals = [str(v).strip().lower() for v in row.values if v is not None]
            if any(v in ["data","nome do exercicio","nome","exercicio"] for v in vals):
                header_row = i; break
        df_ex = pd.read_excel(path, sheet_name="Exercícios", header=header_row, engine="openpyxl")
        df_ex.columns = [str(c).strip().replace(chr(10)," ") for c in df_ex.columns]
        rename = {}
        for col in df_ex.columns:
            cl = col.lower()
            if "data" in cl: rename[col] = "Data"
            elif "microciclo" in cl: rename[col] = "Microciclo (Nr)"
            elif "dia" in cl and "md" in cl: rename[col] = "Dia MD"
            elif ("nome" in cl or "exerc" in cl) and "categ" not in cl: rename[col] = "Exercício"
            elif "categ" in cl: rename[col] = "Categoria"
            elif "duração" in cl or "duracao" in cl: rename[col] = "Duração (min)"
            elif "jogadores" in cl or "nº" in cl: rename[col] = "Nº Jogadores"
            elif "distância" in cl or "distancia" in cl: rename[col] = "Distância Total (m)"
            elif "hsr" in cl: rename[col] = "HSR (m)"
            elif "sprint" in cl: rename[col] = "Sprint (m)"
            elif "acc" in cl and "dcc" not in cl: rename[col] = "Acc (n)"
            elif "dcc" in cl: rename[col] = "Dcc (n)"
            elif "vel" in cl or "vmax" in cl: rename[col] = "Vel. Máx (km/h)"
            elif "pse" in cl: rename[col] = "PSE Exercício"
        df_ex = df_ex.rename(columns=rename)
        if "Data" in df_ex.columns:
            def conv(v):
                if pd.isna(v): return pd.NaT
                try: return pd.Timestamp("1899-12-30") + pd.Timedelta(days=float(v))
                except: return pd.to_datetime(v, errors="coerce")
            df_ex["Data"] = df_ex["Data"].apply(conv)
        df_ex = df_ex.dropna(how="all")
        if "Exercício" in df_ex.columns: df_ex = df_ex[df_ex["Exercício"].notna()]
        for col in ["Microciclo (Nr)","Duração (min)","Nº Jogadores","Distância Total (m)","HSR (m)","Sprint (m)","Acc (n)","Dcc (n)","Vel. Máx (km/h)","PSE Exercício"]:
            if col in df_ex.columns: df_ex[col] = pd.to_numeric(df_ex[col], errors="coerce")
        return df_ex
    except Exception:
        return pd.DataFrame()
