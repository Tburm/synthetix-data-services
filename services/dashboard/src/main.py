import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

conn = init_connection()

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def run_query(query):
    df = pd.read_sql(query, conn)
    return df

# load data
df_trade = run_query('SELECT * FROM trades ORDER BY asset, timestamp')
df_transfer = run_query('SELECT * FROM transfers ORDER BY asset, timestamp')
df_debt = run_query('SELECT * FROM market_debt ORDER BY asset, timestamp')

# view tables
# st.header('Trades')
# st.write(df_trade.head(5))

# st.header('Transfer')
# st.write(df_transfer.head(5))

# st.header('Debt')
# st.write(df_debt.head(5))

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
    # st.write(f'Creating aggregations for {df_debt.shape[0]} debt snapshots')
    # st.write('Summarizing transfers')
    net_transfers = df_debt.apply(lambda row: get_cumulative_value(df_transfer, row, 'size'), axis=1)
    # st.write('Summarizing transfers complete')

    # st.write('Summarizing fees')
    fees_paid = df_debt.apply(lambda row: get_cumulative_value(df_trade, row, 'feespaid'), axis=1)
    # st.write('Summarizing fees complete')

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
selected_assets = st.multiselect('Select assets', assets, default=assets)
pnl_fig = px.area(
    df_pnl[df_pnl['asset'].isin(selected_assets)],
    x='date',
    y='staker_pnl',
    color='asset',
    title=f"Total Perps Pnl"
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

selected_asset = st.selectbox('Select asset', assets)
st.plotly_chart(asset_pnl_figs[selected_asset])


@st.cache_data(ttl=600)
def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')

pnl_csv = convert_df(df_pnl)

with st.expander("Export CSV"):
    st.download_button(
        "Press to Download",
        pnl_csv,
        "market_pnl.csv",
        "text/csv",
        key='download-csv'
    )
    st.write(df_pnl)
