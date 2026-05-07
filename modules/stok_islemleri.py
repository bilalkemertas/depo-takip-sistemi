import streamlit as st
from core.services import get_stok, create_urun

def run():

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
        except Exception as e:
            st.error(str(e))
for satir in isleme_alinacaklar:

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

    yeni_hkt_df = pd.concat([yeni_hkt_df, pd.DataFrame([yeni_hkt])], ignore_index=True)

    kod = satir["Kod"]
    miktar = satir["Miktar"]
    kaynak = satir["Kaynak"]
    hedef = satir["Hedef"]

    # -------------------------
    # GİRİŞ
    # -------------------------
    if satir["İşlem"] == "GİRİŞ":

        mask = (df_stok['kod'] == kod) & (df_stok['adres'] == hedef)

        if mask.any():
            df_stok.loc[mask, 'miktar'] += miktar
        else:
            yeni = pd.DataFrame([{
                "kod": kod,
                "isim": satir["İsim"],
                "adres": hedef,
                "miktar": miktar,
                "durum": satir["Durum"]
            }])
            df_stok = pd.concat([df_stok, yeni], ignore_index=True)

    # -------------------------
    # ÇIKIŞ
    # -------------------------
    elif satir["İşlem"] == "ÇIKIŞ":

        mask = (df_stok['kod'] == kod) & (df_stok['adres'] == kaynak)

        if not mask.any():
            raise Exception(f"Stok bulunamadı: {kod} / {kaynak}")

        mevcut = df_stok.loc[mask, 'miktar'].values[0]

        if mevcut < miktar:
            raise Exception(f"Yetersiz stok: {kod} ({mevcut})")

        df_stok.loc[mask, 'miktar'] -= miktar

    # -------------------------
    # İÇ TRANSFER (ASIL EKSİK BUYDU)
    # -------------------------
    elif satir["İşlem"] == "İÇ TRANSFER":

        # KAYNAKTAN DÜŞ
        mask_src = (df_stok['kod'] == kod) & (df_stok['adres'] == kaynak)

        if not mask_src.any():
            raise Exception(f"Kaynak stok yok: {kod} / {kaynak}")

        mevcut = df_stok.loc[mask_src, 'miktar'].values[0]

        if mevcut < miktar:
            raise Exception(f"Yetersiz stok: {kod} ({mevcut})")

        df_stok.loc[mask_src, 'miktar'] -= miktar

        # HEDEFE EKLE
        mask_dst = (df_stok['kod'] == kod) & (df_stok['adres'] == hedef)

        if mask_dst.any():
            df_stok.loc[mask_dst, 'miktar'] += miktar
        else:
            yeni = pd.DataFrame([{
                "kod": kod,
                "isim": satir["İsim"],
                "adres": hedef,
                "miktar": miktar,
                "durum": satir["Durum"]
            }])
            df_stok = pd.concat([df_stok, yeni], ignore_index=True)
