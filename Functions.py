import sqlite3

import fitz
import requests
import json

DB_NAME = "property_manager.db"

def extract_text_from_pdf(path):
    text = ""
    try:
        with fitz.open(path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        print(f"❌ Errore nell'estrazione del testo: {e}")
        return ""
    else:
        print("Testo estratto correttamente")

    if not text.strip():
        print("⚠️ Nessun testo estratto: il PDF potrebbe essere una scansione (immagine).")
        return ""

    return text

def classify_text_llm(text):
    prompt = f"""
        Sei il mio asssitente contabile, del testo che ti do devi trovare la data di fatturazione
        Text:
        {text[:2000]}
        Answer only the JSON:
        """
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False
        })

        response.raise_for_status()  # lancia eccezione se status ≠ 200
        raw_output = response.json()["response"].strip()

        # Prova a fare parsing JSON
        parsed = json.loads(raw_output)
        return parsed
    except Exception as e:
        print("Errore nel parsing LLM:", e)
        return None


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabella proprietà
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        owner TEXT NOT NULL
    )
    """)

    # Tabella movimenti contabili
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT CHECK(type IN ('Entrata','Uscita')) NOT NULL,
        amount REAL NOT NULL,
        provider TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    )
    """)

    conn.commit()
    return conn

def get_dati_proprieta():
    """
    Restituisce tutte le proprietà presenti nel DB come lista di dizionari.
    """
    properties = []
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.execute("SELECT name, address, owner, id FROM properties")
            rows = cursor.fetchall()
            for r in rows:
                properties.append({
                    "name": r[0],
                    "address": r[1],
                    "owner": r[2],
                    "id": r[3]
                })
    except Exception as e:
        print("Errore nel recupero proprietà:", e)
    return properties
