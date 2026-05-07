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

# --- SENİN VERDİĞİN SAF WRITE FONKSİYONU (GELİŞTİRİLMİŞ) ---
def write(table, df, exists_action='replace'):
    with conn() as c:
        # exists_action 'replace' ise overwrite, 'append' ise insert (insert into) yapar
        df.to_sql(table, c, if_exists=exists_action, index=False)

def sync_to_drive():
    g_conn = st.connection("gsheets", type=GSheetsConnection)
    for t in ["stok", "hareketler"]:
        df = read(t)
        if not df.empty:
            g_conn.update(worksheet=t.capitalize(), data=df)

def sync_from_drive():
    g_conn = st.connection("gsheets", type=GSheetsConnection)
    tablolar = {"Stok": "stok", "Urun_Listesi": "urun_listesi", "Hareketler": "hareketler"}
    for sheet, sql in tablolar.items():
        try:
            df = g_conn.read(worksheet=sheet, ttl=0)
            if not df.empty:
                df.columns = [str(c).strip().lower() for c in df.columns]
                write(sql, df, 'replace')
        except: pass
