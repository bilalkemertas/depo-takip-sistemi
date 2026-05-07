import streamlit as st
from core.services import mal_kabul

def run():

    st.title("Mal Kabul")

    kod = st.text_input("Kod")
    isim = st.text_input("İsim")
    miktar = st.number_input("Miktar", 0.0)
    tedarikci = st.text_input("Tedarikçi")

    if st.button("Giriş Yap"):
        try:
            mal_kabul(kod, isim, miktar, tedarikci)
            st.success("Başarılı")
        except Exception as e:
            st.error(str(e))
