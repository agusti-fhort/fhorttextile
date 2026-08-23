"""SOBIRANIA DEL POM · TRAM 1 — EL RESOLUTOR ÚNIC DE NOMENCLATURA.

🚨 LA LLEI (Agus, 22/08): **ÀLIES DEL CLIENT > TENANT > GLOBAL**, per al codi i per al nom.

La nomenclatura PENJA DEL CLIENT. El defecte que la va fer escriure eren DUES implementacions
de la mateixa veritat dient coses contràries sobre la MATEIXA fila:

    POMMaster.pom_code                 → `codi_client or global.codi`   → TENANT guanya
    POMMasterSerializer.get_pom_code   → `global.codi or codi_client`   → GLOBAL guanya

i el mateix model contradint-se sol (`pom_code` tenant, `name_en`/`name_cat` global), que és
el que imprimia «LOSPOM-548 · FRONT ARMHOLE» a la fitxa d'un client que en diu una altra cosa.

Aquests tests són PURS (`SimpleTestCase`, cap BD): el resolutor no consulta res, només llegeix
els atributs que li donen. Amb objectes de mentida es pot dir la llei sencera sense muntar un
tenant, i el dia que algú torni a invertir la precedència, canten aquí i no a una captura.
"""
from django.test import SimpleTestCase

from fhort.pom.nomenclatura import (abreviatura_de, categoria_de, codi_de, noms_de)


class _Global:
    def __init__(self, codi='LOSPOM-548', nom_en='FRONT ARMHOLE', nom_ca='SISA DAVANTERA',
                 abbreviation='FR AH', categoria='Upper body'):
        self.codi = codi
        self.nom_en = nom_en
        self.nom_ca = nom_ca
        self.abbreviation = abbreviation
        self.categoria = categoria


class _Categoria:
    def __init__(self, nom_ca='Tors', nom_en='Upper body'):
        self.nom_ca = nom_ca
        self.nom_en = nom_en


class _Pom:
    """Un POMMaster de mentida: el resolutor només mira aquests atributs."""

    def __init__(self, codi_client='SD', nom_client='Sisa davantera',
                 pom_global=None, categoria=None):
        self.codi_client = codi_client
        self.nom_client = nom_client
        self.pom_global = pom_global
        self.pom_global_id = 1 if pom_global is not None else None
        self.categoria = categoria
        self.categoria_id = 1 if categoria is not None else None


ALIES = {'client_code': 'A', 'client_name_en': 'Front armhole (Brownie)',
         'client_name_local': 'Sisa A'}


class PrecedenciaDelCodiTest(SimpleTestCase):

    def test_amb_alies_de_client_mana_l_alies(self):
        pom = _Pom(pom_global=_Global())
        self.assertEqual(codi_de(pom, ALIES), 'A')
        self.assertEqual(abreviatura_de(pom, ALIES), 'A')

    def test_sense_alies_mana_el_tenant_encara_que_hi_hagi_global(self):
        """🚨 EL DEFECTE D'AGUS. Aquí sortia `LOSPOM-548` i havia de sortir `SD`."""
        pom = _Pom(pom_global=_Global())
        self.assertEqual(codi_de(pom), 'SD')
        self.assertEqual(abreviatura_de(pom), 'SD')

    def test_el_global_nomes_si_no_hi_ha_res_mes(self):
        pom = _Pom(codi_client='', pom_global=_Global())
        self.assertEqual(codi_de(pom), 'LOSPOM-548')
        self.assertEqual(abreviatura_de(pom), 'FR AH')

    def test_sense_res_la_columna_no_s_inventa_un_codi(self):
        self.assertEqual(codi_de(_Pom(codi_client='')), '')
        self.assertEqual(codi_de(None), '')

    def test_l_alies_pot_arribar_com_a_cadena_crua(self):
        """`base_measurements_view` aplana l'àlies a `client_code`; el resolutor ho accepta."""
        self.assertEqual(codi_de(_Pom(pom_global=_Global()), 'A'), 'A')

    def test_espais_no_fan_de_codi(self):
        self.assertEqual(codi_de(_Pom(codi_client='  '), None), '')
        self.assertEqual(codi_de(_Pom(codi_client='  ', pom_global=_Global())), 'LOSPOM-548')


