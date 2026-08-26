"""LA TAXONOMIA DE FAMÍLIES D'INSTÀNCIA (llei d'Agus, 26/08) — el banc de la llei.

  1 PEÇA {front,back} · 2 BANDA {left,right} · 3 VERTICALITAT {top,bottom} ·
  4 COSTURA {side,waistband_seam} (SENSE mirall) · 5 LÍNIA {cf,cb} · Ú ESTAT {relaxed,extended}

La meitat de dalt és PURA (`SimpleTestCase`): la llei viu a `fhort/pom/families.py`, que no
importa res de Django a posta —una migració de dades l'ha de poder cridar—, i per tant es pot
dir sencera sense muntar cap tenant. La de baix toca la BD perquè `error_de_combinacio` només
jutja el vocabulari que el diccionari declara.
"""
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase

from fhort.pom import families as fam

TOTS = [s for _c, slugs, _m in fam.FAMILIES for s in slugs]


class LlistaDeFamiliesTest(SimpleTestCase):

    def test_cap_slug_del_vocabulari_es_orfe(self):
        # 🚨 EL DEFECTE QUE AIXÒ TANCA: sis dels deu slugs de posició no tenien família i per
        # això s'excloïen amb TOT (prémer «Top» apagava «Left»).
        self.assertEqual(len(TOTS), 12)
        for slug in TOTS:
            self.assertTrue(fam.familia_de(slug), f'«{slug}» s\'ha quedat sense família')

    def test_cap_slug_no_es_de_dues_families(self):
        vistos = {}
        for clau, slugs, _m in fam.FAMILIES:
            for s in slugs:
                self.assertNotIn(s, vistos, f'«{s}» és a {vistos.get(s)} i a {clau}')
                vistos[s] = clau

    def test_les_families_son_les_SIS_de_la_llei_i_en_ORDRE(self):
        self.assertEqual([c for c, _s, _m in fam.FAMILIES],
                         ['PECA', 'BANDA', 'VERTICALITAT', 'COSTURA', 'LINIA', 'ESTAT'])

    def test_la_LINIA_es_familia_propia_i_NO_es_la_peca(self):
        # `cf`/`cb` són una LÍNIA de la peça, no la seva cara: per això `front`+`cf` combina.
        self.assertEqual(fam.familia_de('cf'), 'LINIA')
        self.assertNotEqual(fam.familia_de('cf'), fam.familia_de('front'))


class MirallsTest(SimpleTestCase):

    def test_les_binomials_tenen_mirall_i_es_reciproc(self):
        for a, b in [('front', 'back'), ('left', 'right'), ('top', 'bottom'),
                     ('cf', 'cb'), ('relaxed', 'extended')]:
            self.assertEqual(fam.mirall_de(a), b)
            self.assertEqual(fam.mirall_de(b), a)

    def test_la_COSTURA_no_te_mirall(self):
        # «Side seam» i «waistband seam» NO són l'una el revers de l'altra: són dues costures
        # diferents. Declarar-los un mirall convidaria algú a girar-les.
        self.assertEqual(fam.mirall_de('side'), '')
        self.assertEqual(fam.mirall_de('waistband_seam'), '')

    def test_un_slug_desconegut_no_te_mirall(self):
        self.assertEqual(fam.mirall_de('sleeve-2'), '')


class OrdreCanonicTest(SimpleTestCase):

    def test_l_exemple_canonic_de_la_llei(self):
        self.assertEqual(fam.composa(['left', 'back']), 'back-left')
        self.assertEqual(fam.composa(['back', 'left']), 'back-left')

    def test_l_ESTAT_va_SEMPRE_l_ultim(self):
        # 🚨 EL CAS QUE LA BD PORTAVA MAL ESCRIT. L'ordre entre eixos el decidia
        # `order_by('eix')` —ALFABÈTIC, `'ESTAT' < 'POSICIO'`— i el sistema componia
        # `extended-right`. A `fhort` n'hi ha dues files (pk 3389/3390).
        self.assertEqual(fam.composa(['extended', 'right']), 'right-extended')
        self.assertEqual(fam.composa(['relaxed', 'right']), 'right-relaxed')
        self.assertEqual(fam.composa(['relaxed', 'top']), 'top-relaxed')

    def test_les_SIS_families_alhora_i_en_qualsevol_permutacio(self):
        esperat = 'back-left-top-side-cf-relaxed'
        for entrada in (['relaxed', 'left', 'back', 'top', 'side', 'cf'],
                        ['cf', 'side', 'top', 'back', 'left', 'relaxed'],
                        ['back', 'left', 'top', 'side', 'cf', 'relaxed']):
            self.assertEqual(fam.composa(entrada), esperat, entrada)

    def test_sense_duplicats_i_idempotent(self):
        self.assertEqual(fam.composa(['left', 'left']), 'left')
        for v in ['front-left', 'extended-right', 'back-left-top-side-cf-relaxed', '', 'left']:
            self.assertEqual(fam.normalitza(fam.normalitza(v)), fam.normalitza(v))

    def test_el_desconegut_va_al_final_i_no_es_reordena_entre_ell(self):
        # No es pot inventar on cau un slug del qual no se sap la família; moure'l seria
        # canviar-li la clau a algú.
        self.assertEqual(fam.composa(['zz', 'left']), 'left-zz')
        self.assertEqual(fam.composa(['zz', 'aa', 'left']), 'left-zz-aa')

    def test_un_slug_simple_no_canvia(self):
        for v in ['left', 'waistband_seam', '', 'zz']:
            self.assertEqual(fam.normalitza(v), v)


