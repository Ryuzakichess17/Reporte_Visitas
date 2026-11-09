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

# Aplicar filtros (df_base filtrado por gestor, df_baseline SIN filtro de gestor para promedios fijos)
if len(fecha_rango) == 2:
    start_date, end_date = fecha_rango
    mask_fecha = (df['FECHA DE VISITA'].dt.date >= start_date) & (df['FECHA DE VISITA'].dt.date <= end_date)
    df_baseline_raw = df[mask_fecha] # Base para calcular el promedio de todo el equipo
    mask = mask_fecha & (df['GESTOR'].isin(gestores_seleccionados))
    df_base = df[mask] # Base para las tablas
else:
    df_baseline_raw = df.copy()
    df_base = df[df['GESTOR'].isin(gestores_seleccionados)]

# Filtros de duración
df_baseline = df_baseline_raw[df_baseline_raw['DURACION_MINUTOS'] >= min_duracion]
df_valido = df_base[df_base['DURACION_MINUTOS'] >= min_duracion]
df_descartado = df_base[df_base['DURACION_MINUTOS'] < min_duracion]

if df_valido.empty:
    st.warning("No hay datos para los filtros seleccionados.")
    st.stop()

# --- 3. KPIs PRINCIPALES (AHORA CON PROMEDIOS) ---
st.markdown("### 📊 Indicadores Clave de Rendimiento (KPIs)")
col1, col2, col3, col4, col5 = st.columns(5)

# Calculos de Promedio (usando df_baseline para que no cambie al filtrar un solo gestor)
bodegas_x_gestor = df_baseline.groupby('GESTOR')['PDV'].nunique()
promedio_bodegas_gestor = bodegas_x_gestor.mean()

bodegas_x_dia_gestor = df_baseline.groupby(['GESTOR', df_baseline['FECHA DE VISITA'].dt.date])['PDV'].nunique()
promedio_bodegas_dia = bodegas_x_dia_gestor.mean()

col1.metric("Visitas Efectivas", f"{len(df_valido):,}".replace(',', '.'))
col2.metric("Bodegas Únicas (Total)", f"{df_valido['PDV'].nunique():,}".replace(',', '.'))
col3.metric("Promedio Bodegas/Gestor", f"{promedio_bodegas_gestor:.0f}", help="Promedio de cobertura total por gestor (Fijo del equipo)")
col4.metric("Promedio Bodegas/Día", f"{promedio_bodegas_dia:.0f}", help="Ritmo diario promedio de bodegas únicas por gestor (Fijo del equipo)")
col5.metric(f"Visitas Descartadas", f"{len(df_descartado):,}".replace(',', '.'), help=f"Visitas menores a {int(min_duracion)} min", delta_color="inverse")

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
tab_sem, tab_obj_sem, tab_dia = st.tabs(["📊 Acumulado por Semana", "🎯 Objetivo por Semana", "📅 Fluctuación Diaria"])

with tab_sem:
    visitas_semana = df_valido.groupby(['SEMANA_SORT_KEY', 'SEMANA_LABEL']).size().reset_index(name='Visitas')
    fig_semana = px.bar(
        visitas_semana, x='SEMANA_LABEL', y='Visitas', text='Visitas',
        title="Volumen de Visitas por Semana Exacta del Mes",
        color_discrete_sequence=['#1f77b4']
    )
    fig_semana.update_traces(textposition='outside', textfont=dict(size=16, color='black'), texttemplate='<b>%{text}</b>')
    fig_semana.update_layout(margin=dict(t=50))
    st.plotly_chart(fig_semana, use_container_width=True)

