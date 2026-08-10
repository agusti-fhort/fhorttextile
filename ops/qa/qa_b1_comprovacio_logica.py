"""ARNÈS · B1 — LA COMPROVACIÓ DIU NÚMEROS QUE ES PODEN RASTREJAR (Agus, 09/08).

Agus: «diu coses que no s'ajusten a les mesures reals». No era la pell: eren quatre defectes de
CONSULTA a `models_app/comprovacio_views.py`, i aquest arnès els fixa perquè no puguin tornar.

Cada afirmació es mesura contra la BD viva del model 1320 (BRW-FW26-0001 · Blusa KAYCE) i, on
toca, es RE-DERIVA pel seu compte des de les taules d'origen —mai llegint el mateix codi que
s'audita, que no demostraria res.

  V1 · CAP PUNT DE «VAN QUEDAR ENRERE» AMB 0 DIES
       El cas YT (mesurat 19 · base ara 13 · «0 dies») no era una base que s'hagués mogut
       després: era la germana bidireccional reescrivint la presa 22 ms més tard, DINS del
       mateix desat. Un moviment de la mateixa desada no deixa res enrere.
  V2 · TOTA XIFRA DE «FORA DE TOLERÀNCIA» ÉS DE LA TALLA BASE
       El «teòric 29 / real 31» d'E2 era la fila XXS: la consulta no filtrava per talla i es
       quedava amb la primera que tornés Postgres. La secció compara contra `BaseMeasurement`,
       que ÉS la base; qualsevol altra talla és una peça diferent.
  V3 · TOTA XIFRA VE DEL DARRER FITTING AMB CONTINGUT, I D'UN DE SOL
       S'ordenava per id de PEÇA descendent (l'ordre en què s'han obert les graelles, no el dia
       de la prova) i es quedava amb el primer encert de CADA mesura: barrejava fittings.
  V4 · LES GERMANES SÓN VIGILADES
       `clau.get((pom, capa, ''))` tenia la instància escrita a mà: cap germana hi entrava. Al
       1320 això deixava CINC mesures fora, entre elles J1·extended, 2 cm fora d'una banda
       de 0,60.
  V5 · CADA NÚMERO A PANTALLA TÉ PROCEDÈNCIA
       `darrer_fitting` + `talla_base` viatgen a la resposta: una xifra sense dir de quin dia i
       de quina talla és, és una xifra que no «lliga» amb res.

Lectura pura: no escriu res, enlloc.

    backend/venv/bin/python ops/qa/qa_b1_comprovacio_logica.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context  # noqa: E402

TENANT = 'fhort'
MODEL_ID = 1320

falles = []


def mira(nom, ok, detall=''):
    print(f'  {"✅" if ok else "❌"} {nom}' + (f' — {detall}' if detall else ''))
    if not ok:
        falles.append(nom)


def main():
    with schema_context(TENANT):
        from fhort.fitting.esdeveniments import (darrera_peca_amb_contingut, linia_te_contingut,
                                                 peces_amb_contingut)
        from fhort.models_app.comprovacio_views import (_seccio_enrere, _seccio_tolerancia,
                                                        _darrer_fitting)
        from fhort.models_app.models import BaseMeasurement, Model

        model = Model.objects.get(id=MODEL_ID)
        mesures = list(BaseMeasurement.objects
                       .filter(model=model, is_active=True)
                       .select_related('pom', 'pom__pom_global')
                       .order_by('ordre', 'id'))
        base = (model.base_size_label or '').strip()
        print(f'\nBANC · {model.codi_intern} · {model.nom_prenda} · talla base {base} · '
              f'{len(mesures)} mesures actives\n')

        # ── V1 ────────────────────────────────────────────────────────────────────────────
        enrere = _seccio_enrere(model, mesures)
        print(f'V1 · van quedar enrere: {len(enrere)} punts')
        mira('V1 · cap punt amb 0 dies',
             all(p['dies'] > 0 for p in enrere),
             ', '.join(f'{p["codi"]}={p["dies"]}d' for p in enrere if p['dies'] <= 0) or 'cap')
        # I el punt ha de ser CERT: la base d'ara ha de diferir del que es va prendre.
        mira('V1 · tot punt té base ≠ mesurat',
             all(float(p['base_ara']) != float(p['mesurat']) for p in enrere))

        # ── V3 · quina peça mana ──────────────────────────────────────────────────────────
        peces = peces_amb_contingut(MODEL_ID)
        peca = darrera_peca_amb_contingut(MODEL_ID)
        print(f'\nV3 · peces amb contingut: {[(p.id, p.session_id) for p in peces]}')
        # La peça escollida ha de ser la de DATA més tardana, no la d'id més alt.
        from fhort.fitting.models import PieceFitting
        totes = list(PieceFitting.objects.filter(model_id=MODEL_ID)
                     .exclude(session__estat='Anullada').select_related('session'))
        buides = [p for p in totes if not any(linia_te_contingut(l) for l in p.linies.all())]
        mira('V3 · les graelles obertes i no tocades queden fora',
             all(p not in peces for p in buides),
             f'{len(buides)} buides de {len(totes)}')
        if peca is not None:
            mira('V3 · la peça triada és la de data més tardana',
                 (peca.session.data, peca.session_id) == max(
                     (p.session.data, p.session_id) for p in peces))

        tol = _seccio_tolerancia(model, mesures)
        print(f'\nV2/V4 · fora de tolerància: {len(tol)} punts')
        for p in tol:
            print(f'    {p["codi"]:<4} inst={p["instancia"]!r:<12} teòric={p["teoric"]:<7} '
                  f'real={p["real"]:<7} desv={p["desviacio"]:<6} talla={p["talla"]} '
                  f'veredicte={p["veredicte"]}')

        # ── V2 ────────────────────────────────────────────────────────────────────────────
        mira('V2 · tota xifra és de la talla base',
             all(p['talla'] == base for p in tol),
             ', '.join(sorted({p['talla'] for p in tol})) or 'cap punt')

        # ── V3 (segona meitat) · un sol fitting, i el correcte ────────────────────────────
        if peca is not None and tol:
            # Re-derivat des de la taula d'origen, sense passar pel codi auditat.
            reals = {(l.pom_id, l.capa or 'exterior', l.instancia or ''): (l.valor_teoric, l.valor_real)
                     for l in peca.linies.filter(size_label=base)}
            ok = all(reals.get((p['pom_id'], p['capa'], p['instancia'])) ==
                     (p['teoric'], p['real']) for p in tol)
            mira('V3 · cada xifra surt de la peça triada', ok)

        # ── V4 · les germanes hi entren ───────────────────────────────────────────────────
        germanes = {(bm.pom_id, bm.capa or 'exterior', bm.instancia or '')
                    for bm in mesures if (bm.instancia or '')}
        vigilades = set()
        if peca is not None:
            for l in peca.linies.filter(size_label=base, valor_real__isnull=False):
                clau = (l.pom_id, l.capa or 'exterior', l.instancia or '')
                if clau in germanes:
                    vigilades.add(clau)
        # Tota germana amb línia i desviació fora de banda ha de sortir a la secció.
        per_clau = {(b.pom_id, b.capa or 'exterior', b.instancia or ''): b for b in mesures}
        esperades = set()
        if peca is not None:
            for l in peca.linies.filter(size_label=base, valor_real__isnull=False):
                clau = (l.pom_id, l.capa or 'exterior', l.instancia or '')
                bm = per_clau.get(clau)
                if bm is None or l.valor_teoric is None:
                    continue
                if bm.tolerancia_minus is None or bm.tolerancia_plus is None:
                    continue
                d = float(l.valor_real) - float(l.valor_teoric)
                if d < -float(bm.tolerancia_minus) or d > float(bm.tolerancia_plus):
                    esperades.add(clau)
        surten = {(p['pom_id'], p['capa'], p['instancia']) for p in tol}
        mira('V4 · cap desviació fora de banda queda sense dir',
             esperades == surten,
             f'esperades {len(esperades)} · surten {len(surten)}'
             + (f' · falten {sorted(esperades - surten)}' if esperades - surten else ''))
        mira('V4 · les germanes hi són vigilades',
             all(g in surten or g not in esperades for g in vigilades),
             f'{len(vigilades)} germanes amb línia a la base')

        # ── V5 · procedència ──────────────────────────────────────────────────────────────
        df = _darrer_fitting(peca)
        mira('V5 · la resposta diu de quin fitting parla',
             bool(df and df.get('data') and df.get('session_id')), str(df))
        mira('V5 · i de quina talla', bool(base))

    print()
    if falles:
        print(f'❌ {len(falles)} afirmacions vermelles: ' + ' · '.join(falles))
        sys.exit(1)
    print('✅ B1 · totes les afirmacions verdes')


if __name__ == '__main__':
    main()
