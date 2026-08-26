"""Piece recognizer (F4.1) — similarity-first role/face proposals for pattern pieces.

Written in English on purpose: the slugs, the evidence keys and the neighbour-bank
vocabulary are a contract shared with the GarmentCode corpus, and a contract that gets
translated is a contract that drifts.

The cascade never confirms anything. It writes to `PatternPiece.proposed_*` and stops;
the green state is the human's, and only the human's.
"""
