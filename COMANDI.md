# 📖 Libretto istruzioni — Property Manager

Promemoria dei comandi principali. Tutti i comandi si lanciano dalla cartella
del progetto (`Property_manager`), salvo dove indicato.

---

## 🖥️ Lavorare in locale

```bash
# Attiva l'ambiente virtuale (una volta per sessione di terminale)
.venv\Scripts\activate

# Avvia l'app in sviluppo (salta il login grazie a DEV_SKIP_LOGIN nel .env)
python Main.py

# Lancia tutti i test (devono essere 316 verdi)
python -m pytest tests/ -q

# Test rapidi (esclude quelli lenti PBKDF2)
python -m pytest tests/ -m "not slow" -q
```

Il file `.env` locale (NON committarlo, è già nel .gitignore):

```ini
APP_ENV=development
DEV_SKIP_LOGIN=true
LICENSE_SERVER_URL=https://il-tuo-dominio.it   # per admin_cli e sync traduzioni
ADMIN_KEY=la-tua-admin-key                     # per admin_cli
```

---

## 👤 Gestione utenti e licenze (admin_cli.py)

Richiede `LICENSE_SERVER_URL` e `ADMIN_KEY` impostati (nel `.env` o come
variabili d'ambiente).

```bash
# ── Nuovo utente: crea un codice invito e passaglielo ──
python admin_cli.py create-invite --days 90 --note "Mario Rossi"
#   → l'utente si registra dall'app con quel codice

# Invito riutilizzabile (es. per 5 tester)
python admin_cli.py create-invite --uses 5 --days 30 --note "beta testers"

# Lista inviti / revoca un invito
python admin_cli.py list-invites
python admin_cli.py revoke-invite CODICE123

# ── Utenti ──
python admin_cli.py list-users            # tutti gli utenti con giorni residui
python admin_cli.py stats                 # statistiche generali
python admin_cli.py log <user_id>         # storico accessi di un utente

# ── Licenze ──
python admin_cli.py extend <user_id> --days 90    # estendi licenza
python admin_cli.py suspend <user_id>             # sospendi account
python admin_cli.py activate <user_id>            # riattiva account
python admin_cli.py notes <user_id> "ha pagato il rinnovo"

# ── Amministratori ──
python admin_cli.py promote <user_id>     # rendi amministratore
python admin_cli.py demote <user_id>      # togli amministratore
python admin_cli.py delete <user_id>      # elimina utente (definitivo!)
```

---

## 🌍 Traduzioni

Le traduzioni vivono in `shared/translations.db` (tabella `translations`:
categoria, chiave, it, en, es). I client in produzione le scaricano dal server.

```bash
# Dopo aver modificato shared/translations.db in locale:
# 1. committa e pusha il file (vedi sezione Git)
# 2. caricalo sul server, altrimenti i client vedono ancora le vecchie:
#    dall'app: menu Traduzioni (admin) → upload
#    oppure via API:
curl -X POST https://il-tuo-dominio.it/admin/translations/upload \
     -H "X-Admin-Key: LA_TUA_ADMIN_KEY" \
     -F "file=@shared/translations.db"
```

---

## 📦 Git: salvare e pubblicare le modifiche

```bash
git status                    # cosa è cambiato
git add .                     # prepara tutto (o: git add file1 file2)
git commit -m "Descrizione della modifica"
git push origin main          # pubblica su GitHub
```

Se il push chiede l'autenticazione, si apre il browser: accedi con l'account
GitHub e riprova.

```bash
# Scaricare le modifiche fatte altrove
git pull origin main

# Vedere la storia
git log --oneline -10
```

---

## 🏗️ Build dell'eseguibile

**Build automatica (GitHub Actions)** — parte SOLO con un tag `v*`:

```bash
git tag v1.0.0
git push origin v1.0.0
# → GitHub → Actions → scarica PropertyManager-Windows / -macOS dagli artifacts
# (oppure: Actions → Build PropertyManager → Run workflow, per lanciarla a mano)
```

**Build locale** (per provarla subito):

```bash
python -m PyInstaller --clean --noconfirm property_manager.spec
# → risultato in dist/PropertyManager/PropertyManager.exe
```

Note build:
- L'icona dell'exe è `assets/app.ico` → sostituisci il file per cambiarla
- Lo splash è `assets/splash.png`
- ⚠️ NON aggiungere `unittest` agli excludes dello spec: matplotlib lo usa
  a runtime e l'app crasha all'avvio

---

## 🌐 Server licenze (VPS)

```bash
# Sul VPS, nella cartella del server:
pip install -r requirements-server.txt

# .env OBBLIGATORIO (il server rifiuta di partire senza ADMIN_KEY):
#   SECRET_KEY=...   genera con: python -c "import secrets; print(secrets.token_hex(32))"
#   ADMIN_KEY=...    idem, un'altra stringa

# Avvio (dietro reverse proxy HTTPS!)
uvicorn license_server:app --host 127.0.0.1 --port 8000

# Caddy per HTTPS automatico (file: Caddyfile)
#   licenze.tuodominio.it {
#       reverse_proxy 127.0.0.1:8000
#   }
```

Controllo rapido che il server sia vivo:

```bash
curl https://il-tuo-dominio.it/health
```

---

## 📂 Dove stanno le cose

| Cosa | Dove |
|---|---|
| Database app (sviluppo) | `%APPDATA%\PropertyManager\property_manager.db` |
| Database app (produzione) | `%APPDATA%\PropertyManager\property_manager_prod.db` |
| Log applicazione | cartella `logs/` (dev) o `%APPDATA%\PropertyManager\logs` |
| Cache licenza offline | `%APPDATA%\PropertyManager\.license_cache` |
| Database licenze (VPS) | `licenses.db` nella cartella del server |
| Config locale | `.env` (mai su git) |
