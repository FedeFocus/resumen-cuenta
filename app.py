import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Cargar los datos
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")

# Selección de activos
activos_disponibles = df['Activo'].dropna().unique().tolist()
activos_seleccionados = st.multiselect("Seleccioná los activos del cliente:", activos_disponibles)

resumen = []

if activos_seleccionados:
    for activo in activos_seleccionados:
        col1, col2, col3 = st.columns(3)
        with col1:
            nominal = st.number_input(f"Nominal de {activo}", min_value=0.0, step=1.0)
        with col2:
            precio = st.number_input(f"Precio de {activo}", min_value=0.0, step=0.01)
        with col3:
            total = nominal * precio
            st.write(f"**Total:** {total:,.2f}")
        
        resumen.append({
            "Activo": activo,
            "Nominal": nominal,
            "Precio": precio,
            "Total": total
        })

    resumen_df = pd.DataFrame(resumen)
    st.subheader("Resumen del Cliente")
    st.dataframe(resumen_df)

    # Generar PDF
    def crear_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, "Resumen de Cuenta", ln=True, align='C')
        pdf.ln(10)

        # Encabezado
        pdf.set_font("Arial", "B", size=10)
        for col in df.columns:
            pdf.cell(40, 10, str(col), border=1)
        pdf.ln()

        # Filas
        pdf.set_font("Arial", size=10)
        for _, row in df.iterrows():
            for item in row:
                pdf.cell(40, 10, str(round(item, 2)) if isinstance(item, float) else str(item), border=1)
            pdf.ln()

        buffer = BytesIO()
        pdf.output(buffer, dest='F')
        buffer.seek(0)
        return buffer

    pdf_data = crear_pdf(resumen_df)

    st.download_button(
        label="📄 Descargar resumen en PDF",
        data=pdf_data,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )

else:
    st.info("Seleccioná al menos un activo para generar el resumen.")
