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
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None

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

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. YARDIMCI FONKSİYONLAR & PERFORMANS MOTORU ---
@st.cache_data(ttl=60)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        if worksheet_name == "Is_Emirleri" and not df.empty:
            for col in ["Birim", "Mamül Kodu", "Mamül Adı"]:
                if col not in df.columns: df[col] = "ADET" if col == "Birim" else "-"
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    try:
        df = get_internal_data("Urun_Listesi")
        k_col_check = next((c for c in df.columns if "KOD" in str(c).upper()), None) if not df.empty else None
        
        if df.empty or not k_col_check:
            df = get_internal_data("Stok")
            
        if not df.empty:
            k_col = next((c for c in df.columns if "KOD" in str(c).upper()), 'Kod')
            i_col = next((c for c in df.columns if any(x in str(c).upper() for x in ["AD", "İSİM", "ISIM"])), 'İsim')
            
            df['Kod'] = df[k_col].astype(str).str.strip().str.upper()
            df['İsim'] = df[i_col].astype(str).str.strip().str.upper()
            return dict(zip(df['Kod'], df['İsim']))
    except: pass
    return {}

@st.cache_data(ttl=60)
def get_katalog():
    try:
        df_master = get_internal_data("Urun_Listesi")
        k_col_check = next((c for c in df_master.columns if "KOD" in str(c).upper()), None) if not df_master.empty else None
        
        if df_master.empty or not k_col_check:
            df_master = get_internal_data("Stok")
            
        if not df_master.empty:
            k_col = next((c for c in df_master.columns if "KOD" in str(c).upper()), 'Kod')
            i_col = next((c for c in df_master.columns if any(x in str(c).upper() for x in ["AD", "İSİM", "ISIM"])), 'İsim')
            
            df_master['Kod'] = df_master[k_col].astype(str).str.strip().str.upper()
            df_master['İsim'] = df_master[i_col].astype(str).str.strip().str.upper()
            df_master['Arama'] = df_master['Kod'] + " | " + df_master['İsim']
            
            liste = [x for x in df_master['Arama'].unique() if "|" in str(x) and "NAN" not in str(x)]
            return df_master, sorted(liste)
    except: pass
    return pd.DataFrame(), []

def find_name_by_code(kod):
    if not kod: return ""
    kod_str = str(kod).strip().upper()
    return get_kod_map().get(kod_str, "")

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def check_address_stock(kod, adres, miktar):
    df = get_internal_data("Stok")
    if adres == "STOK YOK": return False, 0
    df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
    df['Adres'] = df['Adres'].astype(str).str.strip().str.upper()
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    
    kod_str = str(kod).strip().upper()
    adr_str = str(adres).strip().upper()
    current = df[(df['Kod'] == kod_str) & (df['Adres'] == adr_str)]['Miktar'].sum()
    return current >= miktar, current

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": str(islem),
            "Adres": str(adres).upper(),
            "Malzeme Kodu": str(kod).upper(),
            "Malzeme Adı": isim if isim else find_name_by_code(kod),
            "Miktar": float(miktar),
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except Exception as e:
        st.error(f"Sisteme Log Yazılamadı: {e}")

