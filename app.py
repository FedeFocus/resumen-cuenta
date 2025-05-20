import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# ------------------------
# 1. Cargar datos
# ------------------------
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

df = cargar_datos()

# ------------------------
# 2. Título y selección
# ------------------------
st.title("Resumen de Cuenta de Activos")

activos_disponibles = df['Activo'].dropna().unique()
activos_seleccionados = st.multiselect("Seleccionar activos", activos_disponibles)

# ------------------------
# 3. Cargar datos ingresados
# ------------------------
resumen = []

for activo in activos_seleccionados:
    col1, col2 = st.columns(2)
    with col1:
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, step=1.0, key=f"nominal_{activo}")
    with col2:
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, step=0.01, key=f"precio_{activo}")
    
    total = nominal * precio
    resumen.append({"Activo": activo, "Nominal": nominal, "Precio": precio, "Total": total})

# ------------------------
# 4. Mostrar resumen
# ------------------------
if resumen:
    resumen_df = pd.DataFrame(resumen)
    st.subheader("Resumen calculado")
    st.dataframe(resumen_df)

    total_final = resumen_df["Total"].sum()
    st.markdown(f"### 💰 Total final: ${total_final:,.2f}")

    # ------------------------
    # 5. Botón para descargar Excel
    # ------------------------
    def convertir_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Resumen')
        output.seek(0)
        return output

    st.download_button(
        label="⬇️ Descargar Excel",
        data=convertir_excel(resumen_df),
        file_name="resumen_cuenta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # ------------------------
    # 6. Botón para descargar PDF
    # ------------------------
    def crear_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Resumen de Cuenta", ln=True, align='C')
        pdf.ln(10)

        for index, row in df.iterrows():
            linea = f"{row['Activo']} - Nominal: {row['Nominal']}, Precio: {row['Precio']}, Total: ${row['Total']:,.2f}"
            pdf.cell(200, 10, txt=linea, ln=True)

        pdf.ln(10)
        total_general = df['Total'].sum()
        pdf.cell(200, 10, txt=f"Total general: ${total_general:,.2f}", ln=True)

        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    st.download_button(
        label="📄 Descargar PDF",
        data=crear_pdf(resumen_df),
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
