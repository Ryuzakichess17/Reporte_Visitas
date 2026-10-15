import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# Configuración de la página
st.set_page_config(page_title="Dashboard de Visitas a Bodegas", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #1f77b4;
    }
    h1, h2, h3 { color: #2c3e50; }
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Análisis de Asistencia y Gestión de Visitas")
st.markdown("Dashboard interactivo para el seguimiento y evaluación del desempeño de gestores en punto de venta.")

# --- LÓGICA DE FECHAS (Semana del Mes real) ---
def get_week_info(d):
    meses = {1:'Ene', 2:'Feb', 3:'Mar', 4:'Abr', 5:'May', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dic'}
    
    start_of_week = d - timedelta(days=d.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    start_of_month = d.replace(day=1)
    if d.month == 12:
        next_month = d.replace(year=d.year+1, month=1, day=1)
    else:
        next_month = d.replace(month=d.month+1, day=1)
    end_of_month = next_month - timedelta(days=1)
    
    actual_start = max(start_of_week.date(), start_of_month.date())
    actual_end = min(end_of_week.date(), end_of_month.date())
    
    first_day_week_start = start_of_month - timedelta(days=start_of_month.weekday())
    week_num = (start_of_week.date() - first_day_week_start.date()).days // 7 + 1
    
    label = f"S{week_num} ({actual_start.strftime('%d')}-{actual_end.strftime('%d')} {meses[d.month]})"
    sort_key = f"{d.year}-{d.month:02d}-W{week_num}"
    
    return pd.Series([label, sort_key])

# --- 1. CARGA DE DATOS ---
@st.cache_data
def load_data():
    df = pd.read_excel('Base ,visitas 13.xlsx')
    df['FECHA DE VISITA'] = pd.to_datetime(df['FECHA DE VISITA'])
    df[['SEMANA_LABEL', 'SEMANA_SORT_KEY']] = df['FECHA DE VISITA'].apply(get_week_info)
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("No se encontró el archivo 'Base ,visitas 13.xlsx'.")
    st.stop()

# --- 2. BARRA LATERAL (FILTROS) ---
with st.sidebar:
    st.header("⚙️ Controles del Dashboard")
    st.markdown("---")
    
    st.subheader("📅 Rango de Fechas")
    fecha_min = df['FECHA DE VISITA'].min().date()
    fecha_max = df['FECHA DE VISITA'].max().date()
    fecha_rango = st.date_input("Seleccionar Periodo", [fecha_min, fecha_max])
    
    st.subheader("⏱️ Filtro de Duración")
    min_duracion = st.number_input("Duración Mínima (minutos)", min_value=0.0, value=10.0, step=1.0)
    
    st.subheader("👥 Selección de Gestores")
    todos_gestores = sorted(df['GESTOR'].unique().tolist())
    select_all = st.checkbox("Seleccionar Todos los Gestores", value=True)
    
    if select_all:
        gestores_seleccionados = todos_gestores
    else:
        gestores_seleccionados = st.multiselect("Elegir Gestores:", options=todos_gestores, default=[])

# Aplicar filtros
if len(fecha_rango) == 2:
    start_date, end_date = fecha_rango
    mask = (
        (df['GESTOR'].isin(gestores_seleccionados)) & 
        (df['FECHA DE VISITA'].dt.date >= start_date) & 
        (df['FECHA DE VISITA'].dt.date <= end_date)
    )
    df_base = df[mask]
else:
    df_base = df[df['GESTOR'].isin(gestores_seleccionados)]

df_valido = df_base[df_base['DURACION_MINUTOS'] >= min_duracion]
df_descartado = df_base[df_base['DURACION_MINUTOS'] < min_duracion]

if df_valido.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# --- 3. KPIs PRINCIPALES ---
st.markdown("### 📊 Indicadores Clave de Rendimiento (KPIs)")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Visitas Efectivas", f"{len(df_valido):,}".replace(',', '.'))
col2.metric("Cobertura (Bodegas Únicas)", f"{df_valido['PDV'].nunique():,}".replace(',', '.'))
col3.metric("Tiempo Medio en PDV", f"{df_valido['DURACION_MINUTOS'].mean():.0f} min")
col4.metric(f"Visitas < {int(min_duracion)} min", f"{len(df_descartado):,}".replace(',', '.'), delta_color="inverse")

st.markdown("---")

# --- 4. COMPOSICIÓN DE VISITAS ---
st.markdown("### 🎯 Desglose por Objetivo de Visita (POP, Mantenimiento, Chips)")
col_obj_1, col_obj_2 = st.columns([2, 1])

resumen_objetivos = df_valido['OBJETIVO_VISITA'].value_counts().reset_index()
resumen_objetivos.columns = ['Objetivo', 'Cantidad']

fig_obj = px.bar(
    resumen_objetivos, x='Cantidad', y='Objetivo', orientation='h', 
    title="Cantidad de Visitas por Tipo", color='Cantidad', color_continuous_scale="Blues"
)
fig_obj.update_layout(yaxis={'categoryorder':'total ascending'})
col_obj_1.plotly_chart(fig_obj, use_container_width=True)
col_obj_2.dataframe(resumen_objetivos, use_container_width=True, hide_index=True)

st.markdown("---")

# --- 5. ANÁLISIS TEMPORAL ---
st.markdown("### 📈 Evolución Temporal de Visitas")
tab_sem, tab_dia = st.tabs(["📊 Acumulado por Semana", "📅 Fluctuación Diaria"])

with tab_sem:
    visitas_semana = df_valido.groupby(['SEMANA_SORT_KEY', 'SEMANA_LABEL']).size().reset_index(name='Visitas')
    fig_semana = px.bar(
        visitas_semana, x='SEMANA_LABEL', y='Visitas', text='Visitas',
        title="Volumen de Visitas por Semana Exacta del Mes",
        color_discrete_sequence=['#1f77b4']
    )
    # AJUSTE: Etiquetas más grandes y en negrita
    fig_semana.update_traces(
        textposition='outside',
        textfont=dict(size=16, color='black'),
        texttemplate='<b>%{text}</b>'
    )
    # Aumentar ligeramente el margen superior para que no se corte el número
    fig_semana.update_layout(margin=dict(t=50))
    st.plotly_chart(fig_semana, use_container_width=True)

with tab_dia:
    visitas_dia = df_valido.groupby(df_valido['FECHA DE VISITA'].dt.date).size().reset_index(name='Visitas')
    fig_dia = px.line(
        visitas_dia, x='FECHA DE VISITA', y='Visitas', markers=True,
        title="Fluctuación Diaria", color_discrete_sequence=['#ff7f0e']
    )
    fig_dia.update_traces(fill='tozeroy', fillcolor='rgba(255, 127, 14, 0.1)')
    fig_dia.update_layout(xaxis_tickformat="%d %b")
    st.plotly_chart(fig_dia, use_container_width=True)

st.markdown("---")

# --- 6. DESEMPEÑO POR GESTOR (CON 2 VISTAS) ---
st.markdown("### 🏆 Desempeño y Productividad por Gestor")
st.markdown("Selecciona si deseas comparar las últimas dos semanas registradas, o si prefieres ver el historial completo (semana a semana).")

tab_comp, tab_hist = st.tabs(["⚖️ Comparativa: Últimas 2 Semanas", "📅 Historial Completo (Venta por Semana)"])

semanas_ordenadas = sorted(df_valido['SEMANA_SORT_KEY'].unique())
dict_map = df_valido[['SEMANA_LABEL', 'SEMANA_SORT_KEY']].drop_duplicates().set_index('SEMANA_LABEL')['SEMANA_SORT_KEY'].to_dict()

with tab_comp:
    if len(semanas_ordenadas) >= 2:
        ult_key = semanas_ordenadas[-1]
        pen_key = semanas_ordenadas[-2]
        
        lbl_ult = df_valido[df_valido['SEMANA_SORT_KEY'] == ult_key]['SEMANA_LABEL'].iloc[0]
        lbl_pen = df_valido[df_valido['SEMANA_SORT_KEY'] == pen_key]['SEMANA_LABEL'].iloc[0]
        
        df_ult = df_valido[df_valido['SEMANA_SORT_KEY'] == ult_key].groupby('GESTOR').size().reset_index(name='Visitas_Ult')
        df_pen = df_valido[df_valido['SEMANA_SORT_KEY'] == pen_key].groupby('GESTOR').size().reset_index(name='Visitas_Pen')
        
        df_comp = pd.DataFrame({'GESTOR': df_valido['GESTOR'].unique()})
        df_comp = pd.merge(df_comp, df_pen, on='GESTOR', how='left').fillna(0)
        df_comp = pd.merge(df_comp, df_ult, on='GESTOR', how='left').fillna(0)
        
        df_comp['Variación'] = df_comp['Visitas_Ult'] - df_comp['Visitas_Pen']
        
        df_comp.columns = ['Gestor', f'Semana 1: {lbl_pen}', f'Semana 2: {lbl_ult}', 'Crecimiento / Caída']
        
        def color_variacion(val):
            if isinstance(val, (int, float)):
                return f"color: {'#2ecc71' if val > 0 else ('#e74c3c' if val < 0 else '#95a5a6')}; font-weight: bold"
            return ''
            
        st.dataframe(
            df_comp.style.map(color_variacion, subset=['Crecimiento / Caída'])
            .format({df_comp.columns[1]: "{:.0f}", df_comp.columns[2]: "{:.0f}", 'Crecimiento / Caída': "{:+.0f}"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay suficientes semanas (mínimo 2) en el rango seleccionado para hacer una comparativa.")

with tab_hist:
    pivot_hist = pd.pivot_table(
        df_valido, values='DURACION_MINUTOS', index='GESTOR', 
        columns='SEMANA_LABEL', aggfunc='count', fill_value=0
    )
    
    cols_ordenadas = sorted(pivot_hist.columns, key=lambda x: dict_map[x])
    pivot_hist = pivot_hist[cols_ordenadas]
    pivot_hist['Total General'] = pivot_hist.sum(axis=1)
    
    st.dataframe(
        pivot_hist.style.background_gradient(cmap='Blues', axis=1, subset=cols_ordenadas),
        use_container_width=True
    )

st.markdown("---")

# --- 7. COBERTURA REAL (BODEGAS ÚNICAS) ---
st.markdown("### 🏪 Cobertura Real: Bodegas Únicas y Frecuencia de Visitas")
st.markdown("Análisis de cuántas bodegas DISTINTAS visita cada gestor para medir la cobertura territorial real frente a las visitas repetidas.")

tab_cob_sem, tab_cob_dia, tab_frec = st.tabs([
    "📅 Bodegas Únicas por Semana", 
    "📆 Promedio Diario de Bodegas Únicas", 
    "🔄 Bodegas Más y Menos Visitadas"
])

with tab_cob_sem:
    # Bodegas únicas por semana por gestor
    pivot_unicas_sem = pd.pivot_table(
        df_valido, values='PDV', index='GESTOR', 
        columns='SEMANA_LABEL', aggfunc=lambda x: x.nunique(), fill_value=0
    )
    # Ordenar columnas con la misma lógica de antes
    cols_unicas = sorted(pivot_unicas_sem.columns, key=lambda x: dict_map[x] if x in dict_map else "")
    pivot_unicas_sem = pivot_unicas_sem[cols_unicas]
    
    # Calcular el total de bodegas únicas en todo el periodo filtrado
    total_unicas = df_valido.groupby('GESTOR')['PDV'].nunique()
    pivot_unicas_sem['Total Únicas en Periodo'] = total_unicas
    
    st.dataframe(
        pivot_unicas_sem.style.background_gradient(cmap='Greens', axis=1, subset=cols_unicas),
        use_container_width=True
    )

with tab_cob_dia:
    # Contar bodegas únicas por gestor y día
    unicas_dia_gestor = df_valido.groupby(['GESTOR', df_valido['FECHA DE VISITA'].dt.date])['PDV'].nunique().reset_index(name='Bodegas_Unicas')
    # Promediar esos valores
    promedio_diario = unicas_dia_gestor.groupby('GESTOR')['Bodegas_Unicas'].mean().round(1).reset_index(name='Promedio de Bodegas Únicas por Día')
    
    fig_prom_dia = px.bar(
        promedio_diario.sort_values('Promedio de Bodegas Únicas por Día', ascending=True),
        x='Promedio de Bodegas Únicas por Día', y='GESTOR', orientation='h',
        title='Promedio de Bodegas Distintas que visita un Gestor al Día',
        text='Promedio de Bodegas Únicas por Día', color='Promedio de Bodegas Únicas por Día', color_continuous_scale='Greens'
    )
    fig_prom_dia.update_traces(textposition='outside')
    st.plotly_chart(fig_prom_dia, use_container_width=True)

with tab_frec:
    col_mas, col_menos = st.columns(2)
    # Top bodegas más y menos visitadas
    frecuencia_bodegas = df_valido.groupby(['NOMBRE PDV', 'GESTOR']).size().reset_index(name='Total de Visitas')
    frecuencia_bodegas = frecuencia_bodegas.sort_values('Total de Visitas', ascending=False)
    
    with col_mas:
        st.markdown("**🔝 TOP 15 - Bodegas Más Visitadas**")
        st.markdown("*(Útil para detectar excesos de visita a un mismo local)*")
        st.dataframe(frecuencia_bodegas.head(15), hide_index=True, use_container_width=True)
        
    with col_menos:
        st.markdown("**🔽 Bodegas Menos Visitadas**")
        st.markdown("*(Solo registran 1 o muy pocas visitas)*")
        # Mostrar el tail, pero ordenado para ver las que tienen 1
        st.dataframe(frecuencia_bodegas.tail(15).sort_values('Total de Visitas'), hide_index=True, use_container_width=True)

st.markdown("---")

# --- 8. AUDITORÍA Y ANOMALÍAS ---
st.markdown("### 🚨 Auditoría y Anomalías")
st.markdown("Revisión de alertas tempranas sobre posibles malas prácticas o inconsistencias en los registros de visita.")

st.info(f"**Visitas de duración crítica (< {int(min_duracion)} min):** Se detectaron **{len(df_descartado)}** registros que no cumplen el tiempo mínimo establecido. Revisa la tabla de KPIs para el impacto general.", icon="⏱️")

duplicados = df_base[df_base.duplicated(subset=['FECHA DE VISITA', 'GESTOR', 'NOMBRE PDV'], keep=False)]
if not duplicados.empty:
    st.warning(f"**Revisitas el mismo día:** Se detectaron **{len(duplicados)}** visitas donde el mismo Gestor visitó el mismo 'Nombre PDV' en el mismo día.", icon="⚠️")
    with st.expander("Ver detalle completo de visitas duplicadas"):
        ver_dups = duplicados[['FECHA DE VISITA', 'GESTOR', 'NOMBRE PDV', 'HORA_INICIO', 'OBJETIVO_VISITA']].sort_values(['GESTOR', 'NOMBRE PDV'])
        ver_dups['FECHA DE VISITA'] = ver_dups['FECHA DE VISITA'].dt.strftime('%Y-%m-%d')
        st.dataframe(ver_dups, hide_index=True, use_container_width=True)
else:
    st.success("No se encontraron visitas duplicadas el mismo día (Mismo Gestor, Fecha y Nombre PDV).", icon="✅")