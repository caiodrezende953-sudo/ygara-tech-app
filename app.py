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
conn.execute('''CREATE TABLE IF NOT EXISTS locais_comunidade (nome TEXT PRIMARY KEY, tipo TEXT, lat REAL, lon REAL, profundidade_est REAL, criador TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS historico_rotas (id INTEGER PRIMARY KEY, email TEXT, tipo_barco TEXT, lat REAL, lon REAL, data_hora DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit(); conn.close()

if 'usuario_email' not in st.session_state: st.session_state['usuario_email'] = "usuario@ygaranav.com"
if 'navegando' not in st.session_state: st.session_state['navegando'] = False
if 'gps_progresso' not in st.session_state: st.session_state['gps_progresso'] = 0

# Filtros do Mapa (Pílulas POIs)
if 'mostrar_restaurantes' not in st.session_state: st.session_state['mostrar_restaurantes'] = True
if 'mostrar_postos' not in st.session_state: st.session_state['mostrar_postos'] = True
if 'mostrar_marinas' not in st.session_state: st.session_state['mostrar_marinas'] = True
if 'mostrar_canal' not in st.session_state: st.session_state['mostrar_canal'] = False

# ==========================================
# 1. LAYOUT DINÂMICO E CABEÇALHO LIMPO
# ==========================================
st.set_page_config(page_title="Ygara", layout="wide", page_icon="🧭", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .stButton>button { border-radius: 24px; font-weight: 500; border: 1px solid #ddd; transition: 0.2s; white-space: nowrap;}
        .stButton>button:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.15); }
        .start-nav-btn>button { background-color: #1A73E8; color: white; border-radius: 24px; height: 45px; font-size: 16px; border: none; font-weight: 700; width: 100%;}
        .start-nav-btn>button:hover { background-color: #1557B0; color: white; }
        .swap-btn>button { border-radius: 50%; width: 40px; height: 40px; padding: 0; margin-top: 18px; border: none; background-color: transparent; font-size: 20px;}
        .maps-card { padding: 10px; border-radius: 12px; margin-bottom: 10px; }
        /* Remove espaços excedentes da logo */
        .logo-container { display: flex; justify-content: center; align-items: center; padding-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# CABEÇALHO COM LOGO CENTRALIZADA
c_l1, c_l2, c_l3 = st.columns([2, 1, 2])
with c_l2:
    if os.path.exists(logo_file_path): 
        st.image(logo_file_path, use_container_width=True)

# ==========================================
# 2. BANCO DE DADOS DE POIs (PONTOS DE INTERESSE)
# ==========================================
locais_base = {
    "Praia da Lua": {"lat": -3.0330, "lon": -60.0520, "tipo": "Praia", "prof": 1.5, "desc": "Praia de água doce"},
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia", "prof": 1.2, "desc": "Reserva de desenvolvimento sustentável"},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo", "prof": 25.0, "desc": "Fenômeno natural"},
    "Porto de Manaus (Centro)": {"lat": -3.139, "lon": -60.023, "tipo": "Porto", "prof": 15.0, "desc": "Embarque regional e cargas"}
}

restaurantes = {
    "Abaré SUP and Food": {"lat": -3.042, "lon": -60.105, "tipo": "Restaurante", "prof": 3.0, "desc": "Flutuante de Luxo - Comida Regional"},
    "Flutuante Sedutor": {"lat": -3.050, "lon": -60.100, "tipo": "Restaurante", "prof": 4.0, "desc": "Bebidas e Petiscos"},
    "Morada dos Peixes": {"lat": -3.085, "lon": -60.025, "tipo": "Restaurante", "prof": 5.0, "desc": "Peixaria Regional Tradicional"}
}

postos_combustivel = {
    "Posto Atem Flutuante (Tarumã)": {"lat": -3.055, "lon": -60.085, "tipo": "Posto", "prof": 6.0, "desc": "Gasolina, Diesel e Conveniência"},
    "Posto Equador (Panair)": {"lat": -3.142, "lon": -60.015, "tipo": "Posto", "prof": 8.0, "desc": "Abastecimento rápido 24h"}
}

marinas = {
    "Marina do David": {"lat": -3.0734, "lon": -60.0336, "tipo": "Marina", "prof": 3.0, "desc": "Embarque de passageiros e fretes"},
    "Marina Rio Bello": {"lat": -3.050, "lon": -60.080, "tipo": "Marina", "prof": 4.0, "desc": "Vagas secas, molhadas e descida de lanchas"},
    "Marina Tauá": {"lat": -3.040, "lon": -60.090, "tipo": "Marina", "prof": 4.5, "desc": "Estrutura completa para embarcações de lazer"}
}

# O Canal de Micropontos (Hidrovia Segura)
trilha_rio_negro = [{"lat": -3.136, "lon": -59.897}, {"lat": -3.139, "lon": -60.023}, {"lat": -3.135, "lon": -60.030}, {"lat": -3.125, "lon": -60.038}, {"lat": -3.115, "lon": -60.045}, {"lat": -3.100, "lon": -60.060}, {"lat": -3.085, "lon": -60.075}, {"lat": -3.076, "lon": -60.088}, {"lat": -3.065, "lon": -60.120}, {"lat": -3.045, "lon": -60.180}, {"lat": -3.033, "lon": -60.254}]

def obter_rota_curvada(lat1, lon1, lat2, lon2):
    lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
    pontos_curva = [{"lat": lat1, "lon": lon1}]
    meio_do_caminho = [p for p in trilha_rio_negro if lon_min < p["lon"] < lon_max]
    if lon1 > lon2: meio_do_caminho.reverse()
    pontos_curva.extend(meio_do_caminho)
    pontos_curva.append({"lat": lat2, "lon": lon2})
    rota_suave = []
    for i in range(len(pontos_curva)-1):
        p1, p2 = pontos_curva[i], pontos_curva[i+1]
        for step in range(8):
            f = step / 8.0; rota_suave.append({"lat": p1["lat"] + (p2["lat"] - p1["lat"]) * f, "lon": p1["lon"] + (p2["lon"] - p1["lon"]) * f})
    rota_suave.append(pontos_curva[-1])
    return pd.DataFrame(rota_suave)

# Mesclando todos os locais para o seletor de rotas
todos_locais = {**locais_base, **restaurantes, **postos_combustivel, **marinas}
opcoes_locais = list(todos_locais.keys())

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Marina Rio Bello"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Abaré SUP and Food"
def inverter_rota(): st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

conn = sqlite3.connect(banco_path)
conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', '🚤 Jet Ski', '')", (st.session_state['usuario_email'],))
perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
conn.close()

df_rota_ativa = obter_rota_curvada(todos_locais[st.session_state['rota_origem']]["lat"], todos_locais[st.session_state['rota_origem']]["lon"], todos_locais[st.session_state['rota_destino']]["lat"], todos_locais[st.session_state['rota_destino']]["lon"])

# ==========================================
# 3. INTERFACE DE ROTEAMENTO ESTILO MAPS
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
    if st.button("INICIAR"): st.session_state['navegando'] = True; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Filtros Dinâmicos (Pílulas de Camadas do Mapa)
c_filtro1, c_filtro2, c_filtro3, c_filtro4, c_vazio = st.columns([1.5, 1.3, 1.3, 2, 2])
if c_filtro1.button("🍴 Restaurantes" if not st.session_state['mostrar_restaurantes'] else "✅ Restaurantes"):
    st.session_state['mostrar_restaurantes'] = not st.session_state['mostrar_restaurantes']; st.rerun()
if c_filtro2.button("⛽ Postos" if not st.session_state['mostrar_postos'] else "✅ Postos"):
    st.session_state['mostrar_postos'] = not st.session_state['mostrar_postos']; st.rerun()
if c_filtro3.button("⚓ Marinas" if not st.session_state['mostrar_marinas'] else "✅ Marinas"):
    st.session_state['mostrar_marinas'] = not st.session_state['mostrar_marinas']; st.rerun()
if c_filtro4.button("🛤️ Canal (Micropontos)" if not st.session_state['mostrar_canal'] else "✅ Canal (Micropontos)"):
    st.session_state['mostrar_canal'] = not st.session_state['mostrar_canal']; st.rerun()

# ==========================================
# 4. RENDERIZAÇÃO DO MAPA
# ==========================================
if st.session_state['navegando']:
    progresso = st.slider("Simulador GPS", 0, len(df_rota_ativa)-1, st.session_state['gps_progresso'], label_visibility="collapsed")
    if progresso != st.session_state['gps_progresso']:
        st.session_state['gps_progresso'] = progresso
        conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO historico_rotas (email, tipo_barco, lat, lon) VALUES (?, ?, ?, ?)", (st.session_state['usuario_email'], perfil['tipo_barco'], float(df_rota_ativa.iloc[progresso]['lat']), float(df_rota_ativa.iloc[progresso]['lon']))); conn.commit(); conn.close()
    lat_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lat']
    lon_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lon']
    
    fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", zoom=15, height=600)
    fig.update_traces(mode="lines", line=dict(width=10, color="#1A73E8")) 
    fig.add_trace(go.Scattermapbox(lat=[lat_barco], lon=[lon_barco], mode='markers', marker=go.scattermapbox.Marker(size=20, color="#1A73E8", symbol="circle"), hoverinfo="none"))
    
    fig.update_layout(mapbox=dict(center=dict(lat=lat_barco, lon=lon_barco), zoom=15), mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    if st.button("⏹ Sair da Navegação", type="primary"): st.session_state['navegando'] = False; st.session_state['gps_progresso'] = 0; st.rerun()
    st.plotly_chart(fig, use_container_width=True)

else:
    # MODO EXPLORAÇÃO MAPS
    fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", zoom=11.2, height=600)
    fig.update_traces(mode="lines", line=dict(width=6, color="#1A73E8")) 

    # Plotando Micropontos do Canal
    if st.session_state['mostrar_canal']:
        df_canal = pd.DataFrame(trilha_rio_negro)
        fig.add_trace(go.Scattermapbox(lat=df_canal["lat"], lon=df_canal["lon"], mode='lines+markers', marker=go.scattermapbox.Marker(size=5, color="rgba(100, 100, 100, 0.6)"), line=dict(width=2, color="rgba(100, 100, 100, 0.5)", dash="dot"), hoverinfo="text", text="Canal Principal da Capitania"))

    # Plotando Restaurantes
    if st.session_state['mostrar_restaurantes']:
        for nome, dados in restaurantes.items():
            fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#FF9800", symbol="circle"), text=["🍴 " + nome], textposition="bottom center", textfont=dict(color="#FF9800", size=12, family="Roboto"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

    # Plotando Postos de Combustível
    if st.session_state['mostrar_postos']:
        for nome, dados in postos_combustivel.items():
            fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#E53935", symbol="circle"), text=["⛽ " + nome], textposition="bottom center", textfont=dict(color="#E53935", size=12, family="Roboto"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

    # Plotando Marinas
    if st.session_state['mostrar_marinas']:
        for nome, dados in marinas.items():
            fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#3949AB", symbol="circle"), text=["⚓ " + nome], textposition="bottom center", textfont=dict(color="#3949AB", size=12, family="Roboto"), hoverinfo="text", hovertext=f"<b>{nome}</b><br>{dados['desc']}"))

    # Plotando Locais Base (Praias, Encontro das Águas)
    for nome, dados in locais_base.items():
        fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=10, color="#757575", symbol="circle"), text=[nome], textposition="top center", textfont=dict(color="#616161", size=11, family="Roboto"), hoverinfo="text"))

    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 5. TABS INFERIORES (PERFIL E ALERTAS)
# ==========================================
tab_alertas, tab_perfil = st.tabs(["⚠️ Comunidade & Alertas", "👤 Configurações do Barco"])

with tab_alertas:
    st.write("Reporte perigos para ajudar outros navegantes.")
    with st.form("form_alerta"):
        c_f1, c_f2 = st.columns([1, 2])
        tipo_alerta = c_f1.selectbox("O que há na água?", ["🪵 Tronco", "🏝️ Banco de Areia", "🎣 Rede", "🚓 Marinha", "⚠️ Enguiço"])
        local_alerta = c_f2.selectbox("Perto de onde?", opcoes_locais)
        if st.form_submit_button("Lançar Alerta", type="primary"):
            conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, todos_locais[local_alerta]["lat"] + 0.003, todos_locais[local_alerta]["lon"] + 0.003, "Reportado via App")); conn.commit(); conn.close(); st.success("Criado!")

with tab_perfil:
    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Seu Nome", value=perfil['nome'])
        tipo_barco_edit = c_p2.selectbox("Tipo de Embarcação", ["🛶 Canoa", "🚤 Jet Ski", "🛥️ Lancha Pequena", "🛳️ Iate", "⛴️ Barco Regional"], index=1)
        if st.form_submit_button("Salvar Perfil", type="primary"):
            conn = sqlite3.connect(banco_path); conn.execute("UPDATE perfis_usuarios SET nome=?, tipo_barco=? WHERE email=?", (nome_edit, tipo_barco_edit, st.session_state['usuario_email'])); conn.commit(); conn.close(); st.success("Salvo!"); st.rerun()
            
