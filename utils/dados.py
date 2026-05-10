"""LoadMonitorSystem — Carregamento e processamento de dados"""
import pandas as pd
import streamlit as st
import os
import io

# ── Aliases de colunas GPS ────────────────────────────────────────────────────
COL_ALIASES = {
    "Distância Total (m)":  [
        "distance","dist","distancia","distância","total distance","distance total",
        "dist total","dist. total","total dist","distance (m)","dist (m)","meters","metros",
        "distancia total","distância total","distancia_total","total_distance",
        "distancia (m)","distancia recorrida","total recorrido",
    ],
    "HSR (m)":              [
        "hsr","high speed running","high speed distance","hsd","alta velocidade",
        "high intensity distance","hid","speed zone 4","zona 4","z4 dist",
        "alta intensidad","distancia alta velocidad","carrera alta velocidad",
        "high speed run","high_speed_running","high_speed_distance",
    ],
    "Sprint (m)":           [
        "sprint","sprint distance","sprinting","zona 5","z5","speed zone 5",
        "max speed distance","sprint dist",
        "esprint","distancia sprint","sprint_distance",
    ],
    "Acc (n)":              [
        "acc","accelerations","aceleração","aceleracoes","acelerações","accel",
        "accelerations count","n acc","num acc","ima acc","number of accelerations",
        "aceleraciones","aceleracion","aceleración","numero aceleraciones",
        "n aceleraciones","accel count","accelerations_count",
    ],
    "Dcc (n)":              [
        "dcc","decel","decelerations","desaceleração","desaceleracoes","desacelerações",
        "deceleration count","n dcc","ima dec",
        "desaceleraciones","desaceleracion","desaceleración","numero desaceleraciones",
        "n desaceleraciones","decel count","decelerations_count",
    ],
    "Vel. Máx (km/h)":      [
        "vmax","vel max","velocidade max","velocidade máxima","max speed","max velocity",
        "peak speed","top speed","maximum speed","vmax (km/h)","speed max",
        "velocidad maxima","velocidad máxima","vel maxima","vel máxima",
        "max_speed","peak_speed","velocidad max",
    ],
    "PSE Sessão":           [
        "pse","rpe","perceived exertion","percepcao","perceção","sessão rpe",
        "session rpe","rpe session",
        "pse sesion","rpe sesion","esfuerzo percibido","percepcion esfuerzo",
        "session_rpe","rpe_session",
    ],
    "Duração (min)":        [
        "duracao","duração","duration","tempo","time","minutes","minutos",
        "session duration","dur",
        "duracion","duración","tiempo","tiempo sesion","duracion sesion",
        "session_duration",
    ],
    "Microciclo (Nr)":      [
        "microciclo","mc","week","semana","microcycle","gameweek","matchweek","gw",
        "microciclo nr","microciclo_nr","semana entrenamiento","training week",
    ],
    "Carga Interna":        [
        "carga interna","internal load","session load","training load","load","tl","session tl",
        "carga","carga entrenamiento","carga sesion","internal_load","training_load",
    ],
    "Hooper Index":         [
        "hooper","hooper index","hi","wellness score","wellness","bem estar","bem-estar",
        "indice hooper","índice hooper","bienestar","puntuacion bienestar",
        "wellness_score","hooper_index",
    ],
    "Sono (1-5)":           [
        "sono","sleep","sleep quality","qualidade sono",
        "sueño","sueno","calidad sueño","calidad sueno","horas sueño","sleep_quality",
    ],
    "Dor Musc. (1-5)":      [
        "dor muscular","dor musc","muscle soreness","soreness","doms",
        "dolor muscular","dolor musc","dolor","dolor musculos","muscle_soreness",
    ],
    "Stress (1-5)":         [
        "stress","strain","tensao","tensão",
        "estres","estrés","tension","tensión","nivel estres","nivel estrés",
    ],
    "Humor (1-5)":          [
        "humor","mood","estado humor","estado de humor",
        "estado animo","estado ánimo","ánimo","animo",
    ],
    "PlayerLoad":           [
        "playerload","player load","pl","player_load",
        "carga jugador","carga del jugador",
    ],
    "Mechanical Power":     [
        "mechanical power","mec power","mech power","potencia mecanica","potência mecânica",
        "potencia mec","mech_power","mechanical_power","mecanical power",
    ],
    "Metabolic Power":      [
        "metabolic power","met power","potencia metabolica","potência metabólica","mp",
        "potencia met","metabolic_power","met_power",
    ],
    "Distância/min (m/min)":[
        "dist/min","distance/min","relative distance","distância relativa",
        "dist relativa","m/min","meters per minute",
        "distancia relativa","distancia/min","metros por minuto",
    ],
    "HSR%":                 [
        "hsr%","hsr percent","% hsr","high speed %","% alta velocidade",
        "% alta intensidad","porcentaje hsr",
    ],
}

