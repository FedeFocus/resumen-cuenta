import pandas as pd
import streamlit as st
from fpdf import FPDF

# Cargar archivo Excel
uploaded_file = st.file_uploader("Cargar archivo Excel", type=["xlsx"])
tipo_cambio = st.number_input("Ingresar tipo de cambio (USD)", min_value=0.0, format="%.2f")

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Propagar tipo de activo (rótulos como 'ONs', 'Soberanos', etc.)
    df['TipoActivo'] = df['Activo']
    df['TipoActivo'] = df['TipoActivo'].where(df['Moneda'].notna())  # Solo mantener si es fila real
    df['TipoActivo'] = df['TipoActivo'].ffill()

    # Filtrar solo filas con activos (donde hay moneda cargada)
    activos_df = df[df['Moneda'].isin(['ARS', 'USD'])].copy()

    # Calcular monto en USD
    def calcular_monto(row):
        if row['Moneda'] == 'ARS':
            return row['Nominal'] / tipo_cambio if tipo_cambio else 0
        elif row['Moneda'] == 'USD':
            return row['Nominal'] * row['Precio']
        return 0

    activos_df['Monto USD'] = activos_df.apply(calcular_monto, axis=1)

    # Calcular total y ponderaciones
    total_general = activos_df['Monto USD'].sum()
    activos_df['Ponderacion'] = activos_df['Monto USD'] / total_general * 100

    # Calcular totales por tipo de activo
    resumen_tipos = activos_df.groupby('TipoActivo').agg({
        'Monto USD': 'sum'
    }).reset_index()
    resumen_tipos['Ponderacion'] = resumen_tipos['Monto USD'] / total_general * 100

    # Crear PDF
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, 'Resumen de Cuenta', ln=True, align='C')
            self.ln(5)

    pdf = PDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Tabla de activos
    col_widths = [70, 35, 20, 25, 30, 25, 40, 40]
    headers = ['Activo', 'Benchmark Específico', 'Nominal', 'Precio', 'Monto USD', 'Pond. (%)', 'Benchmark General', 'Tipo de Activo']
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align='C')
    pdf.ln()

    for _, row in activos_df.iterrows():
        valores = [
            str(row['Activo']),
            str(row['Benchmark Especifico']),
            f"{row['Nominal']:.2f}",
            f"${row['Precio']:.2f}",
            f"${row['Monto USD']:.2f}",
            f"{row['Ponderacion']:.2f}%",
            str(row['Benchmark General']),
            str(row['TipoActivo'])
        ]
        for i, valor in enumerate(valores):
            pdf.cell(col_widths[i], 10, valor, border=1)
        pdf.ln()

    # Totales por tipo de activo
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Totales por tipo de activo:", ln=True)

    pdf.set_font("Arial", size=10)
    for _, row in resumen_tipos.iterrows():
        texto = f"{row['TipoActivo']}: ${row['Monto USD']:.2f} ({row['Ponderacion']:.2f}%)"
        pdf.cell(0, 10, texto, ln=True)

    # Total general
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, f"Total general: ${total_general:.2f}", ln=True)

    # Descargar PDF
    st.download_button(
        label="Descargar PDF",
        data=pdf.output(dest='S').encode('latin1'),
        file_name="resumen_cuenta.pdf",
        mime='application/pdf'
    )
