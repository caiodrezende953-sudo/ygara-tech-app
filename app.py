import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

# ==========================================
# 0. SETUP DE BANCO DE DADOS (WAZE COLABORATIVO)
# ==========================================
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
logo_file_path = os.path.join(diretorio_atual, "Ygara Tech.png") 
banco_path = os.path.join(diretorio_atual, "ygara_publico.db")

conn = sqlite3.connect(banco_path)
# Tabela de Alertas Temporários (Troncos, Banhistas)
conn.execute('''CREATE TABLE IF NOT EXISTS alertas_waze (
                id INTEGER PRIMARY KEY, usuario TEXT, tipo_alerta TEXT, 
                lat REAL, lon REAL, descricao TEXT, 
                data_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                upvotes INTEGER DEFAULT 1, downvotes INTEGER DEFAULT 0)''')

# Tabela de Perfis
conn.execute('''CREATE TABLE IF NOT EXISTS perfis_usuarios (
                email TEXT PRIMARY KEY, nome TEXT, sobrenome TEXT,
                tipo_barco TEXT, nome_barco TEXT, pontos INTEGER DEFAULT 0, nivel TEXT DEFAULT 'Navegante')''')

# NOVA TABELA: Mapeamento Comunitário de Locais (Flutuantes, Marinas)
conn.execute('''CREATE TABLE IF NOT EXISTS locais_comunidade (
                nome TEXT PRIMARY KEY, tipo TEXT, lat REAL, lon REAL, 
                profundidade_est REAL, criador TEXT)''')
conn.commit()
conn.close()

if 'usuario_email' not in st.session_state:
    st.session_state['usuario_email'] = "usuario@ygaranav.com"
    st.session_state['gps_ativo'] = False

# ==========================================
# 1. LAYOUT SUPERIOR E ESTILOS
# ==========================================
st.set_page_config(page_title="Ygara Nav | O Waze dos Rios", layout="wide", page_icon="🚤", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        .stButton>button { border-radius: 12px; font-weight: bold; width: 100%; }
        .swap-btn>button { background-color: #f0f2f6; border-radius: 50%; width: 45px; height: 45px; margin: auto; margin-top: 15px;}
        .gps-btn>button { background-color: #0078FF; color: white; border: none; }
        .sos-btn>button { background-color: #FF3B30; color: white; border: none; }
        .stTabs { margin-top: 0rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS SEMENTE + LOCAIS DA COMUNIDADE
# ==========================================
# Locais base (Ajustados aproximadamente para o Rio Negro)
locais_base = {
    "Marina do David": {"lat": -3.0734, "lon": -60.0336, "tipo": "Marina", "prof": 3.0},
    "Praia da Lua": {"lat": -3.0330, "lon": -60.0520, "tipo": "Praia", "prof": 1.5}, # Praia é raso
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia", "prof": 1.2},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo", "prof": 25.0}, # Muito fundo
    "Orla da Ponta Negra": {"lat": -3.076, "lon": -60.088, "tipo": "Praia/Marina", "prof": 5.0},
    "Porto de Manaus (Centro)": {"lat": -3.139, "lon": -60.023, "tipo": "Porto", "prof": 15.0},
    "Meu Local Atual (GPS)": {"lat": -3.080, "lon": -60.060, "tipo": "GPS", "prof": 10.0} 
}

# Carregar locais criados pela comunidade
conn = sqlite3.connect(banco_path)
df_locais_comunidade = pd.read_sql("SELECT * FROM locais_comunidade", conn)
conn.close()

# Fundir locais base com os da comunidade
locais_dinamicos = locais_base.copy()
for i, row in df_locais_comunidade.iterrows():
    locais_dinamicos[row['nome']] = {"lat": row['lat'], "lon": row['lon'], "tipo": row['tipo'], "prof": row['profundidade_est']}

# ==========================================
# 3. MATRIZ DE EMBARCAÇÕES E CALADO (CASCO)
# ==========================================
dicionario_embarcacoes = {
    "🛶 Canoa / Rabeta": 0.3,
    "🚤 Jet Ski": 0.4,
    "🛥️ Lancha (Até 20 pés)": 0.6,
    "🛥️ Lancha (21 a 40 pés)": 1.0,
    "🛳️ Lancha / Iate (+40 pés)": 1.5,
    "⛴️ Barco Regional (Até 15m)": 1.2,
    "⛴️ Barco Regional (+15m)": 2.2,
    "🚢 Navio Gaiola": 3.0,
    "🚢 Empurrador / Balsa": 4.5
}
tipos_embarcacao = list(dicionario_embarcacoes.keys())

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Porto de Manaus (Centro)"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Praia da Lua"

def inverter_rota():
    st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

# ==========================================
# 4. PAINEL SUPERIOR
# ==========================================
c_logo1, c_logo2, c_logo3 = st.columns([1.5, 1, 1.5])
with c_logo2:
    if os.path.exists(logo_file_path): st.image(logo_file_path, use_container_width=True)
    else: st.markdown("<h3 style='text-align: center;'>🚤 YGARA NAV</h3>", unsafe_allow_html=True)

# Bloco de Roteamento Dinâmico
c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.5, 3, 2])
opcoes_locais = list(locais_dinamicos.keys())

with c_rt1:
    idx_origem = opcoes_locais.index(st.session_state['rota_origem']) if st.session_state['rota_origem'] in opcoes_locais else 0
    st.session_state['rota_origem'] = st.selectbox("Partida", opcoes_locais, index=idx_origem, label_visibility="collapsed")
with c_rt2:
    st.markdown('<div class="swap-btn">', unsafe_allow_html=True)
    if st.button("🔁", on_click=inverter_rota, help="Inverter"): pass
    st.markdown('</div>', unsafe_allow_html=True)
with c_rt3:
    idx_destino = opcoes_locais.index(st.session_state['rota_destino']) if st.session_state['rota_destino'] in opcoes_locais else 1
    st.session_state['rota_destino'] = st.selectbox("Destino", opcoes_locais, index=idx_destino, label_visibility="collapsed")
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

# Painéis Ocultos de Mapeamento e Alertas
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    with st.expander("⚠️ Reportar um Perigo na Água", expanded=False):
        with st.form("form_alerta"):
            tipo_alerta = st.selectbox("O que há na água?", ["🏊‍♂️ Banhistas no Canal", "🪵 Tronco Perigoso", "🏝️ Banco de Areia Oculto", "🎣 Rede de Pesca Armada", "🚓 Fiscalização da Marinha", "⚠️ Barco Enguiçado"])
            local_alerta = st.selectbox("Perto de onde?", opcoes_locais)
            desc_alerta = st.text_input("Detalhe", placeholder="Ex: Canal fechado")
            if st.form_submit_button("📢 Lançar no Mapa", type="primary"):
                lat_a = locais_dinamicos[local_alerta]["lat"] + 0.003; lon_a = locais_dinamicos[local_alerta]["lon"] + 0.003
                conn = sqlite3.connect(banco_path)
                conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, lat_a, lon_a, desc_alerta))
                conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 10 WHERE email = ?", (st.session_state['usuario_email'],))
                conn.commit(); conn.close(); st.success("Alerta criado!")

