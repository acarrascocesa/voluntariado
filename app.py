import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import unicodedata

# ---------------------------------------------------------------------------
# Intenta usar Plotly para visualizaciones más ricas. Si no existe, avisa.
# ---------------------------------------------------------------------------
try:
    import plotly.express as px

    PLOTLY = True
except ModuleNotFoundError:
    PLOTLY = False

###############################################################################
# Configuración inicial
###############################################################################

st.set_page_config(
    page_title="Dashboard Voluntarios – JCC 2026",
    page_icon="logo.png",
    layout="wide",
)

st.title("🏟️ Voluntarios Juegos Centroamericanos y del Caribe 2026")

###############################################################################
# Cargar datos (WPForms)
###############################################################################

FILE = "wpforms-45824-Formulario-de-Voluntarios-2025-07-30-15-07-05.csv"


@st.cache_data(show_spinner="Cargando datos…")
def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        st.error(
            f"No se encontró el archivo {path}. Colócalo en el mismo directorio y reinicia."
        )
        st.stop()
    return pd.read_csv(path)


df = load_data(FILE)

###############################################################################
# Normalización de texto para país y nacionalidad
###############################################################################


def normalize_text(col: pd.Series) -> pd.Series:
    # 1) Rellenar NaN y pasar a str
    s = col.fillna("Sin dato").astype(str)
    # 2) Quitar espacios al inicio/fin
    s = s.str.strip()
    # 3) Pasar todo a minúsculas
    s = s.str.lower()
    # 4) Descomponer unicode y eliminar tildes
    s = (
        s.apply(lambda x: unicodedata.normalize("NFKD", x))
        .str.encode("ascii", errors="ignore")
        .str.decode("utf-8")
    )
    # 5) Capitalizar cada palabra (opcional)
    s = s.str.title()
    return s


# ---------------------------------------------------------------------------
# Helper: localizar columnas clave (case‑insensitive)
# ---------------------------------------------------------------------------


def find_col(substrings):
    for col in df.columns:
        low = col.lower()
        if all(s in low for s in substrings):
            return col
    return None


col_country = find_col(["país", "residencia"]) or find_col(["pais", "residencia"])
col_nat = find_col(["nacionalidad"])
col_dob = find_col(["fecha", "nacimiento"])
col_gender = find_col(["sexo"])
col_shirt = find_col(["talla", "camisa"])
col_avail = find_col(["disponibilidad", "horario"])
col_insurance = find_col(["seguro"])

# Aplica normalización a país y nacionalidad
if col_country:
    df[col_country] = normalize_text(df[col_country])
if col_nat:
    df[col_nat] = normalize_text(df[col_nat])

# (Opcional) Restaurar tildes en casos puntuales
mapping = {
    "Republica Dominicana": "República Dominicana",
    # añade más correcciones si es necesario
}

# ————————————————————————————————————————————————
# Unificar género en nacionalidad (Dominicana → Dominicano, Mexicana → Mexicano, etc.)
# ————————————————————————————————————————————————
if col_nat:
    # Lista de valores únicos tras normalizar y mapear tildes
    nat_vals = df[col_nat].unique()
    gender_map = {}
    for val in nat_vals:
        # solo cadenas no vacías
        if not val or not isinstance(val, str):
            continue
        # busca ´Terminadas en "a"´ que tengan contraparte en "o"
        if val.endswith("a"):
            masc = val[:-1] + "o"
            if masc in nat_vals:
                gender_map[val] = masc

    # Aplica el reemplazo
    df[col_nat] = df[col_nat].replace(gender_map)

if col_country:
    df[col_country] = df[col_country].replace(mapping)
if col_nat:
    df[col_nat] = df[col_nat].replace(mapping)

###############################################################################
# KPIs principales
###############################################################################

total_vol = len(df)
unique_countries = df[col_country].nunique() if col_country else 0
unique_national = df[col_nat].nunique() if col_nat else 0

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric("Voluntarios", f"{total_vol:,}")
with kpi2:
    st.metric("Países de residencia", unique_countries)
with kpi3:
    st.metric("Nacionalidades", unique_national)

###############################################################################
# Distribución por país (mapa + barras)
###############################################################################

