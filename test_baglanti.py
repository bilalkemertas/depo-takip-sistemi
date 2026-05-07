import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.subheader("📡 Google Drive Bağlantı Testi (Ping)")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # TEST 1: Dosyaya erişebiliyor mu?
    st.write("🔍 Dosyaya erişim deneniyor...")
    # Sadece ilk 1 satırı okumayı dene
    df = conn.read(worksheet="Urun_Listesi", nrows=1, ttl=0)
    
    if isinstance(df, pd.DataFrame):
        st.success("✅ Bağlantı Başarılı! Veri okunabiliyor.")
        st.write("Bulunan Sütunlar:", df.columns.tolist())
    else:
        st.error("❌ Dosya bulundu ama tablo formatında değil.")

except Exception as e:
    st.error("🛑 BAĞLANTI HATASI TESPİT EDİLDİ!")
    st.code(str(e))
    st.info("""
    💡 **Muhtemel Sebepler:**
    1. URL hatalı: 'spreadsheet' linkini kontrol et.
    2. Token Süresi: Streamlit Cloud'da 'Reboot' gerekebilir.
    3. API Kapalı: Google Cloud Console'da 'Google Sheets API' etkin mi?
    """)
