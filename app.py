import streamlit as st
import pandas as pd

# Cargar datos
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")
st.write("Lista de activos cargados desde Excel:")

# Mostrar tabla completa
st.dataframe(df)

# Crear un diccionario para guardar los totales por activo
valores_activos = {}

st.subheader("Ingresá nominales y precios para cada activo")

for i, activo in enumerate(df['Activo']):
    st.write(f"### Activo: {activo}")

    nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, format="%.2f", key=f"nominal_{i}")
    precio = st.number_input(f"Precio para {activo}", min_value=0.0, format="%.2f", key=f"precio_{i}")

    total = nominal * precio
    st.write(f"Valor total para {activo}: {total:.2f}")

    valores_activos[activo] = total

# Sumar todos los valores totales
valor_final = sum(valores_activos.values())
st.markdown(f"## Valor Final del Resumen de Cuenta: **{valor_final:.2f}**")
