# Archivo: app.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from io import BytesIO
from fpdf import FPDF
import base64

# --- CONFIGURACION DE LA PAGINA ---
st.set_page_config(page_title="Resumen de Cuenta", layout="wide")
st.title("Generador de Resumen de Cuenta - Focus IM")

# --- CARGAR EXCEL BASE ---
st.subheader("1. Cargar base de datos")
file = st.file_uploader("Subí el archivo Excel base", type=["xlsx"])

if file:
    df_base = pd.read_excel(file)

    # Identificamos los grupos por filas donde solo hay valor en columna 'Activo'
    df_base["Grupo"] = None
    current_group = None
    for i, row in df_base.iterrows():
        if pd.notna(row["Activo"]) and df_base.loc[i].drop("Activo").isna().all():
            current_group = row["Activo"]
        else:
            df_base.at[i, "Grupo"] = current_group

    df_activos = df_base[df_base["Ticker"].notna()].copy()

    # --- SELECCION DE ACTIVOS ---
    st.subheader("2. Seleccionar activos del cliente")
    activos_seleccionados = st.multiselect("Seleccioná los activos de la cartera del cliente", df_activos["Activo"].tolist())

    df_seleccion = df_activos[df_activos["Activo"].isin(activos_seleccionados)].copy()

    if not df_seleccion.empty:
        st.subheader("3. Completar datos de la cartera")

        tipo_cambio = st.number_input("Tipo de cambio (USD)", min_value=0.0, format="%.2f")
        nombre_cliente = st.text_input("Nombre del Comitente")
        fecha_resumen = st.date_input("Fecha del resumen", value=date.today())

        st.markdown("---")
        st.subheader("4. Ingresar nominales y precios")

        nominales = []
        precios = []
        montos = []

        for i, row in df_seleccion.iterrows():
            col1, col2 = st.columns(2)
            with col1:
                nom = st.number_input(f"Nominales - {row['Activo']}", min_value=0.0, key=f"nom_{i}")
            with col2:
                pre = st.number_input(f"Precio - {row['Activo']}", min_value=0.0, key=f"pre_{i}")

            nominales.append(nom)
            precios.append(pre)

            if row['Moneda'] == 'ARS':
                monto = nom / tipo_cambio
            else:
                monto = nom * pre

            montos.append(monto)

        df_seleccion['Nominales'] = nominales
        df_seleccion['Precio'] = precios
        df_seleccion['Monto'] = montos

        total_monto = sum(montos)
        df_seleccion['% Indiv.'] = df_seleccion['Monto'] / total_monto * 100

        # Calculo por grupo
        df_seleccion['Monto Grupal'] = df_seleccion.groupby('Grupo')['Monto'].transform('sum')
        df_seleccion['% Grupal'] = df_seleccion['Monto Grupal'] / total_monto * 100

        # --- PDF ---
        st.subheader("5. Generar PDF")

        def generar_pdf():
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page()

            pdf.image("focus_logo.png", x=10, y=8, w=30)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Comitente: {nombre_cliente}", ln=True)
            pdf.cell(0, 10, f"Fecha: {fecha_resumen.strftime('%d/%m/%Y')}", ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 10)
            col_widths = [65, 20, 20, 25, 25, 30, 25, 50, 40]
            headers = ["Activo", "Nominales", "Precio", "Monto", "% Indiv.", "Monto Grupal", "% Grupal", "Benchmark Específico", "Benchmark General"]
            aligns = ["L", "C", "C", "C", "C", "C", "C", "L", "C"]

            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 8, h, border=1, align=aligns[i])
            pdf.ln()

            pdf.set_font("Arial", '', 9)
            for _, row in df_seleccion.iterrows():
                values = [
                    str(row['Activo']),
                    f"{row['Nominales']:.2f}",
                    f"{row['Precio']:.2f}",
                    f"{row['Monto']:.2f}",
                    f"{row['% Indiv.']:.2f}%",
                    f"{row['Monto Grupal']:.2f}",
                    f"{row['% Grupal']:.2f}%",
                    str(row['Benchmark Específico']),
                    str(row['Benchmark General'])
                ]
                for i, v in enumerate(values):
                    pdf.cell(col_widths[i], 8, v, border=1, align=aligns[i])
                pdf.ln()

            # Totales
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(col_widths[0] + col_widths[1] + col_widths[2], 8, "TOTALES", border=1, align="R")
            pdf.cell(col_widths[3], 8, f"{total_monto:.2f}", border=1, align="C")
            pdf.cell(col_widths[4], 8, "100.00%", border=1, align="C")
            pdf.cell(col_widths[5], 8, f"{total_monto:.2f}", border=1, align="C")
            pdf.cell(col_widths[6], 8, "100.00%", border=1, align="C")
            pdf.cell(col_widths[7] + col_widths[8], 8, "", border=1)

            return pdf.output(dest='S').encode('latin-1')

        if st.button("Generar y descargar PDF"):
            pdf_bytes = generar_pdf()
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="Resumen_{nombre_cliente}.pdf">📥 Descargar PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

