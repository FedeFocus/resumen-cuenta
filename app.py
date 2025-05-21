import streamlit as st
import pandas as pd
from io import BytesIO
from fpdf import FPDF

# Leer Excel desde GitHub
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
df_raw = pd.read_excel(url_excel)

st.title("Resumen de Cuenta")

# Tipo de cambio manual
tipo_cambio = st.number_input("Ingrese tipo de cambio (USD/ARS)", min_value=0.01, format="%.2f")

# Filtrar activos para trabajar
activos_disponibles = df_raw["Activo"].dropna().tolist()
activos_seleccionados = st.multiselect("Seleccione los activos a cargar", activos_disponibles)

# Filtrar dataframe
df = df_raw[df_raw["Activo"].isin(activos_seleccionados)].copy()

# Carga manual de valores nominales y precios
df["Valor Nominal"] = 0.0
df["Precio"] = 0.0

for i, row in df.iterrows():
    df.at[i, "Valor Nominal"] = st.number_input(f"Nominal - {row['Activo']}", key=f"nom_{i}", format="%.2f")
    df.at[i, "Precio"] = st.number_input(f"Precio - {row['Activo']}", key=f"pre_{i}", format="%.2f")

# Calcular Monto USD
df["Monto USD"] = df.apply(lambda row:
    row["Valor Nominal"] / tipo_cambio if row["Moneda"] == "ARS"
    else row["Valor Nominal"] * row["Precio"], axis=1)

# Calcular ponderaciones
total_general = df["Monto USD"].sum()
df["Ponderación"] = df["Monto USD"] / total_general

# Totales por tipo de activo
grupos = df.groupby("Tipo de Activo")
filas_pdf = []

for nombre, grupo in grupos:
    filas_pdf.append({
        "Activo": f"TOTAL {nombre}",
        "Valor Nominal": grupo["Valor Nominal"].sum(),
        "Precio": None,
        "Monto USD": grupo["Monto USD"].sum(),
        "Ponderación": grupo["Monto USD"].sum() / total_general,
        "Benchmark Específico": "",
        "Benchmark General": ""
    })
    filas_pdf.extend(grupo.to_dict(orient="records"))

# Crear PDF horizontal
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Resumen de Cuenta", border=False, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", size=9)

# Anchos de columna personalizados
col_widths = [60, 30, 20, 30, 30, 50, 50]
headers = ["Activo", "Valor Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]

# Encabezado
pdf.set_fill_color(200, 200, 200)
for i, header in enumerate(headers):
    pdf.cell(col_widths[i], 8, header, 1, 0, "C", fill=True)
pdf.ln()

# Cuerpo
for fila in filas_pdf:
    pdf.set_font("Arial", "B" if str(fila["Activo"]).startswith("TOTAL") else "", 9)
    pdf.cell(col_widths[0], 8, str(fila["Activo"]), 1)
    pdf.cell(col_widths[1], 8, f"{fila['Valor Nominal']:.2f}", 1, 0, "R")
    pdf.cell(col_widths[2], 8, "" if fila["Precio"] is None else f"{fila['Precio']:.2f}", 1, 0, "R")
    pdf.cell(col_widths[3], 8, f"{fila['Monto USD']:.2f}", 1, 0, "R")
    pdf.cell(col_widths[4], 8, f"{fila['Ponderación']:.2%}", 1, 0, "R")
    pdf.cell(col_widths[5], 8, str(fila["Benchmark Específico"]), 1)
    pdf.cell(col_widths[6], 8, str(fila["Benchmark General"]), 1)
    pdf.ln()

# Descargar PDF
pdf_output = BytesIO()
pdf_output.write(pdf.output(dest="S").encode("latin1"))

st.download_button(
    "📄 Descargar PDF",
    data=pdf_output.getvalue(),
    file_name="resumen_cuenta.pdf",
    mime="application/pdf"
)
