# SEMBRA v5 · TANCAMENT — la pantalla ho ensenya

**Data:** 2026-08-23 · **Entorn:** staging (`ftt_staging`, tenant `fhort`) · **Patró B**
**Decisions:** Agus, 23/08 — *el catàleg mana* i *el nom del tenant que duplica o divergeix del
canònic deixa de manar*.
**Gate:** `manage.py check` **net** + `test_sembra_v5` **38 · OK** + les evidències. **Cap altra
suite.** · **PROD no s'ha tocat.**

---

# EL RESULTAT

| | abans d'aquest tram | ara |
|---|---|---|
| POMs vius lligats al catàleg | 89 / 144 | **103 / 144** |
| POMs amb nom propi que tapava el canònic | 103 | **0** |
| La fitxa ensenya nom CA | només si el tenant no en tenia (mai) | **sí, fila pròpia** |
| La fitxa ensenya nom ES | **enlloc del contracte** | **sí, fila pròpia** |

`hash_sembra` (famílies + globals) **no s'ha mogut**: `6637686664c678d0…`. Correcte — aquest
tram no toca el catàleg sembrat, toca el LLIGAM i el NOM del tenant. El bloc `poms` sí que
canvia: `38d71f3b…` → `7d6047f7…`.

---

# 1 · LLIGATS ELS 14 QUE FALTAVEN

`lliga_fhort_al_sistema --schema fhort --el-cataleg-mana --no-dry-run`

El mapa `Codi Brownie → codi de sistema` del r2 passa a ser **autoritat**: és un document
aprovat per la Montse, i el nom divergent ja no barra el lligam. **89 → 103.**

⛔ **Dues excepcions, i queden fora fins i tot amb el flag** (`EXCEPCIONS_DEL_MAPA`):

| | el tenant en diu | → | el v5 en diu |
|---|---|---|---|
| `N` | Motive placement | `N5` | Reflective band height |
| `RW` | Welt height | `R7` | Pocket topstitch |

🚨 **I un defecte propi que la BD va cantar abans que ningú.** La primera escriptura va reportar
«per autoritat 14» i `POMMaster` va seguir amb **89**: el comptador s'incrementava i el
`continue` de sota se'ls enduia igualment. **Comptats i no lligats, amb RC=0 i el report en
verd.** Es va veure perquè el pas es verifica contra la TAULA i no contra el seu propi report.
Corregit, i el banc en porta les dues cares.

# 2 · BUIDAT EL NOM PROPI DELS 103 LLIGATS

`adopta_nom_del_canonic --schema fhort --no-dry-run --buida-el-nom-del-tenant` → **103 buidats**,
segona passada **0**.

`nomenclatura.noms_de` fa guanyar el `nom_client` del tenant sobre el global. Amb els 144 POMs
batejats en anglès per Brownie, **el català i el castellà del v5 no arribaven mai a la fitxa**
encara que la sembra els hagués escrit. Amb el nom buit, la cascada cau al `POMGlobal`.

🔒 **És un rebateig i porta la porta que els rebateigs porten:** `--buida-el-nom-del-tenant` és
obligatori per escriure (tren de panys, 22/08). **No s'ha tocat**: els 41 no lligats, els
sobirans, el `codi_client`, els àlies de Brownie ni l'arxiu.

`pom/0082` (`blank=True` a `nom_client`) — `sqlmigrate` la resol en **no-op**; el que canvia és
el significat: **buit vol dir «mana el canònic»**. Aplicada als tres schemes.

# 3 · PER QUÈ NO ES VEIA — tres coses, i cap era la que semblava

| | Diagnòstic | Fet |
|---|---|---|
| **Precedència** | el `nom_client` tapava el canònic i les traduccions | §2 |
| **Serializer** | `name_es` **no existia al contracte** (ni al model de dades: `POMGlobal.nom_es` era buit a les 125 files velles) | `noms_de` publica `nom_es` i el serializer el treu com a `name_es` |
| **Frontend** | el bloc COM ES MESURA **ja pintava els cinc camps** i el nom local ja tenia la seva ⓘ — **el que faltava eren les DADES** | s'hi afegeixen dues files pròpies de nom CA i ES a la fitxa |

**El que s'ha tocat de codi, i per què cada cosa:**

