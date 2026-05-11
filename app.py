import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Dashboard de Performance de Compras", layout="wide")

st.title("📊 Indicadores de Solicitações e Compras")
st.markdown("Análise de volumetria, prazos de entrega e compras urgentes por solicitante.")

# Função para carregar dados
@st.cache_data
def load_data(file):
    # Lendo a planilha (CSV ou Excel)
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    # Conversão de colunas para datetime
    date_cols = ['Data Solicitação', 'Data Entrega', 'Data OC']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # --- CÁLCULOS DE PRAZOS ---
    
    # 1. Prazo Solicitado (Dias entre Solicitação e Entrega Desejada)
    df['Prazo Solicitado'] = (df['Data Entrega'] - df['Data Solicitação']).dt.days
    
    # 2. Dias para Compra (Data Solicitação até Data OC)
    df['Dias Solicitação x OC'] = (df['Data OC'] - df['Data Solicitação']).dt.days
    
    # 3. Gap de Atraso (OC gerada após a Data de Entrega desejada)
    df['Gap Entrega x OC'] = (df['Data OC'] - df['Data Entrega']).dt.days
    
    # --- REGRAS DE NEGÓCIO ---
    
    # Identifica se foi comprado fora do prazo (OC após Data Entrega)
    df['Fora do Prazo'] = df['Gap Entrega x OC'] > 0
    
    # Identifica Compras Urgentes (Prazo Solicitado <= 1 dia)
    df['Eh Urgente'] = df['Prazo Solicitado'] <= 1
    
    return df

# Upload do arquivo
uploaded_file = st.file_uploader("Arraste aqui sua planilha 'solicitações e compras.xlsx'", type=["xlsx", "csv"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    # --- FILTROS LATERAIS ---
    st.sidebar.header("Filtros de Pesquisa")
    
    # Filtro de Status
    status_list = sorted(df['Status'].dropna().unique().tolist())
    status_filtro = st.sidebar.multiselect("Filtrar por Status", options=status_list, default=status_list)
    
    # NOVO: Filtro de Solicitante
    # Removemos nulos e ordenamos para facilitar a busca
    solicitante_list = sorted(df['Solicitante'].dropna().unique().tolist())
    solicitante_filtro = st.sidebar.multiselect("Filtrar por Solicitante", options=solicitante_list, default=solicitante_list)
    
    # Aplicação dos Filtros Cruzados
    df_filtered = df[
        (df['Status'].isin(status_filtro)) & 
        (df['Solicitante'].isin(solicitante_filtro))
    ].copy()

    # --- CÁLCULO DOS INDICADORES ---
    total_itens = len(df_filtered)
    
    # 1. Fora do Prazo (Considerando apenas itens com OC emitida)
    itens_com_oc = df_filtered[df_filtered['Data OC'].notna()]
    total_com_oc = len(itens_com_oc)
    fora_prazo_qtd = itens_com_oc['Fora do Prazo'].sum()
    perc_fora_prazo = (fora_prazo_qtd / total_com_oc * 100) if total_com_oc > 0 else 0
    
    # 2. Urgentes (Prazo solicitado <= 1 dia)
    urgentes_qtd = df_filtered['Eh Urgente'].sum()
    perc_urgentes = (urgentes_qtd / total_itens * 100) if total_itens > 0 else 0

    # --- EXIBIÇÃO DAS MÉTRICAS ---
    st.subheader("Indicadores de Eficiência e Urgência")
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Total de Itens", f"{total_itens}")
        st.caption("Volume na seleção atual")

    with c2:
        st.metric("Compras Fora do Prazo", f"{fora_prazo_qtd}", f"{perc_fora_prazo:.1f}%", delta_color="inverse")
        st.caption("OC emitida após Data Entrega")

    with c3:
        st.metric("Qtd. Compras Urgentes", f"{urgentes_qtd}")
        st.caption("Prazo solicitado ≤ 1 dia")

    with c4:
        st.metric("% Urgência", f"{perc_urgentes:.1f}%")
        st.caption("Impacto de pedidos imediatos")

    # --- DETALHAMENTO ---
    st.subheader("Análise Detalhada")
    
    # Função para destacar Urgências e Atrasos
    def style_dataframe(row):
        style = [''] * len(row)
        if row['Eh Urgente']:
            style = ['background-color: #fff3cd'] * len(row) # Amarelo para urgente
        if row['Gap Entrega x OC'] > 0:
            style = ['background-color: #f8d7da'] * len(row) # Vermelho para atraso
        return style

    cols_view = ['Solicitação', 'Solicitante', 'Status', 'Descrição', 'Data Solicitação', 'Data Entrega', 
                 'Data OC', 'Prazo Solicitado', 'Gap Entrega x OC', 'Eh Urgente']
    
    st.dataframe(
        df_filtered[cols_view].style.apply(style_dataframe, axis=1),
        use_container_width=True
    )

    # --- GRÁFICO DE TENDÊNCIA ---
    st.subheader("Evolução de Pedidos Urgentes por Mês")
    df_chart = df_filtered.dropna(subset=['Data Solicitação']).copy()
    if not df_chart.empty:
        try:
            # Agrupando por mês (frequência ME para versões novas do pandas)
            urgentes_mensal = df_chart.set_index('Data Solicitação')['Eh Urgente'].resample('ME').sum()
            st.area_chart(urgentes_mensal)
        except:
            urgentes_mensal = df_chart.set_index('Data Solicitação')['Eh Urgente'].resample('M').sum()
            st.area_chart(urgentes_mensal)
    else:
        st.warning("Sem dados temporais para o filtro selecionado.")

else:
    st.info("Aguardando upload da planilha.")
