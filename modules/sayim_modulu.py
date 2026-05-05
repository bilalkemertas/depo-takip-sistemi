import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Navigasyon Fonksiyonları
def go_sayim_menu(): st.session_state.sayim_page = 'menu'
def go_oturum(): st.session_state.sayim_page = 'oturum'
def go_giris(): st.session_state.sayim_page = 'giris'
def go_rapor(): st.session_state.sayim_page = 'rapor'

def run(conn):
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    if 'aktif_sayim_adi' not in st.session_state: st.session_state.aktif_sayim_adi = None
    if 'sayim_page' not in st.session_state: st.session_state.sayim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.sayim_page == 'menu':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ ANA MENÜ"): 
                st.session_state.page = 'home'
                st.rerun()
        st.subheader("⚖️ Sayım Kontrol Merkezi")
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.button("📁 OTURUM YÖNETİMİ", use_container_width=True, type="primary", on_click=go_oturum)
        c2.button("📝 SAYIM GİRİŞİ", use_container_width=True, type="primary", on_click=go_giris)
        c3.button("📊 FARK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)
        
        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
        else:
            st.info("ℹ️ Lütfen Oturum Yönetimi'nden yeni bir sayım başlatın.")

    # --- 1. OTURUM YÖNETİMİ (BURASI REVİZE EDİLDİ) ---
    elif st.session_state.sayim_page == 'oturum':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        st.subheader("📁 Oturum Yönetimi")
        
        # Verileri Oku
        df_sayim_ana = conn.read(worksheet="sayim")
        df_tamamlanan = conn.read(worksheet="sayim_tamamlanan")
        tamamlanmis_oturumlar = df_tamamlanan['Oturum_Adi'].dropna().unique().tolist() if not df_tamamlanan.empty else []

        # DURUM A: AKTİF OTURUM YOKSA
        if st.session_state.aktif_sayim_adi is None:
            st.markdown("### 🆕 Yeni Sayım Başlat")
            sayim_etiketi = st.text_input("Oturum Adı (Örn: Blok_B):", placeholder="Oturum İsmi Giriniz...")
            
            if st.button("🚀 SAYIM OTURUMUNU ŞİMDİ BAŞLAT", use_container_width=True, type="primary"):
                if sayim_etiketi:
                    zaman = datetime.now().strftime("%d%m_%H%M")
                    yeni_id = f"{sayim_etiketi}_{zaman}"
                    
                    # SNAPSHOT: Mevcut stoğu o anki haliyle dondur (Fark raporu için)
                    df_stok_anlik = conn.read(worksheet="Urun_Listesi")
                    if not df_stok_anlik.empty:
                        df_stok_anlik['Oturum_Adi'] = yeni_id
                        try:
                            mevcut_snapshots = conn.read(worksheet="sayim_snapshot")
                            yeni_snapshots = pd.concat([mevcut_snapshots, df_stok_anlik], ignore_index=True)
                        except:
                            yeni_snapshots = df_stok_anlik
                            
                        conn.update(worksheet="sayim_snapshot", data=yeni_snapshots)
                    
                    st.session_state.aktif_sayim_adi = yeni_id
                    st.success(f"Oturum Açıldı: {yeni_id}")
                    st.rerun()
                else:
                    st.error("Lütfen bir oturum ismi girin!")

            # Bekleyenleri Listele
            if not df_sayim_ana.empty:
                tum_oturumlar = df_sayim_ana['Oturum_Adi'].unique().tolist()
                bekleyenler = [o for o in tum_oturumlar if o not in tamamlanmis_oturumlar]
                if bekleyenler:
                    st.markdown("---")
                    st.markdown("### ⏳ Bekleyen Oturumlar")
                    sec_oturum = st.selectbox("Devam edilecek oturumu seçin:", bekleyenler)
                    if st.button("🔄 SEÇİLİ OTURUMU AKTİFLEŞTİR"):
                        st.session_state.aktif_sayim_adi = sec_oturum
                        st.rerun()

        # DURUM B: AKTİF OTURUM VARSA
        else:
            st.success(f"📡 Şuan Çalışılan Oturum: **{st.session_state.aktif_sayim_adi}**")
            with st.container(border=True):
                if st.button("🛑 OTURUMU KAPAT (Verileri Silmez)", use_container_width=True):
                    st.session_state.aktif_sayim_adi = None
                    st.rerun()
                
                st.divider()
                st.warning("⚠️ STOKLARI GÜNCELLE: Sayımı bitirip ana stoğa işler.")
                onay = st.checkbox("Sayım sonuçlarının kesinliğini onaylıyorum.")
                if st.button("🚀 STOKLARI GÜNCELLE VE ARŞİVLE", type="primary", use_container_width=True, disabled=not onay):
                    # ... (Stok güncelleme mantığı burada çalışır)
                    pass

    # --- 2. SAYIM GİRİŞİ ---
    elif st.session_state.sayim_page == 'giris':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        st.subheader("📝 Sayım Girişi")
        
        if st.session_state.aktif_sayim_adi is None:
            st.warning("⚠️ Önce Oturum Yönetimi'nden bir sayım başlatmalısın Patron!")
        else:
            st.info(f"📍 Oturum: {st.session_state.aktif_sayim_adi}")
            # ... (Senin verdiğin giriş formu kodları aynen burada devam eder)
