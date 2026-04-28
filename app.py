import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
        .row-font { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# --- NAVİGASYON ---
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_sayim(): st.session_state.page = 'sayim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI VE VERİ ÇEKME ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 5. ANA EKRAN (GÜÇLENDİRİLMİŞ METRİKLER) ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    
    df_ana = get_internal_data("Stok")
    m1, m2 = st.columns(2)
    m1.metric("SKU Çeşitliliği", len(df_ana['Kod'].unique()) if not df_ana.empty else 0)
    m2.metric("Toplam Stok", f"{pd.to_numeric(df_ana['Miktar'], errors='coerce').sum() if not df_ana.empty else 0:,.0f}")
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 RAPOR ARŞİVİ", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (OCA EKLEMELİ) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Stok Hareketleri")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        katalog = get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
        col1, col2 = st.columns(2)
        with col1:
            s_kod = st.text_input("📦 Kod:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
            s_lot = st.text_input("🔢 Parti / Lot No:", placeholder="Opsiyonel").upper()
        with col2:
            s_adr = st.text_input("📍 Adres:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
        s_durum = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        if st.button("KAYDET", use_container_width=True, type="primary"):
            st.success("İşlem veritabanına hazır!")

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")
    df_emirler = get_internal_data("Is_Emirleri")
    if not df_emirler.empty:
        emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
        s_list = st.multiselect("İş Emirlerini Seçin:", emir_list)
        if s_list:
            filtered = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- 8. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres:").upper()
            katalog = get_katalog()
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
            k_i = sec.split(" | ")[0] if sec != "+ MANUEL" else ""
            s_kod = st.text_input("📦 Kod:", value=k_i).upper()
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), "Personel": st.session_state.user,
                    "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik
                })
                st.toast("Eklendi")
        
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 KAYDET", type="primary", use_container_width=True):
                eski = get_internal_data("sayim")
                yeni = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([eski, yeni], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veritabanı Güncellendi!"); st.rerun()

    with t2:
        df_sayim = get_internal_data("sayim")
        df_stok = get_internal_data("Stok")
        if not df_sayim.empty:
            df_sayim[['Kod', 'Adres']] = df_sayim[['Kod', 'Adres']].astype(str)
            df_stok[['Kod', 'Adres']] = df_stok[['Kod', 'Adres']].astype(str)
            s_ozet = df_sayim.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
            st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left', suffixes=('_Sayilan', '_Sistem')).fillna(0)
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            rapor = rapor.sort_values(by=['Adres', 'Kod'])
            
            def color_diff(val):
                return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'

            st.metric("Toplam Sayım Farkı", f"{rapor['FARK'].sum():,.0f}")
            st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)
            st.download_button("📥 Fark Raporunu İndir", data=get_excel_buffer(rapor), file_name="Sayim_Fark.xlsx")
        else:
            st.info("Henüz bir sayım verisi bulunmuyor.")

# --- 9. RAPORLAR (ARŞİV GERİ GELDİ) ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Raporlar ve Arşiv")
    rt1, rt2, rt3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Özeti", "📜 Hareket Arşivi"])
    
    with rt1:
        st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            sum_h = df_h.groupby('İş Emri', sort=False)[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            st.dataframe(sum_h, use_container_width=True, hide_index=True)
    with rt3:
        # Arşiv kısmında logları (Sayfa1) en yeniden en eskiye gösteriyoruz
        st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
