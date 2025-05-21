import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from fpdf import FPDF

st.set_page_config(page_title="Resumen de Cuenta", layout="wide")
st.title("Resumen de Cuenta en PDF")

# Ingreso del tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", min_value=0.01, step=0.01, format="%.2f")

# Ingreso de la URL del Excel
url = st.text_input("📄 URL del Excel en GitHub (Raw)", value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

@st.cache_data
def cargar_excel_desde_github(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return pd.read_excel(BytesIO(response.content))
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        return None

df_original = cargar_excel_desde_github(url)

if df_original is not None:
    activos_disponibles = df_original["Activo"].dropna().unique().tolist()
    seleccionados = st.multiselect("📌 Seleccioná los activos a incluir", activos_disponibles)

    if seleccionados:
        df = df_original[df_original["Activo"].isin(seleccionados)].copy()

        # Ingreso de valores por activo
        st.subheader("✏️ Ingresá valores para cada activo")
        for i, row in df.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                df.at[i, "Valores Nominales"] = st.number_input(f"Nominal de {row['Activo']}", key=f"nom_{i}", step=1.0)
            with col2:
                df.at[i, "Precio"] = st.number_input(f"Precio de {row['Activo']}", key=f"pre_{i}", step=0.01)

        # Cálculo del monto en USD
        def calcular_monto(row):
            try:
                if row["Moneda"] == "ARS":
                    return row["Valores Nominales"] * row["Precio"] / tipo_cambio
                else:
                    return row["Valores Nominales"] * row["Precio"]
            except:
                return 0

        df["Monto USD"] = df.apply(calcular_monto, axis=1)
        total_general = df["Monto USD"].sum()
        df["Ponderación"] = df["Monto USD"] / total_general

        # Cálculo de totales por tipo de activo
        resumen_por_tipo = df.groupby("Tipo de Activo").agg({
            "Monto USD": "sum"
        }).rename(columns={"Monto USD": "Monto Total Tipo"}).reset_index()
        resumen_por_tipo["Ponderación Tipo"] = resumen_por_tipo["Monto Total Tipo"] / total_general

        # Exportación a PDF
        st.subheader("📤 Exportar resumen a PDF")
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=10)

        # Encabezados
        encabezados = ["Activo", "Valores Nominales", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]
        for col in encabezados:
            pdf.cell(40, 10, col, border=1)
        pdf.ln()

        # Filas por activo
        for _, row in df.iterrows():
            pdf.cell(40, 10, str(row["Activo"]), border=1)
            pdf.cell(40, 10, f"{row['Valores Nominales']:.2f}", border=1)
            pdf.cell(40, 10, f"{row['Precio']:.2f}", border=1)
            pdf.cell(40, 10, f"{row['Monto USD']:.2f}", border=1)
            pdf.cell(40, 10, f"{row['Ponderación']:.2%}", border=1)
            pdf.cell(40, 10, str(row["Benchmark Específico"]), border=1)
            pdf.cell(40, 10, str(row["Benchmark General"]), border=1)
            pdf.ln()

        # Totales por tipo de activo
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(40, 10, "Totales por Tipo de Activo", ln=1)

        for _, row in resumen_por_tipo.iterrows():
            pdf.cell(60, 10, row["Tipo de Activo"], border=1)
            pdf.cell(60, 10, f"{row['Monto Total Tipo']:.2f}", border=1)
            pdf.cell(60, 10, f"{row['Ponderación Tipo']:.2%}", border=1)
            pdf.ln()

        # Generar archivo PDF en memoria
        pdf_bytes = pdf.output(dest='S').encode('latin1')

        st.download_button(
            label="📥 Descargar PDF",
            data=pdf_bytes,
            file_name="resumen_cuenta.pdf",
            mime="application/pdf"
        )
