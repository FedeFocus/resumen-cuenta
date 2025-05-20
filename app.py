import streamlit as st
import pandas as pd
from fpdf import FPDF

st.title("Resumen de Cuenta")

# Cargar Excel
df = pd.read_excel("BD.xlsx", header=None)

# Ingreso manual del tipo de cambio
tipo_cambio = st.number_input("Ingresar tipo de cambio (USD)", min_value=0.01, step=0.01)

# Variables para almacenar resultados
data_final = []
grupos = []
current_group = None

# Procesar filas
for _, row in df.iterrows():
    # Fila vacía
    if pd.isna(row[0]):
        continue

    # Si es fila de título de grupo (como "ONs", "Bopreal", etc.)
    if pd.isna(row[1]) and pd.isna(row[2]):
        current_group = row[0]
        grupos.append({"nombre": current_group, "activos": []})
        continue

    try:
        activo = str(row[0])
        benchmark_especifico = str(row[6])  # Asumiendo que esta es la columna correspondiente
        benchmark_general = str(row[7])     # Última columna
        nominal = float(row[2])
        precio = float(row[3])
        moneda = str(row[5]).strip().upper()

        # Cálculo del total en USD
        if moneda == "ARS":
            total_usd = nominal / tipo_cambio if tipo_cambio != 0 else 0
        elif moneda == "USD":
            total_usd = nominal * precio
        else:
            continue  # moneda desconocida, se salta

        grupos[-1]["activos"].append({
            "Activo": activo,
            "Benchmark Específico": benchmark_especifico,
            "Benchmark General": benchmark_general,
            "Nominal": nominal,
            "Precio": precio,
            "Total USD": total_usd
        })
    except Exception as e:
        continue  # Se salta cualquier fila malformada

# Cálculo total general
total_general = sum(
    sum(activo["Total USD"] for activo in grupo["activos"])
    for grupo in grupos
)

# Mostrar tabla
st.write("## Resumen de Cuenta")
for grupo in grupos:
    st.write(f"### {grupo['nombre']}")
    grupo_total = sum(act["Total USD"] for act in grupo["activos"])
    for act in grupo["activos"]:
        act["Ponderación (%)"] = f"{(act['Total USD'] / total_general * 100):.2f}%"
    df_mostrar = pd.DataFrame(grupo["activos"])
    st.table(df_mostrar[[
        "Activo", "Benchmark Específico", "Nominal", "Precio", "Total USD", "Ponderación (%)"
    ]])
    st.write(f"**Total {grupo['nombre']}: ${grupo_total:,.2f}**")

# Mostrar total general
st.write(f"## Total general: ${total_general:,.2f}")
