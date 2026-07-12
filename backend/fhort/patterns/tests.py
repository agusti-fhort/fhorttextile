"""Tests del motor de patrons.

Convenció del repo: `tests.py` pla dins de l'app, executat amb
`python manage.py test fhort.patterns` (el projecte NO fa servir pytest).

Els tests de l'engine són `unittest.TestCase` PURS —sense `TenantTestCase` i sense
BD— perquè el motor no en necessita: és un paquet Python pur.

⚠️ `patterns/tests/` (directori de fixtures) NO ha de tenir mai `__init__.py`, o
passaria a ser un paquet i desplaçaria aquest mòdul en la resolució d'imports.
"""
