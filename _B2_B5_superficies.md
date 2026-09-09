# B2 · `BaseMeasurement` i B5 · `POMPlacement` — dimensionat de superfícies per a ELEMENTS

> **Mode**: lectura pura. Cap escriptura a BD, cap migració, cap canvi de codi.
> **Entorn llegit**: `/var/www/ftt-staging` · Django **6.0.5** · PostgreSQL **18.4** · schemas `public`, `fhort`, `los`.
> **Mètode**: definicions llegides al codi viu; cens de relacions amb `Model._meta.related_objects` (mai `information_schema`); constraints reals llegits de `pg_constraint`/`pg_indexes`.
> Cap recomanació d'implementació: només terreny.

---

## B2 · `BaseMeasurement` — la quaterna

### B2.1 · Definició literal + Meta exacta

**Consultat**: `backend/fhort/models_app/models.py:588-836`

Definició sencera (`models.py:588`; el bloc de `ORIGEN_CHOICES` amb els seus comentaris s'enganxa tal qual perquè els valors `DERIVAT`/`COPIED`/`FEDERAT` són part del contracte d'auditoria):

```python
class BaseMeasurement(models.Model):
    """Base-size measurements entered for the Model before generating sizes."""

    ORIGEN_CHOICES = [
        ('STANDARD',   'Estàndard (carregat del RuleSet)'),
        ('IMPORTED',   'Importat de fitxa externa'),
        ('MANUAL',     'Introduït manualment'),
        ('FITTED',     'Modificat en fitting'),
        ('CALCULATED', 'Calculat des de talla base + delta'),
        ('TEMPLATE',   'Materialitzat de plantilla (sense valor encara)'),
        ('CHECKED',    'Validat en size check (proto a talla base)'),
        ('ITEM_STANDARD', 'Sembrat de l\'estàndard de l\'item (copy-at-the-moment)'),
        # Sprint B (2026-07-27) — còpia model→model. Cap dels valors anteriors serveix: copiar
        # `src.origen` verbatim faria que un MANUAL del model A afirmés que algú va mesurar el
        # model B, que és una mentida d'auditoria. `COPIED` diu la veritat: el valor és cert
        # però la seva autoritat viu en un altre model.
        ('COPIED', 'Copiat d\'un altre model'),
        # RETORN-1 (2026-07-27) — arribat per la FEDERACIÓ, de l'altra casa. No és 'COPIED'
        # (que parla d'un altre MODEL d'aquesta mateixa casa) ni 'IMPORTED' (que parla d'una
        # fitxa externa que algú ha llegit): és el mateix model, mesurat per l'altra banda del
        # pont. La distinció importa el dia que algú pregunti «qui va mesurar això»: la
        # resposta és «l'estudi», i cap dels altres valors ho diu.
        ('FEDERAT', "Arribat de l'altra casa (federació)"),
        # C3/C (2026-08-02) — DERIVAT D'UNA GERMANA. El valor no l'ha mesurat ningú: el sistema
        # l'ha mogut perquè s'ha corregit una altra fila del MATEIX POM dins del mateix model
        # (l'exterior puja de 54 a 56 → el folre puja de 52 a 54). Es mou el VALOR, mai el
        # grading; la folgança es conserva sola perquè ningú no la toca.
        #
        # Cap dels valors anteriors ho pot dir: 'CALCULATED' parla de talla base + delta dins
        # d'una mateixa fila, i 'COPIED'/'FEDERAT' parlen de valors que vénen de fora del model.
        # Aquest ve de la fila del costat.
        #
        # La distinció no és decorativa: sense ella una auditoria exterior↔folre es compara amb
        # ella mateixa i sempre dona verd, perquè no pot saber si el folre el va mesurar algú o
        # el va moure el sistema. I el que ho ha de dir sobretot és L'ENTRADA DEL REGISTRE, no
        # aquesta columna: l'origen d'una fila el sobreescriu el canvi següent, mentre que el
        # `MeasurementChangeLog` és append-only i conserva la seqüència.
        ('DERIVAT', 'Derivat d\'una germana (mateix POM, altra capa o instància)'),
    ]

    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name='base_measurements')
    pom = models.ForeignKey('pom.POMMaster', on_delete=models.PROTECT, related_name='base_measurements')
    # NULL = POM materialitzat de la plantilla de l'item sense valor encara (origen='TEMPLATE').
    # El signal del log i el motor de grading IGNOREN les files amb base_value_cm=None.
    base_value_cm = models.FloatField(null=True, blank=True)
    # Còpia de la plantilla GarmentPOMMap de l'item (snapshot per-model).
    is_key = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Sprint 3 / F1: root versioning ---
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='base_measurements_created',
    )

    # --- Sprint 5B.1: tolerance copied from the catalogue POM at pour time ---
    # NULL for the pre-existing measurements; consumers fall back to 0.6 (wired in 5B.4).
    tolerancia_minus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tolerancia_plus = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Sprint S14-A
    nom_fitxa = models.CharField(
        max_length=20, blank=True, default='',
        help_text='Nomenclatura de la fletxa al croquis (ex: A, 1, CH). '
                  'Per defecte: abbreviation del POMGlobal.'
    )
    origen = models.CharField(
        max_length=20, choices=ORIGEN_CHOICES, default='STANDARD',
    )
    ordre = models.PositiveIntegerField(default=0)

    # F3 — SECCIÓ d'origen de la mesura al document importat ('01.- DRESS', 'Bodice:'…).
    # [...comentari llarg; v. models.py:661-673...]
    # ⚠️ LÍMIT CONEGUT, no resolt aquí (DIAGNOSI_MULTIPECA_DALIA §Q2 i taula final §9): la
    # clau segueix sent `unique_together = [('model','pom')]`. Si DUES seccions del mateix
    # document comparteixen un POM, el confirm en col·lapsa les files i la que sobreviu es
    # queda amb la secció de l'ÚLTIMA — aquest camp no ho pot arreglar, perquè el bloqueig
    # no és el camp que faltava sinó la clau. Separar-les de debò vol tocar la clau, que
    # travessa 5 taules més, i és decisió d'arquitectura (Patró C), no d'aquest sprint.
    seccio = models.CharField(max_length=60, blank=True, default='')

    # Sprint NOMS-POM (2026-07-30) — EL BATEIG DEL MODEL. [...v. models.py:676-700...]
    nom_canonic_model = models.CharField(
        max_length=160, blank=True, default='',
        help_text="Nom canònic (EN) amb què AQUEST model anomena la mesura. "
                  "Buit: mana el catàleg (POMGlobal.nom_en).",
    )
    nom_traduit_model = models.CharField(
        max_length=160, blank=True, default='',
        help_text="Traducció del nom que fa servir el client d'aquest model. "
                  "Buit: mana el catàleg (POMGlobal.nom_ca / POMMaster.nom_client).",
    )

    # ── C1 (2026-07-30) — LA CAPA. Declaració canònica del camp; les altres set taules
    # de mesura el porten igual i apunten aquí. [...v. models.py:707-724...]
    # REFERÈNCIA PER SLUG, MAI PER PK (llei G9). No és un FK a `pom.MeasurementLayer` a
    # posta: el catàleg viu a `fhort.pom` (SHARED **i** TENANT) i aquestes taules són
    # tenant-only o creuen schemas — un FK real petaria a `public` [...]
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # ── C1-ins — LA INSTÀNCIA. Declaració canònica del camp; les altres vuit taules de la
    # cadena en porten una d'igual i apunten aquí. [...v. models.py:726-748...]
    # `''` (cadena buida, MAI NULL) és la instància ÚNICA [...]
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
```

