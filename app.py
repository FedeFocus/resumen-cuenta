import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Resumen de Cuenta en PDF")

# Ingresar URL del Excel en GitHub
url_excel = st.text_input("📄 URL del Excel en GitHub (Raw)", value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

# Ingresar tipo de cambio
tipo_cambio = st.number_input("💱 Tipo de cambio ARS/USD", value=1000.0)

try:
    df = pd.read_excel(url_excel)

    # Filtrar filas con datos válidos
    df = df[df["Activo"].notna()]

    # Selección manual de activos
    activos_disponibles = df["Activo"].tolist()
    activos_seleccionados = st.multiselect("📌 Seleccioná los activos a incluir", activos_disponibles)

    df = df[df["Activo"].isin(activos_seleccionados)].copy()

    # Ingreso manual de valores
    for idx, row in df.iterrows():
        col1, col2 = st.columns(2)
        with col1:
            df.at[idx, "Valores Nominales"] = st.number_input(f'Nominales de {row["Activo"]}', key=f'nom_{idx}', value=0.0)
        with col2:
            df.at[idx, "Precio"] = st.number_input(f'Precio de {row["Activo"]}', key=f'precio_{idx}', value=0.0)

    # Calcular Monto USD (versión segura)
    def calcular_monto(row):
        try:
            nominal = float(row.get("Valores Nominales", 0) or 0)
            precio = float(row.get("Precio", 0) or 0)
            moneda = str(row.get("Moneda", "")).strip().upper()

            if moneda == "ARS":
                return nominal * precio / tipo_cambio if tipo_cambio != 0 else 0
            elif moneda == "USD":
                return nominal * precio
            else:
                return 0
        except:
            return 0

    df["Monto USD"] = df.apply(calcular_monto, axis=1).astype(float)

    # Cálculo de ponderaciones
    total_general = df["Monto USD"].sum()
    df["Ponderación"] = df["Monto USD"] / total_general

    # Agrupar por tipo de activo
    resumen = df.groupby("Tipo de Activo")[["Monto USD"]].sum().rename(columns={"Monto USD": "Total x Tipo"})
    resumen["Ponderación x Tipo"] = resumen["Total x Tipo"] / total_general
    df = df.merge(resumen, on="Tipo de Activo", how="left")

    # PDF
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 12)
            self.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

    pdf = PDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", "", 9)

    column_names = ["Activo", "Valores Nominales", "Precio", "Monto USD", "Ponderación",
                    "Total x Tipo", "Ponderación x Tipo", "Benchmark Específico", "Benchmark General"]

    col_widths = [60, 30, 20, 30, 25, 30, 30, 40, 40]

    for i, col in enumerate(column_names):
        pdf.cell(col_widths[i], 10, col, border=1)

    pdf.ln()

    for _, row in df.iterrows():
        values = [
            row["Activo"],
            f'{row["Valores Nominales"]:,.2f}',
            f'{row["Precio"]:,.2f}',
            f'{row["Monto USD"]:,.2f}',
            f'{row["Ponderación"]:.2%}',
            f'{row["Total x Tipo"]:,.2f}',
            f'{row["Ponderación x Tipo"]:.2%}',
            row["Benchmark Específico"],
            row["Benchmark General"],
        ]
        for i, val in enumerate(values):
            pdf.cell(col_widths[i], 10, str(val), border=1)
        pdf.ln()

    # Descargar PDF
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    st.download_button("📥 Descargar PDF", data=pdf_output, file_name="resumen_cuenta.pdf")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
