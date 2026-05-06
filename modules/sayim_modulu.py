import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime

def get_db_connection():
    """SQLite veritabanı bağlantısını kurar."""
    return sqlite3.connect('depo.db', check_same_thread=False)

def go_sayim_menu(): st.session_state.sayim_page = 'menu'
def go_oturum(): st.session_state.sayim_page = 'oturum'
def go_giris(): st.session_state.sayim_page = 'giris'
def go_rapor(): st.session_state.sayim_page = 'rapor'

def init_sayim_tables(db):
    """Sayım tabloları veritabanında yoksa otomatik oluşturur."""
    db.execute('''CREATE TABLE IF NOT EXISTS sayim_snapshot 
                  (Oturum_Adi TEXT, Adres TEXT, Kod TEXT, İsim TEXT, Sistem_Stogu REAL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS sayim 
                  (Oturum_Adi TEXT, Tarih TEXT, Adres TEXT, Kod TEXT, Miktar REAL, Personel TEXT)''')
    db.commit()

def run():
    # Sayfa içi yönlendirme state'leri
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    if 'aktif_sayim_adi' not in st.session_state: st.session_state.aktif_sayim_adi = None
    if 'sayim_page' not in st.session_state: st.session_state.sayim_page = 'menu'

    db = get_db_connection()
    init_sayim_tables(db)

    # --- 0. ANA MENÜ ---
    if st.session_state.sayim_page == 'menu':
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
        
        if st.session_state.aktif_sayim_adi is None:
            st.markdown("### 🆕 Yeni Sayım Başlat")
            sayim_etiketi = st.text_input("Oturum Adı (Örn: Depo_A_Sayimi):")
            if st.button("🚀 SAYIMI BAŞLAT", use_container_width=True, type="primary"):
                if sayim_etiketi:
                    yeni_id = f"{sayim_etiketi}_{datetime.now().strftime('%d%m_%H%M')}"
                    
                    try:
                        # SQLite'dan Stok tablosunun anlık görüntüsünü (snapshot) al
                        df_anlik = pd.read_sql("SELECT Adres, Kod, İsim, Miktar as Sistem_Stogu FROM Stok", db)
                        if not df_anlik.empty:
                            df_anlik['Oturum_Adi'] = yeni_id
                            df_anlik.to_sql("sayim_snapshot", db, if_exists="append", index=False)
                        st.session_state.aktif_sayim_adi = yeni_id
                        st.success(f"Oturum Başladı: {yeni_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Snapshot alınırken hata oluştu (Stok tablosu boş olabilir): {e}")
                else:
                    st.warning("Lütfen bir oturum adı girin.")
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
                if s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Oturum_Adi": st.session_state.aktif_sayim_adi,
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik,
                        "Personel": st.session_state.get('user', 'Patron')
                    })
        
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']))
            if st.button("💾 VERİTABANINA KAYDET", type="primary"):
                try:
                    df_yeni = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                    df_yeni.to_sql("sayim", db, if_exists="append", index=False)
                    st.session_state['gecici_sayim_listesi'] = []
                    st.success("✅ Sayımlar SQLite veritabanına kaydedildi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kayıt Hatası: {e}")

    # --- 3. FARK RAPORU ---
    elif st.session_state.sayim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        st.subheader("📊 Sayım Fark Raporu")
        
        try:
            df_sayim = pd.read_sql("SELECT * FROM sayim", db)
            df_snap = pd.read_sql("SELECT * FROM sayim_snapshot", db)
        except:
            st.error("❌ Henüz kayıtlı bir sayım veya snapshot bulunamadı.")
            return
        
        if not df_sayim.empty:
            oturumlar = df_sayim['Oturum_Adi'].unique().tolist()
            secilen = st.selectbox("Analiz edilecek oturum:", oturumlar)
            
            # Sayılanları topla
            s_data = df_sayim[df_sayim['Oturum_Adi'] == secilen].groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            # Snapshot'u getir
            sys_data = df_snap[df_snap['Oturum_Adi'] == secilen].groupby(['Adres', 'Kod'])['Sistem_Stogu'].sum().reset_index()
            
            # İkisini birleştir ve farkı bul
            fark_df = pd.merge(s_data, sys_data, on=['Adres', 'Kod'], how='outer').fillna(0)
            fark_df['FARK'] = fark_df['Miktar'] - fark_df['Sistem_Stogu']
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Sayılan", int(fark_df['Miktar'].sum()))
            c2.metric("Sistem Beklenen", int(fark_df['Sistem_Stogu'].sum()))
            c3.metric("Net Fark", int(fark_df['FARK'].sum()), delta=int(fark_df['FARK'].sum()))
            
            def color_fark(val):
                color = 'red' if val < 0 else 'green' if val > 0 else 'gray'
                return f'color: {color}'
            
            # Yeni Pandas Sürümüne Uyumlu Formatlama
            try:
                styled_df = fark_df.style.map(color_fark, subset=['FARK'])
            except AttributeError:
                styled_df = fark_df.style.applymap(color_fark, subset=['FARK'])
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Excel İndirme
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                fark_df.to_excel(writer, index=False)
            st.download_button("📥 EXCEL İNDİR", output.getvalue(), f"Fark_Raporu_{secilen}.xlsx")

    # Veritabanı bağlantısını kapat
    db.close()
