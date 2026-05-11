import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Dashboard de Compras e Solicitações", layout="wide")

st.title("📊 Indicadores de Solicitações e Compras")
st.markdown("Análise de prazos entre Solicitação, Entrega Desejada e Compra (OC).")

# Função para carregar dados
@st.cache_data
def load_data(file):
    # Lendo a planilha (CSV ou Excel)
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    # Conversão de colunas para datetime de forma robusta
    date_cols = ['Data Solicitação', 'Data Entrega', 'Data OC']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    
    # Cálculos de Lead Time (Dias)
    # 1. Dias entre Solicitação e Entrega Desejada
    df['Dias Solicitação x Entrega'] = (df['Data Entrega'] - df['Data Solicitação']).dt.days
    
    # 2. Dias entre Solicitação e Compra Efetiva (Data OC)
    df['Dias Solicitação x OC'] = (df['Data OC'] - df['Data Solicitação']).dt.days
    
    # 3. Gap entre Entrega Desejada e Data da OC (Atraso na formalização)
    df['Gap Entrega x OC'] = (df['Data OC'] - df['Data Entrega']).dt.days
    
    return df

# Upload do arquivo
uploaded_file = st.file_uploader("Arraste aqui sua planilha 'solicitações e compras.xlsx'", type=["xlsx", "csv"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    # Filtros laterais
    st.sidebar.header("Filtros")
    
    # Garantir que não temos problemas com NAs nos filtros
    status_list = df['Status'].dropna().unique().tolist()
    status_filtro = st.sidebar.multiselect("Filtrar por Status", options=status_list, default=status_list)
    
    df_filtered = df[df['Status'].isin(status_filtro)].copy()

    # --- MÉTRICAS PRINCIPAIS ---
    m1, m2, m3 = st.columns(3)
    
    with m1:
        avg_sol_ent = df_filtered['Dias Solicitação x Entrega'].mean()
        st.metric("Média: Solicitação ➔ Entrega", f"{avg_sol_ent:.1f} dias" if not np.isnan(avg_sol_ent) else "N/A")
        st.caption("Prazo médio pedido pelo solicitante")

    with m2:
        avg_sol_oc = df_filtered['Dias Solicitação x OC'].mean()
        st.metric("Média: Solicitação ➔ Compra (OC)", f"{avg_sol_oc:.1f} dias" if not np.isnan(avg_sol_oc) else "N/A")
        st.caption("Tempo médio para gerar a Ordem de Compra")

    with m3:
        # Filtramos onde a OC foi gerada após a entrega solicitada
        atrasos = df_filtered[df_filtered['Gap Entrega x OC'] > 0].shape[0]
        st.metric("Compras após Data de Entrega", f"{atrasos} itens")
        st.caption("Casos onde a OC foi gerada após o prazo de entrega solicitado")

    # --- VISUALIZAÇÃO DOS DADOS ---
    st.subheader("Detalhamento dos Prazos")
    
    # Regra visual para destacar linhas onde a OC atrasou em relação à data pedida
    def highlight_delay(row):
        color = 'background-color: #ffcccc' if row['Gap Entrega x OC'] > 0 else ''
        return [color] * len(row)

    # Exibição da tabela formatada
    cols_to_show = ['Solicitação', 'Status', 'Descrição', 'Data Solicitação', 'Data Entrega', 'Data OC', 
                    'Dias Solicitação x Entrega', 'Dias Solicitação x OC', 'Gap Entrega x OC']
    
    st.dataframe(
        df_filtered[cols_to_show].style.apply(highlight_delay, axis=1),
        use_container_width=True
    )

    # --- GRÁFICOS (Correção do Erro de Resample) ---
    st.subheader("Análise Temporal de Lead Time de Compra")
    
    # Para o gráfico, precisamos remover datas nulas na 'Data Solicitação' e usar a nova frequência 'ME'
    df_chart = df_filtered.dropna(subset=['Data Solicitação']).copy()
    
    if not df_chart.empty:
        # 'ME' é a nova sigla para Month End no Pandas 2.2+
        try:
            chart_data = df_chart.set_index('Data Solicitação')[['Dias Solicitação x OC']].resample('ME').mean()
            st.line_chart(chart_data)
        except ValueError:
            # Fallback para 'M' caso esteja em uma versão muito antiga (raro no Streamlit Cloud)
            chart_data = df_chart.set_index('Data Solicitação')[['Dias Solicitação x OC']].resample('M').mean()
            st.line_chart(chart_data)
    else:
        st.warning("Sem dados temporais suficientes para gerar o gráfico.")

else:
    st.info("Aguardando upload da planilha para gerar indicadores.")
