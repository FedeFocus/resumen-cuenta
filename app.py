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

# Mostrar estructura para validación
st.write("Vista previa de datos:")
st.dataframe(df.head())
st.write(f"Columnas: {list(df.columns)}")

# Columnas necesarias
col_activo = "Activo"
col_benchmark_esp = "Benchmark Específico"
col_benchmark_gen = "Benchmark General"
col_moneda = "Moneda"

# Ingreso manual del tipo de cambio
tipo_cambio = st.number_input("Tipo de cambio ARS/USD para convertir montos", min_value=0.0, step=0.01, format="%.2f")

# Lista de activos disponibles
activos = df[col_activo].dropna().unique()

# Diccionarios útiles
benchmark_esp_dict = dict(zip(df[col_activo], df[col_benchmark_esp]))
benchmark_gen_dict = dict(zip(df[col_activo], df[col_benchmark_gen]))
moneda_dict = dict(zip(df[col_activo], df[col_moneda]))

# Selección de activos
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

# Recolectar datos de cada activo
for activo in activos_seleccionados:
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"**Activo:** {activo}")
        st.text_input("Benchmark específico", benchmark_esp_dict.get(activo, "N/A"), disabled=True, key=f"bench_{activo}")
        st.text_input("Benchmark general", benchmark_gen_dict.get(activo, "N/A"), disabled=True, key=f"benchgen_{activo}")
    with col2:
        nominal = st.number_input(f"Nominal ({moneda_dict.get(activo, '')})", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col3:
        precio = st.number_input(f"Precio (USD)", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")

    # Calcular total en USD según moneda
    moneda = moneda_dict.get(activo, "").upper()
    if moneda == "ARS":
        total_usd = nominal / tipo_cambio if tipo_cambio > 0 else 0.0
    elif moneda == "USD":
        total_usd = nominal * precio
    else:
        total_usd = 0.0

    resumen.append({
        "Activo": activo,
        "Moneda": moneda,
        "Nominal": nominal,
        "Precio USD": precio,
        "Importe USD": total_usd,
        "Benchmark Específico": benchmark_esp_dict.get(activo, "N/A"),
        "Benchmark General": benchmark_gen_dict.get(activo, "N/A"),
    })

resumen_df = pd.DataFrame(resumen)

# Calcular ponderación
if not resumen_df.empty:
    total_general = resumen_df["Importe USD"].sum()
    resumen_df["Ponderación (%)"] = resumen_df["Importe USD"] / total_general * 100

    st.subheader("📋 Resumen calculado")
    st.dataframe(resumen_df, use_container_width=True)
    st.markdown(f"### 🪙 Total final en USD: ${total_general:,.2f}")
else:
    st.info("No hay activos seleccionados.")
    total_general = 0.0

# Crear PDF
def crear_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align='C')
    pdf.ln(10)

    # Cabecera de tabla
    pdf.set_font("Arial", "B", 11)
    columnas = ["Activo", "Moneda", "Nominal", "Precio USD", "Importe USD", "Ponderación (%)", "Benchmark Específico", "Benchmark General"]
    col_widths = [80, 20, 25, 25, 30, 30, 50, 50]

    for i, col in enumerate(columnas):
        pdf.cell(col_widths[i], 8, col, border=1, align='C')
    pdf.ln()

    # Filas
    pdf.set_font("Arial", "", 10)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 8, str(row["Activo"])[:60], border=1)
        pdf.cell(col_widths[1], 8, row["Moneda"], border=1, align='C')
        pdf.cell(col_widths[2], 8, f"{row['Nominal']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[3], 8, f"{row['Precio USD']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[4], 8, f"{row['Importe USD']:,.2f}", border=1, align='R')
        pdf.cell(col_widths[5], 8, f"{row['Ponderación (%)']:.2f}%", border=1, align='R')
        pdf.cell(col_widths[6], 8, str(row["Benchmark Específico"])[:35], border=1)
        pdf.cell(col_widths[7], 8, str(row["Benchmark General"])[:35], border=1)
        pdf.ln()

    pdf.set_font("Arial", "B", 11)
    pdf.ln(3)
    pdf.cell(0, 10, f"Total general en USD: ${df['Importe USD'].sum():,.2f}", ln=True, align='R')

    # Benchmarks Generales agregados abajo
    benchmarks_generales = df["Benchmark General"].dropna().unique()
    if len(benchmarks_generales) > 0:
        texto_bench = ", ".join(benchmarks_generales)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, f"Benchmarks Generales: {texto_bench}", ln=True)

    pdf_output = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_output)

# Botón para descargar PDF
if not resumen_df.empty:
    pdf_data = crear_pdf(resumen_df)
    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_data,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
