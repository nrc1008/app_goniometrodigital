import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
import numpy as np
import math
from PIL import Image, ImageDraw
from datetime import datetime
import os, csv
import matplotlib.pyplot as plt

# 1. CONFIGURACIÓN TÉCNICA
st.set_page_config(page_title="DigitROM Analysis", page_icon="🖐️📐", layout="wide")

def calcular_angulo_clinico(A, B, C):
    BA, BC = A - B, C - B
    norm_a, norm_c = np.linalg.norm(BA), np.linalg.norm(BC)
    if norm_a == 0 or norm_c == 0: return 0.0
    cos_angle = np.dot(BA, BC) / (norm_a * norm_c)
    return round(180 - math.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))), 2)

def fase_analisis_foto(titulo, session_key, color, cache_key):
    st.markdown(f"### {titulo}")
    archivo = st.file_uploader(f"Cargar imagen: {titulo}", type=["jpg", "jpeg", "png"], key=f"u_{session_key}")
    
    if archivo:
        if cache_key not in st.session_state or st.session_state.get(f"name_{cache_key}") != archivo.name:
            img = Image.open(archivo)
            img.thumbnail((1000, 2000), Image.Resampling.LANCZOS)
            st.session_state[cache_key] = img
            st.session_state[f"name_{cache_key}"] = archivo.name
        
        img = st.session_state[cache_key]
        canvas = img.copy()
        draw = ImageDraw.Draw(canvas)
        puntos = st.session_state[session_key]
        
        if len(puntos) > 1: draw.line(puntos, fill=color, width=3)
        for p in puntos: draw.ellipse((p[0]-8, p[1]-8, p[0]+8, p[1]+8), fill=color)
        
        clic = streamlit_image_coordinates(canvas, key=f"c_{session_key}", width=img.size[0])
        
        if clic:
            nuevo_punto = (clic['x'], clic['y'])
            if nuevo_punto not in puntos and len(puntos) < 5:
                st.session_state[session_key].append(nuevo_punto)
                st.rerun()
        
        if len(puntos) == 5:
            st.success("✅ 5 puntos registrados correctamente.")
            return True
    return False

# 2. ENCABEZADO
st.title("🖐️ DigitROM Analysis: Goniometría Digital")
st.markdown("**Desarrollado por: Niamey Rey**")

if 'paso_n' not in st.session_state: st.session_state.paso_n = 0
if 'puntos_ext' not in st.session_state: st.session_state.puntos_ext = []
if 'puntos_flex' not in st.session_state: st.session_state.puntos_flex = []

# 3. REFERENCIA ANATÓMICA 
with st.expander("📖 Protocolo de Referencia Anatómica", expanded=False):
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write("**Puntos de Control:**")
        st.markdown("1. Dorso metacarpiano\n2. MCF\n3. IFP\n4. IFD\n5. Extremo distal")
    with c2:
        try: st.image("referencia_mano.png", width=350)
        except: st.warning("Imagen de referencia no localizada.")

st.markdown("---")

fases_lista = ["Extensión", "Flexión", "Reporte Final"]
with st.sidebar:
    st.header("📂 Gestión de Expediente")
    paciente = st.text_input("ID Paciente", placeholder="Historia Clínica")
    dedo_opcion = st.selectbox("Dedo a evaluar", ['2 (Índice)', '5 (Meñique)'])
    
    st.divider()
    fase = st.radio("Fase de Evaluación:", fases_lista, index=st.session_state.paso_n)
    if fase != fases_lista[st.session_state.paso_n]:
        st.session_state.paso_n = fases_lista.index(fase)
        st.rerun()
    
    if st.button("🗑️ Reiniciar Evaluación"):
        st.session_state.puntos_ext, st.session_state.puntos_flex, st.session_state.paso_n = [], [], 0
        for key in ["img_ext_cache", "img_flex_cache", "name_img_ext_cache", "name_img_flex_cache"]:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

# 4. EJECUCIÓN POR FASES 
if fase == "Extensión":
    if fase_analisis_foto("Evaluación de Extensión", "puntos_ext", "red", "img_ext_cache"):
        if st.button("Siguiente: Evaluación de Flexión ➡️", use_container_width=True):
            st.session_state.paso_n = 1
            st.rerun()

elif fase == "Flexión":
    if fase_analisis_foto("Evaluación de Flexión Máxima", "puntos_flex", "blue", "img_flex_cache"):
        if st.button("Siguiente: Generar Reporte Final ➡️", use_container_width=True):
            st.session_state.paso_n = 2
            st.rerun()

