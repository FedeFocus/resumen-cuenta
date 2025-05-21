import streamlit as st
import pandas as pd
from fpdf import FPDF
import tempfile
import os

st.set_page_config(layout="wide")
st.title("Generador de Resumen de Cuenta")

# Ingreso tipo de cambio
st.sidebar.subheader("Configuración")
tipo_cambio = st.sidebar.number_input("Tipo de cambio de activos en ARS", min_value=0.01, step=0.01, format="%.2f")

# Cargar Excel desde GitHub
url_excel = "https://github.com/FedeFocus/resumen-cuenta/raw/main/BD.xlsx"
df_raw = pd.read_excel(url_excel)
df_raw.dropna(how="all", inplace=True)

# Detectar grupos
df_raw["tipo"] = None
grupo_actual = None
for i, fila in df_raw.iterrows():
    activo = fila["Activo"]
    if pd.isna(fila["Moneda"]) and pd.isna(fila["Benchmark Específico"]) and pd.isna(fila["Benchmark General"]):
        grupo_actual = activo.strip()
        df_raw.at[i, "tipo"] = "grupo"
    else:
        df_raw.at[i, "tipo"] = grupo_actual

# Filtrar filas útiles
df_activos = df_raw[df_raw["tipo"] != "grupo"].copy()

# Selección manual de activos
activos_seleccionados = st.multiselect("Seleccionar activos a incluir", options=df_activos["Activo"].tolist())

if activos_seleccionados:
    df_activos = df_activos[df_activos["Activo"].isin(activos_seleccionados)].copy()

    # Ingreso de precio y nominal
    df_activos["Precio"] = 0.0
    df_activos["Nominal"] = 0.0
    for i, row in df_activos.iterrows():
        st.markdown(f"**{row['Activo']}** ({row['Moneda']})")
        precio = st.number_input(f"Precio - {row['Activo']}", key=f"precio_{i}", min_value=0.0, step=0.01)
        nominal = st.number_input(f"Nominal - {row['Activo']}", key=f"nominal_{i}", min_value=0.0, step=0.01)
        df_activos.at[i, "Precio"] = precio
        df_activos.at[i, "Nominal"] = nominal

    # Calcular monto en USD
    def calcular_monto(row):
        if row["Moneda"] == "ARS":
            return (row["Nominal"] / tipo_cambio)
        else:
            return row["Nominal"] * row["Precio"]

    df_activos["Monto USD"] = df_activos.apply(calcular_monto, axis=1)

    # Calcular ponderación individual
    total_general = df_activos["Monto USD"].sum()
    df_activos["Ponderación"] = df_activos["Monto USD"] / total_general * 100

    # Agrupar por tipo
    resumen = []
    for tipo, grupo in df_activos.groupby("tipo"):
        resumen.extend(grupo.to_dict("records"))
        total_tipo = grupo["Monto USD"].sum()
        ponderacion_tipo = total_tipo / total_general * 100
        resumen.append({
            "Activo": f"TOTAL {tipo.upper()}",
            "Nominal": "",
            "Precio": "",
            "Monto USD": total_tipo,
            "Ponderación": ponderacion_tipo,
            "Benchmark Específico": "",
            "Benchmark General": "",
            "tipo": tipo
        })

    df_final = pd.DataFrame(resumen)

    # Mostrar tabla previa
    st.subheader("Vista previa del resumen")
    st.dataframe(df_final[["Activo", "Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]])

    # Generar PDF
    def generar_pdf(df):
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=9)

        columnas = ["Activo", "Nominal", "Precio", "Monto USD", "Ponderación", "Benchmark Específico", "Benchmark General"]
        anchos = [90, 20, 20, 30, 25, 45, 45]

        for i, col in enumerate(columnas):
            pdf.cell(anchos[i], 8, col, border=1, ln=0)
        pdf.ln()

        for _, fila in df.iterrows():
            for i, col in enumerate(columnas):
                valor = fila[col]
                if isinstance(valor, float):
                    texto = f"{valor:,.2f}"
                else:
                    texto = str(valor)
                pdf.cell(anchos[i], 8, texto, border=1, ln=0)
            pdf.ln()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(tmp.name)
        return tmp.name

    if st.button("Generar PDF"):
        ruta_pdf = generar_pdf(df_final)
        with open(ruta_pdf, "rb") as f:
            st.download_button("Descargar PDF", f, file_name="resumen_cuenta.pdf")
