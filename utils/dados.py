"""LoadMonitorSystem — Carregamento e processamento de dados"""
import pandas as pd
import os
import io
import re

# ── Streamlit — importação tolerante ──────────────────────────────────────────
# Permite reutilizar este módulo a partir do FastAPI (api/), que não tem (nem
# precisa d)o Streamlit instalado. Quando o Streamlit não está disponível,
# cache_data() passa a ser um no-op — o FastAPI faz a sua própria gestão de
# cache/estado, ao contrário do Streamlit que precisa disto entre reruns.
try:
    import streamlit as st
    cache_data = st.cache_data
except ImportError:
    def cache_data(*dargs, **dkwargs):
        def _decorator(func):
            return func
        return _decorator

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


def _limpar(nome: str) -> str:
    """Reduz um nome de coluna ao essencial para comparação: minúsculas, sem
    espaços/underscores/parênteses/pontuação — só letras e números (mantém
    acentos). "Dia (MD)" e "dia_md" ficam ambos "diamd"."""
    return re.sub(r"[^\w]", "", nome.lower().strip(), flags=re.UNICODE).replace("_", "")


def normalizar_coluna(nome: str) -> str:
    """Normaliza nome de coluna usando aliases."""
    nome_lower = nome.lower().strip()
    nome_limpo = _limpar(nome)
    for standard, aliases in COL_ALIASES.items():
        if nome_lower == standard.lower(): return standard
        for a in aliases:
            a_lower = a.lower()
            if nome_lower == a_lower or nome_limpo == _limpar(a):
                return standard
    return nome


def _match_obrigatorio(col_name: str, aliases: list) -> bool:
    col_lower = col_name.lower().strip()
    col_limpo = _limpar(col_name)
    for a in aliases:
        a_lower = a.lower().strip()
        if col_lower == a_lower or col_limpo == _limpar(a):
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


def ler_raw(_path) -> pd.DataFrame:
    """Lê o ficheiro (CSV/Excel) e limpa apenas a estrutura de colunas —
    SEM renomear para nomes canónicos. É a base tanto do fluxo automático
    (`carregar_dados`) como do fluxo de importação robusta, onde o utilizador
    revê/ajusta o mapeamento de colunas antes de gravar."""
    extensao = _detectar_extensao(_path)
    df = _ler_csv_robusto(_path) if extensao == "csv" else _ler_excel_robusto(_path)
    df = df.loc[:, ~df.columns.str.match(r'^Unnamed')]
    df = df.dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def auto_mapa(colunas) -> dict:
    """Deteção automática de nomes canónicos para uma lista de colunas cruas.
    Devolve {coluna_crua: nome_canónico} apenas para as que reconhece. É a
    proposta que o fluxo de importação robusta apresenta ao utilizador."""
    mapa: dict[str, str] = {}
    usados: set[str] = set()
    # Métricas + colunas de identificação não-Data (via COL_ALIASES/normalizar).
    for col in colunas:
        canon = normalizar_coluna(col)
        if canon != col and canon not in usados and canon not in colunas:
            mapa[col] = canon
            usados.add(canon)
    # Obrigatórias (Jogador, Posição, Tipo, Dia MD) por aliases dedicados.
    for standard, aliases in COL_ALIASES_OBRIG.items():
        if standard == "Data" or standard in usados or standard in colunas:
            continue
        match = next((c for c in colunas if c not in mapa and _match_obrigatorio(c, aliases)), None)
        if match:
            mapa[match] = standard
            usados.add(standard)
    # Data (tratada à parte por ser convertida de forma especial).
    if "Data" not in usados and "Data" not in colunas:
        match = next((c for c in colunas if c not in mapa and _match_obrigatorio(c, COL_ALIASES_OBRIG["Data"])), None)
        if match:
            mapa[match] = "Data"
    return mapa


