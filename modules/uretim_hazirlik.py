import streamlit as st
import pandas as pd

def run(conn):
    st.header("🏗️ Üretim Hazırlık (İş Emri)")
    
    uploaded_file = st.file_uploader("Üretim Excel Dosyasını Yükle", type=['xlsx'])
    
    if uploaded_file:
        # Dinamik Başlık Avcısı Mantığı
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # Başlık satırını bulma (İçinde 'Malzeme' geçen satır)
        header_idx = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains('Malzeme', case=False).any(), axis=1)].index[0]
        df = pd.read_excel(uploaded_file, skiprows=header_idx)
        
        # Boş satırları temizle ve Birleştirilmiş hücreleri (FFill) doldur
        df = df.dropna(how='all').reset_index(drop=True)
        df['İş Emri No'] = df['İş Emri No'].ffill() 
        
        # İndeksleme (Açılır Pencere)
        is_emirleri = df['İş Emri No'].unique()
        secilen_emri = st.selectbox("İş Emri Seçin:", is_emirleri)
        
        # Detay Tablosu (5 Sütun Kuralı)
        detay = df[df['İş Emri No'] == secilen_emri][['Malzeme Kodu', 'Malzeme Adı', 'Miktar', 'Birim', 'Durum']]
        st.table(detay)
        # [cite: 1, 2]
