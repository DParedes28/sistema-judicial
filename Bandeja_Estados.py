import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Bandeja de Estados y Novedades", page_icon="📌", layout="wide")

st.title("📌 Bandeja de Entrada de Novedades Judiciales")
st.markdown("Revisa aquí las últimas actuaciones detectadas por el robot, valida la sugerencia de la IA y marca como revisado.")

# Conexión segura leída desde los Secrets de Streamlit Cloud
DATABASE_URL = st.secrets["DATABASE_URL"]

def obtener_actuaciones_pendientes():
    """Trae de Neon las actuaciones que aún no han sido marcadas como revisadas"""
    try:
        conexion = psycopg2.connect(DATABASE_URL)
        query = """
            SELECT 
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
            ORDER BY a.fecha DESC;
        """
        df = pd.read_sql(query, conexion)
        conexion.close()
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

# Cargamos los datos
df_pendientes = obtener_actuaciones_pendientes()

if df_pendientes.empty:
    st.success("🎉 ¡Excelente trabajo! No hay actuaciones pendientes por revisar en este momento.")
else:
    st.info(f"Tienes **{len(df_pendientes)}** actuaciones nuevas capturadas por el robot pendientes de revisión.")

    df_editable = df_pendientes.copy()
    
    if 'tipificacion_definitiva' in df_editable.columns:
        df_editable['tipificacion_definitiva'] = df_editable['tipificacion_definitiva'].fillna(df_editable['tipificacion_sugerida'])

    opciones_tipificacion = [
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
    st.markdown("Modifica la tipificación si lo consideras necesario y marca la casilla **Revisado** para limpiar este pendiente de tu bandeja.")

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
                "Tipificación Definitiva",
                options=opciones_tipificacion,
                required=True
            ),
            "revisado": st.column_config.CheckboxColumn("¿Revisado? ✅", default=False)
        },
        hide_index=True,
        use_container_width=True
    )

    if st.button("💾 Guardar Cambios y Actualizar Bandeja", type="primary"):
        try:
            conexion = psycopg2.connect(DATABASE_URL)
            cursor = conexion.cursor()
            
            actualizados = 0
            for index, row in df_resultado.iterrows():
                cursor.execute("""
                    UPDATE actuaciones 
                    SET tipificacion_definitiva = %s, revisado = %s 
                    WHERE id = %s
                """, (row['tipificacion_definitiva'], row['revisado'], row['id']))
                actualizados += 1
                
            conexion.commit()
            cursor.close()
            conexion.close()
            
            st.success(f"¡Se actualizaron {actualizados} registros correctamente! Recargando vista...")
            st.rerun()
            
        except Exception as e:
            st.error(f"Ocurrió un error al guardar en la base de datos: {e}")
