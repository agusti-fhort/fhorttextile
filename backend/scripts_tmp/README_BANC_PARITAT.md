# BANC DE PARITAT — empremta del motor de graduació

> **Segell:** 2026-08-16 · **Versió del golden:** `banc-brownie-v1`
> **Clau:** `model_id|pom_id|capa|instancia|garment|size_label`

## Com es pren

```bash
cd backend
venv/bin/python manage.py sembra_banc_paritat            # sembra/actualitza el banc (idempotent)
venv/bin/python manage.py shell -c "OUT='/tmp/g.json'; exec(open('scripts_tmp/golden_c3_snapshot.py').read())"
md5sum /tmp/g.json
```

## L'EMPREMTA

| | |
|---|---|
| **md5** | `56286b6ebf9828bb7138b208ce4040fa` |
| **cel·les preview** | 310 |
| **cel·les generador** | 310 |
| **models censats** | 27 (`BANC-01` … `BANC-27`) |
| **mesures base** | 450 |
| **regles residents** | 62 |

> ⚠️ **SEGELL PENDENT DE CERTIFICACIÓ.** La condició acordada és que la **suite sencera** sigui
> verda sobre el mateix HEAD —una empremta neix d'un motor certificat, no d'un motor sense
> mesurar—. La correguda llançada el 16/08 a les 08:53 UTC **encara no havia acabat** quan es va
> prendre aquesta empremta. El número de dalt és REPRODUÏBLE (dues corregudes seguides, md5
> idèntic) però **no queda segellat fins que la suite doni verd**. Qui hi arribi: mira el log,
> i si és verd, treu aquest bloc i data-ho.

## Qui és del banc: el PREFIX, no una llista

El cens és **dinàmic pel prefix `BANC-`**, i el motiu és una lliçó cara. Fins al 16/08 el golden
duia una llista escrita a mà —162 · 163 · 174 · 182 · 186 · 268 · 269— i aquell dia es va
descobrir que **cap d'aquells models existia**: la sembra v4 del 09/08 se'n va endur el corpus.
El golden no va petar mai, perquè un golden que mesura models inexistents emet 0 cel·les i un md5
perfectament estable. **Una llista a mà no pot dir «ja no sóc el banc».**

Amb el prefix, qui és del banc és qui `sembra_banc_paritat` ha sembrat. Afegir una fitxa al
document MOU l'empremta — i això és el que ha de passar: obliga a un segell nou i datat en comptes
de deixar-la entrar en silenci.

## D'on surten les dades

`docs/ordres/GRADING_ENTRADA_MODELS_BROWNIE.md` — 27 fitxes REALS de Brownie.

**Només 3 porten run i grading** (01 «Dessuadora Animal» · 02 «RUFFLES» · 04 «MEREDITH»): són
les úniques que deriven regles residents i, per tant, **les 310 cel·les surten d'aquestes tres**.
Les altres 24 són de talla base sola —el document ho diu elles mateixes— i entren al banc com a
`BaseMeasurement` reals amb 0 cel·les de graduació. Val més un banc petit i cert que un de gran i
inventat.

Les seccions de les fitxes (Bodice · Pocket · Hoodie · Sleeves…) són **seccions, no peces**: van
a la mare amb `seccio` informada i el banc no crea cap `ModelGarment`.

## Guards

- **Re-sembra idempotent**: `sembra_banc_paritat` dues vegades → empremta de BD `069bb404fe34aba7f31d70a0a7129102`, idèntica.
- **Purga + re-sembra**: `--purga` (1016 objectes) i tornar-hi → **la mateixa** `069bb404…`.
- **Mesura idempotent**: dues corregudes seguides del golden → el mateix `56286b6e…`.

## El banc VELL queda SUPERAT (no s'esborra)

> ⚠️ **SUPERAT 2026-08-16** — md5 `165d6701…` / 560 cel·les, models 162·163·174·182·186·268·269.
> **Motiu: el corpus és mort.** Cap d'aquells models existeix a cap tenant (`fhort` en té 3,
> `los` 51) des de la sembra v4 del 09/08. L'empremta no es pot tornar a prendre ni comparar amb
> res. Es conserva com a històric; **no és font de veritat per a cap decisió**.

## Codis del document que NO resolen (censats, mai inventats)

Dos codis del client no són al catàleg canònic — i **són polisèmics al mateix document**, que és
una raó més forta que la primera per no inventar-los:

| codi | fitxes | què vol dir segons la fitxa |
|---|---|---|
| `O` | 3 · 4 · 5 · 21 · 22 | «Back opening length» · «Opening at sleeve» · «Front opening length» |
| `LZ` | 9 · 17 | «Cord length» · «Collar height» · «Cord width» |

A més, **31 codis distints col·lapsen contra un POM que una altra fila de la MATEIXA fitxa ja
ocupa** (`R4`→`R2`, `RR`→`G1`, `V1`/`V2`→`V`, `PR2`/`PR3`→`PR`…). La segona fila es salta i es
censa: escriure-hi a sobre perdria una mesura en silenci. **Això no és un defecte del banc, és el
senyal que el catàleg encara no distingeix mesures que el client sí que distingeix** — i és
exactament la comparació que el document de la bústia existeix per fer.

Tres fitxes (07 MILEY · 10 BEYONCÉ · 11 BONITA) tenen la columna de talla **buida**: el valor viu
a `PROTO`/`SAMPLE`, que el document distingeix a posta del valor d'especificació. **No s'interpreta
com a talla base**: els seus models existeixen al banc amb 0 mesures. Decisió d'Agus si s'hi han
d'incorporar.
