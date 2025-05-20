import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# Cargar los datos desde el archivo Excel
@st.cache_data
def cargar_datos():
    return pd.read_excel("BD.xlsx", header=None)

df = cargar_datos()

# Detectar filas con nombre de tipo de activo (solo una celda no vacía)
df['Tipo de Activo'] = None
current_type = None
for idx, row in df.iterrows():
    non_empty = row.notna().sum()
    if non_empty == 1:
        current_type = row[row.notna()].values[0]
    df.at[idx, 'Tipo de Activo'] = current_type

# Eliminar filas que son cabeceras de grupo (solo una celda no vacía)
df = df[df.apply(lambda x: x.notna().sum(), axis=1) > 1].reset_index(drop=True)

# Renombrar columnas
columnas = ["Activo", "Ticker", "Moneda", "Benchmark Específico", "Benchmark General", "Tipo de Activo"]
df.columns = columnas

st.title("Resumen de Cuenta de Activos")

# Ingreso manual de tipo de cambio
tipo_cambio = st.number_input("Ingresar tipo de cambio para activos en ARS:", min_value=0.01, step=0.01, format="%.2f")

# Listado de activos seleccionables
activos = df['Activo'].dropna().unique()
activos_seleccionados = st.multiselect("Seleccionar activos del cliente", activos)

resumen = []

for activo in activos_seleccionados:
    fila = df[df['Activo'] == activo].iloc[0]
    moneda = fila['Moneda']
    tipo_activo = fila['Tipo de Activo']
    benchmark_esp = fila['Benchmark Específico']
    benchmark_gen = fila['Benchmark General']

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.write(f"**Activo:** {activo}")
    with col2:
        nominal = st.number_input(f"Nominal para {activo}", min_value=0.0, step=1.0, format="%.2f", key=f"nom_{activo}")
    with col3:
        precio = st.number_input(f"Precio para {activo}", min_value=0.0, step=0.01, format="%.2f", key=f"pre_{activo}")

    if moneda == "ARS":
        total_usd = nominal / tipo_cambio if tipo_cambio else 0
    else:
        total_usd = nominal * precio

    resumen.append({
        "Activo": activo,
        "Tipo de Activo": tipo_activo,
        "Nominal": nominal,
        "Precio": precio,
        "Monto USD": total_usd,
        "Benchmark Específico": benchmark_esp,
        "Benchmark General": benchmark_gen
    })

# Crear DataFrame del resumen
resumen_df = pd.DataFrame(resumen)

if not resumen_df.empty:
    total_general = resumen_df['Monto USD'].sum()
    resumen_df['Pond. Activo (%)'] = resumen_df['Monto USD'] / total_general * 100

    # Totales por tipo de activo
    resumen_con_totales = []
    for tipo, grupo in resumen_df.groupby("Tipo de Activo"):
        subtotal = grupo['Monto USD'].sum()
        pond_tipo = subtotal / total_general * 100

        for _, row in grupo.iterrows():
            resumen_con_totales.append(row)

        resumen_con_totales.append({
            "Activo": f"TOTAL {tipo}",
            "Tipo de Activo": tipo,
            "Nominal": "",
            "Precio": "",
            "Monto USD": subtotal,
            "Pond. Activo (%)": pond_tipo,
            "Benchmark Específico": "",
            "Benchmark General": ""
        })

    resumen_final = pd.DataFrame(resumen_con_totales)

    # Mostrar tabla en pantalla
    st.dataframe(resumen_final, use_container_width=True)

    # Exportar a PDF en horizontal
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            self.cell(0, 10, "Resumen de Cuenta", ln=True, align='C')
            self.ln(5)

    def crear_pdf(data):
        pdf = PDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", "B", 10)

        columnas = ["Activo", "Nominal", "Precio", "Monto USD", "Pond. Activo (%)", "Benchmark Específico", "Benchmark General"]
        col_widths = [60, 30, 25, 30, 35, 50, 50]

        for i, col in enumerate(columnas):
            pdf.cell(col_widths[i], 10, col, border=1, align='C')
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        for _, row in data.iterrows():
            pdf.cell(col_widths[0], 8, str(row["Activo"])[0:40], border=1)
            pdf.cell(col_widths[1], 8, str(row["Nominal"]) if row["Nominal"] != "" else "", border=1, align='R')
            pdf.cell(col_widths[2], 8, str(row["Precio"]) if row["Precio"] != "" else "", border=1, align='R')
            pdf.cell(col_widths[3], 8, f"{row['Monto USD']:,.2f}" if row["Monto USD"] != "" else "", border=1, align='R')
            pdf.cell(col_widths[4], 8, f"{row['Pond. Activo (%)']:.2f}%" if row["Pond. Activo (%)"] != "" else "", border=1, align='R')
            pdf.cell(col_widths[5], 8, str(row["Benchmark Específico"])[0:30], border=1)
            pdf.cell(col_widths[6], 8, str(row["Benchmark General"])[0:30], border=1)
            pdf.ln()

        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"Total de la cartera: USD {total_general:,.2f}", ln=True, align='R')

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return BytesIO(pdf_bytes)

    pdf_file = crear_pdf(resumen_final)

    st.download_button(
        label="📄 Descargar PDF",
        data=pdf_file,
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )

else:
    st.warning("No se seleccionaron activos o falta completar los datos.")

