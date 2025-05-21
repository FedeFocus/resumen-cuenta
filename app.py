import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from fpdf import FPDF

st.set_page_config(layout="centered")
st.title("Resumen de Cuenta en PDF")

# Entrada: URL del Excel
excel_url = st.text_input("📄 URL del Excel en GitHub (Raw)", 
    value="https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx")

# Entrada: tipo de cambio
tipo_cambio_str = st.text_input("💱 Tipo de cambio ARS/USD", value="1000,00")

try:
    tipo_cambio = float(tipo_cambio_str.replace(".", "").replace(",", "."))
except:
    st.error("Ingresá un tipo de cambio válido (por ejemplo: 1000,00)")
    st.stop()

# Descargar Excel desde GitHub
try:
    response = requests.get(excel_url)
    response.raise_for_status()
    excel_file = BytesIO(response.content)
    excel_file.seek(0)  # necesario para evitar error BytesIO
    df = pd.read_excel(excel_file)
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
    st.stop()

# Selección manual de activos
activos_disponibles = df["Activo"].dropna().tolist()
activos_seleccionados = st.multiselect("📌 Seleccioná los activos a incluir", activos_disponibles)

if not activos_seleccionados:
    st.stop()

# Filtrar el DataFrame
df = df[df["Activo"].isin(activos_seleccionados)].copy()

# Entradas manuales para cada activo
for i, row in df.iterrows():
    nominal = st.number_input(f"Valores nominales - {row['Activo']}", value=0.0, key=f"nominal_{i}")
    precio = st.number_input(f"Precio (USD o ARS) - {row['Activo']}", value=0.0, key=f"precio_{i}")
    df.at[i, "Nominal"] = nominal
    df.at[i, "Precio"] = precio

# Calcular monto en USD según moneda
def calcular_monto(row):
    if row["Moneda"] == "ARS":
        return (row["Nominal"] * row["Precio"]) / tipo_cambio
    else:
        return row["Nominal"] * row["Precio"]

df["Monto USD"] = df.apply(calcular_monto, axis=1)
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Agrupar por tipo de activo
resumen = []
for tipo, grupo in df.groupby("Tipo de Activo"):
    subtotal = grupo["Monto USD"].sum()
    subponderacion = subtotal / total_general

    resumen.extend(grupo.to_dict(orient="records"))

    resumen.append({
        "Activo": f"TOTAL {tipo}",
        "Nominal": "",
        "Precio": "",
        "Monto USD": subtotal,
        "Ponderación": subponderacion,
        "Benchmark Específico": "",
        "Benchmark General": "",
        "Tipo de Activo": tipo
    })

# Crear PDF horizontal
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", "B", 14)
pdf.cell(0, 10, "Resumen de Cuenta", ln=True)

# Encabezado de tabla
pdf.set_font("Arial", "B", 10)
columnas = ["Activo", "Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]
anchos = [60, 25, 20, 30, 30, 40, 40]

for col, w in zip(columnas, anchos):
    pdf.cell(w, 10, col, 1)
pdf.ln()

# Cuerpo de tabla
pdf.set_font("Arial", "", 9)
for row in resumen:
    for col, w in zip(columnas, anchos):
        val = row.get(col, "")
        if isinstance(val, float):
            if "Ponderación" in col:
                val = f"{val:.2%}"
            else:
                val = f"{val:,.2f}"
        pdf.cell(w, 8, str(val), 1)
    pdf.ln()

# Descargar PDF
pdf_output = BytesIO()
pdf.output(pdf_output)
pdf_output.seek(0)

st.download_button("📥 Descargar PDF", data=pdf_output, file_name="resumen_cuenta.pdf", mime="application/pdf")
