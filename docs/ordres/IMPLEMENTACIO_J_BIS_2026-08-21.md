# J-BIS · TRES PECES CURTES

> **21/08/2026 · ✅ TRAM TANCAT · 4 commits a `dev`, CAP PUSH.**
> Substrat: `IMPLEMENTACIO_J_CONSULTA` (les 3 regles + `batec_escriptura`) + `IMPLEMENTACIO_H_BIS` §7.
> Banc: **25 tests** (1 skip) · **19/19** de QA sobre la fitxa del 1383.

---

## PEÇA 1 · `InProgress → Pending`, i només pel camí de consulta

J tornava «exactament on era» per a `Paused` i **mentia per a `Pending`**: una tasca que ningú no
havia començat mai, on algú entrava a mirar i sortia sense tocar res, quedava **`Paused` amb
`started_at` posat**. El Pla deia «pausada» d'una feina no començada.

### 🔒 Ser a `ALLOWED` no és ser permesa

La transició hi entra com a **única entrada guardada de la taula**. El guard de `transition_task`
exigeix **les dues condicions alhora**, i cap és decorativa:

| | Condició | Què aporta |
|---|---|---|
| **(a)** | `auto=AUTO_CONSULTA` | diu **QUI** la demana. La llei del log ja separa el gest del tècnic (`auto` null) del sistema (slug); aquí el mateix camp és a més la clau. **Un gest humà no en porta cap** |
| **(b)** | tram obert **sense `escriptura_at`** | diu **QUE ÉS VERITAT**. La marca sola seria una paraula que qualsevol cridador pot escriure; això no es pot fingir des de fora, perquè només `batec_escriptura` estampa aquell camp |

Sense les dues, el rebuig és **el mateix `TransitionError` que abans que la transició existís**.
⚠️ **La màquina d'estats humana no canvia**: cap botó nou, cap gest nou, cap camí d'usuari nou.

### D'on se sap l'estat d'entrada: del **LOG**

L'última transició cap a `InProgress` en porta el `from_status`. **Cap camp nou, cap memòria al
client** — i per això val per a totes les portes (menú, `?task_id=`, Pla de treball), que és el
que un estat recordat al front no aconseguiria. `TaskTransition` ja és la font de veritat de per
on ha passat una tasca. Sense cap transició registrada es cau a `Paused`: no saber d'on venies no
pot impedir que surtis.

I **«exactament» inclou el `started_at`**: una `Pending` és, per definició, feina que ningú no ha
començat. Es torna enrere sencer o no es torna.

### Els dos sentits, com demanava l'ordre

✅ la consulta torna a `Pending` · ✅ un `transition_task` humà segueix **rebutjat**. I tres guards
més que valia la pena escriure: amb una marca `auto` **qualsevol** també es rebutja (si no,
`guard_30min` o `exclusio_inprogress` hi caurien per accident), amb la marca bona però **amb
escriptura** també, i **la resta de la taula no s'ha mogut de rebot** (sis parells comprovats).

---

## PEÇA 2 · R1 a l'editor de fitxa

L'editor era **l'última eina** que preguntava «Has acabat?» a qui havia entrat, mirat i marxat.
Les dues sortides hi passen ara.

Verificat abans de construir-hi: **l'autosave bat**. `save_document` crida `SUP_FITXA` a
`ftt_document_views.py:250`, o sigui que una edició real marca el tram i **no es reverteix res**.
I la QA ho confirma per l'altra banda: **obrir el `.ftt` no compta com a escriptura**, que és
exactament el que separa mirar de treballar.

### 🔑 El desmuntatge no pot encadenar dues crides

Aquí hi havia una **pausa cega**: tancar la pestanya pausava la tasca encara que no s'hagués tocat
res. **No es pot arreglar encadenant** «pregunta i després pausa»: `keepalive` garanteix que surti
la petició ja llançada, **no** la que vindria després de resoldre-la, i en tancar la pestanya la
segona no s'enviaria mai.

