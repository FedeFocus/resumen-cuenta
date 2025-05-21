import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Título
st.title("Resumen de Cuenta - Generador PDF")

# Cargar Excel desde GitHub (reemplazá esta URL por la tuya real si cambia)
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
df_raw = pd.read_excel(url_excel)

# Mostrar la tabla base
st.subheader("Activos disponibles")
st.dataframe(df_raw)

# Selección de activos
activos_seleccionados = st.multiselect("Seleccioná los activos que querés incluir", df_raw["Activo"].dropna().unique())

# Filtrar los seleccionados
df = df_raw[df_raw["Activo"].isin(activos_seleccionados)].copy()

# Ingreso de tipo de cambio
tipo_cambio = st.number_input("Tipo de cambio (USD/ARS)", min_value=0.01, value=100.0, step=0.1)

# Ingreso manual de valores nominales y precios
st.subheader("Ingresar datos por activo")
for i, row in df.iterrows():
    nominal = st.number_input(f"Nominal de {row['Activo']}", min_value=0.0, key=f"nominal_{i}")
    precio = st.number_input(f"Precio de {row['Activo']}", min_value=0.0, key=f"precio_{i}")
    df.at[i, "Valores Nominales"] = nominal
    df.at[i, "Precio"] = precio

# Calcular Monto USD
def calcular_monto(row):
    if row["Moneda"] == "ARS":
        return row["Valores Nominales"] * row["Precio"] / tipo_cambio
    else:
        return row["Valores Nominales"] * row["Precio"]

df["Monto USD"] = df.apply(calcular_monto, axis=1)

# Calcular ponderación general
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Calcular totales por tipo de activo
resumen = df.groupby("Tipo de Activo").agg(
    {"Monto USD": "sum"}
).rename(columns={"Monto USD": "Total Tipo USD"}).reset_index()

resumen["Ponderación Tipo"] = resumen["Total Tipo USD"] / total_general

# Crear PDF
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", "B", 14)
pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

# Columnas
columnas = ["Activo", "Valores Nominales", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]
ancho_col = [60, 35, 25, 30, 30, 60, 60]

pdf.set_font("Arial", "B", 10)
for col, ancho in zip(columnas, ancho_col):
    pdf.cell(ancho, 10, col, border=1)
pdf.ln()

# Filas por tipo
pdf.set_font("Arial", "", 9)

for tipo in df["Tipo de Activo"].unique():
    subset = df[df["Tipo de Activo"] == tipo]
    for _, fila in subset.iterrows():
        pdf.cell(ancho_col[0], 8, str(fila["Activo"]), border=1)
        pdf.cell(ancho_col[1], 8, f'{fila["Valores Nominales"]:.2f}', border=1, align="R")
        pdf.cell(ancho_col[2], 8, f'{fila["Precio"]:.2f}', border=1, align="R")
        pdf.cell(ancho_col[3], 8, f'{fila["Monto USD"]:.2f}', border=1, align="R")
        pdf.cell(ancho_col[4], 8, f'{fila["Ponderación"]:.2%}', border=1, align="R")
        pdf.cell(ancho_col[5], 8, str(fila["Benchmark Específico"]), border=1)
        pdf.cell(ancho_col[6], 8, str(fila["Benchmark General"]), border=1)
        pdf.ln()

    # Fila total por tipo
    total_fila = resumen[resumen["Tipo de Activo"] == tipo].iloc[0]
    pdf.set_font("Arial", "B", 9)
    pdf.cell(ancho_col[0], 8, f"Total {tipo}", border=1)
    pdf.cell(ancho_col[1], 8, "", border=1)
    pdf.cell(ancho_col[2], 8, "", border=1)
    pdf.cell(ancho_col[3], 8, f'{total_fila["Total Tipo USD"]:.2f}', border=1, align="R")
    pdf.cell(ancho_col[4], 8, f'{total_fila["Ponderación Tipo"]:.2%}', border=1, align="R")
    pdf.cell(ancho_col[5], 8, "", border=1)
    pdf.cell(ancho_col[6], 8, "", border=1)
    pdf.ln()
    pdf.set_font("Arial", "", 9)

# Descargar PDF
pdf_bytes = pdf.output(dest="S").encode("latin1")  # exportar como string y codificar
pdf_output = BytesIO(pdf_bytes)

st.download_button(
    "📄 Descargar PDF",
    data=pdf_output,
    file_name="resumen_cuenta.pdf",
    mime="application/pdf"
)
