#!/usr/bin/env python3
"""
admin_cli.py — Pannello admin per Property Manager License Server

Uso:
    python admin_cli.py <comando> [opzioni]

Variabili ambiente:
    LICENSE_SERVER_URL  URL del server (es. https://mio-vps.com)
    ADMIN_KEY           Chiave admin segreta

Esempi:
    python admin_cli.py stats
    python admin_cli.py list-users
    python admin_cli.py create-invite --uses 1 --days 90 --note "Beta tester Mario"
    python admin_cli.py list-invites
    python admin_cli.py extend 3 --days 90
    python admin_cli.py suspend 3
    python admin_cli.py activate 3
    python admin_cli.py promote 3
    python admin_cli.py demote 3
    python admin_cli.py log 3
    python admin_cli.py delete 3
"""

import argparse
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Installa requests: pip install requests")
    sys.exit(1)

SERVER_URL = os.getenv("LICENSE_SERVER_URL", "http://localhost:8000").rstrip("/")
ADMIN_KEY  = os.getenv("ADMIN_KEY", "")

HEADERS = {"X-Admin-Key": ADMIN_KEY, "Content-Type": "application/json"}


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def req(method, path, **kwargs):
    url  = f"{SERVER_URL}{path}"
    resp = getattr(requests, method)(url, headers=HEADERS, timeout=10, **kwargs)
    if resp.status_code not in (200, 201):
        print(f"❌ Errore {resp.status_code}: {resp.text}")
        sys.exit(1)
    return resp.json()


def fmt_date(s):
    if not s:
        return "—"
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s


def days_label(n):
    if n > 14:
        return f"🟢 {n}gg"
    if n > 0:
        return f"🟡 {n}gg"
    return "🔴 scaduta"


def print_table(rows, cols):
    widths = {k: len(k) for k in cols}
    for r in rows:
        for k in cols:
            widths[k] = max(widths[k], len(str(r.get(k, ""))))

    header = "  ".join(k.ljust(widths[k]) for k in cols)
    sep    = "  ".join("-" * widths[k] for k in cols)
    print(header)
    print(sep)
    for r in rows:
        print("  ".join(str(r.get(k, "")).ljust(widths[k]) for k in cols))


# ─────────────────────────────────────────────
#  COMANDI
# ─────────────────────────────────────────────
def cmd_stats(_args):
    data = req("get", "/admin/stats")
    print("\n📊 Statistiche License Server")
    print("─" * 35)
    print(f"  Utenti totali    {data['total_users']}")
    print(f"  Attivi           {data['active']}")
    print(f"  In scadenza      {data['expiring_soon']}")
    print(f"  Scaduti          {data['expired']}")
    print(f"  Login oggi       {data['logins_today']}")
    print()


def cmd_list_users(_args):
    users = req("get", "/admin/users")
    if not users:
        print("Nessun utente.")
        return

    rows = []
    for u in users:
        rows.append({
            "ID"        : u["id"],
            "Email"     : u["email"],
            "Nome"      : u["full_name"] or "—",
            "Piano"     : u["plan"],
            "Stato"     : u["status"],
            "Scadenza"  : u["expires_at"][:10],
            "Giorni"    : days_label(u["days_left"]),
            "Ultimo acc": fmt_date(u["last_login"])[:10] if u["last_login"] else "mai",
            "Accessi"   : u["login_count"]
        })

    print(f"\n👥 Utenti registrati ({len(rows)})\n")
    print_table(rows, ["ID", "Email", "Nome", "Piano", "Stato", "Scadenza", "Giorni", "Ultimo acc", "Accessi"])
    print()


def cmd_create_invite(args):
    payload = {
        "max_uses"    : args.uses,
        "expires_days": args.days,
        "plan"        : args.plan,
        "note"        : args.note or ""
    }
    data = req("post", "/admin/invites", json=payload)
    print("\n✅ Codice invito creato:")
    print(f"   Codice   : {data['code']}")
    print(f"   Piano    : {data['plan']}")
    print(f"   Usi max  : {data['max_uses']}")
    print(f"   Licenza  : {data['expires_days']} giorni dal momento della registrazione")
    print(f"   Note     : {data['note'] or '—'}")
    print("\n   🔗 Condividi questo codice con il tester.\n")


def cmd_list_invites(_args):
    invites = req("get", "/admin/invites")
    if not invites:
        print("Nessun codice invito.")
        return

    rows = []
    for i in invites:
        rows.append({
            "Codice"  : i["code"],
            "Piano"   : i["plan"],
            "Gg lic." : i["expires_days"],
            "Usato"   : f"{i['used_count']}/{i['max_uses']}",
            "Attivo"  : "✓" if i["is_active"] else "✗",
            "Note"    : (i["note"] or "")[:30]
        })

    print(f"\n🎟️  Codici invito ({len(rows)})\n")
    print_table(rows, ["Codice", "Piano", "Gg lic.", "Usato", "Attivo", "Note"])
    print()


def cmd_revoke_invite(args):
    req("patch", f"/admin/invites/{args.code}/revoke")
    print(f"✅ Codice '{args.code}' revocato.")


def cmd_extend(args):
    data = req("patch", f"/admin/users/{args.user_id}/extend",
               params={"days": args.days})
    print(f"✅ Utente {args.user_id}: licenza estesa a {data['new_expires_at']}")


