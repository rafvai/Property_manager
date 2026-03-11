"""
conftest.py
===========
Configurazione globale pytest per l'intera test suite.

Marker registrati:
- slow: test lenti (hashing PBKDF2) — escludi con: pytest -m "not slow"
- integration: test che toccano risorse esterne
- security: test specifici per la sicurezza

Uso:
    pytest tests/              # Tutti i test
    pytest tests/ -v           # Output verboso
    pytest tests/ -m "not slow"  # Escludi test lenti
    pytest tests/ --tb=short   # Traceback brevi
    pytest tests/ -x           # Fermati al primo errore
"""

import pytest


def pytest_configure(config):
    """Registrazione marker personalizzati"""
    config.addinivalue_line("markers", "slow: test computazionalmente intensi (es. PBKDF2)")
    config.addinivalue_line("markers", "integration: test che richiedono risorse esterne")
    config.addinivalue_line("markers", "security: test focalizzati sulla sicurezza")


@pytest.fixture(scope="session")
def tenant_id_default():
    """Tenant ID usato in tutti i test — centralizzato per cambio facile"""
    return "tenant_001"


@pytest.fixture(scope="session")
def tenant_id_altro():
    """Secondo tenant per test di isolamento"""
    return "tenant_002"