def update_stock_record(kod, isim, adres, miktar, is_increase=True):
    kod_str = str(kod).strip().upper()
    adr_str = str(adres).strip().upper()
    hedef_adres = "GENEL" if adr_str == "STOK YOK" else adr_str
    
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    stok_df['Kod'] = stok_df['Kod'].astype(str).str.strip().str.upper()
    stok_df['Adres'] = stok_df['Adres'].astype(str).str.strip().str.upper()
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    
    mask = (stok_df['Kod'] == kod_str) & (stok_df['Adres'] == hedef_adres)
    
    if mask.any():
        if is_increase: 
            stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: 
            stok_df.loc[mask, 'Miktar'] = (stok_df.loc[mask, 'Miktar'] - float(miktar)).clip(lower=0)
    elif is_increase:
        gercek_isim = isim if isim else find_name_by_code(kod_str)
        new_row = pd.DataFrame([{"Adres": hedef_adres, "Kod": kod_str, "İsim": gercek_isim, "Birim": "ADET", "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)
    
    get_internal_data.clear()
    get_kod_map.clear()
    get_katalog.clear()
    
    return hedef_adres

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ", key="nav_s"): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 Giriş/Çıkış", "🔄 Transfer", "🔍 Stok Sorgu"])
    stok_df_all, katalog_list = get_katalog()
    
    with t1:
        is_t = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"], key="st_is_t")
        sec = st.selectbox("🔍 Ürün Seç (Kod/İsim):", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_is_s")
        is_manuel = (sec == "+ MANUEL GİRİŞ")
        
        k_i = sec.split(" | ")[0] if not is_manuel else ""
        i_i = sec.split(" | ")[1] if not is_manuel else ""
        
        kod = st.text_input("Stok Kodu:", value=k_i, key="st_is_k").strip().upper()
        isim = st.text_input("Stok Adı:", value=i_i if i_i else find_name_by_code(kod), key="st_is_i").strip().upper()
        
        adr = st.text_input("Adres:", value="GENEL", key="st_is_a").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, step=1.0, key="st_is_q")
        if st.button("KAYDET", use_container_width=True, type="primary", key="st_is_btn"):
            f_kod = kod if kod else k_i
            f_isim = isim if isim else i_i
            
            if is_t == "ÇIKIŞ":
                ok, mev = check_address_stock(f_kod, adr, qty)
                if not ok: st.error(f"Yetersiz Stok! Mevcut: {mev}"); st.stop()
            update_stock_record(f_kod, f_isim, adr, qty, is_increase=(is_t == "GİRİŞ"))
            log_movement(is_t, adr, f_kod, f_isim, qty)
            st.success("İşlem Başarılı!")

    with t2:
        e_adr = st.text_input("Nereden:", key="st_tr_f").strip().upper()
        y_adr = st.text_input("Nereye:", key="st_tr_t").strip().upper()
        t_sec = st.selectbox("🔍 Ürün Seç (Kod/İsim):", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_tr_s")
        t_is_manuel = (t_sec == "+ MANUEL GİRİŞ")
        t_k_i = t_sec.split(" | ")[0] if not t_is_manuel else ""
        
        t_kod = st.text_input("Ürün Kodu:", value=t_k_i, key="st_tr_k").strip().upper()
        t_qty = st.number_input("Miktar:", min_value=0.1, step=1.0, key="st_tr_q")
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary", key="st_tr_btn"):
            f_t_kod = t_kod if t_kod else t_k_i
            
            ok, mev = check_address_stock(f_t_kod, e_adr, t_qty)
            if ok:
                ti = find_name_by_code(f_t_kod)
                update_stock_record(f_t_kod, ti, e_adr, t_qty, is_increase=False)
                update_stock_record(f_t_kod, ti, y_adr, t_qty, is_increase=True)
                log_movement("TRANSFER ÇIKIŞ", e_adr, f_t_kod, ti, t_qty)
                log_movement("TRANSFER GİRİŞ", y_adr, f_t_kod, ti, t_qty)
                st.success("Transfer Başarılı!")
            else: st.error(f"Stok Yok! Mevcut: {mev}")

    with t3:
        search = st.text_input("🔍 Stok Sorgula:", key="st_sq_in").strip().upper()
        if not katalog_list:
            st.info("Katalog yükleniyor veya boş.")
        else:
            df_v, _ = get_katalog()
            if search: df_v = df_v[df_v['Kod'].str.contains(search, na=False) | df_v['İsim'].str.contains(search, na=False)]
            st.dataframe(df_v[["Kod", "İsim"]], use_container_width=True, hide_index=True)

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ", key="nav_u"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık (Toplu Seçim)")
    with st.expander("📥 Yeni İş Emri Yükle"):
        f = st.file_uploader("Excel Seç:", type=["xlsx"], key="u_f")
        if f:
            try:
                eno = f.name.split('.')[0]
                df_r = pd.read_excel(f, sheet_name="HAZIRLIK", skiprows=3)
                
                kc = next((c for c in df_r.columns if "STOK KOD" in str(c).upper()), None)
                ac = next((c for c in df_r.columns if "STOK AD" in str(c).upper()), None)
                mc = next((c for c in df_r.columns if "TOTAL" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                bc = next((c for c in df_r.columns if "BİRİM" in str(c).upper()), None)
                uac = next((c for c in df_r.columns if "MAMÜL AD" in str(c).upper() or "ÜRÜN AD" in str(c).upper()), None)
                ukc = next((c for c in df_r.columns if "MAMÜL KOD" in str(c).upper() or "ÜRÜN KOD" in str(c).upper()), None)
                
                if not kc or not ac or not mc:
                    st.error("Excel formatı uyumsuz! 'STOK KOD', 'STOK AD' ve 'MİKTAR/TOTAL' sütunları bulunamadı.")
                    st.stop()
                
                if uac: df_r[uac] = df_r[uac].ffill()
                if ukc: df_r[ukc] = df_r[ukc].ffill()
                df_r = df_r.dropna(subset=[kc])
                df_r = df_r[~df_r[kc].astype(str).str.upper().str.contains("TOTAL|TOPLAM")]
                df_r[mc] = pd.to_numeric(df_r[mc], errors='coerce').fillna(0)
                df_r = df_r[df_r[mc] > 0]
                
                df_f = df_r[[kc, ac, mc]].copy()
                df_f.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                df_f["Birim"] = df_r[bc].astype(str).str.upper() if bc else "ADET"
                df_f.insert(0, "Mamül Adı", df_r[uac] if uac else "-")
                df_f.insert(1, "Mamül Kodu", df_r[ukc] if ukc else "-")
                df_f.insert(0, "İş Emri", eno); df_f["Hazırlanan Adet"] = 0
                
                if st.button(f"'{eno}' Kaydet", key="u_s_b"):
                    old = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
                    if not old.empty and "İş Emri" in old.columns:
                        old = old[old["İş Emri"] != eno]
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                    get_internal_data.clear()
                    st.success("İş emri listesi güncellendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    df_emirler_master = get_internal_data("Is_Emirleri")
    if not df_emirler_master.empty:
        is_emri_listesi = sorted(df_emirler_master["İş Emri"].unique().tolist())
        s_list = st.multiselect("📋 Hazırlanacak İş Emirlerini Seçin:", is_emri_listesi, key="u_sel_multi", placeholder="Birden fazla iş emri seçebilirsiniz...")
        
        if s_list:
            df_is_emri = df_emirler_master[df_emirler_master["İş Emri"].isin(s_list)].copy()
            df_prep = df_is_emri.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            
            stok_verisi = get_internal_data("Stok")
            stok_verisi['Miktar'] = pd.to_numeric(stok_verisi['Miktar'], errors='coerce').fillna(0)
            stok_verisi['Kod'] = stok_verisi['Kod'].astype(str).str.strip().str.upper()

            def get_best_address(kod):
                kod_str = str(kod).strip().upper()
                urun_raflari = stok_verisi[(stok_verisi['Kod'] == kod_str) & (stok_verisi['Miktar'] > 0)]
                if urun_raflari.empty: return "STOK YOK"
                return urun_raflari.loc[urun_raflari['Miktar'].idxmin(), 'Adres']

            df_prep["Alınan Adres"] = df_prep["Stok Kodu"].apply(get_best_address)
            
            bt = df_prep.groupby('Birim')['İhtiyaç Miktarı'].sum()
            ozet = " | ".join([f"{m:.2f} {b}" for b, m in bt.items()])
            st.info(f"💡 Seçilen {len(s_list)} İş Emrinde Toplam {len(df_prep)} Farklı Kalem | {ozet}")
            
            c_u1, c_u2 = st.columns([0.7, 0.3])
            c_u2.download_button("📥 Excel", data=get_excel_buffer(df_prep, "Toplu_Hazirlik"), file_name=f"Toplu_Hazirlik.xlsx", use_container_width=True)
            
            ed = st.data_editor(df_prep, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim"], hide_index=True, use_container_width=True, key="u_ed")
            
            if st.button("HAZIRLIĞI ONAYLA", key="u_ok"):
                fresh_emirler = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
                secilen_isimler = ", ".join(s_list)
                
                for idx, row in ed.iterrows():
                    fark = float(row["Hazırlanan Adet"]) - float(df_prep.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        ok, mevcut = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                        
                        if not ok:
                            eksik = fark - mevcut
                            hedef_adr = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], eksik, is_increase=True)
                            log_movement("OTOMATİK SİSTEM GİRİŞİ (HAZIRLIK)", hedef_adr, row["Stok Kodu"], row["Stok Adı"], eksik)
                        
                        adr_son = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], fark, is_increase=False)
                        log_movement(f"{secilen_isimler} ÜRETİM ÇIKIŞ", adr_son, row["Stok Kodu"], row["Stok Adı"], fark)
                        
                        kalan = float(row["Hazırlanan Adet"])
                        mask = (fresh_emirler["İş Emri"].isin(s_list)) & (fresh_emirler["Stok Kodu"].astype(str).str.strip().str.upper() == str(row["Stok Kodu"]).strip().upper())
                        
                        for i in fresh_emirler[mask].index:
                            iht = float(fresh_emirler.at[i, "İhtiyaç Miktarı"])
                            val = iht if kalan >= iht else kalan
                            fresh_emirler.at[i, "Hazırlanan Adet"] = val
                            kalan -= val
                            
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=fresh_emirler)
                get_internal_data.clear()
                st.success("Sanal tamamlama yapıldı ve toplu hazırlık onaylandı!"); st.rerun()
    else:
        st.info("📂 Veritabanında kayıtlı iş emri bulunmuyor. Lütfen yukarıdaki '📥 Yeni İş Emri Yükle' sekmesinden excel dosyası yükleyiniz.")

# --- 8. SAYIM SİSTEMİ EKRANI ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ", key="nav_sayim"): go_home(); st.rerun()
    st.title("⚖️ Sayım İşlemleri Ekranı")
    
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "İncelemede"]
    stok_df_all, katalog_list = get_katalog()

    with st_tab1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres", key="sayim_adr").upper()
            
            sec = st.selectbox("🔍 Ürün Seç (Kod/İsim):", ["+ MANUEL GİRİŞ"] + katalog_list, key="sayim_is_s")
            is_manuel = (sec == "+ MANUEL GİRİŞ")
            
            k_i = sec.split(" | ")[0] if not is_manuel else ""
            i_i = sec.split(" | ")[1] if not is_manuel else ""
            
            s_kod = st.text_input("📦 Stok Kodu:", value=k_i, key="sayim_is_k").strip().upper()
            s_isim = st.text_input("📝 Stok Adı:", value=i_i if i_i else find_name_by_code(s_kod), key="sayim_is_i").strip().upper()
            
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0, key="sayim_mik")
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari, key="sayim_dur")
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                g_kod = s_kod if s_kod else k_i
                g_isim = s_isim if s_isim else i_i
                
                if s_adr:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user, 
                        "Adres": s_adr, 
                        "Kod": g_kod, 
                        "Ürün Adı": g_isim, 
                        "Miktar": s_mik, 
                        "Durum": s_dur
                    })
                    st.toast("Listeye Eklendi (Lokal)")
                else: 
                    st.warning("Adres alanı zorunludur!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyenler (Kaydedilmedi)")
            h_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
            h_cols[0].write("**Adres**")
            h_cols[1].write("**Kod**")
            h_cols[2].write("**Ürün**")
            h_cols[3].write("**Mik.**")
            h_cols[4].write("**Durum**")
            h_cols[5].write("**Sil**")
            st.markdown("---")

            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
                r_cols[0].write(item['Adres'])
                r_cols[1].write(item['Kod'])
                r_cols[2].markdown(f"<p class='row-font'>{item['Ürün Adı'][:15]}</p>", unsafe_allow_html=True)
                r_cols[3].write(str(item['Miktar']))
                r_cols[4].write(item['Durum'])
                
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
            
            if st.button("📤 SAYIMI KAYDET (Veritabanına Gönder)", type="primary", use_container_width=True):
                df_db = conn.read(spreadsheet=SHEET_URL, worksheet="sayim", ttl=0) 
                yeni_sayim_df = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, yeni_sayim_df], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                get_internal_data.clear()
                st.success("Sayım Başarıyla Veritabanına Yazıldı!")
                st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Filtreler", expanded=True):
                    col_f1, col_f2 = st.columns(2)
                    col_f3, col_f4 = st.columns(2)
                    
                    f_t = col_f1.selectbox("📅 Tarih", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    sel_k = col_f2.multiselect("📦 Kod", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = col_f3.multiselect("📍 Adres", sorted(df_s_db["Adres"].unique().tolist()))
                    
                    if "Durum" in df_s_db.columns:
                        durum_listesi = sorted(df_s_db["Durum"].astype(str).unique().tolist())
                    else:
                        durum_listesi = durum_opsiyonlari
                    sel_d = col_f4.multiselect("🛠️ Durum", durum_listesi)

                act = df_s_db.copy()
                if f_t != "Tümü": 
                    act = act[act["Tarih"] == f_t]
                if sel_k: 
                    act = act[act["Kod"].isin(sel_k)]
                if sel_a: 
                    act = act[act["Adres"].isin(sel_a)]
                if sel_d: 
                    act = act[act["Durum"].isin(sel_d)]

                if not act.empty:
                    say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı', 'Durum'])['Miktar'].sum().reset_index()
                    say_ozet.columns = ["Adres", "Kod", "Ürün Adı", "Durum", "Sayılan"]
                    
                    sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                    sis_ozet.columns = ["Adres", "Kod", "Sistem"]
                    
                    res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                    res['FARK'] = res['Sayılan'] - res['Sistem']
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Sayılan (Filtreli)", f"{res['Sayılan'].sum():,.0f}")
                    m2.metric("Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
                    
                    c_sr1, c_sr2 = st.columns([0.7, 0.3])
                    c_sr2.download_button("📥 Excel", data=get_excel_buffer(res, "Sayim_Farki"), file_name=f"Sayim_Raporu_{f_t}.xlsx", use_container_width=True)
                    
                    def renk_ver(v):
                        if v < 0: return 'color:red; font-weight:bold'
                        elif v > 0: return 'color:green; font-weight:bold'
                        return ''
                    
                    st.dataframe(res.style.map(renk_ver, subset=['FARK']), use_container_width=True, hide_index=True)
                else: 
                    st.warning("Seçilen filtrelere uygun sayım verisi bulunamadı.")
            else: 
                st.info("Sayım verisi bulunamadı.")
        except Exception as e: 
            st.error(f"Hata Oluştu: {e}")

# --- 9. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ", key="n_r"): go_home(); st.rerun()
    st.subheader("📊 Merkezi Raporlar")
    rt1, rt2, rt3 = st.tabs(["🏠 Stok Durumu", "🏭 Hazırlık Takibi", "📜 Hareket Arşivi"])
    
    with rt1: 
        stok_veritabani = get_internal_data("Stok")
        c_st1, c_st2 = st.columns([0.7, 0.3])
        c_st2.download_button("📥 Excel", data=get_excel_buffer(stok_veritabani, "Stoklar"), file_name="Stok_Veritabani.xlsx", use_container_width=True)
        st.dataframe(stok_veritabani, use_container_width=True, hide_index=True)

    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            df_h['İhtiyaç Miktarı'] = pd.to_numeric(df_h['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            df_h['Hazırlanan Adet'] = pd.to_numeric(df_h['Hazırlanan Adet'], errors='coerce').fillna(0)
            summary = df_h.groupby('İş Emri')[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            summary['%'] = (summary['Hazırlanan Adet'] / summary['İhtiyaç Miktarı'] * 100).round(1)
            
            c_hz1, c_hz2 = st.columns([0.7, 0.3])
            c_hz2.download_button("📥 Excel", data=get_excel_buffer(summary, "Hazirlik_Ozet"), file_name="Hazirlik_Ozeti.xlsx", use_container_width=True)
            st.dataframe(summary, column_config={"%": st.column_config.ProgressColumn("İlerleme", format="%.1f%%", min_value=0, max_value=100)}, use_container_width=True, hide_index=True)
            st.divider()
            
            secilen = st.selectbox("Detay:", ["Seçiniz..."] + sorted(summary['İş Emri'].unique().tolist()), key="rep_s")
            if secilen != "Seçiniz...":
                detay = df_h[df_h['İş Emri'] == secilen].copy()
                
                mamul_listesi = ["TÜMÜ"] + sorted(detay['Mamül Adı'].astype(str).unique().tolist())
                secilen_mamul = st.selectbox("Mamül Adı Filtresi:", mamul_listesi, key="rep_mamul_s")
                
                if secilen_mamul != "TÜMÜ":
                    detay = detay[detay['Mamül Adı'] == secilen_mamul]
                
                gosterilecek_detay = detay[["Mamül Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]]
                
                c_hd1, c_hd2 = st.columns([0.7, 0.3])
                c_hd2.download_button("📥 Excel", data=get_excel_buffer(gosterilecek_detay, "Is_Emri_Detay"), file_name=f"Hazirlik_Detay_{secilen}.xlsx", use_container_width=True)
                st.dataframe(gosterilecek_detay, use_container_width=True, hide_index=True)
    
    with rt3:
        hareketler = get_internal_data("Sayfa1")
        if not hareketler.empty:
            c1, c2, c3 = st.columns(3)
            fk = c1.text_input("📦 Kod:", key="f_k").strip().upper()
            fi = c2.text_input("🏷️ İsim:", key="f_i").strip().upper()
            fa = c3.text_input("📍 Adres:", key="f_a").strip().upper()
            df_f = hareketler.copy()
            if fk: df_f = df_f[df_f['Malzeme Kodu'].astype(str).str.contains(fk, na=False)]
            if fi: df_f = df_f[df_f['Malzeme Adı'].astype(str).str.contains(fi, na=False)]
            if fa: df_f = df_f[df_f['Adres'].astype(str).str.contains(fa, na=False)]
            
            gosterilecek_hareketler = df_f.iloc[::-1]
            
            c_hr1, c_hr2 = st.columns([0.7, 0.3])
            c_hr2.download_button("📥 Excel", data=get_excel_buffer(gosterilecek_hareketler, "Hareketler"), file_name="Hareket_Gecmisi.xlsx", use_container_width=True)
            st.dataframe(gosterilecek_hareketler, use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
