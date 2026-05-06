import streamlit as st
import pandas as pd
import io
from datetime import datetime

def run(conn):
    st.subheader("🏭 Üretim Hazırlık Ekranı")
    uploaded_file = st.file_uploader("İş Emri Excel Dosyasını Yükleyin", type=['xlsx'])

    if uploaded_file:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # Sekme Yakalama
            target_sheet = "HAZIRLIK" if "HAZIRLIK" in sheet_names else "Sheet4" if "Sheet4" in sheet_names else None

            if target_sheet:
                df_raw = pd.read_excel(uploaded_file, sheet_name=target_sheet, header=None)
                
                # Başlık Avcısı
                baslik_satiri = next((i for i in range(min(30, len(df_raw))) if "stok kodu" in [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]), None)
                
                if baslik_satiri is not None:
                    df_clean = pd.read_excel(uploaded_file, sheet_name=target_sheet, skiprows=baslik_satiri)
                    df_clean.columns = [str(c).strip() for c in df_clean.columns]
                    
                    # Boş Hücreleri Doldur (ffill)
                    for col in ["Mamül Adı", "Mamül Kodu", "Ürün Kodu", "İş Emri No"]:
                        if col in df_clean.columns: df_clean[col] = df_clean[col].ffill()

                    is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                    df_clean['İş Emri'] = is_emri_adi
                    
                    cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                    for c in cols_target:
                        if c not in df_clean.columns: df_clean[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                    
                    df_final = df_clean.dropna(subset=['Stok Kodu'])[cols_target]
                    st.dataframe(df_final, use_container_width=True)

                    if st.button("VERİTABANINA KAYDET", type="primary"):
                        existing = conn.read(worksheet="Is_Emirleri")
                        conn.update(worksheet="Is_Emirleri", data=pd.concat([existing, df_final], ignore_index=True))
                        st.success("İş Emri Kaydedildi!")
                else:
                    st.error("❌ 'stok kodu' başlığı bulunamadı.")
            else:
                st.error("❌ 'HAZIRLIK' veya 'Sheet4' sekmesi bulunamadı.")
        except Exception as e:
            st.error(f"Hata: {e}")
