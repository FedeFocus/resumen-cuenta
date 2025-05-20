import streamlit as st
import pandas as pd
from fpdf import FPDF

# Cargar el archivo Excel
df = pd.read_excel("BD.xlsx", header=None)

# Ingreso del tipo de cambio
tipo_cambio = st.number_input("Ingresar tipo de cambio para activos en ARS:", min_value=0.01, step=0.01, format="%.2f")

# Procesamiento de datos
data_rows = []
tipo_activo_actual = None
activos_tipo_actual = []

for index, row in df.iterrows():
    activo = str(row[0]).strip()
    
    # Si la fila es una fila de tipo de activo (indicador de agrupación)
    if pd.isna(row[1]) and pd.isna(row[2]):
        # Procesar los activos del grupo anterior
        if activos_tipo_actual:
            total_tipo = sum([r["Monto USD"] for r in activos_tipo_actual])
            for r in activos_tipo_actual:
                r["% por tipo"] = (r["Monto USD"] / total_tipo * 100) if total_tipo else 0
            data_rows.extend(activos_tipo_actual)

            # Fila de subtotales
            data_rows.append({
                "Activo": f"TOTAL {tipo_activo_actual}",
                "Valores Nominales": "",
                "Precio": "",
                "Monto USD": total_tipo,
                "% Total": 0,  # Se calcula luego
                "% por tipo": 100,
                "Benchmark Específico": "",
                "Benchmark General": ""
            })
            activos_tipo_actual = []

        tipo_activo_actual = activo
        continue

    try:
        nominal = float(row[1]) if not pd.isna(row[1]) else 0
        precio = float(row[2]) if not pd.isna(row[2]) else 0
        moneda = str(row[3]).strip().upper()
        benchmark_esp = str(row[4]).strip()
        benchmark_gen = str(row[5]).strip()
    except Exception as e:
        continue  # Saltear si hay datos mal formateados

    # Calcular monto en USD
    if moneda == "ARS":
        monto_usd = nominal / tipo_cambio if tipo_cambio != 0 else 0
    elif moneda == "USD":
        monto_usd = nominal * precio
    else:
        monto_usd = 0

    activos_tipo_actual.append({
        "Activo": activo,
        "Valores Nominales": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "% Total": 0,  # se completa después
        "% por tipo": 0,
        "Benchmark Específico": benchmark_esp,
        "Benchmark General": benchmark_gen
    })

# Procesar último grupo
if activos_tipo_actual:
    total_tipo = sum([r["Monto USD"] for r in activos_tipo_actual])
    for r in activos_tipo_actual:
        r["% por tipo"] = (r["Monto USD"] / total_tipo * 100) if total_tipo else 0
    data_rows.extend(activos_tipo_actual)
    data_rows.append({
        "Activo": f"TOTAL {tipo_activo_actual}",
        "Valores Nominales": "",
        "Precio": "",
        "Monto USD": total_tipo,
        "% Total": 0,
        "% por tipo": 100,
        "Benchmark Específico": "",
        "Benchmark General": ""
    })

# Calcular total general
total_general = sum([r.get("Monto USD", 0) for r in data_rows if "TOTAL" not in r["Activo"]])
for r in data_rows:
    if "TOTAL" not in r["Activo"]:
        r["% Total"] = (r["Monto USD"] / total_general * 100) if total_general else 0
    elif r["Activo"].startswith("TOTAL"):
        r["% Total"] = (r["Monto USD"] / total_general * 100) if total_general else 0

# Crear PDF
pdf = FPDF(orientation='L', unit='mm', format='A4')
pdf.add_page()
pdf.set_font("Arial", size=8)

# Encabezados
headers = [
    "Activo", "Valores Nominales", "Precio", "Monto USD", "% Total", "% por tipo",
    "Benchmark Específico", "Benchmark General"
]
col_widths = [50, 30, 20, 25, 20, 25, 50, 50]
for header, width in zip(headers, col_widths):
    pdf.cell(width, 10, header, border=1)
pdf.ln()

# Contenido
for row in data_rows:
    pdf.cell(col_widths[0], 8, str(row.get("Activo", "")), border=1)
    pdf.cell(col_widths[1], 8, f'{row.get("Valores Nominales", ""):,}' if row.get("Valores Nominales") != "" else "", border=1)
    pdf.cell(col_widths[2], 8, f'{row.get("Precio", ""):.2f}' if isinstance(row.get("Precio"), (int, float)) else "", border=1)
    pdf.cell(col_widths[3], 8, f'{row.get("Monto USD", 0):.2f}', border=1)
    pdf.cell(col_widths[4], 8, f'{row.get("% Total", 0):.2f}%', border=1)
    pdf.cell(col_widths[5], 8, f'{row.get("% por tipo", 0):.2f}%', border=1)
    pdf.cell(col_widths[6], 8, row.get("Benchmark Específico", ""), border=1)
    pdf.cell(col_widths[7], 8, row.get("Benchmark General", ""), border=1)
    pdf.ln()

# Guardar PDF
pdf.output("ResumenCuenta.pdf")

# Descargar desde Streamlit
with open("ResumenCuenta.pdf", "rb") as f:
    st.download_button("Descargar PDF", f, file_name="ResumenCuenta.pdf", mime="application/pdf")
