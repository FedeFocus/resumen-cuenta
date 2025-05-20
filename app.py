import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Cargar archivo Excel original
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")

# Seleccionar los activos que tiene el cliente
activos_disponibles = df['Activo'].dropna().unique().tolist()
activos_seleccionados = st.multiselect("Seleccioná los activos del cliente:", activos_disponibles)

resumen = []

if activos_seleccionados:
    for activo in activos_seleccionados:
        col1, col2, col3 = st.columns(3)
        with col1:
            nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, step=1.0, key=f"nominal_{activo}")
        with col2:
            precio = st.number_input(f"Precio para {activo}", min_value=0.0, step=0.01, key=f"precio_{activo}")
        with col3:
            total = nominal * precio
            st.markdown(f"**Total:** ${total:,.2f}")
        
        resumen.append({
            "Activo": activo,
            "Nominal": nominal,
            "Precio": precio,
            "Total": total
        })

    resumen_df = pd.DataFrame(resumen)
    st.subheader("📋 Resumen calculado")
    st.dataframe(resumen_df)

    total_final = resumen_df["Total"].sum()
    st.markdown(f"### 🪙 Total final: ${total_final:,.2f}")

    # 🔸 Crear PDF desde el resumen
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

        buffer = BytesIO()
        pdf.output(buffer, 'F')
        buffer.seek(0)
        return buffer

    pdf_data = crear_pdf(resumen_df)

    # 🔸 Botón de descarga del PDF
    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_data,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
else:
    st.info("Seleccioná uno o más activos para comenzar.")