# ── Aliases para colunas de contexto/identificação ────────────────────────────
COL_ALIASES_OBRIG = {
    "Jogador":   [
        "player","atleta","athlete","name","nome",
        "jugador","nombre","nombre jugador",
    ],
    "Posição":   [
        "position","pos","posicion",
        "posición","posicao","puesto",
    ],
    "Tipo":      [
        "type","session type","sessao","sessão",
        "tipo sesion","tipo sesión","tipo de sesion","tipo de sesión",
        "session_type","tipo_sesion","tipo_sesao","tipo entrenamiento",
    ],
    "Dia MD":    [
        "matchday","match day","dia jogo","game day",
        "dia md","dia_md","matchday","match_day","dia partido","dia_partido",
        "match-day","md day",
    ],
    "Data":      [
        "data","date","fecha",
        "fecha sesion","fecha sesión","fecha entrenamiento","data sessao",
        "session_date","fecha_sesion",
    ],
}


def normalizar_coluna(nome: str) -> str:
    """Normaliza nome de coluna usando aliases."""
    nome_lower = nome.lower().strip()
    nome_limpo = nome_lower.replace(" ", "").replace("_", "")
    for standard, aliases in COL_ALIASES.items():
        if nome_lower == standard.lower(): return standard
        for a in aliases:
            a_lower = a.lower()
            a_limpo = a_lower.replace(" ", "").replace("_", "")
            if nome_lower == a_lower or nome_limpo == a_limpo:
                return standard
    return nome


def _match_obrigatorio(col_name: str, aliases: list) -> bool:
    col_lower = col_name.lower().strip()
    col_limpo = col_lower.replace(" ", "").replace("_", "")
    for a in aliases:
        a_lower = a.lower().strip()
        a_limpo = a_lower.replace(" ", "").replace("_", "")
        if col_lower == a_lower or col_limpo == a_limpo:
            return True
    return False


def get_mets_gps(df: pd.DataFrame) -> list:
    excluir = {"Jogador","Posição","Tipo","Dia MD","Data","Observações",
               "Microciclo (Nr)","Exercício","Categoria"}
    return [c for c in df.columns if c not in excluir
            and pd.api.types.is_numeric_dtype(df[c])
            and df[c].notna().any()]


def _detectar_extensao(path) -> str:
    """Devolve 'csv' ou 'xlsx' baseado na extensão do path."""
    if hasattr(path, "name"):
        nome = str(path.name).lower()
    elif isinstance(path, str):
        nome = path.lower()
    else:
        return "xlsx"
    if nome.endswith(".csv"):
        return "csv"
    return "xlsx"


def _ler_csv_robusto(path) -> pd.DataFrame:
    """Lê CSV detectando automaticamente separador e encoding.
    IMPORTANTE: cria um BytesIO LIMPO (sem .name) para evitar que pandas/Streamlit
    interpretem o .name como caminho de disco e tentem abrir um ficheiro inexistente.
    """
    # Extrair os bytes do input (path pode ser BytesIO, file path, ou file-like)
    if hasattr(path, "read") and hasattr(path, "seek"):
        # É file-like (BytesIO ou similar)
        try:
            path.seek(0)
            bytes_data = path.read()
        except Exception as e:
            raise ValueError(f"Não foi possível ler bytes do CSV: {e}")
    elif isinstance(path, str) and os.path.isfile(path):
        # É um caminho de ficheiro real no disco
        with open(path, "rb") as f:
            bytes_data = f.read()
    else:
        raise ValueError("Formato de input inválido para CSV.")

    # Tentar combinações: separador (auto, ;, \t, ,) + encoding (utf-8, latin-1, cp1252)
    erros = []
    for sep in [None, ";", "\t", ","]:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                # Criar um BytesIO LIMPO a cada tentativa (sem .name)
                buffer = io.BytesIO(bytes_data)
                if sep is None:
                    df = pd.read_csv(buffer, sep=None, engine="python", encoding=enc)
                else:
                    df = pd.read_csv(buffer, sep=sep, encoding=enc)
                # Validação mínima
                if len(df.columns) >= 2 and len(df) >= 1:
                    return df
            except Exception as e:
                erros.append(f"sep={sep}, enc={enc}: {str(e)[:60]}")
                continue
    raise ValueError(f"Não foi possível ler o CSV. Tentativas: {erros[:3]}")


