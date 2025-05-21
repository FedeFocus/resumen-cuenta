import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
import base64

# Leer base de datos
@st.cache_data
def cargar_base():
    return pd.read_excel("BD.xlsx")

df_base = cargar_base()

st.set_page_config(layout="wide")
st.title("Resumen de Cuenta")

# Filtro para seleccionar activos
activos_disponibles = df_base["Activo"].tolist()
activos_seleccionados = st.multiselect("Seleccioná los activos a incluir", activos_disponibles)

if not activos_seleccionados:
    st.warning("Seleccioná al menos un activo para continuar.")
    st.stop()

# Filtrar base según selección
df_filtrado = df_base[df_base["Activo"].isin(activos_seleccionados)].copy()

# Ingreso de tipo de cambio
tipo_cambio = st.number_input("Ingresá el tipo de cambio (USD/ARS)", min_value=0.01, step=0.01)

# Tabla para ingresar valores
st.subheader("Cargá los valores de la cartera")

valores_nominales = []
precios = []

for idx, row in df_filtrado.iterrows():
    col1, col2 = st.columns(2)
    with col1:
        nominal = st.number_input(f"{row['Activo']} - Nominal", key=f"nominal_{idx}", value=0.0)
    with col2:
        precio = st.number_input(f"{row['Activo']} - Precio", key=f"precio_{idx}", value=0.0)
    valores_nominales.append(nominal)
    precios.append(precio)

# Armar estructura con totales por tipo de activo
activos_data = []
total_general = 0
grupo_actual = None

for i, row in df_filtrado.iterrows():
    activo = row["Activo"]
    ticker = row["Ticker"]
    moneda = row["Moneda"]
    bench_esp = row["Benchmark Específico"]
    bench_gral = row["Benchmark General"]
    
    nominal = valores_nominales[i]
    precio = precios[i]

    if pd.isna(ticker) and pd.isna(moneda):
        grupo_actual = activo
        activos_data.append({
            "Activo": f"{grupo_actual}",
            "es_titulo": True
        })
        continue

    if moneda == "ARS":
        monto_usd = nominal / tipo_cambio if tipo_cambio else 0
    elif moneda == "USD":
        monto_usd = nominal * precio
    else:
        monto_usd = 0

    activos_data.append({
        "Tipo": grupo_actual,
        "Activo": activo,
        "Nominal": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "Benchmark Específico": bench_esp,
        "Benchmark General": bench_gral,
        "es_titulo": False
    })

# Convertir a DataFrame y verificar si hay activos seleccionados
resumen_df = pd.DataFrame([d for d in activos_data if not d.get("es_titulo")])

if resumen_df.empty:
    st.warning("Seleccioná al menos un activo para continuar.")
    st.stop()

# Calcular totales
total_general = resumen_df["Monto USD"].sum()
resumen_df["% del total"] = resumen_df["Monto USD"] / total_general * 100

# Insertar filas de totales por tipo
resumen_con_totales = []
for tipo, grupo in resumen_df.groupby("Tipo"):
    resumen_con_totales.append({
        "Activo": tipo,
        "es_titulo": True
    })
    resumen_con_totales.extend(grupo.to_dict(orient="records"))
    subtotal = grupo["Monto USD"].sum()
    resumen_con_totales.append({
        "Activo": f"TOTAL {tipo.upper()}",
        "Monto USD": subtotal,
        "% del total": subtotal / total_general * 100,
        "es_titulo": True
    })

# Generar PDF
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

    def tabla(self, data):
        self.set_font("Arial", "", 9)
        col_widths = [60, 25, 20, 30, 25, 35, 35]

        headers = ["Activo", "Nominal", "Precio", "Monto USD", "% del total", "Benchmark Específico", "Benchmark General"]
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1)
        self.ln()

        for row in data:
            if row.get("es_titulo"):
                self.set_font("Arial", "B", 9)
                self.cell(0, 8, row["Activo"], 1, ln=True)
                self.set_font("Arial", "", 9)
                continue
            self.cell(col_widths[0], 8, str(row["Activo"]), 1)
            self.cell(col_widths[1], 8, f"{row['Nominal']:.2f}", 1)
            self.cell(col_widths[2], 8, f"{row['Precio']:.2f}", 1)
            self.cell(col_widths[3], 8, f"{row['Monto USD']:.2f}", 1)
            self.cell(col_widths[4], 8, f"{row['% del total']:.2f}%", 1)
            self.cell(col_widths[5], 8, str(row["Benchmark Específico"]), 1)
            self.cell(col_widths[6], 8, str(row["Benchmark General"]), 1)
            self.ln()

pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.tabla(resumen_con_totales)

# Exportar PDF
pdf_output = BytesIO()
pdf.output(pdf_output)
b64_pdf = base64.b64encode(pdf_output.getvalue()).decode("utf-8")
st.download_button("Descargar PDF", data=pdf_output.getvalue(), file_name="resumen_cuenta.pdf", mime="application/pdf")
