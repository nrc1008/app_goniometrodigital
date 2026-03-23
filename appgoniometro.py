import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
import numpy as np
import math
from PIL import Image, ImageDraw
from datetime import datetime
import os, csv
import matplotlib.pyplot as plt

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="DigitROM Analysis", page_icon="🖐️📐", layout="wide")

#FUNCIONES MATEMÁTICAS E HISTORIAL 
def calcular_angulo_clinico(A, B, C):
    BA, BC = A - B, C - B
    norm_a, norm_c = np.linalg.norm(BA), np.linalg.norm(BC)
    if norm_a == 0 or norm_c == 0: return 0.0
    cos_angle = np.dot(BA, BC) / (norm_a * norm_c)
    return round(180 - math.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))), 2)

def obtener_historial_previo(paciente, dedo):
    if not paciente: return None
    p_f = paciente.title().replace(' ', '_')
    archivo = os.path.join("Pacientes", p_f, f"Historial_{p_f}.csv")
    if not os.path.isfile(archivo): return None
    try:
        with open(archivo, mode='r', encoding='utf-8-sig') as f:
            reader = list(csv.reader(f, delimiter=';'))
            hist = [r for r in reader[1:] if len(r) > 9 and f"Dedo {dedo}" in r[2]]
            return {"fecha": hist[-1][0], "tam": float(hist[-1][9])} if hist else None
    except: return None

#  FUNCIÓN ANÁLISIS  
def fase_analisis_foto(titulo, session_key, color, cache_key):
    st.subheader(titulo)
    archivo = st.file_uploader("Selecciona foto", type=["jpg", "jpeg", "png"], key=f"u_{session_key}")
    if archivo:
        col_izq, col_med, col_der = st.columns([1, 2, 1])
        with col_med:
            img = Image.open(archivo)
            img.thumbnail((700, 2000), Image.Resampling.LANCZOS)
            st.session_state[cache_key] = img
            canvas = img.copy()
            draw = ImageDraw.Draw(canvas)
            puntos = st.session_state[session_key]
            if len(puntos) > 1: draw.line(puntos, fill=color, width=3)
            for p in puntos: draw.ellipse((p[0]-6, p[1]-6, p[0]+6, p[1]+6), fill=color)
            clic = streamlit_image_coordinates(canvas, key=f"c_{session_key}", width=img.size[0])
            if clic and (clic['x'], clic['y']) not in puntos and len(puntos) < 5:
                st.session_state[session_key].append((clic['x'], clic['y']))
                st.rerun()
        if len(puntos) == 5: st.success("¡5 puntos registrados! Pasa al siguiente apartado")

# 2. TÍTULO Y MEMORIA
st.title("🖐️ DigitROM Analysis: Goniometría Digital")
st.markdown("**Desarrollado por: Niamey Rey**")

if 'puntos_ext' not in st.session_state: st.session_state.puntos_ext = []
if 'puntos_flex' not in st.session_state: st.session_state.puntos_flex = []

# 3. REFERENCIA CLÍNICA 
with st.expander("📖 Guía de Referencia Anatómica (Cerrar para analizar)", expanded=False):
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write("### Cómo realizar los 5 Clics")
        st.markdown("1. **Dorso**\n2. **MCF**\n3. **IFP**\n4. **IFD**\n5. **Punta**")
        st.info("💡 Usa la imagen de la derecha como guía.")
    with c2:
        try: st.image("referencia_mano.png", caption="Guía visual de puntos")
        except: st.error("Falta 'referencia_mano.png'")
st.markdown("---")

# 4. SIDEBAR
with st.sidebar:
    st.header("📂 Expediente")
    paciente = st.text_input("ID Paciente", placeholder="Ej: 7579")
    dedo = st.selectbox("Dedo a evaluar", ['2 (Índice)', '5 (Meñique)'])
    fase = st.radio("Fase:", ["1. EXTENSIÓN", "2. FLEXIÓN", "3. Reporte Final"])
    if st.button("🗑️ Reiniciar Evaluación"):
        st.session_state.puntos_ext, st.session_state.puntos_flex = [], []
        st.rerun()

# 5. EJECUCIÓN DE FASES
if fase == "1. EXTENSIÓN":
    fase_analisis_foto("FOTO 1: Análisis de EXTENSIÓN", "puntos_ext", "red", "img_ext_cache")
elif fase == "2. FLEXIÓN":
    fase_analisis_foto("FOTO 2: Análisis de FLEXIÓN", "puntos_flex", "blue", "img_flex_cache")