**La `Meta` EXACTA** (`models.py:755-832`), enganxada sencera amb els seus comentaris (els comentaris són el registre de per què les comportes ja no hi són):

```python
    class Meta:
        verbose_name = 'Mesura base'
        verbose_name_plural = 'Mesures base'
        # C1/T3 — la clau incorpora la CAPA. Fins avui un model no podia tenir el pit de
        # l'exterior i el pit del folre alhora: la segona fila xocava amb la primera. Amb tot
        # a 'exterior' la clau nova és estrictament més permissiva que la vella (mateixes
        # columnes + una), o sigui que no pot rebutjar res que abans passés ni deixar entrar
        # cap duplicat que abans es barrés. Qui de debò impedeix una segona capa avui és la
        # comporta CHECK de T4, no aquesta clau.
        #
        # C1-ins/T3 — i ara també la INSTÀNCIA, pel mateix argument literal: mateixes
        # columnes + una, amb `instancia` constant ('') a totes les files → estrictament més
        # permissiva, 0 duplicats latents possibles. Qui impedeix la segona instància avui és
        # la comporta `_instancia_gate_cins`, no aquesta clau.
        unique_together = [('model', 'pom', 'capa', 'instancia')]
        # `capa` entra a l'ordre entre el model i l'ordre de fitxa: quan hi hagi més d'una
        # capa, la fitxa les vol AGRUPADES, no barrejades per `ordre`. Avui és un no-op
        # observable —amb una sola capa el valor és constant i l'ordre relatiu no es mou—,
        # i el fumeig de base-stages ho verifica byte a byte.
        ordering = ['model', 'capa', 'ordre', 'pom']
        constraints = [
            # ── C1/T4 — LA COMPORTA. [...tot el bloc explicatiu...]
            # ✅ C4/G1 (04/08) — LA COMPORTA DE CAPA S'HA RETIRAT (migració 0076). [...]
            # ✅ C4/G1 (04/08) — LA COMPORTA D'INSTÀNCIA S'HA RETIRAT (migració 0076) [...]
            # ── C1-ins · DECISIÓ D1 — UNA INSTÀNCIA SENSE NOM DE FITXA ÉS IL·LEGAL.
            #
            # Aquesta no és bastida: és una llei de domini, i sobreviu a C4-ins. Si una
            # mesura es desdobla, l'única cosa que fa que les dues files siguin
            # distingibles per a un humà —al croquis, a la taula, al paper— és el
            # `nom_fitxa`. Dues files «pit» sense res que les separi visualment no són dues
            # mesures: són un duplicat amb aparença de dada bona, que és exactament el mode
            # de fallada que tot aquest tram existeix per evitar.
            #
            # Amb la comporta tancada (`instancia` sempre '') la condició és trivialment
            # certa a totes les files, present i futures: no rebutja res que avui passi.
            models.CheckConstraint(
                condition=~models.Q(instancia__gt='', nom_fitxa=''),
                name='models_app_basemeasurement_instancia_exigeix_nom',
            ),
        ]
```

**Els constraints REALS a BD** (`pg_constraint` sobre `fhort.models_app_basemeasurement`) — el que hi ha, no el que diu la `Meta`:

| tipus | nom | definició |
|---|---|---|
| `p` | `models_app_basemeasurement_pkey` | `PRIMARY KEY (id)` |
| `u` | `models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq` | `UNIQUE (model_id, pom_id, capa, instancia)` |
| `c` | `models_app_basemeasurement_instancia_exigeix_nom` | `CHECK ((NOT (((instancia)::text > ''::text) AND ((nom_fitxa)::text = ''::text))))` |
| `c` | `models_app_basemeasurement_ordre_check` | `CHECK ((ordre >= 0))` ← **no és a la `Meta`**: el genera `PositiveIntegerField` |
| `f` | `..._model_id_270d8b7b_fk_models_ap` | `FK (model_id) → fhort.models_app_model(id)` DEFERRABLE |
| `f` | `..._pom_id_440368f9_fk_pom_pommaster_id` | `FK (pom_id) → fhort.pom_pommaster(id)` DEFERRABLE |
| `f` | `..._created_by_id_4935e12a_fk_auth_user` | `FK (created_by_id) → fhort.auth_user(id)` DEFERRABLE |

Índexs: `..._model_id_270d8b7b`, `..._pom_id_440368f9`, `..._capa_5b964362` (+`_like`), `..._instancia_72542d99` (+`_like`), i l'únic UNIQUE `models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq`.

**Cens de relacions** (`_meta.related_objects`, baixant pels fills):

- fill únic: `models_app.MeasurementChangeLog.base_measurement` — **`on_delete=SET_NULL`**, `db_constraint=True`.
- FKs cap amunt: `model → models_app.Model` **CASCADE** (`null=False`), `pom → pom.POMMaster` **PROTECT**, `created_by → auth.User` **SET_NULL**.

Migracions aplicades fins a `0079_m3_derivat_de_rule_set` (totes `[X]`, inclosa **`0073_instancia_mesures`** i `0074`, `0076-0078` que retiren les comportes). El 🚩 de memòria «la 0073 no s'ha aplicat» **ja no és cert a staging**.

---

### B2.2 · Dimensionat: FK `element` nullable amb default al contenidor implícit

**Constraint per constraint** (els 7 reals de la taula):

**1. `models_app_basemeasurement_pkey` — `PRIMARY KEY (id)`**
No es toca. Afegir una columna no l'afecta. Cost 0.

**2. `models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq` — `UNIQUE (model_id, pom_id, capa, instancia)` — AQUÍ ÉS ON PASSA TOT.**

Hi ha dos escenaris i tots dos són dolents de maneres oposades:

- **(a) Afegir `element_id` SENSE tocar la clau.** La clau segueix sent de 4 columnes. El mateix POM a la mateixa capa i instància però en **dos elements diferents** (el pit del cos i el pit de la caputxa) xoca: `IntegrityError`. La taula no pot representar el cas que motiva els elements. La clau **ha de créixer** a 5 columnes.

- **(b) Fer créixer la clau amb `element_id` NULLABLE.** Aquí el precedent de C1/C1-ins **NO s'aplica**, i el seu propi comentari explica per què: «mateixes columnes + una, amb `instancia` constant (`''`) a totes les files → estrictament més permissiva». Això era cert perquè `capa` i `instancia` són `NOT NULL` amb default **no-nul**. Un `element_id` **NULL** és una cosa diferent a Postgres: en un índex UNIQUE ordinari **els NULLs són DISTINTS entre ells**. Amb 693 files (les del dump pre-wipe) totes amb `element_id IS NULL`, la unicitat que avui protegeix `(model, pom, capa, instancia)` **desapareix en silenci**: es podrien inserir N files idèntiques al contenidor implícit i cap constraint diria res. No és «més permissiva», és **cega**.
  - **Terreny disponible**: PG **18.4** i Django **6.0.5** → `UniqueConstraint(..., nulls_distinct=False)` existeix (PG ≥15, Django ≥5.0). Però `unique_together` **no ho sap expressar**: caldria convertir-lo a `UniqueConstraint` amb nom (un `AlterUniqueTogether(None)` + `AddConstraint`), que és exactament el que la migració `0071_capa_unicitats` ja va haver de fer per a `POMPlacement` («`POMPlacement` no fa servir `unique_together` sinó un `UniqueConstraint` amb nom: DROP del…»). O sigui: **`POMPlacement` ja té la forma barata; `BaseMeasurement` no.**
  - L'alternativa que preserva el precedent C1 al peu de la lletra és un **element sentinella real** (FK `NOT NULL` a una fila «element implícit» per model), i llavors la clau de 5 columnes torna a ser «mateixes columnes + una amb valor constant» i l'argument de C1 es pot reciclar sencer.

