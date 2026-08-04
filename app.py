import streamlit as st
import sqlite3
import pandas as pd
import unicodedata
from datetime import datetime, date, timedelta
import holidays
import io
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO DARK MODE (CUPERTINO) ---
st.set_page_config(page_title="Sistema de Gestión Judicial", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { 
        background-color: #000000; 
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
        color: #f2f2f7;
        animation: fadeIn 0.4s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    h1, h2, h3 { 
        color: #f2f2f7 !important; 
        font-weight: 600 !important;
        letter-spacing: -0.025em;
    }
    
    .stTextInput label, .stSelectbox label, .stRadio label, .stDateInput label, .stTextArea label, .stNumberInput label {
        font-weight: 500 !important; 
        color: #8e8e93 !important; 
        font-size: 13px !important;
    }
    
    /* Campos de entrada modo oscuro */
    input[type="text"], textarea, input[type="number"], input[type="password"] {
        background-color: #1c1c1e !important; 
        border: 1px solid #38383a !important;
        border-radius: 10px !important; 
        padding: 10px 14px !important;
        color: #f2f2f7 !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    input[type="text"]:focus, textarea:focus, input[type="number"]:focus, input[type="password"]:focus {
        border-color: #0a84ff !important;
        box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.15) !important;
    }
    
    /* Fichas técnicas Glassmorphism Dark */
    .ficha-tecnica {
        background: rgba(28, 28, 30, 0.8);
        backdrop-filter: blur(12px);
        padding: 20px; 
        border-radius: 12px;
        border-left: 4px solid #0a84ff; 
        margin-bottom: 20px;
        font-size: 14px; 
        color: #e5e5ea;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
    }
    
    /* Badge de usuario */
    .user-badge {
        background: linear-gradient(135deg, #1c1c1e 0%, #2c2c2e 100%);
        color: #f2f2f7; 
        padding: 10px 14px;
        border-radius: 10px; 
        font-size: 13px; 
        font-weight: 500;
        display: inline-block; 
        margin-bottom: 15px;
        border: 1px solid #38383a;
    }
    
    /* Tarjetas de métricas interactivas */
    .metric-card {
        background: #1c1c1e; 
        border: 1px solid #38383a; 
        border-radius: 14px;
        padding: 22px; 
        text-align: center; 
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: #0a84ff;
    }
    
    div[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #1c1c1e;
    }
    
/* --- SUPER MENÚ LATERAL DEFINITIVO --- */
    
    /* 1. Ocultar los círculos rojos nativos a la fuerza */
    div[data-testid="stSidebar"] div[role="radiogroup"] label div[data-baseweb="radio"] > div:first-child,
    div[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    /* 2. Convertir las opciones en botones amplios */
    div[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #1c1c1e !important;
        border: 1px solid #2c2c2e !important;
        padding: 14px 20px !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.25s ease !important;
    }

    /* 3. Efecto al pasar el cursor (Hover) */
    div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #2c2c2e !important;
        border-color: #8e8e93 !important;
        transform: translateY(-2px) !important;
    }

    /* 4. Efecto de "Botón Presionado/Activo" en color Azul */
    div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: #0a84ff !important;
        border-color: #005ecb !important;
        box-shadow: 0 4px 15px rgba(10, 132, 255, 0.3) !important;
    }

    /* 5. Ajuste del texto interno */
    div[data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Gestión Judicial")

# --- FUNCIONES DE BASE DE DATOS ---
def conectar_bd():
    return sqlite3.connect("firma_abogados.db")

def crear_tablas():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (identificacion TEXT PRIMARY KEY, nombre TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS abogados (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, email TEXT, telefono TEXT, rol TEXT DEFAULT 'Abogado', password TEXT DEFAULT '1234')''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS procesos (
            radicado_interno TEXT PRIMARY KEY, radicado_rama TEXT, naturaleza TEXT,
            juzgado TEXT, etapa_actual TEXT, id_cliente TEXT, demandado TEXT, id_demandado TEXT, estado TEXT,
            pretensiones REAL, medidas_cautelares TEXT, abogado_id INTEGER
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS actuaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, radicado_interno TEXT, fecha TEXT, etapa TEXT, descripcion TEXT, usuario TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS vencimientos (id INTEGER PRIMARY KEY AUTOINCREMENT, radicado_interno TEXT, titulo TEXT, fecha_vencimiento TEXT, estado TEXT DEFAULT 'Pendiente', observaciones TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS contactos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT, telefono TEXT, email TEXT, direccion TEXT, ciudad TEXT, identificacion TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY AUTOINCREMENT, radicado_interno TEXT, fecha TEXT, concepto TEXT, valor REAL)''')
    
    # Migraciones
    cursor.execute("PRAGMA table_info(procesos)")
    cols_procesos = [col[1] for col in cursor.fetchall()]
    if 'abogado_id' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN abogado_id INTEGER")
    if 'pretensiones' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN pretensiones REAL")
    if 'medidas_cautelares' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN medidas_cautelares TEXT")
    if 'estado' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN estado TEXT DEFAULT 'Activo'")

    cursor.execute("PRAGMA table_info(contactos)")
    cols_contactos = [col[1] for col in cursor.fetchall()]
    if 'identificacion' not in cols_contactos: 
        cursor.execute("ALTER TABLE contactos ADD COLUMN identificacion TEXT")

    cursor.execute("PRAGMA table_info(abogados)")
    cols_abogados = [col[1] for col in cursor.fetchall()]
    if 'password' not in cols_abogados:
        cursor.execute("ALTER TABLE abogados ADD COLUMN password TEXT DEFAULT '1234'")

    cursor.execute("PRAGMA table_info(actuaciones)")
    cols_actuaciones = [col[1] for col in cursor.fetchall()]
    if 'usuario' not in cols_actuaciones:
        cursor.execute("ALTER TABLE actuaciones ADD COLUMN usuario TEXT")
        
    cursor.execute("SELECT COUNT(*) FROM abogados")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO abogados (nombre, email, telefono, rol, password) VALUES (?, ?, ?, ?, ?)", ("ADMINISTRADOR MAESTRO", "admin@firma.com", "3000000000", "Maestro", "1234"))
    conn.commit()
    conn.close()

crear_tablas()

# --- CONTROL DE ACCESO ---
st.sidebar.title("Control de Acceso")
conn = conectar_bd()
abogados_db = pd.read_sql_query("SELECT id, nombre, rol, password FROM abogados", conn)
conn.close()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario_nombre = None
    st.session_state.usuario_id = None
    st.session_state.usuario_rol = None

if not st.session_state.logged_in:
    if not abogados_db.empty:
        with st.sidebar.form("login_form"):
            nombres_usuarios = abogados_db['nombre'].tolist()
            usuario_seleccionado = st.selectbox("Perfil de usuario:", nombres_usuarios)
            password_input = st.text_input("Credencial de acceso:", type="password")
            submit_login = st.form_submit_button("🔑 Iniciar Sesión", use_container_width=True)
            
            if submit_login:
                row_usuario = abogados_db[abogados_db['nombre'] == usuario_seleccionado].iloc[0]
                stored_password = row_usuario['password'] if pd.notna(row_usuario['password']) and row_usuario['password'] != "" else "1234"
                
                if password_input == stored_password:
                    st.session_state.logged_in = True
                    st.session_state.usuario_nombre = row_usuario['nombre']
                    st.session_state.usuario_id = row_usuario['id']
                    st.session_state.usuario_rol = row_usuario['rol']
                    st.rerun()
                else:
                    st.sidebar.error("Credencial incorrecta.")
        st.stop()
    else:
        st.error("No hay perfiles configurados.")
        st.stop()
else:
    usuario_seleccionado = st.session_state.usuario_nombre
    usuario_id = st.session_state.usuario_id
    usuario_rol = st.session_state.usuario_rol
    
    st.sidebar.markdown(f"<div class='user-badge'>👤 {usuario_seleccionado}<br><span style='color:#8e8e93;'>{usuario_rol}</span></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.usuario_nombre = None
        st.session_state.usuario_id = None
        st.session_state.usuario_rol = None
        st.rerun()
        
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", [
        "🏠 Inicio", 
        "📝 Nuevo Proceso", 
        "📂 Expedientes", 
        "⏰ Vencimientos", 
        "📞 Directorio", 
        "📊 Resumen e Informes", 
        "👥 Administración"
    ])

# --- DÍAS HÁBILES Y FUNCIONES ---
festivos_colombia = holidays.Colombia()

def sumar_dias_habiles(fecha_inicio, dias_a_sumar):
    fecha = datetime.strptime(str(fecha_inicio), "%Y-%m-%d").date()
    dias_agregados = 0
    while dias_agregados < dias_a_sumar:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in festivos_colombia:
            dias_agregados += 1
    return str(fecha)

def limpiar_texto(texto):
    if pd.isna(texto) or texto is None: return ""
    texto = str(texto)
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).upper()

def obtener_nombre_numero(n):
    nombres = {1: "PRIMERO", 2: "SEGUNDO", 3: "TERCERO", 4: "CUARTO", 5: "QUINTO", 6: "SEXTO", 7: "SÉPTIMO", 8: "OCTAVO", 9: "NOVENO", 10: "DÉCIMO", 11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE", 16: "DIECISÉIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE", 20: "VEINTE"}
    return nombres.get(n, str(n))

def generar_radicado_interno():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT radicado_interno FROM procesos")
    radicados = cursor.fetchall()
    conn.close()
    max_num = 0
    for rad in radicados:
        try:
            numero = int(rad[0].split("-")[1])
            if numero > max_num: max_num = numero
        except: pass
    return f"EXP-{max_num + 1:04d}"

lista_procesos = ["EJECUTIVO SINGULAR", "EJECUTIVO HIPOTECARIO", "EJECUTIVO MIXTO", "ORDINARIO LABORAL", "OTRO"]
lista_etapas = [
    "1. Presentación de la demanda", 
    "2. Inadmisión", 
    "3. Admisión", 
    "4. Medidas Cautelares", 
    "5. Notificación", 
    "6. Excepciones", 
    "7. Sentencia", 
    "8. Desistimiento tácito"
]
lista_juzgados_esp = ["CIVIL MUNICIPAL", "CIVIL DEL CIRCUITO", "LABORAL", "DE FAMILIA", "PROMISCUO MUNICIPAL", "DE PEQUEÑAS CAUSAS"]

mapa_subetapas = {
    "1. Presentación de la demanda": {"Radicación": 30, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "2. Inadmisión": {"Auto de inadmisión": 5, "Subsanación": 30, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "3. Admisión": {"Solicitud de oficios": 15, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "4. Medidas Cautelares": {"Gestión de medidas cautelares": 15, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "5. Notificación": {"Envío de notificación": 10, "Envío de informe a despacho": 30, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "6. Excepciones": {"Traslado": 10, "Contestación a excepciones": 30, "Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "7. Sentencia": {"Requerimiento por DT": 25, "Impulso o memorial": 30, "Observación": 0},
    "8. Desistimiento tácito": {"Impulso o memorial": 30, "Observación": 0}
}

# --- SISTEMA DE TOASTS (NOTIFICACIONES FLOTANTES) ---
if 'toast_msg' in st.session_state:
    st.toast(st.session_state['toast_msg'], icon=st.session_state.get('toast_icon', '✅'))
    del st.session_state['toast_msg']
    if 'toast_icon' in st.session_state:
        del st.session_state['toast_icon']

if 'form_key' not in st.session_state:
    st.session_state.form_key = 0
fk = st.session_state.form_key 

# ==========================================
# SECCIÓN 0: INICIO (DASHBOARD GERENCIAL)
# ==========================================
if menu == "🏠 Inicio":
    st.header(f"Panel de Control | {usuario_seleccionado}")
    st.write("Panorama operativo general de la práctica jurídica y agenda de términos.")
    
    conn = conectar_bd()
    total_activos = pd.read_sql_query("SELECT COUNT(*) as c FROM procesos WHERE estado='Activo'", conn).iloc[0]['c']
    total_terminados = pd.read_sql_query("SELECT COUNT(*) as c FROM procesos WHERE estado='Terminado'", conn).iloc[0]['c']
    sum_pretensiones = pd.read_sql_query("SELECT SUM(pretensiones) as s FROM procesos WHERE estado='Activo'", conn).iloc[0]['s']
    sum_pretensiones = sum_pretensiones if pd.notna(sum_pretensiones) else 0.0
    
    limite_urgente = str(date.today() + timedelta(days=5))
    hoy_str = str(date.today())
    venc_urgentes_df = pd.read_sql_query(f"SELECT COUNT(*) as c FROM vencimientos WHERE estado='Pendiente' AND fecha_vencimiento <= '{limite_urgente}'", conn).iloc[0]['c']
    
    conn.close()
    
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.markdown(f"""
            <div class='metric-card'>
                <h2 style='color: #0a84ff; margin:0;'>📁 {total_activos}</h2>
                <p style='color: #8e8e93; margin:5px 0 0 0; font-weight:500;'>Procesos Activos</p>
            </div>
        """, unsafe_allow_html=True)
    with col_k2:
        st.markdown(f"""
            <div class='metric-card'>
                <h2 style='color: #ff453a; margin:0;'>🚨 {venc_urgentes_df}</h2>
                <p style='color: #8e8e93; margin:5px 0 0 0; font-weight:500;'>Términos (Próx. 5 días)</p>
            </div>
        """, unsafe_allow_html=True)
    with col_k3:
        st.markdown(f"""
            <div class='metric-card'>
                <h2 style='color: #30d158; margin:0;'>💰 ${sum_pretensiones:,.2f}</h2>
                <p style='color: #8e8e93; margin:5px 0 0 0; font-weight:500;'>Capital en Gestión</p>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    c_grafico, c_radar = st.columns([1, 1.5])
    
    with c_grafico:
        st.subheader("Balance de Expedientes")
        if total_activos == 0 and total_terminados == 0:
            st.info("No hay procesos registrados para graficar.")
        else:
            # Gráfico de Plotly Premium Dark
            df_chart = pd.DataFrame({
                'Estado': ['Activos', 'Terminados'], 
                'Cantidad': [total_activos, total_terminados]
            })
            fig = px.pie(df_chart, names='Estado', values='Cantidad', hole=0.6, 
                         color_discrete_sequence=['#0a84ff', '#38383a'])
            fig.update_layout(
                showlegend=True, 
                margin=dict(t=20, b=20, l=0, r=0), 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#f2f2f7")
            )
            st.plotly_chart(fig, use_container_width=True)

    with c_radar:
        st.subheader("Radar de Vencimientos")
        conn = conectar_bd()
        radar_df = pd.read_sql_query(f"SELECT * FROM vencimientos WHERE estado='Pendiente' AND fecha_vencimiento <= '{limite_urgente}' ORDER BY fecha_vencimiento ASC", conn)
        conn.close()
        
        if not radar_df.empty:
            for idx, r in radar_df.iterrows():
                if r['fecha_vencimiento'] < hoy_str:
                    estado_alerta = "🔴 VENCIDO"
                elif r['fecha_vencimiento'] == hoy_str:
                    estado_alerta = "⚠️ VENCE HOY"
                else:
                    estado_alerta = "⏰ Próximo a vencer"
                    
                st.warning(f"**[{estado_alerta}]** | Expediente: **{r['radicado_interno']}** | Tarea: **{r['titulo']}** | Límite: **{r['fecha_vencimiento']}**")
        else:
            st.success("✅ Agenda limpia. No hay términos críticos para los próximos 5 días.")

# ==========================================
# SECCIÓN 1: REGISTRAR PROCESO
# ==========================================
elif menu == "📝 Nuevo Proceso":
    st.header("Registro de Nuevo Proceso")
    
    with st.container(border=True):
        st.subheader("1. Identificación Básica")
        col_id1, col_id2 = st.columns(2)
        radicado_interno = generar_radicado_interno()
        col_id1.text_input("Radicado Interno (Automático)", value=radicado_interno, disabled=True, key=f"rad_int_{fk}")
        naturaleza = col_id2.selectbox("Naturaleza del Proceso", sorted(lista_procesos), key=f"nat_{fk}")
    
    with st.container(border=True):
        st.subheader("2. Radicado y Despacho Judicial")
        en_reparto_check = st.checkbox("📌 El proceso está en REPARTO", value=True, key=f"rep_{fk}")
        if not en_reparto_check:
            radicado_rama = st.text_input("Radicado Rama Judicial (23 dígitos)", max_chars=23, key=f"rad_rama_{fk}")
            col_j1, col_j2, col_j3 = st.columns(3)
            numero = col_j1.selectbox("Número del Juzgado", list(range(1, 101)), key=f"juz_num_{fk}")
            tipo = col_j2.selectbox("Especialidad", lista_juzgados_esp, key=f"juz_tip_{fk}")
            ciudad = col_j3.text_input("Ciudad", value="PEREIRA", key=f"juz_ciu_{fk}").upper()
            juzgado_final = f"JUZGADO {obtener_nombre_numero(numero)} {tipo} DE {ciudad}"
        else:
            st.info("💡 El expediente se registrará con radicado PENDIENTE POR REPARTO.")
            radicado_rama = "EN REPARTO"
            juzgado_final = "PENDIENTE POR REPARTO"
    
    with st.container(border=True):
        st.subheader("3. Partes Intervinientes")
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.markdown("**Demandante / Cliente**")
            conn = conectar_bd()
            clientes_df = pd.read_sql_query("SELECT identificacion, nombre FROM contactos WHERE tipo='Cliente' AND identificacion IS NOT NULL AND identificacion != ''", conn)
            
            opcion_cliente = st.radio("Origen del cliente:", ["Seleccionar existente", "Registrar cliente nuevo"], key=f"opc_cli_{fk}")
            id_demandante, nombre_demandante = "", ""
            if opcion_cliente == "Seleccionar existente":
                if not clientes_df.empty:
                    lista_opciones_c = clientes_df['identificacion'] + " - " + clientes_df['nombre']
                    cliente_sel = st.selectbox("Buscar Cliente", lista_opciones_c, key=f"cli_sel_{fk}")
                    id_demandante = cliente_sel.split(" - ")[0]
                    nombre_demandante = cliente_sel.split(" - ")[1]
                else: 
                    st.warning("No hay clientes registrados.")
            else:
                id_demandante = st.text_input("CC o NIT del Cliente Nuevo", key=f"id_cli_{fk}")
                nombre_demandante = st.text_input("Nombre Completo o Razón Social", key=f"nom_cli_{fk}").upper()
                
        with col_d2:
            st.markdown("**Demandado / Contraparte**")
            demandados_df = pd.read_sql_query("SELECT identificacion, nombre FROM contactos WHERE tipo='Contraparte' AND identificacion IS NOT NULL AND identificacion != ''", conn)
            conn.close()
            
            opcion_demandado = st.radio("Origen de la contraparte:", ["Seleccionar existente", "Registrar contraparte nueva"], key=f"opc_dem_{fk}")
            id_demandado, demandado = "", ""
            if opcion_demandado == "Seleccionar existente":
                if not demandados_df.empty:
                    lista_opciones_d = demandados_df['identificacion'] + " - " + demandados_df['nombre']
                    demandado_sel = st.selectbox("Buscar Demandado", lista_opciones_d, key=f"dem_sel_{fk}")
                    id_demandado = demandado_sel.split(" - ")[0]
                    demandado = demandado_sel.split(" - ")[1]
                else: 
                    st.warning("No hay contrapartes registradas.")
            else:
                id_demandado = st.text_input("CC o NIT Contraparte Nueva (Opcional)", key=f"id_dem_{fk}")
                demandado = st.text_input("Nombre Completo de Contraparte", key=f"nom_dem_{fk}").upper()
                
    with st.container(border=True):
        st.subheader("4. Pretensiones, Medidas y Asignación")
        col_p1, col_p2 = st.columns([1, 1])
        pretensiones = col_p1.number_input("Pretensiones ($)", min_value=0.0, step=50000.0, key=f"pret_{fk}")
        
        conn = conectar_bd()
        abogados_activos = pd.read_sql_query("SELECT id, nombre FROM abogados", conn)
        conn.close()
        dic_abogados = {row['nombre']: row['id'] for index, row in abogados_activos.iterrows()}
        abogado_sel_nombre = col_p2.selectbox("Abogado Responsable", list(dic_abogados.keys()), index=list(dic_abogados.keys()).index(usuario_seleccionado) if usuario_seleccionado in dic_abogados else 0, key=f"abg_{fk}")
        abogado_asignado_id = dic_abogados[abogado_sel_nombre]

        st.markdown("---")
        st.markdown("**🛡️ Medidas Cautelares Solicitadas**")
        lista_mc = ["INMUEBLE", "CUENTAS BANCARIAS", "SALARIO", "ESTABLECIMIENTO DE COMERCIO", "OTRO"]
        mc_seleccionadas = st.multiselect("Seleccione las medidas:", lista_mc, key=f"mclist_{fk}")
        detalles_mc = []
        if mc_seleccionadas:
            for i, mc in enumerate(mc_seleccionadas):
                if mc == "CUENTAS BANCARIAS":
                    detalles_mc.append(mc)
                else:
                    detalle = st.text_input(f"Detalle de la medida ({mc}):", placeholder="Placa, matrícula, etc.", key=f"mcdet_{fk}_{i}")
                    if detalle:
                        detalles_mc.append(f"{mc} ({detalle})")
                    else:
                        detalles_mc.append(mc) 
        medidas_finales = " | ".join(detalles_mc)
    
    if st.button("💾 Guardar Proceso en el Sistema", use_container_width=True):
        if opcion_cliente == "Registrar cliente nuevo" and (not nombre_demandante or not id_demandante):
            st.error("Complete los datos obligatorios del cliente nuevo.")
        elif not demandado:
            st.error("Ingrese el nombre del demandado.")
        else:
            conn = conectar_bd()
            cursor = conn.cursor()
            try:
                if opcion_cliente == "Registrar cliente nuevo":
                    cursor.execute('''INSERT OR IGNORE INTO clientes (identificacion, nombre) VALUES (?, ?)''', (id_demandante, nombre_demandante))
                    cursor.execute('''INSERT INTO contactos (identificacion, nombre, tipo, ciudad) VALUES (?, ?, 'Cliente', 'PEREIRA')''', (id_demandante, nombre_demandante))
                
                if opcion_demandado == "Registrar contraparte nueva":
                    if not id_demandado: id_demandado_guardar = f"SIN-CC-{datetime.now().microsecond}"
                    else: id_demandado_guardar = id_demandado
                    cursor.execute('''INSERT INTO contactos (identificacion, nombre, tipo, ciudad) VALUES (?, ?, 'Contraparte', 'PEREIRA')''', (id_demandado_guardar, demandado))

                cursor.execute('''INSERT INTO procesos (radicado_interno, radicado_rama, naturaleza, juzgado, etapa_actual, id_cliente, demandado, id_demandado, estado, pretensiones, medidas_cautelares, abogado_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (radicado_interno, radicado_rama, naturaleza, juzgado_final, lista_etapas[0], id_demandante, demandado, id_demandado, "Activo", pretensiones, medidas_finales, abogado_asignado_id))
                
                fecha_hoy = str(date.today())
                cursor.execute('''INSERT INTO actuaciones (radicado_interno, fecha, etapa, descripcion, usuario) VALUES (?, ?, ?, ?, ?)''', (radicado_interno, fecha_hoy, lista_etapas[0], "Radicación: Presentación inicial de la demanda.", usuario_seleccionado))
                
                fecha_alarma = sumar_dias_habiles(fecha_hoy, 30)
                cursor.execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento) VALUES (?, ?, ?)", (radicado_interno, "Radicación", fecha_alarma))

                conn.commit() 
                st.session_state.form_key += 1 
                st.session_state['toast_msg'] = f"Expediente {radicado_interno} registrado correctamente."
                st.session_state['toast_icon'] = "📁"
                st.rerun() 
            except Exception as e:
                st.error(f"Error al guardar: {e}")
            finally:
                conn.close()

# ==========================================
# SECCIÓN 2: EXPEDIENTES (BÚSQUEDA Y EDICIÓN)
# ==========================================
elif menu == "📂 Expedientes":
    st.header("Gestión de Expedientes")
    conn = conectar_bd()
    
    query = '''SELECT p.*, c.nombre AS demandante, a.nombre AS abogado_asignado FROM procesos p LEFT JOIN clientes c ON p.id_cliente = c.identificacion LEFT JOIN abogados a ON p.abogado_id = a.id'''
    df_procesos = pd.read_sql_query(query, conn)
    abogados_df = pd.read_sql_query("SELECT id, nombre FROM abogados", conn)
    conn.close()
    
    if not df_procesos.empty:
        df_procesos = df_procesos.fillna("")
        
        with st.container(border=True):
            st.markdown("### 🔍 Buscador de Expedientes")
            busqueda = st.text_input("Filtrar por radicado, parte interviniente o despacho:", placeholder="Ej: EXP-0001, Juan Pérez...", label_visibility="collapsed").strip()
        
        if busqueda:
            bus_limpia = limpiar_texto(busqueda)
            df_procesos['busqueda_aux'] = df_procesos.apply(lambda r: limpiar_texto(r['radicado_interno']) + " " + limpiar_texto(r['radicado_rama']) + " " + limpiar_texto(r['demandante']) + " " + limpiar_texto(r['demandado']) + " " + limpiar_texto(r['abogado_asignado']), axis=1)
            df_filtrado = df_procesos[df_procesos['busqueda_aux'].str.contains(bus_limpia, na=False)]
        else:
            df_filtrado = df_procesos.copy()
            
        st.write(f"Mostrando **{len(df_filtrado)}** expediente(s). Seleccione una fila para abrir su carpeta.")
            
        if not df_filtrado.empty:
            df_mostrar = df_filtrado[['radicado_interno', 'radicado_rama', 'naturaleza', 'demandante', 'demandado', 'juzgado', 'etapa_actual', 'estado']]
            evento = st.dataframe(df_mostrar, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            filas_seleccionadas = evento.selection.rows
            
            if filas_seleccionadas:
                proceso_fila = df_filtrado.iloc[filas_seleccionadas[0]]
                radicado_seleccionado = proceso_fila['radicado_interno']
                id_dem = proceso_fila['id_cliente'] if proceso_fila['id_cliente'] else "N/A"
                id_ddo = proceso_fila['id_demandado'] if proceso_fila['id_demandado'] else "N/A"
                medidas_texto = proceso_fila['medidas_cautelares'] if proceso_fila['medidas_cautelares'] else "No registradas"
                estado_proceso = proceso_fila['estado'] if 'estado' in proceso_fila else "Activo"
                try: val_pret_ficha = float(proceso_fila['pretensiones']) if proceso_fila['pretensiones'] else 0.0
                except: val_pret_ficha = 0.0
                
                st.markdown("---")
                
                with st.container(border=True):
                    st.markdown(f"""
                        <div style='text-align: center; margin-bottom: 25px;'>
                            <h2 style='color: #f2f2f7; margin-bottom: 5px; font-size: 26px; font-weight: bold;'>
                                {proceso_fila['demandante']} <span style='color: #8e8e93; font-size: 18px;'>VS</span> {proceso_fila['demandado']}
                            </h2>
                            <div style='color: #8e8e93; font-size: 13px; margin-top: -5px;'>
                                <span style='display: inline-block; width: 45%; text-align: right; padding-right: 25px;'>CC/NIT: {id_dem}</span>
                                <span style='display: inline-block; width: 45%; text-align: left; padding-left: 25px;'>CC/NIT: {id_ddo}</span>
                            </div>
                        </div>
                        <div class='ficha-tecnica'>
                            <b>Despacho:</b> {proceso_fila['juzgado']}<br>
                            <b>Radicado Rama:</b> {proceso_fila['radicado_rama']}<br>
                            <b>Expediente Interno:</b> {radicado_seleccionado} | <b>Estado:</b> {estado_proceso}<br>
                            <b>Pretensiones:</b> ${val_pret_ficha:,.2f}<br>
                            <b>Medidas Cautelares:</b> {medidas_texto}<br>
                            <b>Abogado Responsable:</b> {proceso_fila['abogado_asignado']}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("⚙️ Editar Datos Generales"):
                        with st.form(key=f"form_editar_proc_{radicado_seleccionado}"):
                            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
                            n_nat = c_e1.selectbox("Naturaleza", sorted(lista_procesos), index=sorted(lista_procesos).index(proceso_fila['naturaleza']) if proceso_fila['naturaleza'] in lista_procesos else 0)
                            n_dem = c_e2.text_input("Demandado", value=proceso_fila['demandado'])
                            n_rad = c_e3.text_input("Radicado Rama", value=proceso_fila['radicado_rama'] if proceso_fila['radicado_rama'] != "EN REPARTO" else "")
                            n_estado = c_e4.selectbox("Estado", ["Activo", "Terminado"], index=0 if estado_proceso == "Activo" else 1)

                            st.markdown("---")
                            actualizar_juz = st.checkbox("Actualizar Juzgado mediante selectores", value=False)
                            c_j1, c_j2, c_j3 = st.columns(3)
                            n_num = c_j1.selectbox("Número", list(range(1, 101)))
                            n_tipo = c_j2.selectbox("Especialidad", lista_juzgados_esp)
                            n_ciu = c_j3.text_input("Ciudad", value="PEREIRA").upper()
                            
                            st.markdown("---")
                            c_e5, c_e6, c_e7 = st.columns(3)
                            n_pret = c_e5.number_input("Pretensiones ($)", value=val_pret_ficha)
                            
                            abogados_list = abogados_df['nombre'].tolist()
                            idx_abg = abogados_list.index(proceso_fila['abogado_asignado']) if proceso_fila['abogado_asignado'] in abogados_list else 0
                            n_abg_nombre = c_e6.selectbox("Abogado Responsable", abogados_list, index=idx_abg)
                            n_abg_id = abogados_df[abogados_df['nombre'] == n_abg_nombre]['id'].values[0]
                            n_med = c_e7.text_input("Medidas Cautelares", value=proceso_fila['medidas_cautelares'])

                            if st.form_submit_button("💾 Guardar Cambios"):
                                if actualizar_juz: juz_guardar = f"JUZGADO {obtener_nombre_numero(n_num)} {n_tipo} DE {n_ciu}"
                                else: juz_guardar = proceso_fila['juzgado']
                                rad_guardar = n_rad if n_rad else "EN REPARTO"
                                
                                conn_up = conectar_bd()
                                conn_up.cursor().execute("""UPDATE procesos SET naturaleza=?, demandado=?, radicado_rama=?, juzgado=?, pretensiones=?, medidas_cautelares=?, abogado_id=?, estado=? WHERE radicado_interno=?""", (n_nat, n_dem, rad_guardar, juz_guardar, n_pret, n_med, int(n_abg_id), n_estado, radicado_seleccionado))
                                conn_up.commit()
                                conn_up.close()
                                st.session_state['toast_msg'] = "Expediente actualizado exitosamente."
                                st.session_state['toast_icon'] = "✅"
                                st.rerun()

                    with st.expander("🚨 Zona de Riesgo: Eliminar Expediente"):
                        st.warning("Esta acción eliminará permanentemente el expediente, actuaciones, vencimientos y gastos asociados.")
                        if st.button("🗑️ Eliminar Expediente Completamente"):
                            conn_del = conectar_bd()
                            conn_del.cursor().execute("DELETE FROM procesos WHERE radicado_interno=?", (radicado_seleccionado,))
                            conn_del.cursor().execute("DELETE FROM actuaciones WHERE radicado_interno=?", (radicado_seleccionado,))
                            conn_del.cursor().execute("DELETE FROM vencimientos WHERE radicado_interno=?", (radicado_seleccionado,))
                            conn_del.cursor().execute("DELETE FROM gastos WHERE radicado_interno=?", (radicado_seleccionado,))
                            conn_del.commit()
                            conn_del.close()
                            st.session_state['toast_msg'] = f"Expediente {radicado_seleccionado} eliminado."
                            st.session_state['toast_icon'] = "🗑️"
                            st.rerun()

                    st.markdown("---")
                    col_a1, col_a2 = st.columns([1, 1.5])
                    with col_a1:
                        st.markdown("**📝 Registrar Actuación Procesal**")
                        
                        f_act = st.date_input("Fecha", key=f"f_act_{radicado_seleccionado}")
                        e_act = st.selectbox("Etapa Procesal", lista_etapas, key=f"e_act_{radicado_seleccionado}")
                        
                        opciones_sub = list(mapa_subetapas[e_act].keys())
                        sub_act = st.selectbox("Sub-etapa (Plazo automático)", opciones_sub, key=f"sub_act_{radicado_seleccionado}")
                        
                        dias_alarma = mapa_subetapas[e_act][sub_act]
                        if dias_alarma > 0:
                            st.info(f"⏰ Término aplicable: **{dias_alarma} días hábiles**.")
                        else:
                            st.info("📌 Opción de mera nota (Sin generación de vencimientos).")
                        
                        d_act = st.text_area("Detalle / Observaciones", key=f"d_act_{radicado_seleccionado}")
                        
                        if st.button("💾 Guardar Actuación", use_container_width=True, key=f"btn_act_{radicado_seleccionado}"):
                            conn_ins = conectar_bd()
                            cursor = conn_ins.cursor()
                            
                            if sub_act != "Observación":
                                cursor.execute("UPDATE vencimientos SET estado='Completado' WHERE radicado_interno=? AND estado='Pendiente'", (radicado_seleccionado,))
                            
                            detalle_completo = f"{sub_act}: {d_act}" if d_act else sub_act
                            cursor.execute("INSERT INTO actuaciones (radicado_interno, fecha, etapa, descripcion, usuario) VALUES (?, ?, ?, ?, ?)", (radicado_seleccionado, str(f_act), e_act, detalle_completo, usuario_seleccionado))
                            cursor.execute("UPDATE procesos SET etapa_actual=? WHERE radicado_interno=?", (e_act, radicado_seleccionado))
                            
                            if dias_alarma > 0:
                                fecha_alarma_principal = sumar_dias_habiles(f_act, dias_alarma)
                                cursor.execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento, observaciones) VALUES (?, ?, ?, ?)", (radicado_seleccionado, sub_act, fecha_alarma_principal, d_act))
                            
                            conn_ins.commit()
                            conn_ins.close()
                            st.session_state['toast_msg'] = "Actuación registrada con éxito."
                            st.session_state['toast_icon'] = "📝"
                            st.rerun()

                    with col_a2:
                        st.markdown("**📜 Historial de Actuaciones**")
                        conn_hist = conectar_bd()
                        hist_df = pd.read_sql_query(f"SELECT * FROM actuaciones WHERE radicado_interno='{radicado_seleccionado}' ORDER BY fecha DESC", conn_hist)
                        conn_hist.close()
                        for idx, r in hist_df.iterrows():
                            autor_nota = f" (Por: {r['usuario']})" if 'usuario' in r and pd.notna(r['usuario']) and r['usuario'] != "" else ""
                            with st.expander(f"{r['fecha']} | {r['etapa']}{autor_nota}"):
                                with st.form(key=f"edit_act_{r['id']}"):
                                    n_f = st.text_input("Fecha", value=r['fecha'])
                                    n_e = st.selectbox("Etapa", lista_etapas, index=lista_etapas.index(r['etapa']) if r['etapa'] in lista_etapas else 0)
                                    n_d = st.text_area("Descripción", value=r['descripcion'])
                                    cb1, cb2 = st.columns(2)
                                    if cb1.form_submit_button("💾 Modificar"):
                                        conn_u = conectar_bd()
                                        conn_u.cursor().execute("UPDATE actuaciones SET fecha=?, etapa=?, descripcion=? WHERE id=?", (n_f, n_e, n_d, r['id']))
                                        conn_u.commit()
                                        conn_u.close()
                                        st.rerun()
                                    if cb2.form_submit_button("🗑️ Eliminar"):
                                        conn_d = conectar_bd()
                                        conn_d.cursor().execute("DELETE FROM actuaciones WHERE id=?", (r['id'],))
                                        conn_d.commit()
                                        conn_d.close()
                                        st.rerun()
                    
                    st.markdown("---")
                    col_g1, col_g2 = st.columns([1, 1.5])
                    with col_g1:
                        st.markdown("**💸 Control de Gastos y Costas**")
                        with st.form("form_gasto", clear_on_submit=True):
                            f_gasto = st.date_input("Fecha", key=f"f_gas_{radicado_seleccionado}")
                            c_gasto = st.text_input("Concepto (Arancel, Copias, Notificación)", key=f"c_gas_{radicado_seleccionado}")
                            v_gasto = st.number_input("Valor ($)", min_value=0.0, step=10000.0, key=f"v_gas_{radicado_seleccionado}")
                            
                            if st.form_submit_button("💾 Registrar Gasto", use_container_width=True):
                                if c_gasto and v_gasto > 0:
                                    conn_g = conectar_bd()
                                    conn_g.cursor().execute("INSERT INTO gastos (radicado_interno, fecha, concepto, valor) VALUES (?, ?, ?, ?)", (radicado_seleccionado, str(f_gasto), c_gasto, v_gasto))
                                    conn_g.commit()
                                    conn_g.close()
                                    st.session_state['toast_msg'] = "Gasto registrado."
                                    st.session_state['toast_icon'] = "💸"
                                    st.rerun()
                                else:
                                    st.error("Ingrese concepto y valor válidos.")
                                    
                    with col_g2:
                        st.markdown("**📊 Historial Financiero del Proceso**")
                        conn_hg = conectar_bd()
                        gastos_df = pd.read_sql_query(f"SELECT * FROM gastos WHERE radicado_interno='{radicado_seleccionado}' ORDER BY fecha DESC", conn_hg)
                        conn_hg.close()
                        
                        if not gastos_df.empty:
                            total_gastos = gastos_df['valor'].sum()
                            st.info(f"**Total Invertido:** ${total_gastos:,.2f}")
                            
                            for idx, r in gastos_df.iterrows():
                                with st.expander(f"🧾 {r['fecha']} | {r['concepto']} - ${r['valor']:,.2f}"):
                                    with st.form(key=f"edit_gas_{r['id']}"):
                                        n_fg = st.text_input("Fecha", value=r['fecha'])
                                        n_cg = st.text_input("Concepto", value=r['concepto'])
                                        n_vg = st.number_input("Valor ($)", value=float(r['valor']))
                                        
                                        c_bg1, c_bg2 = st.columns(2)
                                        if c_bg1.form_submit_button("💾 Modificar"):
                                            conn_ug = conectar_bd()
                                            conn_ug.cursor().execute("UPDATE gastos SET fecha=?, concepto=?, valor=? WHERE id=?", (n_fg, n_cg, n_vg, r['id']))
                                            conn_ug.commit()
                                            conn_ug.close()
                                            st.rerun()
                                        if c_bg2.form_submit_button("🗑️ Eliminar"):
                                            conn_dg = conectar_bd()
                                            conn_dg.cursor().execute("DELETE FROM gastos WHERE id=?", (r['id'],))
                                            conn_dg.commit()
                                            conn_dg.close()
                                            st.rerun()
                        else:
                            st.write("Sin gastos registrados.")
        else:
            st.warning("No se encontraron expedientes.")
    else:
        st.info("No hay procesos registrados en la base de datos.")

# ==========================================
# SECCIÓN 3: AGENDA 
# ==========================================
elif menu == "⏰ Vencimientos":
    st.header("Control de Vencimientos y Términos")
    c_ag1, c_ag2 = st.columns([1, 1.5])
    with c_ag1:
        st.subheader("📌 Programar Término Manual")
        with st.form("form_venc"):
            conn = conectar_bd()
            df_proc = pd.read_sql_query("SELECT radicado_interno FROM procesos", conn)
            conn.close()
            rad_sel = st.selectbox("Asociar a Proceso", df_proc['radicado_interno'].tolist() if not df_proc.empty else ["GENERAL"])
            tit_venc = st.text_input("Descripción del Término")
            f_venc = st.date_input("Fecha Límite")
            obs_venc = st.text_area("Observaciones")
            if st.form_submit_button("💾 Agendar Vencimiento"):
                if tit_venc:
                    conn_v = conectar_bd()
                    conn_v.cursor().execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento, observaciones) VALUES (?, ?, ?, ?)", (rad_sel, tit_venc, str(f_venc), obs_venc))
                    conn_v.commit()
                    conn_v.close()
                    st.session_state['toast_msg'] = "Término agendado con éxito."
                    st.session_state['toast_icon'] = "⏰"
                    st.rerun()
                    
    with c_ag2:
        st.subheader("🚨 Alarmas Pendientes")
        conn = conectar_bd()
        venc_df = pd.read_sql_query("SELECT * FROM vencimientos ORDER BY fecha_vencimiento ASC", conn)
        conn.close()
        
        venc_pendientes = venc_df[venc_df['estado'] == 'Pendiente']
        
        if not venc_pendientes.empty:
            for idx, row in venc_pendientes.iterrows():
                with st.expander(f"🔴 [{row['radicado_interno']}] {row['titulo']} (Vence: {row['fecha_vencimiento']})"):
                    with st.form(key=f"form_venc_edit_{row['id']}"):
                        u_tit = st.text_input("Tarea", value=row['titulo'])
                        u_fec = st.text_input("Fecha Vencimiento (AAAA-MM-DD)", value=row['fecha_vencimiento'])
                        u_est = st.selectbox("Estado", ["Pendiente", "Completado"], index=0)
                        
                        cv1, cv2 = st.columns(2)
                        if cv1.form_submit_button("💾 Actualizar"):
                            conn_uv = conectar_bd()
                            conn_uv.cursor().execute("UPDATE vencimientos SET titulo=?, fecha_vencimiento=?, estado=? WHERE id=?", (u_tit, u_fec, u_est, row['id']))
                            conn_uv.commit()
                            conn_uv.close()
                            st.rerun()
                        if cv2.form_submit_button("🗑️ Eliminar"):
                            conn_dv = conectar_bd()
                            conn_dv.cursor().execute("DELETE FROM vencimientos WHERE id=?", (row['id'],))
                            conn_dv.commit()
                            conn_dv.close()
                            st.rerun()
        else:
            st.success("✅ Agenda limpia. No hay alarmas pendientes.")

        with st.expander("👁️ Historial de Tareas Completadas"):
            venc_completados = venc_df[venc_df['estado'] == 'Completado']
            for idx, row in venc_completados.iterrows():
                st.caption(f"🟢 [{row['radicado_interno']}] {row['titulo']} | Cumplida: {row['fecha_vencimiento']}")

# ==========================================
# SECCIÓN 4: DIRECTORIO 
# ==========================================
elif menu == "📞 Directorio":
    st.header("Directorio de Contactos")
    c_d1, c_d2 = st.columns([1, 1.5])
    
    with c_d1:
        st.subheader("➕ Agregar Contacto")
        with st.form("form_cont", clear_on_submit=True):
            id_c = st.text_input("Cédula / NIT")
            n_c = st.text_input("Nombre Completo o Razón Social").upper()
            tipo_c = st.selectbox("Tipo", ["Cliente", "Contraparte", "Juzgado", "Perito", "Otro"])
            t_c = st.text_input("Teléfono")
            e_c = st.text_input("Email")
            d_c = st.text_input("Dirección")
            ciu_c = st.text_input("Ciudad", value="PEREIRA").upper()
            if st.form_submit_button("💾 Guardar Contacto"):
                if n_c:
                    conn_c = conectar_bd()
                    conn_c.cursor().execute("INSERT INTO contactos (identificacion, nombre, tipo, telefono, email, direccion, ciudad) VALUES (?, ?, ?, ?, ?, ?, ?)", (id_c, n_c, tipo_c, t_c, e_c, d_c, ciu_c))
                    conn_c.commit()
                    conn_c.close()
                    st.session_state['toast_msg'] = "Contacto guardado."
                    st.session_state['toast_icon'] = "📞"
                    st.rerun()
    
    with c_d2:
        st.subheader("🔎 Directorio General")
        conn = conectar_bd()
        df_cont = pd.read_sql_query("SELECT * FROM contactos", conn)
        conn.close()
        
        if not df_cont.empty:
            df_cont = df_cont.fillna("")
            
            lista_busqueda = []
            for i, r in df_cont.iterrows():
                if r['identificacion']:
                    lista_busqueda.append(f"{r['identificacion']} - {r['nombre']}")
                else:
                    lista_busqueda.append(r['nombre'])
                    
            contacto_sel = st.selectbox("Seleccionar contacto:", lista_busqueda)
            nombre_puro = contacto_sel.split(" - ")[1] if " - " in contacto_sel else contacto_sel
            
            datos_c = df_cont[df_cont['nombre'] == nombre_puro].iloc[0]
            
            with st.form(key="edit_contacto"):
                e_id_c = st.text_input("Cédula / NIT", value=datos_c['identificacion'])
                e_n_c = st.text_input("Nombre", value=datos_c['nombre'])
                e_tipo_c = st.selectbox("Tipo", ["Cliente", "Contraparte", "Juzgado", "Perito", "Otro"], index=["Cliente", "Contraparte", "Juzgado", "Perito", "Otro"].index(datos_c['tipo']) if datos_c['tipo'] in ["Cliente", "Contraparte", "Juzgado", "Perito", "Otro"] else 0)
                e_t_c = st.text_input("Teléfono", value=datos_c['telefono'])
                e_em_c = st.text_input("Email", value=datos_c['email'])
                e_d_c = st.text_input("Dirección", value=datos_c['direccion'])
                e_ciu_c = st.text_input("Ciudad", value=datos_c['ciudad'])
                
                ce1, ce2 = st.columns(2)
                if ce1.form_submit_button("💾 Guardar Cambios"):
                    conn_ec = conectar_bd()
                    conn_ec.cursor().execute("UPDATE contactos SET identificacion=?, nombre=?, tipo=?, telefono=?, email=?, direccion=?, ciudad=? WHERE id=?", (e_id_c, e_n_c, e_tipo_c, e_t_c, e_em_c, e_d_c, e_ciu_c, int(datos_c['id'])))
                    conn_ec.commit()
                    conn_ec.close()
                    st.session_state['toast_msg'] = "Contacto actualizado."
                    st.session_state['toast_icon'] = "✅"
                    st.rerun()
                if ce2.form_submit_button("🗑️ Eliminar"):
                    conn_dc = conectar_bd()
                    conn_dc.cursor().execute("DELETE FROM contactos WHERE id=?", (int(datos_c['id']),))
                    conn_dc.commit()
                    conn_dc.close()
                    st.rerun()
            st.dataframe(df_cont.drop(columns=['id']), use_container_width=True)
        else:
            st.info("Directorio vacío.")

# ==========================================
# SECCIÓN 5: RESUMEN E INFORMES (EXCEL)
# ==========================================
elif menu == "📊 Resumen e Informes":
    st.header("Informes y Exportación de Datos")
    conn = conectar_bd()
    total_p = pd.read_sql_query("SELECT COUNT(*) as c FROM procesos", conn).iloc[0]['c']
    conn.close()
    st.markdown(f"""
        <div class='metric-card' style='max-width: 300px; margin-bottom: 25px;'>
            <h2 style='color: #0a84ff; margin:0;'>📁 {total_p}</h2>
            <p style='color: #8e8e93; margin:5px 0 0 0; font-weight:500;'>Procesos Totales Registrados</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("Reporte General en Excel")
    st.write("Genera y descarga un archivo corporativo en formato Excel (.xlsx) con la consolidación de procesos, historiales de actuaciones unificados por expediente de forma cronológica, vencimientos y gastos.")
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        conn_rep = conectar_bd()
        df_proc_r = pd.read_sql_query("SELECT * FROM procesos", conn_rep)
        df_act_r = pd.read_sql_query("SELECT * FROM actuaciones ORDER BY fecha DESC", conn_rep)
        df_venc_r = pd.read_sql_query("SELECT * FROM vencimientos", conn_rep)
        df_gas_r = pd.read_sql_query("SELECT * FROM gastos", conn_rep)
        df_cont_r = pd.read_sql_query("SELECT * FROM contactos", conn_rep)
        conn_rep.close()
        
        actuaciones_consolidadas = {}
        for rad in df_proc_r['radicado_interno']:
            acts_subset = df_act_r[df_act_r['radicado_interno'] == rad]
            textos = []
            for _, act in acts_subset.iterrows():
                usuario_str = f" (Por: {act['usuario']})" if act['usuario'] else ""
                textos.append(f"[{act['fecha']}] {act['etapa']} - {act['descripcion']}{usuario_str}")
            actuaciones_consolidadas[rad] = "\n".join(textos)
            
        df_proc_r['Historial_Actuaciones'] = df_proc_r['radicado_interno'].map(actuaciones_consolidadas)
        
        df_proc_r.to_excel(writer, sheet_name='Procesos', index=False)
        df_venc_r.to_excel(writer, sheet_name='Vencimientos', index=False)
        df_gas_r.to_excel(writer, sheet_name='Gastos', index=False)
        df_cont_r.to_excel(writer, sheet_name='Directorio', index=False)
        df_act_r.to_excel(writer, sheet_name='Actuaciones', index=False)
        
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Descargar Reporte Ejecutivo (.xlsx)",
        data=excel_data,
        file_name=f"informe_judicial_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==========================================
# SECCIÓN 6: ADMINISTRACIÓN 
# ==========================================
elif menu == "👥 Administración":
    st.header("Administración de Perfiles y Seguridad")
    if usuario_rol == "Maestro":
        c_m1, c_m2 = st.columns([1, 1.5])
        with c_m1:
            st.subheader("➕ Nuevo Usuario")
            with st.form("form_abg", clear_on_submit=True):
                n_abg = st.text_input("Nombre Completo").upper()
                e_abg = st.text_input("Correo Electrónico")
                t_abg = st.text_input("Teléfono")
                p_abg = st.text_input("Contraseña de Acceso", type="password")
                r_abg = st.selectbox("Rol del Sistema", ["Abogado", "Maestro"])
                if st.form_submit_button("💾 Crear Perfil"):
                    try:
                        conn_m = conectar_bd()
                        conn_m.cursor().execute("INSERT INTO abogados (nombre, email, telefono, rol, password) VALUES (?, ?, ?, ?, ?)", (n_abg, e_abg, t_abg, r_abg, p_abg if p_abg else "1234"))
                        conn_m.commit()
                        conn_m.close()
                        st.session_state['toast_msg'] = "Perfil creado con éxito."
                        st.session_state['toast_icon'] = "👥"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe un usuario registrado con ese nombre.")
        with c_m2:
            st.subheader("✏️ Gestión de Credenciales")
            conn = conectar_bd()
            df_abg = pd.read_sql_query("SELECT id, nombre, email, telefono, rol FROM abogados", conn)
            conn.close()
            if not df_abg.empty:
                abg_editar = st.selectbox("Seleccionar usuario:", df_abg['nombre'].tolist())
                datos_a = df_abg[df_abg['nombre'] == abg_editar].iloc[0]
                with st.form(key="edit_abg"):
                    ed_n = st.text_input("Nombre", value=datos_a['nombre']).upper()
                    ed_e = st.text_input("Correo", value=datos_a['email'])
                    ed_t = st.text_input("Teléfono", value=datos_a['telefono'])
                    ed_p = st.text_input("Nueva Contraseña (dejar en blanco para mantener actual)", type="password")
                    ed_r = st.selectbox("Rol", ["Abogado", "Maestro"], index=0 if datos_a['rol'] == "Abogado" else 1)
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("💾 Guardar Cambios"):
                        conn_ea = conectar_bd()
                        if ed_p:
                            conn_ea.cursor().execute("UPDATE abogados SET nombre=?, email=?, telefono=?, rol=?, password=? WHERE id=?", (ed_n, ed_e, ed_t, ed_r, ed_p, int(datos_a['id'])))
                        else:
                            conn_ea.cursor().execute("UPDATE abogados SET nombre=?, email=?, telefono=?, rol=? WHERE id=?", (ed_n, ed_e, ed_t, ed_r, int(datos_a['id'])))
                        conn_ea.commit()
                        conn_ea.close()
                        st.session_state['toast_msg'] = "Modificaciones de seguridad guardadas."
                        st.session_state['toast_icon'] = "🔐"
                        st.rerun()
                    if c_b2.form_submit_button("🗑️ Eliminar Perfil"):
                        if abg_editar == "ADMINISTRADOR MAESTRO":
                            st.error("No es posible eliminar al administrador principal.")
                        else:
                            conn_da = conectar_bd()
                            conn_da.cursor().execute("DELETE FROM abogados WHERE id=?", (int(datos_a['id']),))
                            conn_da.commit()
                            conn_da.close()
                            st.session_state['toast_msg'] = "Perfil eliminado."
                            st.session_state['toast_icon'] = "🗑️"
                            st.rerun()
            st.dataframe(df_abg, use_container_width=True)
    else:
        st.warning("Acceso restringido. Se requiere rol de Administrador Maestro.")
