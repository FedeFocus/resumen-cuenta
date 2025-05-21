import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# URL del archivo Excel (reemplazá esta con tu URL "Raw")
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"

# Leer Excel
df_raw = pd.read_excel(url_excel)

st.title("Resumen de Cuenta")

# Elegir activos a cargar
activos_seleccionados = st.multiselect(
    "Seleccioná los activos a cargar:",
    options=df_raw["Activo"].dropna().unique()
)

# Filtrar activos seleccionados
df = df_raw[df_raw["Activo"].isin(activos_seleccionados)].copy()

# Inputs manuales
tipo_cambio = st.number_input("Tipo de cambio (USD/ARS)", value=1100.0)

valores_nominales = {}
precios = {}
montos_usd = []

st.subheader("Cargar valores nominales y precios:")
for idx, row in df.iterrows():
    activo = row["Activo"]
    moneda = row["Moneda"]

    valores_nominales[activo] = st.number_input(f"Valor nominal de {activo}", value=0.0)
    precios[activo] = st.number_input(f"Precio de {activo}", value=0.0)

    if moneda == "ARS":
        monto_usd = valores_nominales[activo] / tipo_cambio
    else:  # USD
        monto_usd = valores_nominales[activo] * precios[activo]

    montos_usd.append(monto_usd)

df["Nominal"] = df["Activo"].map(valores_nominales)
df["Precio"] = df["Activo"].map(precios)
df["Monto USD"] = montos_usd

# Calcular totales y ponderaciones
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Calcular subtotales por tipo de activo
resumen_tipo = df.groupby("Tipo de Activo").agg({
    "Monto USD": "sum"
}).rename(columns={"Monto USD": "Total por tipo"})
resumen_tipo["Ponderación tipo"] = resumen_tipo["Total por tipo"] / total_general
df = df.merge(resumen_tipo, on="Tipo de Activo")

# Mostrar tabla en pantalla
st.dataframe(df[[
    "Activo", "Nominal", "Precio", "Monto USD", "Ponderación", 
    "Total por tipo", "Ponderación tipo", 
    "Benchmark Específico", "Benchmark General"
]])

# Generar PDF
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", "", 10)

columns = [
    "Activo", "Nominal", "Precio", "Monto USD", "Ponderación", 
    "Total por tipo", "Ponderación tipo", 
    "Benchmark Específico", "Benchmark General"
]

# Encabezados
for col in columns:
    pdf.cell(35, 8, col, border=1)
pdf.ln()

# Filas
for _, row in df.iterrows():
    for col in columns:
        val = row[col]
        if isinstance(val, float):
            pdf.cell(35, 8, f"{val:,.2f}", border=1)
        else:
            pdf.cell(35, 8, str(val), border=1)
    pdf.ln()

# Descargar PDF
pdf_output = BytesIO()
pdf.output(pdf_output)
st.download_button("📄 Descargar PDF", data=pdf_output.getvalue(), file_name="resumen_cuenta.pdf")
