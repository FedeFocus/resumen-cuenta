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

# Selección múltiple de activos
activos = df.iloc[:, 0].dropna().unique()
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

# Ingreso de datos por cada activo seleccionado
for activo in activos_seleccionados:
    col1, col2 = st.columns(2)
    with col1:
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col2:
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")
    
    total = nominal * precio
    resumen.append({
        "Activo": activo,
        "Nominal": nominal,
        "Precio": precio,
        "Total": total
    })

# Crear DataFrame con resumen
resumen_df = pd.DataFrame(resumen)

# Mostrar el resumen
st.subheader("📋 Resumen calculado")
st.dataframe(resumen_df, use_container_width=True)

total_general = resumen_df["Total"].sum()
st.markdown(f"### 🪙 Total final: ${total_general:,.2f}")

# Función para generar PDF
def crear_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Resumen de Cuenta", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    columnas = ["Activo", "Nominal", "Precio", "Total"]
    for col in columnas:
        pdf.cell(45, 10, col, border=1)
    pdf.ln()

    pdf.set_font("Arial", "", 11)
    for _, row in df.iterrows():
        pdf.cell(45, 10, str(row["Activo"])[:25], border=1)
        pdf.cell(45, 10, f"{row['Nominal']:,.2f}", border=1)
        pdf.cell(45, 10, f"${row['Precio']:,.2f}", border=1)
        pdf.cell(45, 10, f"${row['Total']:,.2f}", border=1)
        pdf.ln()

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, f"Total general: ${df['Total'].sum():,.2f}", ln=True)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
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
