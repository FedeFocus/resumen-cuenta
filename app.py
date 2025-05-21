import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

st.set_page_config(layout="wide")
st.title("Resumen de Cuenta en PDF")

# Entrada del tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", value=1000.0, step=0.1)

# Cargar archivo Excel desde GitHub
st.subheader("📄 URL del Excel en GitHub (Raw)")
url_excel = st.text_input(
    "Pegá acá el enlace RAW del archivo Excel",
    value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx",
)

@st.cache_data
def cargar_excel(url):
    return pd.read_excel(url)

try:
    df_raw = cargar_excel(url_excel)
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
    st.stop()

# Selección manual de activos
st.subheader("📌 Seleccioná los activos a incluir")
activos_seleccionados = st.multiselect(
    "Elegí los activos que querés incluir",
    options=df_raw["Activo"].dropna().unique(),
)

# Filtrar activos seleccionados
df = df_raw[df_raw["Activo"].isin(activos_seleccionados)].copy()

# Entrada de valores nominales y precios
st.subheader("✏️ Ingresá valores para cada activo")
for i, row in df.iterrows():
    col1, col2 = st.columns(2)
    with col1:
        df.at[i, "Valor Nominal"] = st.number_input(f"Valor nominal de {row['Activo']}", value=0.0, step=1.0, key=f"nom_{i}")
    with col2:
        df.at[i, "Precio"] = st.number_input(f"Precio de {row['Activo']}", value=0.0, step=0.1, key=f"pre_{i}")

# Cálculo del monto en USD
def calcular_monto(row):
    if row["Moneda"] == "ARS":
        return row["Valor Nominal"] / tipo_cambio
    elif row["Moneda"] == "USD":
        return row["Valor Nominal"] * row["Precio"]
    else:
        return 0.0

df["Monto USD"] = df.apply(calcular_monto, axis=1)
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Cálculo por tipo de activo
resumen_tipo = df.groupby("Tipo de Activo")[["Monto USD"]].sum().rename(columns={"Monto USD": "Total por Tipo"})
resumen_tipo["% por Tipo"] = resumen_tipo["Total por Tipo"] / total_general
df = df.merge(resumen_tipo, on="Tipo de Activo", how="left")

# Exportar a PDF
st.subheader("📤 Exportar resumen a PDF")

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", border=False, ln=True, align="C")
        self.ln(5)

    def tabla(self, data):
        self.set_font("Arial", size=8)
        col_widths = [40, 20, 20, 25, 25, 25, 25, 30, 30]
        headers = [
            "Activo", "Nominal", "Precio", "Monto USD", "% Activo",
            "Total por Tipo", "% por Tipo", "Benchmark Esp.", "Benchmark Gral."
        ]
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1, 0, "C")
        self.ln()
        for _, row in data.iterrows():
            self.cell(col_widths[0], 8, str(row["Activo"]), 1)
            self.cell(col_widths[1], 8, f"{row['Valor Nominal']:.0f}", 1, 0, "R")
            self.cell(col_widths[2], 8, f"{row['Precio']:.2f}", 1, 0, "R")
            self.cell(col_widths[3], 8, f"{row['Monto USD']:.2f}", 1, 0, "R")
            self.cell(col_widths[4], 8, f"{row['Ponderación']*100:.2f}%", 1, 0, "R")
            self.cell(col_widths[5], 8, f"{row['Total por Tipo']:.2f}", 1, 0, "R")
            self.cell(col_widths[6], 8, f"{row['% por Tipo']*100:.2f}%", 1, 0, "R")
            self.cell(col_widths[7], 8, str(row["Benchmark Específico"]), 1)
            self.cell(col_widths[8], 8, str(row["Benchmark General"]), 1)
            self.ln()

pdf = PDF(orientation='L', unit='mm', format='A4')
pdf.add_page()
pdf.tabla(df)

pdf_buffer = BytesIO()
pdf.output(pdf_buffer)
pdf_buffer.seek(0)

st.download_button(
    label="📥 Descargar PDF",
    data=pdf_buffer,
    file_name="resumen_cuenta.pdf",
    mime="application/pdf",
)
