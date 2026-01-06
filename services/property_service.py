class PropertyService:
    """Gestisce le operazioni sulle proprietà"""

    def __init__(self, conn, logger):
        self.conn = conn
        self.cursor = conn.cursor()
        self.logger = logger

    def get_all(self):
        """Recupera tutte le proprietà"""
        try:
            self.cursor.execute("SELECT id, name, address, owner FROM properties")
            rows = self.cursor.fetchall()

            properties = []
            for row in rows:
                properties.append({
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "owner": row[3]
                })
            return properties
        except Exception as e:
            print(f"Errore recupero proprietà: {e}")
            return []

    def get_by_id(self, property_id):
        """Recupera una proprietà per ID"""
        try:
            self.cursor.execute(
                "SELECT id, name, address, owner FROM properties WHERE id = ?",
                (property_id,)
            )
            row = self.cursor.fetchone()

            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "address": row[2],
                    "owner": row[3]
                }
            return None
        except Exception as e:
            print(f"Errore recupero proprietà: {e}")
            return None

    def create(self, name, address, owner):
        """Crea una nuova proprietà"""
        try:
            self.cursor.execute(
                "INSERT INTO properties (name, address, owner) VALUES (?, ?, ?)",
                (name, address, owner)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Errore creazione proprietà: {e}")
            return None

    def update(self, property_id, name=None, address=None, owner=None):
        """Aggiorna una proprietà esistente"""
        try:
            updates = []
            params = []

            if name:
                updates.append("name = ?")
                params.append(name)
            if address:
                updates.append("address = ?")
                params.append(address)
            if owner:
                updates.append("owner = ?")
                params.append(owner)

            if not updates:
                return False

            params.append(property_id)
            query = f"UPDATE properties SET {', '.join(updates)} WHERE id = ?"

            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Errore aggiornamento proprietà: {e}")
            return False

    def delete(self, property_id):
        """Elimina una proprietà"""
        try:
            self.cursor.execute("DELETE FROM properties WHERE id = ?", (property_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Errore eliminazione proprietà: {e}")
            return False