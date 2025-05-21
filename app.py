import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import requests

st.set_page_config(page_title="Resumen de Cuenta", layout="wide")
st.title("📄 Resumen de Cuenta en PDF")

# 📥 Ingreso de datos
url = st.text_input("📄 URL del Excel en GitHub (Raw)", "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")
tipo_cambio = st.text_input("💱 Tipo de cambio ARS/USD", value="1000,00")

# Reemplazar coma por punto y convertir a float
try:
    tipo_cambio = float(tipo_cambio.replace(",", "."))
except:
    st.error("⚠️ Tipo de cambio inválido.")
    st.stop()

# 📂 Cargar Excel desde URL Raw de GitHub
@st.cache_data
def cargar_base(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise ValueError("No se pudo descargar el archivo desde GitHub")
    content = BytesIO(response.content)
    return pd.read_excel(content, engine="openpyxl")

try:
    df = cargar_base(url)
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
    st.stop()

# Filtrar activos a incluir
activos_disponibles = df["Activo"].dropna().tolist()
seleccionados = st.multiselect("📌 Seleccioná los activos a incluir", activos_disponibles)

if not seleccionados:
    st.stop()

df = df[df["Activo"].isin(seleccionados)]

# 🧮 Ingreso de valores
valores_nominales = {}
precios = {}

st.subheader("🧾 Ingresá los valores para cada activo")

for activo in df["Activo"]:
    col1, col2 = st.columns(2)
    with col1:
        valores_nominales[activo] = st.number_input(f"Nominal de {activo}", min_value=0.0, step=1.0, key=f"nominal_{activo}")
    with col2:
        precios[activo] = st.number_input(f"Precio de {activo}", min_value=0.0, step=0.01, key=f"precio_{activo}")

# Calcular Monto USD
def calcular_monto(row):
    nominal = valores_nominales.get(row["Activo"], 0)
    precio = precios.get(row["Activo"], 0)
    if row["Moneda"] == "ARS":
        return (nominal * precio) / tipo_cambio
    else:
        return nominal * precio

df["Monto USD"] = df.apply(calcular_monto, axis=1)

# Ponderación individual
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Agregar totales por tipo de activo
resumen = []
for tipo, grupo in df.groupby("Tipo de Activo"):
    subtotal = grupo["Monto USD"].sum()
    ponderacion = subtotal / total_general
    resumen.append({
        "Activo": f"TOTAL {tipo.upper()}",
        "Monto USD": subtotal,
        "Ponderación": ponderacion,
        "Es total": True
    })
    resumen.extend(grupo.to_dict("records"))

df_final = pd.DataFrame(resumen)

# 🖨️ Generar PDF
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", 0, 1, "C")

    def tabla(self, data):
        self.set_font("Arial", "B", 9)
        col_widths = [60, 30, 30, 30, 50, 50]
        headers = ["Activo", "Nominal", "Precio", "Monto USD", "Benchmark Específico", "Benchmark General"]
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1)
        self.ln()

        self.set_font("Arial", "", 8)
        for row in data:
            if row.get("Es total"):
                self.set_font("Arial", "B", 9)
                self.set_fill_color(220, 220, 220)
            else:
                self.set_font("Arial", "", 8)
                self.set_fill_color(255, 255, 255)

            self.cell(col_widths[0], 8, str(row.get("Activo", "")), 1, fill=True)
            self.cell(col_widths[1], 8, "-", 1, fill=True)
            self.cell(col_widths[2], 8, "-", 1, fill=True)
            self.cell(col_widths[3], 8, f"{row.get('Monto USD', 0):,.2f}", 1, fill=True)
            self.cell(col_widths[4], 8, str(row.get("Benchmark Específico", "")), 1, fill=True)
            self.cell(col_widths[5], 8, str(row.get("Benchmark General", "")), 1, fill=True)
            self.ln()

pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.tabla(df_final.to_dict("records"))

pdf_output = BytesIO()
pdf.output(pdf_output)
pdf_output.seek(0)

st.download_button("📥 Descargar PDF", data=pdf_output, file_name="resumen_cuenta.pdf", mime="application/pdf")
