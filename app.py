from fpdf import FPDF
import pandas as pd
import streamlit as st
import requests
from io import BytesIO

st.set_page_config(page_title="Resumen de Cuenta", layout="wide")
st.title("Resumen de Cuenta en PDF")

# Ingreso de tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", min_value=0.0, value=1000.0, step=1.0, format="%.2f")

# URL del Excel en GitHub
excel_url = st.text_input("📄 URL del Excel en GitHub (Raw)", value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

# Descargar archivo Excel
try:
    response = requests.get(excel_url)
    response.raise_for_status()
    excel_file = BytesIO(response.content)
    df = pd.read_excel(excel_file)

    # Limpieza
    df = df.dropna(subset=["Activo"])
    df = df[df["Activo"] != ""]

    # Selección manual de activos
    activos_disponibles = df["Activo"].tolist()
    activos_seleccionados = st.multiselect("📌 Seleccioná los activos a incluir", activos_disponibles)

    if activos_seleccionados:
        df = df[df["Activo"].isin(activos_seleccionados)]

        st.subheader("✏️ Ingresá valores para cada activo")

        nominales = []
        precios = []

        for index, row in df.iterrows():
            activo = row["Activo"]
            moneda = row["Moneda"]
            nominal = st.number_input(f"{activo} - Nominal ({moneda})", min_value=0.0, step=1.0, key=f"nom_{index}")
            precio = st.number_input(f"{activo} - Precio ({'USD' if moneda == 'USD' else 'ARS'})", min_value=0.0, step=0.01, format="%.2f", key=f"prc_{index}")
            nominales.append(nominal)
            precios.append(precio)

        df["Nominal"] = nominales
        df["Precio"] = precios

        # Calcular monto USD según moneda
        def calcular_monto(row):
            if row["Moneda"] == "ARS":
                return (row["Nominal"] * row["Precio"]) / tipo_cambio
            else:
                return row["Nominal"] * row["Precio"]

        df["Monto USD"] = df.apply(calcular_monto, axis=1)
        total_general = df["Monto USD"].sum()
        df["Ponderación"] = df["Monto USD"] / total_general

        # Totales por Tipo de Activo
        totales = df.groupby("Tipo de Activo").agg({
            "Monto USD": "sum"
        }).rename(columns={"Monto USD": "Total por Tipo"}).reset_index()

        df = df.merge(totales, on="Tipo de Activo")
        df["Ponderación por Tipo"] = df["Total por Tipo"] / total_general

        # Exportar PDF
        if st.button("📤 Exportar resumen a PDF"):
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

            # Encabezados
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(60, 8, "Activo", border=1)
            pdf.cell(25, 8, "Nominal", border=1, align="R")
            pdf.cell(20, 8, "Precio", border=1, align="R")
            pdf.cell(25, 8, "Monto USD", border=1, align="R")
            pdf.cell(25, 8, "% del Total", border=1, align="R")
            pdf.cell(30, 8, "Tipo de Activo", border=1)
            pdf.cell(25, 8, "Total por Tipo", border=1, align="R")
            pdf.cell(25, 8, "% por Tipo", border=1, align="R")
            pdf.cell(35, 8, "Benchmark Esp.", border=1)
            pdf.cell(35, 8, "Benchmark Gral.", border=1)
            pdf.ln()

            # Contenido
            pdf.set_font("Arial", '', 8)
            for _, row in df.iterrows():
                pdf.cell(60, 6, str(row["Activo"]), border=1)
                pdf.cell(25, 6, f'{row["Nominal"]:,.0f}', border=1, align="R")
                pdf.cell(20, 6, f'{row["Precio"]:,.2f}', border=1, align="R")
                pdf.cell(25, 6, f'{row["Monto USD"]:,.2f}', border=1, align="R")
                pdf.cell(25, 6, f'{row["Ponderación"]*100:.2f}%', border=1, align="R")
                pdf.cell(30, 6, row["Tipo de Activo"], border=1)
                pdf.cell(25, 6, f'{row["Total por Tipo"]:,.2f}', border=1, align="R")
                pdf.cell(25, 6, f'{row["Ponderación por Tipo"]*100:.2f}%', border=1, align="R")
                pdf.cell(35, 6, str(row["Benchmark Específico"]), border=1)
                pdf.cell(35, 6, str(row["Benchmark General"]), border=1)
                pdf.ln()

            # Descargar
            pdf_output = BytesIO()
            pdf.output(pdf_output)
            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_output.getvalue(),
                file_name="resumen_cuenta.pdf",
                mime="application/pdf"
            )
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