class PrecedenciaDelNomTest(SimpleTestCase):

    def test_amb_alies_manen_les_descripcions_del_client(self):
        n = noms_de(_Pom(pom_global=_Global()), ALIES)
        self.assertEqual(n['nom_en'], 'Front armhole (Brownie)')
        self.assertEqual(n['nom_ca'], 'Sisa A')

    def test_sense_alies_mana_el_nom_del_tenant(self):
        """🚨 Aquí sortia `FRONT ARMHOLE` (global) sobre el nom de la casa."""
        n = noms_de(_Pom(pom_global=_Global()))
        self.assertEqual(n['nom_en'], 'Sisa davantera')
        self.assertEqual(n['nom_ca'], 'Sisa davantera')

    def test_el_global_nomes_si_el_tenant_no_te_nom(self):
        n = noms_de(_Pom(nom_client='', pom_global=_Global()))
        self.assertEqual(n['nom_en'], 'FRONT ARMHOLE')
        self.assertEqual(n['nom_ca'], 'SISA DAVANTERA')

    def test_pom_tenant_only_no_surt_mut(self):
        """Els 144 POMs de `fhort` no tenen `pom_global`: el nom ha de sortir igualment."""
        n = noms_de(_Pom())
        self.assertEqual((n['nom_en'], n['nom_ca']), ('Sisa davantera', 'Sisa davantera'))

    def test_l_alies_incomplet_no_esborra_el_nom(self):
        """Un àlies amb codi però sense descripcions cau al tenant, no a la cadena buida."""
        n = noms_de(_Pom(pom_global=_Global()), {'client_code': 'A'})
        self.assertEqual(n['nom_en'], 'Sisa davantera')


class CategoriaTest(SimpleTestCase):

    def test_la_familia_de_la_casa_mana_sobre_el_text_del_global(self):
        pom = _Pom(pom_global=_Global(), categoria=_Categoria())
        self.assertEqual(categoria_de(pom), 'Tors')

    def test_sense_familia_propia_cau_al_vocabulari_global(self):
        self.assertEqual(categoria_de(_Pom(pom_global=_Global())), 'Upper body')

    def test_sense_cap_de_les_dues(self):
        self.assertEqual(categoria_de(_Pom()), '')


class LesDuesPortesDiuenElMateixTest(SimpleTestCase):
    """La contradicció original, dita com a test: model i serializer NO poden divergir.

    No s'instancien ni `POMMaster` ni el serializer (això demanaria BD): es comprova que les
    DUES portes criden el MATEIX resolutor, que és el que fa impossible la divergència.
    """

    def test_la_propietat_del_model_delega_al_resolutor(self):
        import inspect
        from fhort.pom.models import POMMaster
        for prop, fn in (('pom_code', 'codi_de'), ('name_en', 'noms_de'), ('name_cat', 'noms_de')):
            font = inspect.getsource(getattr(POMMaster, prop).fget)
            self.assertIn(fn, font, f'POMMaster.{prop} ha deixat de passar pel resolutor')

    def test_el_serializer_delega_al_resolutor(self):
        import inspect
        from fhort.pom.serializers import POMMasterSerializer
        for metode, fn in (('get_pom_code', 'codi_de'), ('get_name_en', 'noms_de'),
                           ('get_name_cat', 'noms_de'), ('get_abbreviation', 'abreviatura_de'),
                           ('get_categoria_nom', 'categoria_de')):
            font = inspect.getsource(getattr(POMMasterSerializer, metode))
            self.assertIn(fn, font, f'POMMasterSerializer.{metode} ha deixat de passar pel resolutor')
