import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

# ==========================================
# 0. SETUP DE BANCO DE DADOS (PERFIS + WAZE)
# ==========================================
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
logo_file_path = os.path.join(diretorio_atual, "Ygara Tech.png") 
banco_path = os.path.join(diretorio_atual, "ygara_publico.db")

conn = sqlite3.connect(banco_path)
conn.execute('''CREATE TABLE IF NOT EXISTS alertas_waze (
                id INTEGER PRIMARY KEY, usuario TEXT, tipo_alerta TEXT, 
                lat REAL, lon REAL, descricao TEXT, 
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                upvotes INTEGER DEFAULT 1, downvotes INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS perfis_usuarios (
                email TEXT PRIMARY KEY, nome TEXT, sobrenome TEXT,
                tipo_barco TEXT, nome_barco TEXT, pontos INTEGER DEFAULT 0, nivel TEXT DEFAULT 'Navegante')''')
conn.commit()
conn.close()

if 'usuario_email' not in st.session_state:
    st.session_state['usuario_email'] = "usuario@ygaranav.com"
    st.session_state['gps_ativo'] = False

# ==========================================
# 1. LAYOUT SUPERIOR (SEM BARRA LATERAL)
# ==========================================
# initial_sidebar_state="collapsed" garante que a barra suma
st.set_page_config(page_title="Ygara Nav | O Waze dos Rios", layout="wide", page_icon="🚤", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Oculta completamente a estrutura da barra lateral do Streamlit */
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        
        /* Ajustes de tela cheia */
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        
        /* Estilização dos Botões Superiores */
        .stButton>button { border-radius: 12px; font-weight: bold; }
        .gps-btn>button { background-color: #0078FF; color: white; border-radius: 12px; width: 100%; border: none; }
        .sos-btn>button { background-color: #FF3B30; color: white; border-radius: 12px; width: 100%; border: none; }
        
        /* Colar as abas no painel superior */
        .stTabs { margin-top: 0rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS REAIS DO PÚBLICO
# ==========================================
locais = {
    "Marina do David": {"lat": -3.069, "lon": -60.088, "tipo": "Marina"},
    "Praia da Lua": {"lat": -3.063, "lon": -60.052, "tipo": "Praia"},
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia"},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo"},
    "Flutuante Sedutor": {"lat": -3.050, "lon": -60.100, "tipo": "Lazer"},
    "Ponta Negra": {"lat": -3.076, "lon": -60.088, "tipo": "Praia/Marina"},
    "Meu Local Atual (GPS)": {"lat": -3.080, "lon": -60.060, "tipo": "GPS"} 
}

# ==========================================
# 3. PAINEL SUPERIOR FIXO (TOP BAR)
# ==========================================
# Logo Centralizada e Menor
c_logo1, c_logo2, c_logo3 = st.columns([1.5, 1, 1.5])
with c_logo2:
    if os.path.exists(logo_file_path): st.image(logo_file_path, use_container_width=True)
    else: st.markdown("<h3 style='text-align: center;'>🚤 YGARA NAV</h3>", unsafe_allow_html=True)

# Controle de Roteamento Compacto
st.markdown("#### 📍 Para onde vamos?")
col_origem, col_destino, col_acoes = st.columns([2, 2, 1.5])

with col_origem:
    origem_default = 6 if st.session_state['gps_ativo'] else 0
    origem = st.selectbox("Ponto de Partida", list(locais.keys()), index=origem_default, label_visibility="collapsed")

with col_destino:
    destino = st.selectbox("Destino", list(locais.keys()), index=1, label_visibility="collapsed")

with col_acoes:
    c_gps, c_sos = st.columns(2)
    with c_gps:
        st.markdown('<div class="gps-btn">', unsafe_allow_html=True)
        if st.button("📡 GPS"):
            st.session_state['gps_ativo'] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_sos:
        st.markdown('<div class="sos-btn">', unsafe_allow_html=True)
        if st.button("🆘 SOS"):
            st.error("Sinal emitido!")
        st.markdown('</div>', unsafe_allow_html=True)

# Ferramenta Retrátil de Reporte (Waze Style)
with st.expander("⚠️ Reportar um Perigo na Água", expanded=False):
    with st.form("form_alerta"):
        c_f1, c_f2, c_f3 = st.columns([2, 2, 3])
        tipo_alerta = c_f1.selectbox("O que há na água?", ["🏊‍♂️ Banhistas no Canal", "🪵 Tronco Perigoso", "🏝️ Banco de Areia Oculto", "🎣 Rede de Pesca Armada", "🚓 Fiscalização", "⚠️ Barco Enguiçado"])
        local_alerta = c_f2.selectbox("Perto de onde?", list(locais.keys()))
        desc_alerta = c_f3.text_input("Detalhe rápido", placeholder="Ex: No lado esquerdo da margem")
        
        if st.form_submit_button("📢 Lançar no Mapa", type="primary"):
            lat_a = locais[local_alerta]["lat"] + 0.005 
            lon_a = locais[local_alerta]["lon"] + 0.005
            conn = sqlite3.connect(banco_path)
            conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, lat_a, lon_a, desc_alerta))
            conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 10 WHERE email = ?", (st.session_state['usuario_email'],))
            conn.commit()
            conn.close()
            st.success("Alerta criado com sucesso!")

st.markdown("---")

# ==========================================
# 4. ABAS DE NAVEGAÇÃO E UX
# ==========================================
tab_mapa, tab_feed, tab_perfil = st.tabs(["🗺️ O Mapa", "💬 Feed da Água", "🚤 Meu Convés"])

# --- ABA 1: O MAPA WAZE ---
with tab_mapa:
    map_layer = st.radio("Selecione a visualização:", ["Satélite Real (Google)", "Ruas (Padrão Waze)", "Náutico Escuro"], horizontal=True)
    
    estilos = {"Satélite Real (Google)": "satellite-streets", "Ruas (Padrão Waze)": "open-street-map", "Náutico Escuro": "carto-darkmatter"}
    df_rota = pd.DataFrame({'lat': [locais[origem]["lat"], locais[destino]["lat"]], 
                            'lon': [locais[origem]["lon"], locais[destino]["lon"]], 
                            'Ponto': [origem, destino]})
    
    fig = px.line_mapbox(df_rota, lat="lat", lon="lon", mapbox_style=estilos[map_layer], zoom=11.5, height=600)
    fig.update_traces(mode="markers+lines", marker=dict(size=15, color="#00C853"), line=dict(width=6, color="#2979FF"))

    for nome, dados in locais.items():
        if nome != "Meu Local Atual (GPS)":
            fig.add_trace(go.Scattermapbox(
                lat=[dados['lat']], lon=[dados['lon']], mode='markers+text',
                marker=go.scattermapbox.Marker(size=12, color="white", symbol="circle"),
                text=[nome], textposition="top center", textfont=dict(color="white", size=14, family="Arial Black"),
                hoverinfo="text", name=dados['tipo']
            ))

    conn = sqlite3.connect(banco_path)
    df_alertas = pd.read_sql("SELECT * FROM alertas_waze", conn)
    conn.close()
    
    if not df_alertas.empty:
        df_confiaveis = df_alertas[df_alertas['upvotes'] >= df_alertas['downvotes']]
        for i, row in df_confiaveis.iterrows():
            emoji = row['tipo_alerta'].split(" ")[0]
            fig.add_trace(go.Scattermapbox(
                lat=[row['lat']], lon=[row['lon']], mode='markers+text',
                marker=go.scattermapbox.Marker(size=28, color="rgba(255, 60, 0, 0.8)"),
                text=[emoji], textposition="middle center", textfont=dict(size=18),
                hoverinfo="text", hovertext=f"<b>{row['tipo_alerta']}</b><br>{row['descricao']}"
            ))

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --- ABA 2: FEED DA COMUNIDADE ---
with tab_feed:
    st.markdown("### 🗣️ O que está rolando na água")
    if df_alertas.empty:
        st.info("O rio está limpo! Nenhum alerta reportado hoje.")
    else:
        for idx, row in df_alertas.sort_values(by="id", ascending=False).iterrows():
            with st.container():
                st.markdown(f"#### {row['tipo_alerta']}")
                st.write(f"_{row['descricao']}_ | **Reportado às {row['data_hora'][:16]}**")
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button(f"👍 Vi também ({row['upvotes']})", key=f"up_{row['id']}"):
                        conn = sqlite3.connect(banco_path)
                        conn.execute(f"UPDATE alertas_waze SET upvotes = upvotes + 1 WHERE id = {row['id']}")
                        conn.commit(); conn.close(); st.rerun()
                with c2:
                    if st.button(f"👎 Fake/Sumiu ({row['downvotes']})", key=f"dw_{row['id']}"):
                        conn = sqlite3.connect(banco_path)
                        conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}")
                        conn.commit(); conn.close(); st.rerun()
                st.divider()

