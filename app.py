import streamlit as st
import pandas as pd
from fpdf import FPDF

# Cargar archivo
df = pd.read_excel("BD.xlsx", header=None)

st.title("Resumen de cuenta")

tipo_cambio = st.number_input("Ingresar tipo de cambio para activos en ARS:", min_value=0.01, step=0.01, format="%.2f")

# Variables
rows = []
grupo_actual = None
grupo_fila = []
totales_por_grupo = []

# Procesar filas
for index, row in df.iterrows():
    # Si es una fila que solo tiene el nombre del grupo (ej. 'ONs', 'Bopreal')
    if pd.notna(row[0]) and pd.isna(row[1]) and pd.isna(row[2]):
        # Si ya había un grupo, procesar y cerrar
        if grupo_fila:
            total_usd = sum(r["Monto USD"] for r in grupo_fila)
            for r in grupo_fila:
                r["% por tipo"] = (r["Monto USD"] / total_usd * 100) if total_usd else 0
            rows.extend(grupo_fila)
            rows.append({
                "Activo": f"TOTAL {grupo_actual}",
                "Valores Nominales": "",
                "Precio": "",
                "Monto USD": total_usd,
                "% Total": 0,
                "% por tipo": 100,
                "Benchmark Específico": "",
                "Benchmark General": ""
            })
            grupo_fila = []

        grupo_actual = str(row[0]).strip()
        continue

    try:
        activo = str(row[0]).strip()
        nominal = float(row[1]) if not pd.isna(row[1]) else 0
        precio = float(row[2]) if not pd.isna(row[2]) else 0
        moneda = str(row[3]).strip().upper()
        bench_esp = str(row[4]).strip()
        bench_gen = str(row[5]).strip()

        if moneda == "ARS":
            monto_usd = nominal / tipo_cambio if tipo_cambio else 0
        elif moneda == "USD":
            monto_usd = nominal * precio
        else:
            monto_usd = 0

        grupo_fila.append({
            "Activo": activo,
            "Valores Nominales": nominal,
            "Precio": precio,
            "Monto USD": monto_usd,
            "% Total": 0,
            "% por tipo": 0,
            "Benchmark Específico": bench_esp,
            "Benchmark General": bench_gen
        })
    except:
        continue

# Procesar último grupo
if grupo_fila:
    total_usd = sum(r["Monto USD"] for r in grupo_fila)
    for r in grupo_fila:
        r["% por tipo"] = (r["Monto USD"] / total_usd * 100) if total_usd else 0
    rows.extend(grupo_fila)
    rows.append({
        "Activo": f"TOTAL {grupo_actual}",
        "Valores Nominales": "",
        "Precio": "",
        "Monto USD": total_usd,
        "% Total": 0,
        "% por tipo": 100,
        "Benchmark Específico": "",
        "Benchmark General": ""
    })

# Calcular total general y % Total
total_general = sum(r["Monto USD"] for r in rows if "TOTAL" not in r["Activo"])
for r in rows:
    if "TOTAL" not in r["Activo"]:
        r["% Total"] = (r["Monto USD"] / total_general * 100) if total_general else 0
    elif r["Activo"].startswith("TOTAL"):
        r["% Total"] = (r["Monto USD"] / total_general * 100) if total_general else 0

# PDF
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.add_page()
pdf.set_font("Arial", size=8)

headers = ["Activo", "Valores Nominales", "Precio", "Monto USD", "% Total", "% por tipo", "Benchmark Específico", "Benchmark General"]
col_widths = [50, 30, 20, 25, 20, 25, 50, 50]

# Header
for header, w in zip(headers, col_widths):
    pdf.cell(w, 8, header, border=1)
pdf.ln()

# Rows
for r in rows:
    pdf.cell(col_widths[0], 8, str(r["Activo"]), border=1)
    pdf.cell(col_widths[1], 8, f'{r["Valores Nominales"]:,}' if r["Valores Nominales"] != "" else "", border=1)
    pdf.cell(col_widths[2], 8, f'{r["Precio"]:.2f}' if isinstance(r["Precio"], (int, float)) else "", border=1)
    pdf.cell(col_widths[3], 8, f'{r["Monto USD"]:.2f}', border=1)
    pdf.cell(col_widths[4], 8, f'{r["% Total"]:.2f}%', border=1)
    pdf.cell(col_widths[5], 8, f'{r["% por tipo"]:.2f}%', border=1)
    pdf.cell(col_widths[6], 8, r["Benchmark Específico"], border=1)
    pdf.cell(col_widths[7], 8, r["Benchmark General"], border=1)
    pdf.ln()

# Guardar
pdf.output("ResumenCuenta.pdf")

# Descargar
with open("ResumenCuenta.pdf", "rb") as f:
    st.download_button("Descargar PDF", f, file_name="ResumenCuenta.pdf", mime="application/pdf")
