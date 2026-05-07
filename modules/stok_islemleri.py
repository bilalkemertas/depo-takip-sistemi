import streamlit as st
from core.services import get_stok, create_urun

def run():

    st.title("Stok Yönetimi")

    df = get_stok()
    st.dataframe(df)

    st.subheader("Yeni Ürün")

    kod = st.text_input("Kod")
    isim = st.text_input("İsim")

    if st.button("Ekle"):
        try:
            create_urun(kod, isim)
            st.success("Ürün eklendi")
        except Exception as e:
            st.error(str(e))
