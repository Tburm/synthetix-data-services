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
@st.cache_data(ttl=600)
def run_query(query):
    df = pd.read_sql(query, conn)
    return df

# load data
df_trade = run_query('SELECT * FROM trades ORDER BY timestamp')
df_transfer = run_query('SELECT * FROM transfers ORDER BY timestamp')
df_debt = run_query('SELECT * FROM market_debt ORDER BY timestamp')

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

@st.cache_data(ttl=600)
def get_pnl_summary(df_debt, df_transfer, df_trade):
    # calculate cumulative values
    df_transfer['cumulative_size'] = df_transfer.groupby('asset')['size'].cumsum()
    df_trade['cumulative_fees_paid'] = df_trade.groupby('asset')['feespaid'].cumsum()

    # Use merge_asof to carry forward values with respect to a timestamp
    df_debt = pd.merge_asof(df_debt, df_transfer[['asset', 'timestamp', 'cumulative_size']], on='timestamp', by='asset', direction='backward')
    df_debt = pd.merge_asof(df_debt, df_trade[['asset', 'timestamp', 'cumulative_fees_paid']], on='timestamp', by='asset', direction='backward')

    # fill missing values with 0
    df_debt['net_transfers'] = df_debt['cumulative_size'].fillna(0)
    df_debt['fees_paid'] = df_debt['cumulative_fees_paid'].fillna(0)
    df_debt.drop(['cumulative_size', 'cumulative_fees_paid'], axis=1, inplace=True)

    # sort the dataframe
    df_debt = df_debt.sort_values(['asset', 'timestamp'])

    # add columns
    df_debt['date'] = pd.to_datetime(df_debt['timestamp'], unit='s')
    df_debt['net_pnl'] = df_debt['market_debt'] - df_debt['net_transfers'] - df_debt['fees_paid']
    df_debt['staker_pnl'] = -df_debt['net_pnl']

    df_pnl = df_debt.copy(deep=True)
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
