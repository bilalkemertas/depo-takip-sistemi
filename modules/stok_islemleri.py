import streamlit as st
from core import db
import pandas as pd
from datetime import datetime

# ----------------------------
# KATALOG CACHE (AYNEN KORUNDU)
# ----------------------------
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
                    lambda x: f"{x[kod_col]} | {x[isim_col]}",
                    axis=1
                ).tolist()

        return []
    except Exception as e:
        st.error(f"Katalog hatası: {e}")
        return []


# ----------------------------
# FORM RESET
# ----------------------------
def clear_form():
    st.session_state.reset_form = True


# ----------------------------
# ÜRÜN SEÇİM CALLBACK
# ----------------------------
def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec.split(" | ")[0]


# ----------------------------
# ANA MODÜL
# ----------------------------
def run_islem():

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # form reset
    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            if k in st.session_state:
                st.session_state[k] = ""
        st.session_state.reset_form = False

    # success mesajı
    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

    # ----------------------------
    # KATALOG GÜNCELLE
    # ----------------------------
    if st.button("🔄 Drive'dan Katalog İndir", type="secondary"):
        with st.spinner("Katalog güncelleniyor..."):
            db.init_db()
            basarili, hatali = db.sync_from_drive()
        st.cache_data.clear()
        st.rerun()

    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")

    # ----------------------------
    # İŞLEM PANELİ
    # ----------------------------
    with st.container(border=True):

        move_type = st.selectbox(
            "İşlem Tipi:",
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"],
            key="move_type"
        )

        # ----------------------------
        # KATALOGDAN ÜRÜN SEÇİMİ (SENİN EKRANIN)
        # ----------------------------
        katalog = get_katalog()

        sec = st.selectbox(
            "🔍 Ürün Seç:",
            ["+ MANUEL GİRİŞ"] + katalog,
            key="sec",
            on_change=urun_secildi
        )

        c1, c2 = st.columns(2)

        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()

        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")

        # ----------------------------
        # ADRES MANTIĞI (SENİN ORİJİNAL)
        # ----------------------------
        src_adr, dst_adr = "-", "-"

        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()

        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        # ----------------------------
        # LİSTEYE EKLE
        # ----------------------------
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):

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
                    "Kaynak": src_adr if move_type != "GİRİŞ" else "-",
                    "Hedef": dst_adr if move_type != "ÇIKIŞ" else "-"
                }

                st.session_state.gecici_liste.append(kalem)
                clear_form()
                st.rerun()

    # ----------------------------
    # İŞLEM TABLOSU (SENİN EKSİK OLMASIN DEDİĞİN KISIM)
    # ----------------------------
    if st.session_state.gecici_liste:

        st.markdown("### 📋 Bekleyen Hareketler")

        for i, item in enumerate(st.session_state.gecici_liste):

            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']}"):

                st.write(item)

                if st.button(f"🗑️ Sil {i}", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        # ----------------------------
        # DB POST
        # ----------------------------
        if st.button("🚀 TÜM HAREKETLERİ İŞLE", use_container_width=True, type="primary"):

            try:
                df_stok = db.read("stok")
                yeni_hkt_df = pd.DataFrame()

                is_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                personel = st.session_state.get("user", "Sistem")

                for satir in st.session_state.gecici_liste:

                    yeni_hkt = {
                        "tarih": is_time,
                        "islem": satir["İşlem"],
                        "kod": satir["Kod"],
                        "isim": satir["İsim"],
                        "kaynak": satir["Kaynak"],
                        "hedef": satir["Hedef"],
                        "miktar": satir["Miktar"],
                        "user": personel,
                        "aciklama": satir["Lot"]
                    }

                    yeni_hkt_df = pd.concat(
                        [yeni_hkt_df, pd.DataFrame([yeni_hkt])],
                        ignore_index=True
                    )

                    kod = satir["Kod"]
                    miktar = satir["Miktar"]
                    kaynak = satir["Kaynak"]
                    hedef = satir["Hedef"]

                    # ---------------- GİRİŞ ----------------
                    if satir["İşlem"] == "GİRİŞ":

                        mask = (df_stok['kod'] == kod) & (df_stok['adres'] == hedef)

                        if mask.any():
                            df_stok.loc[mask, 'miktar'] += miktar
                        else:
                            df_stok = pd.concat([df_stok, pd.DataFrame([{
                                "kod": kod,
                                "isim": satir["İsim"],
                                "adres": hedef,
                                "miktar": miktar,
                                "durum": satir["Durum"]
                            }])], ignore_index=True)

                    # ---------------- ÇIKIŞ ----------------
                    elif satir["İşlem"] == "ÇIKIŞ":

                        mask = (df_stok['kod'] == kod) & (df_stok['adres'] == kaynak)

                        if mask.any():
                            df_stok.loc[mask, 'miktar'] -= miktar

                    # ---------------- TRANSFER ----------------
                    elif satir["İşlem"] == "İÇ TRANSFER":

                        mask_src = (df_stok['kod'] == kod) & (df_stok['adres'] == kaynak)
                        mask_dst = (df_stok['kod'] == kod) & (df_stok['adres'] == hedef)

                        if mask_src.any():
                            df_stok.loc[mask_src, 'miktar'] -= miktar

                        if mask_dst.any():
                            df_stok.loc[mask_dst, 'miktar'] += miktar
                        else:
                            df_stok = pd.concat([df_stok, pd.DataFrame([{
                                "kod": kod,
                                "isim": satir["İsim"],
                                "adres": hedef,
                                "miktar": miktar,
                                "durum": satir["Durum"]
                            }])], ignore_index=True)

                db.write("hareketler", yeni_hkt_df, "append")
                db.write("stok", df_stok, "replace")

                st.session_state.gecici_liste = []
                st.success("İşlemler tamamlandı")
                st.rerun()

            except Exception as e:
                st.error(str(e))


def run_transfer():
    run_islem()