- `nomenclatura.noms_de` → tercera clau `nom_es`, **només del global**: el tenant no té camp de
  castellà i l'àlies només en té un de «local» sense declarar de quina llengua és. Es llegeix
  amb **`getattr`** perquè aquest lector rep objectes duck-typed — i **dos bancs de sobirania
  tenien un `_Global` sense el camp i hi haurien petat**. (Trobat amb un `grep`, sense córrer
  cap suite; els dos stubs també s'han completat.)
- `POMMasterSerializer.name_es` — additiu i read-only.
- `POMCataleg.jsx` — a la **llista** el nom local segueix darrere la ⓘ (maqueta v3); a la
  **fitxa** el CA i l'ES tenen fila pròpia, perquè és on es va a mirar la identitat sencera i
  una traducció que només es veu amb el ratolí a sobre no és consultable. Les dues files
  **callen** quan no hi ha res a dir (regla del silenci).
- i18n `ca`/`en`/`es` — dues claus noves, paritat als tres.
- `npm run build` (staging serveix `frontend/dist`) i `systemctl restart ftt-staging`.

---

# 4 · LES EVIDÈNCIES — servei viu, posteriors al restart i al build

## (a) POM `A` · `GET /api/v1/poms/904/` → **HTTP 200**

```
IDENTITAT
  codi            'A'
  nom canònic EN  'Chest width (armpit to armpit)'
  nom CA          'Ample de pit'
  nom ES          'Ancho de pecho'
  família         'Pit i sisa'
  unitat          'cm'
COM ES MESURA
  des d'on        'Side seam'
  fins on         'Side seam'
  referència      '1 inch below armhole'
  scope           'HALF'          zona  'BOTH'
  toleràncies     prod 1.00 · mostra 0.50
```

*(`A` era, fa dues hores, el POM que no es lligava i no ensenyava res.)*

## (b) Les 14 famílies · `GET /api/v1/pom-categories/` → **HTTP 200**

```
 1. E  Coll, escot, espatlla i canesú    8. Q  Talls, pinces i plecs
 2. A  Pit i sisa                        9. G  Acabats i vores
 3. I  Màniga                           10. U  Botonadura i tancaments
 4. F  Llargs del cos                   11. T  Tirants, tapetes i trabilles
 5. B  Cintura                          12. R  Butxaca
 6. C  Maluc, cuixa i entrecuix         13. H  Caputxa i cap
 7. D  Baix, camal i peu                14. N  Elements aplicats i fornitures
```

## (c) El comptador · **103 de 144**, i els 41 de fora són **llista tancada**

```
· excepcions mesurades (2):  N · RW
· homònims (16):  E2 E3 F1 F3 F4 I3 I4 I6 I7 L1 M P1 P2 S2 S3 T3
· sense cap codi del v5 (23):  CR CR1 CR3 E6 E7 E8 EC EK1 FB FD FE FF FJ FR FS
                               FS4 FT PC SLT SLT1 TR VR ZZS45D
  2 + 16 + 23 = 41
```

## Servei

```
● ftt-staging.service — Active: active (running) since 2026-08-23 12:15:14 UTC
  Status: "Gunicorn arbiter booted"
  post-restart · A → Chest width (armpit to armpit) | Ample de pit | Ancho de pecho | cm | HALF
```

---

# 5 · EL QUE QUEDA PER A LA MONTSE (i no s'ha tocat)

**41 POMs sense canònic**, en tres piles i totes tancades:

1. **`N` i `RW`** — el full els aparella i **no són la mateixa mesura**. O es corregeix el full,
   o es queden. Decisió de catàleg, no de codi.
2. **Els 16 homònims** — mateix codi, mesura diferent (`M` del tenant és *Leg opening*; el del
   v5, *Neck width*). **No tenen destí al v5**: caldria que el full els en donés un.
3. **Els 23 sense cap codi** — uns quants el v5 els resol com a **DATUM** d'un altre POM
   (`FD`/`FE` amb cinturilla, `FB` part visible, `EK1` a la costura), i **l'eix DATUM no s'ha
   construït encara**. `ZZS45D` és un banc de QA, no domini.

I una que no és de la Montse: **3 àlies de Brownie apunten a un altre POM** (`BW`→`QTD`,
`U`→`Y`, `U1`→`Y1`) i no s'han mogut. A PROD n'hi ha 32, quasi tots cap a l'arxiu.

---

**PROD no s'ha tocat. La fase D vol tren a `main` i la finestra d'Agus.**
