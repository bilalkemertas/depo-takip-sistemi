import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

def get_db_connection():
    """SQLite veritabanı bağlantısını kurar."""
    conn = sqlite3.connect('depo.db', check_same_thread=False)
    return conn

def run():
    st.subheader("🏭 Üretim Hazırlık Ekranı")
    st.markdown("---")

    uploaded_file = st.file_uploader("İş Emri Excel Dosyasını Yükleyin", type=['xlsx'])

    if uploaded_file:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # Dinamik Sekme Yakalama
            target_sheet = "Hazırlık" if "Hazırlık" in sheet_names else "Sheet4" if "Sheet4" in sheet_names else None

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
                    
                    # Veritabanına gidecek hedef sütunlar
                    cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                    for c in cols_target:
                        if c not in df_clean.columns: df_clean[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                    
                    df_final = df_clean.dropna(subset=['Stok Kodu'])[cols_target]
                    st.dataframe(df_final, use_container_width=True)

                    if st.button("🚀 VERİTABANINA KAYDET", type="primary"):
                        db = get_db_connection()
                        try:
                            # SQLite veritabanına ekleme (append) işlemi
                            df_final.to_sql("Is_Emirleri", db, if_exists="append", index=False)
                            st.success(f"✅ {is_emri_adi} başarıyla sisteme kaydedildi!")
                            st.balloons()
                        except Exception as sql_e:
                            st.error(f"Veritabanına yazılırken hata: {sql_e}")
                        finally:
                            db.close()
                else:
                    st.error("❌ Excel dosyasında 'stok kodu' başlığı bulunamadı. Formatı kontrol edin.")
            else:
                st.error("❌ Dosya içinde 'Hazırlık' veya 'Sheet4' sekmesi bulunamadı.")
        except Exception as e:
            st.error(f"Hata: {e}")

    # Alt kısımda geçmiş iş emirlerini göstermek istersen (Opsiyonel)
    st.markdown("---")
    with st.expander("📊 Kayıtlı İş Emirlerini Görüntüle"):
        try:
            db = get_db_connection()
            arsiv_df = pd.read_sql("SELECT * FROM Is_Emirleri", db)
            st.dataframe(arsiv_df, use_container_width=True)
            db.close()
        except:
            st.info("Henüz kaydedilmiş bir iş emri bulunmuyor.")
