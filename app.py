import streamlit as st
import pandas as pd

# Cargar datos
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")
st.write("Seleccioná los activos que querés incluir:")

# Multiselect para elegir activos
activos_seleccionados = st.multiselect("Seleccionar activos", options=df['Activo'].unique())

if activos_seleccionados:
    st.subheader("Ingresá nominales y precios para los activos seleccionados")

    valores_activos = {}
    for i, activo in enumerate(activos_seleccionados):
        st.write(f"### Activo: {activo}")
        
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, format="%.2f", key=f"nominal_{i}")
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, format="%.2f", key=f"precio_{i}")
        
        total = nominal * precio
        st.write(f"Valor total para {activo}: {total:.2f}")
        
        valores_activos[activo] = total

    # Sumar solo los valores de los activos seleccionados
    valor_final = sum(valores_activos.values())
    st.markdown(f"## Valor Final del Resumen de Cuenta: **{valor_final:.2f}**")
else:
    st.write("No hay activos seleccionados.")
