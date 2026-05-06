from core import db
from core.inventory import check_stock, is_blocked


# ---------------- SAFE MOVE ----------------
def transfer(user, islem, kod, isim, src, dst, miktar):

    stok = db.read("stok")

    # BLOCK CHECK
    if is_blocked(kod, src):
        return False, "BLOKE STOK - ÇIKIŞ YASAK"

    if islem in ["CIKIS", "TRANSFER"]:
        ok, msg = check_stock(kod, src, miktar)
        if not ok:
            return False, msg

    # ---------------- APPLY LOGIC ----------------
    if islem == "GIRIS":

        mask = (stok["kod"] == kod) & (stok["adres"] == dst)

        if mask.any():
            stok.loc[mask, "miktar"] += miktar
        else:
            stok = stok.append({
                "kod": kod,
                "isim": isim,
                "adres": dst,
                "miktar": miktar,
                "durum": "Kullanılabilir"
            }, ignore_index=True)

    elif islem == "CIKIS":

        mask = (stok["kod"] == kod) & (stok["adres"] == src)
        stok.loc[mask, "miktar"] -= miktar

    elif islem == "TRANSFER":

        src_mask = (stok["kod"] == kod) & (stok["adres"] == src)
        dst_mask = (stok["kod"] == kod) & (stok["adres"] == dst)

        stok.loc[src_mask, "miktar"] -= miktar

        if dst_mask.any():
            stok.loc[dst_mask, "miktar"] += miktar
        else:
            stok = stok.append({
                "kod": kod,
                "isim": isim,
                "adres": dst,
                "miktar": miktar,
                "durum": "Kullanılabilir"
            }, ignore_index=True)

    # NEGATIVE STOCK GUARD
    stok["miktar"] = stok["miktar"].apply(lambda x: max(0, x))

    db.write("stok", stok)

    db.log(user, islem, f"{kod} {src}->{dst} {miktar}")

    return True, "OK"