def _ler_excel_robusto(path):
    """Lê Excel da folha BD_Carga. Usa BytesIO limpo se path for file-like,
    para evitar problemas de cache do Streamlit com .name."""
    # Se path é file-like, criar BytesIO limpo
    if hasattr(path, "read") and hasattr(path, "seek"):
        try:
            path.seek(0)
            bytes_data = path.read()
            path_clean = io.BytesIO(bytes_data)
        except Exception:
            path_clean = path
    else:
        path_clean = path

    raw = pd.read_excel(path_clean, sheet_name="BD_Carga", header=None, engine="openpyxl")
    header_row = 0
    cabecalhos_jog = ["jogador","player","atleta","athlete","name","nome","jugador"]
    for i, row in raw.iterrows():
        row_vals = [str(v).strip().lower() for v in row.values if pd.notna(v) and str(v).strip()]
        if any(v in cabecalhos_jog for v in row_vals):
            header_row = i
            break

    # Recriar BytesIO limpo para a segunda leitura
    if hasattr(path, "read") and hasattr(path, "seek"):
        path_clean = io.BytesIO(bytes_data)
    df = pd.read_excel(path_clean, sheet_name="BD_Carga", header=header_row, engine="openpyxl")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def carregar_dados(path) -> pd.DataFrame:
    extensao = _detectar_extensao(path)

    if extensao == "csv":
        df = _ler_csv_robusto(path)
        df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
        df = df.dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]
    else:
        df = _ler_excel_robusto(path)
        df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
        df = df.dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.duplicated()]

    # Renomear métricas via COL_ALIASES
    rename_map = {col: normalizar_coluna(col) for col in df.columns
                  if normalizar_coluna(col) != col and normalizar_coluna(col) not in df.columns}
    if rename_map: df = df.rename(columns=rename_map)

    # Renomear obrigatórias
    for standard, aliases in COL_ALIASES_OBRIG.items():
        if standard == "Data":
            continue
        if standard not in df.columns:
            match = next((c for c in df.columns if _match_obrigatorio(c, aliases)), None)
            if match: df = df.rename(columns={match: standard})

    # Coluna Data
    col_data = next((c for c in df.columns
                     if _match_obrigatorio(c, COL_ALIASES_OBRIG["Data"])), None)
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
        col_dur = next((c for c in df.columns if "dura" in c.lower() or "duration" in c.lower() or "tiempo" in c.lower() or c.lower() in ["min","minutes","minutos"]), None)
        if col_pse and col_dur:
            df["Carga Interna"] = pd.to_numeric(df[col_pse], errors="coerce") * pd.to_numeric(df[col_dur], errors="coerce")

    if "Hooper Index" not in df.columns:
        keywords = ["sono","sleep","sueño","sueno","dor musc","soreness","dolor muscular",
                    "stress","estres","estrés","humor","mood","animo","ánimo","fadiga"]
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
    """Carrega Excel/CSV com tratamento de erros amigável."""
    try:
        df = carregar_dados(path)
        if df is None or df.empty:
            return None, "O ficheiro parece estar vazio ou não contém dados válidos."
        return df, None
    except FileNotFoundError as e:
        return None, f"Ficheiro não encontrado: {e}"
    except Exception as e:
        msg_tecnica = str(e)
        if "Worksheet named" in msg_tecnica or "BD_Carga" in msg_tecnica:
            return None, "O Excel não tem a folha 'BD_Carga'. Usa o template oficial ou renomeia a tua folha para 'BD_Carga'."
        if "str accessor" in msg_tecnica or "string values" in msg_tecnica:
            return None, "O ficheiro parece estar vazio ou tem formato inválido. Verifica que tem dados."
        if "openpyxl" in msg_tecnica.lower() or "xlrd" in msg_tecnica.lower():
            return None, "Formato de ficheiro não suportado. Usa Excel (.xlsx) ou CSV (.csv)."
        if "Não foi possível ler o CSV" in msg_tecnica:
            return None, "Não foi possível ler o CSV. Verifica o formato (separador , ou ;) e codificação (UTF-8)."
        return None, "Não foi possível ler o ficheiro. Verifica que segue o formato esperado."


@st.cache_data(ttl=300, show_spinner=False)
def carregar_exercicios(path) -> pd.DataFrame:
    """Carrega folha 'Exercícios' do Excel. CSV não suporta múltiplas folhas."""
    if _detectar_extensao(path) == "csv":
        return pd.DataFrame()
    try:
        # BytesIO limpo se file-like
        if hasattr(path, "read") and hasattr(path, "seek"):
            try:
                path.seek(0)
                bytes_data = path.read()
                path_clean = io.BytesIO(bytes_data)
            except Exception:
                path_clean = path
        else:
            path_clean = path

        raw = pd.read_excel(path_clean, sheet_name="Exercícios", header=None, engine="openpyxl")
        header_row = 2
        for i, row in raw.iterrows():
            vals = [str(v).strip().lower() for v in row.values if v is not None]
            if any(v in ["data","nome do exercicio","nome","exercicio"] for v in vals):
                header_row = i; break

        if hasattr(path, "read") and hasattr(path, "seek"):
            path_clean = io.BytesIO(bytes_data)
        df_ex = pd.read_excel(path_clean, sheet_name="Exercícios", header=header_row, engine="openpyxl")
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
