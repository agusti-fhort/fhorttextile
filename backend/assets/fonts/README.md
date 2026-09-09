# Fonts TTF per als PDF comercials

Directori per defecte de `settings.PDF_FONTS_DIR` (override via env `PDF_FONTS_DIR`).

El `commerce/pdf_service.py` hi busca aquests fitxers exactes:

| Fitxer | Nom registrat a reportlab | Ús |
|---|---|---|
| `Montserrat-Light.ttf` | `MS-Light` | capçalera (disseny validat B2-PDF-v2), NO tocada pel bloc A |
| `Montserrat-Regular.ttf` | `MS` | capçalera |
| `Montserrat-SemiBold.ttf` | `MS-SemiBold` | capçalera |
| `Montserrat-Bold.ttf` | `MS-Bold` | capçalera |
| `IBMPlexMono-Regular.ttf` | `IBMPlexMono` | **cos** de l'albarà (maqueta §3, `ops/maquetes/maqueta_albara_v1.html`) |
| `IBMPlexMono-SemiBold.ttf` | `IBMPlexMono-SemiBold` | **cos** de l'albarà — noms, imports, «Pressupost/Encàrrec directe» |

Si algun no hi és, el PDF es genera igualment amb un fallback (Helvetica per a Montserrat,
**Courier** per a IBM Plex Mono — l'únic dels dos que és monospace, com l'original) i un
WARNING al log, però no és el look validat.

**Montserrat**: Google Fonts, OFL. **IBM Plex Mono**: IBM Corp., OFL — convertits offline
(`fontTools`, `flavor=None`) des dels `.woff` de `@fontsource/ibm-plex-mono` (pesos 400/600),
ja presents al disc al projecte `ftt-web`; cap descàrrega, cap CDN.
