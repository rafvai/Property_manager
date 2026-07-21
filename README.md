# Property Manager

Applicazione desktop per la gestione di case vacanza: immobili, fornitori,
transazioni, scadenze, documenti e report — con interfaccia unica che elimina
le attività ripetitive.

Il progetto è composto da due parti:

| Componente | Tecnologie | Descrizione |
|---|---|---|
| **Client desktop** (`Main.py`) | PySide6, SQLAlchemy, SQLite | L'app usata quotidianamente: dashboard, proprietà, fornitori, report PDF/Excel |
| **License server** (`license_server.py`) | FastAPI, SQLite | Backend su VPS: autenticazione, licenze con grace period, codici invito, distribuzione traduzioni |

## Avvio in sviluppo

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-dev.txt

# Copia e configura le variabili d'ambiente
# (crea un file .env — vedi sezione Configurazione)

python Main.py
```

### Configurazione (`.env`)

```ini
APP_ENV=development           # development | production | saas
DEV_SKIP_LOGIN=true           # solo dev: salta il login
LICENSE_SERVER_URL=https://...  # URL del license server (usa HTTPS!)
```

## Test

```bash
pytest tests/ -v
pytest tests/ -m "not slow"   # esclude i test PBKDF2 lenti
```

## License server (VPS)

```bash
pip install -r requirements-server.txt
# .env obbligatorio:
#   SECRET_KEY=<64 hex, es: python -c "import secrets; print(secrets.token_hex(32))">
#   ADMIN_KEY=<altra stringa casuale — il server rifiuta di partire senza>
uvicorn license_server:app --host 127.0.0.1 --port 8000
```

**Importante — HTTPS**: esponi il server solo dietro un reverse proxy con TLS
(Caddy lo fa in due righe con certificato Let's Encrypt automatico):

```
# Caddyfile
licenze.tuodominio.it {
    reverse_proxy 127.0.0.1:8000
}
```

Poi imposta `LICENSE_SERVER_URL=https://licenze.tuodominio.it` nel client.
Senza TLS le credenziali degli utenti viaggiano in chiaro sulla rete
(il client logga un warning se rileva un URL `http://`).

### Sicurezza integrata

- Password con hash bcrypt, token JWT firmati (HS256)
- Rate limiting sul login: max 5 tentativi falliti / 15 minuti per account
- Admin key obbligatoria e confronto constant-time sugli endpoint `/admin/*`
- Registrazione solo con codice invito; grace period di 7 giorni alla scadenza
- Cache offline del client firmata HMAC con chiave per-installazione (keyring)

## Build eseguibile

```bash
pyinstaller --clean property_manager.spec
```

La CI (`.github/workflows/build.yml`) genera gli eseguibili Windows e macOS
a ogni tag `v*`.

## Struttura

```
Main.py              entry point desktop (AppController: login → dashboard)
config.py            configurazione centralizzata da .env
license_server.py    backend FastAPI licenze (deploy separato su VPS)
database/            modelli SQLAlchemy + connessione
services/            logica di business (proprietà, fornitori, transazioni, …)
views/               viste Qt della dashboard
migrations/          migrazioni Alembic
tests/               test suite pytest (~3.500 righe)
```
