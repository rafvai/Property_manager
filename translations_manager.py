"""
Sistema di gestione traduzioni per Property Manager
Supporta: Italiano (IT), Spagnolo (ES), Inglese (EN)
"""

class TranslationManager:
    """Gestisce le traduzioni dell'applicazione"""

    def __init__(self):
        self.current_language = "it"
        self.translations = self._load_all_translations()

    def _load_all_translations(self):
        """Carica tutte le traduzioni inline"""
        return {
            "it": {
                "app_title": "🏠 Property Manager",
                "menu": {
                    "dashboard": "Dashboard",
                    "properties": "Le mie proprietà",
                    "documents": "Documenti",
                    "accounting": "Contabilità",
                    "report": "Report",
                    "calendar": "Calendario",
                    "settings": "Impostazioni"
                },
                "common": {
                    "add": "Aggiungi",
                    "edit": "Modifica",
                    "delete": "Elimina",
                    "cancel": "Annulla",
                    "save": "Salva",
                    "yes": "Sì",
                    "no": "No",
                    "property": "Proprietà",
                    "all_properties": "Tutte le proprietà",
                    "period": "Periodo",
                    "income": "Entrata",
                    "expense": "Uscita",
                    "success": "Successo",
                    "error": "Errore",
                    "date": "Data",
                    "description": "Descrizione",
                    "category": "Categoria",
                    "total": "Totale",
                    "type": "Tipo"
                },
                "dashboard": {
                    "title": "Dashboard",
                    "select_property": "Seleziona proprietà:",
                    "movements": "Movimenti",
                    "income_label": "Entrate",
                    "expense_label": "Uscite",
                    "property_info": "📋 Informazioni Proprietà",
                    "next_deadline": "⏰ Prossima Scadenza",
                    "no_deadline": "Nessuna scadenza imminente",
                    "all_ok": "✅ Tutto in regola!",
                    "no_properties": "Nessuna proprietà registrata.",
                    "total_properties": "proprietà totali",
                    "aggregate_view": "📊 Vista aggregata di tutte le proprietà",
                    "click_to_manage": "👥 Clicca per gestire le proprietà",
                    "no_data": "Nessun dato",
                    "period_1_month": "1 mese",
                    "period_6_months": "6 mesi",
                    "period_1_year": "1 anno",
                    "period_3_years": "3 anni"
                },
                "properties": {
                    "title": "Le mie proprietà",
                    "add_property": "+ Aggiungi proprietà",
                    "search_placeholder": "🔍 Cerca per nome o indirizzo...",
                    "no_properties": "📭 Nessuna proprietà trovata",
                    "balance": "Saldo",
                    "documents_short": "doc",
                    "deadlines": "scadenze"
                },
                "documents": {
                    "title": "Documenti",
                    "add_document": "+ Aggiungi documento"
                },
                "accounting": {
                    "title": "Contabilità - Andamento annuale",
                    "year": "Anno",
                    "income_total": "Entrate (€)",
                    "expenses_total": "Uscite (€)",
                    "balance": "Saldo (€)",
                    "no_data_year": "Nessun dato per l'anno selezionato",
                    "quantity": "Quantità in €",
                    "month": "Mese"
                },
                "report": {
                    "title": "Tracking mensile",
                    "new_transaction": "Nuova transazione",
                    "view_transactions": "📋 Visualizza transazioni",
                    "export": "📥 Esporta",
                    "expenses": "Uscite",
                    "income": "Entrate",
                    "filter": "Filtra:",
                    "supplier": "Fornitore",
                    "supplier_name": "Nome fornitore",
                    "amount": "Importo"
                },
                "calendar": {
                    "title": "Calendario",
                    "new_deadline": "Nuova Scadenza"
                },
                "settings": {
                    "title": "Impostazioni"
                },
                "months": {
                    "short": ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"],
                    "full": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
                },
                "weekdays": {
                    "short": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
                }
            },
            "es": {
                "app_title": "Property Manager",
                "menu": {
                    "dashboard": "Panel de Control",
                    "properties": "Mis Propiedades",
                    "documents": "Documentos",
                    "accounting": "Contabilidad",
                    "report": "Informes",
                    "calendar": "Calendario",
                    "settings": "Configuración"
                },
                "common": {
                    "add": "Añadir",
                    "edit": "Editar",
                    "delete": "Eliminar",
                    "cancel": "Cancelar",
                    "save": "Guardar",
                    "yes": "Sí",
                    "no": "No",
                    "property": "Propiedad",
                    "all_properties": "Todas las propiedades",
                    "period": "Período",
                    "income": "Ingreso",
                    "expense": "Gasto",
                    "success": "Éxito",
                    "error": "Error",
                    "date": "Fecha",
                    "description": "Descripción",
                    "category": "Categoría",
                    "total": "Total",
                    "type": "Tipo"
                },
                "dashboard": {
                    "title": "Panel de Control",
                    "select_property": "Seleccionar propiedad:",
                    "movements": "Movimientos",
                    "income_label": "Ingresos",
                    "expense_label": "Gastos",
                    "property_info": "📋 Información de Propiedad",
                    "next_deadline": "⏰ Próximo Vencimiento",
                    "no_deadline": "No hay vencimientos próximos",
                    "all_ok": "✅ ¡Todo en orden!",
                    "no_properties": "No hay propiedades registradas.",
                    "total_properties": "propiedades totales",
                    "aggregate_view": "📊 Vista agregada de todas las propiedades",
                    "click_to_manage": "👥 Haz clic para gestionar propiedades",
                    "no_data": "Sin datos",
                    "period_1_month": "1 mes",
                    "period_6_months": "6 meses",
                    "period_1_year": "1 año",
                    "period_3_years": "3 años"
                },
                "properties": {
                    "title": "Mis Propiedades",
                    "add_property": "+ Añadir propiedad",
                    "search_placeholder": "🔍 Buscar por nombre o dirección...",
                    "no_properties": "📭 No se encontraron propiedades",
                    "balance": "Saldo",
                    "documents_short": "docs",
                    "deadlines": "vencimientos"
                },
                "documents": {
                    "title": "Documentos",
                    "add_document": "+ Añadir documento"
                },
                "accounting": {
                    "title": "Contabilidad - Evolución anual",
                    "year": "Año",
                    "income_total": "Ingresos (€)",
                    "expenses_total": "Gastos (€)",
                    "balance": "Saldo (€)",
                    "no_data_year": "Sin datos para el año seleccionado",
                    "quantity": "Cantidad en €",
                    "month": "Mes"
                },
                "report": {
                    "title": "Seguimiento mensual",
                    "new_transaction": "Nueva transacción",
                    "view_transactions": "📋 Ver transacciones",
                    "export": "📥 Exportar",
                    "expenses": "Gastos",
                    "income": "Ingresos",
                    "filter": "Filtrar:",
                    "supplier": "Proveedor",
                    "supplier_name": "Nombre Proveedor",
                    "amount": "Importe",
                },
                "calendar": {
                    "title": "Calendario",
                    "new_deadline" : "Nueva fecha limite"
                },
                "settings": {
                    "title": "Configuración"
                },
                "months": {
                    "short": ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
                    "full": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                },
                "weekdays": {
                    "short": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                }
            },
            "en": {
                "app_title": "Property Manager",
                "menu": {
                    "dashboard": "Dashboard",
                    "properties": "My Properties",
                    "documents": "Documents",
                    "accounting": "Accounting",
                    "report": "Reports",
                    "calendar": "Calendar",
                    "settings": "Settings"
                },
                "common": {
                    "add": "Add",
                    "edit": "Edit",
                    "delete": "Delete",
                    "cancel": "Cancel",
                    "save": "Save",
                    "yes": "Yes",
                    "no": "No",
                    "property": "Property",
                    "all_properties": "All Properties",
                    "period": "Period",
                    "income": "Income",
                    "expense": "Expense",
                    "success": "Success",
                    "error": "Error",
                    "date": "Data",
                    "description": "Description",
                    "category": "Category",
                    "total": "Total",
                    "type": "Type"
                },
                "dashboard": {
                    "title": "Dashboard",
                    "select_property": "Select property:",
                    "movements": "Movements",
                    "income_label": "Income",
                    "expense_label": "Expenses",
                    "property_info": "📋 Property Information",
                    "next_deadline": "⏰ Next Deadline",
                    "no_deadline": "No upcoming deadlines",
                    "all_ok": "✅ All good!",
                    "no_properties": "No properties registered.",
                    "total_properties": "total properties",
                    "aggregate_view": "📊 Aggregate view of all properties",
                    "click_to_manage": "👥 Click to manage properties",
                    "no_data": "No data",
                    "period_1_month": "1 month",
                    "period_6_months": "6 months",
                    "period_1_year": "1 year",
                    "period_3_years": "3 years"
                },
                "properties": {
                    "title": "My Properties",
                    "add_property": "+ Add property",
                    "search_placeholder": "🔍 Search by name or address...",
                    "no_properties": "📭 No properties found",
                    "balance": "Balance",
                    "documents_short": "docs",
                    "deadlines": "deadlines"
                },
                "documents": {
                    "title": "Documents",
                    "add_document": "+ Add document"
                },
                "accounting": {
                    "title": "Accounting - Annual Overview",
                    "year": "Year",
                    "income_total": "Income (€)",
                    "expenses_total": "Expenses (€)",
                    "balance": "Balance (€)",
                    "no_data_year": "No data for selected year",
                    "quantity": "Amount in €",
                    "month": "Month"
                },
                "report": {
                    "title": "Monthly Tracking",
                    "new_transaction": "New transaction",
                    "view_transactions": "📋 View transactions",
                    "export": "📥 Export",
                    "expenses": "Expenses",
                    "income": "Income",
                    "filter": "Filter:",
                    "supplier": "Supplier",
                    "supplier_name": "Supplier_name",
                    "amount": "Amount",
                },
                "calendar": {
                    "title": "Calendar",
                    "new_deadline": "New deadline",
                },
                "settings": {
                    "title": "Settings"
                },
                "months": {
                    "short": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "full": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                },
                "weekdays": {
                    "short": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                }
            }
        }

    def set_language(self, lang_code):
        """Imposta la lingua corrente"""
        if lang_code in ["it", "es", "en"]:
            self.current_language = lang_code
            return True
        return False

    def get(self, section, key):
        """Ottiene una traduzione"""
        try:
            return self.translations[self.current_language][section][key]
        except KeyError:
            return f"[{section}.{key}]"

    def get_month_labels(self, short=True):
        """Ritorna lista dei mesi nella lingua corrente"""
        try:
            key = "short" if short else "full"
            return self.translations[self.current_language]["months"][key]
        except KeyError:
            return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def get_weekday_labels(self, short=True):
        """Ritorna lista dei giorni della settimana nella lingua corrente"""
        try:
            key = "short" if short else "full"
            return self.translations[self.current_language]["weekdays"][key]
        except KeyError:
            return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# Istanza globale del manager
_translation_manager = None

def get_translation_manager():
    """Ottiene l'istanza globale del TranslationManager"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager