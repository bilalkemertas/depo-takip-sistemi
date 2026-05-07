import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False, timeout=60)

def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS stok (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, isim TEXT, adres TEXT, miktar REAL, durum TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS hareketler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, islem TEXT, kod TEXT, isim TEXT, kaynak TEXT, hedef TEXT, miktar REAL, user TEXT, aciklama TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS urun_listesi (kod TEXT PRIMARY KEY, isim TEXT, birim TEXT, adres TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS mal_kabul (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, irsaliye_no TEXT, siparis_no TEXT, tedarikci TEXT, kod TEXT, isim TEXT, miktar REAL, adres TEXT, personel TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, personel TEXT, islem_tipi TEXT, detay TEXT)")
        c.commit()

def read(table):
    try:
        with conn() as c:
            df = pd.read_sql_query(f"SELECT * FROM {table.lower()}", c)
            if not df.empty:
                df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except:
        return pd.DataFrame()

def write(table, df, exists_action='replace'):
    """TABLO ÇAKIŞMA HATASINI ÖNLEYEN GÜNCEL YAZMA MODÜLÜ"""
    table_name = table.lower()
    with conn() as c:
        if exists_action == 'append':
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            df.to_sql(table_name, c, if_exists='append', index=False)
        else:
            # HATANIN ÇÖZÜMÜ: Tabloyu silmek yerine içini boşaltıp veriyi basıyoruz
            try:
                c.execute(f"DELETE FROM {table_name}")
                df.to_sql(table_name, c, if_exists='append', index=False)
            except:
                # Tablo hiç yoksa normal akışa dön
                df.to_sql(table_name, c, if_exists='replace', index=False)

def sync_to_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        tablolar = {"stok": "Stok", "hareketler": "Hareketler", "mal_kabul": "Mal_Kabul"}
        for sql_t, sheet_n in tablolar.items():
            df = read(sql_t)
            if not df.empty:
                g_conn.update(worksheet=sheet_n, data=df)
    except Exception as e:
        st.error(f"Drive Hatası: {e}")

def sync_from_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        tablolar = {"Stok": "stok", "Urun_Listesi": "urun_listesi", "Hareketler": "hareketler", "Mal_Kabul": "mal_kabul"}
        for sheet, sql in tablolar.items():
            df = g_conn.read(worksheet=sheet, ttl=0)
            if df is not None and not df.empty:
                df.columns = [str(c).strip().lower() for c in df.columns]
                write(sql, df, 'replace')
    except Exception as e:
        st.error(f"İndirme Hatası: {e}")
