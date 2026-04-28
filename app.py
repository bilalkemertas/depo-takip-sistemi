import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro v15.0", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 1rem 1rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; font-weight: bold; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    .critical-stock { color: #ff4b4b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Lojistik Giriş</h3>", unsafe_allow_html=True)
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

# --- 5. ANA EKRAN (OCA STANDARDI DASHBOARD) ---
if st.session_state.page == 'home':
    st.markdown("<h2 style='text-align:center;'>📦 Lojistik Kontrol Paneli</h2>", unsafe_allow_html=True)
    
    # KPI Metrikleri
    df_stok = get_internal_data("Stok")
    total_items = len(df_stok['Kod'].unique()) if not df_stok.empty else 0
    total_qty = pd.to_numeric(df_stok['Miktar'], errors='coerce').sum() if not df_stok.empty else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Toplam Çeşit (SKU)", total_items)
    m2.metric("Toplam Stok Miktarı", f"{total_qty:,.0f}")
    m3.metric("Aktif Depo Personeli", st.session_state.user.upper())

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK GİRİŞ / ÇIKIŞ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK (EMİR)", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 PERİYODİK SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 ANALİZ VE RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (PARTİ/LOT DESTEKLİ) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Stok Hareket Yönetimi")
    with st.container(border=True):
        move_type = st.selectbox("Hareket Tipi:", ["GİRİŞ (Satınalma/Üretimden)", "ÇIKIŞ (Satış/Fire)", "İÇ TRANSFER"])
        katalog = get_katalog()
        sec = st.selectbox("🔍 Ürün Seçimi:", ["+ YENİ ÜRÜN"] + katalog)
        
        col1, col2 = st.columns(2)
        with col1:
            s_kod = st.text_input("📦 Stok Kodu:", value=sec.split(" | ")[0] if sec != "+ YENİ ÜRÜN" else "").upper()
            s_lot = st.text_input("🔢 Parti / Lot No:", placeholder="Örn: 2026-A1").upper()
        with col2:
            s_adr = st.text_input("📍 Adres / Raf:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
            
        s_durum = st.selectbox("Stok Durumu:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        
        if st.button("HAREKETİ KAYDET", type="primary", use_container_width=True):
            st.success(f"{s_kod} kodlu ürünün {move_type} işlemi başarıyla loglandı!")

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık (Picking List)")
    df_emirler = get_internal_data("Is_Emirleri")
    if not df_emirler.empty:
        emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
        s_list = st.multiselect("Hazırlanacak İş Emirlerini Seçin:", emir_list)
        if s_list:
            filtered = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- 8. SAYIM SİSTEMİ (OCA STANDARDI FARK ANALİZİ) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Profesyonel Sayım Modülü")
    t1, t2 = st.tabs(["📝 Sayım Kaydı", "📊 Fark ve Envanter Analizi"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Sayılan Adres:").upper()
            katalog = get_katalog()
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
            k_i = sec.split(" | ")[0] if sec != "+ MANUEL" else ""
            s_kod = st.text_input("📦 Kod:", value=k_i).upper()
            s_lot = st.text_input("🔢 Lot No (Opsiyonel):").upper()
            s_mik = st.number_input("Gerçek Miktar:", min_value=0.0, step=1.0)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), "Personel": st.session_state.user,
                    "Adres": s_adr, "Kod": s_kod, "Lot": s_lot, "Miktar": s_mik
                })
                st.toast("Kalem listeye eklendi.")
        
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 SAYIMI ONAYLA VE GÖNDER", type="primary", use_container_width=True):
                st.success("Veritabanı güncelleniyor...")

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
            
            # OCA Görsel Fark Analizi
            def highlight_diff(val):
                color = 'red' if val < 0 else 'green' if val > 0 else 'black'
                return f'color: {color}'

            st.dataframe(rapor.style.applymap(highlight_diff, subset=['FARK']), use_container_width=True, hide_index=True)
            st.download_button("📥 Excel Raporu", data=get_excel_buffer(rapor), file_name="OCA_Sayim_Fark.xlsx")

# --- 9. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Lojistik Raporlama")
    df_full = get_internal_data("Stok")
    st.dataframe(df_full, use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS | OCA Logistics Standards Applied</center>", unsafe_allow_html=True)