with col_exp2:
    with st.expander("📍 Adicionar Novo Flutuante/Marina", expanded=False):
        with st.form("form_novo_local"):
            st.write("Catologue o rio para outros navegantes!")
            novo_nome = st.text_input("Nome do Local", placeholder="Ex: Flutuante do Zé")
            novo_tipo = st.selectbox("Categoria", ["🛖 Flutuante", "⚓ Marina", "🏖️ Praia de Água Doce", "🎣 Ponto de Pesca"])
            novo_prof = st.slider("Profundidade Estimada na Seca (metros)", 0.5, 20.0, 3.0)
            # Simulando pegar as coordenadas atuais (Num app real, viria do GPS HTML5)
            st.info("O sistema usará a sua localização de GPS atual para gravar o ponto no mapa.")
            
            if st.form_submit_button("💾 Salvar no Catálogo Público", type="primary"):
                if novo_nome:
                    # Usando uma coordenada fictícia baseada no destino para simular o "Local Atual"
                    lat_n = locais_dinamicos[st.session_state['rota_destino']]["lat"] - 0.01
                    lon_n = locais_dinamicos[st.session_state['rota_destino']]["lon"] - 0.01
                    try:
                        conn = sqlite3.connect(banco_path)
                        conn.execute("INSERT INTO locais_comunidade (nome, tipo, lat, lon, profundidade_est, criador) VALUES (?, ?, ?, ?, ?, ?)", 
                                     (f"{novo_tipo.split(' ')[0]} {novo_nome}", novo_tipo, lat_n, lon_n, novo_prof, st.session_state['usuario_email']))
                        conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 50 WHERE email = ?", (st.session_state['usuario_email'],))
                        conn.commit(); conn.close(); st.success("Local catalogado! Ganhou 50 Pontos."); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este nome já existe no mapa.")

st.markdown("---")

# ==========================================
# 5. ABAS E INTELIGÊNCIA DE ROTA
# ==========================================
tab_mapa, tab_feed, tab_perfil = st.tabs(["🗺️ O Mapa", "💬 Feed da Água", "🚤 Meu Convés"])

# Buscar perfil do usuário para cálculo de segurança
conn = sqlite3.connect(banco_path)
conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', '🚤 Jet Ski', '')", (st.session_state['usuario_email'],))
perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
conn.close()

