import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("Generador de Resumen de Cuenta")

# Ingreso del tipo de cambio
st.sidebar.subheader("Configuración")
tipo_cambio = st.sidebar.number_input("Tipo de cambio para activos en ARS", min_value=0.01, step=0.01, format="%.2f")

# Cargar Excel desde GitHub
url_excel = "https://github.com/FedeFocus/resumen-cuenta/raw/refs/heads/main/BD.xlsx"  # Reemplazar con tu URL real
df_raw = pd.read_excel(url_excel)
df_raw.dropna(how="all", inplace=True)

# Detectar grupos (tipos de activos)
df_raw["tipo"] = None
grupo_actual = None
for idx, row in df_raw.iterrows():
    activo = row["Activo"]
    if pd.isna(row["Ticker"]):
        grupo_actual = activo
        df_raw.at[idx, "tipo"] = None
    else:
        df_raw.at[idx, "tipo"] = grupo_actual

# Filtrar activos seleccionados
activos_disponibles = df_raw[df_raw["Ticker"].notna()]["Activo"].tolist()
activos_seleccionados = st.multiselect("Seleccionar activos a cargar", activos_disponibles)

# Crear lista de datos
activos_data = []
total_usd = 0.0

st.write("### Ingreso de valores por activo")

for idx, row in df_raw.iterrows():
    if pd.isna(row["Activo"]) or pd.isna(row["Ticker"]):
        continue

    if row["Activo"] not in activos_seleccionados:
        continue

    st.markdown(f"**{row['Activo']}** ({row['Moneda']})")
    nominal = st.number_input(f"Nominal de {row['Activo']}", key=f"nom_{idx}", value=0.0)
    precio = st.number_input(f"Precio de {row['Activo']}", key=f"precio_{idx}", value=0.0)

    if row["Moneda"] == "ARS":
        monto_usd = nominal / tipo_cambio
    else:
        monto_usd = nominal * precio

    activos_data.append({
        "tipo": row["tipo"],
        "Activo": row["Activo"],
        "Valores Nominales": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "Benchmark Específico": row["Benchmark Específico"],
        "Benchmark General": row["Benchmark General"],
        "es_total": False,
        "es_titulo": False
    })

# Crear DataFrame con los activos ingresados
resumen_df = pd.DataFrame(activos_data)
total_general = resumen_df["Monto USD"].sum() if not resumen_df.empty else 0
resumen_df["% del total"] = resumen_df["Monto USD"] / total_general * 100 if total_general else 0

# Agregar totales por tipo
tipos = resumen_df["tipo"].dropna().unique()
final_data = []

for tipo in tipos:
    subtipo_df = resumen_df[resumen_df["tipo"] == tipo]

    if subtipo_df.empty:
        continue

    final_data.extend(subtipo_df.to_dict("records"))
    subtotal = subtipo_df["Monto USD"].sum() if "Monto USD" in subtipo_df.columns else 0
    porcentaje = subtotal / total_general * 100 if total_general else 0

    final_data.append({
        "Activo": f"TOTAL {tipo}",
        "Monto USD": subtotal,
        "% del total": porcentaje,
        "es_total": True
    })

# Crear PDF horizontal
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", ln=True, align="C")

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", size=10)

columnas = ["Activo", "Valores Nominales", "Precio", "Monto USD", "% del total", "Benchmark Específico", "Benchmark General"]
anchos = [80, 30, 25, 30, 30, 50, 50]  # Ensanchamos columna "Activo"

for i, col in enumerate(columnas):
    pdf.cell(anchos[i], 10, col, 1, 0, "C")
pdf.ln()

for row in final_data:
    if row.get("es_total"):
        pdf.set_font("Arial", "B", 10)
    else:
        pdf.set_font("Arial", size=10)

    pdf.cell(anchos[0], 10, str(row.get("Activo", ""))[:40], 1)  # Cortamos si el texto es muy largo
    pdf.cell(anchos[1], 10, str(round(row.get("Valores Nominales", 0), 2)) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[2], 10, str(round(row.get("Precio", 0), 2)) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[3], 10, f"{round(row.get('Monto USD', 0), 2):,.2f}", 1)
    pdf.cell(anchos[4], 10, f"{round(row.get('% del total', 0), 2):.2f}%", 1)
    pdf.cell(anchos[5], 10, str(row.get("Benchmark Específico", "")) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[6], 10, str(row.get("Benchmark General", "")) if not row.get("es_total") else "", 1)
    pdf.ln()

# Descargar PDF
with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
    pdf.output(tmpfile.name)
    with open(tmpfile.name, "rb") as f:
        st.download_button("Descargar resumen en PDF", f, file_name="resumen_cuenta.pdf")
    os.unlink(tmpfile.name)
