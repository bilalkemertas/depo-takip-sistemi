import sqlite3
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"


# -----------------------------
# CONNECTION
# -----------------------------
def conn():
    return sqlite3.connect(DB, check_same_thread=False, timeout=60)


# -----------------------------
# INIT DB
# -----------------------------
def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.cursor()

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
            user TEXT,
            aciklama TEXT
        )
        """)

        # URUN LISTESI
        cur.execute("""
        CREATE TABLE IF NOT EXISTS urun_listesi (
            kod TEXT PRIMARY KEY,
            isim TEXT,
            birim TEXT,
            adres TEXT
        )
        """)

        # MAL KABUL
        cur.execute("""
        CREATE TABLE IF NOT EXISTS mal_kabul (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            irsaliye_no TEXT,
            siparis_no TEXT,
            tedarikci TEXT,
            kod TEXT,
            isim TEXT,
            miktar REAL,
            adres TEXT,
            personel TEXT
        )
        """)

        c.commit()


# -----------------------------
# READ
# -----------------------------
def read(table):
    try:
        with conn() as c:
            df = pd.read_sql_query(f"SELECT * FROM {table.lower()}", c)
            return df if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# -----------------------------
# WRITE (SAFE UPSERT STYLE)
# -----------------------------
def write(table, df, exists_action="replace"):
    try:
        with conn() as c:

            if df is None:
                return

            if df.empty:
                return

            df = df.copy()

            # SQLite ID çakışmasını engelle
            if "id" in df.columns:
                df = df.drop(columns=["id"])

            df.to_sql(
                table.lower(),
                c,
                if_exists=exists_action,
                index=False
            )

    except Exception as e:
        st.error(f"DB WRITE ERROR ({table}): {e}")


# -----------------------------
# GOOGLE SHEETS → DB
# -----------------------------
def sync_from_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)

        tablolar = {
            "Stok": "stok",
            "Urun_Listesi": "urun_listesi",
            "Hareketler": "hareketler",
            "Mal_Kabul": "mal_kabul"
        }

        basarili = []
        hatali = []

        for sheet, sql in tablolar.items():
            try:
                df = g_conn.read(worksheet=sheet, ttl=0)

                if df is not None and not df.empty:
                    df.columns = [str(c).strip().lower() for c in df.columns]
                    write(sql, df, "replace")
                    basarili.append(sql)

            except Exception as e:
                hatali.append(f"{sheet}: {str(e)}")

        return basarili, hatali

    except Exception as e:
        return [], [str(e)]


# -----------------------------
# DB → GOOGLE SHEETS
# -----------------------------
def sync_to_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        tablolar = {"stok": "Stok", "hareketler": "Hareketler", "mal_kabul": "Mal_Kabul"}
        for sql_t, sheet_n in tablolar.items():
            df = read(sql_t)
            if not df.empty:
                # Ekranda neyin güncellendiğini görmek için (Debug)
                # st.info(f"{sheet_n} Drive'a gönderiliyor...") 
                g_conn.update(worksheet=sheet_n, data=df)
    except Exception as e:
        st.error(f"Drive Senkronizasyon Hatası: {e}")
            df = read(sql_t)

            if df is not None and not df.empty:
                g_conn.update(worksheet=sheet_n, data=df)

    except Exception as e:
        st.error(f"SYNC ERROR: {e}")
