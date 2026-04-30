import streamlit as st
import pandas as pd
from datetime import datetime

def run_islem(conn):
    st.subheader("📊 Stok Giriş / Çıkış Paneli")
    
    try:
        # --- GÜNCELLEME: Sayfa adı "Urun_Listesi" olarak değiştirildi ---
        df_stok = conn.read(worksheet="Urun_Listesi")
        df_hareketler = conn.read(worksheet="Hareketler")
        
        # Akıllı Arama Bölümü
        search_query = st.text_input("🔍 Ürün Ara (Ad veya Kod yazın)", "")
        
        if search_query:
            # Arama hem isimde hem kodda yapılır
            filtered_df = df_stok[
                df_stok['URUN_ADI'].str.contains(search_query, case=False, na=False) | 
                df_stok['URUN_KODU'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = df_stok

        # Seçim Kutusu
        if not filtered_df.empty:
            # Seçenekleri hazırlıyoruz
            options = filtered_df.apply(lambda x: f"{x['URUN_KODU']} | {x['URUN_ADI']}", axis=1).tolist()
            selected_option = st.selectbox("Ürünü Onaylayın:", options)
            
            # Seçilen Ürünün Detaylarını Ayıkla
            sel_kodu = selected_option.split(" | ")[0]
            urun_bilgi = df_stok[df_stok['URUN_KODU'] == sel_kodu].iloc[0]
            
            # Mevcut stok miktarını göster (Urun_Listesi'nden çekilir)
            st.info(f"Mevcut Stok: {urun_bilgi.get('MIKTAR', 0)} {urun_bilgi.get('BIRIM', 'ADET')}")
            
            # Kayıt Formu
            with st.form("islem_formu", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    islem = st.selectbox("İşlem Türü", ["GİRİŞ", "ÇIKIŞ"])
                    miktar = st.number_input("İşlem Miktarı", min_value=0.1, step=1.0)
                with col2:
                    # Adres ve personel bilgisi
                    adres = st.text_input("Depo Adresi", value=urun_bilgi.get('ADRES', ''))
                    personel = st.text_input("İşlemi Yapan Personel")
                
                submitted = st.form_submit_button("KAYDET")
                
                if submitted:
                    if not personel:
                        st.error("Lütfen personel ismini girin!")
                    else:
                        # Hareket Tablosuna Kayıt Hazırlığı
                        final_miktar = miktar if islem == "GİRİŞ" else -miktar
                        yeni_kayit = pd.DataFrame([{
                            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Ürün Kodu": sel_kodu,
                            "Ürün Adı": urun_bilgi['URUN_ADI'],
                            "Adres": adres,
                            "Miktar": final_miktar,
                            "İşlem": islem,
                            "Personel": personel
                        }])
                        
                        # Google Sheets "Hareketler" sayfasına ekleme
                        updated_df = pd.concat([df_hareketler, yeni_kayit], ignore_index=True)
                        conn.update(worksheet="Hareketler", data=updated_df)
                        st.success(f"{islem} İşlemi Başarıyla Kaydedildi!")
                        st.balloons()
        else:
            st.warning("Aranan kriterlere uygun ürün bulunamadı.")
            
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        st.info("İpucu: Google Sheets'teki sekme adının tam olarak 'Urun_Listesi' olduğundan emin olun.")

def run_transfer(conn):
    st.subheader("↔️ Depo İçi Transfer")
    # Transfer ekranında da listeyi "Urun_Listesi" sayfasından okuması için güncellendi
    try:
        df_stok = conn.read(worksheet="Urun_Listesi")
        # ... (Transfer fonksiyonun diğer satırları hiçbir özellik eksilmeden devam eder)
    except:
        pass
