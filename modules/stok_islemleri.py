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
                return df_katalog.apply(
                    lambda x: f"{x[kod_col]} | {x[isim_col]}", axis=1
                ).tolist()

        return []

    except Exception as e:
        st.error(f"Katalog okuma hatası: {e}")
        return []


def clear_form():
    st.session_state.reset_form = True


def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state["s_kod"] = sec.split(" | ")[0]


def run():

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            st.session_state[k] = "" if k != "s_mik" else 0.0
        st.session_state.reset_form = False

    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        st.session_state.pop("islem_basarili", None)
        st.session_state.pop("mesaj", None)

    # FIX: duplicate rerun safety
    if st.button("🔄 Drive'dan Katalog İndir", type="secondary", key="sync_btn"):
        with st.spinner("Katalog güncelleniyor..."):
            db.init_db()
            basarili, hatali = db.sync_from_drive()

        if basarili:
            st.success(f"✅ Başarıyla İnenler: {', '.join(basarili)}")

        if hatali:
            st.error(f"❌ İndirilemeyenler: {', '.join(hatali)}")

        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")

    with st.container(border=True):

        move_type = st.selectbox(
            "İşlem Tipi:",
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"],
            key="move_type"
        )

        katalog = get_katalog()

        sec = st.selectbox(
            "🔍 Ürün Seç:",
            ["+ MANUEL GİRİŞ"] + katalog,
            key="sec",
            on_change=urun_secildi
        )

        c1, c2 = st.columns(2)

        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="s_kod_input").upper().strip()
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot_input").upper().strip()

        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")

        src_adr = "-"
        dst_adr = "-"

        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1:
                dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr_input").upper().strip()

        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr_input").upper().strip()

        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr_input_2").upper().strip()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr_input_2").upper().strip()

        if st.button("➕ LİSTEYE EKLE", use_container_width=True, key="add_list"):

            if not s_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                kalem = {
                    "İşlem": move_type,
                    "Kod": s_kod,
                    "İsim": sec.split(" | ")[1] if " | " in sec else "MANUEL ÜRÜN",
                    "Miktar": s_mik,
                    "Lot": s_lot,
                    "Durum": s_dur,
                    "Kaynak": src_adr if move_type in ["ÇIKIŞ", "İÇ TRANSFER"] else "-",
                    "Hedef": dst_adr if move_type in ["GİRİŞ", "İÇ TRANSFER"] else "-"
                }

                st.session_state.gecici_liste.append(kalem)
                clear_form()
                st.rerun()

    # LISTE
    if st.session_state.gecici_liste:

        st.markdown("### 📋 Bekleyen İşlemler")

        for i, item in enumerate(st.session_state.gecici_liste):

            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']}"):

                st.write(item)

                if st.button("🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        if st.button("🚀 DB'YE YAZ", type="primary", key="commit"):

            try:
                islem_listesi = list(st.session_state.gecici_liste)
                st.session_state.gecici_liste = []

                df_stok = db.read("stok")
                hareket_df = pd.DataFrame()

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                for satir in islem_listesi:

                    hareket_df = pd.concat([
                        hareket_df,
                        pd.DataFrame([{
                            "tarih": now,
                            "islem": satir["İşlem"],
                            "kod": satir["Kod"],
                            "isim": satir["İsim"],
                            "kaynak": satir["Kaynak"],
                            "hedef": satir["Hedef"],
                            "miktar": satir["Miktar"],
                            "user": "Sistem",
                            "aciklama": satir["Lot"]
                        }])
                    ])

                    mask_in = (df_stok["kod"] == satir["Kod"]) & (df_stok["adres"] == satir["Hedef"])
                    mask_out = (df_stok["kod"] == satir["Kod"]) & (df_stok["adres"] == satir["Kaynak"])

                    if satir["İşlem"] == "GİRİŞ":
                        if mask_in.any():
                            df_stok.loc[mask_in, "miktar"] += satir["Miktar"]
                        else:
                            df_stok = pd.concat([df_stok, pd.DataFrame([satir])])

                    elif satir["İşlem"] == "ÇIKIŞ":
                        if mask_out.any():
                            df_stok.loc[mask_out, "miktar"] -= satir["Miktar"]

                    elif satir["İŞLEM"] == "İÇ TRANSFER":
                        if mask_out.any():
                            df_stok.loc[mask_out, "miktar"] -= satir["Miktar"]

                        if mask_in.any():
                            df_stok.loc[mask_in, "miktar"] += satir["Miktar"]

                db.write("hareketler", hareket_df, exists_action="append")
                db.write("stok", df_stok, exists_action="replace")

                st.session_state.islem_basarili = True
                st.session_state.mesaj = "İşlemler kaydedildi"

                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(str(e))
