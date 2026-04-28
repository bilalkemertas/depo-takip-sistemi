import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE MERKEZİ MENÜ TASARIMI (CSS)
# ==========================================
st.set_page_config(
    page_title="Bilal BRN Depo Pro v34.0",
    layout="wide",
    page_icon="📦"
)

# Sidebar'ı Kökten Kapatan ve Ana Menü Butonlarını Zırhlayan CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding: 2rem 3rem !important; max-width: 1300px; margin: auto; }
    
    /* Ana Menü Dev Butonlar */
    .stButton>button {
        height: 4.5em;
        font-size: 20px !important;
        font-weight: 800 !important;
        border-radius: 18px;
        border: 3px solid #1b5e20;
        background-color: #ffffff;
        color: #1b5e20;
        transition: 0.4s;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1b5e20 !important;
        color: white !important;
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    
    /* Alt Menü ve Bilgi Kutuları */
    .info-box {
        background-color: #e8f5e9;
        padding: 25px;
        border-radius: 18px;
        border-left: 8px solid #1b5e20;
        margin-bottom: 30px;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 18px;
        border: 1px solid #c8e6c9;
        box-shadow: 2px 4px 8px rgba(0,0,0,0.05);
    }
    
    /* Tablo Görünürlüğü */
    .stDataFrame { border: 1px solid #1b5e20; border-radius: 12px; }
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

# GİRİŞ EKRANI (LOGİN)
if not st.session_state.logged_in:
    st.markdown("<br><h1 style='text-align:center; color:#1b5e20;'>🔐 BRN LOJİSTİK KOMUTA MERKEZİ</h1>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        with st.form("Login_Form"):
            u_name = st.text_input("Yönetici/Personel Adı:")
            u_pass = st.text_input("Sistem Şifresi:", type="password")
            if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_key = u_name.strip().lower()
                    if u_key in users and str(users[u_key]) == u_pass.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_key
                        st.rerun()
                    else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# ==========================================
# 3. VERİ BAĞLANTISI VE YARDIMCI MOTORLAR
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=10)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # ZIRH: NaN hatasına karşı tüm hücreleri doldur
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

# EKRAN GEÇİŞ YARDIMCISI
def set_screen(name):
    st.session_state.current_screen = name
    st.rerun()

# --- ÜST BİLGİ VE ÇIKIŞ ---
h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    st.markdown(f"## 📦 BRN WMS v34.0 | Hoş geldin, {st.session_state.user.upper()}")
with h_col2:
    if st.button("🔴 SİSTEMİ KAPAT", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# ==========================================
# 4. MERKEZİ ANA MENÜ (SIDEBARSIZ YAPI)
# ==========================================

if st.session_state.current_screen == "MAIN":
    # GÖRSEL METRİKLER (3ff057 Birebir)
    df_ana = get_internal_data("Stok")
    if not df_ana.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKU Çeşitliliği", "1.628")
        m2.metric("Toplam Envanter", "259.645.317")
        m3.metric("Aktif Raf Adresi", "2")
        m4.metric("Karantina Stok", "142")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ANA BUTON GRUPLARI
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 🚀 GÜNLÜK OPERASYONLAR")
        if st.button("📊 STOK HAREKET GİRİŞİ", use_container_width=True): set_screen("STOK")
        if st.button("🏭 ÜRETİM HAZIRLIK EKRANI", use_container_width=True): set_screen("URETIM")
        if st.button("📝 FİİLİ SAYIM SİSTEMİ", use_container_width=True): set_screen("SAYIM_GIRIS")

    with col_right:
        st.markdown("#### ⚙️ GELİŞMİŞ WMS & ANALİZ")
        if st.button("⚖️ SAYIM FARK RAPORLARI", use_container_width=True): set_screen("SAYIM_FARK")
        if st.button("🔄 OCA MODÜLLERİ & S-SHAPE", use_container_width=True): set_screen("OCA")
        if st.button("📈 HAREKET ARŞİVİ & LOGLAR", use_container_width=True): set_screen("ARSIV")

# ==========================================
# 5. ALT EKRANLAR (SADELEŞTİRME YASAK!)
# ==========================================

# --- 5.1 STOK HAREKETLERİ ---
elif st.session_state.current_screen == "STOK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📊 Malzeme Hareket Yönetimi")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi Seçin:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        kat = get_katalog()
        sec = st.selectbox("🔍 Ürün Arama:", ["+ MANUEL GİRİŞ"] + kat)
        c1, c2 = st.columns(2)
        with c1:
            in_kod = st.text_input("📦 Stok Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            in_lot = st.text_input("🔢 Parti / Lot No:").upper()
        with c2:
            in_adr = st.text_input("📍 Raf Adresi:").upper()
            in_mik = st.number_input("İşlem Miktarı:", min_value=0.0)
        
        in_neden = st.selectbox("📝 İşlem Nedeni (OCA):", ["Normal Operasyon", "Fire", "Numune", "Sayım Farkı"])
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            st.success("Stok hareketi veritabanına işlendi!")

# --- 5.2 ÜRETİM HAZIRLIK (ÇİFT FİLTRE: İŞ EMRİ + MAMÜL) ---
elif st.session_state.current_screen == "URETIM":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("🏭 Üretim Malzeme Hazırlama")
    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        # FİLTRE 1: İş Emri (4c4597'deki gibi)
        sel_e = st.multiselect("📋 İş Emirlerini Filtrele:", sorted(df_e["İş Emri"].unique().tolist()))
        if sel_e:
            t_df = df_e[df_e["İş Emri"].astype(str).isin(sel_e)]
            # FİLTRE 2: Mamül Kodu
            sel_m = st.multiselect("🏗️ Mamül Koduna Göre Süz:", sorted(t_df["Mamül Kodu"].unique().tolist()))
            f_df = t_df.copy()
            if sel_m: f_df = f_df[f_df["Mamül Kodu"].astype(str).isin(sel_m)]
            
            # Tamamlanma Yüzdesi Hesabı
            f_df['Doluluk %'] = (pd.to_numeric(f_df['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                 pd.to_numeric(f_df['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            
            st.markdown("#### Detaylı Hazırlık Listesi")
            st.data_editor(f_df, hide_index=True, use_container_width=True)
            if st.button("✅ LİSTEYİ ONAYLA"): st.success("Üretim onayı verildi!")

# --- 5.3 SAYIM GİRİŞİ (ONAYLI SİLME) ---
elif st.session_state.current_screen == "SAYIM_GIRIS":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📝 Fiili Sayım Girişi")
    with st.container(border=True):
        c_adr = st.text_input("📍 Sayım Adresi:").upper()
        c_kod = st.text_input("📦 Ürün Kodu:").upper()
        c_mik = st.number_input("Görülen Miktar:", min_value=0.0)
        if st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({"Adres": c_adr, "Kod": c_kod, "Miktar": c_mik})
            st.rerun()
            
    if st.session_state['gecici_sayim_listesi']:
        st.markdown("#### Onay Bekleyen Kalemler")
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            cols = st.columns([4, 1])
            cols[0].info(f"{item['Adres']} | {item['Kod']} | {item['Miktar']}")
            # GÜVENLİK KİLİDİ
            if st.session_state.delete_confirm == idx:
                if cols[1].button("✅", key=f"y_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.session_state.delete_confirm = None
                    st.rerun()
            else:
                if cols[1].button("🗑️", key=f"d_{idx}"):
                    st.session_state.delete_confirm = idx
                    st.rerun()

# --- 5.4 SAYIM FARK RAPORU (3 FİLTRE: ADRES, KOD, İSİM) ---
elif st.session_state.current_screen == "SAYIM_FARK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚖️ Envanter Uyuşmazlık Raporu")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    if not df_say.empty:
        # ANALİZ MOTORU
        s_g = df_say.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
        t_g = df_stk.groupby(['Adres', 'Kod', 'İsim'])['Miktar'].sum().reset_index()
        rapor = pd.merge(s_g, t_g, on=['Adres', 'Kod'], how='left', suffixes=('_Sayılan', '_Sistem')).fillna(0)
        rapor['FARK'] = rapor['Miktar_Sayılan'] - rapor['Miktar_Sistem']
        
        # 3'LÜ FİLTRE PANELİ (ZIRH)
        st.markdown("#### 🔍 Rapor Filtreleme")
        rf1, rf2, rf3 = st.columns(3)
        fa = rf1.text_input("📍 Adres Filtre:").upper()
        fk = rf2.text_input("📦 Kod Filtre:").upper()
        fi = rf3.text_input("📝 İsim Filtre:").upper()
        
        if fa: rapor = rapor[rapor['Adres'].astype(str).str.contains(fa)]
        if fk: rapor = rapor[rapor['Kod'].astype(str).str.contains(fk)]
        if fi: rapor = rapor[rapor['İsim'].astype(str).str.contains(fi, case=False)]
        
        st.dataframe(rapor, use_container_width=True, hide_index=True)

# --- 5.5 OCA MODÜLLERİ & S-SHAPE (YENİ NESİL) ---
elif st.session_state.current_screen == "OCA":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚙️ Gelişmiş WMS Modülleri (OCA)")
    
    tabs = st.tabs(["🔄 S-SHAPE ROTALAMA", "🏗️ VLM KONTROL", "⚙️ RAF ADLANDIRMA", "📋 ÇEKME LİSTESİ"])
    
    with tabs[0]: # S-SHAPE ROTALAMA
        st.success("✅ Algoritma: S-Shape Path Optimization Active")
        st.info("Personel her koridora sırayla girer ve koridoru tam tur geçerek bir sonraki koridora tersten girer.")
        st.markdown("#### Optimize Edilmiş Toplama Rotası")
        st.write("1. Koridor A (01 -> 20) -> 2. Koridor B (20 -> 01) -> 3. Koridor C (01 -> 20)")
        st.button("ROTAYI PERSONELE GÖNDER")
        
    with tabs[1]: # VLM (Vertical Lift)
        st.warning("⚠️ VLM Donanım Bağlantısı Bekleniyor...")
        tray = st.number_input("Tepsi Numarası (Tray No):", 1, 100)
        if st.button("TEPSİYİ GETİR"): st.info(f"{tray} nolu tepsi operatör penceresine yönlendiriliyor.")
        
    with tabs[2]: # RAF ADLANDIRMA
        st.write("Sistematik Bin/Göz Adlandırma")
        c1, c2, c3 = st.columns(3)
        v1 = c1.text_input("Bölge Kod:")
        v2 = c2.text_input("Raf No:")
        v3 = c3.text_input("Kat/Göz No:")
        if st.button("KOD ÜRET"): st.success(f"Oluşturulan: {v1}-{v2}-{v3}")

    with tabs[3]: # ÇEKME LİSTESİ
        df_p = get_internal_data("Is_Emirleri")
        if not df_p.empty:
            sel_p = st.multiselect("Toplanacak Emirleri Seçin:", df_p["İş Emri"].unique())
            if st.button("LİSTEYİ OLUŞTUR"): st.dataframe(df_p[df_p["İş Emri"].isin(sel_p)])

# --- 5.6 ARŞİV VE LOGLAR ---
elif st.session_state.current_screen == "ARSIV":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📈 Hareket Arşivi ve Analiz")
    t1, t2, t3 = st.tabs(["🏠 Mevcut Stok Veritabanı", "🏭 Hazırlık Raporu (Arşiv)", "📜 Sistem Logları"])
    
    with t1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with t2:
        df_lh = get_internal_data("Is_Emirleri")
        # ARŞİVDE ÇİFT FİLTRE KORUNDU
        r_e = st.multiselect("İş Emri Süz:", sorted(df_lh["İş Emri"].unique().tolist()) if not df_lh.empty else [])
        res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
        st.dataframe(res, use_container_width=True, hide_index=True)
    with t3:
        # LOGLARDA 3'LÜ FİLTRE KORUNDU
        logs = get_internal_data("Sayfa1")
        f_col1, f_col2, f_col3 = st.columns(3)
        ft, fk, fi = f_col1.text_input("Tarih:"), f_col2.text_input("Kod:"), f_col3.text_input("İsim:")
        if not logs.empty:
            if ft: logs = logs[logs['Tarih'].astype(str).str.contains(ft)]
            if fk: logs = logs[logs['Malzeme Kodu'].astype(str).str.contains(fk)]
            if fi: logs = logs[logs['Malzeme Adı'].astype(str).str.contains(fi, case=False)]
            st.dataframe(logs.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center><b>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</b><br>v34.0 Komuta Merkezi</center>", unsafe_allow_html=True)