with tab_obj_sem:
    visitas_obj_semana = df_valido.groupby(['SEMANA_SORT_KEY', 'SEMANA_LABEL', 'OBJETIVO_VISITA']).size().reset_index(name='Visitas')
    visitas_obj_semana = visitas_obj_semana.sort_values('SEMANA_SORT_KEY')
    fig_obj_sem = px.bar(
        visitas_obj_semana, x='SEMANA_LABEL', y='Visitas', color='OBJETIVO_VISITA', barmode='group',
        text='Visitas', title="Volumen de Visitas por Objetivo y Semana",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_obj_sem.update_traces(textposition='outside', textfont=dict(size=12, color='black'))
    fig_obj_sem.update_layout(margin=dict(t=50), xaxis_title="", legend_title_text="Objetivo")
    st.plotly_chart(fig_obj_sem, use_container_width=True)

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

# --- 6. DESEMPEÑO POR GESTOR ---
st.markdown("### 🏆 Desempeño y Productividad por Gestor")
tab_comp, tab_hist, tab_obj_gest = st.tabs(["⚖️ Comparativa: Últimas 2 Semanas", "📅 Historial Completo", "🎯 Desglose Semanal por Objetivo"])

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
        
        col_penultima = f'Semana 1: {lbl_pen}'
        df_comp.columns = ['Gestor', col_penultima, f'Semana 2: {lbl_ult}', 'Crecimiento / Caída']
        promedio_penultima = df_comp[col_penultima].mean()
        
        def color_variacion(val):
            if isinstance(val, (int, float)):
                return f"color: {'#2ecc71' if val > 0 else ('#e74c3c' if val < 0 else '#95a5a6')}; font-weight: bold"
            return ''
            
        def highlight_below_avg(val):
            if isinstance(val, (int, float)) and val < promedio_penultima:
                return 'background-color: #ffcccc; color: #900000;'
            return ''
            
        st.dataframe(
            df_comp.style.map(color_variacion, subset=['Crecimiento / Caída'])
                         .map(highlight_below_avg, subset=[col_penultima])
                         .format({df_comp.columns[1]: "{:.0f}", df_comp.columns[2]: "{:.0f}", 'Crecimiento / Caída': "{:+.0f}"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No hay suficientes semanas para hacer una comparativa.")

with tab_hist:
    pivot_hist = pd.pivot_table(df_valido, values='DURACION_MINUTOS', index='GESTOR', columns='SEMANA_LABEL', aggfunc='count', fill_value=0)
    cols_ordenadas = sorted(pivot_hist.columns, key=lambda x: dict_map[x])
    pivot_hist = pivot_hist[cols_ordenadas]
    pivot_hist['Total General'] = pivot_hist.sum(axis=1)
    st.dataframe(pivot_hist.style.background_gradient(cmap='Blues', axis=1, subset=cols_ordenadas), use_container_width=True)

with tab_obj_gest:
    pivot_obj = pd.pivot_table(df_valido, values='DURACION_MINUTOS', index=['GESTOR', 'OBJETIVO_VISITA'], columns='SEMANA_LABEL', aggfunc='count', fill_value=0)
    cols_ordenadas_obj = sorted(pivot_obj.columns, key=lambda x: dict_map[x] if x in dict_map else "")
    pivot_obj = pivot_obj[cols_ordenadas_obj]
    pivot_obj['Total General'] = pivot_obj.sum(axis=1)
    st.dataframe(pivot_obj.style.background_gradient(cmap='Blues', axis=1, subset=cols_ordenadas_obj), use_container_width=True)

st.markdown("---")

# --- 7. COBERTURA REAL ---
st.markdown("### 🏪 Cobertura Real: Bodegas Únicas y Frecuencia de Visitas")
tab_cob_sem, tab_cob_dia, tab_frec = st.tabs(["📅 Bodegas Únicas por Semana", "📆 Promedio Diario de Bodegas Únicas", "🔄 Bodegas Más/Menos Visitadas"])

with tab_cob_sem:
    pivot_unicas_sem = pd.pivot_table(df_valido, values='PDV', index='GESTOR', columns='SEMANA_LABEL', aggfunc=lambda x: x.nunique(), fill_value=0)
    cols_unicas = sorted(pivot_unicas_sem.columns, key=lambda x: dict_map[x] if x in dict_map else "")
    pivot_unicas_sem = pivot_unicas_sem[cols_unicas]
    total_unicas = df_valido.groupby('GESTOR')['PDV'].nunique()
    pivot_unicas_sem['Total Únicas (Acumulado)'] = total_unicas
    st.dataframe(pivot_unicas_sem.style.background_gradient(cmap='Reds_r', axis=1, subset=cols_unicas), use_container_width=True)

with tab_cob_dia:
    unicas_dia_gestor = df_valido.groupby(['GESTOR', df_valido['FECHA DE VISITA'].dt.date])['PDV'].nunique().reset_index(name='Bodegas_Unicas')
    promedio_diario = unicas_dia_gestor.groupby('GESTOR')['Bodegas_Unicas'].mean().round(1).reset_index(name='Promedio Bodegas Únicas / Día')
    fig_prom_dia = px.bar(
        promedio_diario.sort_values('Promedio Bodegas Únicas / Día', ascending=True),
        x='Promedio Bodegas Únicas / Día', y='GESTOR', orientation='h',
        text='Promedio Bodegas Únicas / Día', color='Promedio Bodegas Únicas / Día', color_continuous_scale='Greens'
    )
    fig_prom_dia.update_traces(textposition='outside')
    st.plotly_chart(fig_prom_dia, use_container_width=True)

with tab_frec:
    col_mas, col_menos = st.columns(2)
    frecuencia_bodegas = df_valido.groupby(['NOMBRE PDV', 'GESTOR']).size().reset_index(name='Total de Visitas').sort_values('Total de Visitas', ascending=False)
    with col_mas:
        st.markdown("**🔝 TOP 15 - Bodegas Más Visitadas**")
        st.dataframe(frecuencia_bodegas.head(15), hide_index=True, use_container_width=True)
    with col_menos:
        st.markdown("**🔽 Bodegas Menos Visitadas**")
        st.dataframe(frecuencia_bodegas.tail(15).sort_values('Total de Visitas'), hide_index=True, use_container_width=True)

st.markdown("---")

# --- 8. MATRIZ UNIFICADA COMPACTA (SOMBREADO POR DEBAJO DEL PROMEDIO) ---
st.markdown("### 📊 Matriz Combinada: Visitas Totales vs Bodegas Únicas")
st.markdown("Tabla consolidada. <br>🔴 *El sombreado rojo indica que ese gestor está por debajo del **promedio de esa columna** en esa semana.*", unsafe_allow_html=True)

df_vis = df_valido.groupby(['GESTOR', 'SEMANA_LABEL']).size().reset_index(name='Visitas')
df_uni = df_valido.groupby(['GESTOR', 'SEMANA_LABEL'])['PDV'].nunique().reset_index(name='Bodegas Únicas')
df_merge = pd.merge(df_vis, df_uni, on=['GESTOR', 'SEMANA_LABEL'])

pivot_unificado = df_merge.pivot(index='GESTOR', columns='SEMANA_LABEL', values=['Visitas', 'Bodegas Únicas']).fillna(0)
pivot_unificado = pivot_unificado.swaplevel(axis=1).sort_index(axis=1)

semanas_ordenadas_cols = sorted(pivot_unificado.columns.levels[0], key=lambda x: dict_map.get(x, ""))
pivot_unificado = pivot_unificado[semanas_ordenadas_cols]

def highlight_below_avg_matrix(s):
    # s es cada columna de la matriz
    promedio_col = s.mean()
    # Si el valor es menor que el promedio de la columna, pinta de rojo
    return ['background-color: #ffcccc; color: #900000;' if v < promedio_col else '' for v in s]

# Aplicamos la función a nivel de columnas (axis=0)
st.dataframe(pivot_unificado.style.apply(highlight_below_avg_matrix, axis=0).format("{:.0f}"), use_container_width=True)

st.markdown("---")

# --- 9. EL ANALISTA VIRTUAL: EVALUACIÓN FIJA ---
st.markdown("### 🧠 Análisis Integral y Diagnóstico Automático")
st.markdown("Clasificación de gestores basada en sus métricas frente a los **promedios fijos del equipo**.")

# 1. Calculamos los promedios FIJOS del equipo (usando df_baseline, ignora el filtro visual de gestores)
visitas_totales_base = df_baseline.groupby('GESTOR').size()
unicas_totales_base = df_baseline.groupby('GESTOR')['PDV'].nunique()

prom_equipo_visitas = visitas_totales_base.mean() if not visitas_totales_base.empty else 0
prom_equipo_unicas = unicas_totales_base.mean() if not unicas_totales_base.empty else 0

# Promedio diario FIJO del equipo
dias_activos_base = df_baseline.groupby('GESTOR')['FECHA DE VISITA'].apply(lambda x: x.dt.date.nunique())
df_diario_base = pd.DataFrame({'visitas': visitas_totales_base, 'dias': dias_activos_base})
df_diario_base['vis_dia'] = df_diario_base['visitas'] / df_diario_base['dias']
prom_equipo_diario = df_diario_base['vis_dia'].mean() if not df_diario_base.empty else 0

# 2. Evaluamos a los gestores seleccionados actualmente (df_valido)
gestores_stats = []
for gestor in df_valido['GESTOR'].unique():
    df_g = df_valido[df_valido['GESTOR'] == gestor]
    
    visitas_totales = len(df_g)
    bodegas_unicas = df_g['PDV'].nunique()
    dias_activos = df_g['FECHA DE VISITA'].dt.date.nunique()
    
    visitas_x_dia = visitas_totales / dias_activos if dias_activos > 0 else 0
    unicas_x_dia = bodegas_unicas / dias_activos if dias_activos > 0 else 0
    
    df_g_base = df_base[df_base['GESTOR'] == gestor]
    visitas_cortas = len(df_g_base[df_g_base['DURACION_MINUTOS'] < min_duracion])
    
    gestores_stats.append({
        'Gestor': gestor,
        'Días Trabajados': dias_activos,
        'Visitas Totales': visitas_totales,
        'Bodegas Únicas': bodegas_unicas,
        'Visitas/Día': visitas_x_dia,
        'Bod. Únicas/Día': unicas_x_dia,
        'Visitas Descartadas': visitas_cortas
    })

df_eval = pd.DataFrame(gestores_stats)

def clasificar_gestor(row):
    # Ahora la regla compara siempre contra los promedios generales fijos
    if row['Bodegas Únicas'] >= prom_equipo_unicas and row['Visitas Totales'] >= prom_equipo_visitas:
        return '🌟 Bien (Excelente)'
    elif row['Bodegas Únicas'] < (prom_equipo_unicas * 0.75) and row['Visitas Totales'] < (prom_equipo_visitas * 0.75):
        return '🚨 Mal (Crítico)'
    else:
        return '⚠️ Regular (Seguimiento)'

def generar_observacion(row):
    obs = []
    if row['Bodegas Únicas'] < prom_equipo_unicas and row['Visitas Totales'] >= prom_equipo_visitas:
        obs.append("Alta productividad pero baja cobertura (muchas revisitas).")
    if row['Bodegas Únicas'] < prom_equipo_unicas and row['Visitas Totales'] < prom_equipo_visitas:
         obs.append("Volumen general por debajo del promedio del equipo.")
    if row['Visitas/Día'] < (prom_equipo_diario * 0.75):
        obs.append("Bajo volumen de visitas diarias.")
    if row['Visitas Descartadas'] > 5:
        obs.append("Alto volumen de visitas registradas como muy cortas.")
    if row['Bodegas Únicas'] >= prom_equipo_unicas and row['Visitas/Día'] >= prom_equipo_diario:
        obs.append("Excelente ritmo de visita y expansión territorial.")
    
    if not obs:
        if 'Bien' in row['Estado']:
            return "Buen desempeño consistente frente al promedio del equipo."
        elif 'Mal' in row['Estado']:
            return "Requiere revisión urgente de su productividad territorial."
        else:
            return "Rendimiento regular, en el límite del promedio esperado."
            
    return " | ".join(obs)

if not df_eval.empty:
    df_eval['Estado'] = df_eval.apply(clasificar_gestor, axis=1)
    df_eval['Diagnóstico Automático'] = df_eval.apply(generar_observacion, axis=1)

    df_eval = df_eval.sort_values(by=['Estado', 'Visitas Totales'], ascending=[False, False]).reset_index(drop=True)

    def color_estado(val):
        if 'Bien' in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if 'Regular' in val: return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        if 'Mal' in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''

    format_dict = {'Visitas/Día': "{:.1f}", 'Bod. Únicas/Día': "{:.1f}"}

    st.dataframe(
        df_eval.style.map(color_estado, subset=['Estado']).format(format_dict),
        use_container_width=True, hide_index=True
    )
else:
    st.info("No hay datos suficientes para evaluar a los gestores seleccionados.")

st.markdown("---")

# --- 10. AUDITORÍA Y ANOMALÍAS ---
st.markdown("### 🚨 Auditoría y Anomalías")
st.markdown("Revisión de alertas tempranas sobre posibles malas prácticas o inconsistencias en los registros de visita.")

st.info(f"**Visitas de duración crítica (< {int(min_duracion)} min):** Se detectaron **{len(df_descartado)}** registros que no cumplen el tiempo mínimo establecido. Esto corresponde a la métrica de 'Visitas Descartadas'.", icon="⏱️")

duplicados = df_base[df_base.duplicated(subset=['FECHA DE VISITA', 'GESTOR', 'NOMBRE PDV'], keep=False)]
if not duplicados.empty:
    st.warning(f"**Revisitas el mismo día:** Se detectaron **{len(duplicados)}** visitas donde el mismo Gestor visitó el mismo 'Nombre PDV' en el mismo día.", icon="⚠️")
    with st.expander("Ver detalle completo de visitas duplicadas"):
        ver_dups = duplicados[['FECHA DE VISITA', 'GESTOR', 'NOMBRE PDV', 'HORA_INICIO', 'DURACION_MINUTOS', 'OBJETIVO_VISITA']].sort_values(['GESTOR', 'NOMBRE PDV'])
        ver_dups['FECHA DE VISITA'] = ver_dups['FECHA DE VISITA'].dt.strftime('%Y-%m-%d')
        st.dataframe(ver_dups, hide_index=True, use_container_width=True)
else:
    st.success("No se encontraron visitas duplicadas el mismo día (Mismo Gestor, Fecha y Nombre PDV).", icon="✅")