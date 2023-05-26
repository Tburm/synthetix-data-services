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

@st.cache_data(ttl=1)
def get_pnl_summary():
    df_pnl = pd.read_csv('./data/market_pnl.csv')
    return df_pnl

df_pnl = get_pnl_summary()
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
