import sqlite3
import pandas as pd

DB_NAME = "wms.db"

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # STOK HAREKETLERİ
    c.execute("""
    CREATE TABLE IF NOT EXISTS hareketler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        urun TEXT,
        miktar REAL,
        islem TEXT,
        kaynak TEXT,
        hedef TEXT
    )
    """)

    # SAYIM
    c.execute("""
    CREATE TABLE IF NOT EXISTS sayim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        urun TEXT,
        miktar REAL
    )
    """)

    conn.commit()
    conn.close()

def insert(table, data: dict):
    conn = get_conn()
    keys = ','.join(data.keys())
    qmarks = ','.join(['?'] * len(data))
    values = tuple(data.values())

    conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({qmarks})", values)
    conn.commit()
    conn.close()

def read(table):
    conn = get_conn()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df
