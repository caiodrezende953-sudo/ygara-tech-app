import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import sqlite3
import os

# ==========================================
# 0. SETUP DE BANCO DE DADOS
# ==========================================
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
logo_file_path = os.path.join(diretorio_atual, "Ygara Tech.png") 
banco_path = os.path.join(diretorio_atual, "ygara_publico.db")

conn = sqlite3.connect(banco_path)
conn.execute('''CREATE TABLE IF NOT EXISTS alertas_waze (id INTEGER PRIMARY KEY, usuario TEXT, tipo_alerta TEXT, lat REAL, lon REAL, descricao TEXT, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP, upvotes INTEGER DEFAULT 1, downvotes INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS perfis_usuarios (email TEXT PRIMARY KEY, nome TEXT, sobrenome TEXT, tipo_barco TEXT, nome_barco TEXT, pontos INTEGER DEFAULT 0, nivel TEXT DEFAULT 'Navegante')''')
conn.commit(); conn.close()

if 'usuario_email' not in st.session_state: st.session_state['usuario_email'] = "usuario@ygaranav.com"
if 'navegando' not in st.session_state: st.session_state['navegando'] = False
if 'gps_progresso' not in st.session_state: st.session_state['gps_progresso'] = 0

if 'mostrar_restaurantes' not in st.session_state: st.session_state['mostrar_restaurantes'] = True
if 'mostrar_postos' not in st.session_state: st.session_state['mostrar_postos'] = True
if 'mostrar_marinas' not in st.session_state: st.session_state['mostrar_marinas'] = True

# ==========================================
# 1. LAYOUT MOBILE & ESTILO MAPS
# ==========================================
st.set_page_config(page_title="Ygara Nav", layout="wide", page_icon="🧭", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 2rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stButton>button { border-radius: 24px; font-weight: 500; border: 1px solid #ddd; white-space: nowrap;}
        .start-nav-btn>button { background-color: #1A73E8; color: white; border-radius: 24px; height: 45px; font-size: 16px; border: none; font-weight: 700; width: 100%;}
        .swap-btn>button { border-radius: 50%; width: 40px; height: 40px; padding: 0; margin-top: 18px; border: none; background-color: transparent; font-size: 20px;}
        .maps-card { padding: 15px; border-radius: 16px; margin-bottom: 10px; background-color: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        div[data-testid="stAppViewContainer"] { background-color: #f5f5f5; }
        
        /* Estilo do Rodapé Global */
        .footer-global {
            text-align: center;
            padding: 30px 10px;
            margin-top: 40px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 14px;
        }
        .footer-emergencia { color: #D32F2F; font-weight: bold; margin-bottom: 10px;}
        .footer-creditos { font-size: 12px; color: #888; margin-top: 10px;}
    </style>
""", unsafe_allow_html=True)

# CABEÇALHO LIMPO (LOGO CENTRALIZADA)
c_espaco1, c_logo, c_espaco2 = st.columns([4, 2, 4])
with c_logo:
    if os.path.exists(logo_file_path): st.image(logo_file_path, use_container_width=True)
    else: st.markdown("<h3 style='text-align: center; color:#1A73E8; margin:0;'>YGARA</h3>", unsafe_allow_html=True)

# ==========================================
# 2. BANCO DE DADOS DE ALTA PRECISÃO
# ==========================================
locais_base = {
    "Praia da Lua": {"lat": -3.0305, "lon": -60.0570, "tipo": "Praia", "desc": "Área de banhistas"},
    "Praia do Tupé": {"lat": -3.0400, "lon": -60.2500, "tipo": "Praia", "desc": "Reserva Sustentável"},
    "Encontro das Águas": {"lat": -3.1360, "lon": -59.8970, "tipo": "Turismo", "desc": "Não misturam"},
    "Porto de Manaus (Panair)": {"lat": -3.1430, "lon": -60.0150, "tipo": "Porto", "desc": "Embarque Regional"},
    "Ponta Negra (Calha)": {"lat": -3.0850, "lon": -60.0950, "tipo": "Referência", "desc": "Canal Principal"}
}

restaurantes = {
    "Abaré SUP and Food": {"lat": -3.0440, "lon": -60
                           
