import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
import locale
import calendar

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # Para que los meses se vean en español

# --- Funciones ---
def procesar_datos(df):
    col_fecha = [col for col in df.columns if col.strip().lower() == 'fecha'][0]
    df[col_fecha] = pd.to_datetime(df[col_fecha])
    df['Fecha'] = df[col_fecha]
    df['Mes'] = df['Fecha'].dt.month
    df['Mes_Nombre'] = df['Fecha'].dt.month.apply(lambda x: calendar.month_name[x].capitalize())
    df['Año'] = df['Fecha'].dt.year
    df['Periodo'] = df['Fecha'].dt.to_period('M')
    return df

def filtrar_datos(df, clientes_seleccionados, categorias_seleccionadas, fecha_inicio, fecha_fin):
    return df[
        (df['cliente'].isin(clientes_seleccionados)) &
        (df['categoria'].isin(categorias_seleccionadas)) &
        (df['Fecha'] >= fecha_inicio) &
        (df['Fecha'] <= fecha_fin)
    ]

def generar_graficos(df):
    figs = {}

    df['Tipo Proveedor'] = df['categoria'].apply(lambda x: 'Nuevo' if 'nuevo' in str(x).lower() else 'Frecuente')

    def crear_figura(df_group, tipo, title, xlabel='', ylabel='Ventas ($)', color='skyblue'):
        fig, ax = plt.subplots(figsize=(10, 4))
        df_group.plot(kind=tipo, ax=ax, color=color, title=title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        plt.xticks(rotation=45)
        plt.tight_layout()
        return fig

    figs['compras_mensuales'] = crear_figura(df.groupby('Periodo')['venta'].sum(), 'bar', 'Total de Compras por Mes')
    figs['ventas_cliente'] = crear_figura(df.groupby('cliente')['venta'].sum().sort_values(ascending=False), 'bar', 'Ventas por Cliente')
    figs['ventas_categoria'] = crear_figura(df.groupby('categoria')['venta'].sum().sort_values(ascending=False), 'bar', 'Ventas por Categoría')
    figs['totales_anuales'] = crear_figura(df.groupby('Año')['venta'].sum(), 'bar', 'Total Ventas por Año', color=['#1f77b4', '#ff7f0e'])

    fig5, ax5 = plt.subplots(figsize=(10, 4))
    df.pivot_table(index='Mes_Nombre', columns='Año', values='venta', aggfunc='sum').plot(kind='bar', ax=ax5, title='Comparativa Mensual Año a Año')
    ax5.set_xlabel('Mes')
    ax5.set_ylabel('Ventas ($)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    figs['comparacion_anual'] = fig5

    fig2, ax2 = plt.subplots(figsize=(6, 6))
    df['Tipo Proveedor'].value_counts().plot(kind='pie', autopct='%1.1f%%', ax=ax2, title='Distribución Tipo Proveedor')
    ax2.set_ylabel('')
    plt.tight_layout()
    figs['tipo_proveedor'] = fig2

    return figs

def generar_pdf(nombre_archivo, df, figs, resumen_texto):
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    styles = getSampleStyleSheet()
    estilo_titulo = styles['Title']
    estilo_normal = styles['Normal']
    estilo_titulo.alignment = 1  # Centrado

    elements = [Paragraph("📄 Informe Contable Detallado", estilo_titulo), Spacer(1, 12)]
    elements.append(Paragraph(resumen_texto, estilo_normal))
    elements.append(Spacer(1, 12))

    for key in figs:
        buffer = BytesIO()
        figs[key].savefig(buffer, format='png')
        buffer.seek(0)
        elements.append(Image(buffer, width=450, height=250))
        elements.append(Spacer(1, 12))

    doc.build(elements)

# --- Streamlit App ---
st.set_page_config("Dashboard Contable", layout="wide")
st.title("📊 Dashboard Contable para Empresas")

archivo = st.file_uploader("Sube tu archivo Excel con datos de ventas", type=["xlsx"])

if archivo:
    try:
        df = pd.read_excel(archivo)
        df = procesar_datos(df)

        st.sidebar.header("📌 Filtros")
        clientes = df['cliente'].unique().tolist()
        categorias = df['categoria'].unique().tolist()

        clientes_seleccionados = st.sidebar.multiselect("Clientes", clientes, default=clientes)
        categorias_seleccionadas = st.sidebar.multiselect("Categorías", categorias, default=categorias)

        fecha_min, fecha_max = df['Fecha'].min(), df['Fecha'].max()
        fecha_inicio, fecha_fin = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

        if isinstance(fecha_inicio, list) or isinstance(fecha_inicio, tuple):
            fecha_inicio, fecha_fin = fecha_inicio

        df_filtrado = filtrar_datos(df, clientes_seleccionados, categorias_seleccionadas, pd.to_datetime(fecha_inicio), pd.to_datetime(fecha_fin))

        st.markdown(f"### Registros encontrados: {len(df_filtrado)}")

        total = df_filtrado['venta'].sum()
        iva = total * 0.19
        neto = total - iva
        ticket_promedio = df_filtrado.groupby('cliente')['venta'].sum().mean()

        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Total Ventas", f"${total:,.2f}")
        col2.metric("💵 Neto", f"${neto:,.2f}")
        col3.metric("📈 Ticket Promedio", f"${ticket_promedio:,.2f}")

        figs = generar_graficos(df_filtrado)

        for key in figs:
            st.pyplot(figs[key])

        resumen_texto = f"""
        Este informe presenta un análisis detallado de las ventas, categorizadas por cliente, tipo de proveedor y periodo mensual/anual.
        <br/><br/>
        <b>Total:</b> ${total:,.2f}<br/>
        <b>IVA (19%):</b> ${iva:,.2f}<br/>
        <b>Neto:</b> ${neto:,.2f}<br/>
        <b>Ticket Promedio por Cliente:</b> ${ticket_promedio:,.2f}
        """

        if st.button("📄 Generar Informe PDF Unificado"):
            generar_pdf("informe_contable.pdf", df_filtrado, figs, resumen_texto)
            with open("informe_contable.pdf", "rb") as f:
                st.download_button("📥 Descargar PDF", f, file_name="informe_contable.pdf")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
