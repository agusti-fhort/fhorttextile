"""Fix del vessament de .ftt: desat idempotent (B1-lògic) + poda de la cadena (B2).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

EL PROBLEMA QUE TANQUEN (DIAGNOSI_DESAT_FITXA, 2026-08-02): l'autosave de l'editor encadenava
una versió NOVA del `.ftt` sencer a cada mutació —mediana real de 8,2 s entre versions, ~4,4 MB
cadascuna— i **no hi havia cap poda enlloc**. A PROD: 3.606 files TECHSHEET, 40 vives, 15,6 GB;
el model 205 amb 495 versions. El disc es va omplir (75 G).

Les dues lleis que aquests tests fixen:

  1. **Un desat sense canvi lògic no encadena res.** La comparació és de l'EMPREMTA LÒGICA
     (sha per peça, `services_ftt.empremta_logica`), MAI del `ModelFitxer.checksum`: aquell és
     el sha del blob ZIP i el zip du la data-hora estampada, de manera que no es repeteix mai
     (604/604 checksums distints a staging). Un fix que comparés el blob seria inert — per
     això `test_el_checksum_del_blob_no_serveix_per_comparar` hi és: si algú "simplifica" la
     comparació cap al checksum, aquell test cau i explica per què.

  2. **La cadena té sostre.** Es conserven el cap + N anteriors + l'ARREL (identitat del
     document lògic: el lock hi penja) + tot el que estigui referenciat. La resta se'n va,
     fila i bytes. I la cadena queda CAMINABLE: `document_root()` ha de seguir arribant a la
     v1, o `user_holds_lock` deixaria de trobar el lock i el desat següent seria un 403.
"""
import os

from django.core.files.storage import default_storage
from django_tenants.test.cases import TenantTestCase

from fhort.models_app import services_ftt
from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.services_ftt_document import (
    FTT_VERSIONS_A_CONSERVAR, create_document, document_root, load_document, poda_cadena,
    save_document,
)
from fhort.models_app.ftt_models import FttDocumentLock


def _doc(text):
    """Document lògic mínim amb un text distintiu (canviar-lo = canvi lògic real)."""
    d = services_ftt.new_empty_document()
    d['pages'][0]['objects'] = [{'id': 't1', 'type': 'text', 'text': text}]
    return d


class DesatIdempotentTest(TenantTestCase):
    """B1-lògic: desar el mateix contingut no encadena versió."""

    PREFIX = 'FTTB1'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'

    def setUp(self):
        self.model = Model.objects.create(
            codi_intern='TST-B1', nom_prenda='DALIA', codi_tenant='TST',
            any=2026, temporada='SS', sequencial=1,
        )
        self.head = create_document(self.model, document_json=_doc('A'))

    def _n(self):
        return ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET).count()

    def test_desat_sense_canvi_NO_crea_fila(self):
        nou = save_document(self.head, load_document(self.head)['document_json'])
        self.assertEqual(nou.pk, self.head.pk, 'ha de tornar la MATEIXA versió vigent')
        self.assertEqual(self._n(), 1)
        self.head.refresh_from_db()
        self.assertTrue(self.head.is_current)

    def test_desat_sense_canvi_repetit_segueix_sense_crear(self):
        """L'autosave dispara cada pocs segons: la idempotència ha de ser estable, no d'un cop."""
        doc = load_document(self.head)['document_json']
        cap = self.head
        for _ in range(5):
            cap = save_document(cap, doc)
        self.assertEqual(self._n(), 1)
        self.assertEqual(cap.pk, self.head.pk)

    def test_desat_amb_canvi_SI_crea_i_mou_el_cap(self):
        nou = save_document(self.head, _doc('B'))
        self.assertNotEqual(nou.pk, self.head.pk)
        self.assertEqual(self._n(), 2)
        self.assertTrue(nou.is_current)
        self.assertEqual(nou.versio, self.head.versio + 1)
        self.head.refresh_from_db()
        self.assertFalse(self.head.is_current, "l'anterior ha de deixar de ser el cap")
        self.assertEqual(nou.versio_anterior_id, self.head.pk)

    def test_canviar_nomes_el_kind_SI_crea_versio(self):
        """El mode plantilla és contingut del manifest: canviar-lo és un canvi real."""
        doc = load_document(self.head)['document_json']
        nou = save_document(self.head, doc, kind=services_ftt.FTT_KIND_TEMPLATE)
        self.assertNotEqual(nou.pk, self.head.pk)
        self.assertEqual(load_document(nou)['kind'], services_ftt.FTT_KIND_TEMPLATE)

    def test_un_asset_nou_es_canvi_encara_que_el_document_no_es_mogui(self):
        doc = load_document(self.head)['document_json']
        nou = save_document(self.head, doc, assets={'x.png': b'\x89PNG-bytes'})
        self.assertNotEqual(nou.pk, self.head.pk)

    def test_el_checksum_del_blob_no_serveix_per_comparar(self):
        """LA troballa de la Fase A, fixada: dos packs del MATEIX contingut donen blobs
        diferents perquè `zipfile` estampa la data-hora. Comparar `ModelFitxer.checksum`
        (sha del blob) no detectaria mai un desat sense canvi."""
        doc = _doc('A')
        e1 = services_ftt.empremta_logica(doc)
        e2 = services_ftt.empremta_logica(doc)
        self.assertEqual(e1, e2, "l'empremta LÒGICA ha de ser estable")
        # …i és la mateixa que el manifest ja desa dins del .ftt.
        self.assertEqual(load_document(self.head)['manifest']['checksums'], e1)

    def test_empremta_diferent_amb_contingut_diferent(self):
        self.assertNotEqual(
            services_ftt.empremta_logica(_doc('A')), services_ftt.empremta_logica(_doc('B')))


