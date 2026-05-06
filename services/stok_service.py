from core import db

# --- STOK HESAPLA ---
def get_stok(malzeme=None, lokasyon=None):
    query = """
    SELECT malzeme,
           hedef as lokasyon,
           SUM(miktar) as stok
    FROM hareketler
    GROUP BY malzeme, hedef
    """

    return db.fetch(query)

# --- HAREKET EKLE ---
def hareket_ekle(data):
    db.execute("""
    INSERT INTO hareketler (tarih, malzeme, miktar, hareket_tipi, kaynak, hedef, referans)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["tarih"],
        data["malzeme"],
        data["miktar"],
        data["tip"],
        data["kaynak"],
        data["hedef"],
        data.get("ref", "")
    ))

# --- STOK KONTROL ---
def stok_yeterli_mi(malzeme, miktar):
    df = db.fetch("""
    SELECT SUM(miktar) as stok FROM hareketler WHERE malzeme=?
    """, (malzeme,))
    
    mevcut = df.iloc[0]["stok"] if not df.empty else 0
    return mevcut >= miktar
