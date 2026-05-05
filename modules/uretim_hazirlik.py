import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Navigasyon Fonksiyonları
def go_uretim_menu(): 
    st.session_state.uretim_page = 'menu'
    # Güvenli temizlik: Varsa sil, yoksa hata verme
    st.session_state.pop('local_stok', None)
    st.session_state.pop('local_emirler', None)

def go_is_emri(): st.session_state.uretim_page = 'is_emri'
def go_hazirlik(): st.session_state.uretim_page = 'hazirlik'
def go_rapor(): st.session_state.uretim_page = 'rapor'

def run(conn):
    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"): 
            st.session_state.page = 'home'
            st.rerun()
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. İŞ EMRİ YÜKLEME ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Yeni İş Emri Yükle")
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                # 1. Ham okuma yap
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                
                # 2. Başlık Satırını Bul (Dinamik Başlık Avcısı)
                baslik_satiri = None
                for i in range(min(30, len(df_raw))):
                    satir_degerleri = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir_degerleri:
                        baslik_satiri = i
                        break
                
                if baslik_satiri is None:
                    st.error("❌ Hata: Excel'de 'stok kodu' başlığı bulunamadı! Lütfen sütun isimlerini kontrol edin.")
                    return

                # 3. Veriyi başlık satırına göre yeniden şekillendir
                df_clean = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=baslik_satiri)
                df_clean.columns = [str(c).strip() for c in df_clean.columns]
                
                # 4. Sütunları Standartlaştır (Eksiltme Yapma)
                if "Mamül Kodu" in df_clean.columns: df_clean["Ürün Kodu"] = df_clean["Mamül Kodu"]
                
                # 'total' geçen miktarı bul
                for col in df_clean.columns:
                    if "total" in str(col).lower() or "miktar" in str(col).lower():
                        df_clean["İhtiyaç Miktarı"] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
                        break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_clean['İş Emri'] = is_emri_adi
                
                # Hedef Şablon
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_clean.columns: 
                        df_clean[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_final = df_clean.dropna(subset=['Stok Kodu'])[cols_target]
                
                st.write(f"✅ {len(df_final)} kalem malzeme algılandı.")
                st.dataframe(df_final.head(), use_container_width=True)

                if st.button("VERİTABANINA KAYDET", type="primary"):
                    existing = conn.read(worksheet="Is_Emirleri")
                    updated = pd.concat([existing, df_final], ignore_index=True)
                    conn.update(worksheet="Is_Emirleri", data=updated)
                    st.success("İş Emri başarıyla işlendi!")
                    st.cache_data.clear()
                    go_uretim_menu()
                    st.rerun()

            except Exception as e:
                st.error(f"Excel Okuma Hatası: {e}")
                st.info("İpucu: Sayfa adının 'HAZIRLIK' olduğundan ve 'Stok Kodu' başlığının bulunduğundan emin olun.")

    # Diğer 'hazirlik' ve 'rapor' kısımları aynı mantıkla devam eder...