elif fase == "3. Reporte Final":
    if len(st.session_state.puntos_ext) == 5 and len(st.session_state.puntos_flex) == 5:
        # Cálculos de ángulos y TAM
        pts_e, pts_f = [np.array(p) for p in st.session_state.puntos_ext], [np.array(p) for p in st.session_state.puntos_flex]
        ang_e = [calcular_angulo_clinico(pts_e[i], pts_e[i+1], pts_e[i+2]) for i in range(3)]
        ang_f = [calcular_angulo_clinico(pts_f[i], pts_f[i+1], pts_f[i+2]) for i in range(3)]
        tam_total = round(sum(ang_f) - sum(ang_e), 2)
        diag = "EXCELENTE" if tam_total >= 220 else "BUENO" if tam_total >= 180 else "REGULAR / MALO"

        # Reporte Visual 
        ca, cb = st.columns(2)
        with ca:
            st.markdown("### 🔴 Extensión")
            fig_e, ax_e = plt.subplots(); ax_e.imshow(st.session_state.img_ext_cache)
            ex, ey = zip(*st.session_state.puntos_ext); ax_e.plot(ex, ey, 'o-', color='red', linewidth=2)
            ax_e.axis('off'); st.pyplot(fig_e)
        with cb:
            st.markdown("### 🔵 Flexión ")
            fig_f, ax_f = plt.subplots(); ax_f.imshow(st.session_state.img_flex_cache)
            fx, fy = zip(*st.session_state.puntos_flex); ax_f.plot(fx, fy, 'o-', color='blue', linewidth=2)
            ax_f.axis('off'); st.pyplot(fig_f)

        st.markdown("---")
        m1, m2 = st.columns(2)
        m1.metric(
            label="TAM Actual", 
            value=f"{tam_total}°",
            help="Fórmula TAM: (Flexión MCF+IFP+IFD) - (Déficit Extensión MCF+IFP+IFD). Estándar oficial de la ASSH."
        )
        m2.metric(
            label="Clasificación", 
            value=diag,
            help="Basado en la escala de Strickland: Excelente (>220°), Bueno (180-220°), Regular/Malo (<180°)."
        )
        
        hist = obtener_historial_previo(paciente, dedo)
        if hist: st.info(f"📈 Evolución: {round(tam_total - hist['tam'], 2)}° respecto a {hist['fecha']}")

        st.subheader("Desglose Articular")
        cols = st.columns(3)
        arts = ["MCF (Nudillo)", "IFP (Medio)", "IFD (Punta)"]
        for i in range(3): 
            cols[i].metric(
                label=arts[i], 
                value=f"{ang_f[i]}°", 
                delta=f"Déficit: {ang_e[i]}°", 
                delta_color="inverse",
                help=f"Ángulos calculados para la articulación {arts[i]}."
            )
            
        # 6. GUARDAR Y PDF
        if st.button("💾 GUARDAR Y GENERAR PDF", use_container_width=True):
            if not paciente: st.error("ID Paciente vacío")
            else:
                p_f = paciente.title().replace(' ', '_')
                folder = os.path.join("Pacientes", p_f)
                if not os.path.exists(folder): os.makedirs(folder)
                
                # Guardar CSV
                csv_path = os.path.join(folder, f"Historial_{p_f}.csv")
                existe = os.path.isfile(csv_path)
                with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    if not existe: writer.writerow(["Fecha", "ID", "Dedo", "E_MCF", "E_IFP", "E_IFD", "F_MCF", "F_IFP", "F_IFD", "TAM", "Diag"])
                    writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M"), paciente, f"Dedo {dedo}", *ang_e, *ang_f, tam_total, diag])
                
                # PDF 
                fig_pdf = plt.figure(figsize=(8.27, 11.69))
                fig_pdf.text(0.5, 0.95, "INFORME DE CINEMÁTICA DIGITAL", ha='center', fontsize=14, fontweight='bold')
                fig_pdf.text(0.5, 0.92, f"ID: {paciente} | Fecha: {datetime.now().strftime('%d/%m/%Y')}", ha='center')
                ax1 = fig_pdf.add_axes([0.1, 0.65, 0.35, 0.22]); ax1.imshow(st.session_state.img_ext_cache)
                ax1.plot(ex, ey, 'o-', color='red', linewidth=2); ax1.set_title("Déficit Extensión"); ax1.axis('off')
                ax2 = fig_pdf.add_axes([0.55, 0.65, 0.35, 0.22]); ax2.imshow(st.session_state.img_flex_cache)
                ax2.plot(fx, fy, 'o-', color='blue', linewidth=2); ax2.set_title("Flexión Máxima"); ax2.axis('off')
                txt = f"TAM: {tam_total}°\nResultado: {diag}"
                fig_pdf.text(0.5, 0.58, txt, ha='center', fontsize=12, bbox=dict(facecolor='none', edgecolor='black', pad=10))
                
                pdf_name = f"Informe_{p_f}_{datetime.now().strftime('%H%M%S')}.pdf"
                pdf_p = os.path.join(folder, pdf_name)
                plt.savefig(pdf_p, format='pdf', dpi=300); plt.close()
                st.success("✅ Guardado."); st.download_button("📥 DESCARGAR PDF", open(pdf_p, "rb"), file_name=pdf_name)
    else: st.warning("⚠️ Completa los clics en ambas fotos.")