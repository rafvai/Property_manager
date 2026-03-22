    def navigate_to_section(self, section_name):
        """
        Naviga a una sezione specifica tramite nome.
        Le chiavi devono corrispondere ESATTAMENTE a quelle usate in update_menu_items()
        di DashboardWindow, altrimenti la navigazione non funziona.
        """
        section_indices = {
            self.tm.get("ETICHETTE", "DASHBOARD")    : 0,
            self.tm.get("ETICHETTE", "PROPERTIES")   : 1,
            self.tm.get("ETICHETTE", "DOCUMENTS")    : 2,
            self.tm.get("ETICHETTE", "FINANZE")      : 3,
            self.tm.get("ETICHETTE", "TRANSAZIONI")  : 4,
            self.tm.get("ETICHETTE", "CALENDAR")     : 5,
            self.tm.get("ETICHETTE", "FORNITORI")    : 6,
            self.tm.get("ETICHETTE", "IMPOSTAZIONI") : 7,
        }

        if section_name in section_indices:
            index = section_indices[section_name]
            self.main_window.menu.setCurrentRow(index)
            self.main_window.menu_navigation(index)
