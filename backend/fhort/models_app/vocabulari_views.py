"""
fhort/models_app/vocabulari_views.py
LES ENUMERACIONS DE DOMINI, PUBLICADES: règims de graduació, fases i estats.

**PER QUÈ EXISTEIX.** Mateixa raó, i mateix patró, que `pom/identity_views.py` (el vocabulari de
capes i instàncies): les llistes estaven als `choices` dels models des de sempre i **cap endpoint
les publicava**, o sigui que el frontend se les havia d'escriure a mà. I havien derivat: la còpia
dels règims a `SizeMapSetup.jsx` en tenia QUATRE quan el model en declara CINC —hi faltava
`EXCEPTION`—, i una maqueta va arribar a dibuixar un `LINEAR+BREAK` que no existeix ni pot
existir (el break és una PROPIETAT de la regla, no un règim: v. `pom/grading_regime.py`).

La llei que això fa complir (Agus, 08/08): **cap enumeració de domini es declara al frontend**.
Una constant al client que dupliqui uns `choices` és una segona font de veritat que ningú
actualitza el dia que la primera canvia.

**PER QUÈ UN SOL ENDPOINT I NO QUATRE.** Són quatre llistes curtes i cap pantalla en fa servir
una de sola: la llista de models filtra per fase I per estat; la superfície de graduació
necessita els règims i el context del model. Quatre peticions per pintar una pantalla serien
quatre rellotges per a una sola pregunta.

**ELS CODIS NO ES TRADUEIXEN.** `LINEAR`, `FIXED`, `Pending`, `TOP` són DADA de domini, com un
codi de POM: viatgen crus i s'ensenyen crus. La mateixa llei que `MeasurementInstance` ja
aplica als noms d'instància (v. `utils/capaInstancia.js`). Per això aquí s'emet `codi` i
`etiqueta` —l'etiqueta que ve dels propis `choices`— i no cap `nom_ca`/`nom_es`: si algun dia
alguna d'aquestes llistes s'ha de traduir, la decisió serà d'Agus i el lloc serà una taula, no
aquest endpoint.

⚠️ **DUES «FASES» QUE NO SÓN LA MATEIXA COSA**, i per això tenen claus diferents i explícites:
`fases_model` és el cicle de vida del MODEL (`Model.FASE_CHOICES`: Pending…TOP) i `fases_tasca`
és la fase d'una TASCA del pla de treball (`tasks.TaskType.FASE_CHOICES`: Disseny…Producció). Són
vocabularis independents. `components/PhaseStepper.jsx` les barrejava —i hi afegia `'Nou'` i
`'Tancat'`, que són d'`ESTAT_CHOICES`, i un `'Tècnic'` que no existeix enlloc (la fase real és
`'Dev. tècnic'`)—; és codi mort i no el consumeix ningú, però el report ho deixa dit.

────────────────────────────────────────────────────────────────────────────────────────────
**CODA F2.2 (Agus, 08/08) — LA MARCA LA POSA EL BACKEND, MAI UNA LLISTA AL CLIENT.**

Publicar una enumeració crua no és suficient: hi ha llistes on **no tots els membres valen per a
tot**. Un `codi` pot ser dada legítima que es LLEGEIX i alhora una opció que ningú no ha de poder
TRIAR. Fins ara això es resolia amb una llista escurçada al client —`REGIMS = ['LINEAR','STEP',
'FIXED']` a `GraduacioSuperficie`— i això és exactament la segona font de veritat que aquest
mòdul existeix per matar, només que disfressada de filtre.

La llei: **la marca viatja amb l'element**. El client ofereix el que l'endpoint diu que és
oferible, i no perquè ell en tingui una llista pròpia. Dues marques, i les dues són PROPIETATS
d'un membre, no llistes a part:

  · `regims_graduacio[].autorable` — ¿un tècnic pot TRIAR aquest règim en escriure una regla?
  · `estats_sessio_fitting[].segellat` — ¿en aquest estat la sessió és de només lectura?

Ho fem així i no amb dues llistes paral·leles (`regims_autorables: [...]`) perquè una llista
paral·lela es pot desincronitzar de la principal; un booleà al costat del codi, no.

**ELS NO-AUTORABLES, I PER QUÈ CADASCUN.** El règim és una columna de `GradingRule`, o sigui que
els cinc valors són LLEGIBLES i cap desapareix de la llista: el que la marca diu és si es pot
ESCRIURE de nou.

  · `EXCEPTION` — **és una PETJA que escriu el motor, no un règim que es triï.** `pom/services.py`
    (:177, :259, :266) l'estampa a `grading_type_applied` quan la cel·la ve d'un
    `ModelGradingOverride` o del folre (:768). Cap camí d'autoria l'escriu ni el pot escriure.
    Oferir-lo en un select deixaria que un tècnic marqués una regla com a override sense ser-ho.

  · `ZERO` — **cap camí el produeix ni el porta cap dada viva.** El detector
    (`pom/grading_utils.py:245-256`) només pot sortir amb LINEAR, STEP o FIXED. A la BD de
    staging, de 1.267 regles n'hi ha 1.034 LINEAR i 233 FIXED: **zero ZERO, zero STEP, zero
    EXCEPTION**. I la única raó escrita que hi ha al codi el descarta explícitament
    (`GraduacioSuperficie.jsx:81` — «ZERO i EXCEPTION NO s'ofereixen com a tria nova; ZERO =
    nínxol "sempre 0"»); «sempre 0» ja és FIXED amb base 0, i el mateix full en surt.
    🛑 **NO és unànime i va al report:** `SizeMapSetup.jsx:21` SÍ que l'ofereix, sense cap raó
    escrita. La marca resol la contradicció en el sentit de l'única raó documentada. Si l'Agus
    la vol en l'altre sentit, és **una línia**: treure `LOGICA_ZERO` de `REGIMS_NO_AUTORABLES`.

**LES ≈25 SENSE ENDPOINT — PARTICIÓ PER FASE (Agus, 08/08).** No s'exposen totes de cop: cada
enumeració s'exposa quan la SEVA pantalla passa conformitat. Aquí hi entren ara les de la Fase A
—veredictes de fitting i estats de sessió— i la resta (comanda, oferta, albarà, encàrrec, rols,
capabilities, geometria…) queda **CENSAT-PENDENT** al report, amb les constants del client vives
fins llavors. Afegir-les totes ara seria publicar vocabulari que ninguna pantalla conforme
consumeix, i el dia que la pantalla arribés ningú no sabria si l'endpoint encara diu la veritat.

**UNITATS I NORMES: COMPROVAT, I NO S'EXPOSEN.** L'ordre les condicionava a que les pantalles de
Mesures/Fitting les PINTESSIN. No les pinten: el selector de `CM`/`INCH` i el d'`ISO_8559`/
`ASTM_D13` viuen només a `GeneralConfig.jsx:13,14` (mòdul Sistema) i a `OnboardingWizard.jsx:110`
(alta). Mesures i Fitting només CONSUMEIXEN el valor que el tenant ja ha triat
(`fittingShared.jsx:9-13` el llegeix de `/tenant-config/` per formatar), i consumir un valor no
és duplicar una enumeració. Queden CENSAT-PENDENT amb la resta del mòdul Sistema.
────────────────────────────────────────────────────────────────────────────────────────────

Lectura pura: cap escriptura, cap efecte, cap paràmetre.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.commerce.models import (DeliveryNote, DeliveryNoteLine, Product, Quote,
                                   SalesOrder, WorkOrder)
from fhort.fitting.models import FittingSession, PieceFittingLine
from fhort.fitting.services import SEALED_SESSION_ESTATS
from fhort.models_app.models import Model
from fhort.pom.models import CustomerPOMAlias, GradingRule
from fhort.tasks.models import Customer, ModelTask, TaskType
from fhort.tenants.federation_service import ESTATS_LOCALS_ENCARREC
from fhort.tenants.models import TenantLink

#: Règims que existeixen com a DADA però que cap camí d'autoria pot escriure. El raonament de
#: cadascun és a la capçalera del mòdul; aquí només hi ha la llista, perquè hi hagi UN sol lloc
#: on canviar-la el dia que la decisió canviï.
REGIMS_NO_AUTORABLES = frozenset({
    GradingRule.LOGICA_EXCEPTION,
    GradingRule.LOGICA_ZERO,
})


def _choices_del_camp(model, camp):
    """Els `choices` que el CAMP accepta de debò, preguntats al `_meta` del model.

    NO ÉS UN PREÀMBUL: és la defensa contra l'error que aquest mòdul persegueix. Els tres
    documents comercials hereten `AbstractDocument.STATUS_CHOICES` (DRAFT·SENT·ACCEPTED·
    REJECTED·EXPIRED) i **dos dels tres el sobreescriuen** amb el seu propi cicle
    (`SalesOrder.SO_STATUS_CHOICES` OPEN·COMPLETED·CANCELLED · `DeliveryNote.DN_STATUS_CHOICES`
    DRAFT·ISSUED·INVOICED). Escrivint `SalesOrder.STATUS_CHOICES` s'obté l'heretada —cinc valors
    que aquell camp no accepta— i el codi sembla correcte. El mateix problema, amb la mateixa
    cara, que va fer que un cens comptés els `ORIGEN_CHOICES` equivocats de `pom/models.py`, que
    en té QUATRE blocs diferents (:147, :214, :282, :513).

    Preguntar-ho al camp no es pot equivocar: és exactament el que la BD validarà.
    """
    return model._meta.get_field(camp).choices


def _llista(choices, marca=None):
    """`[(codi, etiqueta), …]` → `[{codi, etiqueta}, …]`, en l'ordre en què el model els declara.

    L'ORDRE ÉS PART DE LA DADA: les fases d'un model van en seqüència (Pending → … → TOP) i
    reordenar-les alfabèticament al client trencaria qualsevol stepper que les pinti.

    `marca` és `(nom, predicat)` i afegeix UNA propietat booleana a cada element —la marca viatja
    AMB el membre i no en una llista paral·lela que es pugui desincronitzar (v. capçalera).
    """
    files = [{'codi': c, 'etiqueta': str(e)} for c, e in choices]
    if marca:
        nom, predicat = marca
        for f in files:
            f[nom] = predicat(f['codi'])
    return files


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vocabulari_domini_view(request):
    """
    GET /api/v1/vocabulari/

    → FASE A: {regims_graduacio, fases_model, estats_model, fases_tasca,
               estats_sessio_fitting, veredictes_fitting}
      PART B · lot comercial: {estats_oferta, estats_comanda, estats_albara, estats_encarrec,
               tipus_encarrec, origens_encarrec, tipus_linia_albara, natures_producte,
               modes_preu_producte, estats_tasca, origens_alias_pom, regims_fiscals_client,
               metodes_pagament_client, estats_vincle_tenant, estats_locals_encarrec}

    Cada element: `{codi, etiqueta}`. El `codi` és el que es desa i el que viatja a l'API;
    l'`etiqueta` és la del `choices` i és per als ulls. Dues llistes porten una marca de més
    (`autorable`, `segellat`): v. la capçalera del mòdul.

    ⚠️ **`veredictes_fitting` NO porta el buit, i és a posta.** `PieceFittingLine.decisio` admet
    `''` —«sense decidir»— però `''` **no és un membre de l'enumeració**: és l'absència de
    veredicte. Emetre'l aquí faria que qualsevol select el pintés com una quarta opció triable i
    tornaria a ensorrar la distinció que `PieceFittingLine` defensa amb el `default=''`: una
    cel·la que ningú no ha mirat no és una cel·la acceptada. Qui hagi d'oferir «cap» que el posi
    com el que és, un buit de la seva UI, i no com un codi de domini.
    """
    return Response({
        'regims_graduacio': _llista(
            GradingRule.LOGICA_CHOICES,
            marca=('autorable', lambda c: c not in REGIMS_NO_AUTORABLES),
        ),
        'fases_model': _llista(Model.FASE_CHOICES),
        'estats_model': _llista(Model.ESTAT_CHOICES),
        'fases_tasca': _llista(TaskType.FASE_CHOICES),
        # FASE A · el cicle del fitting. `segellat` NO és una llista nova: és el mateix
        # `SEALED_SESSION_ESTATS` que `fitting_line_is_locked` fa complir a l'escriptura,
        # importat i no copiat. El client en tenia DUES còpies (`FittingDetail.jsx:164` i
        # `FittingConvocatoriaSheet.jsx:69`) i cap de les dues sabia que era un mirall d'un
        # guard: el dia que un tercer estat segellés, la pantalla hauria seguit deixant escriure
        # fins que el 403 del backend l'aturés.
        'estats_sessio_fitting': _llista(
            FittingSession.ESTAT_CHOICES,
            marca=('segellat', lambda c: c in SEALED_SESSION_ESTATS),
        ),
        # FASE A · el veredicte de la modista (D-31.21). Codis crus: van en anglès a totes les
        # llengües perquè són el que el full imprès porta cap al fabricant.
        'veredictes_fitting': _llista(PieceFittingLine.DECISIO_CHOICES),

        # ══ PART B · LOT COMERCIAL ═══════════════════════════════════════════════════════
        # Entren ara perquè les SEVES pantalles passen conformitat ara (§ «partició per fase»
        # de la capçalera): Clients · fitxa del client · Proveïdors · Productes · Ofertes ·
        # Comandes · Encàrrecs · WorkOrderDetail · Albarans · Orfes · Condicions de pagament.
        # Cens fet pel lot comercial, contrastat aquí contra el `_meta` de cada camp.
        #
        # ELS TRES ESTATS DE DOCUMENT VAN PEL CAMP, no per la constant: v. `_choices_del_camp`.
        'estats_oferta': _llista(_choices_del_camp(Quote, 'status')),
        'estats_comanda': _llista(_choices_del_camp(SalesOrder, 'status')),
        'estats_albara': _llista(_choices_del_camp(DeliveryNote, 'status')),
        'estats_encarrec': _llista(_choices_del_camp(WorkOrder, 'status')),
        'tipus_encarrec': _llista(_choices_del_camp(WorkOrder, 'kind')),
        'origens_encarrec': _llista(_choices_del_camp(WorkOrder, 'origin')),
        # ⚠️ EL CAMP ES DIU `line_kind`, NO `kind` — i preguntar-ho al `_meta` és el que ho ha
        # dit: amb `kind` això explotava amb `FieldDoesNotExist`. Publicar la constant
        # `LINE_KIND_CHOICES` a cegues hauria funcionat i hauria estat igual de correcte per
        # casualitat; el dia que la constant i el camp divergeixin, aquesta forma peta i l'altra
        # menteix.
        'tipus_linia_albara': _llista(_choices_del_camp(DeliveryNoteLine, 'line_kind')),
        'natures_producte': _llista(_choices_del_camp(Product, 'nature')),
        'modes_preu_producte': _llista(_choices_del_camp(Product, 'price_mode')),
        'estats_tasca': _llista(_choices_del_camp(ModelTask, 'status')),
        # 🚨 LA QUE JA HAVIA DERIVAT, i és el cas de manual del perquè existeix aquest endpoint.
        # `CustomerDetail.jsx` en declarava QUATRE valors amb el comentari «els QUATRE choices
        # d'origen del model»; el model en declara CINC des que el cercador de Definició POM va
        # estrenar el camí «Crear POM propi del model» (`pom/wizard_views.py:694` escriu
        # `origen='MODEL'`, provinença PERMANENT). Ningú va tornar al fitxer del client, i el
        # resultat és visible a pantalla AVUI: un àlies nascut d'un model pinta la clau i18n
        # crua a la cel·la, perquè l'etiqueta es construeix per interpolació del codi.
        'origens_alias_pom': _llista(_choices_del_camp(CustomerPOMAlias, 'origen')),
        'regims_fiscals_client': _llista(_choices_del_camp(Customer, 'tax_regime')),
        'metodes_pagament_client': _llista(_choices_del_camp(Customer, 'payment_method')),
        'estats_vincle_tenant': _llista(TenantLink.ESTAT_CHOICES),
        # L'ÚNICA QUE NO SURT DE CAP `choices` I ENTRA IGUAL. `estat_local` d'un model de la
        # safata és una COMPARACIÓ, no un camp (`federation_service.safata_del_studio`: el
        # `codi_intern` del Brand ¿ja existeix al meu schema?), i això és a posta —així no es
        # pot desincronitzar. Però el conjunt de valors que una pantalla ha de saber pintar és
        # una enumeració de domini encara que la dada sigui derivada, i `Encarrecs.jsx` en
        # tenia la còpia. Es publica des de la constant del MÒDUL QUE LA CALCULA, mai d'una
        # llista escrita aquí: si algun dia n'hi ha un tercer, arriba sol.
        'estats_locals_encarrec': _llista(ESTATS_LOCALS_ENCARREC),
    })
