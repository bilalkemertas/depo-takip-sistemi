import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

DB_NAME = "wms.db"


# -------------------------
# CONNECTION
# -------------------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


# -------------------------
# INIT DB
# -------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # STOK
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

    # HAREKETLER
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
        user TEXT
    )
    """)

    # SAYIM
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sayim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oturum TEXT,
        tarih TEXT,
        adres TEXT,
        kod TEXT,
        miktar REAL,
        user TEXT
    )
    """)

    conn.commit()
    conn.close()


# -------------------------
# GENERIC READ
# -------------------------
def read_table(table):
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df


# -------------------------
# WRITE (REPLACE MODE - MVP)
# -------------------------
def write_table(table, df):
    conn = get_conn()
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()


# -------------------------
# LOG SYSTEM
# -------------------------
def add_log(islem, kod, isim, kaynak, hedef, miktar, user):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO hareketler
        (tarih, islem, kod, isim, kaynak, hedef, miktar, user)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        islem, kod, isim, kaynak, hedef, miktar, user
    ))

    conn.commit()
    conn.close()
