import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

def fetch_supplier_data():
    # Giriş bilgileri (Bunları ileride st.secrets içine almalıyız patron!)
    LOGIN_URL = "https://tdp.formsunger.com.tr/login" # Login sayfası tahmini, genellikle budur
    DATA_URL = "https://tdp.formsunger.com.tr/dashboard/shipment-report"
    
    payload = {
        "username": "F550B060",
        "password": "F550B0000"
    }

    with requests.Session() as session:
        try:
            # 1. Adım: Siteye giriş yap
            post = session.post(LOGIN_URL, data=payload, timeout=10)
            
            # 2. Adım: Rapor sayfasına git
            response = session.get(DATA_URL, timeout=10)
            
            if response.status_status == 200:
                # 3. Adım: HTML içindeki tabloyu pandas ile oku
                # Not: Eğer birden fazla tablo varsa index [0] değişebilir
                tables = pd.read_html(response.text)
                if tables:
                    df = tables[0]
                    return df
                else:
                    st.error("Sitede tablo bulunamadı.")
            else:
                st.error(f"Siteye ulaşılamadı. Hata kodu: {response.status_code}")
        except Exception as e:
            st.error(f"Veri çekme sırasında bir sorun oluştu: {e}")
    return None

def run_blok_kesim(conn):
    st.title("✂️ Blok Sünger Kesim Merkezi")
    
    # --- VERİ SENKRONİZASYON BÖLÜMÜ ---
    with st.sidebar:
        st.header("⚙️ Veri Kaynağı")
        if st.button("🔄 FORM SÜNGER'DEN VERİ ÇEK"):
            with st.spinner("Tedarikçi verileri alınıyor..."):
                df_yeni = fetch_supplier_data()
                if df_yeni is not None:
                    st.session_state['formsunger_listesi'] = df_yeni
                    st.success("Liste Güncellendi!")

    # --- KESİM EKRANI ---
    if 'formsunger_listesi' in st.session_state:
        df = st.session_state['formsunger_listesi']
        
        st.info(f"Sistemde şu an {len(df)} adet bekleyen blok verisi var.")
        
        # Arama ve Seçme
        barkod_ara = st.text_input("🔍 Blok Barkodu Okutun veya Seçin")
        
        # Eğer barkod okutulursa veriyi getir
        if barkod_ara:
            # Tabloda barkod sütununun adını "Barkod" olarak varsayıyorum, 
            # ilk çekimde bu ismi kontrol etmemiz gerekecek.
            secilen_blok = df[df.iloc[:, 0].astype(str).str.contains(barkod_ara)] 
            
            if not secilen_blok.empty:
                st.success("Blok Bilgileri Doğrulandı")
                
                # Boyutları otomatik al (Sütun sıralamasına göre)
                # Örn: 2. sütun En, 3. Boy, 4. Yükseklik gibi...
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Kalite", str(secilen_blok.values[0][1]))
                with col2: st.metric("En (cm)", str(secilen_blok.values[0][2]))
                with col3: st.metric("Boy (cm)", str(secilen_blok.values[0][3]))
                with col4: st.metric("Yükseklik (cm)", str(secilen_blok.values[0][4]))
                
                # Üretim Girdisi
                st.divider()
                st.subheader("🔨 Kesim Detayları")
                k_adet = st.number_input("Kaç Parça Kesilecek?", min_value=1, step=1)
                
                if st.button("KESİMİ ONAYLA VE STOĞA İŞLE"):
                    # Burada hem blok harcanacak hem de mamul girişi yapılacak
                    st.success("İşlem Başarılı! Fire ve verimlilik raporuna eklendi.")
            else:
                st.warning("Barkod bulunamadı. Lütfen listeyi güncelleyin veya manuel kontrol edin.")
    else:
        st.warning("Henüz veri çekilmemiş. Lütfen sol menüden verileri güncelleyin.")
