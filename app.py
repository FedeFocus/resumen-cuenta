import streamlit as st
import pandas as pd
from fpdf import FPDF

st.set_page_config(layout="centered")

# Entrada de tipo de cambio
tipo_cambio = st.number_input("Ingresar tipo de cambio (USD)", min_value=0.01, step=0.01, format="%.2f")

# Cargar archivo Excel directamente del repositorio
try:
    df = pd.read_excel("BD.xlsx", header=None)
except FileNotFoundError:
    st.error("No se encontró el archivo BD.xlsx. Asegúrate de que esté en la raíz del repositorio.")
    st.stop()

# Identificar los grupos de activos por filas vacías o etiquetas
activos_final = []
grupo_actual = None

for i, row in df.iterrows():
    # Detectar fila con nombre del grupo de activos
    if pd.isna(row[0]) and pd.notna(row[1]):
        grupo_actual = row[1]
        continue

    # Filas que contienen activos válidos
    if pd.notna(row[0]) and pd.notna(row[2]) and pd.notna(row[3]):
        activos_final.append({
            "Grupo": grupo_actual,
            "Activo": str(row[0]),
            "Benchmark Específico": str(row[7]),
            "Benchmark General": str(row[8]),
            "Nominal": float(row[2]),
            "Precio": float(row[3]),
            "Moneda": str(row[6]).upper(),
        })

# Crear DataFrame limpio
df_final = pd.DataFrame(activos_final)

# Cálculo del Total en USD
if tipo_cambio <= 0:
    st.warning("Ingresar un tipo de cambio válido para procesar los datos.")
    st.stop()

def calcular_total(row):
    if row["Moneda"] == "ARS":
        return row["Nominal"] / tipo_cambio
    elif row["Moneda"] == "USD":
        return row["Nominal"] * row["Precio"]
    else:
        return 0

df_final["Total"] = df_final.apply(calcular_total, axis=1)

total_general = df_final["Total"].sum()
df_final["Ponderación (%)"] = df_final["Total"] / total_general * 100

# Calcular totales por tipo de activo (grupo)
grupos = df_final.groupby("Grupo").agg({
    "Total": "sum"
}).reset_index()
grupos["Ponderación (%)"] = grupos["Total"] / total_general * 100

# Mostrar tabla
st.title("Resumen de Cuenta")
st.dataframe(df_final.style.format({"Precio": "$ {:.2f}", "Total": "$ {:.2f}", "Ponderación (%)": "{:.2f}%"}))

# Mostrar totales por grupo
st.subheader("Totales por Tipo de Activo")
st.dataframe(grupos.style.format({"Total": "$ {:.2f}", "Ponderación (%)": "{:.2f}%"}))

# Mostrar total general
st.markdown(f"**Total General:** $ {total_general:,.2f}")

# Mostrar benchmarks generales
benchmarks_generales = df_final["Benchmark General"].dropna().unique()
st.markdown("**Benchmarks Generales:** " + ", ".join(benchmarks_generales))
