import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

st.set_page_config(layout="wide")
st.title("Resumen de Cuenta PDF")

# Cargar Excel desde GitHub (reemplazá esta URL por la tuya si cambia)
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
df_raw = pd.read_excel(url_excel)

# Selección manual de activos
activos_disponibles = df_raw["Activo"].dropna().unique()
activos_seleccionados = st.multiselect("Seleccionar activos a incluir:", activos_disponibles)

# Filtrar base
df = df_raw[df_raw["Activo"].isin(activos_seleccionados)].copy()

if not df.empty:
    # Ingresar valores manuales
    st.markdown("### Ingresar datos por activo")

    for i, fila in df.iterrows():
        df.at[i, "Nominal"] = st.number_input(f"Nominal - {fila['Activo']}", value=0.0, key=f"nom_{i}")
        if fila["Moneda"] == "ARS":
            df.at[i, "Precio"] = st.number_input(f"Precio ARS - {fila['Activo']}", value=0.0, key=f"pr_ars_{i}")
        else:
            df.at[i, "Precio"] = st.number_input(f"Precio USD - {fila['Activo']}", value=0.0, key=f"pr_usd_{i}")

    tipo_cambio = st.number_input("Tipo de cambio ARS/USD", value=100.0)

    # Calcular Monto en USD según moneda
    def calcular_monto(row):
        if row["Moneda"] == "ARS":
            return (row["Nominal"] * row["Precio"]) / tipo_cambio
        else:
            return row["Nominal"] * row["Precio"]

    df["Monto USD"] = df.apply(calcular_monto, axis=1)
    total_general = df["Monto USD"].sum()
    df["Ponderación"] = df["Monto USD"] / total_general

    # Calcular totales por tipo de activo
    resumen = df.groupby("Tipo de Activo").agg({
        "Monto USD": "sum"
    }).rename(columns={"Monto USD": "Total por Tipo"}).reset_index()
    resumen["Ponderación Tipo"] = resumen["Total por Tipo"] / total_general

    # Merge para agregar las columnas de totales por tipo de activo a cada fila
    df = df.merge(resumen, on="Tipo de Activo", how="left")

    # Crear PDF
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")
    pdf.ln(5)

    # Encabezados
    headers = [
        "Activo", "Nominal", "Precio", "Monto USD", "Ponderación",
        "Total por Tipo", "Pond. Tipo", "Benchmark Específico", "Benchmark General"
    ]
    col_widths = [60, 20, 20, 25, 25, 25, 25, 50, 50]

    pdf.set_font("Arial", "B", 9)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, border=1, align="C")
    pdf.ln()

    # Filas
    pdf.set_font("Arial", "", 8)
    for _, row in df.iterrows():
        valores = [
            str(row["Activo"]),
            f'{row["Nominal"]:,.0f}',
            f'{row["Precio"]:,.2f}',
            f'{row["Monto USD"]:,.2f}',
            f'{row["Ponderación"]:.2%}',
            f'{row["Total por Tipo"]:,.2f}',
            f'{row["Ponderación Tipo"]:.2%}',
            str(row["Benchamark Específico"]),
            str(row["Benchmark General"]),
        ]
        for valor, width in zip(valores, col_widths):
            pdf.cell(width, 8, valor, border=1)
        pdf.ln()

    # Descargar PDF
    pdf_output = BytesIO()
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)

    st.download_button(
        "📄 Descargar PDF",
        data=pdf_output.getvalue(),
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
else:
    st.warning("Seleccioná al menos un activo para continuar.")
