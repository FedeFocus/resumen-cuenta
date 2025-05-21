import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from fpdf import FPDF

st.set_page_config(layout="wide")

st.title("Resumen de Cuenta en PDF")

# Tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", min_value=0.0, format="%.2f")

# URL del archivo Excel en GitHub
default_url = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
mostrar_url = st.toggle("¿Usar otra URL de Excel?", value=False)
if mostrar_url:
    excel_url = st.text_input("📄 URL del Excel en GitHub (Raw)", value=default_url)
else:
    excel_url = default_url

# Descargar archivo
try:
    response = requests.get(excel_url)
    df = pd.read_excel(BytesIO(response.content))

    # Filtrar activos a incluir
    st.markdown("### 📌 Seleccioná los activos a incluir")
    activos_seleccionados = st.multiselect(
        "Elegí los activos que querés incluir", df["Activo"].dropna().unique()
    )

    if activos_seleccionados:
        df = df[df["Activo"].isin(activos_seleccionados)].copy()

        st.markdown("### ✏️ Ingresá valores para cada activo")
        nominales = []
        precios = []

        for i, row in df.iterrows():
            st.markdown(f"**{row['Activo']} ({row['Moneda']})**")
            nominal = st.number_input(f"Nominal de {row['Activo']}", key=f"nominal_{i}", value=0.0)
            nominales.append(nominal)

            if row["Moneda"] == "USD":
                precio = st.number_input(f"Precio de {row['Activo']}", key=f"precio_{i}", value=0.0)
            else:
                precio = None
            precios.append(precio)

        df["Nominal"] = nominales
        df["Precio"] = precios

        # Calcular Monto USD
        def calcular_monto(row):
            if row["Moneda"] == "USD":
                return row["Nominal"] * (row["Precio"] or 0)
            else:
                return row["Nominal"] / tipo_cambio if tipo_cambio else 0

        df["Monto USD"] = df.apply(calcular_monto, axis=1)

        total_general = df["Monto USD"].sum()
        df["Ponderación"] = df["Monto USD"] / total_general

        # Calcular totales por tipo de activo
        resumen_tipo = df.groupby("Tipo de Activo").agg({
            "Monto USD": "sum"
        }).rename(columns={"Monto USD": "Total x Tipo"}).reset_index()

        resumen_tipo["Ponderación x Tipo"] = resumen_tipo["Total x Tipo"] / total_general

        # Unir totales al DataFrame original
        df = pd.merge(df, resumen_tipo, on="Tipo de Activo", how="left")

        # Generar PDF
        if st.button("📤 Exportar resumen a PDF"):
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

            pdf.set_font("Arial", "B", 10)
            col_widths = [60, 22, 18, 25, 22, 25, 30, 35, 35]
            headers = [
                "Activo", "Nominal", "Precio", "Monto USD", "Ponderación",
                "Total x Tipo", "Pond. x Tipo", "Benchmark Esp.", "Benchmark Gral."
            ]
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, border=1)
            pdf.ln()

            pdf.set_font("Arial", "", 8)
            for _, row in df.iterrows():
                pdf.cell(col_widths[0], 8, str(row["Activo"]), border=1)
                pdf.cell(col_widths[1], 8, f"{row['Nominal']:.2f}", border=1, align="R")
                pdf.cell(col_widths[2], 8, f"{row['Precio']:.2f}" if row["Moneda"] == "USD" else "-", border=1, align="R")
                pdf.cell(col_widths[3], 8, f"{row['Monto USD']:.2f}", border=1, align="R")
                pdf.cell(col_widths[4], 8, f"{row['Ponderación']:.2%}", border=1, align="R")
                pdf.cell(col_widths[5], 8, f"{row['Total x Tipo']:.2f}", border=1, align="R")
                pdf.cell(col_widths[6], 8, f"{row['Ponderación x Tipo']:.2%}", border=1, align="R")
                pdf.cell(col_widths[7], 8, str(row["Benchmark Específico"]), border=1)
                pdf.cell(col_widths[8], 8, str(row["Benchmark General"]), border=1)
                pdf.ln()

            pdf_output = BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)

            st.download_button(
                label="📥 Descargar PDF",
                data=pdf_output,
                file_name="resumen_cuenta.pdf",
                mime="application/pdf"
            )

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
