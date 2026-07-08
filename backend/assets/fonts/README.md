# Fonts TTF per als PDF comercials (Montserrat)

Directori per defecte de `settings.PDF_FONTS_DIR` (override via env `PDF_FONTS_DIR`).

El `commerce/pdf_service.py` (disseny validat B2-PDF-v2) hi busca aquests **4 fitxers exactes**:

| Fitxer | Nom registrat a reportlab |
|---|---|
| `Montserrat-Light.ttf` | `MS-Light` |
| `Montserrat-Regular.ttf` | `MS` |
| `Montserrat-SemiBold.ttf` | `MS-SemiBold` |
| `Montserrat-Bold.ttf` | `MS-Bold` |

Si algun no hi és, el PDF es genera igualment amb **Helvetica** (fallback amb WARNING al log),
però no és el look validat. Deixa-hi els 4 TTF (Google Fonts: Montserrat, OFL) per al disseny final.
