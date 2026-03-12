MODIFICHE ALLA STRUTTURA DEI FILE DB
Alembic confronta la modifica e allinea il DB alla modifica

# Modifichi un modello → generi → applichi
alembic revision --autogenerate -m "cosa hai cambiato"
alembic upgrade head