import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI VE MOBİL CSS ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    .stDataFrame { width: 100% !important; overflow-x: auto !important; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
        .row-font { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = None

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                if u_raw.strip().lower() in users and str(users[u_raw.strip().lower()]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_raw.lower()
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# --- 3. BAĞLANTI VE YARDIMCI FONKSİYONLAR ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty: return dict(zip(df['Kod'].astype(str), df['İsim'].astype(str)))
    return {}

# --- 4. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary"): st.session_state.page = 'stok'; st.rerun()
        if st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary"): st.session_state.page = 'uretim'; st.rerun()
    with c2:
        if st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary"): st.session_state.page = 'sayim'; st.rerun()
        if st.button("📈 GENEL RAPORLAR", use_container_width=True, type="primary"): st.session_state.page = 'rapor'; st.rerun()
    if st.sidebar.button("Güvenli Çıkış"): st.session_state.clear(); st.rerun()

# --- 5. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres").upper()
            s_kod = st.selectbox("📦 Kod", [""] + sorted(list(kod_map.keys())))
            st.caption(f"Ürün Adı: {kod_map.get(s_kod, 'Seçilmedi')}")
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user, "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""), "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast("Eklendi")
                else: st.warning("Adres ve Kod zorunludur!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyenler")
            h_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
            h_cols[0].write("**Adres**"); h_cols[1].write("**Kod**"); h_cols[2].write("**Ürün**")
            h_cols[3].write("**Mik.**"); h_cols[4].write("**Durum**"); h_cols[5].write("**Sil**")
            st.markdown("---")

            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
                r_cols[0].write(item['Adres'])
                r_cols[1].write(item['Kod'])
                r_cols[2].markdown(f"<p class='row-font'>{item['Ürün Adı'][:15]}</p>", unsafe_allow_html=True)
                r_cols[3].write(str(item['Miktar']))
                r_cols[4].write(item['Durum'])
                
                # GÜVENLİ SİLME
                if st.session_state.delete_confirm == idx:
                    c_del, c_esc = r_cols[5].columns(2)
                    if c_del.button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx)
                        st.session_state.delete_confirm = None
                        st.rerun()
                    if c_esc.button("❌", key=f"esc_{idx}"):
                        st.session_state.delete_confirm = None
                        st.rerun()
                else:
                    if r_cols[5].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx
                        st.rerun()
            
            if st.button("📤 DRIVE'A KAYDET", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.success("Kaydedildi!"); st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Filtreler", expanded=True):
                    f_t = st.selectbox("📅 Tarih", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    c_f1, c_f2 = st.columns(2)
                    sel_k = c_f1.multiselect("📦 Kod", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = c_f2.multiselect("📍 Adres", sorted(df_s_db["Adres"].unique().tolist()))

                act = df_s_db.copy()
                if f_t != "Tümü": act = act[act["Tarih"] == f_t]
                if sel_k: act = act[act["Kod"].isin(sel_k)]
                if sel_a: act = act[act["Adres"].isin(sel_a)]

                if not act.empty:
                    say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı'])['Miktar'].sum().reset_index()
                    sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                    res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                    res.columns = ["Adres", "Kod", "Ürün Adı", "Sayılan", "Sistem"]
                    res['FARK'] = res['Sayılan'] - res['Sistem']
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Sayılan", f"{res['Sayılan'].sum():,.0f}")
                    m2.metric("Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
                    
                    # HATA DÜZELTME: applymap yerine map kullanıldı
                    st.dataframe(res.style.map(lambda v: 'color:red; font-weight:bold' if v < 0 else 'color:green; font-weight:bold' if v > 0 else '', subset=['FARK']), use_container_width=True, hide_index=True)
            else: st.info("Sayım verisi yok.")
        except Exception as e: st.error(f"Rapor Hatası: {e}")

# Diğer ekranlar...
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.subheader("📦 Stok İşlemleri")

elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.subheader("🏭 Üretim Hazırlık")

elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.subheader("📈 Genel Raporlar")
    t1, t2 = st.tabs(["Stok Listesi", "Hareket Arşivi"])
    with t1: st.dataframe(get_internal_data("Stok"), use_container_width=True)
    with t2: st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
