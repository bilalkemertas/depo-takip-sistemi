import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "wms.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # STOK
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT,
        isim TEXT,
        miktar REAL,
        adres TEXT
    )
    """)

    # HAREKETLER
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hareketler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        tip TEXT,
        kod TEXT,
        isim TEXT,
        miktar REAL,
        kaynak TEXT,
        hedef TEXT
    )
    """)

    # MAL KABUL
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mal_kabul (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        irsaliye TEXT,
        tedarikci TEXT,
        kod TEXT,
        isim TEXT,
        miktar REAL
    )
    """)

    # SAYIM
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sayim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        kod TEXT,
        miktar REAL
    )
    """)

    conn.commit()
    conn.close()

def read(table):
    conn = get_conn()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def write(table, df, mode="append"):
    conn = get_conn()
    df.to_sql(table, conn, if_exists=mode, index=False)
    conn.close()
