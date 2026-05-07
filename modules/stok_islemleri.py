import streamlit as st
import pandas as pd
from core import db

def run():

    st.title("Stok Yönetimi")

    df = db.read("stok")

    st.dataframe(df)

    st.subheader("Yeni Ürün")

    kod = st.text_input("Kod")
    isim = st.text_input("İsim")
    miktar = st.number_input("Miktar", 0.0)
    adres = st.text_input("Adres")

    if st.button("Kaydet"):
        yeni = pd.DataFrame([{
            "kod": kod,
            "isim": isim,
            "miktar": miktar,
            "adres": adres
        }])

        db.write("stok", yeni, "append")
        st.success("Kaydedildi")