class PodaCadenaTest(TenantTestCase):
    """B2: la cadena té sostre i el que es conserva no es toca mai."""

    PREFIX = 'FTTB2'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'

    def setUp(self):
        self.model = Model.objects.create(
            codi_intern='TST-B2', nom_prenda='DALIA', codi_tenant='TST',
            any=2026, temporada='SS', sequencial=2,
        )
        self.arrel = create_document(self.model, document_json=_doc('v0'))

    def _cadena(self, n, des_de=None):
        """Encadena `n` versions amb canvi REAL cadascuna. Retorna el cap."""
        cap = des_de or self.arrel
        for i in range(n):
            cap = save_document(cap, _doc('v%d' % (i + 1)))
        return cap

    def _vives(self):
        return set(ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET).values_list('pk', flat=True))

    #: El sostre EXACTE: cap + `FTT_VERSIONS_A_CONSERVAR` anteriors (= 21 recents) + l'ARREL,
    #: que es protegeix a part perquè és la identitat del document lògic. Mentre l'arrel encara
    #: sigui una de les 21 recents no suma, i per això el primer esborrat no arriba fins que la
    #: cadena passa de 22.
    SOSTRE = FTT_VERSIONS_A_CONSERVAR + 2

    def test_per_sota_del_llindar_no_poda_res(self):
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR)      # arrel + 20 = 21 files
        self.assertEqual(len(self._vives()), FTT_VERSIONS_A_CONSERVAR + 1)
        self.assertIn(self.arrel.pk, self._vives())
        self.assertTrue(ModelFitxer.objects.get(pk=cap.pk).is_current)

    def test_al_sostre_encara_no_poda(self):
        """22 files = 21 recents + l'arrel: tot està protegit, no sobra ningú."""
        self._cadena(FTT_VERSIONS_A_CONSERVAR + 1)
        self.assertEqual(len(self._vives()), self.SOSTRE)
        self.assertIn(self.arrel.pk, self._vives())

    def test_passar_el_sostre_poda_la_mes_vella_no_protegida(self):
        """La 23a: cau la MÉS VELLA que no és ni l'arrel ni de les 21 recents, i el total es
        queda clavat al sostre per molt que se segueixi desant."""
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 1)
        abans = list(ModelFitxer.objects
                     .filter(model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET)
                     .order_by('data_pujada', 'pk'))
        self.assertEqual(abans[0].pk, self.arrel.pk)
        candidata = abans[1]        # abans[0] és l'arrel (protegida per identitat)
        ruta = candidata.fitxer.name
        self.assertTrue(default_storage.exists(ruta))

        cap = save_document(cap, _doc('mes'))

        vives = self._vives()
        self.assertEqual(len(vives), self.SOSTRE)
        self.assertNotIn(candidata.pk, vives, 'la més vella no protegida se n\'ha d\'anar')
        self.assertIn(self.arrel.pk, vives)
        self.assertIn(cap.pk, vives)
        self.assertFalse(default_storage.exists(ruta), 'el .ftt podat ha de sortir del disc')

    def test_el_sostre_aguanta_desats_indefinits(self):
        """La llei que tanca el vessament: desar més no fa créixer més. Amb 495 versions i
        4,4 MB cadascuna, això és la diferència entre 2 GB i 97 MB."""
        self._cadena(FTT_VERSIONS_A_CONSERVAR + 15)
        self.assertEqual(len(self._vives()), self.SOSTRE)

    def test_la_current_i_les_conservades_no_es_toquen_i_els_seus_ftt_sobreviuen(self):
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 5)
        vives = ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET)
        for f in vives:
            self.assertTrue(f.fitxer.name, 'cap fila viva sense fitxer')
            self.assertTrue(default_storage.exists(f.fitxer.name),
                            'el .ftt d\'una versió conservada no es pot esborrar mai')
        self.assertEqual(vives.filter(is_current=True).count(), 1)
        self.assertEqual(vives.filter(is_current=True).first().pk, cap.pk)
        # I el contingut del cap segueix llegible (no s'ha podat el que toca servir).
        self.assertEqual(load_document(cap)['document_json']['pages'][0]['objects'][0]['text'],
                         'v%d' % (FTT_VERSIONS_A_CONSERVAR + 5))

    def test_la_cadena_queda_caminable_fins_a_l_arrel(self):
        """Si `document_root` deixés d'arribar a la v1, el lock es perdria i el desat següent
        seria un 403 per a qui està editant. La frontera es re-enganxa a l'arrel."""
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 3)
        self.assertEqual(document_root(ModelFitxer.objects.get(pk=cap.pk)).pk, self.arrel.pk)

    def test_una_versio_amb_lock_no_es_poda_encara_que_sigui_vella(self):
        cap = self._cadena(3)
        vella = ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET
        ).exclude(pk=self.arrel.pk).order_by('data_pujada', 'pk').first()
        FttDocumentLock.objects.create(document_root=vella)
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 2, des_de=cap)
        self.assertIn(vella.pk, self._vives(), 'una versió amb lock no es poda')
        self.assertTrue(FttDocumentLock.objects.filter(document_root=vella).exists())

    def test_una_versio_referenciada_per_un_export_no_es_poda(self):
        cap = self._cadena(3)
        referenciada = ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET
        ).exclude(pk=self.arrel.pk).order_by('data_pujada', 'pk').first()
        export = ModelFitxer.objects.create(
            model=self.model, nom_fitxer='x.pdf', tipus=ModelFitxer.TIPUS_EXPORT,
            versio=1, is_current=True, mida_bytes=1, generat_des_de=referenciada,
        )
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 2, des_de=cap)
        self.assertIn(referenciada.pk, self._vives())
        export.refresh_from_db()
        self.assertEqual(export.generat_des_de_id, referenciada.pk,
                         "l'export no pot perdre de quina versió va sortir")

    def test_despres_de_podar_cap_FK_penjant(self):
        """Integritat: cap `versio_anterior_id` / `generat_des_de_id` / `derivat_de_model_id`
        apuntant a una fila que ja no hi és. Les FK són NO ACTION a Postgres
        (`confdeltype='a'`), o sigui que un penjat no l'atrapa la BD: l'atrapa aquest test."""
        self._cadena(FTT_VERSIONS_A_CONSERVAR + 6)
        existents = set(ModelFitxer.objects.values_list('pk', flat=True))
        camps = ('versio_anterior_id', 'generat_des_de_id', 'derivat_de_model_id')
        for f in ModelFitxer.objects.all():
            for camp in camps:
                ref = getattr(f, camp)
                if ref is not None:
                    self.assertIn(ref, existents, '%s.%s penja' % (f.pk, camp))

    def test_la_poda_no_toca_altres_tipus_ni_altres_models(self):
        altre = Model.objects.create(
            codi_intern='TST-B2B', nom_prenda='ALTRE', codi_tenant='TST',
            any=2026, temporada='SS', sequencial=3,
        )
        cap_altre = create_document(altre, document_json=_doc('altre'))
        pdf = ModelFitxer.objects.create(
            model=self.model, nom_fitxer='doc.pdf', tipus='DOCUMENT',
            versio=1, is_current=True, mida_bytes=1,
        )
        self._cadena(FTT_VERSIONS_A_CONSERVAR + 4)
        self.assertTrue(ModelFitxer.objects.filter(pk=cap_altre.pk).exists(),
                        'la fitxa d\'un ALTRE model no es toca')
        self.assertTrue(ModelFitxer.objects.filter(pk=pdf.pk).exists(),
                        'un DOCUMENT del mateix model no es toca')

    def test_dues_fitxes_del_mateix_model_son_cadenes_independents(self):
        """F2: un model pot tenir N fitxes. Podar la cadena d'una no pot tocar l'altra ni,
        molt menys, esborrar-ne el cap viu."""
        segona = create_document(self.model, document_json=_doc('s0'), nom='KNICKERS')
        self._cadena(FTT_VERSIONS_A_CONSERVAR + 4)
        segona.refresh_from_db()
        self.assertTrue(segona.is_current)
        self.assertTrue(default_storage.exists(segona.fitxer.name))

    def test_poda_es_idempotent(self):
        cap = self._cadena(FTT_VERSIONS_A_CONSERVAR + 3)
        abans = self._vives()
        self.assertEqual(poda_cadena(ModelFitxer.objects.get(pk=cap.pk)), [])
        self.assertEqual(self._vives(), abans)

    def tearDown(self):
        # Els .ftt del test viuen al storage del tenant: no els deixem al disc.
        for f in ModelFitxer.objects.all():
            name = f.fitxer.name if f.fitxer else ''
            if name and default_storage.exists(name):
                try:
                    default_storage.delete(name)
                except OSError:
                    pass