Per això **decideix el servidor**: `pausa_si_cal` fa que la MATEIXA petició que abans pausava
sempre ara pausi només si hi ha hagut escriptura i, si no, torni la tasca a l'estat d'entrada
(`Pending` inclòs).

⚠️ **El flag és només per a sortides que ja pausaven soles.** La sortida DELIBERADA no el passa:
allà la persona ha de poder triar `Done`, i decidir-ho per ella seria treure-li la decisió que el
modal existeix per fer. Hi ha test que ho afirma.

### 🚩 Dues línies fora de l'encàrrec, i es diuen

`ModelSheet.pauseActiveTask` tenia **exactament la mateixa pausa cega** al desmuntatge: `exitEdit`
duia el guard des de J, però navegar fora o tancar la pestanya el saltava per l'altra porta.
Deixar-ho hauria estat tancar el forat a la fitxa i conservar-lo intacte **a la superfície per a
la qual J es va construir**. El monòlit no s'ha tocat enlloc més.

---

## PEÇA 3 · Els 8 `.ftt` del banc 1383

### (a) Diagnòstic — què va verificar de veritat la sembra

**Que un `open()` no havia petat, i res més.** El comptador s'incrementava després d'escriure, i
escriure va funcionar: els vuit fitxers hi eren. Ningú no va comprovar si eren **llegibles** ni si
eren **al lloc on es llegeixen**.

No ho eren per **dos motius independents** — i és el que ho feia difícil de veure, perquè
arreglar-ne un de sol no hauria servit:

| # | Defecte | Què passava | Per què no cantava |
|---|---|---|---|
| **1** | **FORMAT** | `json.dump(doc)` cru. Un `.ftt` és un **ZIP** amb `manifest.json` + `document.json` | `load_document` no el pot desempaquetar → **l'editor l'obre BUIT, sense error** |
| **2** | **CAMÍ** | `os.path.join(MEDIA_ROOT, name)`, però el storage és `TenantFileSystemStorage` | van a `media/model_fitxers/…`; Django llegeix `media/fhort/model_fitxers/…` |

La prova del format és la **mida**: la foto diu 451 B per al primer i al disc n'hi havia **94** —
el JSON cru. I el report deia una cosa **literalment certa i pràcticament falsa** («existeixen
sota `MEDIA_ROOT`»), que és la pitjor combinació possible: va passar la verificació independent
per ORM, que mira la BD i no el disc.

**No era «bytes mai exportats».** L'export en porta el document sencer per als vuit.

### (b) Reparació — 🚩 **NO calia cap `scp`, i això canvia l'encàrrec**

L'ordre demanava preparar la comanda perquè els fitxers els mogués l'Agus des de PROD. **No fa
falta**: el contingut ja era al repo (`MODEL_837_EXPORT.json`). S'han reempaquetat amb `pack` i
escrits per `ModelFitxer.fitxer.path` — **cap accés creuat PROD↔staging, i res a fer per part
d'Agus**.

Mides resultants, **idèntiques a la foto una per una**:

```
451 · 468 · 594 · 1571 · 1591 · 1623 · 1626 · 1624
```

🔑 **El `checksum` no casa, i és CORRECTE que no casi.** És el sha del **blob ZIP**, i
`zipfile.writestr` hi estampa l'hora de cada entrada: **dos empaquetats del mateix contingut donen
bytes diferents sempre** (mesurat al repo: 604/604 distints a staging, 3.603/3.606 a PROD — v.
l'avís d'`empremta_logica`). El de la foto és el del ZIP de PROD i **no és reproduïble per ningú**.
S'ha desat el dels bytes reals d'aquest disc: copiar el de la foto hauria estat desar una empremta
que no correspon a cap fitxer existent. **El que es compara és la mida i l'empremta lògica.**

