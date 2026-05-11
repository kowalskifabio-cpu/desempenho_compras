import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras e Solicitações", layout="wide")

st.title("📊 Indicadores de Solicitações e Compras")
st.markdown("Análise de prazos entre Solicitação, Entrega Desejada e Compra (OC).")

# Função para carregar dados
@st.cache_data
def load_data(file):
    # Lendo a planilha (ajustar o nome da aba se necessário)
    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    
    # Conversão de colunas para datetime
    date_cols = ['Data Solicitação', 'Data Entrega', 'Data OC']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Cálculos de Dias (Lead Time)
    # 1. Dias entre Solicitação e Entrega Desejada (Prazo solicitado pelo usuário)
    df['Dias Solicitação x Entrega'] = (df['Data Entrega'] - df['Data Solicitação']).dt.days
    
    # 2. Dias entre Solicitação e Compra Efetiva (Tempo de processamento de compras)
    df['Dias Solicitação x OC'] = (df['Data OC'] - df['Data Solicitação']).dt.days
    
    # 3. Diferença entre Entrega Desejada e Data da OC (Atraso na formalização da compra)
    df['Gap Entrega x OC'] = (df['Data OC'] - df['Data Entrega']).dt.days
    
    return df

# Upload do arquivo
uploaded_file = st.file_uploader("Arraste aqui sua planilha 'solicitações e compras.xlsx'", type=["xlsx", "csv"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    # Filtros laterais
    st.sidebar.header("Filtros")
    status_filtro = st.sidebar.multiselect("Filtrar por Status", options=df['Status'].unique(), default=df['Status'].unique())
    df_filtered = df[df['Status'].isin(status_filtro)]

    # --- MÉTRICAS PRINCIPAIS ---
    m1, m2, m3 = st.columns(3)
    
    with m1:
        avg_sol_ent = df_filtered['Dias Solicitação x Entrega'].mean()
        st.metric("Média: Solicitação ➔ Entrega", f"{avg_sol_ent:.1f} dias")
        st.caption("Prazo médio pedido pelo solicitante")

    with m2:
        avg_sol_oc = df_filtered['Dias Solicitação x OC'].mean()
        st.metric("Média: Solicitação ➔ Compra (OC)", f"{avg_sol_oc:.1f} dias")
        st.caption("Tempo médio para gerar a Ordem de Compra")

    with m3:
        atrasos = df_filtered[df_filtered['Gap Entrega x OC'] > 0].shape[0]
        st.metric("Compras após Data de Entrega", f"{atrasos} itens", delta_color="inverse")
        st.caption("Casos onde a OC foi gerada após o prazo de entrega solicitado")

    # --- VISUALIZAÇÃO DOS DADOS ---
    st.subheader("Detalhamento dos Prazos")
    
    # Estilização básica para destacar linhas críticas (ex: OC após data de entrega)
    def highlight_delay(row):
        return ['background-color: #ffcccc' if row['Gap Entrega x OC'] > 0 else '' for _ in row]

    st.dataframe(
        df_filtered[['Solicitação', 'Status', 'Descrição', 'Data Solicitação', 'Data Entrega', 'Data OC', 
                     'Dias Solicitação x Entrega', 'Dias Solicitação x OC', 'Gap Entrega x OC']].style.apply(highlight_delay, axis=1),
        use_container_width=True
    )

    # --- GRÁFICOS ---
    st.subheader("Análise Temporal")
    chart_data = df_filtered.set_index('Data Solicitação')[['Dias Solicitação x OC']].resample('M').mean()
    st.line_chart(chart_data)

else:
    st.info("Aguardando upload da planilha para gerar indicadores.")
