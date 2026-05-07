import pandas as pd
from core import db


# -------------------------
# STOK GETİR
# -------------------------
def get_stok():
    return db.read("stok")


# -------------------------
# STOK GÜNCELLE
# -------------------------
def update_stok(kod, miktar_degisim):

    df = db.read("stok")

    if kod not in df["kod"].values:
        raise Exception(f"Ürün bulunamadı: {kod}")

    df.loc[df["kod"] == kod, "miktar"] += miktar_degisim

    if (df.loc[df["kod"] == kod, "miktar"] < 0).any():
        raise Exception("Yetersiz stok")

    db.write("stok", df, "replace")


# -------------------------
# YENİ ÜRÜN EKLE
# -------------------------
def create_urun(kod, isim, adres=""):

    df = db.read("stok")

    if kod in df["kod"].values:
        raise Exception("Ürün zaten var")

    yeni = pd.DataFrame([{
        "kod": kod,
        "isim": isim,
        "miktar": 0,
        "adres": adres
    }])

    df = pd.concat([df, yeni])
    db.write("stok", df, "replace")


# -------------------------
# HAREKET YAZ
# -------------------------
def log_hareket(tip, kod, isim, miktar, kaynak="", hedef=""):

    df = pd.DataFrame([{
        "tarih": pd.Timestamp.now(),
        "tip": tip,
        "kod": kod,
        "isim": isim,
        "miktar": miktar,
        "kaynak": kaynak,
        "hedef": hedef
    }])

    db.write("hareketler", df, "append")


# -------------------------
# MAL KABUL (GERÇEK İŞLEM)
# -------------------------
def mal_kabul(kod, isim, miktar, tedarikci):

    df = db.read("stok")

    if kod not in df["kod"].values:
        create_urun(kod, isim)

    update_stok(kod, miktar)

    log_hareket("GIRIS", kod, isim, miktar)

    df_kabul = pd.DataFrame([{
        "tarih": pd.Timestamp.now(),
        "irsaliye": "",
        "tedarikci": tedarikci,
        "kod": kod,
        "isim": isim,
        "miktar": miktar
    }])

    db.write("mal_kabul", df_kabul, "append")


# -------------------------
# TRANSFER (KONTROLLÜ)
# -------------------------
def transfer(kod, miktar, kaynak, hedef):

    df = db.read("stok")

    if kod not in df["kod"].values:
        raise Exception("Ürün bulunamadı")

    mevcut = df.loc[df["kod"] == kod, "miktar"].values[0]

    if mevcut < miktar:
        raise Exception("Yetersiz stok")

    update_stok(kod, -miktar)

    log_hareket("TRANSFER", kod, "", miktar, kaynak, hedef)


# -------------------------
# SAYIM İŞLEMİ
# -------------------------
def sayim_gir(kod, sayilan_miktar):

    df = db.read("stok")

    if kod not in df["kod"].values:
        raise Exception("Ürün bulunamadı")

    mevcut = df.loc[df["kod"] == kod, "miktar"].values[0]
    fark = sayilan_miktar - mevcut

    update_stok(kod, fark)

    log_hareket("SAYIM", kod, "", fark)

    df_sayim = pd.DataFrame([{
        "tarih": pd.Timestamp.now(),
        "kod": kod,
        "miktar": sayilan_miktar
    }])

    db.write("sayim", df_sayim, "append")
