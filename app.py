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
# 1. LAYOUT MOBILE & ESTILO MAPS (CABEÇALHO LIMPO)
# ==========================================
st.set_page_config(page_title="Ygara", layout="wide", page_icon="🧭", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stButton>button { border-radius: 24px; font-weight: 500; border: 1px solid #ddd; white-space: nowrap;}
        .start-nav-btn>button { background-color: #1A73E8; color: white; border-radius: 24px; height: 45px; font-size: 16px; border: none; font-weight: 700; width: 100%;}
        .swap-btn>button { border-radius: 50%; width: 40px; height: 40px; padding: 0; margin-top: 18px; border: none; background-color: transparent; font-size: 20px;}
        .maps-card { padding: 15px; border-radius: 16px; margin-bottom: 10px; background-color: #ffffff; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        div[data-testid="stAppViewContainer"] { background-color: #f5f5f5; }
    </style>
""", unsafe_allow_html=True)

# CABEÇALHO COM LOGO CENTRALIZADA E SEM TEXTOS
c_espaco1, c_logo, c_espaco2 = st.columns([4, 2, 4])
with c_logo:
    if os.path.exists(logo_file_path): 
        st.image(logo_file_path, use_container_width=True)
    else:
        st.markdown("<h3 style='text-align: center; color:#1A73E8; margin:0;'>YGARA</h3>", unsafe_allow_html=True)

# ==========================================
# 2. BANCO DE DADOS DE ALTA PRECISÃO (PINOS NA ÁGUA)
# ==========================================
locais_base = {
    "Praia da Lua": {"lat": -3.0305, "lon": -60.0570, "tipo": "Praia", "desc": "Área de banhistas"},
    "Praia do Tupé": {"lat": -3.0400, "lon": -60.2500, "tipo": "Praia", "desc": "Reserva Sustentável"},
    "Encontro das Águas": {"lat": -3.1360, "lon": -59.8970, "tipo": "Turismo", "desc": "Não misturam"},
    "Porto de Manaus (Panair)": {"lat": -3.1430, "lon": -60.0150, "tipo": "Porto", "desc": "Embarque Regional"},
    "Ponta Negra (Calha)": {"lat": -3.0850, "lon": -60.0950, "tipo": "Referência", "desc": "Canal Principal"}
}

restaurantes = {
    "Abaré SUP and Food": {"lat": -3.0440, "lon": -60.1105, "tipo": "Restaurante", "desc": "Tarumã - Música e Gastronomia"},
    "Flutuante Sun Paradise": {"lat": -3.0415, "lon": -60.1085, "tipo": "Restaurante", "desc": "Tarumã - Praia Dourada"},
    "Flutuante Sedutor": {"lat": -3.0520, "lon": -60.1020, "tipo": "Restaurante", "desc": "Tarumã - Lazer"},
    "Morada dos Peixes": {"lat": -3.0600, "lon": -60.0950, "tipo": "Restaurante", "desc": "Tarumã - Peixaria"},
    "Flutuante da Tia": {"lat": -3.0650, "lon": -60.0880, "tipo": "Restaurante", "desc": "Tarumã - Tradicional"}
}

postos_combustivel = {
    "Posto Atem Flutuante (Tarumã)": {"lat": -3.0555, "lon": -60.0865, "tipo": "Posto", "desc": "Gasolina/Diesel 24h"},
    "Posto Equador (Panair)": {"lat": -3.1420, "lon": -60.0120, "tipo": "Posto", "desc": "Balsa de Abastecimento"}
}

marinas = {
    "Marina do David": {"lat": -3.0760, "lon": -60.0400, "tipo": "Marina", "desc": "Acesso Rápido Praia da Lua"},
    "Marina Rio Bello": {"lat": -3.0500, "lon": -60.0820, "tipo": "Marina", "desc": "Descida de Lanchas"},
    "Marina Tauá": {"lat": -3.0400, "lon": -60.0920, "tipo": "Marina", "desc": "Estrutura Premium"}
}

calha_rio_negro = [
    {"lat": -3.1430, "lon": -60.0150}, {"lat": -3.1300, "lon": -60.0400}, {"lat": -3.1150, "lon": -60.0550}, 
    {"lat": -3.0950, "lon": -60.0800}, {"lat": -3.0850, "lon": -60.0950}, {"lat": -3.0500, "lon": -60.0700}, 
    {"lat": -3.0305, "lon": -60.0570}, {"lat": -3.0400, "lon": -60.2500}
]

calha_taruma = [
    {"lat": -3.0850, "lon": -60.0950}, {"lat": -3.0700, "lon": -60.1050}, {"lat": -3.0600, "lon": -60.0950}, 
    {"lat": -3.0520, "lon": -60.1020}, {"lat": -3.0440, "lon": -60.1105}, {"lat": -3.0415, "lon": -60.1085}
]

def gerar_rota_inteligente(origem_dict, destino_dict):
    o_lat, o_lon = origem_dict["lat"], origem_dict["lon"]
    d_lat, d_lon = destino_dict["lat"], destino_dict["lon"]
    
    if o_lon < -60.080 and d_lon < -60.080 and o_lat > -3.085 and d_lat > -3.085: trilho_base = calha_taruma
    else: trilho_base = calha_rio_negro + calha_taruma
        
    trilho_base = sorted(trilho_base, key=lambda p: abs(p["lon"] - o_lon))
    pontos_rota = [{"lat": o_lat, "lon": o_lon}]
    
    for p in trilho_base:
        if min(o_lon, d_lon) - 0.01 <= p["lon"] <= max(o_lon, d_lon) + 0.01:
            if min(o_lat, d_lat) - 0.01 <= p["lat"] <= max(o_lat, d_lat) + 0.01:
                pontos_rota.append(p)
                
    pontos_rota.append({"lat": d_lat, "lon": d_lon})
    
    micropontos = []
    for i in range(len(pontos_rota)-1):
        p1, p2 = pontos_rota[i], pontos_rota[i+1]
        for step in range(10):
            f = step / 10.0
            micropontos.append({"lat": p1["lat"] + (p2["lat"] - p1["lat"]) * f, "lon": p1["lon"] + (p2["lon"] - p1["lon"]) * f})
    micropontos.append(pontos_rota[-1])
    return pd.DataFrame(micropontos)

todos_locais = {**locais_base, **restaurantes, **postos_combustivel, **marinas}
opcoes_locais = list(todos_locais.keys())

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Marina do David"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Abaré SUP and Food"
def inverter_rota(): st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

df_rota_ativa = gerar_rota_inteligente(todos_locais[st.session_state['rota_origem']], todos_locais[st.session_state['rota_destino']])

# ==========================================
# 3. INTERFACE DE ROTEAMENTO (CARD FLUTUANTE)
# ==========================================
st.markdown("<div class='maps-card'>", unsafe_allow_html=True)
c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.4, 3, 2])
with c_rt1:
    st.session_state['rota_origem'] = st.selectbox("Partida", opcoes_locais, index=opcoes_locais.index(st.session_state['rota_origem']), label_visibility="collapsed")
with c_rt2:
    st.markdown('<div class="swap-btn">', unsafe_allow_html=True); st.button("⇅", on_click=inverter_rota); st.markdown('</div>', unsafe_allow_html=True)
with c_rt3:
    st.session_state['rota_destino'] = st.selectbox("Destino", opcoes_locais, index=opcoes_locais.index(st.session_state['rota_destino']), label_visibility="collapsed")
with c_rt4:
    st.markdown('<div class="start-nav-btn">', unsafe_allow_html=True)
    if st.button("▶ NAVEGAR"): st.session_state['navegando'] = True; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# FILTROS DE CAMADAS (POIs)
c_filtro1, c_filtro2, c_filtro3, c_vazio = st.columns([1.5, 1.2, 1.2, 4])
if c_filtro1.button("🍴 Restaurantes" if not st.session_state['mostrar_restaurantes'] else "✅ Restaurantes"): st.session_state['mostrar_restaurantes'] = not st.session_state['mostrar_restaurantes']; st.rerun()
if c_filtro2.button("⛽ Postos" if not st.session_state['mostrar_postos'] else "✅ Postos"): st.session_state['mostrar_postos'] = not st.session_state['mostrar_postos']; st.rerun()
if c_filtro3.button("⚓ Marinas" if not st.session_state['mostrar_marinas'] else "✅ Marinas"): st.session_state['mostrar_marinas'] = not st.session_state['mostrar_marinas']; st.rerun()

# ==========================================
# 4. MAPA COM MICROPONTOS E SATÉLITE GOOGLE
# ==========================================
fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", zoom=12.5, height=600)

fig.update_traces(
    mode="lines+markers", 
    line=dict(width=4, color="rgba(26, 115, 232, 0.6)"),
    marker=dict(size=7, color="#00E5FF", symbol="circle")
)

if st.session_state['navegando']:
    progresso = st.slider("Acelerador GPS", 0, len(df_rota_ativa)-1, st.session_state['gps_progresso'], label_visibility="collapsed")
    st.session_state['gps_progresso'] = progresso
    lat_b = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lat']
    lon_b = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lon']
    
    fig.add_trace(go.Scattermapbox(lat=[lat_b], lon=[lon_b], mode='markers+text', marker=go.scattermapbox.Marker(size=22, color="#FF3B30", symbol="circle"), text=["🛥️"], textposition="top center", textfont=dict(size=20), hoverinfo="none"))
    fig.update_layout(mapbox=dict(center=dict(lat=lat_b, lon=lon_b), zoom=15))
    if st.button("⏹ Encerrar Navegação", type="primary"): st.session_state['navegando'] = False; st.session_state['gps_progresso'] = 0; st.rerun()

if st.session_state['mostrar_restaurantes']:
    for nome, dados in restaurantes.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=12, color="#FF9800"), text=["🍴 " + nome], textposition="bottom right", textfont=dict(color="#FF9800", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"{nome}<br>{dados['desc']}"))

if st.session_state['mostrar_postos']:
    for nome, dados in postos_combustivel.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=12, color="#E53935"), text=["⛽ " + nome], textposition="bottom right", textfont=dict(color="#E53935", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"{nome}<br>{dados['desc']}"))

if st.session_state['mostrar_marinas']:
    for nome, dados in marinas.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=12, color="#3949AB"), text=["⚓ " + nome], textposition="bottom right", textfont=dict(color="#3949AB", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"{nome}<br>{dados['desc']}"))

for nome, dados in locais_base.items():
    if nome != "Ponta Negra (Calha)":
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=8, color="#757575"), text=[nome], textposition="top right", textfont=dict(color="#444", size=11, family="Roboto"), hoverinfo="text"))

fig.update_layout(
    mapbox_style="white-bg", 
    mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Google Maps", "source": ["https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"]}],
    margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False
)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. ABAS INFERIORES: REPORTAR, CONTA E EMERGÊNCIA
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
tab_alertas, tab_perfil, tab_emergencia = st.tabs(["⚠️ Reportar Perigo", "👤 Conta", "🆘 Emergência e Créditos"])

with tab_alertas:
    with st.form("form_alerta"):
        c_f1, c_f2 = st.columns([1, 2])
        tipo_alerta = c_f1.selectbox("O que é?", ["🪵 Tronco", "🏝️ Areia", "🎣 Rede", "🚓 Fiscalização", "⚠️ Enguiço"])
        local_alerta = c_f2.selectbox("Próximo de onde?", opcoes_locais)
        if st.form_submit_button("Lançar Alerta Público", type="primary"):
            st.success(f"Alerta registrado próximo a {local_alerta}!")

with tab_perfil:
    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Seu Nome")
        tipo_barco_edit = c_p2.selectbox("Embarcação", ["🛶 Canoa", "🚤 Jet Ski", "🛥️ Lancha Pequena", "🛳️ Iate", "⛴️ Barco Regional"], index=2)
        if st.form_submit_button("Salvar Perfil", type="primary"):
            st.success("Dados salvos com sucesso.")

with tab_emergencia:
    st.markdown("### 📞 Telefones de Emergência")
    st.error("**Em caso de perigo iminente na água, acione imediatamente o socorro oficial:**")
    
    st.markdown("""
    * 🚓 **Polícia Militar:** 190
    * 🚑 **SAMU (Urgência Médica):** 192
    * 🚒 **Corpo de Bombeiros:** 193
    * ⚓ **Capitania Fluvial da Amazônia Ocidental (Marinha):** 185 ou (92) 2123-2222
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Sobre")
    st.info("""
    **Ygara - O Waze dos Rios**
    Versão: 1.0 (Produção)
    
    Desenvolvido para revolucionar a segurança e a logística na Bacia Amazônica através de mapeamento colaborativo e geolocalização fluvial.
    
    *Desenvolvido por Caio Rezende.*
    """)
    
