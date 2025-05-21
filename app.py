import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# === CARGAR BASE DE DATOS DESDE GITHUB ===
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
df_base = pd.read_excel(url_excel)

# === FILTRAR ACTIVOS A UTILIZAR ===
activos_filtrados = st.multiselect("Seleccionar activos a incluir", options=df_base["Activo"])
df = df_base[df_base["Activo"].isin(activos_filtrados)].copy()

# === INGRESO DE DATOS MANUAL ===
st.write("Ingresar valores nominales y precios:")
for i, row in df.iterrows():
    df.at[i, "Nominal"] = st.number_input(f"Nominal - {row['Activo']}", min_value=0.0, step=1.0, key=f"nominal_{i}")
    df.at[i, "Precio"] = st.number_input(f"Precio - {row['Activo']}", min_value=0.0, step=0.01, key=f"precio_{i}")

# === TIPO DE CAMBIO MANUAL ===
tipo_cambio = st.number_input("Tipo de cambio (USD/ARS)", min_value=0.1, step=0.1)

# === CÁLCULOS ===
def calcular_monto_usd(row):
    if row["Moneda"] == "ARS":
        return (row["Nominal"] * row["Precio"]) / tipo_cambio
    elif row["Moneda"] == "USD":
        return row["Nominal"] * row["Precio"]
    return 0

df["Monto USD"] = df.apply(calcular_monto_usd, axis=1)
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# === TOTALES POR TIPO DE ACTIVO ===
totales = df.groupby("Tipo de Activo")["Monto USD"].sum().reset_index()
totales["Ponderación"] = totales["Monto USD"] / total_general

# === PDF GENERACIÓN ===
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", border=False, ln=True, align="C")
        self.ln(5)

    def tabla(self, df, totales):
        self.set_font("Arial", "", 8)
        col_widths = [50, 20, 20, 25, 25, 30, 30, 30, 30]
        headers = ["Activo", "Nominal", "Precio", "Monto USD", "% Activo", "Tipo Activo", "% Tipo", "B. Específico", "B. General"]
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, border=1)
        self.ln()
        for _, row in df.iterrows():
            tipo = row["Tipo de Activo"]
            total_tipo = totales[totales["Tipo de Activo"] == tipo]["Monto USD"].values[0]
            porcentaje_tipo = totales[totales["Tipo de Activo"] == tipo]["Ponderación"].values[0]
            values = [
                str(row["Activo"]),
                f'{row["Nominal"]:.2f}',
                f'{row["Precio"]:.2f}',
                f'{row["Monto USD"]:.2f}',
                f'{row["Ponderación"]*100:.2f}%',
                tipo,
                f'{porcentaje_tipo*100:.2f}%',
                row["Benchmark Específico"],
                row["Benchmark General"]
            ]
            for i, val in enumerate(values):
                self.cell(col_widths[i], 8, str(val), border=1)
            self.ln()

# === BOTÓN PARA GENERAR PDF ===
if st.button("Generar PDF"):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.tabla(df, totales)
    
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    st.download_button(
        label="Descargar PDF",
        data=pdf_output.getvalue(),
        file_name="resumen_cuenta.pdf",
        mime="application/pdf"
    )
