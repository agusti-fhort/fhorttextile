# DIAGNOSI Q8-bis/B0 · «amb l'escalat TANCAT no es pot inserir ni escalat ni size set»

> 17/08/2026, 21:30 · QA visual d'Agus a les 20:45. Diagnosi abans de tocar res.

## EL PREDICAT QUE BLOQUEJA

És **`ok: !!sessioTancada`**, la porta que Q8a/Q8c/notes comparteixen
([`TechSheetEditor.jsx`](../../frontend/src/pages/TechSheetEditor.jsx), `TABLE_VARIANTS`).
`sessioTancada` surt de `GET /fitting-sessions/?model=<id>&estat=Tancada`.

**Mesurat contra la BD viva (tenant `fhort`):**

```
sess 155 · model 1379 · estat Tancada · finished_at = 2026-08-17 18:50:21 UTC
```

18:50 UTC = **20:50 local**. La QA és de les **20:45**. O sigui que quan Agus va obrir el panell
la sessió encara era **`Oberta`** i les tres entrades de sessió estaven en fade. Es va segellar
cinc minuts després.

I mentrestant **l'escalat JA era tancat**:

```
model 1379 · sf=366 num=1 tipus=Proto   estat=TallesGenerades · nGV=1 · nPF=1  ← aquí viuen les línies
             sf=367 num=2 tipus=SizeSet estat=Tancat          · nGV=0 · nPF=0  ← «l'escalat tancat»
```

## 🚨 LA TROBALLA, I NO ÉS LA QUE SEMBLAVA

**`SizeFitting.estat='Tancat'` i `FittingSession.estat='Tancada'` són DOS segells diferents que
no es mouen junts.** I el segon fet mata la reparació òbvia:

> **L'escalat tancat (`sf=367`) té 0 `GradingVersion` i 0 `PieceFitting`.**
> No conté ni una sola `PieceFittingLine`.

Per tant «anar a buscar el `PieceFitting` de l'escalat tancat» **no hauria arreglat res**: no n'hi
ha cap. Les línies de presa pengen de `sf=366` (Proto) via `pf=40`, que és de la sessió que
llavors era oberta.

## LA LLEI, QUE JA ERA AL BRIEF I JO HAVIA LLEGIT DE PRESSA

> «la font és **l'estat consolidat** / l'ÚLTIMA SESSIÓ TANCADA, no la viva»

El SIZE SET no és una propietat del fitting: és **la corba del model**. Viu consolidada a
`GradedSpec` i la serveix `taula-mesures`, que per al 1379 dona **18 files amb `graded` i
`logica`, run `XXS·XS·S·M·L`, garments `['', '02']`** — sense demanar cap sessió. El que aporta
una sessió tancada són les **preses** (`Actual`, `Dif`, `Verdict`), i que no n'hi hagi cap no vol
dir que no hi hagi size set: vol dir que **encara ningú no l'ha mesurat**.

**Correcció:** Q8c passa a llegir l'**estat consolidat** i la sessió tancada l'ENRIQUEIX quan
n'hi ha. La seva porta deixa de mirar cap sessió i passa a ser la mateixa que Q8b i la T0 (que hi
hagi mesures). Amb sessió tancada, comportament d'ara, cel·la per cel·la.

**Q8a (fitting) i les NOTES no canvien de porta**: una taula de fitting sense fitting no és una
taula incompleta, és una taula que no existeix. La seva llei ja era bona.

**Q8b (escalat) ja no mirava cap sessió** (`ok: baseMeasuresOk`) — i el seu payload és sencer:
verificat 200 amb règim `LINEAR`, Δ 2.0, break 3.0 a `XS`. Es blinda amb prova perquè cap sessió
li pugui tornar a entrar a la porta.

## C4 · APAÏSAT PER PÀGINA — HI ÉS, NO CAL CAP FALLBACK

Verificat abans de dissenyar res, perquè el brief demanava STOP si no hi era:

- `PAGE_FORMATS` ja porta `A4P`/`A4L`/`A3P`/`A3L` amb les seves mides **en punts PostScript**.
- La pàgina ja té `format` OPCIONAL i sobreviu al round-trip (`ambFormat`, F4).
- **L'export PDF ja deriva la mida PER PÀGINA**: `const f = fmtDe(pages[pi]); const [pdfW, pdfH] = f.pdf; pdf.addPage([pdfW, pdfH])`.

O sigui que una pàgina apaïsada dins d'un document vertical ja és un cas suportat de punta a
punta. **Cap STOP, cap partició vertical de talles.**
