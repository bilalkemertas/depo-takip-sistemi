import streamlit as st
import pandas as pd
from datetime import datetime

def run_islem(conn):
    st.subheader("📊 Stok Giriş / Çıkış Paneli")
    
    try:
        df_stok = conn.read(worksheet="Urun_Listesi")
        df_hareketler = conn.read(worksheet="Hareketler")
        
        # Akıllı Arama
        search_query = st.text_input("🔍 Ürün Ara (Ad veya Kod yazın)", "")
        
        if search_query:
            filtered_df = df_stok[
                df_stok['isim'].str.contains(search_query, case=False, na=False) | 
                df_stok['kod'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = df_stok

        if not filtered_df.empty:
            options = filtered_df.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
            selected_option = st.selectbox("Ürünü Onaylayın:", options)
            
            sel_kodu = selected_option.split(" | ")[0]
            urun_bilgi = df_stok[df_stok['kod'] == sel_kodu].iloc[0]
            
            st.info(f"Mevcut Stok: {urun_bilgi.get('MIKTAR', 0)} {urun_bilgi.get('BIRIM', 'ADET')}")
            
            with st.form("islem_formu", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    islem = st.selectbox("İşlem Türü", ["GİRİŞ", "ÇIKIŞ"])
                    miktar = st.number_input("İşlem Miktarı", min_value=0.1, step=1.0)
                with col2:
                    adres = st.text_input("Depo Adresi", value=urun_bilgi.get('ADRES', ''))
                
                submitted = st.form_submit_button("KAYDET")
                
                if submitted:
                    # Personel bilgisini session_state'den otomatik alıyoruz
                    personel = st.session_state.get('user', 'Bilinmeyen Personel')
                    final_miktar = miktar if islem == "GİRİŞ" else -miktar
                    
                    yeni_kayit = pd.DataFrame([{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Ürün Kodu": sel_kodu,
                        "Ürün Adı": urun_bilgi['isim'],
                        "Adres": adres,
                        "Miktar": final_miktar,
                        "İşlem": islem,
                        "Personel": personel
                    }])
                    
                    updated_df = pd.concat([df_hareketler, yeni_kayit], ignore_index=True)
                    conn.update(worksheet="Hareketler", data=updated_df)
                    st.success(f"İşlem Kaydedildi. Personel: {personel}")
                    st.balloons()
        else:
            st.warning("Ürün bulunamadı.")
            
    except Exception as e:
        st.error(f"Hata: {e}")

def run_transfer(conn):

    st.title("↔️ Depo İçi Transfer")

    try:
        # ÖRNEK: mevcut stok verisini çek
        df = conn.read(worksheet="stok")

        st.subheader("Mevcut Stok")
        st.dataframe(df)

        # Transfer giriş alanları
        col1, col2, col3 = st.columns(3)

        with col1:
            urun = st.text_input("Ürün Kodu")

        with col2:
            kaynak = st.text_input("Kaynak Lokasyon")

        with col3:
            hedef = st.text_input("Hedef Lokasyon")

        miktar = st.number_input("Miktar", min_value=1, step=1)

        if st.button("Transfer Yap"):

            if urun and kaynak and hedef:

                # filtreleme (örnek mantık)
                df.loc[
                    (df["urun"] == urun) & (df["lokasyon"] == kaynak),
                    "lokasyon"
                ] = hedef

                # Google Sheets'e yaz
                conn.update(worksheet="stok", data=df)

                st.success("Transfer başarılı")

            else:
                st.warning("Tüm alanları doldurun")

    except Exception as e:
        st.error(f"Sistem hatası: {e}")
