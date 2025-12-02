from datetime import datetime


class DeadlineService:
    """Gestisce le operazioni sulle scadenze"""

    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()

    def get_all(self, property_id=None, include_completed=False):
        """Recupera tutte le scadenze con filtri opzionali"""
        query = """
            SELECT id, property_id, title, description, due_date, completed, created_at
            FROM deadlines
            WHERE 1=1
        """
        params = []

        if property_id:
            query += " AND property_id = ?"
            params.append(property_id)

        if not include_completed:
            query += " AND completed = 0"

        query += " ORDER BY due_date ASC"

        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            deadlines = []
            for row in rows:
                deadlines.append({
                    "id": row[0],
                    "property_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "due_date": row[4],
                    "completed": row[5],
                    "created_at": row[6]
                })
            return deadlines
        except Exception as e:
            print(f"Errore recupero scadenze: {e}")
            return []

    def get_next_deadline(self, property_id=None):
        """Recupera la prossima scadenza non completata"""
        query = """
            SELECT id, property_id, title, description, due_date, completed
            FROM deadlines
            WHERE completed = 0
        """
        params = []

        if property_id:
            query += " AND property_id = ?"
            params.append(property_id)

        query += " AND date(due_date) >= date('now') ORDER BY due_date ASC LIMIT 1"

        try:
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "property_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "due_date": row[4],
                    "completed": row[5]
                }
            return None
        except Exception as e:
            print(f"Errore recupero prossima scadenza: {e}")
            return None

    def get_by_date(self, date_str):
        """Recupera scadenze per una data specifica (formato: YYYY-MM-DD)"""
        try:
            self.cursor.execute("""
                SELECT id, property_id, title, description, completed
                FROM deadlines
                WHERE due_date = ?
                ORDER BY title ASC
            """, (date_str,))

            rows = self.cursor.fetchall()
            deadlines = []
            for row in rows:
                deadlines.append({
                    "id": row[0],
                    "property_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "completed": row[4]
                })
            return deadlines
        except Exception as e:
            print(f"Errore recupero scadenze per data: {e}")
            return []

    def create(self, title, due_date, description=None, property_id=None):
        """Crea una nuova scadenza"""
        try:
            self.cursor.execute("""
                INSERT INTO deadlines (property_id, title, description, due_date, completed)
                VALUES (?, ?, ?, ?, 0)
            """, (property_id, title, description, due_date))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Errore creazione scadenza: {e}")
            return None

    def update(self, deadline_id, **kwargs):
        """Aggiorna una scadenza"""
        allowed_fields = ['title', 'description', 'due_date', 'completed', 'property_id']
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return False

        params.append(deadline_id)
        query = f"UPDATE deadlines SET {', '.join(updates)} WHERE id = ?"

        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Errore aggiornamento scadenza: {e}")
            return False

    def mark_completed(self, deadline_id):
        """Segna una scadenza come completata"""
        return self.update(deadline_id, completed=1)

    def delete(self, deadline_id):
        """Elimina una scadenza"""
        try:
            self.cursor.execute("DELETE FROM deadlines WHERE id = ?", (deadline_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Errore eliminazione scadenza: {e}")
            return False