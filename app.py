import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Dashboard de Performance de Compras", layout="wide")

st.title("📊 Gestão de Indicadores: Compras e Solicitações")
st.markdown("Análise detalhada de volumetria, urgência e performance por solicitante.")

# Função para carregar dados
@st.cache_data
def load_data(file):
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
    df['Fora do Prazo'] = df['Gap Entrega x OC'] > 0
    df['Eh Urgente'] = df['Prazo Solicitado'] <= 1
    
    # Extração de Ano e Mês para filtros
    df['Ano'] = df['Data Solicitação'].dt.year
    df['Mês'] = df['Data Solicitação'].dt.month
    
    return df

# Upload do arquivo
uploaded_file = st.file_uploader("Arraste aqui sua planilha 'solicitações e compras.xlsx'", type=["xlsx", "csv"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    # --- FILTROS LATERAIS ---
    st.sidebar.header("Filtros de Pesquisa")
    
    # 1. Filtro de Ano
    anos_disponiveis = sorted(df['Ano'].dropna().unique().astype(int).tolist(), reverse=True)
    ano_selecionado = st.sidebar.multiselect("Ano", options=anos_disponiveis, default=anos_disponiveis)
    
    # 2. Filtro de Mês
    meses_nomes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 
                   7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
    meses_disponiveis = sorted(df['Mês'].dropna().unique().astype(int).tolist())
    mes_selecionado = st.sidebar.multiselect("Mês", options=meses_disponiveis, 
                                            format_func=lambda x: meses_nomes[x],
                                            default=meses_disponiveis)
    
    # 3. Filtro de Status
    status_list = sorted(df['Status'].dropna().unique().tolist())
    status_filtro = st.sidebar.multiselect("Status", options=status_list, default=status_list)
    
    # 4. Filtro de Solicitante
    solicitante_list = sorted(df['Solicitante'].dropna().unique().tolist())
    solicitante_filtro = st.sidebar.multiselect("Solicitante", options=solicitante_list, default=solicitante_list)
    
    # Aplicação dos Filtros
    mask = (
        (df['Ano'].isin(ano_selecionado)) &
        (df['Mês'].isin(mes_selecionado)) &
        (df['Status'].isin(status_filtro)) & 
        (df['Solicitante'].isin(solicitante_filtro))
    )
    df_filtered = df[mask].copy()

    # --- CÁLCULO DOS INDICADORES GERAIS ---
    total_itens = len(df_filtered)
    itens_com_oc = df_filtered[df_filtered['Data OC'].notna()]
    fora_prazo_qtd = itens_com_oc['Fora do Prazo'].sum()
    perc_fora_prazo = (fora_prazo_qtd / len(itens_com_oc) * 100) if len(itens_com_oc) > 0 else 0
    urgentes_qtd = df_filtered['Eh Urgente'].sum()
    perc_urgentes = (urgentes_qtd / total_itens * 100) if total_itens > 0 else 0

    # Exibição das Métricas
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Itens", total_itens)
    with c2: st.metric("Fora do Prazo", fora_prazo_qtd, f"{perc_fora_prazo:.1f}%", delta_color="inverse")
    with c3: st.metric("Qtd. Urgentes", urgentes_qtd)
    with c4: st.metric("% Urgência", f"{perc_urgentes:.1f}%")

    # --- RANKING DE SOLICITANTES ---
    st.subheader("🏆 Ranking de Solicitantes")
    ranking = df_filtered.groupby('Solicitante').agg(
        Qtd_Itens=('Solicitação', 'count'),
        Urgentes=('Eh Urgente', 'sum'),
        Fora_do_Prazo=('Fora do Prazo', 'sum')
    ).sort_values(by='Qtd_Itens', ascending=False)
    
    ranking['% Urgência'] = (ranking['Urgentes'] / ranking['Qtd_Itens'] * 100).map('{:.1f}%'.format)
    st.table(ranking)

    # --- GRÁFICO DE TENDÊNCIA DE URGÊNCIAS (REINTEGRADO) ---
    st.subheader("📈 Evolução de Pedidos Urgentes")
    df_chart = df_filtered.dropna(subset=['Data Solicitação']).copy()
    if not df_chart.empty:
        try:
            # Usando 'ME' para compatibilidade com Pandas 2.2+
            urgentes_mensal = df_chart.set_index('Data Solicitação')['Eh Urgente'].resample('ME').sum()
            st.area_chart(urgentes_mensal)
        except:
            urgentes_mensal = df_chart.set_index('Data Solicitação')['Eh Urgente'].resample('M').sum()
            st.area_chart(urgentes_mensal)
    else:
        st.warning("Sem dados temporais para gerar o gráfico de urgências.")

    # --- DETALHAMENTO ---
    st.subheader("📑 Análise Detalhada (Lista)")
    
    def style_dataframe(row):
        style = [''] * len(row)
        if row['Eh Urgente']: style = ['background-color: #fff3cd'] * len(row)
        if row['Gap Entrega x OC'] > 0: style = ['background-color: #f8d7da'] * len(row)
        return style

    cols_view = ['Solicitação', 'Solicitante', 'Status', 'Descrição', 'Data Solicitação', 
                 'Data Entrega', 'Data OC', 'Prazo Solicitado', 'Gap Entrega x OC', 'Eh Urgente']
    
    st.dataframe(df_filtered[cols_view].style.apply(style_dataframe, axis=1), use_container_width=True)

else:
    st.info("Aguardando upload da planilha.")
