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
# 1. LAYOUT E ESTILOS
# ==========================================
st.set_page_config(page_title="Ygara Nav | O Waze dos Rios", layout="wide", page_icon="🚤", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        .stButton>button { border-radius: 12px; font-weight: bold; width: 100%; }
        .swap-btn>button { background-color: #f0f2f6; color: #31333F; border-radius: 50%; width: 45px; height: 45px; padding: 0; display: flex; align-items: center; justify-content: center; margin: auto; margin-top: 15px;}
        .gps-btn>button { background-color: #0078FF; color: white; border: none; }
        .sos-btn>button { background-color: #FF3B30; color: white; border: none; }
        .stTabs { margin-top: 0rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS E MOTOR DE CURVAS FLUVIAIS
# ==========================================
locais = {
    "Marina do David": {"lat": -3.069, "lon": -60.088, "tipo": "Marina"},
    "Praia da Lua": {"lat": -3.063, "lon": -60.052, "tipo": "Praia"},
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia"},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo"},
    "Flutuante Sedutor": {"lat": -3.050, "lon": -60.100, "tipo": "Lazer"},
    "Orla da Ponta Negra": {"lat": -3.076, "lon": -60.088, "tipo": "Praia/Marina"},
    "Centro (Porto de Manaus)": {"lat": -3.139, "lon": -60.023, "tipo": "Porto"},
    "Meu Local Atual (GPS)": {"lat": -3.080, "lon": -60.060, "tipo": "GPS"} 
}

tipos_embarcacao = [
    "🛶 Canoa / Rabeta",
    "🚤 Jet Ski",
    "🛥️ Lancha (Até 20 pés)",
    "🛥️ Lancha (21 a 40 pés)",
    "🛳️ Lancha / Iate (+40 pés)",
    "⛴️ Barco Regional (Até 15m)",
    "⛴️ Barco Regional (+15m)",
    "🚢 Navio Gaiola",
    "🚢 Empurrador / Balsa"
]

# Variáveis de Inversão de Rota
if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Centro (Porto de Manaus)"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Praia do Tupé"

def inverter_rota():
    temp = st.session_state['rota_origem']
    st.session_state['rota_origem'] = st.session_state['rota_destino']
    st.session_state['rota_destino'] = temp

# ==========================================
# 3. PAINEL SUPERIOR (GOOGLE MAPS STYLE)
# ==========================================
c_logo1, c_logo2, c_logo3 = st.columns([1.5, 1, 1.5])
with c_logo2:
    if os.path.exists(logo_file_path): st.image(logo_file_path, use_container_width=True)
    else: st.markdown("<h3 style='text-align: center;'>🚤 YGARA NAV</h3>", unsafe_allow_html=True)

# Bloco de Roteamento Ida e Volta
c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.5, 3, 2])

with c_rt1:
    st.session_state['rota_origem'] = st.selectbox("Partida", list(locais.keys()), index=list(locais.keys()).index(st.session_state['rota_origem']), label_visibility="collapsed")
with c_rt2:
    st.markdown('<div class="swap-btn">', unsafe_allow_html=True)
    if st.button("🔁", on_click=inverter_rota, help="Inverter rota"): pass
    st.markdown('</div>', unsafe_allow_html=True)
with c_rt3:
    st.session_state['rota_destino'] = st.selectbox("Destino", list(locais.keys()), index=list(locais.keys()).index(st.session_state['rota_destino']), label_visibility="collapsed")
with c_rt4:
    c_gps, c_sos = st.columns(2)
    with c_gps:
        st.markdown('<div class="gps-btn">', unsafe_allow_html=True)
        if st.button("📡 GPS"): st.session_state['gps_ativo'] = True; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_sos:
        st.markdown('<div class="sos-btn">', unsafe_allow_html=True)
        if st.button("🆘 SOS"): st.error("Sinal emitido!")
        st.markdown('</div>', unsafe_allow_html=True)

# Ferramenta de Reporte
with st.expander("⚠️ Reportar um Perigo na Água", expanded=False):
    with st.form("form_alerta"):
        c_f1, c_f2, c_f3 = st.columns([2, 2, 3])
        tipo_alerta = c_f1.selectbox("O que há na água?", ["🏊‍♂️ Banhistas no Canal", "🪵 Tronco Perigoso", "🏝️ Banco de Areia Oculto", "🎣 Rede de Pesca Armada", "🚓 Fiscalização da Marinha", "⚠️ Barco Enguiçado"])
        local_alerta = c_f2.selectbox("Perto de onde?", list(locais.keys()))
        desc_alerta = c_f3.text_input("Detalhe rápido", placeholder="Ex: Canal esquerdo bloqueado")
        
        if st.form_submit_button("📢 Lançar no Mapa", type="primary"):
            lat_a = locais[local_alerta]["lat"] + 0.005 
            lon_a = locais[local_alerta]["lon"] + 0.005
            conn = sqlite3.connect(banco_path)
            conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, lat_a, lon_a, desc_alerta))
            conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 10 WHERE email = ?", (st.session_state['usuario_email'],))
            conn.commit(); conn.close()
            st.success("Alerta criado com sucesso!")

