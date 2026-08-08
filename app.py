import streamlit as st
import psycopg2
import pandas as pd
import unicodedata
from datetime import datetime, date, timedelta
import holidays
import io
import json
import plotly.express as px
from streamlit_option_menu import option_menu
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO DARK MODE ---
st.set_page_config(page_title="Sistema de Gestión Judicial", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { 
        background-color: #000000; 
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
        color: #f2f2f7;
    }
    
    h1, h2, h3 { color: #f2f2f7 !important; font-weight: 600 !important; letter-spacing: -0.025em; }
    
    .stTextInput label, .stSelectbox label, .stRadio label, .stDateInput label, .stTextArea label, .stNumberInput label, .stMultiSelect label {
        font-weight: 500 !important; color: #8e8e93 !important; font-size: 13px !important;
    }
    
    input[type="text"], textarea, input[type="number"], input[type="password"] {
        background-color: #1c1c1e !important; border: 1px solid #38383a !important; border-radius: 10px !important; 
        padding: 10px 14px !important; color: #f2f2f7 !important;
    }
    
    input[type="text"]:focus, textarea:focus, input[type="number"]:focus, input[type="password"]:focus {
        border-color: #0a84ff !important; box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.15) !important;
    }
    
    .ficha-tecnica {
        background: rgba(28, 28, 30, 0.8); backdrop-filter: blur(12px); padding: 20px; border-radius: 12px;
        border-left: 4px solid #0a84ff; margin-bottom: 20px; font-size: 14px; color: #e5e5ea; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
    }
    
    .user-badge {
        background: linear-gradient(135deg, #1c1c1e 0%, #2c2c2e 100%); color: #f2f2f7; padding: 10px 14px;
        border-radius: 10px; font-size: 13px; font-weight: 500; display: inline-block; margin-bottom: 15px;
        border: 1px solid #38383a; width: 100%; text-align: center;
    }
    
    .metric-card {
        background: #1c1c1e; border: 1px solid #38383a; border-radius: 14px; padding: 22px; text-align: center; 
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); transition: transform 0.25s ease, border-color 0.25s ease;
    }
    
    .metric-card:hover { transform: translateY(-4px); border-color: #0a84ff; }
    
    div[data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1c1c1e; }
    
    div[data-baseweb="select"] > div {
        background-color: #1c1c1e !important; border-color: #38383a !important; color: #f2f2f7 !important; border-radius: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Gestión Judicial")

# --- CONEXIÓN A POSTGRESQL (NEON POOLED) ---
def conectar_bd():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

@st.cache_data(ttl=60)
def cargar_abogados():
    conn = conectar_bd()
    df = pd.read_sql_query("SELECT id, nombre, rol, password, email, telefono FROM abogados", conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def cargar_procesos_general():
    conn = conectar_bd()
    query = '''SELECT p.*, c.nombre AS demandante_db, a.nombre AS abogado_asignado FROM procesos p LEFT JOIN clientes c ON p.id_cliente = c.identificacion LEFT JOIN abogados a ON p.abogado_id = a.id'''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def cargar_contactos_general():
    conn = conectar_bd()
    df = pd.read_sql_query("SELECT * FROM contactos", conn)
    conn.close()
    return df

def limpiar_identificacion(texto):
    if pd.isna(texto) or not texto: return ""
    return str(texto).replace(".", "").replace(",", "").replace(" ", "").strip().upper()

def obtener_nombres_demandantes(id_cliente_str, conn):
    if not id_cliente_str: return "DEMANDANTE"
    ids = [i.strip() for i in str(id_cliente_str).split("|")]
    nombres = []
    cursor = conn.cursor()
    for i in ids:
        try:
            cursor.execute("SELECT nombre FROM clientes WHERE identificacion = %s", (i,))
            res = cursor.fetchone()
            if res:
                nombres.append(res[0])
            else:
                cursor.execute("SELECT nombre FROM contactos WHERE identificacion = %s", (i,))
                res2 = cursor.fetchone()
                if res2: nombres.append(res2[0])
                else: nombres.append(i)
        except:
            nombres.append(i)
    return " / ".join(nombres) if nombres else "DEMANDANTE"

def registrar_auditoria(conn, usuario, accion, tabla, registro_id, estado_anterior, estado_nuevo, datos_json):
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO auditoria (usuario, accion, tabla, registro_id, estado_anterior, estado_nuevo, datos_json) 
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (usuario, accion, tabla, str(registro_id), str(estado_anterior), str(estado_nuevo), datos_json)
    )
    conn.commit()

def crear_tablas():
    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS clientes (identificacion TEXT PRIMARY KEY, nombre TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS abogados (id SERIAL PRIMARY KEY, nombre TEXT UNIQUE, email TEXT, telefono TEXT, rol TEXT DEFAULT 'Abogado', password TEXT DEFAULT '1234')''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS procesos (
                radicado_interno TEXT PRIMARY KEY, radicado_rama TEXT, naturaleza TEXT,
                juzgado TEXT, etapa_actual TEXT, id_cliente TEXT, demandado TEXT, id_demandado TEXT, estado TEXT DEFAULT 'Activo',
                pretensiones NUMERIC, medidas_cautelares TEXT, abogado_id INTEGER
            )
        ''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS actuaciones (id SERIAL PRIMARY KEY, radicado_interno TEXT, fecha TEXT, etapa TEXT, descripcion TEXT, usuario TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS vencimientos (id SERIAL PRIMARY KEY, radicado_interno TEXT, titulo TEXT, fecha_vencimiento TEXT, estado TEXT DEFAULT 'Pendiente', observaciones TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS contactos (id SERIAL PRIMARY KEY, nombre TEXT, tipo TEXT, telefono TEXT, email TEXT, direccion TEXT, ciudad TEXT, identificacion TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS gastos (id SERIAL PRIMARY KEY, radicado_interno TEXT, fecha TEXT, concepto TEXT, valor NUMERIC)''')
        
        # Tabla de Auditoría y Papelera
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auditoria (
                id SERIAL PRIMARY KEY,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario TEXT,
                accion TEXT,
                tabla TEXT,
                registro_id TEXT,
                estado_anterior TEXT,
                estado_nuevo TEXT,
                datos_json TEXT
            )
        ''')
        
        # Migraciones seguras automáticas (incluyendo soporte para IA y revisión de robot)
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'abogados'")
        cols_abgs = [col[0] for col in cursor.fetchall()]
        if 'email' not in cols_abgs: cursor.execute("ALTER TABLE abogados ADD COLUMN email TEXT")
        if 'telefono' not in cols_abgs: cursor.execute("ALTER TABLE abogados ADD COLUMN telefono TEXT")
        if 'password' not in cols_abgs: cursor.execute("ALTER TABLE abogados ADD COLUMN password TEXT DEFAULT '1234'")
        if 'rol' not in cols_abgs: cursor.execute("ALTER TABLE abogados ADD COLUMN rol TEXT DEFAULT 'Abogado'")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'procesos'")
        cols_procesos = [col[0] for col in cursor.fetchall()]
        if 'abogado_id' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN abogado_id INTEGER")
        if 'pretensiones' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN pretensiones NUMERIC")
        if 'medidas_cautelares' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN medidas_cautelares TEXT")
        if 'estado' not in cols_procesos: cursor.execute("ALTER TABLE procesos ADD COLUMN estado TEXT DEFAULT 'Activo'")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'contactos'")
        cols_contactos = [col[0] for col in cursor.fetchall()]
        if 'identificacion' not in cols_contactos: cursor.execute("ALTER TABLE contactos ADD COLUMN identificacion TEXT")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'actuaciones'")
        cols_act = [col[0] for col in cursor.fetchall()]
        if 'usuario' not in cols_act: cursor.execute("ALTER TABLE actuaciones ADD COLUMN usuario TEXT")
        if 'tipificacion_sugerida' not in cols_act: cursor.execute("ALTER TABLE actuaciones ADD COLUMN tipificacion_sugerida TEXT")
        if 'tipificacion_definitiva' not in cols_act: cursor.execute("ALTER TABLE actuaciones ADD COLUMN tipificacion_definitiva TEXT")
        if 'revisado' not in cols_act: cursor.execute("ALTER TABLE actuaciones ADD COLUMN revisado BOOLEAN DEFAULT FALSE")
            
        cursor.execute("SELECT COUNT(*) FROM abogados")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO abogados (nombre, email, telefono, rol, password) VALUES (%s, %s, %s, %s, %s)", ("ADMINISTRADOR MAESTRO", "admin@firma.com", "3000000000", "Maestro", "1234"))
        
        # SISTEMA SECUENCIAL BLINDADO
        cursor.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor INTEGER)")
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'secuencia_exp'")
        if not cursor.fetchone():
            cursor.execute("SELECT radicado_interno FROM procesos")
            act = cursor.fetchall()
            cursor.execute("SELECT registro_id FROM auditoria WHERE tabla = 'procesos'")
            borr = cursor.fetchall()
            max_n = 0
            for r in act + borr:
                try:
                    num = int(r[0].split("-")[1])
                    if num > max_n: max_n = num
                except: pass
            cursor.execute("INSERT INTO configuracion (clave, valor) VALUES ('secuencia_exp', %s)", (max_n,))

        conn.commit()
    finally:
        conn.close()

try:
    crear_tablas()
except Exception as e:
    st.error(f"Error conectando a Neon: {e}")

# --- CONTROL DE ACCESO ---
st.sidebar.title("Control de Acceso")
abogados_db = cargar_abogados()

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
    
    st.sidebar.markdown(f"<div class='user-badge'>👤 <b>{usuario_seleccionado}</b><br><span style='color:#8e8e93;'>{usuario_rol}</span></div>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.usuario_nombre = None
        st.session_state.usuario_id = None
        st.session_state.usuario_rol = None
        st.rerun()
        
    st.sidebar.markdown("---")
    
    with st.sidebar:
        menu = option_menu(
            menu_title=None,
            options=["Inicio", "Bandeja de Estados", "Nuevo Proceso", "Expedientes", "Vencimientos", "Directorio", "Informes", "Administración"],
            icons=["house", "inbox", "file-earmark-plus", "folder2-open", "alarm", "book", "graph-up", "people"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#8e8e93", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px", "text-align": "left", "margin":"4px 0px", 
                    "padding": "12px", "color": "#f2f2f7", "border-radius": "10px", "font-weight": "600"
                },
                "nav-link-selected": { "background-color": "#1c1c1e", "color": "#0a84ff", "border": "1px solid #38383a" },
            }
        )

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

def previsualizar_siguiente_radicado():
    conn = conectar_bd()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'secuencia_exp'")
        actual = cursor.fetchone()[0]
        return f"EXP-{actual + 1:04d}"
    finally:
        conn.close()

def consumir_siguiente_radicado(cursor):
    cursor.execute("UPDATE configuracion SET valor = valor + 1 WHERE clave = 'secuencia_exp' RETURNING valor")
    nuevo = cursor.fetchone()[0]
    return f"EXP-{nuevo:04d}"

lista_procesos = [
    "EJECUTIVO SINGULAR", "EJECUTIVO HIPOTECARIO", "EJECUTIVO MIXTO", 
    "EJECUTIVO LABORAL", "EJECUTIVO CONTENCIOSO",
    "CIVIL: VERBAL", "CIVIL: VERBAL SUMARIO", "CIVIL: MONITORIO", "CIVIL: ESPECIAL DECLARATIVO",
    "CIVIL: SUCESIÓN", "CIVIL: LIQUIDACIÓN DE SOCIEDAD", "CIVIL: INSOLVENCIA", "CIVIL: JURISDICCIÓN VOLUNTARIA",
    "FAMILIA: DIVORCIO / NULIDAD", "FAMILIA: ALIMENTOS / CUSTODIA", "FAMILIA: INVESTIGACIÓN PATERNIDAD", "FAMILIA: ADOPCIÓN",
    "LABORAL: ORDINARIO", "LABORAL: MONITORIO", "LABORAL: FUERO", "LABORAL: CALIFICACIÓN DE HUELGA",
    "CONTENCIOSO: NULIDAD Y RESTABLECIMIENTO", "CONTENCIOSO: REPARACIÓN DIRECTA", "CONTENCIOSO: CONTROVERSIAS CONTRACTUALES", 
    "CONTENCIOSO: ACCIÓN DE REPETICIÓN", "CONTENCIOSO: PROTECCIÓN DERECHOS COLECTIVOS",
    "OTRO"
]

lista_etapas = [
    "1. Presentación de la demanda", "2. Inadmisión", "3. Admisión", 
    "4. Medidas Cautelares", "5. Notificación", "6. Excepciones", 
    "7. Sentencia", "8. Desistimiento tácito"
]
lista_juzgados_esp = ["CIVIL MUNICIPAL", "CIVIL DEL CIRCUITO", "LABORAL", "DE FAMILIA", "PROMISCUO MUNICIPAL", "DE PEQUEÑAS CAUSAS", "ADMINISTRATIVO", "PENAL"]

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

if 'toast_msg' in st.session_state:
    st.toast(st.session_state['toast_msg'], icon=st.session_state.get('toast_icon', '✅'))
    del st.session_state['toast_msg']
    if 'toast_icon' in st.session_state: del st.session_state['toast_icon']

if 'form_key' not in st.session_state: st.session_state.form_key = 0
fk = st.session_state.form_key 

if 'num_dem_nuevos' not in st.session_state: st.session_state.num_dem_nuevos = 0
if 'num_ddo_nuevos' not in st.session_state: st.session_state.num_ddo_nuevos = 0

# ==========================================
# SECCIÓN 0: INICIO (DASHBOARD GERENCIAL)
# ==========================================
if menu == "Inicio":
    st.header(f"Panel de Control | {usuario_seleccionado}")
    st.write("Panorama operativo general de la práctica jurídica y agenda de términos.")
    
    conn = conectar_bd()
    try:
        limite_urgente = str(date.today() + timedelta(days=5))
        hoy_str = str(date.today())
        
        query_kpis = f"""
            SELECT 
                (SELECT COUNT(*) FROM procesos WHERE estado='Activo') as total_activos,
                (SELECT COUNT(*) FROM procesos WHERE estado='Terminado') as total_terminados,
                (SELECT COALESCE(SUM(pretensiones), 0) FROM procesos WHERE estado='Activo' AND naturaleza LIKE '%EJECUTIVO%') as sum_pretensiones,
                (SELECT COUNT(*) FROM vencimientos WHERE estado='Pendiente' AND fecha_vencimiento <= '{limite_urgente}') as venc_urgentes
        """
        df_kpis = pd.read_sql_query(query_kpis, conn)
        total_activos = int(df_kpis.iloc[0]['total_activos'])
        total_terminados = int(df_kpis.iloc[0]['total_terminados'])
        sum_pretensiones = float(df_kpis.iloc[0]['sum_pretensiones'])
        venc_urgentes_df = int(df_kpis.iloc[0]['venc_urgentes'])
        
        radar_df = pd.read_sql_query(f"SELECT * FROM vencimientos WHERE estado='Pendiente' AND fecha_vencimiento <= '{limite_urgente}' ORDER BY fecha_vencimiento ASC", conn)
    finally:
        conn.close()
    
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        st.markdown(f"<div class='metric-card'><h2 style='color:#0a84ff;margin:0;font-size:32px;'>📁 {total_activos}</h2><p style='color:#8e8e93;margin:5px 0 0 0;font-weight:500;'>Procesos Activos</p></div>", unsafe_allow_html=True)
    with col_k2:
        st.markdown(f"<div class='metric-card'><h2 style='color:#ff453a;margin:0;font-size:32px;'>🚨 {venc_urgentes_df}</h2><p style='color:#8e8e93;margin:5px 0 0 0;font-weight:500;'>Términos (Próx. 5 días)</p></div>", unsafe_allow_html=True)
    with col_k3:
        st.markdown(f"<div class='metric-card'><h2 style='color:#30d158;margin:0;font-size:26px;'>💰 ${sum_pretensiones:,.0f}</h2><p style='color:#8e8e93;margin:5px 0 0 0;font-weight:500;'>Capital Ejecutivo Activo</p></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    c_grafico, c_radar = st.columns([1, 1.5])
    
    with c_grafico:
        st.subheader("Balance de Expedientes")
        if total_activos == 0 and total_terminados == 0:
            st.info("No hay procesos registrados para graficar.")
        else:
            df_chart = pd.DataFrame({'Estado': ['Activos', 'Terminados'], 'Cantidad': [total_activos, total_terminados]})
            fig = px.pie(df_chart, names='Estado', values='Cantidad', hole=0.6, color_discrete_sequence=['#0a84ff', '#38383a'])
            fig.update_layout(showlegend=True, margin=dict(t=20, b=20, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#f2f2f7"))
            st.plotly_chart(fig, use_container_width=True)

    with c_radar:
        st.subheader("Radar de Vencimientos")
        if not radar_df.empty:
            for idx, r in radar_df.iterrows():
                estado_alerta = "🔴 VENCIDO" if r['fecha_vencimiento'] < hoy_str else "⚠️ VENCE HOY" if r['fecha_vencimiento'] == hoy_str else "⏰ Próximo a vencer"
                st.warning(f"**[{estado_alerta}]** | Expediente: **{r['radicado_interno']}** | Tarea: **{r['titulo']}** | Límite: **{r['fecha_vencimiento']}**")
        else:
            st.success("✅ Agenda limpia. No hay términos críticos para los próximos 5 días.")

# ==========================================
# SECCIÓN: BANDEJA DE ESTADOS (ROBOT IA)
# ==========================================
elif menu == "Bandeja de Estados":
    st.header("📌 Bandeja de Entrada de Novedades Judiciales")
    st.markdown("Revisa aquí la última actuación detectada por el robot para cada expediente, valida la tipificación y marca como revisado.")
    
    conn = conectar_bd()
    try:
        # Usamos DISTINCT ON para traer UNICAMENTE la actuación más reciente por cada radicado
        query_bandeja = """
            DISTINCT ON (p.radicado_interno)
                a.id,
                p.radicado_interno,
                p.juzgado,
                p.demandado,
                a.fecha,
                a.descripcion,
                a.tipificacion_sugerida,
                a.tipificacion_definitiva,
                a.revisado
            FROM actuaciones a
            JOIN procesos p ON a.radicado_interno = p.radicado_interno
            WHERE a.revisado = FALSE
            ORDER BY p.radicado_interno, a.fecha DESC, a.id DESC;
        """
        # Sintaxis segura compatible con pandas/psycopg2 para DISTINCT ON
        query_final = f"SELECT {query_bandeja}"
        df_pendientes = pd.read_sql_query(query_final, conn)
    finally:
        conn.close()
        
    if df_pendientes.empty:
        st.success("🎉 ¡Excelente trabajo! No hay actuaciones pendientes por revisar en este momento.")
    else:
        st.info(f"Tienes **{len(df_pendientes)}** expedientes con novedades recientes pendientes de validación.")
        
        df_editable = df_pendientes.copy()
        
        # Limpieza segura de nulos y unificación con la sugerencia de la IA
        if 'tipificacion_definitiva' in df_editable.columns:
            df_editable['tipificacion_definitiva'] = df_editable['tipificacion_definitiva'].fillna(df_editable['tipificacion_sugerida']).fillna("Sin clasificar")
        else:
            df_editable['tipificacion_definitiva'] = df_editable['tipificacion_sugerida'].fillna("Sin clasificar")
            
        # Incluimos "Sin clasificar" en las opciones para evitar errores de validación en el editor
        opciones_tipificacion = [
            "Sin clasificar",
            "Mandamiento de Pago", 
            "Admisión de Demanda", 
            "Rechazo / Inadmisión", 
            "Traslado", 
            "Oficio / Despacho Comisorio", 
            "Liquidación de Crédito / Costas", 
            "Auto de Trámite / General", 
            "Terminación del Proceso"
        ]
        
        st.markdown("### 📝 Panel de Validación Rápida")
        st.markdown("Modifica la tipificación desplegando la celda si lo deseas y marca la casilla **Revisado** para retirar el expediente de tu bandeja.")
        
        df_resultado = st.data_editor(
            df_editable,
            column_config={
                "id": None,
                "radicado_interno": st.column_config.TextColumn("Expediente", disabled=True),
                "juzgado": st.column_config.TextColumn("Juzgado", disabled=True),
                "demandado": st.column_config.TextColumn("Parte Demandada", disabled=True),
                "fecha": st.column_config.TextColumn("Fecha Actuación", disabled=True),
                "descripcion": st.column_config.TextColumn("Texto del Juzgado", disabled=True),
                "tipificacion_sugerida": st.column_config.TextColumn("Sugerencia IA", disabled=True),
                "tipificacion_definitiva": st.column_config.SelectboxColumn(
                    "Tipificación Definitiva", options=opciones_tipificacion, required=True
                ),
                "revisado": st.column_config.CheckboxColumn("¿Revisado? ✅", default=False)
            },
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("💾 Guardar Cambios y Actualizar Bandeja", type="primary"):
            conn_upd = conectar_bd()
            try:
                cursor = conn_upd.cursor()
                actualizados = 0
                for index, row in df_resultado.iterrows():
                    cursor.execute("""
                        UPDATE actuaciones 
                        SET tipificacion_definitiva = %s, revisado = %s 
                        WHERE id = %s
                    """, (row['tipificacion_definitiva'], row['revisado'], row['id']))
                    actualizados += 1
                conn_upd.commit()
            finally:
                conn_upd.close()
                
            st.cache_data.clear()
            st.session_state['toast_msg'] = f"¡Se actualizaron {actualizados} registros correctamente!"
            st.session_state['toast_icon'] = "✅"
            st.rerun()

# ==========================================
# SECCIÓN 1: REGISTRAR PROCESO
# ==========================================
elif menu == "Nuevo Proceso":
    st.header("Registro de Nuevo Proceso (Soporta Litisconsorcio)")
    
    with st.container(border=True):
        st.subheader("1. Identificación Básica")
        col_id1, col_id2 = st.columns(2)
        radicado_preview = previsualizar_siguiente_radicado()
        col_id1.text_input("Radicado Interno (Automático)", value=radicado_preview, disabled=True, key=f"rad_int_{fk}")
        naturaleza = col_id2.selectbox("Naturaleza del Proceso", lista_procesos, key=f"nat_{fk}")
    
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
        st.subheader("3. Partes Intervinientes (Litisconsorcio)")
        st.caption("Los puntos o espacios en las cédulas serán eliminados automáticamente para mantener la base de datos estandarizada.")
        
        contactos_df = cargar_contactos_general()
        clientes_db = contactos_df[contactos_df['tipo'] == 'Cliente'] if not contactos_df.empty else pd.DataFrame()
        lista_opciones_c = (clientes_db['identificacion'] + " - " + clientes_db['nombre']).tolist() if not clientes_db.empty else []
        
        contrapartes_db = contactos_df[contactos_df['tipo'] == 'Contraparte'] if not contactos_df.empty else pd.DataFrame()
        lista_opciones_d = (contrapartes_db['identificacion'] + " - " + contrapartes_db['nombre']).tolist() if not contrapartes_db.empty else []
        
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.markdown("**Demandantes / Clientes**")
            clientes_existentes = st.multiselect("1. Seleccionar del directorio:", lista_opciones_c, key=f"cli_sel_{fk}")
            
            st.markdown("**2. Registrar nuevos:**")
            if st.button("➕ Agregar demandante", key=f"add_dem_{fk}"):
                st.session_state.num_dem_nuevos += 1
                st.rerun()
                
            nuevos_clientes_data = []
            for i in range(st.session_state.num_dem_nuevos):
                with st.container(border=True):
                    c_id, c_nom = st.columns([1, 1.8])
                    nid = c_id.text_input("CC/NIT", key=f"n_cli_id_{fk}_{i}", placeholder="Ej: 1088123456")
                    nom = c_nom.text_input("Nombre completo", key=f"n_cli_nom_{fk}_{i}")
                    nuevos_clientes_data.append((nid, nom))
                
        with col_d2:
            st.markdown("**Demandados / Contrapartes**")
            demandados_existentes = st.multiselect("1. Seleccionar del directorio:", lista_opciones_d, key=f"dem_sel_{fk}")
            
            st.markdown("**2. Registrar nuevos:**")
            if st.button("➕ Agregar demandado", key=f"add_ddo_{fk}"):
                st.session_state.num_ddo_nuevos += 1
                st.rerun()
                
            nuevos_demandados_data = []
            for i in range(st.session_state.num_ddo_nuevos):
                with st.container(border=True):
                    c_id, c_nom = st.columns([1, 1.8])
                    nid = c_id.text_input("CC/NIT", key=f"n_ddo_id_{fk}_{i}", placeholder="Ej: 900123456")
                    nom = c_nom.text_input("Nombre completo", key=f"n_ddo_nom_{fk}_{i}")
                    nuevos_demandados_data.append((nid, nom))
                
    with st.container(border=True):
        st.subheader("4. Pretensiones, Medidas y Asignación")
        col_p1, col_p2 = st.columns([1, 1])
        pretensiones = col_p1.number_input("Pretensiones / Cuantía ($)", min_value=0.0, step=50000.0, key=f"pret_{fk}")
        
        abogados_activos = cargar_abogados()
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
                    detalles_mc.append(f"{mc} ({detalle})" if detalle else mc)
        medidas_finales = " | ".join(detalles_mc)
    
    if st.button("💾 Guardar Proceso en el Sistema", use_container_width=True):
        faltan_datos_nuevos = any((c[0] and not c[1]) or (c[1] and not c[0]) for c in nuevos_clientes_data) or any((d[0] and not d[1]) or (d[1] and not d[0]) for d in nuevos_demandados_data)

        if faltan_datos_nuevos:
            st.error("⚠️ Para registrar nuevas partes, debe diligenciar tanto la cédula como el nombre de cada uno.")
        elif not (clientes_existentes or any(c[0] and c[1] for c in nuevos_clientes_data)):
            st.error("⚠️ Debe ingresar o seleccionar al menos un Demandante/Cliente.")
        elif not (demandados_existentes or any(d[0] and d[1] for d in nuevos_demandados_data)):
            st.error("⚠️ Debe ingresar o seleccionar al menos un Demandado/Contraparte.")
        else:
            conn = conectar_bd()
            try:
                cursor = conn.cursor()
                
                # Consumo final del autoincremental
                radicado_interno_real = consumir_siguiente_radicado(cursor)
                
                nombres_dem, ids_dem = [], []
                for c in clientes_existentes:
                    i, n = c.split(" - ", 1)
                    ids_dem.append(i); nombres_dem.append(n)
                    
                for cid, cnom in nuevos_clientes_data:
                    if cid and cnom:
                        i = limpiar_identificacion(cid)
                        n = cnom.strip().upper()
                        ids_dem.append(i); nombres_dem.append(n)
                        cursor.execute('''INSERT INTO clientes (identificacion, nombre) VALUES (%s, %s) ON CONFLICT (identificacion) DO NOTHING''', (i, n))
                        cursor.execute('''INSERT INTO contactos (identificacion, nombre, tipo, ciudad) VALUES (%s, %s, 'Cliente', 'PEREIRA')''', (i, n))
                
                nombres_ddo, ids_ddo = [], []
                for d in demandados_existentes:
                    i, n = d.split(" - ", 1)
                    ids_ddo.append(i); nombres_ddo.append(n)
                    
                for did, dnom in nuevos_demandados_data:
                    if did and dnom:
                        i = limpiar_identificacion(did)
                        n = dnom.strip().upper()
                        ids_ddo.append(i); nombres_ddo.append(n)
                        cursor.execute('''INSERT INTO contactos (identificacion, nombre, tipo, ciudad) VALUES (%s, %s, 'Contraparte', 'PEREIRA')''', (i, n))
                
                id_demandante_final = " | ".join(ids_dem)
                nombre_demandado_final = " | ".join(nombres_ddo)
                id_demandado_final = " | ".join(ids_ddo)

                cursor.execute('''INSERT INTO procesos (radicado_interno, radicado_rama, naturaleza, juzgado, etapa_actual, id_cliente, demandado, id_demandado, estado, pretensiones, medidas_cautelares, abogado_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', (radicado_interno_real, radicado_rama, naturaleza, juzgado_final, lista_etapas[0], id_demandante_final, nombre_demandado_final, id_demandado_final, "Activo", pretensiones, medidas_finales, abogado_asignado_id))
                
                fecha_hoy = str(date.today())
                cursor.execute('''INSERT INTO actuaciones (radicado_interno, fecha, etapa, descripcion, usuario) VALUES (%s, %s, %s, %s, %s)''', (radicado_interno_real, fecha_hoy, lista_etapas[0], "Radicación: Presentación inicial de la demanda.", usuario_seleccionado))
                
                if "EJECUTIVO" in naturaleza:
                    fecha_alarma = sumar_dias_habiles(fecha_hoy, 30)
                    cursor.execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento) VALUES (%s, %s, %s)", (radicado_interno_real, "Radicación", fecha_alarma))

                datos_reg = {"radicado_interno": radicado_interno_real, "naturaleza": naturaleza, "juzgado": juzgado_final, "demandado": nombre_demandado_final}
                registrar_auditoria(conn, usuario_seleccionado, "CREACION", "procesos", radicado_interno_real, "", "Creado", json.dumps(datos_reg))

                conn.commit() 
                st.session_state.num_dem_nuevos = 0
                st.session_state.num_ddo_nuevos = 0
                st.session_state.form_key += 1 
                st.cache_data.clear()
                st.session_state['toast_msg'] = f"Expediente {radicado_interno_real} registrado correctamente en Neon."
                st.session_state['toast_icon'] = "☁️"
                st.rerun() 
            except Exception as e:
                st.error(f"Error al guardar: {e}")
            finally:
                conn.close()

# ==========================================
# SECCIÓN 2: EXPEDIENTES
# ==========================================
elif menu == "Expedientes":
    st.header("Gestión de Expedientes")
    df_procesos = cargar_procesos_general()
    abogados_df = cargar_abogados()
    
    if not df_procesos.empty:
        df_procesos = df_procesos.fillna("")
        
        with st.container(border=True):
            busqueda = st.text_input("Filtrar por radicado, partes intervinientes o despacho:", placeholder="Ej: EXP-0001, Empresa SAS...", label_visibility="collapsed").strip()
        
        if busqueda:
            bus_limpia = limpiar_texto(busqueda)
            df_procesos['busqueda_aux'] = df_procesos.apply(lambda r: limpiar_texto(r['radicado_interno']) + " " + limpiar_texto(r['radicado_rama']) + " " + limpiar_texto(r['id_cliente']) + " " + limpiar_texto(r['demandado']) + " " + limpiar_texto(r['abogado_asignado']), axis=1)
            df_filtrado = df_procesos[df_procesos['busqueda_aux'].str.contains(bus_limpia, na=False)]
        else:
            df_filtrado = df_procesos.copy()
            
        st.write(f"Mostrando **{len(df_filtrado)}** expediente(s). Seleccione una fila para abrir su carpeta.")
            
        if not df_filtrado.empty:
            df_mostrar = df_filtrado[['radicado_interno', 'radicado_rama', 'naturaleza', 'demandado', 'juzgado', 'etapa_actual', 'estado']]
            evento = st.dataframe(df_mostrar, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            filas_seleccionadas = evento.selection.rows
            
            if filas_seleccionadas:
                proceso_fila = df_filtrado.iloc[filas_seleccionadas[0]]
                radicado_seleccionado = proceso_fila['radicado_interno']
                id_dem = proceso_fila['id_cliente'] if proceso_fila['id_cliente'] else "N/A"
                id_ddo = proceso_fila['id_demandado'] if proceso_fila['id_demandado'] else "N/A"
                medidas_texto = proceso_fila['medidas_cautelares'] if proceso_fila['medidas_cautelares'] else "No registradas"
                estado_proceso = proceso_fila['estado'] if 'estado' in proceso_fila else "Activo"
                es_ejecutivo = "EJECUTIVO" in proceso_fila['naturaleza']
                try: val_pret_ficha = float(proceso_fila['pretensiones']) if proceso_fila['pretensiones'] else 0.0
                except: val_pret_ficha = 0.0
                
                conn_n = conectar_bd()
                try:
                    nombre_demandante_str = obtener_nombres_demandantes(proceso_fila['id_cliente'], conn_n)
                finally:
                    conn_n.close()
                
                st.markdown("---")
                with st.container(border=True):
                    st.markdown(f"""
                        <div style='text-align: center; margin-bottom: 25px;'>
                            <h2 style='color: #f2f2f7; margin-bottom: 5px; font-size: 26px; font-weight: bold;'>{nombre_demandante_str} VS {proceso_fila['demandado']}</h2>
                            <div style='color: #8e8e93; font-size: 13px; margin-top: -5px;'>
                                <span style='display: inline-block; width: 45%; text-align: right; padding-right: 25px;'>Identificación Demandante(s): {id_dem}</span>
                                <span style='display: inline-block; width: 45%; text-align: left; padding-left: 25px;'>Identificación Demandado(s): {id_ddo}</span>
                            </div>
                        </div>
                        <div class='ficha-tecnica'>
                            <b>Naturaleza:</b> {proceso_fila['naturaleza']}<br><b>Despacho:</b> {proceso_fila['juzgado']}<br>
                            <b>Radicado Rama:</b> {proceso_fila['radicado_rama']}<br><b>Expediente Interno:</b> {radicado_seleccionado} | <b>Estado:</b> {estado_proceso}<br>
                            <b>Pretensiones / Cuantía:</b> ${val_pret_ficha:,.2f}<br><b>Medidas Cautelares:</b> {medidas_texto}<br>
                            <b>Abogado Responsable:</b> {proceso_fila['abogado_asignado']}
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.expander("⚙️ Editar Datos Generales"):
                        with st.form(key=f"form_editar_proc_{radicado_seleccionado}"):
                            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
                            n_nat = c_e1.selectbox("Naturaleza", lista_procesos, index=lista_procesos.index(proceso_fila['naturaleza']) if proceso_fila['naturaleza'] in lista_procesos else 0, key=f"edit_nat_{radicado_seleccionado}")
                            n_dem = c_e2.text_input("Demandado(s)", value=proceso_fila['demandado'], key=f"edit_dem_{radicado_seleccionado}")
                            n_rad = c_e3.text_input("Radicado Rama", value=proceso_fila['radicado_rama'] if proceso_fila['radicado_rama'] != "EN REPARTO" else "", key=f"edit_rad_{radicado_seleccionado}")
                            n_estado = c_e4.selectbox("Estado", ["Activo", "Terminado"], index=0 if estado_proceso == "Activo" else 1, key=f"edit_est_{radicado_seleccionado}")

                            st.markdown("---")
                            st.markdown("**Actualizar Despacho Judicial**")
                            c_j1, c_j2, c_j3 = st.columns(3)
                            n_num = c_j1.selectbox("Número", list(range(1, 101)), key=f"edit_num_{radicado_seleccionado}")
                            n_tipo = c_j2.selectbox("Especialidad", lista_juzgados_esp, key=f"edit_tipo_{radicado_seleccionado}")
                            n_ciu = c_j3.text_input("Ciudad", value="PEREIRA", key=f"edit_ciu_{radicado_seleccionado}").upper()
                            
                            st.markdown("---")
                            c_e5, c_e6, c_e7 = st.columns(3)
                            n_pret = c_e5.number_input("Pretensiones ($)", value=val_pret_ficha, key=f"edit_pret_{radicado_seleccionado}")
                            
                            abogados_list = abogados_df['nombre'].tolist()
                            idx_abg = abogados_list.index(proceso_fila['abogado_asignado']) if proceso_fila['abogado_asignado'] in abogados_list else 0
                            n_abg_nombre = c_e6.selectbox("Abogado Responsable", abogados_list, index=idx_abg, key=f"edit_abg_{radicado_seleccionado}")
                            n_abg_id = abogados_df[abogados_df['nombre'] == n_abg_nombre]['id'].values[0]
                            n_med = c_e7.text_input("Medidas Cautelares", value=proceso_fila['medidas_cautelares'], key=f"edit_med_{radicado_seleccionado}")

                            if st.form_submit_button("💾 Guardar Cambios"):
                                juz_guardar = f"JUZGADO {obtener_nombre_numero(n_num)} {n_tipo} DE {n_ciu}"
                                rad_guardar = n_rad if n_rad else "EN REPARTO"
                                
                                estado_anterior_dict = dict(proceso_fila)
                                estado_nuevo_dict = {"naturaleza": n_nat, "demandado": n_dem, "radicado_rama": rad_guardar, "juzgado": juz_guardar, "pretensiones": n_pret, "medidas_cautelares": n_med, "estado": n_estado}

                                conn_up = conectar_bd()
                                try:
                                    conn_up.cursor().execute("""UPDATE procesos SET naturaleza=%s, demandado=%s, radicado_rama=%s, juzgado=%s, pretensiones=%s, medidas_cautelares=%s, abogado_id=%s, estado=%s WHERE radicado_interno=%s""", (n_nat, n_dem, rad_guardar, juz_guardar, n_pret, n_med, int(n_abg_id), n_estado, radicado_seleccionado))
                                    registrar_auditoria(conn_up, usuario_seleccionado, "MODIFICACION", "procesos", radicado_seleccionado, json.dumps(estado_anterior_dict, default=str), json.dumps(estado_nuevo_dict), json.dumps(estado_nuevo_dict))
                                    conn_up.commit()
                                finally:
                                    conn_up.close()
                                    
                                st.cache_data.clear()
                                st.session_state['toast_msg'] = "Expediente actualizado exitosamente."
                                st.session_state['toast_icon'] = "✅"
                                st.rerun()

                    # ZONA DE RIESGO: ELIMINACIÓN RESTRINGIDA AL ROL MAESTRO
                    if usuario_rol == "Maestro":
                        with st.expander("🚨 Zona de Riesgo: Eliminar Expediente (Exclusivo Maestro)"):
                            st.warning("Esta acción eliminará permanentemente el expediente y enviará una copia de respaldo estructurada a la Papelera de Auditoría.")
                            if st.button("🗑️ Eliminar Expediente Completamente", key=f"btn_del_proc_{radicado_seleccionado}"):
                                conn_del = conectar_bd()
                                try:
                                    cursor_del = conn_del.cursor()
                                    
                                    cursor_del.execute("SELECT * FROM procesos WHERE radicado_interno=%s", (radicado_seleccionado,))
                                    row_proc = cursor_del.fetchone()
                                    if row_proc:
                                        cols = [desc[0] for desc in cursor_del.description]
                                        datos_respaldo_dict = dict(zip(cols, row_proc))
                                        datos_respaldo = json.dumps(datos_respaldo_dict, default=str)
                                    else:
                                        datos_respaldo = "{}"
                                    
                                    cursor_del.execute("DELETE FROM procesos WHERE radicado_interno=%s", (radicado_seleccionado,))
                                    cursor_del.execute("DELETE FROM actuaciones WHERE radicado_interno=%s", (radicado_seleccionado,))
                                    cursor_del.execute("DELETE FROM vencimientos WHERE radicado_interno=%s", (radicado_seleccionado,))
                                    cursor_del.execute("DELETE FROM gastos WHERE radicado_interno=%s", (radicado_seleccionado,))
                                    
                                    registrar_auditoria(conn_del, usuario_seleccionado, "ELIMINACION", "procesos", radicado_seleccionado, "Activo", "Eliminado", datos_respaldo)
                                    conn_del.commit()
                                finally:
                                    conn_del.close()
                                    
                                st.cache_data.clear()
                                st.session_state['toast_msg'] = f"Expediente {radicado_seleccionado} eliminado y respaldado."
                                st.session_state['toast_icon'] = "🗑️"
                                st.rerun()
                    else:
                        st.info("🔒 Los perfiles de Abogado no tienen autorización para eliminar expedientes. Contacte al Administrador Maestro si requiere esta acción.")

                    st.markdown("---")
                    col_a1, col_a2 = st.columns([1, 1.5])
                    with col_a1:
                        st.markdown("**📝 Registrar Actuación Procesal**")
                        f_act = st.date_input("Fecha", key=f"f_act_{radicado_seleccionado}")
                        e_act = st.selectbox("Etapa Procesal", lista_etapas, key=f"e_act_{radicado_seleccionado}")
                        sub_act = st.selectbox("Sub-etapa (Plazo automático)", list(mapa_subetapas[e_act].keys()), key=f"sub_act_{radicado_seleccionado}")
                        d_act = st.text_area("Detalle / Observaciones", key=f"d_act_{radicado_seleccionado}")
                        
                        dias_alarma = mapa_subetapas[e_act][sub_act]
                        if not es_ejecutivo:
                            dias_alarma = 0
                            st.info("📌 **Proceso no ejecutivo:** Alarmas automáticas desactivadas para esta naturaleza.")
                        elif dias_alarma > 0:
                            st.success(f"⏰ Término aplicable: **{dias_alarma} días hábiles**.")
                        else:
                            st.info("📌 Opción de mera nota (Sin generación de vencimientos).")
                        
                        if st.button("💾 Guardar Actuación", use_container_width=True, key=f"btn_act_{radicado_seleccionado}"):
                            conn_ins = conectar_bd()
                            try:
                                cursor = conn_ins.cursor()
                                if sub_act != "Observación":
                                    cursor.execute("UPDATE vencimientos SET estado='Completado' WHERE radicado_interno=%s AND estado='Pendiente'", (radicado_seleccionado,))
                                
                                detalle_completo = f"{sub_act}: {d_act}" if d_act else sub_act
                                cursor.execute("INSERT INTO actuaciones (radicado_interno, fecha, etapa, descripcion, usuario) VALUES (%s, %s, %s, %s, %s)", (radicado_seleccionado, str(f_act), e_act, detalle_completo, usuario_seleccionado))
                                cursor.execute("UPDATE procesos SET etapa_actual=%s WHERE radicado_interno=%s", (e_act, radicado_seleccionado))
                                
                                if dias_alarma > 0:
                                    fecha_alarma_principal = sumar_dias_habiles(f_act, dias_alarma)
                                    cursor.execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento, observaciones) VALUES (%s, %s, %s, %s)", (radicado_seleccionado, sub_act, fecha_alarma_principal, d_act))
                                
                                registrar_auditoria(conn_ins, usuario_seleccionado, "CREACION", "actuaciones", radicado_seleccionado, "", e_act, json.dumps({"etapa": e_act, "desc": detalle_completo}))
                                conn_ins.commit()
                            finally:
                                conn_ins.close()
                                
                            st.cache_data.clear()
                            st.session_state['toast_msg'] = "Actuación registrada."
                            st.session_state['toast_icon'] = "📝"
                            st.rerun()

                    with col_a2:
                        st.markdown("**📜 Historial de Actuaciones**")
                        conn_hist = conectar_bd()
                        try:
                            hist_df = pd.read_sql_query(f"SELECT * FROM actuaciones WHERE radicado_interno='{radicado_seleccionado}' ORDER BY fecha DESC", conn_hist)
                        finally:
                            conn_hist.close()
                            
                        for idx, r in hist_df.iterrows():
                            autor_nota = f" (Por: {r['usuario']})" if 'usuario' in r and pd.notna(r['usuario']) and r['usuario'] != "" else ""
                            with st.expander(f"{r['fecha']} | {r['etapa']}{autor_nota}"):
                                with st.form(key=f"edit_act_{r['id']}"):
                                    n_f = st.text_input("Fecha", value=r['fecha'], key=f"f_act_edit_{r['id']}")
                                    n_e = st.selectbox("Etapa", lista_etapas, index=lista_etapas.index(r['etapa']) if r['etapa'] in lista_etapas else 0, key=f"e_act_edit_{r['id']}")
                                    n_d = st.text_area("Descripción", value=r['descripcion'], key=f"d_act_edit_{r['id']}")
                                    cb1, cb2 = st.columns(2)
                                    if cb1.form_submit_button("💾 Modificar", key=f"btn_mod_act_{r['id']}"):
                                        conn_u = conectar_bd()
                                        try:
                                            conn_u.cursor().execute("UPDATE actuaciones SET fecha=%s, etapa=%s, descripcion=%s WHERE id=%s", (n_f, n_e, n_d, r['id']))
                                            registrar_auditoria(conn_u, usuario_seleccionado, "MODIFICACION", "actuaciones", r['id'], r['descripcion'], n_d, json.dumps({"fecha": n_f, "etapa": n_e, "desc": n_d}))
                                            conn_u.commit()
                                        finally:
                                            conn_u.close()
                                        st.cache_data.clear()
                                        st.rerun()
                                    if cb2.form_submit_button("🗑️ Eliminar", key=f"btn_del_act_{r['id']}"):
                                        if usuario_rol == "Maestro":
                                            conn_d = conectar_bd()
                                            try:
                                                conn_d.cursor().execute("DELETE FROM actuaciones WHERE id=%s", (r['id'],))
                                                registrar_auditoria(conn_d, usuario_seleccionado, "ELIMINACION", "actuaciones", r['id'], r['descripcion'], "Eliminado", json.dumps(dict(r), default=str))
                                                conn_d.commit()
                                            finally:
                                                conn_d.close()
                                            st.cache_data.clear()
                                            st.rerun()
                                        else:
                                            st.error("🔒 Solo el Administrador Maestro puede eliminar actuaciones.")
                    
                    st.markdown("---")
                    col_g1, col_g2 = st.columns([1, 1.5])
                    with col_g1:
                        st.markdown("**💸 Control de Gastos y Costas**")
                        with st.form(f"form_gasto_{radicado_seleccionado}", clear_on_submit=True):
                            f_gasto = st.date_input("Fecha", key=f"f_gas_{radicado_seleccionado}")
                            c_gasto = st.text_input("Concepto", key=f"c_gas_{radicado_seleccionado}")
                            v_gasto = st.number_input("Valor ($)", min_value=0.0, step=10000.0, key=f"v_gas_{radicado_seleccionado}")
                            
                            if st.form_submit_button("💾 Registrar Gasto", use_container_width=True):
                                if c_gasto and v_gasto > 0:
                                    conn_g = conectar_bd()
                                    try:
                                        conn_g.cursor().execute("INSERT INTO gastos (radicado_interno, fecha, concepto, valor) VALUES (%s, %s, %s, %s)", (radicado_seleccionado, str(f_gasto), c_gasto, v_gasto))
                                        registrar_auditoria(conn_g, usuario_seleccionado, "CREACION", "gastos", radicado_seleccionado, "", str(v_gasto), json.dumps({"concepto": c_gasto, "valor": v_gasto}))
                                        conn_g.commit()
                                    finally:
                                        conn_g.close()
                                    st.cache_data.clear()
                                    st.session_state['toast_msg'] = "Gasto registrado."
                                    st.session_state['toast_icon'] = "💸"
                                    st.rerun()
                                    
                    with col_g2:
                        st.markdown("**📊 Historial Financiero del Proceso**")
                        conn_hg = conectar_bd()
                        try:
                            gastos_df = pd.read_sql_query(f"SELECT * FROM gastos WHERE radicado_interno='{radicado_seleccionado}' ORDER BY fecha DESC", conn_hg)
                        finally:
                            conn_hg.close()
                        
                        if not gastos_df.empty:
                            total_gastos = gastos_df['valor'].sum()
                            st.info(f"**Total Invertido:** ${total_gastos:,.2f}")
                            
                            for idx, r in gastos_df.iterrows():
                                with st.expander(f"🧾 {r['fecha']} | {r['concepto']} - ${r['valor']:,.2f}"):
                                    with st.form(key=f"edit_gas_{r['id']}"):
                                        n_fg = st.text_input("Fecha", value=r['fecha'], key=f"f_gas_edit_{r['id']}")
                                        n_cg = st.text_input("Concepto", value=r['concepto'], key=f"c_gas_edit_{r['id']}")
                                        n_vg = st.number_input("Valor ($)", value=float(r['valor']), key=f"v_gas_edit_{r['id']}")
                                        
                                        c_bg1, c_bg2 = st.columns(2)
                                        if c_bg1.form_submit_button("💾 Modificar", key=f"btn_mod_gas_{r['id']}"):
                                            conn_ug = conectar_bd()
                                            try:
                                                conn_ug.cursor().execute("UPDATE gastos SET fecha=%s, concepto=%s, valor=%s WHERE id=%s", (n_fg, n_cg, n_vg, r['id']))
                                                registrar_auditoria(conn_ug, usuario_seleccionado, "MODIFICACION", "gastos", r['id'], str(r['valor']), str(n_vg), json.dumps({"concepto": n_cg, "valor": n_vg}))
                                                conn_ug.commit()
                                            finally:
                                                conn_ug.close()
                                            st.cache_data.clear()
                                            st.rerun()
                                        if c_bg2.form_submit_button("🗑️ Eliminar", key=f"btn_del_gas_{r['id']}"):
                                            if usuario_rol == "Maestro":
                                                conn_dg = conectar_bd()
                                                try:
                                                    conn_dg.cursor().execute("DELETE FROM gastos WHERE id=%s", (r['id'],))
                                                    registrar_auditoria(conn_dg, usuario_seleccionado, "ELIMINACION", "gastos", r['id'], str(r['valor']), "Eliminado", json.dumps(dict(r), default=str))
                                                    conn_dg.commit()
                                                finally:
                                                    conn_dg.close()
                                                st.cache_data.clear()
                                                st.rerun()
                                            else:
                                                st.error("🔒 Solo el Administrador Maestro puede eliminar gastos.")
            else:
                st.warning("No se encontraron expedientes.")
    else:
        st.warning("No se encontraron expedientes en la base de datos.")

# ==========================================
# SECCIÓN 3: AGENDA 
# ==========================================
elif menu == "Vencimientos":
    st.header("Control de Vencimientos y Términos")
    c_ag1, c_ag2 = st.columns([1, 1.5])
    with c_ag1:
        st.subheader("📌 Programar Término Manual")
        with st.form("form_venc"):
            conn = conectar_bd()
            try:
                df_proc = pd.read_sql_query("SELECT radicado_interno FROM procesos", conn)
            finally:
                conn.close()
            
            rad_sel = st.selectbox("Asociar a Proceso", df_proc['radicado_interno'].tolist() if not df_proc.empty else ["GENERAL"])
            tit_venc = st.text_input("Descripción del Término")
            f_venc = st.date_input("Fecha Límite")
            obs_venc = st.text_area("Observaciones")
            if st.form_submit_button("💾 Agendar Vencimiento"):
                if tit_venc:
                    conn_v = conectar_bd()
                    try:
                        conn_v.cursor().execute("INSERT INTO vencimientos (radicado_interno, titulo, fecha_vencimiento, observaciones) VALUES (%s, %s, %s, %s)", (rad_sel, tit_venc, str(f_venc), obs_venc))
                        registrar_auditoria(conn_v, usuario_seleccionado, "CREACION", "vencimientos", rad_sel, "", str(f_venc), json.dumps({"titulo": tit_venc, "fecha": str(f_venc)}))
                        conn_v.commit()
                    finally:
                        conn_v.close()
                    st.cache_data.clear()
                    st.session_state['toast_msg'] = "Término agendado con éxito."
                    st.session_state['toast_icon'] = "⏰"
                    st.rerun()
                    
    with c_ag2:
        st.subheader("🚨 Alarmas Pendientes")
        conn = conectar_bd()
        try:
            venc_df = pd.read_sql_query("SELECT * FROM vencimientos ORDER BY fecha_vencimiento ASC", conn)
        finally:
            conn.close()
        
        venc_pendientes = venc_df[venc_df['estado'] == 'Pendiente']
        if not venc_pendientes.empty:
            for idx, row in venc_pendientes.iterrows():
                with st.expander(f"🔴 [{row['radicado_interno']}] {row['titulo']} (Vence: {row['fecha_vencimiento']})"):
                    with st.form(key=f"form_venc_edit_{row['id']}"):
                        u_tit = st.text_input("Tarea", value=row['titulo'])
                        u_fec = st.text_input("Fecha Vencimiento", value=row['fecha_vencimiento'])
                        u_est = st.selectbox("Estado", ["Pendiente", "Completado"], index=0)
                        cv1, cv2 = st.columns(2)
                        if cv1.form_submit_button("💾 Actualizar"):
                            conn_uv = conectar_bd()
                            try:
                                conn_uv.cursor().execute("UPDATE vencimientos SET titulo=%s, fecha_vencimiento=%s, estado=%s WHERE id=%s", (u_tit, u_fec, u_est, row['id']))
                                registrar_auditoria(conn_uv, usuario_seleccionado, "MODIFICACION", "vencimientos", row['id'], row['estado'], u_est, json.dumps({"titulo": u_tit, "estado": u_est}))
                                conn_uv.commit()
                            finally:
                                conn_uv.close()
                            st.cache_data.clear()
                            st.rerun()
                        if cv2.form_submit_button("🗑️ Eliminar"):
                            if usuario_rol == "Maestro":
                                conn_dv = conectar_bd()
                                try:
                                    conn_dv.cursor().execute("DELETE FROM vencimientos WHERE id=%s", (row['id'],))
                                    registrar_auditoria(conn_dv, usuario_seleccionado, "ELIMINACION", "vencimientos", row['id'], row['estado'], "Eliminado", json.dumps(dict(row), default=str))
                                    conn_dv.commit()
                                finally:
                                    conn_dv.close()
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("🔒 Solo el Administrador Maestro puede eliminar vencimientos.")
        else:
            st.success("✅ Agenda limpia.")

# ==========================================
# SECCIÓN 4: DIRECTORIO 
# ==========================================
elif menu == "Directorio":
    st.header("Directorio de Contactos")
    c_d1, c_d2 = st.columns([1, 1.5])
    
    with c_d1:
        st.subheader("➕ Agregar Contacto")
        with st.form("form_cont", clear_on_submit=True):
            id_c = st.text_input("Cédula / NIT", help="Los puntos o comas se eliminarán automáticamente.")
            n_c = st.text_input("Nombre Completo").upper()
            tipo_c = st.selectbox("Tipo", ["Cliente", "Contraparte", "Juzgado", "Perito", "Otro"])
            t_c = st.text_input("Teléfono")
            e_c = st.text_input("Email")
            d_c = st.text_input("Dirección")
            ciu_c = st.text_input("Ciudad", value="PEREIRA").upper()
            if st.form_submit_button("💾 Guardar Contacto"):
                if n_c:
                    id_c_limpio = limpiar_identificacion(id_c)
                    conn_c = conectar_bd()
                    try:
                        conn_c.cursor().execute("INSERT INTO contactos (identificacion, nombre, tipo, telefono, email, direccion, ciudad) VALUES (%s, %s, %s, %s, %s, %s, %s)", (id_c_limpio, n_c, tipo_c, t_c, e_c, d_c, ciu_c))
                        registrar_auditoria(conn_c, usuario_seleccionado, "CREACION", "contactos", id_c_limpio, "", n_c, json.dumps({"nombre": n_c, "tipo": tipo_c}))
                        conn_c.commit()
                    finally:
                        conn_c.close()
                    st.cache_data.clear()
                    st.session_state['toast_msg'] = "Contacto guardado en Neon."
                    st.session_state['toast_icon'] = "📞"
                    st.rerun()
    
    with c_d2:
        st.subheader("🔎 Directorio General")
        df_cont = cargar_contactos_general()
        
        if not df_cont.empty:
            df_cont = df_cont.fillna("")
            lista_busqueda = [f"{r['identificacion']} - {r['nombre']}" if r['identificacion'] else r['nombre'] for i, r in df_cont.iterrows()]
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
                    e_id_c_limpio = limpiar_identificacion(e_id_c)
                    conn_ec = conectar_bd()
                    try:
                        conn_ec.cursor().execute("UPDATE contactos SET identificacion=%s, nombre=%s, tipo=%s, telefono=%s, email=%s, direccion=%s, ciudad=%s WHERE id=%s", (e_id_c_limpio, e_n_c, e_tipo_c, e_t_c, e_em_c, e_d_c, e_ciu_c, int(datos_c['id'])))
                        registrar_auditoria(conn_ec, usuario_seleccionado, "MODIFICACION", "contactos", datos_c['id'], datos_c['nombre'], e_n_c, json.dumps({"nombre": e_n_c}))
                        conn_ec.commit()
                    finally:
                        conn_ec.close()
                    st.cache_data.clear()
                    st.session_state['toast_msg'] = "Contacto actualizado."
                    st.session_state['toast_icon'] = "✅"
                    st.rerun()
                if ce2.form_submit_button("🗑️ Eliminar"):
                    if usuario_rol == "Maestro":
                        conn_dc = conectar_bd()
                        try:
                            conn_dc.cursor().execute("DELETE FROM contactos WHERE id=%s", (int(datos_c['id']),))
                            registrar_auditoria(conn_dc, usuario_seleccionado, "ELIMINACION", "contactos", datos_c['id'], datos_c['nombre'], "Eliminado", json.dumps(dict(datos_c), default=str))
                            conn_dc.commit()
                        finally:
                            conn_dc.close()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("🔒 Solo el Administrador Maestro puede eliminar contactos.")
            st.dataframe(df_cont.drop(columns=['id']), use_container_width=True)

# ==========================================
# SECCIÓN 5: RESUMEN E INFORMES (EXCEL)
# ==========================================
elif menu == "Informes":
    st.header("Informes y Exportación de Datos")
    conn = conectar_bd()
    try:
        total_p = pd.read_sql_query("SELECT COUNT(*) as c FROM procesos", conn).iloc[0]['c']
    finally:
        conn.close()
        
    st.markdown(f"<div class='metric-card' style='max-width:300px;margin-bottom:25px;'><h2 style='color:#0a84ff;margin:0;'>📁 {total_p}</h2><p style='color:#8e8e93;margin:5px 0 0 0;font-weight:500;'>Procesos en Base de Datos</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("Reporte General en Excel")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        conn_rep = conectar_bd()
        try:
            df_proc_r = pd.read_sql_query("SELECT * FROM procesos", conn_rep)
            df_act_r = pd.read_sql_query("SELECT * FROM actuaciones ORDER BY fecha DESC", conn_rep)
            df_venc_r = pd.read_sql_query("SELECT * FROM vencimientos", conn_rep)
            df_gas_r = pd.read_sql_query("SELECT * FROM gastos", conn_rep)
            df_cont_r = pd.read_sql_query("SELECT * FROM contactos", conn_rep)
        finally:
            conn_rep.close()
        
        actuaciones_consolidadas = {}
        for rad in df_proc_r['radicado_interno']:
            acts_subset = df_act_r[df_act_r['radicado_interno'] == rad]
            actuaciones_consolidadas[rad] = "\n".join([f"[{a['fecha']}] {a['etapa']} - {a['descripcion']} (Por: {a['usuario']})" for _, a in acts_subset.iterrows()])
            
        df_proc_r['Historial_Actuaciones'] = df_proc_r['radicado_interno'].map(actuaciones_consolidadas)
        
        df_proc_r.to_excel(writer, sheet_name='Procesos', index=False)
        df_venc_r.to_excel(writer, sheet_name='Vencimientos', index=False)
        df_gas_r.to_excel(writer, sheet_name='Gastos', index=False)
        df_cont_r.to_excel(writer, sheet_name='Directorio', index=False)
        df_act_r.to_excel(writer, sheet_name='Actuaciones', index=False)
        
    st.download_button(label="📥 Descargar Reporte Ejecutivo (.xlsx)", data=output.getvalue(), file_name=f"informe_judicial_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# ==========================================
# SECCIÓN 6: ADMINISTRACIÓN Y AUDITORÍA
# ==========================================
elif menu == "Administración":
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
                        try:
                            conn_m.cursor().execute("INSERT INTO abogados (nombre, email, telefono, rol, password) VALUES (%s, %s, %s, %s, %s)", (n_abg, e_abg, t_abg, r_abg, p_abg if p_abg else "1234"))
                            registrar_auditoria(conn_m, usuario_seleccionado, "CREACION", "abogados", n_abg, "", r_abg, json.dumps({"nombre": n_abg, "rol": r_abg}))
                            conn_m.commit()
                        finally:
                            conn_m.close()
                        st.cache_data.clear()
                        st.session_state['toast_msg'] = "Perfil creado con éxito."
                        st.session_state['toast_icon'] = "👥"
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("Ya existe un usuario registrado con ese nombre en la base de datos.")
        with c_m2:
            st.subheader("✏️ Gestión de Credenciales")
            df_abg = cargar_abogados()
            if not df_abg.empty:
                abg_editar = st.selectbox("Seleccionar usuario:", df_abg['nombre'].tolist())
                datos_a = df_abg[df_abg['nombre'] == abg_editar].iloc[0]
                with st.form(key="edit_abg"):
                    ed_n = st.text_input("Nombre", value=datos_a['nombre']).upper()
                    ed_e = st.text_input("Correo", value=datos_a['email'] if pd.notna(datos_a['email']) else "")
                    ed_t = st.text_input("Teléfono", value=datos_a['telefono'] if pd.notna(datos_a['telefono']) else "")
                    ed_p = st.text_input("Nueva Contraseña (dejar en blanco para mantener actual)", type="password")
                    ed_r = st.selectbox("Rol", ["Abogado", "Maestro"], index=0 if datos_a['rol'] == "Abogado" else 1)
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("💾 Guardar Cambios"):
                        conn_ea = conectar_bd()
                        try:
                            if ed_p: conn_ea.cursor().execute("UPDATE abogados SET nombre=%s, email=%s, telefono=%s, rol=%s, password=%s WHERE id=%s", (ed_n, ed_e, ed_t, ed_r, ed_p, int(datos_a['id'])))
                            else: conn_ea.cursor().execute("UPDATE abogados SET nombre=%s, email=%s, telefono=%s, rol=%s WHERE id=%s", (ed_n, ed_e, ed_t, ed_r, int(datos_a['id'])))
                            registrar_auditoria(conn_ea, usuario_seleccionado, "MODIFICACION", "abogados", datos_a['id'], datos_a['rol'], ed_r, json.dumps({"nombre": ed_n, "rol": ed_r}))
                            conn_ea.commit()
                        finally:
                            conn_ea.close()
                        st.cache_data.clear()
                        st.session_state['toast_msg'] = "Modificaciones de seguridad guardadas."
                        st.session_state['toast_icon'] = "🔐"
                        st.rerun()
                    if c_b2.form_submit_button("🗑️ Eliminar Perfil"):
                        if abg_editar == "ADMINISTRADOR MAESTRO": st.error("No es posible eliminar al administrador principal.")
                        else:
                            conn_da = conectar_bd()
                            try:
                                conn_da.cursor().execute("DELETE FROM abogados WHERE id=%s", (int(datos_a['id']),))
                                registrar_auditoria(conn_da, usuario_seleccionado, "ELIMINACION", "abogados", datos_a['id'], datos_a['nombre'], "Eliminado", json.dumps(dict(datos_a), default=str))
                                conn_da.commit()
                            finally:
                                conn_da.close()
                            st.cache_data.clear()
                            st.session_state['toast_msg'] = "Perfil eliminado."
                            st.session_state['toast_icon'] = "🗑️"
                            st.rerun()
            st.dataframe(df_abg, use_container_width=True)
            
        st.markdown("---")
        st.subheader("📜 Log de Auditoría y Restauración Dinámica")
        conn_aud = conectar_bd()
        try:
            df_aud = pd.read_sql_query("SELECT * FROM auditoria ORDER BY fecha DESC LIMIT 100", conn_aud)
        finally:
            conn_aud.close()
        
        if not df_aud.empty:
            st.dataframe(df_aud, use_container_width=True, hide_index=True)
            
            st.markdown("### ♻️ Bóveda de Restauración (Universal)")
            st.write("Puedes restaurar expedientes, actuaciones, gastos, contactos o vencimientos eliminados.")
            eliminados_df = df_aud[df_aud['accion'] == 'ELIMINACION']
            
            if not eliminados_df.empty:
                opciones_restaurar = [f"ID Log: {r['id']} | Tabla: {r['tabla']} | Registro ID: {r['registro_id']} | Fecha: {r['fecha']}" for _, r in eliminados_df.iterrows()]
                log_sel = st.selectbox("Seleccione el registro eliminado que desea recuperar:", opciones_restaurar)
                
                if st.button("🔄 Ejecutar Restauración Segura"):
                    id_log_sel = int(log_sel.split("|")[0].replace("ID Log:", "").strip())
                    row_log = eliminados_df[eliminados_df['id'] == id_log_sel].iloc[0]
                    tabla_afectada = row_log['tabla']
                    datos_str = row_log['datos_json']
                    
                    try:
                        datos_dict = json.loads(datos_str)
                        if isinstance(datos_dict, dict) and datos_dict:
                            conn_res = conectar_bd()
                            try:
                                cur_res = conn_res.cursor()
                                
                                columnas = ', '.join(datos_dict.keys())
                                placeholders = ', '.join(['%s'] * len(datos_dict))
                                valores = tuple(datos_dict.values())
                                
                                query_insercion = f"INSERT INTO {tabla_afectada} ({columnas}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                                cur_res.execute(query_insercion, valores)
                                
                                registrar_auditoria(conn_res, usuario_seleccionado, "RESTAURACION", tabla_afectada, row_log['registro_id'], "Eliminado", "Restaurado", datos_str)
                                conn_res.commit()
                                
                                st.cache_data.clear()
                                st.success(f"✅ ¡Restauración exitosa! El registro volvió a la tabla '{tabla_afectada}'.")
                            finally:
                                conn_res.close()
                        else:
                            st.error("⚠️ El formato del respaldo no contiene campos válidos para procesar.")
                    except Exception as ex:
                        st.error(f"Error técnico durante la restauración: {ex}")
            else:
                st.info("No hay registros eliminados en la papelera en este momento.")
        else:
            st.info("El historial de auditoría está vacío.")
    else:
        st.warning("🔒 Acceso denegado. Se requiere credencial de Administrador Maestro para acceder a la configuración global y papelera.")
