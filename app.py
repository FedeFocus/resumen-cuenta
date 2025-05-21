import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import requests

st.set_page_config(layout="wide")
st.title("Resumen de Cuenta en PDF")

# Ingreso del tipo de cambio
st.subheader("\U0001F4B1 Tipo de cambio ARS/USD")
tipo_cambio = st.number_input("", min_value=0.01, value=1000.0, step=0.01, format="%.2f")

# Cargar archivo desde GitHub
st.subheader("\U0001F4C4 URL del Excel en GitHub (Raw)")
url_excel = st.text_input("Pegá acá el enlace RAW del archivo Excel", "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

try:
    response = requests.get(url_excel)
    response.raise_for_status()
    df = pd.read_excel(BytesIO(response.content))

    # Convertir columnas necesarias a texto para evitar errores
    df['Activo'] = df['Activo'].astype(str)
    df['Moneda'] = df['Moneda'].astype(str)
    df['Tipo de Activo'] = df['Tipo de Activo'].astype(str)

    # Selección de activos
    st.subheader("\U0001F4CC Seleccioná los activos a incluir")
    activos_filtrados = st.multiselect(
        "Elegí los activos que querés incluir",
        options=df['Activo'].unique().tolist()
    )

    df = df[df['Activo'].isin(activos_filtrados)].copy()

    if not df.empty:
        st.subheader("\u270F\ufe0f Ingresá valores para cada activo")

        # Ingreso manual de precios y nominales
        precios = {}
        nominales = {}
        for _, row in df.iterrows():
            activo = row['Activo']
            precios[activo] = st.number_input(f"Precio de {activo}", value=0.0, key=f"p_{activo}")
            nominales[activo] = st.number_input(f"Nominal de {activo}", value=0.0, key=f"n_{activo}")

        df['Precio'] = df['Activo'].map(precios)
        df['Nominal'] = df['Activo'].map(nominales)

        def calcular_monto(row):
            if row['Moneda'] == 'ARS':
                return row['Nominal'] / tipo_cambio
            else:  # USD
                return row['Nominal'] * row['Precio']

        df['Monto USD'] = df.apply(calcular_monto, axis=1)
        total_general = df['Monto USD'].sum()
        df['Ponderación'] = df['Monto USD'] / total_general

        # Agrupar por Tipo de Activo
        subtotales = df.groupby('Tipo de Activo')['Monto USD'].sum().reset_index()
        subtotales['Ponderación'] = subtotales['Monto USD'] / total_general

        # Exportar a PDF
        st.subheader("\U0001F4E4 Exportar resumen a PDF")

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=10)

        pdf.set_fill_color(200, 200, 200)
        pdf.cell(60, 10, "Activo", 1, 0, 'C', fill=True)
        pdf.cell(30, 10, "Nominal", 1, 0, 'C', fill=True)
        pdf.cell(30, 10, "Precio", 1, 0, 'C', fill=True)
        pdf.cell(30, 10, "Monto USD", 1, 0, 'C', fill=True)
        pdf.cell(30, 10, "% del Total", 1, 0, 'C', fill=True)
        pdf.cell(55, 10, "Benchmark Específico", 1, 0, 'C', fill=True)
        pdf.cell(55, 10, "Benchmark General", 1, 1, 'C', fill=True)

        for _, row in df.iterrows():
            pdf.cell(60, 10, row['Activo'], 1)
            pdf.cell(30, 10, f"{row['Nominal']:.2f}", 1)
            pdf.cell(30, 10, f"{row['Precio']:.2f}", 1)
            pdf.cell(30, 10, f"{row['Monto USD']:.2f}", 1)
            pdf.cell(30, 10, f"{row['Ponderación']*100:.2f}%", 1)
            pdf.cell(55, 10, str(row['Benchmark Específico']), 1)
            pdf.cell(55, 10, str(row['Benchmark General']), 1)
            pdf.ln()

        # Subtotales
        pdf.ln(5)
        pdf.set_font("Arial", style='B', size=10)
        pdf.cell(60, 10, "Totales por Tipo de Activo", 0, 1)
        for _, row in subtotales.iterrows():
            pdf.cell(60, 10, row['Tipo de Activo'], 1)
            pdf.cell(30, 10, f"{row['Monto USD']:.2f}", 1)
            pdf.cell(30, 10, f"{row['Ponderación']*100:.2f}%", 1)
            pdf.ln()

        # Exportar como bytes para descargar
        pdf_output = pdf.output(dest='S').encode('latin1')
        pdf_buffer = BytesIO(pdf_output)

        st.download_button(
            label="\U0001F4C5 Descargar PDF",
            data=pdf_buffer,
            file_name="resumen_cuenta.pdf",
            mime="application/pdf"
        )

    else:
        st.warning("Seleccioná al menos un activo para continuar.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
