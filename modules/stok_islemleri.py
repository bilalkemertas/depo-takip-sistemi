import streamlit as st
import pandas as pd
from core import db
from datetime import datetime

# -------------------------
# STOK GÖRÜNTÜLE
# -------------------------
def get_stok():
    db.init_db()
    return db.read("stok")


# -------------------------
# ÜRÜN EKLE
# -------------------------
def create_urun(kod, isim):
    conn = db.get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO stok (kod, isim, miktar, adres)
        VALUES (?, ?, ?, ?)
    """, (kod, isim, 0, "DEFAULT"))

    conn.commit()
    conn.close()


# -------------------------
# ANA MODÜL
# -------------------------
def run():

    db.init_db()

    st.title("Stok Yönetimi")

    df = get_stok()
    st.dataframe(df)

    st.subheader("Yeni Ürün")

    kod = st.text_input("Kod")
    isim = st.text_input("İsim")

    if st.button("Ekle"):
        try:
            create_urun(kod, isim)
            st.success("Ürün eklendi")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    # -------------------------
    # TRANSACTION ENGINE (DOĞRU YER)
    # -------------------------
    st.markdown("---")
    st.subheader("📦 Stok Hareket Motoru")

    islem_tipi = st.selectbox("İşlem", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])

    kod_t = st.text_input("Kod")
    isim_t = st.text_input("İsim")
    miktar_t = st.number_input("Miktar", min_value=0.0)

    kaynak = st.text_input("Kaynak (Çıkış/Transfer)")
    hedef = st.text_input("Hedef (Giriş/Transfer)")

    if st.button("İŞLEMİ ÇALIŞTIR"):

        try:
            df_stok = db.read("stok")
            is_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if islem_tipi == "GİRİŞ":

                mask = (df_stok["kod"] == kod_t) & (df_stok["adres"] == hedef)

                if mask.any():
                    df_stok.loc[mask, "miktar"] += miktar_t
                else:
                    df_stok = pd.concat([df_stok, pd.DataFrame([{
                        "kod": kod_t,
                        "isim": isim_t,
                        "miktar": miktar_t,
                        "adres": hedef
                    }])], ignore_index=True)

            elif islem_tipi == "ÇIKIŞ":

                mask = (df_stok["kod"] == kod_t) & (df_stok["adres"] == kaynak)

                if not mask.any():
                    raise Exception("Stok yok")

                mevcut = df_stok.loc[mask, "miktar"].values[0]

                if mevcut < miktar_t:
                    raise Exception("Yetersiz stok")

                df_stok.loc[mask, "miktar"] -= miktar_t

            elif islem_tipi == "İÇ TRANSFER":

                mask_src = (df_stok["kod"] == kod_t) & (df_stok["adres"] == kaynak)

                if not mask_src.any():
                    raise Exception("Kaynak yok")

                mevcut = df_stok.loc[mask_src, "miktar"].values[0]

                if mevcut < miktar_t:
                    raise Exception("Yetersiz stok")

                df_stok.loc[mask_src, "miktar"] -= miktar_t

                mask_dst = (df_stok["kod"] == kod_t) & (df_stok["adres"] == hedef)

                if mask_dst.any():
                    df_stok.loc[mask_dst, "miktar"] += miktar_t
                else:
                    df_stok = pd.concat([df_stok, pd.DataFrame([{
                        "kod": kod_t,
                        "isim": isim_t,
                        "miktar": miktar_t,
                        "adres": hedef
                    }])], ignore_index=True)

            db.write("stok", df_stok, "replace")

            st.success("İşlem tamamlandı")
            st.rerun()

        except Exception as e:
            st.error(str(e))
