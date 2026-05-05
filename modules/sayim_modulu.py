import streamlit as st
import pandas as pd
import io
from datetime import datetime

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
            st.info("ℹ️ İşlem için Oturum Yönetimi'nden bir sayım başlatın.")

    # --- 1. OTURUM YÖNETİMİ ---
    elif st.session_state.sayim_page == 'oturum':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        st.subheader("📁 Oturum Yönetimi")
        
        try:
            df_sayim_ana = conn.read(worksheet="sayim")
        except:
            st.error("❌ 'sayim' sayfası bulunamadı! Lütfen Google Sheets'te bu isimle bir sayfa açın.")
            return

        if st.session_state.aktif_sayim_adi is None:
            st.markdown("### 🆕 Yeni Sayım Başlat")
            sayim_etiketi = st.text_input("Oturum Adı (Örn: Depo_A):")
            if st.button("🚀 SAYIMI BAŞLAT", use_container_width=True, type="primary"):
                if sayim_etiketi:
                    yeni_id = f"{sayim_etiketi}_{datetime.now().strftime('%d%m_%H%M')}"
                    df_anlik = conn.read(worksheet="Urun_Listesi")
                    if not df_anlik.empty:
                        df_anlik['Oturum_Adi'] = yeni_id
                        try:
                            eski_snap = conn.read(worksheet="sayim_snapshot")
                            conn.update(worksheet="sayim_snapshot", data=pd.concat([eski_snap, df_anlik], ignore_index=True))
                        except:
                            conn.update(worksheet="sayim_snapshot", data=df_anlik)
                    st.session_state.aktif_sayim_adi = yeni_id
                    st.rerun()
        else:
            st.success(f"📡 Aktif: {st.session_state.aktif_sayim_adi}")
            if st.button("🛑 OTURUMU KAPAT", use_container_width=True):
                st.session_state.aktif_sayim_adi = None
                st.rerun()

    # --- 2. SAYIM GİRİŞİ ---
    elif st.session_state.sayim_page == 'giris':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        if not st.session_state.aktif_sayim_adi:
            st.warning("⚠️ Önce oturum başlatın!")
            return
            
        with st.form("sayim_form"):
            s_adr = st.text_input("📍 Adres:").upper()
            s_kod = st.text_input("📦 Ürün Kodu:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
            if st.form_submit_button("➕ LİSTEYE EKLE"):
                st.session_state['gecici_sayim_listesi'].append({
                    "Oturum_Adi": st.session_state.aktif_sayim_adi,
                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik,
                    "Personel": st.session_state.get('user', 'Bilinmeyen')
                })
        
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']))
            if st.button("📤 BULUTA KAYDET"):
                eski_sayim = conn.read(worksheet="sayim")
                yeni_sayim = pd.concat([eski_sayim, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True)
                conn.update(worksheet="sayim", data=yeni_sayim)
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Kaydedildi!")

    # --- 3. FARK RAPORU ---
    elif st.session_state.sayim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        st.subheader("📊 Sayım Fark Raporu")
        
        try:
            df_sayim = conn.read(worksheet="sayim")
            df_snap = conn.read(worksheet="sayim_snapshot")
        except:
            st.error("❌ Gerekli sayfalar (sayim veya sayim_snapshot) bulunamadı!")
            return
        
        if not df_sayim.empty:
            oturumlar = df_sayim['Oturum_Adi'].unique().tolist()
            secilen = st.selectbox("Analiz edilecek oturum:", oturumlar)
            
            s_data = df_sayim[df_sayim['Oturum_Adi'] == secilen].groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            sys_data = df_snap[df_snap['Oturum_Adi'] == secilen].copy()
            
            # Sütun isimlerini normalize et (Büyük/Küçük harf duyarlılığı için)
            sys_data.columns = [c.upper() for c in sys_data.columns]
            if 'KOD' in sys_data.columns and 'MIKTAR' in sys_data.columns:
                sys_data = sys_data.groupby(['ADRES', 'KOD'])['MIKTAR'].sum().reset_index()
                sys_data.columns = ['Adres', 'Kod', 'Sistem_Stogu']
                
                fark_df = pd.merge(s_data, sys_data, on=['Adres', 'Kod'], how='outer').fillna(0)
                fark_df['FARK'] = fark_df['Miktar'] - fark_df['Sistem_Stogu']
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Sayılan", int(fark_df['Miktar'].sum()))
                c2.metric("Sistem Beklenen", int(fark_df['Sistem_Stogu'].sum()))
                c3.metric("Net Fark", int(fark_df['FARK'].sum()), delta=int(fark_df['FARK'].sum()))
                
                # --- HATA ÇÖZÜMÜ: applymap -> map dönüşümü ---
                def color_fark(val):
                    color = 'red' if val < 0 else 'green' if val > 0 else 'gray'
                    return f'color: {color}'
                
                # Pandas sürümüne göre hem map hem applymap desteği
                try:
                    styled_df = fark_df.style.map(color_fark, subset=['FARK'])
                except AttributeError:
                    styled_df = fark_df.style.applymap(color_fark, subset=['FARK'])
                
                st.dataframe(styled_df, use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    fark_df.to_excel(writer, index=False)
                st.download_button("📥 EXCEL İNDİR", output.getvalue(), f"Fark_{secilen}.xlsx")
            else:
                st.warning("⚠️ Snapshot verisinde 'KOD' veya 'MIKTAR' sütunu bulunamadı.")