with tab_mapa:
    # CÁLCULO DE SEGURANÇA (CALADO VS ROTA)
    calado_meu_barco = dicionario_embarcacoes.get(perfil['tipo_barco'], 1.0)
    profundidade_destino = locais_dinamicos[st.session_state['rota_destino']]['prof']
    folga_agua = profundidade_destino - calado_meu_barco

    if folga_agua < 0.5:
        st.error(f"🚨 **RISCO DE ENCALHE SEVERO:** O seu barco ({perfil['tipo_barco']}) exige {calado_meu_barco}m de água. O destino **{st.session_state['rota_destino']}** está raso ({profundidade_destino}m). Reduza a velocidade ou ancore longe da margem!")
    elif folga_agua < 1.5:
        st.warning(f"⚠️ **ATENÇÃO AO CASCO:** A profundidade na área de destino ({profundidade_destino}m) está no limite para o seu barco ({calado_meu_barco}m de calado).")
    else:
        st.success(f"✅ **ROTA SEGURA:** Profundidade adequada no destino ({profundidade_destino}m) para o seu barco ({calado_meu_barco}m de calado). Boa navegação!")

    map_layer = st.radio("Visualização:", ["Satélite Real (Google)", "Náutico Escuro", "Ruas (Padrão Waze)"], horizontal=True, label_visibility="collapsed")
    estilos = {"Satélite Real (Google)": "satellite-streets", "Ruas (Padrão Waze)": "open-street-map", "Náutico Escuro": "carto-darkmatter"}
    
    origem = st.session_state['rota_origem']
    destino = st.session_state['rota_destino']

    lats_rota = [locais_dinamicos[origem]["lat"]]
    lons_rota = [locais_dinamicos[origem]["lon"]]

    if (origem == "Porto de Manaus (Centro)" and "Praia" in destino) or (destino == "Porto de Manaus (Centro)" and "Praia" in origem):
        lats_rota.insert(1, -3.125); lons_rota.insert(1, -60.050)
        lats_rota.insert(2, -3.090); lons_rota.insert(2, -60.080)

    lats_rota.append(locais_dinamicos[destino]["lat"])
    lons_rota.append(locais_dinamicos[destino]["lon"])

    df_rota = pd.DataFrame({'lat': lats_rota, 'lon': lons_rota})
    fig = px.line_mapbox(df_rota, lat="lat", lon="lon", mapbox_style=estilos[map_layer], zoom=11.2, height=550)
    
    cor_linha = "#FF0000" if folga_agua < 0.5 else ("#FFD600" if folga_agua < 1.5 else "#00E5FF")
    fig.update_traces(mode="lines", line=dict(width=7, color=cor_linha)) 

    # Plotar Locais
    for nome, dados in locais_dinamicos.items():
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
                text=[emoji], textposition="middle center", textfont=dict(size=18), hovertext=f"<b>{row['tipo_alerta']}</b><br>{row['descricao']}"
            ))

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_feed:
    st.markdown("### 🗣️ O que está rolando na água")
    if df_alertas.empty:
        st.info("Nenhum alerta reportado hoje.")
    else:
        for idx, row in df_alertas.sort_values(by="id", ascending=False).iterrows():
            with st.container():
                st.markdown(f"#### {row['tipo_alerta']}")
                st.write(f"_{row['descricao']}_ | **Reportado às {row['data_hora'][:16]}**")
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button(f"👍 Vi também ({row['upvotes']})", key=f"up_{row['id']}"):
                        conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET upvotes = upvotes + 1 WHERE id = {row['id']}")
                        conn.commit(); conn.close(); st.rerun()
                with c2:
                    if st.button(f"👎 Já Sumiu ({row['downvotes']})", key=f"dw_{row['id']}"):
                        conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}")
                        conn.commit(); conn.close(); st.rerun()
                st.divider()

with tab_perfil:
    st.markdown("### 🚤 Personalizar Meu Convés")
    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Primeiro Nome", value=perfil['nome'])
        sobrenome_edit = c_p2.text_input("Sobrenome", value=perfil['sobrenome'])
        
        c_p3, c_p4 = st.columns(2)
        tipo_barco_edit = c_p3.selectbox("Qual é a sua Embarcação?", tipos_embarcacao, index=tipos_embarcacao.index(perfil['tipo_barco']) if perfil['tipo_barco'] in tipos_embarcacao else 1)
        nome_barco_edit = c_p4.text_input("Nome de Batismo da Embarcação", value=perfil['nome_barco'])
        
        st.info(f"O seu barco tem um calado físico estimado em **{dicionario_embarcacoes.get(tipo_barco_edit, 1.0)} metros** da linha d'água. Usaremos isto para evitar que encalhe.")
        
        if st.form_submit_button("💾 Atualizar Perfil Público", type="primary"):
            conn = sqlite3.connect(banco_path)
            conn.execute("UPDATE perfis_usuarios SET nome=?, sobrenome=?, tipo_barco=?, nome_barco=? WHERE email=?", (nome_edit, sobrenome_edit, tipo_barco_edit, nome_barco_edit, st.session_state['usuario_email']))
            conn.commit(); conn.close(); st.success("Perfil atualizado! Configurações de barco ajustadas."); st.rerun()

    st.markdown("---")
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("Reputação na Comunidade", f"{perfil['pontos']} Pontos")
    c_m2.metric("Patente Waze", perfil['nivel'])
  
