import streamlit as st
import pandas as pd

"""
Streamlit dashboard para analizar el CSV de voluntarios de los Juegos Centroamericanos y del Caribe
Santo Domingo 2026. Muestra métricas de país de residencia, nacionalidad y etiquetas, con gráficas
interactivas.
"""

st.set_page_config(
    page_title="Voluntarios JCC 2026 – Análisis",
    layout="wide",
    page_icon="📊",
)

@st.cache_data(show_spinner="Cargando datos…")
def load_data(path: str) -> pd.DataFrame:
    """Carga CSV y lo mantiene en caché (Streamlit ≥1.24)."""
    return pd.read_csv(path)

# ────────────────────────────────────────────────
# Sidebar – entrada de usuario
# ────────────────────────────────────────────────
path = st.sidebar.text_input(
    "📄 Ruta al archivo CSV",
    "subscribed_email_audience_export_52bda5c35c.csv",
    help="Coloca el CSV en la misma carpeta o pega la ruta absoluta",
)

show_raw = st.sidebar.checkbox("Mostrar tabla original", value=False)

# ────────────────────────────────────────────────
# Carga de datos
# ────────────────────────────────────────────────
df = load_data(path)

if show_raw:
    st.subheader("Vista previa del CSV completo")
    st.dataframe(df.head(50))

# ────────────────────────────────────────────────
# Métricas generales
# ────────────────────────────────────────────────
st.title("Análisis de Voluntarios – JCC 2026")

total_volunteers = len(df)
unique_countries = df["Country Of Residence"].nunique(dropna=True)
unique_nationalities = df["Nationality"].nunique(dropna=True)

m1, m2, m3 = st.columns(3)

m1.metric("Voluntarios totales", f"{total_volunteers:,}")
m2.metric("Países representados", unique_countries)
m3.metric("Nacionalidades distintas", unique_nationalities)

st.divider()

# ────────────────────────────────────────────────
# País de residencia
# ────────────────────────────────────────────────
st.header("Distribución por País de Residencia")
country_counts = (
    df["Country Of Residence"].dropna()
    .value_counts()
    .sort_values(ascending=False)
)

max_slider = min(len(country_counts), 30)
top_n_countries = st.sidebar.slider(
    "Top N países", 5, max_slider, 10, key="slider_country"
)

st.bar_chart(country_counts.head(top_n_countries))

with st.expander("Ver tabla completa de países"):
    st.dataframe(
        country_counts.reset_index().rename(
            columns={"index": "País", "Country Of Residence": "Voluntarios"}
        )
    )

st.divider()

# ────────────────────────────────────────────────
# Nacionalidad
# ────────────────────────────────────────────────
st.header("Distribución por Nacionalidad")
nationality_counts = (
    df["Nationality"].dropna()
    .value_counts()
    .sort_values(ascending=False)
)

max_slider_nat = min(len(nationality_counts), 30)
top_n_nat = st.sidebar.slider(
    "Top N nacionalidades", 5, max_slider_nat, 10, key="slider_nat"
)

st.bar_chart(nationality_counts.head(top_n_nat))

with st.expander("Ver tabla completa de nacionalidades"):
    st.dataframe(
        nationality_counts.reset_index().rename(
            columns={"index": "Nacionalidad", "Nationality": "Voluntarios"}
        )
    )

st.divider()

# ────────────────────────────────────────────────
# Cruce País × Nacionalidad (heatmap simplificado)
# ────────────────────────────────────────────────
st.header("Cruce País de Residencia × Nacionalidad (tabla)")
crosstab = pd.crosstab(df["Country Of Residence"], df["Nationality"])

if crosstab.empty:
    st.info("No hay suficientes datos para generar la tabla cruzada.")
else:
    st.dataframe(crosstab)

st.divider()

# ────────────────────────────────────────────────
# Análisis de etiquetas
# ────────────────────────────────────────────────
if "TAGS" in df.columns and df["TAGS"].notna().any():
    st.header("Etiquetas (TAGS) más frecuentes")
    tags_series = (
        df["TAGS"]
        .dropna()
        .str.replace("\"", "", regex=False)
        .str.split(",")
        .explode()
        .str.strip()
    )
    tag_counts = tags_series.value_counts().sort_values(ascending=False)

    st.bar_chart(tag_counts)
    with st.expander("Ver tabla de etiquetas"):
        st.dataframe(tag_counts.reset_index().rename(columns={"index": "Etiqueta", 0: "Voluntarios"}))
