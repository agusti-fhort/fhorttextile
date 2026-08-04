"""
fhort/pom/s10_views.py — Sprint S10 / 5B.5: Fitting vs Spec (PieceFitting)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

CM_TO_INCH = 0.393701

def get_unit(request):
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.get_or_create_default().unitat_mesura
    except Exception:
        return 'CM'

def cv(val, unit):
    if val is None:
        return None
    v = float(val)
    return round(v * CM_TO_INCH, 3) if unit == 'INCH' else round(v, 2)


def _pom_codi(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None):
        return p.pom_global.codi
    return p.codi_client or ''


def _pom_name_en(p):
    if not p:
        return ''
    if getattr(p, 'pom_global_id', None) and p.pom_global.nom_en:
        return p.pom_global.nom_en
    return p.nom_client or ''


TOL_FALLBACK = 0.6


def _tolerance_map(model):
    """Asymmetric tolerance per (pom, capa, instancia), from BaseMeasurement.

    Returns {(pom_id, capa, instancia): (tol_minus, tol_plus)} with TOL_FALLBACK (0.6) when
    a bound is unset. POMs without a BaseMeasurement fall back to (0.6, 0.6) on lookup.

    C2/Onada 1 — the key carries the layer because `PieceFittingLine` does: the lining of
    a chest and its shell are two different measurements of the same POM, and each must be
    judged against its own tolerance. Keyed by pom alone, whichever layer the map met last
    would silently rule the whole family.

    FASE_2/C1-ins — and it carries the INSTANCE for exactly the same reason: the right
    armhole and the left one are two measurements, each with its own tolerance, and the
    consuming line knows which one it is talking about. Whenever the row can name the axis,
    the key carries it — no anchoring here, because there is nothing to anchor to.
    """
    from fhort.models_app.models import BaseMeasurement
    tol = {}
    for bm in BaseMeasurement.objects.filter(model=model, is_active=True):
        tm = float(bm.tolerancia_minus) if bm.tolerancia_minus is not None else TOL_FALLBACK
        tp = float(bm.tolerancia_plus) if bm.tolerancia_plus is not None else TOL_FALLBACK
        tol[(bm.pom_id, bm.capa, bm.instancia)] = (tm, tp)
    return tol


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fitting_vs_spec_view(request, pf_id):
    """
    GET /api/v1/fittings/peca/{pf_id}/vs-spec/
    Compare a PieceFitting's lines: valor_real vs valor_teoric (both on the line).
    Asymmetric tolerance from BaseMeasurement(model, pom). Generates POMAlerts for FAILs.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import PieceFitting, PieceFittingLine

        pf = PieceFitting.objects.select_related(
            'model', 'grading_version', 'grading_version__size_fitting',
        ).get(pk=pf_id)

        model = pf.model
        sf = pf.grading_version.size_fitting if pf.grading_version_id else None

        tol_map = _tolerance_map(model)

        lines = PieceFittingLine.objects.filter(
            piece_fitting=pf
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client', 'size_label')

        resultats = []
        n_pass = n_fail = n_pend = 0

        for line in lines:
            spec_cm = float(line.valor_teoric) if line.valor_teoric is not None else None
            val_cm = float(line.valor_real) if line.valor_real is not None else None
            tol_minus, tol_plus = tol_map.get((line.pom_id, line.capa, line.instancia),
                                              (TOL_FALLBACK, TOL_FALLBACK))

            desv = None
            passa = None
            if val_cm is not None and spec_cm is not None:
                desv = round(val_cm - spec_cm, 2)
                passa = (-tol_minus) <= desv <= tol_plus

            if passa is True:
                n_pass += 1
            elif passa is False:
                n_fail += 1
            else:
                n_pend += 1

            # The exceeded bound (for single-value display / POMAlert.tolerancia_cm).
            tol_rellevant = tol_plus if (desv is not None and desv > 0) else tol_minus

            resultats.append({
                'pom_id': line.pom_id,
                # C4/BLOC 2 — els eixos viatgen amb el resultat: els necessita l'alerta de
                # sota, i el payload d'aquesta vista tampoc no els deia (mateixa espècie que
                # A1/A2/A3 del bloc 1-bis).
                'capa': line.capa,
                'instancia': line.instancia,
                'codi_client': _pom_codi(line.pom),
                'nom_en': _pom_name_en(line.pom),
                'talla': line.size_label,
                'is_key': line.pom.is_key_measure if line.pom_id else False,
                'spec_cm': spec_cm,
                'spec_display': cv(spec_cm, unit),
                'value_cm': val_cm,
                'value_display': cv(val_cm, unit),
                'desviacio_cm': desv,
                'desviacio_display': cv(desv, unit),
                'tolerancia_minus_cm': tol_minus,
                'tolerancia_plus_cm': tol_plus,
                'tolerancia_minus_display': cv(tol_minus, unit),
                'tolerancia_plus_display': cv(tol_plus, unit),
                'tolerancia_cm': tol_rellevant,
                'passa': passa,
                'unitat': unit,
            })

        # Generate POMAlerts for FAILs (origen FITTING).
        try:
            from fhort.fitting.models import POMAlert
            for r in resultats:
                if r['passa'] is False and model:
                    # C4/BLOC 2 — LA CLAU DE L'ALERTA ÉS LA MESURA, NO EL POM. Una alerta
                    # és el veredicte sobre UNA mesura: la sisa dreta pot desviar 2 cm i
                    # l'esquerra estar dins de tolerància. Amb `(model, pom, size_fitting)`
                    # les dues germanes escrivien la MATEIXA fila —l'última guanyava— i el
                    # `missatge`, que porta la talla i la desviació, acabava descrivint una
                    # mesura i titulant-ne una altra. Els eixos surten de la LÍNIA, que els
                    # sap dir; no s'hi posa cap literal.
                    POMAlert.objects.update_or_create(
                        model=model,
                        pom_id=r['pom_id'],
                        capa=r['capa'],
                        instancia=r['instancia'],
                        size_fitting=sf,
                        defaults={
                            'desviacio_cm': r['desviacio_cm'],
                            'tolerancia_cm': r['tolerancia_cm'],
                            'missatge': (f"Fitting peça {pf_id}: {r['codi_client']} "
                                         f"talla {r['talla']} desvia {r['desviacio_cm']:+.2f}cm "
                                         f"(tol -{r['tolerancia_minus_cm']}/+{r['tolerancia_plus_cm']}cm)"),
                            # 'Obert' NO és a `POMAlert.ESTAT_CHOICES`
                            # (Pendent/Acceptat/Corregit): era vocabulari no declarat que
                            # entrava en silenci —Django no valida choices a BD—, i el lector
                            # del dashboard ho havia d'anar tolerant (models_app/views.py:3384).
                            # Mateixa família que el fallback d'origens que C3/C va tancar el
                            # 02/08: es fa servir el valor que JA hi és. 'Pendent' és, a més,
                            # el `default` del camp, o sigui que 'Obert' n'era un sinònim, no
                            # un estat distint: cap decisió de domini, cap migració.
                            'estat': 'Pendent',
                            'origen': 'FITTING',
                        }
                    )
        except Exception:
            pass

        return Response({
            'piece_fitting_id': pf_id,
            'model_nom': model.nom_prenda if model else '',
            'unitat': unit,
            'resum': {'pass': n_pass, 'fail': n_fail, 'pendent': n_pend,
                      'total': n_pass + n_fail + n_pend},
            'count': len(resultats),
            'results': resultats,
        })

    except PieceFitting.DoesNotExist:
        return Response({'error': 'PieceFitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('fitting_vs_spec_view error')
        return Response({'error': str(e)}, status=500)
