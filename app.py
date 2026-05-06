import streamlit as st
from core import db

from modules import (
    stok_islemleri,
    uretim_hazirlik,
    sayim_modulu,
    blok_kesim
)

# INIT DB
db.init_db()

st.set_page_config(
    page_title="Depo Otomasyon v3 (SQLite)",
    layout="wide"
)

st.sidebar.title("📦 WMS SQLITE")

page = st.sidebar.radio(
    "Menü",
    ["Ana", "Stok", "Transfer", "Üretim", "Sayım", "Blok Kesim"]
)

if page == "Ana":
    st.title("SQLite WMS Sistemi")

elif page == "Stok":
    stok_islemleri.run()

elif page == "Transfer":
    stok_islemleri.run_transfer()

elif page == "Üretim":
    uretim_hazirlik.run()

elif page == "Sayım":
    sayim_modulu.run()

elif page == "Blok Kesim":
    blok_kesim.run()