# --- ABA 3: PERFIL EDITÁVEL ---
with tab_perfil:
    st.markdown("### 🚤 Personalizar Meu Perfil")
    
    conn = sqlite3.connect(banco_path)
    conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', 'Lancha', '')", (st.session_state['usuario_email'],))
    perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
    conn.close()

    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Primeiro Nome", value=perfil['nome'])
        sobrenome_edit = c_p2.text_input("Sobrenome", value=perfil['sobrenome'])
        
        c_p3, c_p4 = st.columns(2)
        tipo_barco_edit = c_p3.selectbox("Tipo de Embarcação", ["Lancha", "Jet Ski", "Iate", "Veleiro", "Bote/Canoa"], index=["Lancha", "Jet Ski", "Iate", "Veleiro", "Bote/Canoa"].index(perfil['tipo_barco']))
        nome_barco_edit = c_p4.text_input("Nome de Batismo do Barco", value=perfil['nome_barco'])
        
        if st.form_submit_button("💾 Salvar Meu Convés", type="primary"):
            conn = sqlite3.connect(banco_path)
            conn.execute("UPDATE perfis_usuarios SET nome=?, sobrenome=?, tipo_barco=?, nome_barco=? WHERE email=?", 
                         (nome_edit, sobrenome_edit, tipo_barco_edit, nome_barco_edit, st.session_state['usuario_email']))
            conn.commit()
            conn.close()
            st.success("Perfil atualizado! Você está pronto para zarpar.")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🏆 Suas Conquistas")
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("Reputação na Comunidade", f"{perfil['pontos']} Pontos")
    c_m2.metric("Patente", perfil['nivel'])
  