elif fase == "Reporte Final":
    if len(st.session_state.puntos_ext) == 5 and len(st.session_state.puntos_flex) == 5:
        pts_e = [np.array(p) for p in st.session_state.puntos_ext]
        pts_f = [np.array(p) for p in st.session_state.puntos_flex]
        ang_e = [calcular_angulo_clinico(pts_e[i], pts_e[i+1], pts_e[i+2]) for i in range(3)]
        ang_f = [calcular_angulo_clinico(pts_f[i], pts_f[i+1], pts_f[i+2]) for i in range(3)]
        
        es_meñique = "5" in dedo_opcion
        ref_flex = [90, 100, 80] if not es_meñique else [100, 110, 90]
        tam_total = round(sum(ang_f) - sum(ang_e), 2)
        diag = "EXCELENTE" if tam_total >= 220 else "BUENO" if tam_total >= 180 else "REGULAR / MALO"

        st.subheader("📊 Informe de Movilidad Articular")
        
        p_f = paciente.title().replace(' ', '_') if paciente else "Anonimo"
        folder = os.path.join("Pacientes", p_f)
        csv_path = os.path.join(folder, f"Historial_{p_f}.csv")

        if st.button("💾 Registrar Evaluación y Generar Documentos", use_container_width=True):
            if not paciente:
                st.error("⚠️ Error: Debe introducir un ID de Paciente.")
            else:
                if not os.path.exists(folder): os.makedirs(folder)
                
                existe = os.path.isfile(csv_path)
                with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    if not existe:
                        writer.writerow(["Fecha", "ID", "Dedo", "E_MCF", "E_IFP", "E_IFD", "F_MCF", "F_IFP", "F_IFD", "TAM", "Diag"])
                    writer.writerow([datetime.now().strftime("%d/%m/%Y %H:%M"), paciente, dedo_opcion, *ang_e, *ang_f, tam_total, diag])
                
                fig_pdf = plt.figure(figsize=(8.27, 11.69))
                fig_pdf.text(0.5, 0.96, "INFORME CINEMÁTICO: DigitROM Analysis", ha='center', fontsize=16, fontweight='bold')
                fig_pdf.text(0.5, 0.93, f"ID Paciente: {paciente} | Dedo: {dedo_opcion} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ha='center', fontsize=11)

                ex, ey = zip(*st.session_state.puntos_ext)
                fx, fy = zip(*st.session_state.puntos_flex)
                
                ax1 = fig_pdf.add_axes([0.1, 0.68, 0.38, 0.20])
                ax1.imshow(st.session_state.img_ext_cache); ax1.plot(ex, ey, 'o-', color='red'); ax1.axis('off')
                
                ax2 = fig_pdf.add_axes([0.52, 0.68, 0.38, 0.20])
                ax2.imshow(st.session_state.img_flex_cache); ax2.plot(fx, fy, 'o-', color='blue'); ax2.axis('off')

                ax_g = fig_pdf.add_axes([0.15, 0.44, 0.7, 0.16])
                arcos = [round(ang_f[i] - ang_e[i], 1) for i in range(3)]
                x = np.arange(3)
                ax_g.bar(x - 0.17, arcos, 0.35, label='Paciente', color='#1f77b4')
                ax_g.bar(x + 0.17, ref_flex, 0.35, label='Normalidad', color='#d3d3d3')
                ax_g.set_xticks(x); ax_g.set_xticklabels(["MCF", "IFP", "IFD"]); ax_g.legend()

                txt = f"TAM TOTAL: {tam_total}° | CLASIFICACIÓN: {diag}"
                fig_pdf.text(0.1, 0.35, txt, fontsize=12, fontweight='bold')

                pdf_name = f"Informe_{p_f}_{datetime.now().strftime('%H%M%S')}.pdf"
                pdf_path = os.path.join(folder, pdf_name)
                plt.savefig(pdf_path, format='pdf', dpi=300)
                plt.close(fig_pdf)

                st.session_state['guardado_finalizado'] = True
                st.session_state['ruta_pdf_generado'] = pdf_path
                st.session_state['ruta_csv_generado'] = csv_path
                st.success("✅ Datos registrados correctamente.")

        if st.session_state.get('guardado_finalizado'):
            c1, c2 = st.columns(2)
            with c1:
                with open(st.session_state['ruta_pdf_generado'], "rb") as f:
                    st.download_button("📥 Descargar PDF Final", f, file_name=os.path.basename(st.session_state['ruta_pdf_generado']))
            with c2:
                with open(st.session_state['ruta_csv_generado'], "rb") as f:
                    st.download_button("📊 Descargar Historial CSV", f, file_name=f"Historial_{p_f}.csv")

            st.markdown("---")
            st.markdown("### 🗂️ Historial Evolutivo (Pre/Post)")
            try:
                import pandas as pd
                df = pd.read_csv(st.session_state['ruta_csv_generado'], sep=';')
                st.dataframe(df, use_container_width=True)
            except:
                st.error("Error al cargar la tabla de evolución.")

    else:
        st.warning("⚠️ Evaluación incompleta. Asegúrese de marcar los 5 puntos en Extensión y Flexión.")