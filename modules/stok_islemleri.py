import streamlit as st
from core import db
import pandas as pd
from datetime import datetime

@st.cache_data(ttl=600)
def get_katalog():
    try:
        db.init_db()
        df_katalog = db.read("urun_listesi")
        if not df_katalog.empty:
            df_katalog.columns = [str(c).strip().upper() for c in df_katalog.columns]
            kod_col = next((c for c in df_katalog.columns if 'KOD' in c), None)
            isim_col = next((c for c in df_katalog.columns if 'ISIM' in c or 'İSİM' in c), None)
            if kod_col and isim_col:
                return df_katalog.apply(lambda x: f"{x[kod_col]} | {x[isim_col]}", axis=1).tolist()
        return []
    except: return []

def run_islem():
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    st.subheader("📊 Stok Hareketleri")

    with st.container(border=True):
        move_type = st.selectbox("İşlem", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        katalog = get_katalog()
        sec = st.selectbox("Ürün Seç", ["+ MANUEL"] + katalog)

        c1, c2 = st.columns(2)
        with c1:
            kod = st.text_input("📦 Kod").strip().upper()
            miktar = st.number_input("Miktar", min_value=0.0)
        with c2:
            kaynak = st.text_input("📍 Kaynak").strip().upper()
            hedef = st.text_input("📍 Hedef").strip().upper()

        if st.button("➕ Listeye Ekle", use_container_width=True):
            if kod and miktar > 0:
                st.session_state.gecici_liste.append({
                    "islem": move_type, "kod": kod,
                    "isim": sec.split(" | ")[1] if " | " in sec else "MANUEL",
                    "miktar": miktar, "kaynak": kaynak if kaynak else "-", "hedef": hedef if hedef else "-"
                })
                st.rerun()

    if st.session_state.gecici_liste:
        st.write("📋 Bekleyenler:", st.session_state.gecici_liste)

        if st.button("🚀 TÜM HAREKETLERİ İŞLE", type="primary", use_container_width=True):
            try:
                # 1. HAFIZAYI HEMEN AYIR VE BOŞALT
                isleme_alinacaklar = list(st.session_state.gecici_liste)
                st.session_state.gecici_liste = []

                # 2. STOK TABLOSUNU OKU (Bakiye için mecburi)
                df_stok = db.read("stok")
                if df_stok.empty:
                    df_stok = pd.DataFrame(columns=["kod","isim","adres","miktar","durum"])
                
                df_stok['kod'] = df_stok['kod'].astype(str).str.upper()
                df_stok['adres'] = df_stok['adres'].astype(str).str.upper()
                
                # 3. YENİ HAREKETLERİ LİSTEYE TOPLA (Read 'hareketler' yapmıyoruz!)
                yeni_hkt_df = pd.DataFrame()
                is_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                usr = st.session_state.get("user", "Sistem")

                for s in isleme_alinacaklar:
                    hkt_satiri = {"tarih": is_time, "islem": s["islem"], "kod": s["kod"], "isim": s["isim"], "kaynak": s["kaynak"], "hedef": s["hedef"], "miktar": s["miktar"], "user": usr, "aciklama": "Toplu"}
                    yeni_hkt_df = pd.concat([yeni_hkt_df, pd.DataFrame([hkt_satiri])], ignore_index=True)

                    # Stok bakiye güncelleme
                    if s["islem"] == "GİRİŞ":
                        m = (df_stok['kod'] == s["kod"]) & (df_stok['adres'] == s["hedef"])
                        if m.any(): df_stok.loc[m, 'miktar'] += s["miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"kod":s["kod"],"isim":s["isim"],"adres":s["hedef"],"miktar":s["miktar"],"durum":"OK"}])], ignore_index=True)
                    elif s["islem"] == "ÇIKIŞ":
                        m = (df_stok['kod'] == s["kod"]) & (df_stok['adres'] == s["kaynak"])
                        if m.any(): df_stok.loc[m, 'miktar'] -= s["miktar"]

                # 4. YAZMA OPERASYONU
                # Hareketleri SADECE ekle (append) - Geçmişi geri getirmez!
                db.write("hareketler", yeni_hkt_df, exists_action='append')
                
                # Stoğu komple güncelle (replace) - Bakiye için şart
                db.write("stok", df_stok, exists_action='replace')

                db.sync_to_drive()
                st.success("✅ İşlem Başarılı!"); st.cache_data.clear(); st.rerun()

            except Exception as e:
                st.error(f"Hata: {e}")

def run_transfer(): run_islem()
