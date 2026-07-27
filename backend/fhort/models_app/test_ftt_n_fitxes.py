"""F2 — N fitxes .ftt per model, amb nom propi.

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

Fins ara un model tenia UNA fitxa: `create_document` derivava el nom del model
(`<codi_intern>_fitxa.ftt`) i el resolutor de `/models/<id>/fitxa` obria la primera que
trobava. Per a un model multi-peça això no serveix: les tres peces volen tres fitxes amb
nom (DRESS / KNICKERS / HEADBAND), no tres fitxers homònims que ningú pot distingir.

El que defensen aquests tests:

  1. El nom escrit per una persona es converteix en nom de fitxa .ftt (extensió posada pel
     servei, mai per qui crida) i és el que es veu a la llista.
  2. Sense nom, el camí de sempre no canvia gens — la fitxa única segueix naixent igual.
  3. **`save_document` PRESERVA el nom al llarg de la cadena de versions.** Aquesta és la
     que de debò importa: si el desat el tornés a derivar del model, N fitxes col·lapsarien
     a un sol nom al primer autosave i el treball de F2 s'esborraria sol. El brief demanava
     verificar-ho amb un test i no tocar el codi; això és la verificació.
  4. Un model pot tenir N fitxes .ftt vives alhora (cadascuna amb la seva cadena i el seu
     is_current), que és la condició que fa possible el selector del resolutor.
"""
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import Model, ModelFitxer
from fhort.models_app.services_ftt_document import (
    _nom_de_fitxa, create_document, load_document, save_document,
)


class NomDeFitxaTest(SimpleTestCase):
    """La normalització del nom intern. Pura: sense BD ni fitxers."""

    def test_hi_posa_l_extensio(self):
        self.assertEqual(_nom_de_fitxa('DRESS'), 'DRESS.ftt')

    def test_no_la_duplica_i_no_hi_mira_les_majuscules(self):
        self.assertEqual(_nom_de_fitxa('DRESS.ftt'), 'DRESS.ftt')
        self.assertEqual(_nom_de_fitxa('DRESS.FTT'), 'DRESS.FTT')

    def test_buit_i_espais_son_absencia_de_nom(self):
        """None → el caller cau al nom derivat del model; no un fitxer dit '.ftt'."""
        for cru in (None, '', '   ', '.', ' . '):
            self.assertIsNone(_nom_de_fitxa(cru), cru)

    def test_cap_separador_de_ruta(self):
        """El nom viatja a ContentFile i acaba al FileField: una barra hi obriria un
        subdirectori (o pitjor, en sortiria)."""
        self.assertEqual(_nom_de_fitxa('01/DRESS'), '01-DRESS.ftt')
        # Els punts del davant també cauen: '../x' no ha de poder sortir del directori.
        self.assertEqual(_nom_de_fitxa('../secret'), '-secret.ftt')
        for cru in ('01/DRESS', '../secret', 'a\\b'):
            sortida = _nom_de_fitxa(cru)
            self.assertNotIn('/', sortida)
            self.assertNotIn('\\', sortida)
            self.assertFalse(sortida.startswith('.'))

    def test_es_retalla(self):
        self.assertTrue(len(_nom_de_fitxa('X' * 400)) <= 204)


class NFitxesPerModelTest(TenantTestCase):
    """La cadena sencera contra BD i emmagatzematge reals."""

    PREFIX = 'FTTN'

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'

    def setUp(self):
        self.model = Model.objects.create(
            codi_intern='TST-0001', nom_prenda='DALIA', codi_tenant='TST',
            any=2026, temporada='SS', sequencial=1,
        )

    def test_sense_nom_el_cami_de_sempre_no_canvia(self):
        f = create_document(self.model)
        self.assertEqual(f.nom_fitxer, 'TST-0001_fitxa.ftt')
        self.assertEqual(f.tipus, ModelFitxer.TIPUS_TECHSHEET)
        self.assertEqual(f.versio, 1)
        self.assertTrue(f.is_current)

    def test_el_nom_i_la_descripcio_arriben_a_la_fitxa(self):
        f = create_document(self.model, nom='KNICKERS', descripcio='peça 2 de 3')
        self.assertEqual(f.nom_fitxer, 'KNICKERS.ftt')
        self.assertEqual(f.descripcio, 'peça 2 de 3')

    def test_el_desat_PRESERVA_el_nom_al_llarg_de_la_cadena(self):
        """La que sosté F2: si el desat tornés a derivar el nom del model, N fitxes
        col·lapsarien a un sol nom al primer autosave."""
        f1 = create_document(self.model, nom='HEADBAND')
        doc = load_document(f1)['document_json']
        doc['metadata'] = {'tocat': True}

        f2 = save_document(f1, doc)
        self.assertEqual(f2.nom_fitxer, 'HEADBAND.ftt')
        self.assertEqual(f2.versio, 2)

        f3 = save_document(f2, doc)
        self.assertEqual(f3.nom_fitxer, 'HEADBAND.ftt')
        self.assertEqual(f3.versio, 3)

        # La invariant de cadena segueix intacta: un sol cap viu.
        vius = ModelFitxer.objects.filter(model=self.model, is_current=True)
        self.assertEqual([v.id for v in vius], [f3.id])

    def test_N_fitxes_vives_alhora_amb_cadenes_independents(self):
        """La condició que fa possible el selector del resolutor: tres fitxes del MATEIX
        model, totes is_current, cadascuna amb el seu nom."""
        noms = ['01.- DRESS', '02.- KNICKERS', '03.- HEADBAND']
        fitxes = [create_document(self.model, nom=n) for n in noms]

        # Desar-ne una no toca les altres.
        doc = load_document(fitxes[1])['document_json']
        save_document(fitxes[1], doc)

        vius = ModelFitxer.objects.filter(
            model=self.model, tipus=ModelFitxer.TIPUS_TECHSHEET, is_current=True,
        )
        self.assertEqual(
            sorted(v.nom_fitxer for v in vius),
            ['01.- DRESS.ftt', '02.- KNICKERS.ftt', '03.- HEADBAND.ftt'],
        )
        self.assertEqual(vius.count(), 3)
