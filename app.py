import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# Cargar datos del Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")

# Columnas a usar
col_activo = "Activo"
col_benchmark_especifico = "Benchmark Específico"
col_benchmark_general = "Benchmark General"

# Mostrar datos para verificar estructura
st.write("Vista previa de datos:")
st.dataframe(df.head())
st.write(f"Columnas disponibles: {list(df.columns)}")

# Selección de activos
activos = df[col_activo].dropna().unique()
benchmark_dict = dict(zip(df[col_activo], df[col_benchmark_especifico]))
benchmark_general_dict = dict(zip(df[col_activo], df[col_benchmark_general]))

# Tipo de cambio para activos en ARS
tipo_cambio = st.number_input("Ingresar tipo de cambio ARS/USD:", min_value=0.01, step=0.1, format="%.2f")

# Selección de activos
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

for activo in activos_seleccionados:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"**Activo:** {activo}")
    with col2:
        nominal = st.number_input(f"Nominal ({activo})", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col3:
        precio = st.number_input(f"Precio ({activo})", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")

    # Determinar si el activo está en ARS o USD según nombre
    es_ars = "ARS" in activo or "S" in activo  # Puedes mejorar esta lógica
    if es_ars:
        total_usd = (nominal * precio) / tipo_cambio if tipo_cambio else 0.0
    else:
        total_usd = nominal * precio

    resumen.append({
        "Activo": activo,
        "Nominal (ARS)": nominal,
        "Precio": precio,
        "Total (USD)": total_usd,
        "Benchmark Específico": benchmark_dict.get(activo, "N/A"),
        "Benchmark General": benchmark_general_dict.get(activo, "N/A")
    })

resumen_df = pd.DataFrame(resumen)

# Calcular ponderación
if not resumen_df.empty:
    total_general = resumen_df["Total (USD)"].sum()
    resumen_df["Ponderación"] = resumen_df["Total (USD)"] / total_general * 100

    st.subheader("📋 Resumen calculado")
    st.dataframe(resumen_df, use_container_width=True)
    st.markdown(f"### 🪙 Total final (USD): ${total_general:,.2f}")
else:
    total_general = 0.0

# Función para PDF en formato horizontal
def crear_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 11)
    columnas = ["Activo", "Nominal (ARS)", "Precio", "Total (USD)", "Ponderación (%)", "Benchmark Específico", "Benchmark General"]
    col_widths = [80, 25, 25, 30, 30, 50, 50]

    for i, col in enumerate(columnas):
        pdf.cell(col_widths[i], 10, col, border=1, align='C')
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 10, str(row["Activo"])[:60], border=1)
        pdf.cell(col_widths[1], 10, f"{row['Nominal (ARS)']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[2], 10, f"${row['Precio']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[3], 10, f"${row['Total (USD)']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[4], 10, f"{row['Ponderación']:.2f}%", border=1, align='R')
        pdf.cell(col_widths[5], 10, str(row["Benchmark Específico"])[:30], border=1)
        pdf.cell(col_widths[6], 10, str(row["Benchmark General"])[:30], border=1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total general (USD): ${df['Total (USD)'].sum():,.2f}", ln=True, align='R')

    # Mostrar Benchmarks Generales
    benchmarks_generales = df["Benchmark General"].dropna().unique()
    if len(benchmarks_generales) > 0:
        texto = ", ".join(benchmarks_generales)
        pdf.cell(0, 10, f"Benchmarks Generales: {texto}", ln=True)

    pdf_str = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_str)

# Descargar PDF
if not resumen_df.empty:
    pdf_bytes = crear_pdf(resumen_df)
    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_bytes,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
