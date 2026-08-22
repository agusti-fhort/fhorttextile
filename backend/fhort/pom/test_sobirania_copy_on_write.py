"""SOBIRANIA DEL POM · TRAM 3 — EL COPY-ON-WRITE i el «com es mesura» del tenant.

🚨 LA DECISIÓ D'AGUS (22/08): **en editar qualsevol camp propi d'un POM lligat al global, el
POM ES SEPARA i passa a ser meu.** Mateixa llei que el model que reescriu una regla sembrada:
qui toca una dada n'assumeix la propietat, i el catàleg global —que el comparteixen tots els
tenants— no es toca mai.

🔑 I ÉS COPY-ON-WRITE, NO UN TALL. Separar-se no pot voler dir perdre informació: el que el POM
ENSENYAVA gràcies al global es copia al tenant abans de desfer el lligam. La promesa, dita com
a mesura, és `test_el_POM_diu_el_MATEIX_abans_i_despres_de_separar_se`.

L'altra meitat del tram és que els nou camps del «com es mesura» ara VIUEN al tenant: fins avui
només eren a `POMGlobal`, i per això «complementar la informació d'un POM propi» era literalment
impossible — no hi havia on escriure-la.
"""
from django.test import SimpleTestCase

from fhort.pom.nomenclatura import (CAMPS_QUE_SEPAREN, com_es_mesura_de, noms_de,
                                    separa_del_global)


class _Global:
    codi = 'LOSPOM-548'
    nom_en = 'FRONT ARMHOLE'
    nom_ca = 'SISA DAVANTERA'
    abbreviation = 'FR AH'
    unitat = 'cm'
    start_point = 'Shoulder point'
    end_point = 'Underarm point'
    reference_point = 'Along the armhole seam'
    scope = 'FULL'
    orientation = 'CURVED'
    state = 'FLAT'
    line = 'ALONG CURVE'
    body_section = 'FRONT'


class _Pom:
    def __init__(self, **kw):
        self.codi_client = kw.pop('codi_client', '')
        self.nom_client = kw.pop('nom_client', '')
        self.pom_global = kw.pop('pom_global', None)
        self.pom_global_id = 1 if self.pom_global is not None else None
        self.separat_de_global = ''
        self.separat_at = None
        for c in ('unitat', 'start_point', 'end_point', 'reference_point', 'scope',
                  'orientation', 'state', 'line', 'body_section'):
            setattr(self, c, kw.pop(c, ''))
        assert not kw, kw


class ComEsMesuraTest(SimpleTestCase):
    """La cascada del «com es mesura»: el tenant al davant, el global de reserva."""

    def test_lligat_i_sense_informar_diu_el_global(self):
        c = com_es_mesura_de(_Pom(pom_global=_Global()))
        self.assertEqual(c['start_point'], 'Shoulder point')
        self.assertEqual(c['scope'], 'FULL')

    def test_el_que_el_tenant_informa_mana(self):
        c = com_es_mesura_de(_Pom(pom_global=_Global(), start_point="De l'espatlla"))
        self.assertEqual(c['start_point'], "De l'espatlla")
        self.assertEqual(c['end_point'], 'Underarm point')   # el que no ha tocat, del global

    def test_pom_tenant_only_ja_pot_dir_com_es_mesura(self):
        """El forat que tancava el tram 3: abans això era literalment impossible."""
        c = com_es_mesura_de(_Pom(start_point='HPS', unitat='cm'))
        self.assertEqual(c['start_point'], 'HPS')
        self.assertEqual(c['end_point'], '')   # buit honest, no una dada inventada


