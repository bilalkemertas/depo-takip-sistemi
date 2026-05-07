import streamlit as st
from core.services import sayim_gir

def run():

    st.title("Sayım")

    kod = st.text_input("Kod")
    miktar = st.number_input("Sayım", 0.0)

    if st.button("Kaydet"):
        try:
            sayim_gir(kod, miktar)
            st.success("Kaydedildi")
        except Exception as e:
            st.error(str(e))
