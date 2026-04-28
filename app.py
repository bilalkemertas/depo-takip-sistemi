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
        # KRİTİK ZIRH: Boş hücreleri (NaN) tire işaretiyle doldurarak tip hatasını engeller
        df = df.fillna("-")
        
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
        if not katalog_list: st.info("Katalog yükleniyor veya boş.")
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
                    st.error("Excel formatı uyumsuz!")
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
                        old = old[old["İş Emri"].astype(str) != str(eno)]
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                    get_internal_data.clear()
                    st.success("İş emri listesi güncellendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    df_emirler_master = get_internal_data("Is_Emirleri")
    if not df_emirler_master.empty:
        df_emirler_master["İş Emri"] = df_emirler_master["İş Emri"].astype(str)
        is_emri_listesi = sorted(df_emirler_master["İş Emri"].unique().tolist())
        s_list = st.multiselect("📋 Hazırlanacak İş Emirlerini Seçin:", is_emri_listesi, key="u_sel_multi")
        
        if s_list:
            df_is_emri = df_emirler_master[df_emirler_master["İş Emri"].isin(s_list)].copy()
            df_prep = df_is_emri.groupby(['Stok Kodu', 'Stok Adı', 'Birim'], sort=False).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            stok_verisi = get_internal_data("Stok")
            stok_verisi['Miktar'] = pd.to_numeric(stok_verisi['Miktar'], errors='coerce').fillna(0)
            
            def get_best_address(kod):
                urun_raflari = stok_verisi[(stok_verisi['Kod'].astype(str) == str(kod)) & (stok_verisi['Miktar'] > 0)]
                return urun_raflari.loc[urun_raflari['Miktar'].idxmin(), 'Adres'] if not urun_raflari.empty else "STOK YOK"

            df_prep["Alınan Adres"] = df_prep["Stok Kodu"].apply(get_best_address)
            bt = df_prep.groupby('Birim', sort=False)['İhtiyaç Miktarı'].sum()
            ozet = " | ".join([f"{m:.2f} {b}" for b, m in bt.items()])
            st.info(f"💡 Özet: {ozet}")
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
                            update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], eksik, is_increase=True)
                        adr_son = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], fark, is_increase=False)
                        log_movement(f"{secilen_isimler} ÇIKIŞ", adr_son, row["Stok Kodu"], row["Stok Adı"], fark)
                st.success("Hazırlık Onaylandı!"); st.rerun()
    else: st.info("📂 İş emri bulunmuyor.")

# --- 8. SAYIM SİSTEMİ EKRANI ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ", key="nav_sayim"): go_home(); st.rerun()
    st.title("⚖️ Sayım Girişi")
    st_tab1, st_tab2 = st.tabs(["📝 Giriş", "📊 Rapor"])
    stok_df_all, katalog_list = get_katalog()

    with st_tab1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres").upper()
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog_list)
            is_m = (sec == "+ MANUEL")
            k_i = sec.split(" | ")[0] if not is_m else ""
            i_i = sec.split(" | ")[1] if not is_m else ""
            s_kod = st.text_input("📦 Kod:", value=k_i).strip().upper()
            s_isim = st.text_input("📝 Ad:", value=i_i if i_i else find_name_by_code(s_kod)).strip().upper()
            s_mik = st.number_input("Mik.", min_value=0.0)
            if st.button("➕ Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({"Tarih": get_local_time(), "Personel": st.session_state.user, "Adres": s_adr, "Kod": s_kod, "Ürün Adı": s_isim, "Miktar": s_mik, "Durum": "Kullanılabilir"})
                st.toast("Eklendi")

        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 KAYDET", type="primary", use_container_width=True):
                df_db = conn.read(spreadsheet=SHEET_URL, worksheet="sayim", ttl=0)
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; get_internal_data.clear(); st.success("Kaydedildi!"); st.rerun()

    with st_tab2:
        df_s_db = get_internal_data("sayim")
        if not df_s_db.empty:
            df_stok_ana = get_internal_data("Stok")
            res = pd.merge(df_s_db.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index(), df_stok_ana.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index(), on=['Adres', 'Kod'], how='outer', suffixes=('_Sayilan', '_Sistem')).fillna(0)
            res['FARK'] = res['Miktar_Sayilan'] - res['Miktar_Sistem']
            st.dataframe(res, use_container_width=True, hide_index=True)

# --- 9. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ", key="n_r"): go_home(); st.rerun()
    st.subheader("📊 Raporlar")
    rt1, rt2, rt3 = st.tabs(["🏠 Stok", "🏭 Hazırlık", "📜 Arşiv"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            sum_h = df_h.groupby('İş Emri', sort=False)[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            st.dataframe(sum_h, use_container_width=True, hide_index=True)
    with rt3: st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
