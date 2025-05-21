import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from fpdf import FPDF

st.set_page_config(layout="centered")
st.title("📄 Resumen de Cuenta en PDF")

# 1️⃣ URL del Excel en GitHub (raw)
excel_url = st.text_input(
    "URL del Excel en GitHub (Raw)",
    "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
)

# 2️⃣ Tipo de cambio
tc_str = st.text_input("Tipo de cambio ARS/USD", value="1000,00")
try:
    tipo_cambio = float(tc_str.replace(".", "").replace(",", "."))
except ValueError:
    st.error("Ingresá un tipo de cambio válido (ej.: 1000,00).")
    st.stop()

# 3️⃣ Descargar y leer el Excel
try:
    resp = requests.get(excel_url)
    resp.raise_for_status()
    buffer = BytesIO(resp.content)
    buffer.seek(0)
    df = pd.read_excel(buffer, engine="openpyxl")
except Exception as e:
    st.error(f"No se pudo leer el Excel: {e}")
    st.stop()

# 4️⃣ Seleccionar activos
activos = df["Activo"].dropna().tolist()
seleccionados = st.multiselect("Seleccioná los activos a cargar", activos)
if not seleccionados:
    st.info("Elegí al menos un activo para continuar.")
    st.stop()

df = df[df["Activo"].isin(seleccionados)].copy()

# 5️⃣ Ingresar Nominal y Precio
st.subheader("Ingresar valores nominales y precios")
for i, fila in df.iterrows():
    col1, col2 = st.columns(2)
    with col1:
        df.at[i, "Nominal"] = st.number_input(f"Nominal - {fila['Activo']}", key=f"nom_{i}", min_value=0.0)
    with col2:
        df.at[i, "Precio"] = st.number_input(f"Precio - {fila['Activo']}", key=f"pre_{i}", min_value=0.0)

# 6️⃣ Calcular monto USD y ponderaciones
def monto_usd(row):
    if row["Moneda"] == "ARS":
        return row["Nominal"] * row["Precio"] / tipo_cambio
    return row["Nominal"] * row["Precio"]

df["Monto USD"] = df.apply(monto_usd, axis=1)
total = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total

# 7️⃣ Armar resumen con totales por tipo
resumen = []
for tipo, grupo in df.groupby("Tipo de Activo"):
    resumen.extend(grupo.to_dict("records"))
    subtotal = grupo["Monto USD"].sum()
    resumen.append({
        "Activo": f"TOTAL {tipo.upper()}",
        "Nominal": "",
        "Precio": "",
        "Monto USD": subtotal,
        "Ponderación": subtotal / total,
        "Benchmark Específico": "",
        "Benchmark General": ""
    })

# 8️⃣ Generar PDF
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", "B", 14)
pdf.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

headers = ["Activo", "Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]
widths  = [60, 25, 25, 30, 30, 45, 45]

pdf.set_font("Arial", "B", 10)
for h, w in zip(headers, widths):
    pdf.cell(w, 8, h, border=1, align="C")
pdf.ln()

pdf.set_font("Arial", "", 9)
for r in resumen:
    for h, w in zip(headers, widths):
        val = r.get(h, "")
        if isinstance(val, float):
            val = f"{val:,.2f}" if "Ponderación" not in h else f"{val:.2%}"
        pdf.cell(w, 8, str(val), border=1, align="R" if isinstance(r.get(h, ""), float) else "L")
    pdf.ln()

# 9️⃣ Preparar descarga
pdf_bytes = pdf.output(dest="S").encode("latin1")
pdf_buffer = BytesIO(pdf_bytes)

st.download_button(
    "📥 Descargar PDF",
    data=pdf_buffer,
    file_name="resumen_cuenta.pdf",
    mime="application/pdf"
)