**3. `models_app_basemeasurement_instancia_exigeix_nom` — `CHECK (NOT (instancia > '' AND nom_fitxa = ''))`**
**No es trenca.** És un CHECK **per fila** que no referencia ni `model`, ni `pom`, ni cap columna nova. Afegir `element_id` és DDL d'una columna: cap fila existent queda reescrita, cap fila existent deixa de satisfer-lo. Postgres el revalida en afegir la columna només si el `ALTER TABLE` reescriu la taula, i en tots els casos passa.
**Però la seva RAÓ queda incompleta.** La llei de domini que declara diu: «l'única cosa que fa que les dues files siguin distingibles per a un humà és el `nom_fitxa`; dues files "pit" sense res que les separi visualment no són dues mesures: són un duplicat amb aparença de dada bona». Amb `element` com a tercer eix de desdoblament, **el mateix mode de fallada reapareix per un eix que el CHECK no vigila**: dues files «pit» que només difereixen per `element_id` són indistingibles al croquis, a la taula i al paper exactament igual. El constraint no peta; simplement ja no cobreix tot el que deia cobrir.

**4. `models_app_basemeasurement_ordre_check` — `CHECK (ordre >= 0)`**
No es toca.

**5-7. Els tres FKs existents (`model_id`, `pom_id`, `created_by_id`)**
No es toquen. Afegir una columna no els afecta.

**El FK NOU `element_id` — el `on_delete` és la decisió cara.** Precedent citat al brief (`CustomerPOMAlias`): un `CASCADE` **no bloqueja, s'enduu files**. Aquí:
- `element` amb **CASCADE** → esborrar un element esborra les seves `BaseMeasurement`; i com que `MeasurementChangeLog.base_measurement` és **`SET_NULL`**, les entrades del registre append-only **sobreviuen orfes** (conserven `model_id`, `pom_id`, `capa`, `instancia`, però ja no apunten a res). La història no es perd però queda desancorada.
- `element` amb **PROTECT** → esborrar un element amb mesures dona 409 (patró `pom`/`POMMaster`).
- `element` amb **SET_NULL** → les mesures «tornen» al contenidor implícit, cosa que, amb la clau nulls-distinct de l'escenari (b), pot crear **duplicats immediats i legals** al contenidor implícit.

**El que NO diu cap constraint — el cost real.** La clau de 4 columnes té un **bessó al contracte HTTP**, i aquest sí que es trenca a mà:

- **`backend/fhort/pom/identitat.py:38` · `clau_mesura(pom_id, capa, instancia)`** — la clau aplanada `{pom_id}|{capa}|{instancia}`, «l'ÚNIC lloc on es decideix com». El seu propi docstring prohibeix ometre trams («la instància única és el tram buit, no l'absència del tram»). Un cinquè eix vol un quart tram i **canvia el format de fil a les dues bandes alhora**. Consumidors: `pom/grading_views.py:137,147,178`; `models_app/views.py:1963,1981,3309,3317`.
- **Mirall al frontend, escrit a mà (no importat)**: `frontend/src/pages/TechSheetEditor.jsx:321-322`
  ```js
  const identitatDeCota = (o) => `${o.pomId}|${o.capa || 'exterior'}|${o.instancia || ''}`
  const identitatDeFila = (bm) => `${bm.pom_id}|${bm.capa || 'exterior'}|${bm.instancia || ''}`
  ```
  usat a `:3581, 3600, 5570, 5579, 5681, 5689, 5698, 5700, 5714, 5805, 5854, 6910`.
- **Lectors que indexen per la terna `(pom_id, capa, instancia)`** — cadascun col·lapsaria dos elements en un i **no petaria: pintaria**:
  `fitting/services.py:402,408,413,424,500` · `fitting/serializers.py:256,288,302,305` · `fitting/repas_views.py:112,118,133,151,173,281,296,299,326` · `fitting/graded_spec_views.py:55,73` · `fitting/views.py:650,714` · `pom/s10_views.py:46,64,99` · `pom/s6_views.py:174,192` · `pom/wizard_views.py:311` · `models_app/serializers_size_check.py:90,105,126,141` · `models_app/pom_placement_views.py:53,83-88`.
