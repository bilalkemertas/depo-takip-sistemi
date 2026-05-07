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
        st.error(f"Katalog hatası: {e}")
        return []

def run_islem():
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    st.subheader("Stok Hareketleri")

    move_type = st.selectbox("İşlem", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
    katalog = get_katalog()

    sec = st.selectbox("Ürün", ["+ MANUEL"] + katalog)

    kod = st.text_input("Kod")
    miktar = st.number_input("Miktar", min_value=0.0)

    kaynak = st.text_input("Kaynak")
    hedef = st.text_input("Hedef")

    if st.button("Listeye Ekle"):
        if kod and miktar > 0:
            st.session_state.gecici_liste.append({
                "islem": move_type,
                "kod": kod.strip().upper(),
                "isim": sec.split(" | ")[1] if " | " in sec else "MANUEL",
                "miktar": miktar,
                "kaynak": kaynak.strip().upper(),
                "hedef": hedef.strip().upper()
            })
            st.success("Eklendi")

    if st.session_state.gecici_liste:
        st.write(st.session_state.gecici_liste)

        if st.button("TÜM HAREKETLERİ İŞLE"):

            try:
                df_stok = db.read("stok")

                if df_stok.empty:
                    df_stok = pd.DataFrame(columns=["kod","isim","adres","miktar","durum"])

                df_stok['kod'] = df_stok['kod'].astype(str).str.upper()
                df_stok['adres'] = df_stok['adres'].astype(str).str.upper()

                islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                for satir in st.session_state.gecici_liste:

                    # --- STOK GÜNCELLE ---
                    if satir["islem"] == "GİRİŞ":
                        mask = (df_stok['kod'] == satir["kod"]) & (df_stok['adres'] == satir["hedef"])

                        if mask.any():
                            df_stok.loc[mask, 'miktar'] += satir["miktar"]
                        else:
                            yeni = pd.DataFrame([{
                                "kod": satir["kod"],
                                "isim": satir["isim"],
                                "adres": satir["hedef"],
                                "miktar": satir["miktar"],
                                "durum": "OK"
                            }])
                            df_stok = pd.concat([df_stok, yeni], ignore_index=True)

                    elif satir["islem"] == "ÇIKIŞ":
                        mask = (df_stok['kod'] == satir["kod"]) & (df_stok['adres'] == satir["kaynak"])

                        if mask.any():
                            df_stok.loc[mask, 'miktar'] = df_stok.loc[mask, 'miktar'] - satir["miktar"]

                    # --- HAREKETİ SADECE INSERT ET ---
                    db.insert("hareketler", {
                        "tarih": islem_zamani,
                        "islem": satir["islem"],
                        "kod": satir["kod"],
                        "isim": satir["isim"],
                        "kaynak": satir["kaynak"],
                        "hedef": satir["hedef"],
                        "miktar": satir["miktar"]
                    })

                # SADECE STOK TABLOSUNU YAZ
                db.write("stok", df_stok)

                # Drive sync
                db.sync_to_drive()

                st.success("İşlemler tamamlandı")
                st.session_state.gecici_liste = []
                st.cache_data.clear()
                st.rerun()

            except Exception as e:
                st.error(f"Hata: {e}")

def run_transfer():
    run_islem()
