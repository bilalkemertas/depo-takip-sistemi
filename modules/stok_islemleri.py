import streamlit as st
from datetime import datetime
from services import stok_service

def run_islem():
    st.title("Stok Giriş / Çıkış")

    malzeme = st.text_input("Malzeme")
    miktar = st.number_input("Miktar", step=1.0)
    tip = st.selectbox("Tip", ["GIRIS", "CIKIS"])

    if st.button("Kaydet"):
        if tip == "CIKIS" and not stok_service.stok_yeterli_mi(malzeme, miktar):
            st.error("Yetersiz stok")
            return

        stok_service.hareket_ekle({
            "tarih": datetime.now(),
            "malzeme": malzeme,
            "miktar": miktar if tip=="GIRIS" else -miktar,
            "tip": tip,
            "kaynak": "DIS",
            "hedef": "DEPO"
        })

        st.success("İşlem tamam")

def run_transfer():
    st.title("Transfer")

    malzeme = st.text_input("Malzeme")
    miktar = st.number_input("Miktar")
    kaynak = st.text_input("Kaynak")
    hedef = st.text_input("Hedef")

    if st.button("Transfer"):
        stok_service.hareket_ekle({
            "tarih": datetime.now(),
            "malzeme": malzeme,
            "miktar": -miktar,
            "tip": "TRANSFER_CIKIS",
            "kaynak": kaynak,
            "hedef": hedef
        })

        stok_service.hareket_ekle({
            "tarih": datetime.now(),
            "malzeme": malzeme,
            "miktar": miktar,
            "tip": "TRANSFER_GIRIS",
            "kaynak": kaynak,
            "hedef": hedef
        })

        st.success("Transfer tamam")
