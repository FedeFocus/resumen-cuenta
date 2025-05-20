import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# Cargar los datos desde el archivo Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")

col_activo = "Activo"
col_benchmark_especifico = "Benchmark Específico"
col_benchmark_general = "Benchmark General"

activos = df[col_activo].dropna().unique()
benchmark_dict = dict(zip(df[col_activo], df[col_benchmark_especifico]))
benchmark_general_dict = dict(zip(df[col_activo], df[col_benchmark_general]))

# Selección de tipo de cambio manual para ARS
tipo_cambio = st.number_input("Ingresar tipo de cambio ARS/USD", min_value=0.01, step=0.01, format="%.2f")

# Selección de activos
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

for activo in activos_seleccionados:
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        st.write(f"**Activo:** {activo}")
    with col2:
        nominal = st.number_input(f"Nominal (ARS) - {activo}", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col3:
        precio = st.number_input(f"Precio - {activo}", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")
    with col4:
        moneda = st.selectbox(f"Moneda de {activo}", ["ARS", "USD"], key=f"moneda_{activo}")

    if moneda == "ARS":
        monto_usd = (nominal * precio) / tipo_cambio if tipo_cambio else 0.0
    else:
        monto_usd = st.number_input(f"Importe en USD - {activo}", min_value=0.0, step=0.01, format="%.2f", key=f"usd_{activo}")

    resumen.append({
        "Activo": activo,
        "Nominal": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "Benchmark": benchmark_dict.get(activo, "N/A"),
        "Benchmark General": benchmark_general_dict.get(activo, "N/A")
    })

resumen_df = pd.DataFrame(resumen)

if not resumen_df.empty:
    total_usd = resumen_df["Monto USD"].sum()
    resumen_df["Ponderación"] = resumen_df["Monto USD"] / total_usd * 100 if total_usd else 0.0

    st.subheader("📋 Resumen calculado")
    st.dataframe(resumen_df[["Activo", "Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark", "Benchmark General"]], use_container_width=True)

    st.markdown(f"### 🪙 Total en USD: ${total_usd:,.2f}")

    def crear_pdf(df):
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align='C')
        pdf.ln(8)

        pdf.set_font("Arial", "B", 10)
        columnas = ["Activo", "Nominal", "Precio", "Monto USD", "Ponderación (%)", "Benchmark Específico", "Benchmark General"]
        col_widths = [80, 25, 25, 30, 30, 50, 50]

        for i, col in enumerate(columnas):
            pdf.cell(col_widths[i], 8, col, border=1, align='C')
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for _, row in df.iterrows():
            pdf.cell(col_widths[0], 8, str(row["Activo"])[:60], border=1)
            pdf.cell(col_widths[1], 8, f"{row['Nominal']:,.2f}", border=1, align='R')
            pdf.cell(col_widths[2], 8, f"{row['Precio']:,.2f}", border=1, align='R')
            pdf.cell(col_widths[3], 8, f"{row['Monto USD']:,.2f}", border=1, align='R')
            pdf.cell(col_widths[4], 8, f"{row['Ponderación']:.2f}%", border=1, align='R')
            pdf.cell(col_widths[5], 8, str(row["Benchmark"])[:40], border=1)
            pdf.cell(col_widths[6], 8, str(row["Benchmark General"])[:40], border=1)
            pdf.ln()

        pdf.ln(4)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, f"Total general en USD: ${df['Monto USD'].sum():,.2f}", ln=True, align='R')

        pdf_str = pdf.output(name='', dest='S')
        pdf_bytes = pdf_str.encode('latin1')
        return BytesIO(pdf_bytes)

    pdf_data = crear_pdf(resumen_df)
    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_data,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
else:
    st.info("No hay activos seleccionados o datos ingresados.")
