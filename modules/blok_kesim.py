import streamlit as st
import pandas as pd
import requests
import io # Bu yeni eklendi, dosya hatasını bu çözecek

def fetch_supplier_data():
    # URL ve Bilgiler
    LOGIN_URL = "https://tdp.formsunger.com.tr/login" 
    DATA_URL = "https://tdp.formsunger.com.tr/dashboard/shipment-report"
    
    # HTML'e göre güncellenmiş giriş anahtarları
    payload = {
        "user": "F550B060",      # HTML'de id='user' olduğu için böyle deniyoruz
        "password": "F550B0000"
    }

    session = requests.Session()
    # Bazı modern siteler 'tarayıcı' olduğumuzu kanıtlamamızı ister
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    try:
        # 1. Giriş denemesi
        session.post(LOGIN_URL, data=payload, timeout=10)
        
        # 2. Raporu çek
        response = session.get(DATA_URL, timeout=10)
        
        if response.status_code == 200:
            # EĞER HALA GİRİŞ SAYFASINDAYSAK (Giriş başarısızsa)
            if "Giriş Yap" in response.text:
                st.error("Giriş Başarısız: Site botu reddetti veya bilgiler hatalı.")
                # Gelen sayfanın ne olduğunu görmek için (Debug)
                with st.expander("Site Yanıtı (Hata Detayı)"):
                    st.code(response.text[:500])
                return None
            
            # PANDAS DOSYA HATASI ÇÖZÜMÜ: io.StringIO kullanıyoruz
            tables = pd.read_html(io.StringIO(response.text))
            if tables:
                return tables[0]
            else:
                st.warning("Sayfada okunabilir bir tablo bulunamadı.")
        else:
            st.error(f"Site Hatası: {response.status_code}")

    except Exception as e:
        st.error(f"Bağlantı sırasında bir hata oluştu: {e}")
    return None

def run_blok_kesim(conn):
    st.subheader("✂️ Blok Sünger Kesimi Otomasyonu")
    
    with st.sidebar:
        if st.button("🔄 FORM SÜNGER'DEN VERİ AL"):
            with st.spinner("Tedarikçi portalına bağlanılıyor..."):
                df = fetch_supplier_data()
                if df is not None:
                    st.session_state['formsunger_data'] = df
                    st.success("Veriler başarıyla çekildi!")

    # Tabloyu Görüntüle
    if 'formsunger_data' in st.session_state:
        st.dataframe(st.session_state['formsunger_data'], use_container_width=True)
        
        barkod = st.text_input("🔍 Blok Barkodu Okutun")
        if barkod:
            df = st.session_state['formsunger_data']
            # Barkodu ara
            match = df[df.astype(str).apply(lambda x: x.str.contains(barkod)).any(axis=1)]
            if not match.empty:
                st.write("✅ Blok Bulundu:", match)
            else:
                st.warning("Barkod listede yok.")
    else:
        st.info("Verileri çekmek için sol menüdeki butona basın.")
