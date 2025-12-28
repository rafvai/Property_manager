import json
import os


class PreferencesService:
    """Gestisce le preferenze utente (lingua, tema, ecc.)"""

    def __init__(self):
        self.prefs_file = "preferences.json"
        self.preferences = self.load_preferences()

    def load_preferences(self):
        """Carica le preferenze dal file"""
        if os.path.exists(self.prefs_file):
            try:
                with open(self.prefs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Errore caricamento preferenze: {e}")
                return self.get_default_preferences()
        return self.get_default_preferences()

    def get_default_preferences(self):
        """Ritorna le preferenze di default"""
        return {
            "language": "it"  # Default: Italiano
        }

    def save_preferences(self):
        """Salva le preferenze su file"""
        try:
            with open(self.prefs_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Errore salvataggio preferenze: {e}")
            return False

    def get_language(self):
        """Ottiene la lingua corrente"""
        return self.preferences.get("language", "it")

    def set_language(self, lang_code):
        """Imposta la lingua"""
        if lang_code in ["it", "es", "en"]:
            self.preferences["language"] = lang_code
            return self.save_preferences()
        return False