class ExclusioTest(TenantTestCase):
    """`error_de_combinacio` només jutja el vocabulari que el diccionari DECLARA: cal BD.

    🚨 I PER TANT CAL SEMBRAR-LA. Sense la sembra, la taula del tenant de test és buida, cap
    tram és «conegut» i `error_de_combinacio` torna `''` per a TOT: el test passaria en verd
    dient que `left`+`right` és legal. És el mateix mode de fallada que un fixture que menteix
    — el que aquesta coda existeix per tancar — i per això la sembra és part del banc i no un
    detall del `setUp`.
    """

    def setUp(self):
        from fhort.pom.models import MeasurementInstance as MI
        for clau, slugs, _m in fam.FAMILIES:
            eix = MI.EIX_ESTAT if clau == 'ESTAT' else MI.EIX_POSICIO
            for i, slug in enumerate(slugs):
                MI.objects.update_or_create(
                    slug=slug,
                    defaults={'nom_en': slug.title(), 'nom_ca': slug.title(),
                              'nom_es': slug.title(), 'eix': eix, 'display_order': i,
                              'is_system': True})
        self.assertEqual(MI.objects.count(), 12)

    def test_dins_de_CADA_familia_els_dos_slugs_s_exclouen(self):
        from fhort.pom.models import MeasurementInstance as MI
        for clau, slugs, _m in fam.FAMILIES:
            a, b = slugs
            err = MI.error_de_combinacio(f'{a}-{b}')
            self.assertTrue(err, f'{clau}: «{a}»+«{b}» hauria de ser il·legal')
            self.assertIn(clau, err)

    def test_ENTRE_families_tot_combina(self):
        from fhort.pom.models import MeasurementInstance as MI
        # Un representant de cada família, creuat amb tots els altres.
        caps = ['front', 'left', 'top', 'side', 'cf', 'relaxed']
        for i, a in enumerate(caps):
            for b in caps[i + 1:]:
                self.assertEqual(MI.error_de_combinacio(f'{a}-{b}'), '',
                                 f'«{a}»+«{b}» haurien de conviure')

    def test_els_QUATRE_que_abans_xocaven_i_ara_no(self):
        # El símptoma de la formació, dit en assercions.
        from fhort.pom.models import MeasurementInstance as MI
        for combo in ['top-left', 'cf-back', 'side-top', 'waistband_seam-left']:
            self.assertEqual(MI.error_de_combinacio(combo), '', combo)

    def test_la_redundancia_es_LEGAL(self):
        # `front`+`cf` diu dues vegades que és del davant: criteri de qui mesura, no error.
        from fhort.pom.models import MeasurementInstance as MI
        self.assertEqual(MI.error_de_combinacio('front-cf'), '')

    def test_les_sis_families_alhora_son_legals(self):
        from fhort.pom.models import MeasurementInstance as MI
        self.assertEqual(MI.error_de_combinacio('back-left-top-side-cf-relaxed'), '')

    def test_el_vocabulari_desconegut_no_es_jutja(self):
        from fhort.pom.models import MeasurementInstance as MI
        self.assertEqual(MI.error_de_combinacio('sleeve2-left'), '')

    def test_la_publicacio_porta_la_familia_de_CADA_slug(self):
        # El front no se la reescriu: la llegeix d'aquí (`subeix` per fila). El recompte hi va
        # perquè un bucle sobre una taula buida passa en verd sense mirar res.
        from fhort.pom.models import MeasurementInstance as MI
        files = list(MI.objects.all())
        self.assertEqual(len(files), 12)
        for r in files:
            self.assertTrue(MI.subeix_de(r.slug), f'«{r.slug}» surt publicat sense família')
