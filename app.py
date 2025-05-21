import streamlit as calle
import pandas as pd
from fpdf import FPDF
import tempfile as archivo_temporal
import os as sistema_operativo
import requests
from io import BytesIO

calle.set_page_config(layout="wide")
calle.title("Generador de Resumen de Cuenta")

# Ingreso del tipo de cambio
calle.sidebar.subheader("Configuración")
tipo_cambio = calle.sidebar.number_input("Tipo de cambio de activos en ARS", min_value=0.01, step=0.01, format="%.2f")

# Cargar Excel desde GitHub con requests
url_excel = "https://raw.githubusercontent.com/FedeFocus/resumen-cuenta/main/BD.xlsx"
response = requests.get(url_excel)

if response.status_code == 200:
    df_raw = pd.read_excel(BytesIO(response.content))
else:
    calle.error(f"No se pudo descargar el archivo Excel. Código de error: {response.status_code}")
    calle.stop()

df_raw.dropna(how="all", inplace=True)

# Detectar grupos (tipos de activos)
df_raw["tipo"] = None
grupo_actual = None
for i, fila in df_raw.iterrows():
    activo = fila["Activo"]
    if pd.isna(fila["Corazón"]):
        grupo_actual = activo
        df_raw.at[i, "tipo"] = "grupo"
    else:
        df_raw.at[i, "tipo"] = grupo_actual

# Filtrar solo activos (no grupos)
df_activos = df_raw[df_raw["tipo"] != "grupo"].copy()

# Seleccionar activos manualmente
activos_seleccionados = calle.multiselect("Seleccionar activos a incluir", df_activos["Activo"].tolist())
df_seleccionados = df_activos[df_activos["Activo"].isin(activos_seleccionados)].copy()

# Ingresar valores nominales y precios
calle.subheader("Ingreso de Datos por Activo")
for i, fila in df_seleccionados.iterrows():
    col1, col2 = calle.columns(2)
    nominal = col1.number_input(f"Nominal de {fila['Activo']}", key=f"nom_{i}", min_value=0.0)
    precio = col2.number_input(f"Precio de {fila['Activo']}", key=f"precio_{i}", min_value=0.0)
    df_seleccionados.at[i, "Nominal"] = nominal
    df_seleccionados.at[i, "Precio"] = precio

# Calcular monto USD por activo
def calcular_monto_usd(fila):
    if fila["Moneda"] == "ARS":
        return fila["Nominal"] / tipo_cambio
    elif fila["Moneda"] == "USD":
        return fila["Nominal"] * fila["Precio"]
    return 0

df_seleccionados["Monto USD"] = df_seleccionados.apply(calcular_monto_usd, axis=1)

# Calcular porcentaje de cada activo respecto al total
total_portfolio = df_seleccionados["Monto USD"].sum()
df_seleccionados["Ponderación %"] = df_seleccionados["Monto USD"] / total_portfolio * 100

# Calcular totales por tipo de activo
df_totales = df_seleccionados.groupby("tipo")[["Monto USD"]].sum().rename(columns={"Monto USD": "Total por tipo"})
df_totales["Ponderación por tipo %"] = df_totales["Total por tipo"] / total_portfolio * 100

# Mostrar tabla en pantalla (opcional)
calle.subheader("Resumen calculado")
calle.dataframe(df_seleccionados)

# PDF
calle.subheader("Generar PDF")
if calle.button("Crear PDF"):

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Cabecera
    headers = ["Activo", "Nominal", "Precio", "Monto USD", "Ponderación %", "Benchmark Específico", "Benchmark General"]
    col_widths = [60, 30, 20, 30, 30, 40, 40]

    for header, width in zip(headers, col_widths):
        pdf.cell(width, 10, header, border=1)
    pdf.ln()

    # Contenido
    for _, fila in df_seleccionados.iterrows():
        datos = [
            str(fila["Activo"]),
            f"{fila['Nominal']:.2f}",
            f"{fila['Precio']:.2f}",
            f"{fila['Monto USD']:.2f}",
            f"{fila['Ponderación %']:.2f}%",
            fila["Benchmark Específico"],
            fila["Benchmark General"]
        ]
        for dato, width in zip(datos, col_widths):
            pdf.cell(width, 10, dato, border=1)
        pdf.ln()

    # Guardar temporal y descargar
    with archivo_temporal.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        with open(tmp_file.name, "rb") as f:
            calle.download_button(
                label="Descargar PDF",
                data=f,
                file_name="resumen_cuenta.pdf",
                mime="application/pdf"
            )
        sistema_operativo.remove(tmp_file.name)