- **Escriptors de `BaseMeasurement`** (cadascun hauria de decidir a quin element escriu):
  `models_app/views.py:1424,1435` (`materialize_poms_view`, def a `:1297`) · `models_app/views.py:1664` (`copiar_de_model_view`, def a `:1509`) · `models_app/views.py:2149` (`set_measurements_view`, def a `:2087`) · `models_app/views.py:2324` (`gravar_pom_view`, def a `:2181`) · `models_app/views.py:2755` (`measurements_chat_view`, def a `:2651`) · `pom/wizard_views.py:328` (`save_base_size_view`, def a `:243`) · `models_app/extraction_views.py:2575` (`import_session_confirmar_view`, def a `:2147`) · `tenants/federation_service.py:769` (`_escriu_a_la_marca`, def a `:718`) · `models_app/serializers.py:425` (el ViewSet CRUD).
  ⚠️ **Precedent viu**: `pom_placement_views.py:157-161` escriu literalment `capa=MeasurementLayer.SLUG_DEFECTE, instancia=''` — el mateix accident («escriptor que no s'ha adaptat a una clau que ha crescut») que la memòria registra per a C4.
- **Les 11 taules germanes** que porten `(capa, instancia)` i que fan `join` de tornada cap a la mesura: si `element` només viu a `BaseMeasurement`, aquestes ja no la poden resoldre unívocament (v. taula a B2.4).

---

### B2.3 · El serializer que valida la clau + `instancia_exigeix_nom`

**On**: `backend/fhort/models_app/serializers.py:425` (classe), **`:465-492`** (el `validate`). Consumit per `BaseMeasurementViewSet` a `backend/fhort/models_app/views.py:501-533`.

Codi literal (`serializers.py:437-492`):

```python
    # Q1 (06/08) — `''` ÉS UN VALOR LEGÍTIM D'INSTÀNCIA: és LA MESURA ÚNICA, i el default del
    # camp al model. DRF derivava el camp del model —que no declara `blank=True`— i en sortia
    # `allow_blank=False`: tornar una germana a la identitat base (desfer la píndola) rebia un
    # 400 «Aquest camp no pot estar en blanc» i el camí de tornada quedava tancat al BACKEND
    # encara que la pantalla l'oferís. La invariant que sí que mana —amb instància, cal nom— es
    # segueix comprovant a `validate()`, i és a l'altra banda: prohibeix el nom buit, no el slug.
    instancia = serializers.CharField(required=False, allow_blank=True, max_length=60)

    class Meta:
        model = BaseMeasurement
        fields = (
            'id', 'model', 'pom',
            'pom_code', 'pom_name_en', 'pom_name_cat',
            'pom_abbreviation', 'pom_is_key', 'pom_category',
            'pom_codi_client', 'pom_nom_client',
            # C4 — ELS DOS EIXOS D'IDENTITAT (D-31.22 · D-31.26). Hi entren com a ESCRIVIBLES
            # perquè la pantalla de PRESA els ha de poder tocar per fila (moure una mesura de
            # capa, partir-la per instància) i l'únic camí que ho feia fins ara era
            # `set-measurements`, que reescriu `origen` a 'MANUAL' i les toleràncies de TOTES
            # les files del payload. Fer passar una presa per allà convertiria una base
            # 'CHECKED' en 'MANUAL' sense que ningú ho hagués demanat: dany d'auditoria dins
            # d'un canvi de nom de columna.
            'capa', 'instancia',
            'base_value_cm', 'is_active', 'notes',
            'nom_fitxa', 'origen',
            'updated_at',
        )
        read_only_fields = ('updated_at',)

    def validate(self, attrs):
        """La CLAU ÚNICA `(model, pom, capa, instancia)` i la invariant del nom, dites a temps.

        Totes dues viuen a la BD i, sense això, arriben com un IntegrityError —un 500 mut— quan
        el que ha passat és que l'usuari ha triat una cara que aquesta mesura ja té.
        """
        inst = self.instance
        camps = {
            'model': attrs.get('model', getattr(inst, 'model', None)),
            'pom': attrs.get('pom', getattr(inst, 'pom', None)),
            'capa': attrs.get('capa', getattr(inst, 'capa', '') or ''),
            'instancia': attrs.get('instancia', getattr(inst, 'instancia', '') or ''),
        }
        if camps['model'] and camps['pom']:
            germanes = BaseMeasurement.objects.filter(**camps)
            if inst is not None:
                germanes = germanes.exclude(pk=inst.pk)
            if germanes.exists():
                raise serializers.ValidationError({'instancia': (
                    'Aquesta mesura ja té una fila en aquesta capa i instància.'
                )})
        # `models_app_basemeasurement_instancia_exigeix_nom`: amb instància, el nom és obligatori.
        nom = attrs.get('nom_fitxa', getattr(inst, 'nom_fitxa', '') or '')
        if camps['instancia'] and not (nom or '').strip():
            raise serializers.ValidationError({'nom_fitxa': (
                'Una mesura amb instància ha de portar nomenclatura.'
            )})
        return attrs
```

**Què valida exactament** — dues coses, i cap més:
1. **Preflight de la clau de 4 columnes**: consulta `BaseMeasurement.objects.filter(model, pom, capa, instancia)` (amb `exclude(pk)` a l'update) per convertir un futur `IntegrityError` en un 400 llegible. **No hi ha `UniqueTogetherValidator` automàtic de DRF actiu** aquí (`capa` i `instancia` tenen defaults i `instancia` està sobreescrit a mà) — aquest `filter()` **és** el guard.
2. **Espill d'aplicació del CHECK** `instancia_exigeix_nom`: amb `instancia` no buida, `nom_fitxa` no pot ser buit ni només espais (nota: el serializer és **més estricte** que la BD — el CHECK compara `nom_fitxa = ''`, el serializer fa `.strip()`, o sigui que un `nom_fitxa=' '` passa la BD i el rebutja el serializer).

**Què li caldria si la clau passés a quinar (afegint `element`)**:
- `'element'` dins del dict `camps` amb el mateix patró `attrs.get(..., getattr(inst, ...))`. ⚠️ El patró actual acaba amb `or ''` per a `capa`/`instancia`; per a un FK nullable **`or ''` no serveix** (convertiria `None` en `''` i el `filter(element='')` petaria) — cal `attrs.get('element', getattr(inst, 'element_id', None))` i filtrar per `element_id`, incloent-hi explícitament el cas `None` (`filter(element_id=None)` sí que funciona a l'ORM, a diferència de l'índex UNIQUE).
- `'element'` a `Meta.fields` com a escrivible (mateix argument literal que C4 va fer servir per a `capa`/`instancia`: si no, l'únic camí per moure una mesura d'element seria `set-measurements`, que reescriu `origen` a `MANUAL` de tot el payload — el dany d'auditoria que el comentari de `:451-457` descriu).
- **El pes real**: si `element_id` és nullable i l'índex UNIQUE queda nulls-distinct (escenari B2.2b), **aquest `validate()` passa de ser una cortesia a ser l'ÚNIC guard** de duplicats al contenidor implícit — i és un `filter().exists()` fora de transacció: **cursa** amb dues peticions concurrents, i els camins que no passen pel serializer (els 9 escriptors de B2.2, `bulk_create`, loaders de paquet, `psql`) **no el veuen**. El comentari de C1/T4 ja ho argumentava per a la comporta: «no hi ha guard d'aplicació que ho iguali».

---

### B2.4 · La nota del brief: `instancia` sense `blank=True` al model

**CONFIRMAT.** `backend/fhort/models_app/models.py:749-753`:

```python
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )
```

No hi ha `blank=True`. Introspecció de Django: `blank=False`, `null=False`, `default=''`. La correcció Q1 (06/08) es va fer **només al serializer** (`serializers.py:442`). El model segueix desajustat.

**Matriu DRF-vs-model de `BaseMeasurementSerializer`** (generada per introspecció del serializer instanciat):

| camp | DRF | required | allow_blank | read_only | model |
|---|---|---|---|---|---|
| `model` | PrimaryKeyRelatedField | True | – | False | null=F blank=F |
| `pom` | PrimaryKeyRelatedField | True | – | False | null=F blank=F |
| **`capa`** | **CharField** | False | **False** | False | **null=F blank=F default='exterior'** |
| **`instancia`** | CharField | False | **True** ✅ (pedaç Q1) | False | **null=F blank=F default=''** |
| `base_value_cm` | FloatField | False | – | False | null=T blank=T |
| `is_active` | BooleanField | False | – | False | null=F blank=F default=True |
| `notes` | CharField | False | True | False | null=T blank=T |
| `nom_fitxa` | CharField | False | True | False | null=F **blank=T** default='' |
| `origen` | ChoiceField | False | False | False | null=F blank=F default='STANDARD' (choices sense `''`) |
| `updated_at` | DateTimeField | – | – | True | auto_now |

**TOTS els camps de `BaseMeasurement` amb el mateix desajust**: dins d'aquesta taula, **`instancia` és l'ÚNIC** camp de text amb `blank=False` **i** `default=''`. Els altres candidats queden descartats per lectura:
- `nom_fitxa`, `seccio`, `nom_canonic_model`, `nom_traduit_model`, `notes` → tenen `blank=True`. Correctes.
- `origen` → `blank=False` + default, però és `ChoiceField`: `''` no és un valor legítim. No és el mateix desajust.
- `capa` → `blank=False` + `default='exterior'` (no `''`). **No és el mateix bug, però hi ha una asimetria**: el codi de lectura tolera `''`/`None` per a `capa` i cau a `'exterior'` (`pom/identitat.py:44` fa `capa or "exterior"`; `serializers.py:475` fa `getattr(inst,'capa','') or ''`), mentre que **l'API rebutja `capa: ''` amb un 400**. Un client que reenviï una fila tal com la va rebre amb `capa` buida rep un 400 pel camp que el backend mateix normalitza.
- `is_key`, `is_active`, `ordre`, toleràncies, `created_at/updated_at` → tenen default i DRF els fa `required=False`. Correctes.

**Models germans amb EXACTAMENT el mateix desajust de model** (sweep sobre `models_app`, `pom`, `fitting`, `tasks`: `CharField`/`TextField`/`SlugField` amb `blank=False` **i** `has_default()` **i** `default == ''`). Són **12 taules, i sempre el mateix camp**:

| model | camp | unique_together / constraints | exposat per un `ModelSerializer`? |
|---|---|---|---|
| `pom.GarmentPOMMap` | `instancia` | `('garment_type_item','pom','capa','instancia')` | no |
| `pom.GarmentTypePOMMap` | `instancia` | `('garment_type','pom','capa','instancia')` | **sí — `GarmentTypePOMMapSerializer`: `allow_blank=False`** 🚩 |
| `pom.GarmentGroupPOMMap` | `instancia` | `('garment_group','pom','capa','instancia')` | **sí — `GarmentGroupPOMMapSerializer`: `allow_blank=False`** 🚩 |
| `pom.ItemBaseMeasurement` | `instancia` | `('base_set','pom','capa','instancia')` | no |
| `models_app.BaseMeasurement` | `instancia` | `('model','pom','capa','instancia')` + CHECK `instancia_exigeix_nom` | **sí — PEDAÇAT (`allow_blank=True`)** ✅ |
| `models_app.MeasurementChangeLog` | `instancia` | cap | no |
| `models_app.ModelGradingOverride` | `instancia` | `('model','pom','size_label','capa','instancia')` | no |
| `models_app.SizeCheckLine` | `instancia` | `('size_check','pom','capa','instancia')` | no |
| `models_app.POMPlacement` | `instancia` | `UniqueConstraint('item_fitxer','pom','view_slot','capa','instancia')` | no (vistes de funció) |
| `fitting.POMAlert` | `instancia` | cap | **sí — `POMAlertSerializer`: `allow_blank=False`** 🚩 |
| `fitting.GradedSpec` | `instancia` | `('grading_version','pom','size_label','capa','instancia')` | no |
| `fitting.PieceFittingLine` | `instancia` | `('piece_fitting','pom','size_label','capa','instancia')` | no |

**Conclusió del punt 4**: el desajust és **un sol camp repetit 12 vegades** (la declaració canònica de `capa`/`instancia` es va copiar literalment a totes les taules de la cadena, `blank` inclòs). De les 12, només 4 estan exposades per un `ModelSerializer`; **3 d'aquestes 4 encara tenen `allow_blank=False`** (`POMAlertSerializer`, `GarmentTypePOMMapSerializer`, `GarmentGroupPOMMapSerializer`) → **el mateix 400 «Aquest camp no pot estar en blanc» que Q1 va arreglar per a `BaseMeasurement` continua viu en aquestes tres superfícies**. Les altres 8 tenen el defecte **latent** (els escriptors són vistes de funció que passen literals i mai construeixen el camp des d'un payload).
`MeasurementChangeLog.context` i `POMPlacement.view_slot` **no** entren en aquesta llista: no declaren `default` (el `''` que retorna la introspecció és el fallback de Django, no un default explícit).

---

### B2.5 · Recompte de files per schema

| schema | `models_app_basemeasurement` |
|---|---|
| `public` | **la taula NO existeix** — `models_app` és **només** `TENANT_APPS` (`backend/fhort/settings.py:62-75`; no és a `SHARED_APPS`, `:36-59`) |
| `fhort` | **0** |
| `los` | **0** |

Context per no llegir el 0 com un error:
- El wipe del 06/08 (memòria `ftt-vespre-forats-v1v6`) es confirma: `fhort.models_app_model` = **0**, `models_app_measurementchangelog` = 0, `models_app_sizecheckline` = 0, `fitting_gradedspec` = 0. Al **dump pre-wipe** `/root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump` hi havia ≈**693** `BaseMeasurement`, **48** `Model`, **3** `ItemFitxer`, **306** `ModelFitxer`.
- `los` té **51 models** però **0** mesures base (i 0 `ItemFitxer`, 0 `ItemBaseMeasurement`). `fhort.pom_itembasemeasurement` = **37** (el catàleg, que el wipe no va tocar).
- ⚠️ El `pg_restore` del `PATH` és **16.14** i el dump és de PG18 (`unsupported version (1.16) in file header`). Cal `/usr/lib/postgresql/18/bin/pg_restore`. Els recomptes s'han fet amb `--data-only -f -` **a stdout**: cap BD tocada.

---

## B5 · `POMPlacement` i la traçadora

### B5.1 · Definició literal al codi VIU — i si hi ha una segona

**HI HA UNA SOLA DEFINICIÓ.** `backend/fhort/models_app/models.py:1424-1521`. Cerca exhaustiva de `class POMPlacement` a tot el repo: **una única coincidència**. Les altres referències són consumidores (`models_app/pom_placement_views.py`, `scripts_tmp/onada1_dump_superficies.py:41,101`, `pom/management/commands/sembra_ai_report.py` — que és **només informe, cap escriptura**) o migracions (`0062_pomplacement` la crea; `0070`, `0071`, `0073`, `0074`, `0078` l'evolucionen).

**La «PoC» del repo no és d'això**: `docs/diagnosis/arxiu/POC_PAPER_KONVA.md` documenta una PoC de l'editor Konva i cita `frontend/src/pages/PaperKonvaPoc.jsx`, **fitxer que ja no existeix**. No conté cap model ni cap estructura de placement. **No hi ha segona definició de `POMPlacement` enlloc.**

Definició sencera:

```python
class POMPlacement(models.Model):
    """Precedent de COL·LOCACIÓ d'una cota POM sobre un sketch de CATÀLEG (F2).

    La col·locació viu al CATÀLEG (ItemFitxer), no al model: una sola veritat que els
    documents nascuts de l'item hereten via `ModelFitxer.derivat_de_item` (D1). Els extrems
    estan NORMALITZATS 0..1 respecte de la BOUNDING BOX DE L'OBJECTE SKETCH que la cota
    anota — NO de la pàgina ni de la silueta.

    ⚠️ bbox-d'objecte ≠ silueta: els marges buits dins una imatge (ràster sobretot) poden
    desviar la col·locació respecte del contorn real de la peça. Acceptat a v1 i traçat per
    `source_kind` (mai jerarquia; només qualitat de l'origen).

    NOMÉS és un precedent geomètric: MAI escriu cap valor de mesura (frontera G1). El vincle
    al POM és de LECTURA (PROTECT, com BaseMeasurement/PatternPOM); esborrar un POM
    referenciat dona 409, no arrossega la col·locació.
    """
    SOURCE_VECTOR = 'vector'
    SOURCE_RASTER = 'raster'
    SOURCE_KIND_CHOICES = [(SOURCE_VECTOR, 'Vector'), (SOURCE_RASTER, 'Ràster')]

    # CASCADE: el precedent és del fitxer de catàleg; si el sketch d'origen desapareix, els
    # seus precedents no tenen sentit. (D1: la casa del precedent és l'ItemFitxer.)
    item_fitxer = models.ForeignKey(
        ItemFitxer, on_delete=models.CASCADE, related_name='pom_placements')
    pom = models.ForeignKey(
        'pom.POMMaster', on_delete=models.PROTECT, related_name='placements')
    # Slug de vista dins la pàgina: canònics 'front'/'back'/'detail', sufix lliure
    # ('detail-coll'). NO és un enum tancat (D4): el vocabulari de vistes el fixa el producte.
    view_slot = models.SlugField(max_length=40)
    # Extrems A→B de la cota, normalitzats 0..1 sobre la bbox de l'objecte sketch.
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()
    # Offset del centre de l'etiqueta respecte del punt mig del segment, normalitzat sobre les
    # dimensions de la bbox (captura un arrossegament manual del contenidor vermell; 0,0 = default).
    label_dx = models.FloatField(default=0)
    label_dy = models.FloatField(default=0)
    # Traça de qualitat de l'origen (mai jerarquia): 'vector' és exacte; 'raster' depèn de la
    # bbox de la imatge (v. avís bbox≠silueta).
    source_kind = models.CharField(
        max_length=8, choices=SOURCE_KIND_CHOICES, default=SOURCE_VECTOR)
    creat_per = models.ForeignKey(
        'accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pom_placements_creats')
    creat_el = models.DateTimeField(auto_now_add=True)
    actualitzat_el = models.DateTimeField(auto_now=True)
    # C1 — la capa (declaració canònica a `models_app.BaseMeasurement.capa`). Una cota del
    # folre i una cota de l'exterior poden voler dos traços diferents sobre el mateix sketch.
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
                  "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).",
    )
    # C1-ins — la instància (declaració canònica a `models_app.BaseMeasurement.instancia`).
    # És l'eix que la cota necessita més literalment de tots: la sisa dreta i l'esquerra
    # s'assenyalen amb DUES fletxes en llocs diferents del mateix croquis.
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
                  "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).",
    )

    class Meta:
        verbose_name = 'Col·locació de cota POM (precedent)'
        verbose_name_plural = 'Col·locacions de cota POM (precedent)'
        constraints = [
            # C1/T3 — la clau incorpora la CAPA (v. `BaseMeasurement.Meta`). El nom canvia
            # amb els camps a posta: un constraint que digui `_item_pom_view` i en guardi
            # quatre menteix a qui llegeixi l'esquema. Cap consumidor el referencia pel nom.
            # C1-ins/T3 hi afegeix la INSTÀNCIA, i el nom torna a créixer amb els camps pel
            # mateix motiu: dues cotes del mateix POM al mateix slot són justament el cas
            # que aquesta taula ha de saber guardar (la sisa dreta i l'esquerra
            # s'assenyalen amb dues fletxes al mateix croquis).
            models.UniqueConstraint(
                fields=['item_fitxer', 'pom', 'view_slot', 'capa', 'instancia'],
                name='uniq_pomplacement_item_pom_view_capa_instancia'),
            # C1/T4 — la comporta (v. `BaseMeasurement.Meta`). C4 la retira per migració.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. [...]
            # 🚩 La decisió de producte sobre la col·locació automàtica (una cota o dues per a
            # un POM amb germanes) segueix OBERTA — v. el commit `b56b2dfb`. Retirar la
            # comporta no la pren: la deixa possible.
            # C1-ins — la comporta d'instància (v. `BaseMeasurement.Meta`). C4-ins la retira.
            # ✅ C4/G3 (04/08) — retirada per la migració 0078. [...]
        ]
        indexes = [
            models.Index(fields=['item_fitxer', 'view_slot'],
                         name='idx_pomplacement_item_view'),
        ]

    def __str__(self):
        return f'{self.item_fitxer_id} · POM {self.pom_id} @ {self.view_slot}'
```

**Cens de relacions**: `POMPlacement` **no té cap fill** (`related_objects` buit). FKs cap amunt: `item_fitxer → models_app.ItemFitxer` **CASCADE**, `pom → pom.POMMaster` **PROTECT**, `creat_per → accounts.UserProfile` **SET_NULL**. Tots amb `db_constraint=True`.

**Constraints reals a BD** (`fhort.models_app_pomplacement`): `PRIMARY KEY (id)`; `UNIQUE (item_fitxer_id, pom_id, view_slot, capa, instancia)` (nom `uniq_pomplacement_item_pom_view_capa_instancia`); 3 FK DEFERRABLE; i **14 constraints `NOT NULL` amb nom propi** (Django 6 els materialitza com a constraints amb nom: `..._x1_not_null`, `..._view_slot_not_null`, etc.). **Cap CHECK de domini** (les dues comportes van caure amb `0078`).

---

### B5.2 · p1/p2, absència de sentit, i com es persisteix `view_slot`

**¿Té p1/p2?** **No com a punts: com a QUATRE escalars plans** (`models.py:1453-1457`):

```python
    # Extrems A→B de la cota, normalitzats 0..1 sobre la bbox de l'objecte sketch.
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()
```

Tots quatre **`NOT NULL` sense default** (`..._x1_not_null` … `..._y2_not_null` a BD). No hi ha `JSONField`, no hi ha taula filla de punts, no hi ha `ArrayField`. La cardinalitat **2 està cuita a l'esquema**: exactament dos extrems, mai un ni tres.

**¿Hi ha absència de sentit (direcció)?** **SÍ, hi ha absència de sentit — i és doble:**

1. **No hi ha cap camp de direcció.** L'única cosa que codifica un ordre és la **posició** de les columnes: el comentari diu «Extrems **A→B**». Es persisteix l'ordre en què l'usuari va dibuixar la cota, però **cap consumidor el llegeix com a sentit**.
2. **El render l'anul·la activament.** `frontend/src/pages/TechSheetEditor.jsx:397` — la cota viva es construeix amb **doble punta**: `headStart: true, headEnd: true`. Una fletxa amb punta als dos extrems **no té sentit observable**.
3. **La col·locació de l'etiqueta PLEGA EL SIGNE a posta** (`TechSheetEditor.jsx:377-384`):
   ```js
   export function cotaLabelOffset(dx, dy, halfW, halfH) {
     const len = Math.hypot(dx, dy) || 1
     let nx = -dy / len, ny = dx / len
     const EPS = 1e-6
     if (ny > EPS || (Math.abs(ny) <= EPS && nx < 0)) { nx = -nx; ny = -ny }
     const dist = COTA_LABEL_GAP_MM + Math.abs(nx) * halfW + Math.abs(ny) * halfH
     return { x: nx * dist, y: ny * dist }
   }
   ```
   El `if` normalitza la normal perpendicular perquè sempre apunti «amunt/dreta`: A→B i B→A donen **exactament el mateix offset**. El sistema tracta el segment com a **no orientat**.

   Conseqüència de terreny: la BD **conserva** un ordre (round-trip A→B fidel), però **cap capa el consumeix**, i per tant **ningú l'ha mantingut coherent**: no hi ha cap invariant, cap test, cap normalització que garanteixi que les files existents apuntin en un sentit consistent.

**Com es persisteix `view_slot`** — **denormalitzat: viu a DUES bandes.**

- **A la fila** (`models.py:1450-1452`): `view_slot = models.SlugField(max_length=40)` — `NOT NULL`, **sense default**, **no és enum** («NO és un enum tancat (D4): el vocabulari de vistes el fixa el producte»). Indexat sol (`..._view_slot_a262e0f8` + `_like`) i compost amb l'item (`idx_pomplacement_item_view`). Forma part de la clau única.
- **A l'escriptura**: `backend/fhort/models_app/pom_placement_views.py:136-138` — `view_slot = slugify(data.get('view_slot') or '')`, i **400 si queda buit**. És l'única normalització.
- **A la lectura**: `pom_placement_views.py:47-49` — `view_slot` és **paràmetre de query obligatori** del GET; sense ell, 400.
- **A l'origen (frontend)**: `view_slot` **NO és una propietat de la cota**: viu a l'**objecte sketch del document `.ftt`** (`o.viewSlot`), assignat a `TechSheetEditor.jsx:5599` (`assignaVista`) des d'un **input de text lliure amb `datalist`** a `:7510`. Es copia al body de la petició a `:5760` (`view_slot: host.viewSlot`) i es propaga a la cota viva a `:5657` i `:5864`.
  → **la vista la decideix el DOCUMENT i la BD només la guarda com a string**. No hi ha cap taula de vistes; el vocabulari no està tancat enlloc.

---

### B5.3 · Dimensionat dels DOS canvis, per separat

#### (a) FK a `element`

**El problema previ, abans de cap columna**: `POMPlacement` **no penja del `Model`, penja del CATÀLEG** (`ItemFitxer` → `tasks.GarmentTypeItem`). Ja està censat com «el cas anòmal»: `docs/diagnosis/DIAGNOSI_FEDERACIO_INTERACTIVITAT.md:180-193, 299, 533-550, 701, 754` («**`POMPlacement` divergeix per una via diferent** (catàleg, no Model) … **OBERT** — cap partició per-model l'arregla»). Si «element» és una entitat **del model** (peça sembrada dins del model), un FK directe des d'aquesta taula **travessa la frontera D1**: el precedent és una veritat de catàleg compartida per tots els models derivats de l'item; apuntar a l'element d'**un** model la converteix en una veritat d'aquell model. El destí del FK (element-de-model vs. element-de-catàleg) **no és una decisió d'implementació: és la decisió**.

**Impacte sobre constraints**:
- `uniq_pomplacement_item_pom_view_capa_instancia` — **exactament el mateix problema NULL-distinct** que a B2.2(b): amb `element_id` nullable dins la clau, totes les files amb `element_id IS NULL` deixen de ser mútuament úniques.
  **Diferència de cost respecte de `BaseMeasurement`**: aquí **ja és un `UniqueConstraint` amb nom, no un `unique_together`** (la migració `0071_capa_unicitats` ho documenta explícitament). Passar-lo a `nulls_distinct=False` és un `RemoveConstraint`+`AddConstraint` — **una operació, no dues**. `BaseMeasurement` s'ha de convertir primer.
- Cap CHECK de domini a la taula → res més a revalidar.
- FK nou `element_id`: `on_delete` a decidir. `item_fitxer` ja és CASCADE i **ja s'ha vist actuar** (v. B5.4: el wipe del 06/08 es va endur 2 dels 4 placements per la via de l'`ItemFitxer`).

**Consumidors que es trencarien (element)**:

*Backend*
- `models_app/pom_placement_views.py:53-54` — `def clau(p): return (p.pom_id, p.capa, p.instancia)`. Terna → col·lapsaria dos elements.
- `pom_placement_views.py:57-66` — els diccionaris `exacte` / `germana` / `merged` construïts sobre aquesta clau.
- `pom_placement_views.py:83-88` — `bm_by_pom` = `BaseMeasurement...values_list('pom_id','capa','instancia','id')`. **Aquest mapa lliga el precedent a la mesura viva**: si `BaseMeasurement` guanya `element` i aquest mapa no, la cota es materialitzaria amb el `bm_id` d'un altre element. El comentari de la mateixa vista (`:78-82`) ja descriu aquest mode de fallada per a `capa`: «una cota col·locada sobre el folre rebria el `bm_id` de l'exterior … **el pitjor cas d'aquesta vista, perquè no peta: pinta**».
- `pom_placement_views.py:96-106` — **el payload de resposta no publica `capa` ni `instancia`**, només `pom_id`, `bm_id`, `codi`, geometria, `source_kind`, `derivat`. Un eix nou tampoc hi sortiria: cal ampliar el contracte.
- `pom_placement_views.py:157-161` — l'`update_or_create` fixa **literals**: `capa=MeasurementLayer.SLUG_DEFECTE, instancia=''`. Un `element` nou s'hi hauria d'afegir igual, i el comentari de `:145-155` explica per què això és el punt sensible (l'escriptura fusionava el que la lectura ja sabia separar).
- `models_app/pom_vision_service.py:95` — el **contracte del prompt de la IA**: `{"placements":[{"pom_id":<int>,"object_id":"<str>","x1":<0..1>,"y1":<0..1>,…}]}`. La IA proposa **per `pom_id` pelat**; amb elements, ha de saber de quin element parla o el consumidor ha de resoldre-ho.

*Frontend* (`frontend/src/pages/TechSheetEditor.jsx`)
- `:5624-5628` — el mapa de propostes s'indexa **per `p.pom_id` sol**: `acc.set(p.pom_id, { p, derivat, hostId })`. ⚠️ **Això NO és un descuit**: el comentari de `:5640-5644` ho declara doctrina — «el precedent segueix sent del POM (una col·locació de catàleg **no sap res de capes**: és on va la cota d'aquest POM sobre aquest croquis)». O sigui: **la clau de 5 columnes de la BD ja avui es col·lapsa a `pom_id` a la vora del payload, a posta.** Afegir `element` obliga a **reobrir aquesta decisió de producte**, no només a afegir una columna.
- `:5645-5661` — `buildCotaDeProposta(bm, prop)`: llegeix `p.x1..p.y2` i **agafa els eixos del `bm`, no del precedent** (`capa: bm.capa, instancia: bm.instancia`). El mateix patró serviria per a `element` **si i només si** el precedent segueix sent per-POM.
- `:5748-5767` — `construirPrecedentCota`: construeix el body `{pom_id, view_slot, x1..y2, label_dx, label_dy, source_kind}`. **No envia `capa` ni `instancia`**; tampoc enviaria `element`.
- `:321-322` — `identitatDeCota` / `identitatDeFila`, el format `pom|capa|instancia` escrit a mà (duplicat de `pom/identitat.py:38`).
- `:5599`, `:7510` — assignació de `viewSlot` a l'objecte sketch.
- `:5847-5870` — el consumidor de la proposta IA (mateixa desnormalització de `p.x1..p.y2`).

#### (b) Polilínia ordenada amb sentit

**Impacte sobre l'esquema**: `x1,y1,x2,y2` són **4 columnes `NOT NULL` sense default**. Una polilínia vol o bé un `JSONField` de punts ordenats, o bé una taula filla `POMPlacementPoint(placement, ordre, x, y)`. En tots dos casos les 4 columnes actuals **han de morir o quedar derivades**, i cal **migració de dades** de les files existents (avui **2 a `fhort`**, ≈4 al dump).
El **sentit** vol un camp nou (o una convenció d'ordre declarada + normalització de les files existents — que, com s'ha vist a B5.2, **no estan normalitzades perquè ningú no les ha llegit mai com a orientades**).

**Impacte sobre constraints**: **cap**. La clau única no menciona la geometria, cap índex la toca, cap CHECK la valida. La geometria és, literalment, **columnes lliures**.

**Consumidors que es trencarien (polilínia + sentit)**:

*Backend*
- `pom_placement_views.py:103` — `'x1': p.x1, 'y1': p.y1, 'x2': p.x2, 'y2': p.y2` al payload.
- `pom_placement_views.py:128,133` — `coords = {k: float(data[k]) for k in ('x1','y1','x2','y2')}` i el 400 «pom_id i x1..y2 són obligatoris i numèrics».
- `pom_placement_views.py:160` — `defaults={**coords, ...}`.
- `models_app/pom_vision_service.py:95` — el prompt de la IA demana literalment `x1,y1,x2,y2`: passar a polilínia **reescriu el contracte amb el model de visió**.

*Frontend*
- `:5758-5765` (`construirPrecedentCota`) — normalitza **només dos extrems** sobre la bbox.
- `:5650-5653` (`buildCotaDeProposta`) i `:5858-5861` (proposta IA) — desnormalitzen **només dos extrems**.
- `:389-427` (`buildLiveCota`) — construeix un `path` de **2 nodes**.
- `:352` (`cotaEndsMm`) — extreu **dos** extrems.

**🔑 Descobriment que abarateix (b)**: **la cota VIVA del `.ftt` JA ÉS una polilínia**. `buildLiveCota` (`:399-405`) crea un objecte `type:'path'` amb `paths[].segments[]` (nodes amb `inX/inY/outX/outY`, o sigui suport de corba de Bézier), i `cotaHandleEnds` (`:433-437`) ho diu explícitament:

> «Un `path` corbat pot tenir >2 nodes: l'extrem és el primer i l'últim, no segs[1] (**`cotaEndsMm` assumeix recte, per al precedent**)».

O sigui: **l'editor ja sap dibuixar i desar cotes de N nodes al `.ftt`; l'aplanament a dos extrems és exclusivament del PRECEDENT** (`POMPlacement`) i de la funció `cotaEndsMm` que l'alimenta. El canvi (b) no és «ensenyar polilínies al sistema»: és **deixar de perdre-les en desar el precedent**.

#### ¿Comparteixen migració o són separables?

**Separables a la BD, acoblats a l'endpoint.**
- **A la BD són ortogonals**: (a) toca `element_id` + el `UniqueConstraint`; (b) toca `x1..y2`. **Cap constraint els relaciona** (la clau única no menciona la geometria; la geometria no té índex ni CHECK). Dues migracions independents, en qualsevol ordre.
- **A l'aplicació comparteixen les MATEIXES ~50 línies**: `_desar_precedent` (`pom_placement_views.py:112-166`) i `_cascada` (`:46-110`) són l'únic escriptor i l'únic lector, i **tots dos canvis reescriuen el body de la petició i el payload de la resposta**, consumits pels **mateixos** blocs de `TechSheetEditor.jsx` (`:5620-5661`, `:5748-5797`, `:5840-5870`). Fer-los en dues onades vol dir **dues rondes de contracte HTTP i dos desplegaments de frontend** sobre les mateixes funcions.
- ⚠️ **Recordatori d'infra** (memòria `ftt-tram-t-n-cataleg-i-neteja`): staging serveix `frontend/dist` → qualsevol canvi de contracte al frontend **exigeix rebuild**, i el gunicorn serveix el codi de quan va arrencar (`systemctl restart ftt-staging`).

---

### B5.4 · Recompte de placements per schema

| schema | `models_app_pomplacement` |
|---|---|
| `public` | **la taula NO existeix** (`models_app` és tenant-only, `settings.py:62-75`) |
| `fhort` | **2** |
| `los` | **0** |

Les dues files vives a `fhort` (`id, item_fitxer_id, pom_id, view_slot, x1, y1, x2, y2, capa, instancia, source_kind`):

```
(1, 14, 284, 'front', 0.25, 0.15, 0.75, 0.15, 'exterior', '', 'vector')
(3, 14, 379, 'front', 0.10, 0.30, 0.50, 0.30, 'exterior', '', 'vector')
```

Observacions de terreny:
- **`id=2` falta** → hi va haver un esborrat. El **dump pre-wipe** (`/root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump`, llegit amb `pg_restore --data-only -f -` a **stdout**, cap BD tocada) en tenia **≈4**, amb **3 `ItemFitxer`**; avui n'hi ha **1**. El wipe del 06/08 se'n va endur 2 **per la via `ItemFitxer` CASCADE**, no pel `Model` (aquesta taula no penja del Model). És la confirmació empírica del precedent que el brief cita: **un CASCADE no bloqueja, s'enduu files**.
- Les dues supervivents són **totalment horitzontals** (`y1 == y2`) i **totes dues del mateix `item_fitxer=14`, mateix `view_slot='front'`**, `capa='exterior'`, `instancia=''`. Amb `y1==y2` i el plegat de signe de `cotaLabelOffset`, **el sentit d'aquestes dues files és, literalment, no observable**.
- `fhort.models_app_itemfitxer` = **1**, `fhort.models_app_model` = **0**, `los.models_app_itemfitxer` = **0**.

---

## Què NO s'ha pogut determinar en lectura

1. **Què és exactament un «element»**: no existeix cap model `Element`, `ModelPeca`, `GarmentPiece` ni equivalent al codi (cerca exhaustiva de `class .*Element|class .*Peca|class GarmentPiece|class ModelPeca` → només `SembraRolsDePecaTest` i `PecaGrupRoundtripTest`, que són tests d'altres coses). **Tot el dimensionat d'aquest informe assumeix una entitat nova encara no escrita**; el seu schema (tenant?), la seva casa (Model? ItemFitxer? tots dos?) i la seva cardinalitat no es poden llegir.
2. **A quin element apuntaria `POMPlacement`**: com que la taula penja del **catàleg** i no del Model, un FK a un element-de-model és una violació de D1 que la lectura pot detectar però **no resoldre**. `DIAGNOSI_FEDERACIO_INTERACTIVITAT.md:754` ja marca aquest punt com a **OBERT**.
3. **Si el precedent ha de ser per-element o seguir sent per-POM**: `TechSheetEditor.jsx:5640-5644` declara doctrina explícita («una col·locació de catàleg no sap res de capes») i el commit `b56b2dfb` deixa **OBERTA** la decisió de producte germana («una cota o dues per a un POM amb germanes»). És decisió d'Agus/producte, no de codi.
4. **El sentit de les files existents**: com que cap consumidor llegeix l'orientació, **no es pot saber per lectura si l'ordre A→B de les 2 files vives és intencionat**. Amb `y1==y2` a totes dues, no hi ha ni tan sols un heurístic per inferir-ho.
5. **Estat a PROD**: sense SSH a PROD, els recomptes d'aquest informe són **només de staging** (`fhort`, `los`). `DIAGNOSI_SEMBRA_FASE2_VIABILITAT.md:25-26` registra «a PROD hi ha **0 ItemFitxer i 0 POMPlacement** als DOS schemas», però no s'ha verificat en aquesta sessió.
6. **Si els 3 serializers amb `allow_blank=False` viu** (`POMAlertSerializer`, `GarmentTypePOMMapSerializer`, `GarmentGroupPOMMapSerializer`) **arriben a rebre un `instancia: ''` d'una pantalla real**: la lectura confirma el desajust del contracte, però no si hi ha cap camí d'UI que l'exerciti (caldria córrer les pantalles).
7. **Cost de PROD/dades reals de la migració**: `fhort` té **0 `BaseMeasurement`** post-wipe, o sigui que qualsevol backfill mesurat contra staging **mesuraria zero**. La mida real de la migració s'ha d'estimar contra el dump (≈693 files) o contra PROD.
