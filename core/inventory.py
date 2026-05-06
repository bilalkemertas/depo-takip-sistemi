from core import db


# ---------------- STOCK CHECK ----------------
def check_stock(kod, adres, miktar):
    df = db.read("stok")

    match = df[
        (df["kod"] == kod) &
        (df["adres"] == adres)
    ]

    if match.empty:
        return False, "STOK YOK"

    mevcut = match["miktar"].sum()

    if mevcut < miktar:
        return False, "YETERSİZ STOK"

    return True, "OK"


# ---------------- BLOCK CONTROL ----------------
def is_blocked(kod, adres):
    df = db.read("blokeli_stok")

    match = df[
        (df["kod"] == kod) &
        (df["adres"] == adres)
    ]

    return not match.empty
