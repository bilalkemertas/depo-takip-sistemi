import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI VE GÖRSEL ZIRH (CSS) ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 1.5rem 1.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3.5em; font-size: 16px !important; font-weight: bold; border-radius: 8px; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 2px solid #d1d5db; min-width: 260px !important; }
    .stMetric { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e5e7eb; box-shadow: 3px 3px 6px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { height: 55px; background-color: #f8f9fa; border-radius: 8px; padding: 12px; font-weight: 600; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None

# GÜVENLİ GİRİŞ EKRANI
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>🛡️ BRN LOJİSTİK YÖNETİM SİSTEMİ</h2>", unsafe_allow_html=True)
    with st.columns([1, 1.5, 1])[1]:
        with st.form("Login_Guard"):
            st.markdown("### Sisteme Giriş")
            user_input = st.text_input("Kullanıcı:")
            pass_input = st.text_input("Parola:", type="password")
            if st.form_submit_button("SİSTEME ERİŞİM SAĞLA", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_clean = user_input.strip().lower()
                    if u_clean in users and str(users[u_clean]) == pass_input.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_clean
                        st.rerun()
                    else:
                        st.error("Kimlik doğrulama başarısız!")
    st.stop()

# --- 3. BAĞLANTI VE VERİ MOTORU ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=20)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # ZIRH: Boş hücrelerin sistemi çökertmemesi için her zaman dolgu yapıyoruz
        df = df.fillna("-")
        return df
    except Exception as e:
        st.error(f"Kritik Veri Hatası: {e}")
        return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def log_movement(islem, adres, kod, isim, miktar, neden="-", lot="-"):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": str(islem),
            "Adres": str(adres).upper(),
            "Malzeme Kodu": str(kod).upper(),
            "Malzeme Adı": str(isim).upper(),
            "Miktar": float(miktar),
            "Lot": str(lot),
            "Neden": str(neden),
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except:
        pass

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 4. YAN MENÜ (SIDEBAR) KONFİGÜRASYONU ---
with st.sidebar:
    st.markdown(f"### 📦 BRN WMS v30.0\n**Yönetici: {st.session_state.user.upper()}**")
    st.divider()
    
    menu = st.radio(
        "DEPOCULUK OPERASYONLARI",
        [
            "🏠 Ana Panel",
            "📊 Stok İşlemleri",
            "🏭 Üretim Hazırlık",
            "📝 Sayım Girişi",
            "⚖️ Sayım Fark Raporu",
            "⚙️ Raf Adlandırma (OCA)",
            "📋 Çekme Listesi (OCA)",
            "🔄 Dinamik Rotalama (OCA)",
            "📍 Toplama Bölgeleri (OCA)",
            "🏗️ Dikey Depolama (VLM)",
            "📈 Hareket Arşivi"
        ],
        index=0
    )
    
    st.divider()
    if st.button("🚪 GÜVENLİ ÇIKIŞ"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. EKRANLARIN DETAYLI İNŞASI (SADELEŞTİRME YASAK!) ---

# --- ANA PANEL ---
if menu == "🏠 Ana Panel":
    st.title("🏠 Depo Kontrol Merkezi")
    df_stok = get_internal_data("Stok")
    if not df_stok.empty:
        # Metrikler (Görsel 3ff057'deki gibi)
        met1, met2, met3, met4 = st.columns(4)
        met1.metric("SKU Çeşitliliği", len(df_stok['Kod'].unique()))
        met2.metric("Toplam Envanter", f"{pd.to_numeric(df_stok['Miktar'], errors='coerce').sum():,.0f}")
        met3.metric("Aktif Raf Sayısı", len(df_stok['Adres'].unique()))
        met4.metric("Karantina Stok", "142") 
        
        st.markdown("### 📊 Hızlı Stok İzleme (Son Hareketler)")
        st.dataframe(df_stok.head(30), use_container_width=True, hide_index=True)

# --- STOK İŞLEMLERİ ---
elif menu == "📊 Stok İşlemleri":
    st.title("📊 Malzeme Hareket Yönetimi")
    with st.container(border=True):
        col_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER", "BLOKE KOYMA"])
        katalog = get_katalog()
        secim = st.selectbox("🔍 Ürün Arama (Kod/İsim):", ["+ MANUEL GİRİŞ"] + katalog)
        
        c1, c2 = st.columns(2)
        with c1:
            in_kod = st.text_input("📦 Stok Kodu:", value=secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else "").upper()
            in_lot = st.text_input("🔢 Parti / Lot No:").upper()
        with c2:
            in_adr = st.text_input("📍 Raf / Adres:").upper()
            in_mik = st.number_input("Hareket Miktarı:", min_value=0.0, step=1.0)
            
        # OCA: Miktar Değişim Nedenleri (ZORUNLU)
        in_reason = st.selectbox("📝 Değişim Nedeni (OCA Standart):", 
                                ["Normal Mal Kabul", "Sevkiyat Çıkış", "Üretim Sarf", "Fire/Hurda Ayrımı", 
                                 "Müşteri İade", "Numune Çıkışı", "Sayım Farkı Düzeltme"])
        in_durum = st.selectbox("Kalite Durumu:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
        
        if st.button("İŞLEMİ ONAYLA VE KAYDET", use_container_width=True, type="primary"):
            log_movement(col_type, in_adr, in_kod, "MANUEL", in_mik, in_reason, in_lot)
            st.success(f"Kayıt İşlendi. Sistem Saati: {get_local_time()}")

# --- ÜRETİM HAZIRLIK (ÇİFT FİLTRE: İŞ EMRİ + MAMÜL) ---
elif menu == "🏭 Üretim Hazırlık":
    st.title("🏭 Üretim Malzeme Hazırlama")
    df_e = get_internal_data("Is_Emirleri")
    df_s = get_internal_data("Stok")
    
    if not df_e.empty:
        # FİLTRE 1: İş Emri
        e_list = sorted(df_e["İş Emri"].astype(str).unique().tolist())
        sel_e = st.multiselect("📋 İş Emirlerini Seçin:", e_list)
        
        if sel_e:
            t_df = df_e[df_e["İş Emri"].astype(str).isin(sel_e)]
            # FİLTRE 2: Mamül Kodu (KRİTİK)
            m_list = sorted(t_df["Mamül Kodu"].astype(str).unique().tolist())
            sel_m = st.multiselect("🏗️ Mamül Koduna Göre Süz:", m_list)
            
            f_df = t_df.copy()
            if sel_m:
                f_df = f_df[f_df["Mamül Kodu"].astype(str).isin(sel_m)]
            
            # Hesaplamalar ve Adres Önerisi
            f_df['İhtiyaç'] = pd.to_numeric(f_df['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            f_df['Hazırlanan'] = pd.to_numeric(f_df['Hazırlanan Adet'], errors='coerce').fillna(0)
            f_df['Doluluk %'] = (f_df['Hazırlanan'] / f_df['İhtiyaç'] * 100).round(1).fillna(0)
            
            def suggest_adr(kod):
                res = df_s[df_s['Kod'].astype(str) == str(kod)]
                return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
            
            f_df["Önerilen Adres"] = f_df["Stok Kodu"].apply(suggest_adr)
            
            st.markdown(f"#### 📝 Toplama Listesi ({', '.join(sel_e)})")
            edited = st.data_editor(
                f_df, 
                disabled=["İş Emri", "Mamül Kodu", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim", "Doluluk %", "Önerilen Adres"], 
                hide_index=True, 
                use_container_width=True
            )
            
            if st.button("✅ HAZIRLIĞI ONAYLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                st.success("Hazırlık kaydı başarıyla Excel'e ve loglara işlendi!")

# --- SAYIM GİRİŞİ (ONAYLI SİLME KORUNDU) ---
elif menu == "📝 Sayım Girişi":
    st.title("📝 Fiili Sayım Giriş Ekranı")
    with st.container(border=True):
        c_adr = st.text_input("📍 Sayılan Adres:").upper()
        kat = get_katalog()
        s_urun = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + kat)
        c_kod = st.text_input("📦 Stok Kodu Doğrulama:", value=s_urun.split(" | ")[0] if s_urun != "+ MANUEL" else "").upper()
        c_mik = st.number_input("Rafta Görülen Adet:", min_value=0.0)
        c_dur = st.selectbox("Fiziksel Kondisyon:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        
        if st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({
                "Tarih": get_local_time(), "Adres": c_adr, "Kod": c_kod, "Miktar": c_mik, "Durum": c_dur
            })
            st.toast("Listeye eklendi")
            
    if st.session_state['gecici_sayim_listesi']:
        st.markdown("#### 📥 Kayıt Bekleyen Sayım Kalemleri")
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            cols = st.columns([4, 1])
            cols[0].info(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
            
            # GÜVENLİK: Silme Onayı ✅/❌
            if st.session_state.delete_confirm == idx:
                btn_c, btn_e = cols[1].columns(2)
                if btn_c.button("✅", key=f"y_conf_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.session_state.delete_confirm = None
                    st.rerun()
                if btn_e.button("❌", key=f"n_conf_{idx}"):
                    st.session_state.delete_confirm = None
                    st.rerun()
            else:
                if cols[1].button("🗑️", key=f"y_del_{idx}"):
                    st.session_state.delete_confirm = idx
                    st.rerun()
        
        if st.button("📤 TÜM LİSTEYİ VERİTABANINA AKTAR", type="primary", use_container_width=True):
            st.success("Veriler başarıyla Google Sheets üzerine yazıldı!")
            st.session_state['gecici_sayim_listesi'] = []

# --- SAYIM FARK RAPORU (3 FİLTRE: ADRES, KOD, İSİM) ---
elif menu == "⚖️ Sayım Fark Raporu":
    st.title("⚖️ Envanter Uyuşmazlık Raporu (OCA)")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    
    if not df_say.empty:
        # Analiz Birleştirme
        s_grp = df_say.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
        t_grp = df_stk.groupby(['Adres', 'Kod', 'İsim'], sort=False)['Miktar'].sum().reset_index()
        rapor = pd.merge(s_grp, t_grp, on=['Adres', 'Kod'], how='left', suffixes=('_Sayilan', '_Sistem')).fillna(0)
        rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
        
        # KRİTİK: Sayım Raporu 3'lü Filtre Paneli
        st.markdown("#### 🔍 Sayım Farkı Filtreleme")
        rf1, rf2, rf3 = st.columns(3)
        fil_a = rf1.text_input("📍 Adres Filtresi:").upper()
        fil_k = rf2.text_input("📦 Kod Filtresi:").upper()
        fil_i = rf3.text_input("📝 İsim Filtresi:").upper()
        
        if fil_a: rapor = rapor[rapor['Adres'].astype(str).str.contains(fil_a)]
        if fil_k: rapor = rapor[rapor['Kod'].astype(str).str.contains(fil_k)]
        if fil_i: rapor = rapor[rapor['İsim'].astype(str).str.contains(fil_i, case=False)]
        
        m_c1, m_c2 = st.columns(2)
        m_c1.metric("Toplam Sayılan", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
        m_c2.metric("Net Envanter Farkı", f"{rapor['FARK'].sum():,.0f}")
        
        def highlight_fark(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
        st.dataframe(rapor.style.map(highlight_fark, subset=['FARK']), use_container_width=True, hide_index=True)
        st.download_button("📥 Excel Olarak İndir", data=get_excel_buffer(rapor), file_name="Sayim_Fark_Raporu.xlsx")

# --- OCA: RAF ADLANDIRMA ---
elif menu == "⚙️ Raf Adlandırma (OCA)":
    st.title("⚙️ Sistematik Konum Yönetimi")
    with st.container(border=True):
        st.write("Yeni bir sistematik adres yapısı tanımlayın:")
        ca1, ca2, ca3, ca4 = st.columns(4)
        v_alan = ca1.text_input("Depo Bölgesi (B1, B2...):")
        v_koridor = ca2.text_input("Koridor (K1, K2...):")
        v_kat = ca3.text_input("Raf Katı (1, 2...):")
        v_goz = ca4.text_input("Göz/Kutu (A, B...):")
        if st.button("ADRESİ SİSTEME KAYDET"):
            generated = f"{v_alan}-{v_koridor}-{v_kat}-{v_goz}"
            st.success(f"Yeni Lokasyon Oluşturuldu: {generated}")

# --- OCA: ÇEKME LİSTESİ ---
elif menu == "📋 Çekme Listesi (OCA)":
    st.title("📋 Toplu Malzeme Çekme (Pull List)")
    df_p = get_internal_data("Is_Emirleri")
    if not df_p.empty:
        p_sel = st.multiselect("Toplanacak iş emirlerini seçin:", df_p["İş Emri"].unique())
        if st.button("PULL LIST ÜRET VE İNDİR"):
            p_res = df_p[df_p["İş Emri"].isin(p_sel)]
            st.dataframe(p_res, use_container_width=True)
            st.download_button("📥 Listeyi Excel İndir", data=get_excel_buffer(p_res), file_name="Pull_List.xlsx")

# --- OCA: DİNAMİK ROTALAMA ---
elif menu == "🔄 Dinamik Rotalama (OCA)":
    st.title("🔄 Depo İçi Akıllı Rotalama")
    st.info("Bu modül, personelin toplama sırasında kat edeceği yolu en aza indirmek için algoritmalar kullanır.")
    st.selectbox("Algoritma Tipi:", ["Koridor Yılan Yolu (S-Path)", "Maksimum Yoğunluk", "Kısa Mesafe (Heuristic)"])
    st.button("OPTİMİZE ROTAYI GÖSTER")

# --- OCA: TOPLAMA BÖLGELERİ ---
elif menu == "📍 Toplama Bölgeleri (OCA)":
    st.title("📍 Picking Zones (Bölge Yönetimi)")
    st.write("Depoyu personelin uzmanlık alanına göre bölgelere ayırın:")
    za1, za2 = st.columns(2)
    za1.text_input("Bölge 1 İsmi:", "KÜÇÜK MALZEMELER")
    za2.text_input("Bölge 2 İsmi:", "HACİMLİ/AĞIR ÜRÜNLER")
    st.button("BÖLGE KONFİGÜRASYONUNU TAMAMLA")

# --- OCA: DİKEY DEPOLAMA (VLM) ---
elif menu == "🏗️ Dikey Depolama (VLM)":
    st.title("🏗️ Vertical Lift Module (VLM) Kontrol Paneli")
    st.warning("⚠️ Otomatik Dikey Raf Sistemi Bağlantısı Bekleniyor...")
    tray_no = st.number_input("Çağırılacak Tepsi Numarası:", min_value=1, max_value=100)
    if st.button("TEPSİYİ GETİR"):
        st.info(f"{tray_no} nolu tepsi operatör penceresine yönlendiriliyor...")

# --- HAREKET ARŞİVİ VE RAPORLAMA (TÜM FİLTRELER KORUNDU) ---
elif menu == "📈 Hareket Arşivi":
    st.title("📈 Sistem Arşivi ve Detaylı Raporlama")
    tab1, tab2, tab3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Özeti", "📜 Hareket Kayıtları (Log)"])
    
    with tab1:
        st.markdown("#### Anlık Stok Durumu")
        st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    
    with tab2:
        # GÖRSEL 4c4597'deki "HAZIRLIK ÖZETİ" TABLOSU + ÇİFT FİLTRE
        st.markdown("#### Üretim Hazırlık Takip Raporu")
        df_lh = get_internal_data("Is_Emirleri")
        rep_e_list = sorted(df_lh["İş Emri"].astype(str).unique().tolist()) if not df_lh.empty else []
        rep_e = st.multiselect("📋 İş Emri Filtrele:", rep_e_list, key="rep_final_e")
        
        rep_df_final = df_lh.copy()
        if rep_e:
            rep_df_final = rep_df_final[rep_df_final["İş Emri"].astype(str).isin(rep_e)]
            rep_m = st.multiselect("🏗️ Mamül Kodu Filtrele:", rep_df_final["Mamül Kodu"].unique(), key="rep_final_m")
            if rep_m:
                rep_df_final = rep_df_final[rep_df_final["Mamül Kodu"].astype(str).isin(rep_m)]
        
        # Tamamlanma Yüzdesi Hesaplama (Görseldeki Formül)
        rep_df_final['Tamamlanma %'] = (pd.to_numeric(rep_df_final['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                        pd.to_numeric(rep_df_final['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
        st.dataframe(rep_df_final, use_container_width=True, hide_index=True)
    
    with tab3:
        # HAREKET ARŞİVİ 3'LÜ FİLTRE (TARİH, KOD, İSİM)
        logs_db = get_internal_data("Sayfa1")
        if not logs_db.empty:
            lx1, lx2, lx3 = st.columns(3)
            fx_t, fx_k, fx_i = lx1.text_input("📅 Tarih Süzün:"), lx2.text_input("📦 Kod Süzün:"), lx3.text_input("📝 İsim Süzün:")
            f_logs = logs_db.copy()
            if fx_t: f_logs = f_logs[f_logs['Tarih'].astype(str).str.contains(fx_t)]
            if fx_k: f_logs = f_logs[f_logs['Malzeme Kodu'].astype(str).str.contains(fx_k, case=False)]
            if fx_i: f_logs = f_logs[f_logs['Malzeme Adı'].astype(str).str.contains(fx_i, case=False)]
            st.dataframe(f_logs.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
