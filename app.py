import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os
import streamlit.components.v1 as components

# --- 1. 2026 MODERN TASARIM VE AGRESİF GİZLEME ---
st.set_page_config(page_title="BRN X-Ray Pro", layout="centered", page_icon="brn_logo.webp")

# Modern CSS: 2026 Streamlit framework sınıflarını hedefleyen stil paketi
st.markdown("""
    <style>
    /* Tüm standart Streamlit arayüz elemanlarını kazı */
    #MainMenu, footer, header, .stDeployButton {display: none !important; visibility: hidden !important;}
    [data-testid="stStatusWidget"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
    
    /* Manage App ve Frame Badge gizleme (2026 Güncel) */
    div[class*="viewerBadge"], div[class*="StreamlitFrameBadge"], button[title*="Manage"] {
        display: none !important;
        height: 0px !important;
        width: 0px !important;
    }

    /* El terminali ekran optimizasyonu */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 98% !important;
    }
    
    /* Giriş alanlarını terminalde okunabilir yap */
    input { font-size: 16px !important; }
    
    /* Sekme yüksekliklerini ayarla */
    .stTabs [data-baseweb="tab"] { height: 45px; white-space: pre-wrap; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# 2026 Agresif JavaScript: Shadow DOM ve Iframe dışındaki butonları her 300ms'de bir siler
components.html(
    """
    <script>
    const cleanSystemUI = () => {
        const selectors = [
            'div[class*="viewerBadge"]', 
            'button[title*="Manage app"]', 
            '[data-testid="bundle-viewer-button"]',
            'footer',
            '.stAppDeployButton',
            'header'
        ];
        
        selectors.forEach(selector => {
            // Hem uygulama içini hem de Streamlit Cloud ana çerçevesini tara
            const localElements = document.querySelectorAll(selector);
            localElements.forEach(el => el.remove());
            
            try {
                const parentElements = window.parent.document.querySelectorAll(selector);
                parentElements.forEach(el => el.remove());
            } catch (e) {
                // Cross-origin kısıtlaması olursa sessizce devam et
            }
        });
    };
    setInterval(cleanSystemUI, 300);
    </script>
    """,
    height=0,
)

# --- 2. GÜVENLİK VE GİRİŞ KONTROLÜ ---
try:
    USERS = st.secrets["users"]
except Exception:
    # Secrets tanımlanmamışsa yedek (Settings > Secrets kısmına eklenmeli)
    USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

def login_paneli():
    st.markdown("<h3 style='text-align:center;'>🛡️ BRN Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u = st.text_input("Kullanıcı:")
        p = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if u in USERS and str(USERS[u]) == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Erişim Reddedildi: Bilgileri kontrol edin.")

if not st.session_state.logged_in:
    login_paneli()
    st.stop()

# --- 3. VERİ BAĞLANTISI VE FONKSİYONLAR ---
conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir(ws="Sayfa1"):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=ws)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

df_urunler = taze_veri_getir("Urun_Listesi")
df_hareketler = taze_veri_getir("Sayfa1")

def urun_bilgisi_cek(kod):
    if not df_urunler.empty and kod:
        match = df_urunler[df_urunler['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
        if not match.empty:
            return match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
    return None, None

def kayit_ekle(islem, adr, kod, ad, brm, mik):
    df_t = taze_veri_getir("Sayfa1")
    yeni = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adr).upper()],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [str(ad).upper()],
        "Birim": [str(brm).upper()],
        "Miktar": [float(mik)],
        "Kullanıcı": [st.session_state.user.upper()]
    })
    conn.update(data=pd.concat([df_t, yeni], ignore_index=True), worksheet="Sayfa1")

# --- 4. ÜST PANEL ---
c1, c2, c3 = st.columns([1, 3, 1])
with c1:
    if os.path.exists("brn_logo.webp"): st.image("brn_logo.webp", width=45)
with c2:
    st.markdown(f"<p style='margin-top:10px;'><b>Operatör:</b> {st.session_state.user.upper()}</p>", unsafe_allow_html=True)
with c3:
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("<hr style='margin:0 0 10px 0;'>", unsafe_allow_html=True)

# --- 5. İŞLEMLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "🔍 Stok Sorgu"])

with t1:
    ca, cb = st.columns(2)
    i_tip = ca.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
    adr_v = cb.text_input("Adres:", value="GENEL")
    k_v = st.text_input("📦 Barkod Okutun:", key="scan_reg")
    
    ad_b, brm_b = urun_bilgisi_cek(k_v)
    if k_v and ad_b:
        st.success(f"{ad_b} ({brm_b})")
        step = 0.001 if str(brm_b).upper() not in ["ADET", "ADT"] else 1.0
        m_v = st.number_input("Miktar:", min_value=0.0, step=step)
        if st.button(f"{i_tip} KAYDET", use_container_width=True):
            if m_v > 0:
                kayit_ekle(i_tip, adr_v, k_v, ad_b, brm_b, m_v)
                st.toast("Kayıt Başarılı!")
                st.rerun()
    elif k_v: st.error("Ürün Kayıtlı Değil!")

with t2:
    tr_k = st.text_input("Transfer Edilecek Barkod:", key="scan_tr")
    tr_ad, tr_b = urun_bilgisi_cek(tr_k)
    if tr_k and tr_ad:
        st.info(f"Ürün: {tr_ad}")
        c1, c2 = st.columns(2)
        n_den = c1.text_input("Nerden:", value="GENEL")
        n_ye = c2.text_input("Nereye:")
        tr_m = st.number_input("Miktar:", min_value=0.0, key="tr_qty")
        if st.button("TRANSFERİ GERÇEKLEŞTİR", use_container_width=True):
            if n_ye and tr_m > 0:
                kayit_ekle("ÇIKIŞ", n_den, tr_k, tr_ad, tr_b, tr_m)
                kayit_ekle("GİRİŞ", n_ye, tr_k, tr_ad, tr_b, tr_m)
                st.toast("Transfer Başarılı!")
                st.rerun()

with t3:
    if st.button("🔄 Veriyi Yenile"): st.rerun()
    ara = st.text_input("🔍 Ara (Kod, İsim, Adres):").upper()
    
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        if 'Birim' in df_h.columns:
            df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
            df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            stok.columns = ["Adres", "Kod", "Ürün", "Brm", "Miktar"]
            if ara:
                stok = stok[(stok['Adres'].str.upper().str.contains(ara, na=False)) | 
                            (stok['Kod'].str.upper().str.contains(ara, na=False)) | 
                            (stok['Ürün'].str.upper().str.contains(ara, na=False))]
            st.dataframe(stok, use_container_width=True, hide_index=True)

st.markdown("<div style='text-align:center; color:gray; font-size:10px; margin-top:30px;'>BRN X-Ray Pro v10.0 | 2026 Modern Depo</div>", unsafe_allow_html=True)