class CopyOnWriteTest(SimpleTestCase):

    def test_separar_se_no_es_perdre_informacio(self):
        pom = _Pom(codi_client='', nom_client='', pom_global=_Global())
        separa_del_global(pom)
        self.assertIsNone(pom.pom_global)
        self.assertEqual(pom.separat_de_global, 'LOSPOM-548')
        self.assertIsNotNone(pom.separat_at)
        # tot el que ENSENYAVA gràcies al global, ara és seu
        self.assertEqual(pom.nom_client, 'FRONT ARMHOLE')
        self.assertEqual(pom.codi_client, 'FR AH')
        self.assertEqual(pom.start_point, 'Shoulder point')
        self.assertEqual(pom.body_section, 'FRONT')

    def test_el_que_el_tenant_ja_tenia_NO_es_trepitja(self):
        pom = _Pom(codi_client='SD', nom_client='Sisa davantera',
                   pom_global=_Global(), start_point="De l'espatlla")
        separa_del_global(pom)
        self.assertEqual(pom.codi_client, 'SD')
        self.assertEqual(pom.nom_client, 'Sisa davantera')
        self.assertEqual(pom.start_point, "De l'espatlla")
        self.assertEqual(pom.end_point, 'Underarm point')   # aquest sí, el va heretar

    def test_el_POM_diu_el_MATEIX_abans_i_despres_de_separar_se(self):
        """La promesa del copy-on-write, dita com a mesura: la pantalla no ha de canviar.

        🔒 AMB UNA EXCEPCIÓ, I NO ÉS UN FORAT: **el NOM LOCAL.** `POMGlobal` en té dos
        (`nom_en` + `nom_ca`) i `POMMaster` en té UN (`nom_client`), i això és una decisió
        d'Agus del 09/08 que segueix vigent: *la traducció de vocabulari de domini NO viu a la
        base de dades* —`nom_ca`/`nom_es` a `POMMaster` hi estan explícitament descartats—
        perquè el vocabulari tècnic del client no és dada de la casa i duplicar-lo crearia una
        segona font de veritat per mantenir a mà a cada tenant.

        Per tant el canònic es copia i el local NO es perd: **canvia de font.** Passa a
        `TranslationCache` (`/api/v1/translate/pom/`, tram ⓘ del 13/08), que és on la casa ha
        decidit que viu. Afegir aquí un camp per «no perdre'l» seria desfer aquella decisió
        de passada, per un efecte lateral d'aquest sprint.
        """
        pom = _Pom(codi_client='', nom_client='', pom_global=_Global())
        abans_com = com_es_mesura_de(pom)
        abans_en = noms_de(pom)['nom_en']
        separa_del_global(pom)
        self.assertEqual(com_es_mesura_de(pom), abans_com)   # els nou camps, intactes
        self.assertEqual(noms_de(pom)['nom_en'], abans_en)   # el canònic, intacte
        self.assertEqual(pom.codi_client, 'FR AH')           # i el codi, heretat
        # el local cau al canònic: la ⓘ el demanarà a la traducció, que és la seva casa
        self.assertEqual(noms_de(pom)['nom_ca'], 'FRONT ARMHOLE')

    def test_un_POM_ja_propi_no_es_toca_ni_es_marca(self):
        pom = _Pom(codi_client='ZZ', nom_client='Propi')
        self.assertEqual(separa_del_global(pom), [])
        self.assertEqual(pom.separat_de_global, '')

    def test_retorna_els_camps_tocats_per_al_update_fields(self):
        tocats = separa_del_global(_Pom(pom_global=_Global()))
        for obligatori in ('pom_global', 'separat_de_global', 'separat_at'):
            self.assertIn(obligatori, tocats)

    def test_administrar_un_POM_no_el_separa(self):
        """`actiu`, `notes` i les toleràncies NO hi són: arxivar no és redefinir."""
        for camp in ('actiu', 'notes', 'pendent_revisio', 'origen_import',
                     'tolerancia_default_minus', 'tolerancia_default_plus'):
            self.assertNotIn(camp, CAMPS_QUE_SEPAREN)
        for camp in ('codi_client', 'nom_client', 'categoria', 'unitat', 'start_point'):
            self.assertIn(camp, CAMPS_QUE_SEPAREN)
