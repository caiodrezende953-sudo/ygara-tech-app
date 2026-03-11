import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# 1. LAYOUT DINÂMICO
# ==========================================
st.set_page_config(page_title="Ygara Nav", layout="wide", page_icon="🧭", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stButton>button { border-radius: 24px; font-weight: 500; border: 1px solid #ddd; transition: 0.2s; white-space: nowrap;}
        .start-nav-btn>button { background-color: #1A73E8; color: white; border-radius: 24px; height: 45px; font-size: 16px; border: none; font-weight: 700; width: 100%;}
        .swap-btn>button { border-radius: 50%; width: 40px; height: 40px; padding: 0; margin-top: 18px; border: none; background-color: transparent; font-size: 20px;}
        .maps-card { padding: 10px; border-radius: 12px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

c_l1, c_l2 = st.columns([1, 10])
with c_l1:
    if os.path.exists(logo_file_path): st.image(logo_file_path, width=40)
with c_l2:
    st.markdown("<h4 style='margin:0; padding-top:5px; color:#1A73E8; font-weight:700;'>Ygara Nav</h4>", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS RECALCULADOS (TODOS NA ÁGUA)
# ==========================================
# Ajustado para cair na parte azul do mapa (Fio d'água)
locais_base = {
    "Praia da Lua": {"lat": -3.035, "lon": -60.055, "tipo": "Praia", "prof": 1.5},
    "Praia do Tupé": {"lat": -3.040, "lon": -60.250, "tipo": "Praia", "prof": 1.2},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo", "prof": 25.0},
    "Porto de Manaus (Centro)": {"lat": -3.145, "lon": -60.020, "tipo": "Porto", "prof": 15.0}
}

restaurantes = {
    "Abaré SUP and Food": {"lat": -3.044, "lon": -60.110, "tipo": "Restaurante", "prof": 3.0, "desc": "Tarumã"},
    "Flutuante Sedutor": {"lat": -3.052, "lon": -60.102, "tipo": "Restaurante", "prof": 4.0, "desc": "Tarumã"},
    "Morada dos Peixes": {"lat": -3.060, "lon": -60.095, "tipo": "Restaurante", "prof": 5.0, "desc": "Tarumã"}
}

postos_combustivel = {
    "Posto Atem Flutuante (Tarumã)": {"lat": -3.055, "lon": -60.085, "tipo": "Posto", "prof": 6.0, "desc": "Combustível e Conveniência"},
    "Posto Equador (Panair)": {"lat": -3.142, "lon": -60.012, "tipo": "Posto", "prof": 8.0, "desc": "Balsa Rio Negro"}
}

marinas = {
    "Marina do David": {"lat": -3.075, "lon": -60.038, "tipo": "Marina", "prof": 3.0, "desc": "Acesso principal"},
    "Marina Rio Bello": {"lat": -3.050, "lon": -60.082, "tipo": "Marina", "prof": 4.0, "desc": "Tarumã"},
    "Marina Tauá": {"lat": -3.040, "lon": -60.092, "tipo": "Marina", "prof": 4.5, "desc": "Tarumã"}
}

# VIA EXPRESSA DOS RIOS (MICROPONTOS DENTRO DA ÁGUA)
# Esta matriz garante que o barco faça a curva da Ponta Negra e suba o Tarumã sem encostar na terra
trilha_rio_negro = [
    {"lat": -3.145, "lon": -60.020}, # Centro / Porto
    {"lat": -3.140, "lon": -60.030}, # Rio Negro (Meio)
    {"lat": -3.130, "lon": -60.040}, # São Raimundo (Água)
    {"lat": -3.115, "lon": -60.050}, # Ponte Rio Negro (Eixo)
    {"lat": -3.100, "lon": -60.070}, # Compensa (Água)
    {"lat": -3.085, "lon": -60.090}, # Ponta Negra (Meio do rio)
    {"lat": -3.075, "lon": -60.100}, # Curva Tarumã
    {"lat": -3.065, "lon": -60.110}, # Entrada Tarumã-Açu
    {"lat": -3.050, "lon": -60.100}, # Meio do Tarumã (Marinas)
    {"lat": -3.040, "lon": -60.105}, # Fundo do Tarumã (Abaré)
    {"lat": -3.035, "lon": -60.055}, # Rio Negro direção Praia da Lua
    {"lat": -3.040, "lon": -60.250}  # Direção Tupé
]

def obter_rota_micropontos(lat1, lon1, lat2, lon2):
    lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
    pontos_curva = [{"lat": lat1, "lon": lon1}]
    
    meio_do_caminho = [p for p in trilha_rio_negro if lon_min - 0.02 < p["lon"] < lon_max + 0.02]
    if lon1 > lon2: meio_do_caminho.reverse()
    
    pontos_curva.extend(meio_do_caminho)
    pontos_curva.append({"lat": lat2, "lon": lon2})
    
    # Criador de Micropontos (Cria bolinhas a cada intervalo curto)
    rota_suave = []
    for i in range(len(pontos_curva)-1):
        p1, p2 = pontos_curva[i], pontos_curva[i+1]
        for step in range(5): # Cria 5 micropontos entre cada curva
            f = step / 5.0
            rota_suave.append({"lat": p1["lat"] + (p2["lat"] - p1["lat"]) * f, "lon": p1["lon"] + (p2["lon"] - p1["lon"]) * f})
    rota_suave.append(pontos_curva[-1])
    return pd.DataFrame(rota_suave)

todos_locais = {**locais_base, **restaurantes, **postos_combustivel, **marinas}
opcoes_locais = list(todos_locais.keys())

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Porto de Manaus (Centro)"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Abaré SUP and Food"
def inverter_rota(): st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

df_rota_ativa = obter_rota_micropontos(todos_locais[st.session_state['rota_origem']]["lat"], todos_locais[st.session_state['rota_origem']]["lon"], todos_locais[st.session_state['rota_destino']]["lat"], todos_locais[st.session_state['rota_destino']]["lon"])

# ==========================================
# 3. INTERFACE DE ROTEAMENTO
# ==========================================
st.markdown("<div class='maps-card'>", unsafe_allow_html=True)
c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.4, 3, 2])
with c_rt1:
    st.session_state['rota_origem'] = st.selectbox("Sua Posição", opcoes_locais, index=opcoes_locais.index(st.session_state['rota_origem']), label_visibility="collapsed")
with c_rt2:
    st.markdown('<div class="swap-btn">', unsafe_allow_html=True); st.button("⇅", on_click=inverter_rota); st.markdown('</div>', unsafe_allow_html=True)
with c_rt3:
    st.session_state['rota_destino'] = st.selectbox("Para onde?", opcoes_locais, index=opcoes_locais.index(st.session_state['rota_destino']), label_visibility="collapsed")
with c_rt4:
    st.markdown('<div class="start-nav-btn">', unsafe_allow_html=True)
    if st.button("Navegar"): st.session_state['navegando'] = True; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Filtros Dinâmicos
c_filtro1, c_filtro2, c_filtro3, c_vazio = st.columns([1.5, 1.3, 1.3, 4])
if c_filtro1.button("🍴 Restaurantes" if not st.session_state['mostrar_restaurantes'] else "✅ Restaurantes"): st.session_state['mostrar_restaurantes'] = not st.session_state['mostrar_restaurantes']; st.rerun()
if c_filtro2.button("⛽ Postos" if not st.session_state['mostrar_postos'] else "✅ Postos"): st.session_state['mostrar_postos'] = not st.session_state['mostrar_postos']; st.rerun()
if c_filtro3.button("⚓ Marinas" if not st.session_state['mostrar_marinas'] else "✅ Marinas"): st.session_state['mostrar_marinas'] = not st.session_state['mostrar_marinas']; st.rerun()

# ==========================================
# 4. RENDERIZAÇÃO DO MAPA (COM SATÉLITE RÁPIDO DO GOOGLE)
# ==========================================
map_layer = st.radio("Visual:", ["Satélite Ultra (Rápido)", "Mapa Náutico Simples"], horizontal=True, label_visibility="collapsed")

fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", zoom=11.5, height=650)

# A MÁGICA DOS MICROPONTOS
# Em vez de uma linha dura, mostramos pontos formando o caminho a seguir
fig.update_traces(
    mode="lines+markers", 
    line=dict(width=3, color="rgba(26, 115, 232, 0.5)"), # Linha fina e transparente
    marker=dict(size=8, color="#00E5FF", symbol="circle") # Pontos Ciano Brilhantes guiando o caminho
)

if st.session_state['navegando']:
    progresso = st.slider("Simulador GPS", 0, len(df_rota_ativa)-1, st.session_state['gps_progresso'], label_visibility="collapsed")
    st.session_state['gps_progresso'] = progresso
    lat_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lat']
    lon_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lon']
    fig.add_trace(go.Scattermapbox(lat=[lat_barco], lon=[lon_barco], mode='markers', marker=go.scattermapbox.Marker(size=22, color="#FF3B30", symbol="circle"), hoverinfo="none"))
    fig.update_layout(mapbox=dict(center=dict(lat=lat_barco, lon=lon_barco), zoom=14.5))
    if st.button("⏹ Encerrar Navegação", type="primary"): st.session_state['navegando'] = False; st.session_state['gps_progresso'] = 0; st.rerun()

# Plotando Restaurantes
if st.session_state['mostrar_restaurantes']:
    for nome, dados in restaurantes.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#FF9800", symbol="circle"), text=["🍴 " + nome], textposition="bottom right", textfont=dict(color="#FF9800", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

# Plotando Postos de Combustível
if st.session_state['mostrar_postos']:
    for nome, dados in postos_combustivel.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#E53935", symbol="circle"), text=["⛽ " + nome], textposition="bottom right", textfont=dict(color="#E53935", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

# Plotando Marinas
if st.session_state['mostrar_marinas']:
    for nome, dados in marinas.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#3949AB", symbol="circle"), text=["⚓ " + nome], textposition="bottom right", textfont=dict(color="#3949AB", size=13, family="Roboto", weight="bold"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

# CONFIGURANDO O SATÉLITE RÁPIDO DO GOOGLE (Não trava)
if map_layer == "Satélite Ultra (Rápido)":
    fig.update_layout(
        mapbox_style="white-bg", 
        mapbox_layers=[{
            "below": 'traces', 
            "sourcetype": "raster", 
            "sourceattribution": "Google Maps", 
            "source": ["https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"] # Satélite Google Direto (Super leve)
        }],
        margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False
    )
else:
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. TABS INFERIORES (COMUNIDADE)
# ==========================================
tab_alertas, tab_perfil = st.tabs(["⚠️ Reportar Perigo", "👤 Conta"])
with tab_alertas:
    with st.form("form_alerta"):
        st.write("Viu algo na água? Avise todos.")
        c_f1, c_f2 = st.columns([1, 2])
        tipo_alerta = c_f1.selectbox("O que é?", ["🪵 Tronco", "🏝️ Areia", "🎣 Rede", "🚓 Marinha"])
        local_alerta = c_f2.selectbox("Onde?", opcoes_locais)
        if st.form_submit_button("Lançar Alerta", type="primary"):
            st.success("Alerta registrado com sucesso!")
            
