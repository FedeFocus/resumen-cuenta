import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import requests

st.set_page_config(page_title="Resumen de Cuenta", layout="wide")

st.title("📄 Resumen de Cuenta en PDF")

# Ingreso URL de Excel
excel_url = st.text_input("📎 URL del Excel en GitHub (Raw)", 
    "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

# Tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", min_value=1.0, step=1.0, format="%.2f")

# Cargar base desde GitHub
@st.cache_data
def cargar_base(url):
    content = requests.get(url).content
    return pd.read_excel(BytesIO(content))

try:
    df = cargar_base(excel_url)
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
    st.stop()

# Selección de activos
activos_filtrados = st.multiselect("🔎 Seleccioná los activos a incluir", df["Activo"].dropna().unique())

if activos_filtrados:
    df = df[df["Activo"].isin(activos_filtrados)].copy()

    # Ingreso de valores nominales y precios
    st.subheader("📝 Ingresá valores para cada activo")

    for i, fila in df.iterrows():
        col1, col2 = st.columns(2)
        with col1:
            nominal = st.number_input(f"Nominal de {fila['Activo']}", key=f"nominal_{i}", min_value=0.0, format="%.2f")
        with col2:
            precio = st.number_input(f"Precio de {fila['Activo']}", key=f"precio_{i}", min_value=0.0, format="%.2f")
        df.at[i, "Nominal"] = nominal
        df.at[i, "Precio"] = precio

    # Calcular monto USD
    def calcular_monto(row):
        if row["Moneda"] == "ARS":
            return (row["Nominal"] * row["Precio"]) / tipo_cambio
        elif row["Moneda"] == "USD":
            return row["Nominal"] * row["Precio"]
        else:
            return 0.0

    df["Monto USD"] = df.apply(calcular_monto, axis=1)
    total_general = df["Monto USD"].sum()
    df["Ponderación"] = df["Monto USD"] / total_general

    # Agrupar por tipo de activo y calcular subtotales
    df.sort_values(by="Tipo de Activo", inplace=True)
    resumen_pdf = []

    for tipo, grupo in df.groupby("Tipo de Activo"):
        resumen_pdf.extend(grupo.to_dict("records"))
        subtotal = grupo["Monto USD"].sum()
        ponderacion = subtotal / total_general
        resumen_pdf.append({
            "Activo": f"Total {tipo}",
            "Nominal": "",
            "Precio": "",
            "Monto USD": subtotal,
            "Ponderación": ponderacion,
            "Benchmark Específico": "",
            "Benchmark General": ""
        })

    # Crear PDF
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Resumen de Cuenta", ln=True)

    pdf.set_font("Arial", "B", 10)
    col_widths = [60, 30, 25, 30, 30, 50, 50]
    headers = ["Activo", "Nominal", "Precio", "Monto USD", "%", "Benchmark Específico", "Benchmark General"]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    for fila in resumen_pdf:
        pdf.cell(col_widths[0], 8, str(fila["Activo"]), border=1)
        pdf.cell(col_widths[1], 8, f"{fila['Nominal']:.2f}" if fila["Nominal"] != "" else "", border=1, align="R")
        pdf.cell(col_widths[2], 8, f"{fila['Precio']:.2f}" if fila["Precio"] != "" else "", border=1, align="R")
        pdf.cell(col_widths[3], 8, f"{fila['Monto USD']:.2f}", border=1, align="R")
        pdf.cell(col_widths[4], 8, f"{fila['Ponderación']:.2%}", border=1, align="R")
        pdf.cell(col_widths[5], 8, str(fila["Benchmark Específico"]), border=1)
        pdf.cell(col_widths[6], 8, str(fila["Benchmark General"]), border=1)
        pdf.ln()

    # Descargar PDF
    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    st.download_button("📥 Descargar PDF", data=pdf_output, file_name="resumen_cuenta.pdf")

else:
    st.info("Seleccioná al menos un activo para comenzar.")
