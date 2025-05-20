import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# Cargar los datos desde el archivo Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

# Mostrar datos y columnas para verificar estructura
st.write("Datos cargados del Excel (primeras filas):")
st.dataframe(df.head())
st.write(f"Columnas disponibles: {list(df.columns)}")

st.title("Resumen de Cuenta de Activos")

# Columnas específicas que vamos a usar
col_activo = "Activo"
col_benchmark_especifico = "Benchmark Específico"
col_benchmark_general = "Benchmark General"

# Listado de activos
activos = df[col_activo].dropna().unique()

# Diccionario Activo -> Benchmark Específico
benchmark_dict = dict(zip(df[col_activo], df[col_benchmark_especifico]))

# Diccionario Activo -> Benchmark General
benchmark_general_dict = dict(zip(df[col_activo], df[col_benchmark_general]))

# Selección múltiple de activos
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

# Ingreso de datos por cada activo seleccionado
for activo in activos_seleccionados:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"**Activo:** {activo}")
        st.text_input("Benchmark", benchmark_dict.get(activo, "N/A"), disabled=True, key=f"bench_{activo}")
    with col2:
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col3:
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")

    total = nominal * precio
    resumen.append({
        "Activo": activo,
        "Nominal": nominal,
        "Precio": precio,
        "Total": total,
        "Benchmark": benchmark_dict.get(activo, "N/A"),
        "Benchmark General": benchmark_general_dict.get(activo, "N/A")
    })

# Crear DataFrame con resumen
resumen_df = pd.DataFrame(resumen)

# Calcular ponderación y mostrar tabla
if not resumen_df.empty:
    total_general = resumen_df["Total"].sum()
    resumen_df["Ponderación"] = resumen_df["Total"] / total_general * 100

    st.subheader("📋 Resumen calculado")
    st.dataframe(resumen_df[["Activo", "Nominal", "Precio", "Total", "Ponderación", "Benchmark"]], use_container_width=True)

    st.markdown(f"### 🪙 Total final: ${total_general:,.2f}")
else:
    st.info("No hay activos seleccionados o datos ingresados.")
    total_general = 0.0

# Función para crear PDF en formato horizontal
def crear_pdf(df):
    pdf = FPDF(orientation='L')  # L = Landscape (horizontal)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align='C')
    pdf.ln(10)

    # Encabezados
    pdf.set_font("Arial", "B", 12)
    columnas = ["Activo", "Benchmark", "Nominal", "Precio", "Total", "Ponderación (%)"]
    col_widths = [90, 60, 30, 30, 35, 35]

    for i, col in enumerate(columnas):
        pdf.cell(col_widths[i], 10, col, border=1, align='C')
    pdf.ln()

    # Datos
    pdf.set_font("Arial", "", 11)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 10, str(row["Activo"])[:60], border=1)
        pdf.cell(col_widths[1], 10, str(row["Benchmark"])[:35], border=1)
        pdf.cell(col_widths[2], 10, f"{row['Nominal']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[3], 10, f"${row['Precio']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[4], 10, f"${row['Total']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[5], 10, f"{row['Ponderación']:.2f}%", border=1, align='R')
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Total general: ${df['Total'].sum():,.2f}", ln=True, align='R')

    # Benchmarks Generales
    benchmarks_generales = df["Benchmark General"].dropna().unique()
    if len(benchmarks_generales) == 1:
        pdf.cell(0, 10, f"Benchmark General: {benchmarks_generales[0]}", ln=True)
    elif len(benchmarks_generales) > 1:
        pdf.cell(0, 10, f"Benchmarks Generales: {', '.join(benchmarks_generales)}", ln=True)

    pdf_str = pdf.output(name='', dest='S')
    pdf_bytes = pdf_str.encode('latin1')
    return BytesIO(pdf_bytes)

# Botón para descargar PDF
if not resumen_df.empty:
    pdf_data = crear_pdf(resumen_df)
    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_data,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
