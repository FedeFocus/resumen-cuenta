import streamlit as st
import pandas as pd

# Cargar el archivo Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")
st.write("Lista de activos cargados desde Excel:")

# Mostrar la tabla
st.dataframe(df)

# Filtros opcionales
activos = df['Nombre del activo'].unique()
activo_seleccionado = st.selectbox("Seleccionar activo", opciones := ["Todos"] + list(activos))

if activo_seleccionado != "Todos":
    st.subheader(f"Detalle del activo: {activo_seleccionado}")
    st.dataframe(df[df['Nombre del activo'] == activo_seleccionado])
