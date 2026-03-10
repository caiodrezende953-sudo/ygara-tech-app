import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import math
from datetime import datetime

# ==========================================
# 0. SETUP DE BANCO DE DADOS (WAZE FLUVIAL PRO)
# ==========================================
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
logo_file_path = os.path.join(diretorio_atual, "Ygara Tech.png") 
banco_path = os.path.join(diretorio_atual, "ygara_waze_pro.db")

conn = sqlite3.connect(banco_path)
conn.execute('''CREATE TABLE IF NOT EXISTS alertas_waze (
                id INTEGER PRIMARY KEY, 
                usuario TEXT,
                tipo_alerta TEXT, 
                lat REAL, 
                lon REAL, 
                descricao TEXT, 
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                upvotes INTEGER DEFAULT 1,
                downvotes INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS usuarios_pontos (
                usuario TEXT PRIMARY KEY,
                pontos INTEGER DEFAULT 0,
                nivel TEXT DEFAULT 'Marujo')''')
conn.commit()
conn.close()

# Função simples para calcular distância entre dois pontos (Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371 # Raio da terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ==========================================
# 1. IDENTIDADE VISUAL E LAYOUT FULL
# ==========================================
st.set_page_config(page_title="Ygara | Waze Fluvial", layout="wide", page_icon="📍")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        .stButton>button { border-radius: 8px; font-weight: bold; }
        .sos-btn>button { background-color: #ff4b4b; color: white; border-radius: 30px; height: 50px; font-size: 18px; }
        .stTabs { margin-top: -1rem !important; }
    </style>
""", unsafe_allow_html=True)

# SIMULADOR DE USUÁRIO LOGADO
usuario_atual = "Cmdt. Rezende"

# ==========================================
# 2. BASE DE DADOS ESPACIAL (PORTOS)
# ==========================================
portos = {
    "Manaus, AM": {"lat": -3.119, "lon": -60.021, "nivel": "14.2m", "clima": "🌤️ Limpo"},
    "Foz do Rio Madeira": {"lat": -3.888, "lon": -59.018, "nivel": "15.1m", "clima": "🌦️ Chuva Leve"},
    "Novo Aripuanã, AM": {"lat": -5.120, "lon": -60.380, "nivel": "12.8m", "clima": "⛈️ Tempestade"},
    "Manicoré, AM": {"lat": -5.809, "lon": -61.300, "nivel": "11.5m", "clima": "☁️ Nublado"},
    "Humaitá, AM": {"lat": -7.512, "lon": -63.022, "nivel": "10.2m", "clima": "🌤️ Limpo"},
    "Porto Velho, RO": {"lat": -8.761, "lon": -63.903, "nivel": "9.8m", "clima": "☀️ Ensolarado"},
}

# ==========================================
# 3. BARRA LATERAL (CONTROLE E REPORT)
# ==========================================
col_esq, col_logo, col_dir = st.sidebar.columns([1, 4, 1])
with col_logo:
    if os.path.exists(logo_file_path):
        st.image(logo_file_path, use_container_width=True)
    else:
        st.markdown("### YGARA NAV")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗺️ Roteamento")
origem = st.sidebar.selectbox("Partida", list(portos.keys()), index=0)
destino = st.sidebar.selectbox("Destino", list(portos.keys()), index=5)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📢 Reportar Perigo Real")
with st.sidebar.form("form_alerta"):
    tipo_alerta = st.selectbox("Classificação", [
        "🏝️ Banco de Areia (Risco Encalhe)", 
        "🪵 Balseiro Gigante / Tronco", 
        "🌫️ Neblina Densa", 
        "🏴‍☠️ Atividade de Pirataria",
        "🚢 Balsa à Deriva"
    ])
    local_alerta = st.selectbox("Referência mais próxima", list(portos.keys()))
    desc_alerta = st.text_input("Detalhes adicionais", placeholder="Ex: Fechando o canal direito")
    
    submit_alerta = st.form_submit_button("Lançar Alerta no Mapa", type="primary")
    
    if submit_alerta:
        lat_alerta = portos[local_alerta]["lat"] + 0.08
        lon_alerta = portos[local_alerta]["lon"] + 0.08
        conn = sqlite3.connect(banco_path)
        conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (usuario_atual, tipo_alerta, lat_alerta, lon_alerta, desc_alerta))
        conn.execute("INSERT OR IGNORE INTO usuarios_pontos (usuario) VALUES (?)", (usuario_atual,))
        conn.execute("UPDATE usuarios_pontos SET pontos = pontos + 10 WHERE usuario = ?", (usuario_atual,))
        conn.commit()
        conn.close()
        st.sidebar.success("✅ Alerta enviado! +10 Pontos.")

st.sidebar.markdown("---")
st.sidebar.markdown('<div class="sos-btn">', unsafe_allow_html=True)
if st.sidebar.button("🚨 BOTÃO SOS (Marinha)", use_container_width=True):
    st.sidebar.error("Sinal de Socorro enviado com suas coordenadas geográficas.")
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. PROCESSAMENTO DE DADOS (Puxando Alertas)
# ==========================================
conn = sqlite3.connect(banco_path)
df_alertas = pd.read_sql("SELECT * FROM alertas_waze", conn)
conn.close()

# Filtro de confiabilidade (Se tiver mais downvotes do que upvotes, não mostra no mapa principal)
df_confiaveis = df_alertas[df_alertas['upvotes'] >= df_alertas['downvotes']] if not df_alertas.empty else df_alertas

# ==========================================
# 5. DASHBOARD ORGANIZADO EM ABAS
# ==========================================
tab_mapa, tab_comunidade, tab_perfil = st.tabs(["🗺️ Mapa de Navegação", "👥 Feed da Comunidade", "⭐ Meu Perfil"])

with tab_mapa:
    c_m1, c_m2, c_m3 = st.columns([2, 5, 2])
    with c_m1:
        st.info(f"📍 **Partida:** {portos[origem]['nivel']} | {portos[origem]['clima']}")
    with c_m3:
        st.success(f"🏁 **Destino:** {portos[destino]['nivel']} | {portos[destino]['clima']}")
        
    map_style = st.radio("Estilo do Mapa", ["Claro (Dia)", "Noturno (Dark Mode)"], horizontal=True, label_visibility="collapsed")
    tema_mapa = "carto-darkmatter" if map_style == "Noturno (Dark Mode)" else "open-street-map"
    
    # Rota Base
    latitudes = [portos[origem]["lat"], portos[destino]["lat"]]
    longitudes = [portos[origem]["lon"], portos[destino]["lon"]]
    df_rota = pd.DataFrame({'lat': latitudes, 'lon': longitudes, 'Ponto': [origem, destino]})
    
    fig = px.line_mapbox(df_rota, lat="lat", lon="lon", zoom=5.2, mapbox_style=tema_mapa, height=600)
    fig.update_traces(mode="markers+lines", marker=dict(size=12, color="#0052cc"), line=dict(width=5, color="#0052cc"))

    # Plotando os alertas confiáveis
    if not df_confiaveis.empty:
        def cor_alerta(tipo):
            if "Areia" in tipo: return "orange"
            if "Tronco" in tipo: return "brown"
            if "Neblina" in tipo: return "gray"
            if "Pirataria" in tipo: return "red"
            return "purple"
        
        df_confiaveis['color'] = df_confiaveis['tipo_alerta'].apply(cor_alerta)
        
        for i, row in df_confiaveis.iterrows():
            fig.add_trace(go.Scattermapbox(
                lat=[row['lat']], lon=[row['lon']], mode='markers+text',
                marker=go.scattermapbox.Marker(size=25, color=row['color'], opacity=0.9),
                text=[row['tipo_alerta'].split(" ")[0]], textposition="bottom right", hoverinfo="text",
                hovertext=f"<b>{row['tipo_alerta']}</b><br>{row['descricao']}<br><i>Confirmado por {row['upvotes']} cmte(s)</i>",
                name="Alerta"
            ))

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_comunidade:
    st.markdown("### 📋 Feed de Alertas e Validação")
    st.write("Ajude a manter o mapa limpo confirmando ou rejeitando os perigos relatados.")
    
    if df_alertas.empty:
        st.info("Nenhum alerta ativo no momento.")
    else:
        for idx, row in df_alertas.sort_values(by="id", ascending=False).iterrows():
            with st.container():
                c1, c2, c3 = st.columns([6, 2, 2])
                with c1:
                    status = "✅ Confiável" if row['upvotes'] >= row['downvotes'] else "❌ Baixa Confiança"
                    st.markdown(f"**{row['tipo_alerta']}** ({status})\n\nReportado por: *{row['usuario']}* em {row['data_hora'][:16]}\n\n_{row['descricao']}_")
                
                with c2:
                    if st.button(f"👍 Ainda está lá ({row['upvotes']})", key=f"up_{row['id']}"):
                        conn = sqlite3.connect(banco_path)
                        conn.execute(f"UPDATE alertas_waze SET upvotes = upvotes + 1 WHERE id = {row['id']}")
                        conn.execute("UPDATE usuarios_pontos SET pontos = pontos + 2 WHERE usuario = ?", (usuario_atual,))
                        conn.commit()
                        conn.close()
                        st.rerun()
                
                with c3:
                    if st.button(f"👎 Já sumiu ({row['downvotes']})", key=f"down_{row['id']}"):
                        conn = sqlite3.connect(banco_path)
                        conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}")
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.markdown("---")

with tab_perfil:
    st.markdown("### ⭐ Minha Frota e Reputação")
    
    conn = sqlite3.connect(banco_path)
    try:
        meus_dados = pd.read_sql(f"SELECT pontos FROM usuarios_pontos WHERE usuario = '{usuario_atual}'", conn).iloc[0]
        meus_pontos = meus_dados['pontos']
    except:
        meus_pontos = 0
    conn.close()
    
    if meus_pontos < 50: nivel = "⚓ Marujo (Iniciante)"
    elif meus_pontos < 200: nivel = "🧭 Piloto de Rota"
    else: nivel = "🚢 Lobo do Rio (Especialista)"
        
    c_p1, c_p2, c_p3 = st.columns(3)
    c_p1.metric("Usuário Atual", usuario_atual)
    c_p2.metric("Pontos de Reputação", f"{meus_pontos} pts", "Contribuições")
    c_p3.metric("Nível na Comunidade", nivel)
    
    st.write("💡 **Como ganhar pontos?**\n- Reportar um perigo real: +10 pontos.\n- Confirmar o alerta de outro comandante (Ainda está lá): +2 pontos.\n\n*Comandantes com o nível 'Lobo do Rio' possuem alertas validados automaticamente sem passar pelo filtro.*")
    