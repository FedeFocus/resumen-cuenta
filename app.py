import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import requests
from io import BytesIO

st.set_page_config(layout="wide")
st.title("Resumen de Cuenta en PDF")

# Tipo de cambio manual
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", min_value=0.01, value=1000.0, step=0.01, format="%.2f")

# URL al Excel en GitHub (Raw)
st.markdown("### 📄 URL del Excel en GitHub (Raw)")
excel_url = st.text_input("Pegá acá el enlace RAW del archivo Excel", value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

@st.cache_data
def cargar_datos(url):
    contenido = requests.get(url).content
    df = pd.read_excel(BytesIO(contenido))
    return df

try:
    df_base = cargar_datos(excel_url)
    activos_disponibles = df_base["Activo"].tolist()

    st.markdown("### 📌 Seleccioná los activos a incluir")
    activos_seleccionados = st.multiselect("Elegí los activos que querés incluir", activos_disponibles)

    if activos_seleccionados:
        df = df_base[df_base["Activo"].isin(activos_seleccionados)].copy()

        st.markdown("### ✏️ Ingresá valores para cada activo")
        valores_nominales = {}
        precios_usd = {}

        for i, row in df.iterrows():
            activo = row["Activo"]
            moneda = row["Moneda"]

            col1, col2 = st.columns([3, 2])
            with col1:
                nominal = st.number_input(f"Nominales de {activo}", key=f"nom_{i}", step=1.0)
                valores_nominales[i] = nominal
            if moneda == "USD":
                with col2:
                    precio = st.number_input(f"Precio en USD de {activo}", key=f"precio_{i}", step=0.01, format="%.2f")
                    precios_usd[i] = precio

        # Agregar columnas de datos
        df["Nominales"] = df.index.map(valores_nominales)
        df["Precio"] = df.index.map(precios_usd).fillna(0)

        # Calcular el monto en USD
        def calcular_monto(row):
            if row["Moneda"] == "ARS":
                return row["Nominales"] / tipo_cambio
            else:
                return row["Nominales"] * row["Precio"]

        df["Monto USD"] = df.apply(calcular_monto, axis=1)
        total_general = df["Monto USD"].sum()
        df["Ponderación"] = df["Monto USD"] / total_general

        # Totales por tipo de activo
        totales = df.groupby("Tipo de Activo")["Monto USD"].sum().reset_index(name="Total Subgrupo")
        df = df.merge(totales, on="Tipo de Activo")
        df["Ponderación Subgrupo"] = df["Total Subgrupo"] / total_general

        st.markdown("### 📤 Exportar resumen a PDF")
        if st.button("Generar PDF"):

            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")
            pdf.ln(5)

            # Títulos de tabla
            headers = ["Activo", "Nominales", "Precio", "Monto USD", "% Activo", "Total Subgrupo", "% Subgrupo", "Benchmark Específico", "Benchmark General"]
            col_widths = [80, 25, 20, 25, 20, 30, 25, 35, 35]

            pdf.set_font("Arial", "B", 9)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 8, header, border=1)
            pdf.ln()

            pdf.set_font("Arial", "", 8)

            for _, row in df.iterrows():
                pdf.cell(col_widths[0], 6, str(row["Activo"]), border=1)
                pdf.cell(col_widths[1], 6, f'{row["Nominales"]:.0f}', border=1, align="R")
                pdf.cell(col_widths[2], 6, f'{row["Precio"]:.2f}' if row["Moneda"] == "USD" else "-", border=1, align="R")
                pdf.cell(col_widths[3], 6, f'{row["Monto USD"]:.2f}', border=1, align="R")
                pdf.cell(col_widths[4], 6, f'{row["Ponderación"]*100:.2f}%', border=1, align="R")
                pdf.cell(col_widths[5], 6, f'{row["Total Subgrupo"]:.2f}', border=1, align="R")
                pdf.cell(col_widths[6], 6, f'{row["Ponderación Subgrupo"]*100:.2f}%', border=1, align="R")
                pdf.cell(col_widths[7], 6, str(row["Benchamark Específico"]), border=1)
                pdf.cell(col_widths[8], 6, str(row["Benchmark General"]), border=1)
                pdf.ln()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                pdf.output(tmp_file.name)
                with open(tmp_file.name, "rb") as f:
                    st.download_button("📥 Descargar PDF", f, file_name="resumen_cuenta.pdf")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
