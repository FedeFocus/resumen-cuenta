import streamlit as st
import pandas as pd
from fpdf import FPDF

# Cargar el archivo Excel
df = pd.read_excel("BD.xlsx", header=None)

# Ingreso manual del tipo de cambio
tipo_cambio = st.number_input("Ingresar tipo de cambio para activos en ARS:", min_value=0.01, step=0.01, format="%.2f")

# Preparar lista de filas procesadas
data_rows = []
tipo_activo_actual = None
subtotal_tipo_activo = 0
activos_tipo_actual = []

for index, row in df.iterrows():
    activo = str(row[0]).strip()
    
    # Detectar cambio de tipo de activo por fila vacía (grupo)
    if pd.isna(row[1]):
        if activos_tipo_actual:
            total_tipo = sum([r["Monto USD"] for r in activos_tipo_actual])
            for r in activos_tipo_actual:
                r["% por tipo"] = (r["Monto USD"] / total_tipo * 100) if total_tipo else 0
            data_rows.extend(activos_tipo_actual)

            # Fila de subtotal del tipo de activo
            data_rows.append({
                "Activo": f"TOTAL {tipo_activo_actual}",
                "Valores Nominales": "",
                "Precio": "",
                "Monto USD": total_tipo,
                "% Total": total_tipo / sum([r["Monto USD"] for r in data_rows if "TOTAL" not in r["Activo"]]) * 100,
                "% por tipo": 100,
                "Benchmark Específico": "",
                "Benchmark General": ""
            })
            activos_tipo_actual = []
            subtotal_tipo_activo = 0

        tipo_activo_actual = activo
        continue

    # Leer y convertir campos
    nominal = float(row[1]) if not pd.isna(row[1]) else 0
    precio = float(row[2]) if not pd.isna(row[2]) else 0
    moneda = str(row[3]).strip().upper()
    benchmark_esp = str(row[4]).strip()
    benchmark_gen = str(row[5]).strip()

    if moneda == "ARS":
        monto_usd = nominal / tipo_cambio
    elif moneda == "USD":
        monto_usd = nominal * precio
    else:
        monto_usd = 0  # Moneda no reconocida

    activos_tipo_actual.append({
        "Activo": activo,
        "Valores Nominales": nominal,
        "Precio": precio,
        "Monto USD": monto_usd,
        "% Total": 0,  # Se calcula luego
        "% por tipo": 0,  # Se calcula luego
        "Benchmark Específico": benchmark_esp,
        "Benchmark General": benchmark_gen
    })

# Agregar últimos si quedaron
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
        "% Total": total_tipo / sum([r["Monto USD"] for r in data_rows if "TOTAL" not in r["Activo"]]) * 100,
        "% por tipo": 100,
        "Benchmark Específico": "",
        "Benchmark General": ""
    })

# Calcular porcentaje total general
total_general = sum([r["Monto USD"] for r in data_rows if "TOTAL" not in r["Activo"]])
for r in data_rows:
    if "TOTAL" not in r["Activo"]:
        r["% Total"] = (r["Monto USD"] / total_general * 100) if total_general else 0

# Crear PDF horizontal
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
    pdf.cell(col_widths[0], 8, str(row["Activo"]), border=1)
    pdf.cell(col_widths[1], 8, f'{row["Valores Nominales"]:,}' if row["Valores Nominales"] else "", border=1)
    pdf.cell(col_widths[2], 8, f'{row["Precio"]:.2f}' if row["Precio"] else "", border=1)
    pdf.cell(col_widths[3], 8, f'{row["Monto USD"]:.2f}', border=1)
    pdf.cell(col_widths[4], 8, f'{row["% Total"]:.2f}%', border=1)
    pdf.cell(col_widths[5], 8, f'{row["% por tipo"]:.2f}%', border=1)
    pdf.cell(col_widths[6], 8, row["Benchmark Específico"], border=1)
    pdf.cell(col_widths[7], 8, row["Benchmark General"], border=1)
    pdf.ln()

# Guardar
pdf.output("ResumenCuenta.pdf")

# Mostrar descarga
with open("ResumenCuenta.pdf", "rb") as f:
    st.download_button("Descargar PDF", f, file_name="ResumenCuenta.pdf", mime="application/pdf")