if col_country and PLOTLY:
    st.subheader("Distribución por país de residencia")
    country_counts = df[col_country].value_counts().reset_index()
    country_counts.columns = ["Country", "Volunteers"]

    fig_map = px.choropleth(
        country_counts,
        locations="Country",
        locationmode="country names",
        color="Volunteers",
        color_continuous_scale="Blues",
        height=500,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    top_n = st.slider(
        "Mostrar Top N países",
        3,
        min(30, len(country_counts)),
        10,
        key="slider_country",
    )
    st.bar_chart(country_counts.set_index("Country").head(top_n))
elif col_country:
    st.subheader("País de residencia – Top 10")
    st.bar_chart(df[col_country].value_counts().head(10))

###############################################################################
# Distribución por nacionalidad
###############################################################################

if col_nat:
    st.subheader("Distribución por nacionalidad (Top 20)")
    nat_counts = df[col_nat].value_counts().head(20)
    st.bar_chart(nat_counts)

###############################################################################
# Sexo y rango de edad
###############################################################################

if col_dob:
    today = datetime(2025, 7, 21)
    dob = pd.to_datetime(df[col_dob], errors="coerce", dayfirst=True)
    age = dob.apply(
        lambda d: (
            today.year - d.year - ((today.month, today.day) < (d.month, d.day))
            if pd.notnull(d)
            else np.nan
        )
    )
    df["Age"] = age

    bins = [15, 18, 25, 35, 50, 100]
    labels = ["15‑18", "18‑25", "25‑35", "35‑50", "50+"]
    df["AgeGroup"] = pd.cut(df["Age"], bins=bins, labels=labels, right=False)

    st.subheader("Sexo por rango de edad")
    if col_gender:
        gender_age = (
            df.groupby(["AgeGroup", col_gender], observed=True)
            .size()
            .unstack(fill_value=0)
        )
        st.area_chart(gender_age)
    else:
        age_counts = df["AgeGroup"].value_counts().sort_index()
        st.bar_chart(age_counts)

###############################################################################
# Tallas de camiseta
###############################################################################

if col_shirt:
    st.subheader("Tallas de camiseta")
    shirt_counts = (
        df[col_shirt]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace({"NAN": "Sin dato", "": "Sin dato"})
        .value_counts()
    )
    st.bar_chart(shirt_counts)

###############################################################################
# Disponibilidad horaria – limpiando valores undefined
###############################################################################

if col_avail:
    st.subheader("Disponibilidad horaria declarada")

    clean_avail = (
        df[col_avail]
        .fillna("Sin dato")
        .astype(str)
        .str.strip()
        .replace(
            {
                "undefinido": "Sin dato",
                "undefined": "Sin dato",
                "nan": "Sin dato",
                "": "Sin dato",
            }
        )
    )

    avail_df = clean_avail.value_counts().reset_index()
    avail_df.columns = ["Horario", "Voluntarios"]

    if PLOTLY:
        fig_avail = px.bar(
            avail_df,
            x="Horario",
            y="Voluntarios",
            text="Voluntarios",
            height=400,
        )
        fig_avail.update_layout(xaxis_title="", yaxis_title="Voluntarios")
        st.plotly_chart(fig_avail, use_container_width=True)
    else:
        st.bar_chart(avail_df.set_index("Horario"))

###############################################################################
# Seguro médico
###############################################################################

if col_insurance:
    st.subheader("Cobertura de seguro médico")
    ins_counts = (
        df[col_insurance]
        .fillna("Sin dato")
        .astype(str)
        .str.strip()
        .replace({"": "Sin dato", "nan": "Sin dato"})
        .value_counts()
    )
    st.bar_chart(ins_counts)

###############################################################################
# Correos duplicados (sanity check)
###############################################################################
email_col = find_col(["correo", "electrónico"]) or find_col(["email"])
if email_col:
    # Normalize y quita NaN/espacios
    emails = df[email_col].fillna("").astype(str).str.strip()
    # Mascara de no-vacíos
    non_blank = emails != ""
    # Mascara de duplicados entre los no-vacíos
    dupe_mask = emails.duplicated(keep=False) & non_blank
    dupes = df[dupe_mask]

    if not dupes.empty:
        st.subheader("Correos duplicados (válidos)")
        st.write(f"Se encontraron {len(dupes)} registros duplicados con correo válido.")
        st.dataframe(dupes[[email_col]].drop_duplicates())


###############################################################################
# Footer
###############################################################################

st.caption("© 2025 Comité Organizador JCC 2026 · Dashboard generado con Streamlit")