> L'ordre demanava verificar «mida+checksum contra la foto». La mida ✅; el checksum **no es pot**,
> per construcció. Si algun dia es vol fidelitat de byte, l'única via és copiar el blob de PROD:
> `scp <prod>:/var/www/fhort-textile/backend/media/fhort/model_fitxers/2026/08/TRV-SS27-0001_fitxa*.ftt`
> `→ /var/www/ftt-staging/backend/media/fhort/model_fitxers/2026/08/` (mateix camí relatiu, amb
> el prefix `fhort/` **inclòs** — és el que la sembra es va deixar). No cal per a res funcional.

**Verificat per `load_document`**: els vuit obren, porten manifest i porten contingut, i són una
**cadena d'edició real** —866-867 buits, 868 un objecte, 869-873 amb taula `q8_grading`—, no vuit
còpies. **L'autosave hi persisteix**: desar sobre el cap crea la versió següent (878), al disc i
rellegible amb el contingut intacte.

**El command ja no ho pot repetir** i el report de la sembra queda corregit amb el diagnòstic
sencer (§8-bis), no amb una nota al marge.

---

## QA FINAL — la seqüència de consulta sobre la fitxa del 1383

`ops/qa/qa_jbis_fitxa_consulta.py` · **19/19**

| Cas | Resultat |
|---|---|
| el `.ftt` reparat obre | ✅ 200, **2 objectes** (no buit) |
| **(a)** entrar → mirar → sortir | ✅ torna a **`Pending`**, `started_at` **net**, **cap minut** (4 → 4), tram `consulta=True` i fora dels agregadors |
| obrir el `.ftt` | ✅ **no compta com a escriptura** |
| **(b)** entrar → editar de veritat → sortir | ✅ el batec `SUP_FITXA` marca el tram, la sortida **no reverteix**, la tasca segueix En curs — **la decisió és de la persona** |

Els trams de la 378 ho ensenyen alhora: **508** i **506** amb escriptura → compten; **507** i
**505** sense → `consulta=True`, fora.

🚩 **No va per nginx+gunicorn**: el JWT de QA caduca en 1 h i l'agent no en pot emetre. `APIClient`
de DRF amb el Host del tenant contra la **BD viva** — mateix URLconf, vista, permisos i serializer.

### Escriptures al banc (anotades, com demana l'ordre)

- **8 `.ftt` reescrits** (866-873) al camí del tenant, amb `mida_bytes`/`checksum` actualitzats.
- **Versions noves** 878+ del `.ftt` del 1383 (l'autosave de la verificació i del cas b).
- **Tasca 378** oberta i tancada diverses vegades; retornada a `Paused` amb `auto='qa_tram_jbis'`.
- Cap canvi a mesures, regles ni graduació.

---

## CENS — vist i no tocat

- 🚩 **`ModelFitxer` 874 i 877 són PDF**, no `.ftt`: els va crear l'export de la sessió H. Sorollen
  la cadena de versions del model però no en trenquen res.
- 🚩 Els vuit fitxers **antics** segueixen a `media/model_fitxers/2026/08/` (sense el prefix del
  tenant), ara òrfens. **No s'esborren**: són l'evidència del diagnòstic i no els llegeix ningú.
  Esborrar-los és una línia el dia que convingui.
- 🚩 Segueix obert de J: la consulta **crea** la tasca (R5) i **reancora** el model (R6).
- 🚩 Segueix obert d'H: tota la família Q8 insereix a `Y_INICI = 14`, i el banc
  `test_q8_banc_taules_fitxa.py` encara no s'ha pogut córrer (la BD de test ha estat ocupada tot
  el dia per la suite d'una altra sessió).

---

## COMMITS (cap push)

| Commit | Què |
|---|---|
| `3a928f80` | **Peça 1** · la transició guardada + els dos sentits al banc |
| `ea03184e` | **Peça 2** · R1 a l'editor i el bessó de `ModelSheet` |
| `197c16c8` | **Peça 3** · el diagnòstic, la reparació, el command i el report corregits |
| *(aquest)* | l'acta |

**Porta verda:** `manage.py check` net · `npm run build` ✓ · `eslint` **0 errors** ·
`manage.py test fhort.tasks.test_j_consulta_treball` **25/25** (1 skip) · QA **19/19**.
