import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx")

def crear_pdf(resumen):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Resumen de Cuenta de Activos", ln=True, align='C')
    pdf.ln(10)
    
    # Cabeceras
    pdf.cell(50, 10, "Activo", 1)
    pdf.cell(40, 10, "Nominal", 1)
    pdf.cell(40, 10, "Precio", 1)
    pdf.cell(40, 10, "Total", 1)
    pdf.ln()
    
    for item in resumen:
        pdf.cell(50, 10, item["Activo"], 1)
        pdf.cell(40, 10, f"{item['Nominal']:.2f}", 1)
        pdf.cell(40, 10, f"{item['Precio']:.2f}", 1)
        pdf.cell(40, 10, f"{item['Total']:.2f}", 1)
        pdf.ln()
    
    valor_final = sum(item["Total"] for item in resumen)
    pdf.ln(10)
    pdf.cell(200, 10, f"Valor Final: {valor_final:.2f}", ln=True, align='R')
    
    output = BytesIO()
    pdf.output(output)
    return output.getvalue()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resumen')
    return output.getvalue()

# --- Código principal ---

df = cargar_datos()

st.title("Resumen de Cuenta de Activos")
st.write("Seleccioná los activos que querés incluir:")

activos_seleccionados = st.multiselect("Seleccionar activos", options=df['Activo'].unique())

if activos_seleccionados:
    st.subheader("Ingresá nominales y precios para los activos seleccionados")

    resumen = []

    for i, activo in enumerate(activos_seleccionados):
        st.write(f"### Activo: {activo}")
        
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, format="%.2f", key=f"nominal_{i}")
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, format="%.2f", key=f"precio_{i}")
        
        total = nominal * precio
        st.write(f"Valor total para {activo}: {total:.2f}")
        
        resumen.append({
            "Activo": activo,
            "Nominal": nominal,
            "Precio": precio,
            "Total": total
        })

    valor_final = sum(item["Total"] for item in resumen)
    st.markdown(f"## Valor Final del Resumen de Cuenta: **{valor_final:.2f}**")

    df_resumen = pd.DataFrame(resumen)

    excel_data = to_excel(df_resumen)
    pdf_data = crear_pdf(resumen)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Descargar resumen en Excel",
            data=excel_data,
            file_name="resumen_cuenta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    with col2:
        st.download_button(
            label="📥 Descargar resumen en PDF",
            data=pdf_data,
            file_name="resumen_cuenta.pdf",
            mime="application/pdf"
        )

else:
    st.write("No hay activos seleccionados.")
