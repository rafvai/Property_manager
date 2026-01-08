class TransactionService:
    """Gestisce le operazioni sulle transazioni"""

    def __init__(self, conn, logger):
        self.conn = conn
        self.cursor = conn.cursor()
        self.logger = logger

    def get_all(self, property_id=None, start_date=None, end_date=None):
        """Recupera tutte le transazioni con filtri opzionali"""
        query = """
            SELECT id, property_id, date, type, amount, provider, service
            FROM transactions
            WHERE 1=1
        """
        params = []

        if property_id:
            query += " AND property_id = ?"
            params.append(property_id)

        if start_date and end_date:
            query += """ AND date(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2))
                        BETWEEN date(?) AND date(?)"""
            params.append(start_date)
            params.append(end_date)

        query += " ORDER BY date DESC"

        try:
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()

            transactions = []
            for row in rows:
                transactions.append({
                    "id": row[0],
                    "property_id": row[1],
                    "date": row[2],
                    "type": row[3],
                    "amount": row[4],
                    "provider": row[5],
                    "service": row[6]
                })
            return transactions
        except Exception as e:
            self.logger.error(f"TransactionService:Errore recupero transazioni: {e}")
            return []

    def get_monthly_summary(self, year, property_id=None):
        """Recupera il riepilogo mensile per un anno"""
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        query = """
            SELECT 
                CAST(substr(date, 4, 2) AS INTEGER) as month,
                type,
                SUM(amount) as total
            FROM transactions
            WHERE 
                date(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2))
                BETWEEN date(?) AND date(?)
        """
        params = [start_date, end_date]

        if property_id:
            query += " AND property_id = ?"
            params.append(property_id)

        query += " GROUP BY month, type ORDER BY month ASC"

        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            self.logger.error(f"TransactionService:Errore recupero riepilogo mensile: {e}")
            return []

    def create(self, property_id, date, trans_type, amount, provider, service):
        """Crea una nuova transazione"""
        try:
            self.cursor.execute("""
                INSERT INTO transactions (property_id, date, type, amount, provider, service)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (property_id, date, trans_type, amount, provider, service))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            self.logger.error(f"TransactionService:Errore creazione transazione: {e}")
            return None

    def update(self, transaction_id, **kwargs):
        """Aggiorna una transazione"""
        allowed_fields = ['property_id', 'date', 'type', 'amount', 'provider', 'service']
        updates = []
        params = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return False

        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"

        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"TransactionService:Errore aggiornamento transazione: {e}")
            return False

    def delete(self, transaction_id):
        """Elimina una transazione"""
        try:
            self.cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"TransactionService:Errore eliminazione transazione: {e}")
            return False

    def get_balance(self, property_id=None, end_date=None):
        """Calcola il saldo totale"""
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'Entrata' THEN amount ELSE 0 END), 0) as entrate,
                COALESCE(SUM(CASE WHEN type = 'Uscita' THEN amount ELSE 0 END), 0) as uscite
            FROM transactions
            WHERE 1=1
        """
        params = []

        if property_id:
            query += " AND property_id = ?"
            params.append(property_id)

        if end_date:
            query += """ AND date(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) <= date(?)"""
            params.append(end_date)

        try:
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            entrate = row[0] if row else 0
            uscite = row[1] if row else 0
            return entrate - uscite
        except Exception as e:
            self.logger.error(f"TransactionService:Errore calcolo saldo: {e}")
            return 0