def _pos_processar(df: pd.DataFrame) -> pd.DataFrame:
    """Conversões de valores comuns aos dois fluxos: coluna Data (ou síntese
    por microciclo), coerção numérica, derivação de Carga Interna / Hooper e
    limpeza/normalização de nomes de jogador. Assume que os nomes de coluna
    já estão canónicos."""
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
    elif "Microciclo (Nr)" in df.columns and "Jogador" in df.columns:
        # Ficheiros sem data de calendário, só com número de semana/microciclo
        # (ex: "Semana" 1-16): sintetiza uma "Data" cujo único propósito é
        # preservar a ordem cronológica correta — o ACWR (calcular_acwr) usa
        # EWMA por posição na sequência de sessões, não por diferença real de
        # dias, por isso o valor calendárico em si não tem de ser real, só a
        # ordem (semana, depois posição da sessão dentro da semana/ficheiro).
        semana = pd.to_numeric(df["Microciclo (Nr)"], errors="coerce").fillna(1).astype(int)
        ordem_na_semana = df.groupby([df["Jogador"], semana]).cumcount()
        base = pd.Timestamp("2024-01-01")
        df["Data"] = base + pd.to_timedelta((semana - 1) * 7 + ordem_na_semana, unit="D")

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
        # Normaliza espaçamento e maiúsculas/minúsculas — "João Seco" e
        # "joão seco" não devem virar dois jogadores diferentes. Usa a
        # primeira grafia vista no ficheiro como forma "oficial" exibida.
        df["Jogador"] = df["Jogador"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        chave = df["Jogador"].str.lower()
        df["Jogador"] = df.groupby(chave)["Jogador"].transform("first")
    return df


@cache_data(ttl=300, show_spinner=False)
def carregar_dados(_path) -> pd.DataFrame:
    # NOTA: parâmetro com prefixo "_" para Streamlit IGNORAR hashing.
    # O Streamlit faz hash de BytesIO com .name como UploadedFile (os.stat),
    # o que falha no Cloud com [Errno 2]. Caching externo via session_state.
    df = ler_raw(_path)

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

    return _pos_processar(df)


def carregar_dados_com_mapa(_path, mapa: dict) -> pd.DataFrame:
    """Como `carregar_dados`, mas em vez da deteção automática usa um
    mapeamento explícito {coluna_crua: nome_canónico} escolhido/confirmado
    pelo utilizador. Colunas fora do mapa mantêm o nome cru (viram
    extra_metrics). É o motor do fluxo de importação robusta."""
    df = ler_raw(_path)
    # Só renomeia entradas válidas e sem colisões (a última a mapear para um
    # dado canónico ganha; as seguintes são ignoradas para não duplicar).
    rename: dict[str, str] = {}
    destinos: set[str] = set()
    for cru, canon in (mapa or {}).items():
        if not canon or cru not in df.columns or cru == canon:
            continue
        if canon in destinos or canon in df.columns:
            continue
        rename[cru] = canon
        destinos.add(canon)
    if rename:
        df = df.rename(columns=rename)
    return _pos_processar(df)


@cache_data(ttl=300, show_spinner=False)
def carregar_dados_safe(_path):
    """Carrega Excel/CSV com tratamento de erros amigável.
    Parâmetro com prefixo '_' para Streamlit ignorar hashing (evita os.stat
    do UploadedFile-like com .name no Cloud)."""
    try:
        df = carregar_dados(_path)
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


@cache_data(ttl=300, show_spinner=False)
def carregar_exercicios(_path) -> pd.DataFrame:
    """Carrega folha 'Exercícios' do Excel. CSV não suporta múltiplas folhas.
    Parâmetro com prefixo '_' para Streamlit ignorar hashing."""
    if _detectar_extensao(_path) == "csv":
        return pd.DataFrame()
    try:
        # BytesIO limpo se file-like
        if hasattr(_path, "read") and hasattr(_path, "seek"):
            try:
                _path.seek(0)
                bytes_data = _path.read()
                path_clean = io.BytesIO(bytes_data)
            except Exception:
                path_clean = _path
        else:
            path_clean = _path

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