def cmd_suspend(args):
    req("patch", f"/admin/users/{args.user_id}/suspend")
    print(f"⛔ Utente {args.user_id} sospeso.")


def cmd_activate(args):
    req("patch", f"/admin/users/{args.user_id}/activate")
    print(f"✅ Utente {args.user_id} riattivato.")


def cmd_notes(args):
    req("patch", f"/admin/users/{args.user_id}/notes",
        params={"notes": args.text})
    print(f"✅ Note aggiornate per utente {args.user_id}.")


def cmd_log(args):
    entries = req("get", f"/admin/login-log/{args.user_id}")
    if not entries:
        print("Nessun accesso registrato.")
        return

    print(f"\n📋 Log accessi utente {args.user_id} (ultimi {len(entries)})\n")
    rows = []
    for e in entries:
        rows.append({
            "Data"  : fmt_date(e["timestamp"]),
            "IP"    : e["ip"] or "—",
            "Esito" : "✓ OK" if e["success"] else "✗ KO",
            "Motivo": e["reason"] or ""
        })
    print_table(rows, ["Data", "IP", "Esito", "Motivo"])
    print()


def cmd_promote(args):
    req("patch", f"/admin/users/{args.user_id}/promote")
    print(f"✅ Utente {args.user_id} promosso ad admin.")


def cmd_demote(args):
    req("patch", f"/admin/users/{args.user_id}/demote")
    print(f"⬇️  Utente {args.user_id} declassato a utente normale.")


def cmd_delete(args):
    confirm = input(f"Sei sicuro di voler eliminare l'utente {args.user_id}? (digita 'CONFERMA'): ")
    if confirm != "CONFERMA":
        print("Operazione annullata.")
        return
    req("delete", f"/admin/users/{args.user_id}")
    print(f"🗑️  Utente {args.user_id} eliminato.")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    if not ADMIN_KEY:
        print("⚠️  Imposta la variabile ADMIN_KEY prima di usare l'admin CLI")
        print("   export ADMIN_KEY=la-tua-chiave-segreta")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Property Manager — Admin CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats",       help="Statistiche generali")
    sub.add_parser("list-users",  help="Lista tutti gli utenti")

    p = sub.add_parser("create-invite", help="Crea codice invito")
    p.add_argument("--uses", type=int, default=1,   help="Usi massimi (default 1)")
    p.add_argument("--days", type=int, default=90,  help="Durata licenza in giorni (default 90)")
    p.add_argument("--plan", default="beta",         help="Piano: beta|monthly|annual")
    p.add_argument("--note", default="",             help="Nota (es. nome del tester)")

    sub.add_parser("list-invites", help="Lista codici invito")

    p = sub.add_parser("revoke-invite", help="Revoca codice invito")
    p.add_argument("code", help="Codice da revocare")

    p = sub.add_parser("extend", help="Estendi licenza utente")
    p.add_argument("user_id", type=int)
    p.add_argument("--days", type=int, default=90, help="Giorni da aggiungere")

    p = sub.add_parser("suspend", help="Sospendi utente")
    p.add_argument("user_id", type=int)

    p = sub.add_parser("activate", help="Riattiva utente")
    p.add_argument("user_id", type=int)

    p = sub.add_parser("notes", help="Aggiorna note admin utente")
    p.add_argument("user_id", type=int)
    p.add_argument("text", help="Testo della nota")

    p = sub.add_parser("log", help="Log accessi utente")
    p.add_argument("user_id", type=int)

    # FIX: promote e demote ora registrati nel parser
    p = sub.add_parser("promote", help="Promuovi utente ad admin")
    p.add_argument("user_id", type=int)

    p = sub.add_parser("demote", help="Rimuovi privilegi admin da utente")
    p.add_argument("user_id", type=int)

    p = sub.add_parser("delete", help="Elimina utente (irreversibile)")
    p.add_argument("user_id", type=int)

    p = sub.add_parser("upload-translations", help="Carica nuovo file translations.db")
    p.add_argument("file", help="Path al file translations.db")

    args = parser.parse_args()
    cmds = {
        "stats"        : cmd_stats,
        "list-users"   : cmd_list_users,
        "create-invite": cmd_create_invite,
        "list-invites" : cmd_list_invites,
        "revoke-invite": cmd_revoke_invite,
        "extend"       : cmd_extend,
        "suspend"      : cmd_suspend,
        "activate"     : cmd_activate,
        "notes"        : cmd_notes,
        "log"          : cmd_log,
        "promote"      : cmd_promote,
        "demote"       : cmd_demote,
        "delete"       : cmd_delete,
        "upload-translations": cmd_upload_translations,
    }
    cmds[args.command](args)


def cmd_upload_translations(args):
    headers_no_json = {"X-Admin-Key": ADMIN_KEY}
    with open(args.file, "rb") as f:
        resp = requests.post(
            f"{SERVER_URL}/admin/translations/upload",
            headers=headers_no_json,
            files={"file": ("translations.db", f, "application/octet-stream")},
            timeout=30
        )
    if resp.status_code not in (200, 201):
        print(f"❌ Errore {resp.status_code}: {resp.text}")
        sys.exit(1)
    data = resp.json()
    print(f"✅ Traduzioni aggiornate ({data['size_bytes']} bytes)")
