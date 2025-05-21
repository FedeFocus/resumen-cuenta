import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("Generador de Resumen de Cuenta")

# Ingresar tipo de cambio manual
st.sidebar.subheader("Configuración")
tipo_cambio = st.sidebar.number_input("Tipo de cambio para activos en ARS", min_value=0.01, step=0.01, format="%.2f")

# Cargar Excel desde GitHub
url_excel = "https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/BD.xlsx"  # <-- Actualizá TU_USUARIO y TU_REPO
df_raw = pd.read_excel(url_excel)

# Eliminar filas completamente vacías
df_raw.dropna(how="all", inplace=True)

# Identificar activos disponibles
activos_disponibles = df_raw[df_raw["Ticker"].notna()]["Activo"].tolist()

# Filtro: selección de activos a mostrar
activos_seleccionados = st.multiselect("Seleccioná los activos que querés cargar", activos_disponibles)

# Crear listas para almacenar los datos
activos_data = []
grupo_actual = None

st.write("### Ingreso de valores por activo")

# Leer los datos fila por fila
for idx, row in df_raw.iterrows():
    activo = row.get("Activo", "")
    ticker = row.get("Ticker", "")
    moneda = row.get("Moneda", "")

    # Si la fila representa un título de grupo (ONs, Soberanos, etc.)
    if pd.isna(ticker) and pd.isna(moneda):
        grupo_actual = row["Activo"]
        activos_data.append({"tipo": grupo_actual, "es_total": False, "es_titulo": True})
        continue

    # Ignorar activos no seleccionados
    if activo not in activos_seleccionados:
        continue

    st.markdown(f"**{activo}** ({moneda})")
    nominal = st.number_input(f"Nominal de {activo}", key=f"nom_{idx}", value=0.0)
    precio = st.number_input(f"Precio de {activo}", key=f"precio_{idx}", value=0.0)

    # Cálculo del monto en USD
    if moneda == "ARS":
        monto_usd = nominal / tipo_cambio
    else:
        monto_usd = nominal * precio

    activos_data.append({
        "tipo": grupo_actual,
        "Activo": activo,
        "Valores Nominales": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "Benchmark Específico": row["Benchmark Específico"],
        "Benchmark General": row["Benchmark General"],
        "es_total": False,
        "es_titulo": False
    })

# Convertir a DataFrame y calcular totales
resumen_df = pd.DataFrame([d for d in activos_data if not d.get("es_titulo")])
total_general = resumen_df["Monto USD"].sum()
resumen_df["% del total"] = resumen_df["Monto USD"] / total_general * 100

# Agrupar por tipo de activo y calcular subtotales
tipos = resumen_df["tipo"].dropna().unique()
final_data = []

for tipo in tipos:
    subtipo_df = resumen_df[resumen_df["tipo"] == tipo]
    final_data.extend(subtipo_df.to_dict("records"))
    subtotal = subtipo_df["Monto USD"].sum()
    porcentaje = subtotal / total_general * 100
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
anchos = [85, 30, 25, 30, 30, 50, 50]  # Aumentamos ancho de "Activo"

for i, col in enumerate(columnas):
    pdf.cell(anchos[i], 10, col, 1, 0, "C")
pdf.ln()

for row in final_data:
    if row.get("es_total"):
        pdf.set_font("Arial", "B", 10)
    else:
        pdf.set_font("Arial", size=10)

    pdf.cell(anchos[0], 10, str(row.get("Activo", "")), 1)
    pdf.cell(anchos[1], 10, str(round(row.get("Valores Nominales", 0), 2)) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[2], 10, str(round(row.get("Precio", 0), 2)) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[3], 10, f"{round(row.get('Monto USD', 0), 2):,.2f}", 1)
    pdf.cell(anchos[4], 10, f"{round(row.get('% del total', 0), 2):.2f}%", 1)
    pdf.cell(anchos[5], 10, str(row.get("Benchmark Específico", "")) if not row.get("es_total") else "", 1)
    pdf.cell(anchos[6], 10, str(row.get("Benchmark General", "")) if not row.get("es_total") else "", 1)
    pdf.ln()

# Guardar PDF temporalmente y permitir descarga
with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
    pdf.output(tmpfile.name)
    with open(tmpfile.name, "rb") as f:
        st.download_button("Descargar resumen en PDF", f, file_name="resumen_cuenta.pdf")
    os.unlink(tmpfile.name)