# ==========================================
# 4. ABAS DE NAVEGAÇÃO E UX
# ==========================================
tab_mapa, tab_feed, tab_perfil = st.tabs(["🗺️ O Mapa", "💬 Feed da Água", "🚤 Meu Convés"])

# --- ABA 1: O MAPA COM ROTAS CURVAS ---
with tab_mapa:
    map_layer = st.radio("Selecione a visualização:", ["Satélite Real (Google)", "Náutico Escuro", "Ruas (Padrão Waze)"], horizontal=True)
    estilos = {"Satélite Real (Google)": "satellite-streets", "Ruas (Padrão Waze)": "open-street-map", "Náutico Escuro": "carto-darkmatter"}
    
    origem = st.session_state['rota_origem']
    destino = st.session_state['rota_destino']

    # SIMULADOR DE ROTA CURVA (WAYPOINTS PELO RIO NEGRO)
    lats_rota = [locais[origem]["lat"]]
    lons_rota = [locais[origem]["lon"]]

    # Lógica simples para forçar a curva se cruzar de Manaus Sul (Centro) para Oeste (Tupé/Lua)
    if (origem == "Centro (Porto de Manaus)" and destino in ["Praia do Tupé", "Praia da Lua", "Marina do David"]) or \
       (destino == "Centro (Porto de Manaus)" and origem in ["Praia do Tupé", "Praia da Lua", "Marina do David"]):
        # Adiciona waypoints no meio do rio para a linha não cruzar por cima do bairro Compensa
        lats_rota.insert(1, -3.125) 
        lons_rota.insert(1, -60.050)
        lats_rota.insert(2, -3.090) 
        lons_rota.insert(2, -60.080)

    lats_rota.append(locais[destino]["lat"])
    lons_rota.append(locais[destino]["lon"])

    df_rota = pd.DataFrame({'lat': lats_rota, 'lon': lons_rota})
    
    fig = px.line_mapbox(df_rota, lat="lat", lon="lon", mapbox_style=estilos[map_layer], zoom=11.2, height=600)
    fig.update_traces(mode="lines", line=dict(width=7, color="#00E5FF")) # Linha ciano brilhante estilo GPS

    # Plotar Locais
    for nome, dados in locais.items():
        if nome != "Meu Local Atual (GPS)":
            fig.add_trace(go.Scattermapbox(
                lat=[dados['lat']], lon=[dados['lon']], mode='markers+text',
                marker=go.scattermapbox.Marker(size=14, color="white", symbol="circle"),
                text=[nome], textposition="bottom center", textfont=dict(color="white", size=13, family="Arial"),
                hoverinfo="text", name=dados['tipo']
            ))

    # Plotar Alertas
    conn = sqlite3.connect(banco_path)
    df_alertas = pd.read_sql("SELECT * FROM alertas_waze", conn)
    conn.close()
    
    if not df_alertas.empty:
        df_confiaveis = df_alertas[df_alertas['upvotes'] >= df_alertas['downvotes']]
        for i, row in df_confiaveis.iterrows():
            emoji = row['tipo_alerta'].split(" ")[0]
            fig.add_trace(go.Scattermapbox(
                lat=[row['lat']], lon=[row['lon']], mode='markers+text',
                marker=go.scattermapbox.Marker(size=30, color="rgba(255, 60, 0, 0.9)"),
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
                    if st.button(f"👎 Já Sumiu ({row['downvotes']})", key=f"dw_{row['id']}"):
                        conn = sqlite3.connect(banco_path)
                        conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}")
                        conn.commit(); conn.close(); st.rerun()
                st.divider()

# --- ABA 3: PERFIL DETALHADO ---
with tab_perfil:
    st.markdown("### 🚤 Personalizar Meu Convés")
    
    conn = sqlite3.connect(banco_path)
    conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', '🚤 Jet Ski', '')", (st.session_state['usuario_email'],))
    perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
    conn.close()

    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Primeiro Nome", value=perfil['nome'])
        sobrenome_edit = c_p2.text_input("Sobrenome", value=perfil['sobrenome'])
        
        # Uso da lista detalhada de embarcações
        tipo_barco_edit = st.selectbox("Qual é a sua Embarcação?", tipos_embarcacao, index=tipos_embarcacao.index(perfil['tipo_barco']) if perfil['tipo_barco'] in tipos_embarcacao else 2)
        nome_barco_edit = st.text_input("Nome de Batismo da Embarcação", value=perfil['nome_barco'])
        
        if st.form_submit_button("💾 Atualizar Perfil Público", type="primary"):
            conn = sqlite3.connect(banco_path)
            conn.execute("UPDATE perfis_usuarios SET nome=?, sobrenome=?, tipo_barco=?, nome_barco=? WHERE email=?", 
                         (nome_edit, sobrenome_edit, tipo_barco_edit, nome_barco_edit, st.session_state['usuario_email']))
            conn.commit(); conn.close()
            st.success("Perfil atualizado! Configurações de barco ajustadas.")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🏆 Suas Conquistas")
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("Reputação na Comunidade", f"{perfil['pontos']} Pontos")
    c_m2.metric("Patente Waze", perfil['nivel'])
  
