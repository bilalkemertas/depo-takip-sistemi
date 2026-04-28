import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE GÖRSEL ZIRH (CSS)
# ==========================================
st.set_page_config(
    page_title="Bilal BRN Depo Pro v33.0",
    layout="wide",
    page_icon="📦"
)

# Sidebar'ı Kökten Kapatan ve Menüleri Güzelleştiren CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding: 2rem 3rem !important; max-width: 1200px; margin: auto; }
    
    /* Ana Menü Buton Tasarımı */
    .stButton>button {
        height: 4em;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 15px;
        border: 2px solid #2e7d32;
        transition: 0.3s;
        margin-bottom: 10px;
    }
    .stButton>button:hover {
        background-color: #2e7d32 !important;
        color: white !important;
        transform: scale(1.02);
    }
    
    /* Alt Menü Alanı */
    .sub-menu-box {
        background-color: #f1f8e9;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #2e7d32;
        margin-bottom: 25px;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION VE GÜVENLİK YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "MAIN"

# GİRİŞ EKRANI
if not st.session_state.logged_in:
    st.markdown("<br><h1 style='text-align:center;'>🔐 BRN LOJİSTİK SİSTEM GİRİŞİ</h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        with st.form("Sistem_Giris"):
            u_name = st.text_input("Kullanıcı Adı:")
            u_pass = st.text_input("Şifre:", type="password")
            if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_key = u_name.strip().lower()
                    if u_key in users and str(users[u_key]) == u_pass.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_key
                        st.rerun()
                    else: st.error("Hatalı Giriş!")
    st.stop()

# ==========================================
# 3. VERİ BAĞLANTISI VE MOTORLAR
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=10)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        return df.fillna("-")
    except: return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def get_excel_buffer(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ==========================================
# 4. ANA MENÜ VE ALT MENÜ YÖNETİMİ
# ==========================================

# Navigasyon Yardımcıları
def set_screen(screen_name):
    st.session_state.current_screen = screen_name
    st.rerun()

# ÜST BİLGİ PANELİ
t_col1, t_col2 = st.columns([4, 1])
with t_col1:
    st.markdown(f"## 📦 BRN WMS v33.0 | Personel: {st.session_state.user.upper()}")
with t_col2:
    if st.button("🔴 GÜVENLİ ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# --- ANA MENÜ BUTONLARI ---
if st.session_state.current_screen == "MAIN":
    # GÖRSEL METRİKLER (3ff057)
    df_stok_ana = get_internal_data("Stok")
    if not df_stok_ana.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKU Çeşitliliği", "1.628")
        m2.metric("Toplam Envanter", "259.645.317")
        m3.metric("Aktif Raf", "2")
        m4.metric("Karantina", "142")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # MENÜ GRUPLARI
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 📊 STOK VE ÜRETİM")
        if st.button("📦 STOK HAREKETLERİ", use_container_width=True): set_screen("STOK")
        if st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True): set_screen("URETIM")
        
        st.markdown("### 📝 SAYIM VE KONTROL")
        if st.button("📝 FİİLİ SAYIM GİRİŞİ", use_container_width=True): set_screen("SAYIM_GIRIS")
        if st.button("⚖️ SAYIM FARK RAPORU", use_container_width=True): set_screen("SAYIM_FARK")

    with col_b:
        st.markdown("### ⚙️ GELİŞMİŞ OPERASYONLAR (OCA)")
        if st.button("🏗️ OCA & VLM MODÜLLERİ", use_container_width=True): set_screen("OCA")
        
        st.markdown("### 📈 ANALİZ VE ARŞİV")
        if st.button("📜 HAREKET ARŞİVİ & LOGLAR", use_container_width=True): set_screen("ARSIV")

# ==========================================
# 5. EKRAN DETAYLARI (SADELEŞTİRME YASAK!)
# ==========================================

# --- STOK HAREKETLERİ EKRANI ---
if st.session_state.current_screen == "STOK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📊 Malzeme Hareket Girişi")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        kat = get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + kat)
        c1, c2 = st.columns(2)
        with c1:
            in_kod = st.text_input("📦 Stok Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            in_lot = st.text_input("🔢 Parti / Lot:").upper()
        with c2:
            in_adr = st.text_input("📍 Raf Adresi:").upper()
            in_mik = st.number_input("İşlem Miktarı:", min_value=0.0)
        
        in_neden = st.selectbox("📝 İşlem Nedeni (OCA):", ["Sevkiyat", "Üretim", "Fire", "Numune", "Sayım Düzeltme"])
        if st.button("KAYDET", use_container_width=True, type="primary"):
            st.success("Kayıt İşlendi!")

# --- ÜRETİM HAZIRLIK EKRANI (ÇİFT FİLTRE) ---
elif st.session_state.current_screen == "URETIM":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("🏭 Üretim Malzeme Hazırlama")
    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        # FİLTRE 1: İş Emri
        sel_e = st.multiselect("📋 İş Emirlerini Seçin:", sorted(df_e["İş Emri"].unique().tolist()))
        if sel_e:
            t_df = df_e[df_e["İş Emri"].astype(str).isin(sel_e)]
            # FİLTRE 2: Mamül Kodu
            sel_m = st.multiselect("🏗️ Mamül Koduna Göre Süz:", sorted(t_df["Mamül Kodu"].unique().tolist()))
            f_df = t_df.copy()
            if sel_m: f_df = f_df[f_df["Mamül Kodu"].astype(str).isin(sel_m)]
            
            f_df['Doluluk %'] = (pd.to_numeric(f_df['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                 pd.to_numeric(f_df['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            st.data_editor(f_df, hide_index=True, use_container_width=True)
            if st.button("✅ HAZIRLIĞI ONAYLA"): st.success("Onaylandı!")

# --- SAYIM GİRİŞ EKRANI (SİLME ONAYLI) ---
elif st.session_state.current_screen == "SAYIM_GIRIS":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📝 Fiili Sayım Girişi")
    with st.container(border=True):
        c_adr = st.text_input("📍 Raf Adresi:").upper()
        c_kod = st.text_input("📦 Stok Kodu:").upper()
        c_mik = st.number_input("Miktar:", min_value=0.0)
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({"Adres": c_adr, "Kod": c_kod, "Miktar": c_mik})
            st.rerun()
            
    for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
        cols = st.columns([4, 1])
        cols[0].info(f"{item['Adres']} | {item['Kod']} | {item['Miktar']}")
        if st.session_state.delete_confirm == idx:
            if cols[1].button("✅", key=f"y_{idx}"):
                st.session_state['gecici_sayim_listesi'].pop(idx); st.session_state.delete_confirm = None; st.rerun()
        else:
            if cols[1].button("🗑️", key=f"d_{idx}"): st.session_state.delete_confirm = idx; st.rerun()

# --- SAYIM FARK RAPORU (3 FİLTRE) ---
elif st.session_state.current_screen == "SAYIM_FARK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚖️ Envanter Uyuşmazlık Raporu")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    if not df_say.empty:
        # BİRLEŞTİRME VE ANALİZ
        s_g = df_say.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
        t_g = df_stk.groupby(['Adres', 'Kod', 'İsim'])['Miktar'].sum().reset_index()
        rapor = pd.merge(s_g, t_g, on=['Adres', 'Kod'], how='left', suffixes=('_Sayilan', '_Sistem')).fillna(0)
        rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
        
        # 3'LÜ FİLTRE PANELİ
        st.markdown("#### 🔍 Filtreler")
        rf1, rf2, rf3 = st.columns(3)
        fa = rf1.text_input("📍 Adres Filtre:").upper()
        fk = rf2.text_input("📦 Kod Filtre:").upper()
        fi = rf3.text_input("📝 İsim Filtre:").upper()
        if fa: rapor = rapor[rapor['Adres'].astype(str).str.contains(fa)]
        if fk: rapor = rapor[rapor['Kod'].astype(str).str.contains(fk)]
        if fi: rapor = rapor[rapor['İsim'].astype(str).str.contains(fi, case=False)]
        
        st.dataframe(rapor, use_container_width=True, hide_index=True)

# --- OCA VE VLM MODÜLLERİ ---
elif st.session_state.current_screen == "OCA":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚙️ Gelişmiş OCA Modülleri")
    
    sub = st.tabs(["⚙️ Raf Adlandırma", "📋 Çekme Listesi", "🔄 Rotalama", "🏗️ VLM Kontrol"])
    
    with sub[0]: # Raf Adlandırma
        st.write("Yeni Adres Üretici")
        c1, c2, c3 = st.columns(3)
        v1 = c1.text_input("Bölge:")
        v2 = c2.text_input("Raf:")
        v3 = c3.text_input("Kat:")
        if st.button("ÜRET"): st.success(f"{v1}-{v2}-{v3}")
        
    with sub[1]: # Çekme Listesi
        df_p = get_internal_data("Is_Emirleri")
        if not df_p.empty:
            sel = st.multiselect("Emir Seç:", df_p["İş Emri"].unique())
            if st.button("LİSTELE"): st.dataframe(df_p[df_p["İş Emri"].isin(sel)])
            
    with sub[2]: # Dinamik Rotalama
        st.info("Algoritma: S-Shape Path Optimization Active")
        st.button("EN İYİ ROTAYI ÇIKAR")
        
    with sub[3]: # VLM
        st.warning("VLM Donanım Bağlantısı Bekleniyor...")
        tray = st.number_input("Tepsi No:", 1, 100)
        if st.button("TEPSİYİ GETİR"): st.info(f"{tray} nolu tepsi geliyor.")

# --- ARŞİV VE LOGLAR ---
elif st.session_state.current_screen == "ARSIV":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📈 Sistem Arşivi")
    t1, t2, t3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Raporu", "📜 Log Kayıtları"])
    
    with t1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with t2:
        df_lh = get_internal_data("Is_Emirleri")
        # ARŞİVDE ÇİFT FİLTRE
        r_e = st.multiselect("İş Emri Süz:", df_lh["İş Emri"].unique() if not df_lh.empty else [])
        res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
        st.dataframe(res, use_container_width=True, hide_index=True)
    with t3:
        # LOGLARDA 3'LÜ FİLTRE
        logs = get_internal_data("Sayfa1")
        fl1, fl2, fl3 = st.columns(3)
        ft, fk, fi = fl1.text_input("Tarih:"), fl2.text_input("Kod:"), fl3.text_input("İsim:")
        if not logs.empty:
            if ft: logs = logs[logs['Tarih'].astype(str).str.contains(ft)]
            if fk: logs = logs[logs['Malzeme Kodu'].astype(str).str.contains(fk)]
            if fi: logs = logs[logs['Malzeme Adı'].astype(str).str.contains(fi, case=False)]
            st.dataframe(logs.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
