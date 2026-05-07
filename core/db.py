import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False, timeout=30)

def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.cursor()
        # Tablo oluşturma komutları aynı kalıyor...
        cur.execute("CREATE TABLE IF NOT EXISTS stok (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, isim TEXT, adres TEXT, miktar REAL, durum TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS hareketler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, islem TEXT, kod TEXT, isim TEXT, kaynak TEXT, hedef TEXT, miktar REAL, user TEXT, aciklama TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS urun_listesi (kod TEXT PRIMARY KEY, isim TEXT, birim TEXT, adres TEXT)")
        c.commit()

def read(table):
    try:
        with conn() as c:
            return pd.read_sql_query(f"SELECT * FROM {table}", c)
    except:
        return pd.DataFrame()

def write(table, df):
    # Bu fonksiyon stok tablosunu güncellerken tabloyu overwrite etmeye devam eder
    with conn() as c:
        df.to_sql(table, c, if_exists="replace", index=False)

# --- PATRONUN İSTEDİĞİ KESİN ÇÖZÜM: SADECE INSERT ---
def insert(table, data_dict):
    """Veriyi komple tabloyu okumadan doğrudan SQL ile ekler (Hızlı ve Güvenli)"""
    with conn() as c:
        cols = ', '.join(data_dict.keys())
        placeholders = ', '.join(['?'] * len(data_dict))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        c.execute(sql, list(data_dict.values()))
        c.commit()

def sync_to_drive():
    g_conn = st.connection("gsheets", type=GSheetsConnection)
    for t in ["stok", "hareketler"]:
        df = read(t)
        if not df.empty:
            g_conn.update(worksheet=t.capitalize(), data=df)

def sync_from_drive():
    # Mevcut kodun aynısı...
    pass
