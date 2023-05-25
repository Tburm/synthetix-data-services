import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

st.set_page_config(
    page_title="Perps Market Pnl",
	layout="wide",
)

hide_footer = """
    <style>
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_footer, unsafe_allow_html=True) 

# initialize connection
@st.cache_resource
def init_connection():
    conn_str = 'postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}'.format(**st.secrets["postgres"])
    return create_engine(conn_str)

conn = init_connection()

# perform query and return results
@st.cache_data(ttl=14400)
def run_query(query):
    df = pd.read_sql(query, conn)
    return df

# load data
df_trade = run_query('SELECT * FROM trades ORDER BY asset, timestamp')
df_transfer = run_query('SELECT * FROM transfers ORDER BY asset, timestamp')
df_debt = run_query('SELECT * FROM market_debt ORDER BY asset, timestamp')

# add cumulative values
df_transfer['cumulative_size'] = df_transfer.groupby('asset')['size'].cumsum()
df_trade['cumulative_feespaid'] = df_trade.groupby('asset')['feespaid'].cumsum()

# join summaries to debt
def get_cumulative_value(df, row, value):
    cumulative_values = df.loc[(df['asset'] == row['asset']) & (df['timestamp'] <= row['timestamp']), f'cumulative_{value}']
    if cumulative_values.size == 0:
        return 0
    else:
        return cumulative_values.iloc[-1]

@st.cache_data(ttl=14400)
def get_pnl_summary(df_debt, df_transfer, df_trade):
    net_transfers = df_debt.apply(lambda row: get_cumulative_value(df_transfer, row, 'size'), axis=1)
    fees_paid = df_debt.apply(lambda row: get_cumulative_value(df_trade, row, 'feespaid'), axis=1)

    df_pnl = df_debt.copy(deep=True)

    df_pnl['net_transfers'] = net_transfers
    df_pnl['fees_paid'] = fees_paid

    df_pnl['date'] = pd.to_datetime(df_pnl['timestamp'], unit='s')
    df_pnl['net_pnl'] = df_pnl['market_debt'] - df_pnl['net_transfers'] - df_pnl['fees_paid']
    df_pnl['staker_pnl'] = -df_pnl['net_pnl']
    return df_pnl

df_pnl = get_pnl_summary(df_debt, df_transfer, df_trade)
assets = df_pnl['asset'].unique().tolist()

# Total pnl by asset
def chart_pnl_total():
    df_pnl_total = df_pnl.groupby('date')[['net_pnl', 'staker_pnl']].sum().reset_index()
    pnl_fig = px.area(
        df_pnl_total,
        x='date',
        y='staker_pnl',
        title=f"Total Perps Pnl"
    )

    st.plotly_chart(pnl_fig, use_container_width=True)


# Total pnl by asset
def chart_pnl_asset():
    with st.expander("Select assets"):
        selected_assets = st.multiselect('', assets, default=assets)

    pnl_fig = px.area(
        df_pnl[df_pnl['asset'].isin(selected_assets)],
        x='date',
        y='staker_pnl',
        color='asset',
        title=f"Perps Pnl by Market"
    )

    st.plotly_chart(pnl_fig)

# Pnl per asset
asset_pnl_figs = {}
for ind, asset in enumerate(assets):
    asset_fig = px.line(
        df_pnl[df_pnl['asset'] == asset],
        x='date',
        y=['staker_pnl', 'fees_paid'],
        title=f"{asset} Market Pnl"
    )

    asset_pnl_figs[asset] = asset_fig

def chart_pnl_fees_market():
    selected_asset = st.selectbox('Select asset', assets, index=assets.index('sETH'))
    st.plotly_chart(asset_pnl_figs[selected_asset])

def export_data():
    pnl_csv = df_pnl.to_csv(index=False).encode('utf-8')

    with st.expander("Export CSV"):
        st.download_button(
            "Download CSV",
            pnl_csv,
            "market_pnl.csv",
            "text/csv",
            key='download-csv'
        )
        st.write(df_pnl)

## Content ##
# chart_pnl_total()
# chart_pnl_asset()
# chart_pnl_fees_market()
# export_data()

chart_pnl_total()

with st.container():
    col1, col2 = st.columns(2)

    with col1:
        chart_pnl_asset()
    
    with col2:
        chart_pnl_fees_market()

with st.container():
    export_data()
