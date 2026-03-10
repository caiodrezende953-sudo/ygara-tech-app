import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import os
import math

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
conn.commit(); conn.close()

if 'usuario_email' not in st.session_state: st.session_state['usuario_email'] = "usuario@ygaranav.com"
if 'gps_ativo' not in st.session_state: st.session_state['gps_ativo'] = False

# ==========================================
# 1. LAYOUT, FUNDO CINZA E ESTILOS
# ==========================================
st.set_page_config(page_title="Ygara Nav | O Waze dos Rios", layout="wide", page_icon="🚤", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        div[data-testid="stAppViewContainer"] { background-color: #E8ECEF; }
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        header { visibility: hidden !important; height: 0px !important; }
        .stButton>button { border-radius: 12px; font-weight: bold; width: 100%; }
        .swap-btn>button { background-color: #ffffff; border-radius: 50%; width: 45px; height: 45px; margin: auto; margin-top: 15px; border: 1px solid #ccc;}
        .gps-btn>button { background-color: #0078FF; color: white; border: none; }
        .sos-btn>button { background-color: #FF3B30; color: white; border: none; }
        .oficial-footer { background-color: #1E1E1E; color: #E0E0E0; padding: 25px; border-radius: 12px; text-align: center; margin-top: 40px; margin-bottom: 20px; font-family: Arial, sans-serif; box-shadow: 0px 4px 10px rgba(0,0,0,0.2); }
        .oficial-footer h4 { color: #FFFFFF; margin-bottom: 15px; }
        .oficial-footer strong { color: #4CAF50; font-size: 1.1em;}
        .oficial-footer .creditos { font-size: 12px; color: #888; margin-top: 20px; border-top: 1px solid #333; padding-top: 15px;}
        .stTabs { margin-top: 0rem !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOCAIS E MOTOR "TRILHO FLUVIAL"
# ==========================================
locais_base = {
    "Marina do David": {"lat": -3.0734, "lon": -60.0336, "tipo": "Marina", "prof": 3.0},
    "Praia da Lua": {"lat": -3.0330, "lon": -60.0520, "tipo": "Praia", "prof": 1.5},
    "Praia do Tupé": {"lat": -3.033, "lon": -60.254, "tipo": "Praia", "prof": 1.2},
    "Encontro das Águas": {"lat": -3.136, "lon": -59.897, "tipo": "Turismo", "prof": 25.0},
    "Flutuante Sedutor": {"lat": -3.050, "lon": -60.100, "tipo": "Lazer", "prof": 4.0},
    "Orla da Ponta Negra": {"lat": -3.076, "lon": -60.088, "tipo": "Praia/Marina", "prof": 5.0},
    "Porto de Manaus (Centro)": {"lat": -3.139, "lon": -60.023, "tipo": "Porto", "prof": 15.0},
    "Meu Local Atual (GPS)": {"lat": -3.080, "lon": -60.060, "tipo": "GPS", "prof": 10.0} 
}

conn = sqlite3.connect(banco_path)
df_locais = pd.read_sql("SELECT * FROM locais_comunidade", conn)
conn.close()

locais_dinamicos = locais_base.copy()
for i, row in df_locais.iterrows(): locais_dinamicos[row['nome']] = {"lat": row['lat'], "lon": row['lon'], "tipo": row['tipo'], "prof": row['profundidade_est']}

dicionario_embarcacoes = {
    "🛶 Canoa / Rabeta": 0.3, "🚤 Jet Ski": 0.4, "🛥️ Lancha (Até 20 pés)": 0.6,
    "🛥️ Lancha (21 a 40 pés)": 1.0, "🛳️ Lancha / Iate (+40 pés)": 1.5,
    "⛴️ Barco Regional (Até 15m)": 1.2, "⛴️ Barco Regional (+15m)": 2.2,
    "🚢 Navio Gaiola": 3.0, "🚢 Empurrador / Balsa": 4.5
}
tipos_embarcacao = list(dicionario_embarcacoes.keys())

# --- A ESPINHA DORSAL DO RIO NEGRO (MICRO-PONTOS PARA CURVA PERFEITA) ---
# Uma lista densa de pontos que desenham o formato exato da calha do rio de Leste a Oeste
trilha_rio_negro = [
    {"lat": -3.136, "lon": -59.897}, # Encontro das Águas
    {"lat": -3.139, "lon": -60.023}, # Centro
    {"lat": -3.135, "lon": -60.030}, # Curva Educandos
    {"lat": -3.125, "lon": -60.038}, # Subindo Ponte
    {"lat": -3.115, "lon": -60.045}, # Ponte Rio Negro
    {"lat": -3.100, "lon": -60.060}, # Compensa
    {"lat": -3.085, "lon": -60.075}, # Aproximação Ponta Negra
    {"lat": -3.076, "lon": -60.088}, # Orla Ponta Negra
    {"lat": -3.065, "lon": -60.120}, # Meio do Rio Tarumã
    {"lat": -3.045, "lon": -60.180}, # Curva Praia da Lua
    {"lat": -3.033, "lon": -60.254}  # Tupé
]

def obter_rota_curvada(lat1, lon1, lat2, lon2):
    # Algoritmo de engate: Procura quais pontos da "trilha" estão entre a origem e o destino para fazer a curva
    lon_min, lon_max = min(lon1, lon2), max(lon1, lon2)
    pontos_curva = [{"lat": lat1, "lon": lon1}]
    
    # Filtra os pontos do rio que estão geograficamente entre a origem e o destino
    meio_do_caminho = [p for p in trilha_rio_negro if lon_min < p["lon"] < lon_max]
    
    # Se a viagem for no sentido Oeste -> Leste, inverte a ordem dos pontos do rio
    if lon1 > lon2: 
        meio_do_caminho.reverse()
        
    pontos_curva.extend(meio_do_caminho)
    pontos_curva.append({"lat": lat2, "lon": lon2})
    return pd.DataFrame(pontos_curva)

if 'rota_origem' not in st.session_state: st.session_state['rota_origem'] = "Marina do David"
if 'rota_destino' not in st.session_state: st.session_state['rota_destino'] = "Porto de Manaus (Centro)"
def inverter_rota(): st.session_state['rota_origem'], st.session_state['rota_destino'] = st.session_state['rota_destino'], st.session_state['rota_origem']

# ==========================================
# 3. PAINEL SUPERIOR
# ==========================================
c_logo1, c_logo2, c_logo3 = st.columns([1.5, 1, 1.5])
with c_logo2:
    if os.path.exists(logo_file_path): st.image(logo_file_path, use_container_width=True)
    else: st.markdown("<h3 style='text-align: center; color: #333;'>🚤 YGARA NAV</h3>", unsafe_allow_html=True)

c_rt1, c_rt2, c_rt3, c_rt4 = st.columns([3, 0.5, 3, 2])
opcoes_locais = list(locais_dinamicos.keys())

with c_rt1:
    idx_ori = opcoes_locais.index(st.session_state['rota_origem']) if st.session_state['rota_origem'] in opcoes_locais else 0
    st.session_state['rota_origem'] = st.selectbox("Partida", opcoes_locais, index=idx_ori, label_visibility="collapsed")
with c_rt2:
    st.markdown('<div class="swap-btn">', unsafe_allow_html=True); st.button("🔁", on_click=inverter_rota); st.markdown('</div>', unsafe_allow_html=True)
with c_rt3:
    idx_des = opcoes_locais.index(st.session_state['rota_destino']) if st.session_state['rota_destino'] in opcoes_locais else 1
    st.session_state['rota_destino'] = st.selectbox("Destino", opcoes_locais, index=idx_des, label_visibility="collapsed")
with c_rt4:
    c_gps, c_sos = st.columns(2)
    with c_gps:
        st.markdown('<div class="gps-btn">', unsafe_allow_html=True); 
        if st.button("📡 GPS"): st.session_state['gps_ativo'] = True; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c_sos:
        st.markdown('<div class="sos-btn">', unsafe_allow_html=True); 
        if st.button("🆘 SOS"): st.error("Sinal emitido!")
        st.markdown('</div>', unsafe_allow_html=True)

col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    with st.expander("⚠️ Reportar Perigo", expanded=False):
        with st.form("form_alerta"):
            tipo_alerta = st.selectbox("O que há na água?", ["🏊‍♂️ Banhistas", "🪵 Tronco Perigoso", "🏝️ Banco de Areia", "🎣 Rede de Pesca", "🚓 Fiscalização", "⚠️ Barco Enguiçado"])
            local_alerta = st.selectbox("Perto de onde?", opcoes_locais)
            desc_alerta = st.text_input("Detalhe")
            if st.form_submit_button("📢 Lançar no Mapa", type="primary"):
                conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO alertas_waze (usuario, tipo_alerta, lat, lon, descricao) VALUES (?, ?, ?, ?, ?)", (st.session_state['usuario_email'], tipo_alerta, locais_dinamicos[local_alerta]["lat"] + 0.003, locais_dinamicos[local_alerta]["lon"] + 0.003, desc_alerta)); conn.commit(); conn.close(); st.success("Alerta criado!")

with col_exp2:
    with st.expander("📍 Adicionar Novo Local", expanded=False):
        with st.form("form_novo_local"):
            novo_nome = st.text_input("Nome do Local"); novo_tipo = st.selectbox("Categoria", ["🛖 Flutuante", "⚓ Marina", "🏖️ Praia", "🎣 Pesca"]); novo_prof = st.slider("Profundidade (m)", 0.5, 20.0, 3.0)
            if st.form_submit_button("💾 Catalogar", type="primary"):
                if novo_nome:
                    try:
                        conn = sqlite3.connect(banco_path); conn.execute("INSERT INTO locais_comunidade (nome, tipo, lat, lon, profundidade_est, criador) VALUES (?, ?, ?, ?, ?, ?)", (f"{novo_tipo.split(' ')[0]} {novo_nome}", novo_tipo, locais_dinamicos[st.session_state['rota_destino']]["lat"] - 0.01, locais_dinamicos[st.session_state['rota_destino']]["lon"] - 0.01, novo_prof, st.session_state['usuario_email'])); conn.commit(); conn.close(); st.success("Catalogado!"); st.rerun()
                    except: st.error("Já existe.")

# ==========================================
# 4. ABAS DE NAVEGAÇÃO E MAPA DE ALTA DEFINIÇÃO
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
tab_mapa, tab_feed, tab_perfil = st.tabs(["🗺️ O Mapa", "💬 Feed da Água", "🚤 Meu Convés"])

conn = sqlite3.connect(banco_path)
conn.execute("INSERT OR IGNORE INTO perfis_usuarios (email, nome, sobrenome, tipo_barco, nome_barco) VALUES (?, '', '', '🚤 Jet Ski', '')", (st.session_state['usuario_email'],))
perfil = pd.read_sql(f"SELECT * FROM perfis_usuarios WHERE email = '{st.session_state['usuario_email']}'", conn).iloc[0]
conn.close()

with tab_mapa:
    calado_meu_barco = dicionario_embarcacoes.get(perfil['tipo_barco'], 1.0)
    prof_destino = locais_dinamicos[st.session_state['rota_destino']]['prof']
    folga_agua = prof_destino - calado_meu_barco

    if folga_agua < 0.5: st.error(f"🚨 **RISCO DE ENCALHE SEVERO:** Destino ({prof_destino}m) muito raso para o seu barco ({calado_meu_barco}m calado).")
    elif folga_agua < 1.5: st.warning(f"⚠️ **ATENÇÃO AO CASCO:** Profundidade limite ({prof_destino}m) para o seu barco ({calado_meu_barco}m).")
    else: st.success(f"✅ **ROTA SEGURA:** Profundidade adequada no destino ({prof_destino}m).")

    map_layer = st.radio("Visualização:", ["Satélite (Alta Definição Esri)", "Ruas (Padrão Waze)", "Náutico Escuro"], horizontal=True, label_visibility="collapsed")
    
    origem = st.session_state['rota_origem']
    destino = st.session_state['rota_destino']

    # Usa o novo algoritmo de curva para criar o DataFrame da rota
    df_rota_curva = obter_rota_curvada(locais_dinamicos[origem]["lat"], locais_dinamicos[origem]["lon"], locais_dinamicos[destino]["lat"], locais_dinamicos[destino]["lon"])
    
    fig = px.line_mapbox(df_rota_curva, lat="lat", lon="lon", zoom=11.2, height=580)
    cor_linha = "#FF0000" if folga_agua < 0.5 else ("#FFD600" if folga_agua < 1.5 else "#00E5FF")
    fig.update_traces(mode="lines+markers", line=dict(width=6, color=cor_linha), marker=dict(size=6, color="white")) 

    # --- O SEGREDO DO SATÉLITE QUE NÃO SOME ---
    if map_layer == "Satélite (Alta Definição Esri)":
        fig.update_layout(
            mapbox_style="white-bg",
            mapbox_layers=[{
                "below": 'traces', "sourcetype": "raster", "sourceattribution": "Esri World Imagery",
                "source": ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"]
            }]
        )
    elif map_layer == "Náutico Escuro": fig.update_layout(mapbox_style="carto-darkmatter")
    else: fig.update_layout(mapbox_style="open-street-map")

    # Plotar Locais
    for nome, dados in locais_dinamicos.items():
        if nome != "Meu Local Atual (GPS)":
            fig.add_trace(go.Scattermapbox(lat=[dados['lat']], lon=[dados['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=14, color="white", symbol="circle"), text=[nome], textposition="bottom center", textfont=dict(color="white", size=13), hoverinfo="text", name=dados['tipo']))

    # Plotar Alertas
    conn = sqlite3.connect(banco_path); df_alertas = pd.read_sql("SELECT * FROM alertas_waze", conn); conn.close()
    if not df_alertas.empty:
        df_confiaveis = df_alertas[df_alertas['upvotes'] >= df_alertas['downvotes']]
        for i, row in df_confiaveis.iterrows():
            emoji = row['tipo_alerta'].split(" ")[0]
            fig.add_trace(go.Scattermapbox(lat=[row['lat']], lon=[row['lon']], mode='markers+text', marker=go.scattermapbox.Marker(size=30, color="rgba(255, 60, 0, 0.9)"), text=[emoji], textposition="middle center", textfont=dict(size=18), hovertext=f"<b>{row['tipo_alerta']}</b><br>{row['descricao']}"))

    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_feed:
    st.markdown("### 🗣️ O que está rolando na água")
    if df_alertas.empty: st.info("Nenhum alerta reportado hoje.")
    else:
        for idx, row in df_alertas.sort_values(by="id", ascending=False).iterrows():
            with st.container():
                st.markdown(f"#### {row['tipo_alerta']}")
                st.write(f"_{row['descricao']}_ | **Reportado às {row['data_hora'][:16]}**")
                c1, c2, c3 = st.columns([1, 1, 4])
                with c1:
                    if st.button(f"👍 Vi também ({row['upvotes']})", key=f"up_{row['id']}"): conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET upvotes = upvotes + 1 WHERE id = {row['id']}"); conn.commit(); conn.close(); st.rerun()
                with c2:
                    if st.button(f"👎 Já Sumiu ({row['downvotes']})", key=f"dw_{row['id']}"): conn = sqlite3.connect(banco_path); conn.execute(f"UPDATE alertas_waze SET downvotes = downvotes + 1 WHERE id = {row['id']}"); conn.commit(); conn.close(); st.rerun()
                st.divider()

with tab_perfil:
    st.markdown("### 🚤 Personalizar Meu Convés")
    with st.form("form_perfil"):
        c_p1, c_p2 = st.columns(2)
        nome_edit = c_p1.text_input("Primeiro Nome", value=perfil['nome'])
        sobrenome_edit = c_p2.text_input("Sobrenome", value=perfil['sobrenome'])
        c_p3, c_p4 = st.columns(2)
        tipo_barco_edit = c_p3.selectbox("Sua Embarcação", tipos_embarcacao, index=tipos_embarcacao.index(perfil['tipo_barco']) if perfil['tipo_barco'] in tipos_embarcacao else 1)
        nome_barco_edit = c_p4.text_input("Nome de Batismo", value=perfil['nome_barco'])
        
        if st.form_submit_button("💾 Atualizar Perfil", type="primary"):
            conn = sqlite3.connect(banco_path); conn.execute("UPDATE perfis_usuarios SET nome=?, sobrenome=?, tipo_barco=?, nome_barco=? WHERE email=?", (nome_edit, sobrenome_edit, tipo_barco_edit, nome_barco_edit, st.session_state['usuario_email'])); conn.commit(); conn.close(); st.success("Perfil atualizado!"); st.rerun()

    st.markdown("---")
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("Karma da Comunidade", f"{perfil['pontos']} Pontos")
    c_m2.metric("Nível", perfil['nivel'])

# ==========================================
# 6. RODAPÉ INSTITUCIONAL OFICIAL (CORRIGIDO)
# ==========================================
st.markdown("""
    <div class="oficial-footer">
        <h4>📞 Contatos de Emergência</h4>
        <p>
            🚔 Polícia Militar: <strong>190</strong> &nbsp;&nbsp;|&nbsp;&nbsp; 
            🚑 SAMU: <strong>192</strong> &nbsp;&nbsp;|&nbsp;&nbsp; 
            🚒 Bombeiros: <strong>193</strong>
        </p>
        <p>⚓ Capitania Fluvial da Amazônia Ocidental: <strong>185</strong> ou (92) 2123-2222</p>
        <div class="creditos">
            <strong>Ygara Nav - O Waze dos Rios</strong> &copy; 2026<br>
            Mapeamento colaborativo e segurança fluvial baseada em IA.<br>
            Desenvolvido por Caio Rezende | Manaus, Amazonas.
        </div>
    </div>
""", unsafe_allow_html=True)
