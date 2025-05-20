import streamlit as st
import pandas as pd

# Cargar el archivo Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")
st.write("Lista de activos cargados desde Excel:")

# Mostrar la tabla completa
st.dataframe(df)

# Filtros opcionales
activos = df['Activo'].unique()
activo_seleccionado = st.selectbox("Seleccionar activo", opciones := ["Todos"] + list(activos))

if activo_seleccionado != "Todos":
    st.subheader(f"Detalle del activo: {activo_seleccionado}")
    df_filtrado = df[df['Activo'] == activo_seleccionado]
    st.dataframe(df_filtrado)

    # Inputs para cálculos
    nominal = st.number_input("Ingresar nominal", min_value=0.0, format="%.2f")
    precio = st.number_input("Ingresar precio", min_value=0.0, format="%.2f")

    if nominal > 0 and precio > 0:
        valor_total = nominal * precio
        st.write(f"Valor total: {valor_total:.2f}")
