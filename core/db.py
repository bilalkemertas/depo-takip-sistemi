import sqlite3
import pandas as pd

DB_NAME = "wms.db"

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # MALZEME MASTER
    c.execute("""
    CREATE TABLE IF NOT EXISTS malzemeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT UNIQUE,
        ad TEXT,
        birim TEXT
    )
    """)

    # LOKASYON
    c.execute("""
    CREATE TABLE IF NOT EXISTS lokasyonlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT UNIQUE,
        aciklama TEXT
    )
    """)

    # HAREKETLER
    c.execute("""
    CREATE TABLE IF NOT EXISTS hareketler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        malzeme TEXT,
        miktar REAL,
        hareket_tipi TEXT,
        kaynak TEXT,
        hedef TEXT,
        referans TEXT
    )
    """)

    # REZERVASYON
    c.execute("""
    CREATE TABLE IF NOT EXISTS rezervasyon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        malzeme TEXT,
        miktar REAL,
        lokasyon TEXT,
        durum TEXT
    )
    """)

    # SAYIM
    c.execute("""
    CREATE TABLE IF NOT EXISTS sayim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        malzeme TEXT,
        lokasyon TEXT,
        sayilan REAL
    )
    """)

    conn.commit()
    conn.close()

# --- GENERIC ---
def execute(query, params=()):
    conn = get_conn()
    conn.execute(query, params)
    conn.commit()
    conn.close()

def fetch(query, params=()):
    conn = get_conn()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df
