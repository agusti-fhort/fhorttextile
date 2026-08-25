"""M4 · BANC SINTÈTIC DEL DESBORDAMENT — una comanda amb numeral, i una volta que el passa.

⚠️ **AQUEST SCRIPT ESCRIU.** Fabrica models NOUS amb prefix `[QA-M4]` i un document comercial
sintètic; **mai el 1383**, mai el golden 162, mai un model o una comanda reals.

🔑 **PER QUÈ NO ES MUNTA SOBRE `[QA-M1]`.** El brief demana el fum sobre aquell banc, i no s'hi
pot fer: **cap model de `[QA-M1]` té comanda** —ni cap model de `fhort`, segons el cens del
25/08: 0 `WorkOrder` de tipus `ORDER` als dos tenants— i sense comanda no hi ha numeral, o sigui
que el desbordament no existeix (comportament explícit, no error: v. `numeral_efectiu`).
Enganxar una comanda a un model de `[QA-M1]` mutaria el banc que els fums d'M1, M1-bis, M2 i M3
segueixen consumint. El banc d'M4 és germà del d'M1, amb el MATEIX `Customer`, i per tant surt a
la MATEIXA safata d'albaranables: el fum els veu tots dos alhora.

**IDEMPOTENT**: la guarda és `codi_intern` amb prefix `QA-M4-` i `document_number` de la comanda.

🔑 **TOT PEL CAMÍ NORMAL**: les voltes per `services_r.obrir_ronda`/`ronda_del_gest`, els estats
per `transition_task`, i el veredicte de desbordament el resol el codi de producte en obrir —el
banc **no escriu `fora_de_comanda` a mà** enlloc. Un banc que el forcés no provaria res.

    venv/bin/python ../ops/qa/banc_m4_desbordament.py               (des de backend/)
    venv/bin/python ../ops/qa/banc_m4_desbordament.py --remunta     (esborra el banc i el refà)
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django_tenants.utils import schema_context                        # noqa: E402

from fhort.accounts.models import UserProfile                          # noqa: E402
from fhort.commerce.models import (Product, SalesOrder, SalesOrderLine,   # noqa: E402
                                   WorkOrder)
from fhort.models_app.models import Model                              # noqa: E402
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask,  # noqa: E402
                                Ronda, TaskType, TimerEntrada)
from fhort.tasks.services_c import transition_task                     # noqa: E402
from fhort.tasks.services_g import lookup_estimated_minutes            # noqa: E402
from fhort.tasks.services_r import (obrir_ronda, ronda_del_gest,       # noqa: E402
                                    tancar_ronda)

PREFIX = 'QA-M4-'
TENANT = 'fhort'
PRODUCT_CODE = 'qa-m4-servei'
#: La marca del DRAFT sintètic on el fum de pantalla obre la safata.
MARCA_ALBARA = '[QA-M4] esborrany del banc de desbordament'
#: El numeral del pacte sintètic: 2 voltes incloses → la R3 desborda.
NUMERAL = 2
#: Quantes voltes treballa cada model del banc. La 3a del 0001 és la que ha de sortir marcada.
VOLTES = 3
CODE = 'pom'


def _tecnic_sense_feina_oberta():
    """Un perfil sense cap tram obert: entrar a `InProgress` pausa la feina real del tècnic
    que en tingui (l'exclusió de D-6 és GLOBAL, no per model)."""
    ocupats = set(TimerEntrada.objects.filter(fi__isnull=True, actiu=True)
                  .values_list('tecnic_id', flat=True))
    lliure = UserProfile.objects.exclude(pk__in=ocupats).order_by('pk').first()
    if lliure is None:
        raise SystemExit('Cap UserProfile sense trams oberts: no munto el banc per no pausar '
                         'la feina de ningú.')
    return lliure


def _crea_tasca(model, code, prof):
    """Una tasca com la fa un GEST DE TREBALL (i per tant fa néixer la R1 si cal)."""
    tt = TaskType.objects.get(code=code, active=True)
    return ModelTask.objects.create(
        model=model, task_type=tt, order=ModelTask.objects.filter(model=model).count(),
        status='Pending', origen='prevista',
        estimated_minutes=lookup_estimated_minutes(model, tt),
        ronda=ronda_del_gest(model))


def _acaba(task, prof):
    transition_task(task, 'InProgress', prof)
    task.refresh_from_db()
    transition_task(task, 'Done', prof)
    task.refresh_from_db()
    return task


def _comanda(customer):
    """La comanda sintètica amb el numeral. Idempotent per `product.code` + customer."""
    product, _ = Product.objects.get_or_create(
        code=PRODUCT_CODE,
        defaults={'name': '[QA-M4] Servei de desenvolupament', 'nature': 'INTERNAL_SERVICE',
                  'price_mode': 'FIXED', 'base_price': 120})
    linia = (SalesOrderLine.objects
             .filter(product=product, order__customer=customer)
             .order_by('pk').first())
    if linia is not None:
        if linia.rounds_included != NUMERAL:
            linia.rounds_included = NUMERAL
            linia.save(update_fields=['rounds_included'])
        return linia
    order = SalesOrder.objects.create(customer=customer, status='OPEN',
                                      notes='[QA-M4] comanda sintètica del banc de desbordament')
    linia = SalesOrderLine.objects.create(
        order=order, product=product, description='[QA-M4] Desenvolupament de peça',
        quantity=5, unit_price=120, rounds_included=NUMERAL)
    order.recalculate_totals()
    return linia


def _model_amb_voltes(codi, nom, customer, item, prof, linia):
    """Un model amb `VOLTES` voltes treballades i acabades. `linia=None` → sense comanda."""
    model = Model.objects.filter(codi_intern=codi).first()
    if model is not None:
        return model, False
    model = Model.objects.create(
        codi_intern=codi, codi_tenant='FTT', any=2026, temporada='SS',
        sequencial=int(codi[-4:]), customer=customer, garment_type_item=item, nom_prenda=nom)
    if linia is not None:
        # EL PIVOT model↔comanda. Es crea directament i no per `assign_model_to_order_line`
        # perquè aquell servei MIGRA les tasques del col·lector i imputa cartera: aquí el model
        # acaba de néixer i no té ni una cosa ni l'altra, i el que el banc necessita és
        # exactament el lligam que `linia_de_comanda` llegeix.
        WorkOrder.objects.create(
            customer=customer, model=model, kind='ORDER', status='OPEN', order_line=linia,
            price_snapshot={'unit_price': str(linia.unit_price), 'product_code': PRODUCT_CODE,
                            'tax_rate': str(linia.product.tax_rate)},
            recipe_snapshot={'task_codes': [CODE]})
        linia.qty_allocated = (linia.qty_allocated or 0) + 1
        linia.save(update_fields=['qty_allocated'])

    for volta in range(1, VOLTES + 1):
        if volta == 1:
            _acaba(_crea_tasca(model, CODE, prof), prof)     # el gest fa néixer la R1
        else:
            ronda = obrir_ronda(model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=prof)
            _acaba(ModelTask.objects.get(ronda=ronda, task_type__code=CODE), prof)
        # L'última volta es deixa OBERTA: és l'estat real d'una volta acabada de treballar i
        # encara no entregada, i la safata l'ha de saber ensenyar igualment.
        if volta < VOLTES:
            tancar_ronda(Ronda.objects.get(model=model, seq=volta), profile=prof)
    return model, True


def _albara_esborrany(customer):
    """L'albarà DRAFT sobre el qual el fum de pantalla obre la SAFATA.

    La safata no és una pantalla pròpia: viu dins d'un albarà en esborrany (el botó «Afegir de la
    safata» de `DeliveryNoteDetail`). Sense un DRAFT del client del banc no hi ha on obrir-la, i
    el fum de pantalla no podria mesurar l'agrupació per volta. Es marca a `notes` per poder-lo
    reconèixer i esborrar al `--remunta`; **neix buit i no s'hi afegeix cap línia**: albaranar
    segueix sent gest humà i el banc no el fa per ningú.
    """
    from fhort.commerce.services import create_or_get_draft
    draft, creat = create_or_get_draft(customer)
    if creat:
        draft.notes = MARCA_ALBARA
        draft.save(update_fields=['notes', 'updated_at'])
    return draft, creat


def desmunta():
    """Esborra NOMÉS el banc d'M4: els seus models i el seu document comercial."""
    from fhort.commerce.models import DeliveryNote
    DeliveryNote.objects.filter(status='DRAFT', notes=MARCA_ALBARA).delete()
    qs = Model.objects.filter(codi_intern__startswith=PREFIX)
    codis = list(qs.values_list('codi_intern', flat=True))
    ModelTask.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    Ronda.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    WorkOrder.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    qs.delete()
    ordres = list(SalesOrder.objects.filter(lines__product__code=PRODUCT_CODE)
                  .values_list('document_number', flat=True).distinct())
    SalesOrderLine.objects.filter(product__code=PRODUCT_CODE).delete()
    SalesOrder.objects.filter(document_number__in=ordres).delete()
    Product.objects.filter(code=PRODUCT_CODE).delete()
    print(f'desmuntats: {codis or "(cap)"} · comandes: {ordres or "(cap)"}')


def munta():
    prof = _tecnic_sense_feina_oberta()
    customer = Customer.objects.order_by('pk').first()
    item = GarmentTypeItem.objects.order_by('pk').first()
    if customer is None or item is None:
        raise SystemExit('Falta Customer o GarmentTypeItem al tenant: banc no muntable.')
    if not TaskType.objects.filter(code=CODE, active=True).exists():
        raise SystemExit(f'El TaskType «{CODE}» no existeix o és inactiu: banc no muntable.')

    linia = _comanda(customer)
    fets = [
        _model_amb_voltes(PREFIX + '0001', '[QA-M4] Amb comanda · R3 desborda',
                          customer, item, prof, linia),
        # EL CONTROL NEGATIU: mateixes voltes, cap comanda. Cap de les seves R ha de sortir
        # marcada — «sense numeral no hi ha límit» ha de ser visible al costat del cas positiu.
        _model_amb_voltes(PREFIX + '0002', '[QA-M4] Sense comanda · cap volta desborda',
                          customer, item, prof, None),
    ]

    draft, draft_nou = _albara_esborrany(customer)

    print(f'\n[QA-M4] client={customer.codi} · comanda={linia.order.document_number} '
          f'· línia={linia.pk} · numeral={linia.rounds_included} '
          f'· albarà DRAFT={draft.document_number} ({"nou" if draft_nou else "reaprofitat"})\n')
    print(f'{"model":<12} {"nou":<4} {"volta":<6} {"fora?":<6} {"numeral":<8} comanda')
    for model, nou in fets:
        for r in Ronda.objects.filter(model=model).order_by('seq'):
            com = r.linia_comanda.order.document_number if r.linia_comanda_id else '—'
            print(f'{model.codi_intern:<12} {"sí" if nou else "no":<4} R{r.seq:<5} '
                  f'{"SÍ" if r.fora_de_comanda else "no":<6} '
                  f'{r.numeral_vigent if r.numeral_vigent is not None else "—":<8} {com}')
    desbordades = Ronda.objects.filter(model__codi_intern__startswith=PREFIX,
                                       fora_de_comanda=True).count()
    print(f'\nvoltes FORA DE COMANDA al banc: {desbordades} (s\'espera 1)')


if __name__ == '__main__':
    with schema_context(TENANT):
        if '--remunta' in sys.argv:
            desmunta()
        munta()
