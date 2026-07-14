"""Errors del motor — estructurats, mai traceback cru.

Llei de degradació elegant (la mateixa de l'import de fitxes): un fitxer real, per
corrupte o exòtic que sigui, **no fa petar el parser**. El que passa és que torna un
error amb detall suficient perquè l'usuari entengui què li passa al SEU fitxer.

A S3 aquests errors es tradueixen a **422 amb detall**, mai a 500.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ParseIssue:
    """Un problema concret, localitzat."""
    codi: str                      # 'no_blocks', 'empty_boundary', 'bad_number'…
    missatge: str
    peca: Optional[str] = None     # nom del BLOCK, si el problema hi és local
    detall: dict = field(default_factory=dict)


class PatternEngineError(Exception):
    """Arrel de tots els errors del motor."""


class PatternParseError(PatternEngineError):
    """El fitxer no s'ha pogut llegir com a patró.

    Porta la llista d'`issues` perquè el consumidor (l'API a S3, la UI a S4) pugui
    ensenyar-los tots alhora i no d'un en un.
    """

    def __init__(self, missatge: str, issues: Optional[list[ParseIssue]] = None):
        super().__init__(missatge)
        self.missatge = missatge
        self.issues: list[ParseIssue] = issues or []

    def as_dict(self) -> dict:
        return {
            'error': self.missatge,
            'issues': [
                {'codi': i.codi, 'missatge': i.missatge, 'peca': i.peca, 'detall': i.detall}
                for i in self.issues
            ],
        }

    def __str__(self) -> str:
        if not self.issues:
            return self.missatge
        return f'{self.missatge} ({len(self.issues)} problemes: ' \
               f'{", ".join(i.codi for i in self.issues[:5])})'
