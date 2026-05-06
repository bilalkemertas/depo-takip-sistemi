import sqlite3
import pandas as pd
from datetime import datetime

DB = "wms.db"


def conn():
    return sqlite3.connect(DB, check_same_thread=False)


# ---------------- INIT ----------------
def init_db():
    c = conn()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT,
        isim TEXT,
        adres TEXT,
        miktar REAL,
        durum TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hareketler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        islem TEXT,
        kod TEXT,
        isim TEXT,
        kaynak TEXT,
        hedef TEXT,
        miktar REAL,
        user TEXT,
        aciklama TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS blokeli_stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT,
        adres TEXT,
        miktar REAL,
        sebep TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sayim_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oturum TEXT,
        kod TEXT,
        adres TEXT,
        miktar REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        user TEXT,
        action TEXT,
        detay TEXT
    )
    """)

    c.commit()
    c.close()


# ---------------- READ ----------------
def read(table):
    c = conn()
    df = pd.read_sql_query(f"SELECT * FROM {table}", c)
    c.close()
    return df


# ---------------- WRITE (FULL REPLACE MVP) ----------------
def write(table, df):
    c = conn()
    df.to_sql(table, c, if_exists="replace", index=False)
    c.close()


# ---------------- LOG ----------------
def log(user, action, detail):
    c = conn()
    cur = c.cursor()

    cur.execute("""
        INSERT INTO audit_log (tarih, user, action, detay)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user,
        action,
        detail
    ))

    c.commit()
    c.close()
