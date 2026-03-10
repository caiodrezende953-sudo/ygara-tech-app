import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os

# ==========================================
# 0. SETUP DE BANCO DE DADOS (PRODUÇÃO V1)
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

# ==========================================
# 1. NOVO DESIGN: TEMA DARK, NOVA FONTE E LOGO DISCRETA
# ==========================================
st.set_page_config(page_title="Ygara Nav", layout="wide", page_icon="🧭", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Importar fonte moderna 'Inter' do Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
        
        /* Tema Cinza Escuro e Mapa em Evidência */
        div[data-testid="stAppViewContainer"] { background-color: #1A1C23; color: #E0E0E0; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        
        /* Estilização Premium dos Botões */
        .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; transition: 0.3s; }
        .swap-btn>button { background-color: #2D303E; color: #00E5FF; border-radius: 50%; width: 45px; height: 45px; margin: auto; border: 1px solid #444;}
        .gps-btn>button { background-color: #00E5FF; color: #121212; border: none; font-weight: 800; }
        .sos-btn>button { background-color: #FF3B30; color: white; border: none; font-weight: 800; }
        .start-nav-btn>button { background-color: #00E5FF; color: #1A1C23; border-radius: 12px; height: 50px; font-size: 18px; border: none; font-weight: 800; }
        .stop-nav-btn>button { background-color: #FF3B30; color: white; border-radius: 12px; height: 50px; font-size: 18px; border: none; font-weight: 800; }
        
        /* Design das Abas (Tabs) */
        .stTabs [data-baseweb="tab-list"] { background-color: #252836; border-radius: 12px; padding: 5px; gap: 10px; }
        .stTabs [data-baseweb="tab"] { color: #8F92A1; border-radius: 8px; padding: 10px 20px; font-size: 16px; font-weight: 600; }
        .stTabs [aria-selected="true"] { background-color: #00E5FF !important; color: #1A1C23 !important; }
        
        /* Ajuste do Título da Logo */
        .top-brand { display: flex; align-items: center; margin-bottom: 20px; }
        .top-brand h2 { margin: 0; padding-left: 15px; color: #00E5FF; font-weight: 800; letter-spacing: 1px;}
    </style>
""", unsafe_allow_html=True)

# CABEÇALHO: LOGO PEQUENA NO CANTO ESQUERDO
col_logo, col_vazia = st.columns([1, 10])
with col_logo:
    if os.path.exists(logo_file_path): st.image(logo_file_path, width=70) # Logo reduzida
with col_vazia:
    st.markdown("<div class='top-brand'><h2>YGARA NAV</h2></div>", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS E ALGORITMO DE CURVA
# ==========================================
locais_base = {
    "Marina do David": {"lat": -3.0734, "lon": -60.0336, "tipo": "Marina", "prof": 3.0},
    "Praia da Lua": {"lat": -3.0330, "lon": -60.0520, "tipo": "Praia", "prof": 1.5},
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia", "prof": 1.2},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo", "prof": 25.0},
    "Flutuante Sedutor": {"lat": -3.050, "lon": -60.100, "tipo": "Lazer", "prof": 4.0},
    "Orla da Ponta Negra": {"lat": -3.076, "lon": -60.088, "tipo": "Praia/Marina", "prof": 5.0},
    "Porto de Manaus (Centro)": {"lat": -3.139, "lon": -60.023, "tipo": "Porto", "prof": 15.0}
}
conn = sqlite3.connect(banco_path); df_locais = pd.read_sql("SELECT * FROM locais_comunidade", conn); conn.close()
locais_dinamicos = locais_base.copy()
for i, row in df_locais.iterrows(): locais_dinamicos[row['nome']] = {"lat": row['lat'], "lon": row['lon'], "tipo": row['tipo'], "prof": row['profundidade_est']}

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
        for step in range(10):
            f = step / 10.0; rota_suave.append({"lat": p1["lat"] + (p2["lat"] - p1["lat"]) * f, "lon": p1["lon"] + (p2["lon"] - p1["lon"]) * f})
    rota_suave.append(pontos_curva[-1])
    return pd.DataFrame(rota_suave)

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Marina do David"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Porto de Manaus (Centro)"
def inverter_rota(): st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

conn = sqlite3.connect(banco_path)
conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', '🚤 Jet Ski', '')", (st.session_state['usuario_email'],))
perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
conn.close()
dicionario_embarcacoes = {"🛶 Canoa / Rabeta": 0.3, "🚤 Jet Ski": 0.4, "🛥️ Lancha (Até 20 pés)": 0.6, "🛥️ Lancha (21 a 40 pés)": 1.0, "🛳️ Lancha / Iate (+40 pés)": 1.5, "⛴️ Barco Regional (Até 15m)": 1.2, "⛴️ Barco Regional (+15m)": 2.2, "🚢 Navio Gaiola": 3.0, "🚢 Empurrador / Balsa": 4.5}

df_rota_ativa = obter_rota_curvada(locais_dinamicos[st.session_state['rota_origem']]["lat"], locais_dinamicos[st.session_state['rota_origem']]["lon"], locais_dinamicos[st.session_state['rota_destino']]["lat"], locais_dinamicos[st.session_state['rota_destino']]["lon"])

# ==========================================
# 3. ORGANIZAÇÃO EM ABAS (UI LIMPA)
# ==========================================
tab_rotas, tab_alertas, tab_perfil = st.tabs(["🗺️ Navegação & Mapa", "⚠️ Central de Alertas", "👤 Meu Perfil"])

# -------------------------------------------------------------------------
# ABA 1: MAPA E NAVEGAÇÃO EM EVIDÊNCIA
# -------------------------------------------------------------------------
with tab_rotas:
    if st.session_state['navegando']:
        # MODO DIREÇÃO ATIVO
        c_nav1, c_nav2 = st.columns([3, 1])
        c_nav1.success(f"📍 Navegando para: **{st.session_state['rota_destino']}**")
        with c_nav2:
            st.markdown('<div class="stop-nav-btn">', unsafe_allow_html=True); 
            if st.button("⏹ Encerrar Rota"): st.session_state['navegando'] = False; st.session_state['gps_progresso'] = 0; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        progresso = st.slider("Simulador de Movimento GPS", 0, len(df_rota_ativa)-1, st.session_state['gps_progresso'], label_visibility="collapsed")
        if progresso != st.session_state['gps_progresso']:
            st.session_state['gps_progresso'] = progresso
            conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO historico_rotas (email, tipo_barco, lat, lon) VALUES (?, ?, ?, ?)", (st.session_state['usuario_email'], perfil['tipo_barco'], float(df_rota_ativa.iloc[progresso]['lat']), float(df_rota_ativa.iloc[progresso]['lon']))); conn.commit(); conn.close()
        
        lat_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lat']
        lon_barco = df_rota_ativa.iloc[st.session_state['gps_progresso']]['lon']

        fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", mapbox_style="satellite-streets", zoom=14.5, height=700) # MAPA GIGANTE
        fig.update_traces(mode="lines", line=dict(width=8, color="#00E5FF")) 
        fig.add_trace(go.Scattermapbox(lat=[lat_barco], lon=[lon_barco], mode='markers+text', marker=go.scattermapbox.Marker(size=25, color="#00E5FF", symbol="circle"), text=["🛥️ VOCÊ"], textposition="top center", textfont=dict(color="white", size=18, family="Inter"), hoverinfo="none"))
        fig.update_layout(mapbox=dict(center=dict(lat=lat_barco, lon=lon_barco), zoom=14), mapbox_style="white-bg", mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri World Imagery", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}], margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    else:
        # MODO PLANEJAMENTO (CONTROLES SOBRE O MAPA)
        c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.5, 3, 2])
        opcoes_locais = list(locais_dinamicos.keys())
        with c_rt1:
            idx_ori = opcoes_locais.index(st.session_state['rota_origem']) if st.session_state['rota_origem'] in opcoes_locais else 0
            st.session_state['rota_origem'] = st.selectbox("Partida", opcoes_locais, index=idx_ori)
        with c_rt2:
            st.markdown('<br><div class="swap-btn">', unsafe_allow_html=True); st.button("🔁", on_click=inverter_rota); st.markdown('</div>', unsafe_allow_html=True)
        with c_rt3:
            idx_des = opcoes_locais.index(st.session_state['rota_destino']) if st.session_state['rota_destino'] in opcoes_locais else 1
            st.session_state['rota_destino'] = st.selectbox("Destino", opcoes_locais, index=idx_des)
        with c_rt4:
            st.markdown('<br><div class="start-nav-btn">', unsafe_allow_html=True); 
            if st.button("▶ INICIAR NAVEGAÇÃO", use_container_width=True): st.session_state['navegando'] = True; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Checagem de Segurança
        calado_meu_barco = dicionario_embarcacoes.get(perfil['tipo_barco'], 1.0)
        prof_destino = locais_dinamicos[st.session_state['rota_destino']]['prof']
        folga_agua = prof_destino - calado_meu_barco
        if folga_agua < 0.5: st.error(f"🚨 RISCO DE ENCALHE: O destino é raso ({prof_destino}m) para o seu {perfil['tipo_barco']}.")
        
        map_layer = st.radio("Camada do Mapa:", ["Satélite (Esri)", "Náutico Escuro (Carto)"], horizontal=True)
        
        fig = px.line_mapbox(df_rota_ativa, lat="lat", lon="lon", zoom=11.2, height=650) # MAPA GIGANTE
        cor_linha = "#FF3B30" if folga_agua < 0.5 else ("#FFD600" if folga_agua < 1.5 else "#00E5FF")
        fig.update_traces(mode="lines", line=dict(width=6, color=cor_linha)) 

        if map_layer == "Satélite (Esri)": fig.update_layout(mapbox_style="white-bg", mapbox_layers=[{"below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri World Imagery", "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]}])
        else: fig.update_layout(mapbox_style="carto-darkmatter")

        for nome, dados in locais_dinamicos.items():
            fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="#FAFAFA", symbol="circle"), text=[nome], textposition="bottom center", textfont=dict(color="#FAFAFA", size=13), hoverinfo="text", name=dados['tipo']))

        conn = sqlite3.connect(banco_path); df_alertas = pd.read_sql("SELECT * FROM alertas_waze", conn); conn.close()
        if not df_alertas.empty:
            df_confiaveis = df_alertas[df_alertas['upvotes'] >= df_alertas['downvotes']]
            for i, row in df_confiaveis.iterrows():
                emoji = row['tipo_alerta'].split(" ")[0]
                fig.add_trace(go.Scattermapbox(lat=[row['lat']], lon=[row['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=30, color="rgba(255, 59, 48, 0.9)"), text=[emoji], textposition="middle center", textfont=dict(size=18), hovertext=f"<b>{row['tipo_alerta']}</b><br>{row['descricao']}"))

        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------------------
# ABA 2: ALERTAS E COMUNIDADE
# -------------------------------------------------------------------------
with tab_alertas:
    st.markdown("### ⚠️ Reportar Perigo no Mapa")
    with st.form("form_alerta"):
        c_f1, c_f2, c_f3 = st.columns([2, 2, 3])
        tipo_alerta = c_f1.selectbox("O que há na água?", ["🏊‍♂️ Banhistas", "🪵 Tronco Perigoso", "🏝️ Banco de Areia", "🎣 Rede de Pesca", "🚓 Fiscalização", "⚠️ Barco Enguiçado"])
        local_alerta = c_f2.selectbox("Perto de onde?", opcoes_locais)
        desc_alerta = c_f3.text_input("Detalhe", placeholder="Ex: Canal direito bloqueado")
        if st.form_submit_button("📢 Lançar no Mapa", type="primary"):
            conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, locais_dinamicos[local_alerta]["lat"] + 0.003, locais_dinamicos[local_alerta]["lon"] + 0.003, desc_alerta)); conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 10 WHERE email = ?", (st.session_state['usuario_email'],)); conn.commit(); conn.close(); st.success("Alerta criado com sucesso!")

    st.markdown("---")
    st.markdown("### 🗣️ Feed da Água (Eventos Recentes)")
    if df_alertas.empty: st.info("O rio está limpo no momento.")
    else:
        for idx, row in df_alertas.sort_values(by="id", ascending=False).iterrows():
            with st.container():
                st.markdown(f"**{row['tipo_alerta']}** | <span style='color:#8F92A1; font-size:14px;'>{row['data_hora'][:16]}</span>", unsafe_allow_html=True)
                st.write(f"_{row['descricao']}_")
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button(f"👍 Confirmar ({row['upvotes']})", key=f"up_{row['id']}"): conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET upvotes = upvotes + 1 WHERE id = {row['id']}"); conn.commit(); conn.close(); st.rerun()
                with c2:
                    if st.button(f"👎 Já Sumiu ({row['downvotes']})", key=f"dw_{row['id']}"): conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}"); conn.commit(); conn.close(); st.rerun()
                st.markdown("<hr style='border: 1px solid #252836;'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# ABA 3: PERFIL E CATALOGAÇÃO
# -------------------------------------------------------------------------
with tab_perfil:
    c_pcol1, c_pcol2 = st.columns(2)
    
    with c_pcol1:
        st.markdown("### 👤 Seus Dados e Embarcação")
        with st.form("form_perfil"):
            nome_edit = st.text_input("Nome", value=perfil['nome'])
            tipo_barco_edit = st.selectbox("Sua Embarcação", list(dicionario_embarcacoes.keys()), index=list(dicionario_embarcacoes.keys()).index(perfil['tipo_barco']) if perfil['tipo_barco'] in dicionario_embarcacoes else 1)
            nome_barco_edit = st.text_input("Nome de Batismo da Embarcação", value=perfil['nome_barco'])
            st.info(f"Seu calado estimado: **{dicionario_embarcacoes.get(tipo_barco_edit, 1.0)}m**.")
            if st.form_submit_button("💾 Salvar Perfil", type="primary"):
                conn = sqlite3.connect(banco_path); conn.execute("UPDATE perfis_usuarios SET nome=?, tipo_barco=?, nome_barco=? WHERE email=?", (nome_edit, tipo_barco_edit, nome_barco_edit, st.session_state['usuario_email'])); conn.commit(); conn.close(); st.success("Atualizado!"); st.rerun()
        
        st.markdown(f"**Reputação:** {perfil['pontos']} pts | **Patente:** {perfil['nivel']}")

    with c_pcol2:
        st.markdown("### 📍 Adicionar Local ao Mapa")
        st.write("Conhece uma Marina ou Praia nova? Adicione para todos!")
        with st.form("form_novo_local"):
            novo_nome = st.text_input("Nome do Local"); novo_tipo = st.selectbox("Categoria", ["🛖 Flutuante", "⚓ Marina", "🏖️ Praia", "🎣 Pesca"]); novo_prof = st.slider("Profundidade Estimada (m)", 0.5, 20.0, 3.0)
            if st.form_submit_button("💾 Enviar para Catálogo Público", type="primary"):
                if novo_nome:
                    try:
                        conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO locais_comunidade (nome, tipo, lat, lon, profundidade_est, criador) VALUES (?, ?, ?, ?, ?, ?)", (f"{novo_tipo.split(' ')[0]} {novo_nome}", novo_tipo, locais_dinamicos[st.session_state['rota_destino']]["lat"] - 0.01, locais_dinamicos[st.session_state['rota_destino']]["lon"] - 0.01, novo_prof, st.session_state['usuario_email'])); conn.execute("UPDATE perfis_usuarios SET pontos = pontos + 50 WHERE email = ?", (st.session_state['usuario_email'],)); conn.commit(); conn.close(); st.success("Catalogado! +50 pts"); st.rerun()
                    except: st.error("Este nome já existe.")
                        
