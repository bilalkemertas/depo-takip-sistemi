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
    except Exception as e:
        st.error(f"Katalog okuma hatası: {e}")
        return []

def clear_form():
    st.session_state.reset_form = True

def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec.split(" | ")[0]

def run():
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            if k in st.session_state:
                st.session_state[k] = 0.0 if k == "s_mik" else ""
        st.session_state.reset_form = False

    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

    if st.button("🔄 Drive'dan Katalog İndir", type="secondary"):
        with st.spinner("Katalog güncelleniyor..."):
            db.init_db()
            db.sync_from_drive()
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")
    
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        katalog = get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog, key="sec", on_change=urun_secildi)
        
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        src_adr, dst_adr = "-", "-"
        a1, a2 = st.columns(2)
        if move_type == "GİRİŞ":
            with a1: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()
        elif move_type == "ÇIKIŞ":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
        elif move_type == "İÇ TRANSFER":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
            with a2: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            if not s_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                f_src = src_adr if move_type in ["ÇIKIŞ", "İÇ TRANSFER"] else "-"
                f_dst = dst_adr if move_type in ["GİRİŞ", "İÇ TRANSFER"] else "-"
                kalem = {"İşlem": move_type, "Kod": s_kod, "İsim": sec.split(" | ")[1] if " | " in sec else "MANUEL ÜRÜN", "Miktar": s_mik, "Lot": s_lot, "Durum": s_dur, "Kaynak": f_src, "Hedef": f_dst}
                st.session_state.gecici_liste.append(kalem)
                clear_form(); st.rerun()

    if st.session_state.gecici_liste:
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                if st.button(f"🗑️ Bu Satırı Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i); st.rerun()

        st.divider()
        if st.button("🚀 TÜM HAREKETLERİ VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            try:
                isleme_alinacaklar = list(st.session_state.gecici_liste)
                st.session_state.gecici_liste = [] 
                
                df_stok = db.read("stok")
                # SÜTUN GARANTİSİ
                if df_stok.empty or 'kod' not in df_stok.columns:
                    df_stok = pd.DataFrame(columns=["kod", "isim", "adres", "miktar", "durum"])
                
                yeni_hkt_df = pd.DataFrame()
                is_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                personel = st.session_state.get("user", "Sistem")

                for satir in isleme_alinacaklar:
                    yeni_hkt = {"tarih": is_time, "islem": satir["İşlem"], "kod": satir["Kod"], "isim": satir["İsim"], "kaynak": satir["Kaynak"], "hedef": satir["Hedef"], "miktar": satir["Miktar"], "user": personel, "aciklama": satir["Lot"]}
                    yeni_hkt_df = pd.concat([yeni_hkt_df, pd.DataFrame([yeni_hkt])], ignore_index=True)
                    
                    if satir["İşlem"] == "GİRİŞ":
                        mask = (df_stok['kod'] == satir["Kod"]) & (df_stok['adres'] == satir["Hedef"])
                        if mask.any(): df_stok.loc[mask, 'miktar'] += satir["Miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"kod": satir["Kod"], "isim": satir["İsim"], "adres": satir["Hedef"], "miktar": satir["Miktar"], "durum": satir["Durum"]}])], ignore_index=True)
                    elif satir["İşlem"] == "ÇIKIŞ":
                        mask = (df_stok['kod'] == satir["Kod"]) & (df_stok['adres'] == satir["Kaynak"])
                        if mask.any(): df_stok.loc[mask, 'miktar'] = max(0, df_stok.loc[mask, 'miktar'].values[0] - satir["Miktar"])

                db.write("hareketler", yeni_hkt_df, exists_action='append')
                db.write("stok", df_stok, exists_action='replace')
                
                db.sync_to_drive()
                st.session_state["islem_basarili"] = True; st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Hata detayı: {e}")

def run_transfer(): run()
