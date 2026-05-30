"""
fhort/pom/s8_views.py — Sprint S8: CSV/PDF export
"""
import csv
import io
from django.http import HttpResponse
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
        return '—'
    v = float(val)
    if unit == 'INCH':
        return f'{v * CM_TO_INCH:.3f}"'
    return f'{v:.1f}'


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


def _category_name(p):
    if not p or not getattr(p, 'categoria_id', None):
        return ''
    return p.categoria.nom_ca or p.categoria.nom_en or ''


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_grading_csv_view(request, rule_set_id):
    """GET /api/v1/grading-rule-sets/{id}/export/csv/"""
    unit = get_unit(request)
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet

        rs = GradingRuleSet.objects.get(pk=rule_set_id)
        rules = GradingRule.objects.filter(
            rule_set=rs, actiu=True
        ).select_related('pom', 'pom__categoria', 'pom__pom_global').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="grading_{rs.codi_sistema or rs.id}.csv"'
        )
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['POM Code', 'POM Name EN', 'Categoria', 'Logica',
                         f'Increment ({unit.lower()})/talla'])
        for r in rules:
            writer.writerow([
                _pom_codi(r.pom),
                _pom_name_en(r.pom),
                _category_name(r.pom),
                r.logica,
                cv(r.increment, unit),
            ])
        return response
    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_grading_csv error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_size_set_csv_view(request, profile_id):
    """GET /api/v1/sizing-profiles/{id}/export/csv/"""
    unit = get_unit(request)
    try:
        from fhort.pom.models import SizingProfile, GradingRule, SizeDefinition

        profile = SizingProfile.objects.select_related(
            'target', 'construction', 'fit_type',
            'size_system', 'grading_rule_set'
        ).get(pk=profile_id)

        sizes = SizeDefinition.objects.filter(
            size_system=profile.size_system
        ).order_by('ordre') if profile.size_system_id else []

        rules = GradingRule.objects.filter(
            rule_set=profile.grading_rule_set, actiu=True
        ).select_related('pom', 'pom__categoria', 'pom__pom_global').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        ) if profile.grading_rule_set_id else []

        filename = f"sizeset_{profile.size_system.codi if profile.size_system_id else profile_id}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['FHORT Textile Tech — Size Set Export'])
        writer.writerow(['Sistema', profile.size_system.nom if profile.size_system_id else ''])
        writer.writerow(['Target', profile.target.nom_en if profile.target_id else ''])
        writer.writerow(['Construccio', profile.construction.nom_en if profile.construction_id else ''])
        writer.writerow(['Fit', profile.fit_type.nom_en if profile.fit_type_id else ''])
        writer.writerow(['Grading', profile.grading_rule_set.nom if profile.grading_rule_set_id else ''])
        writer.writerow(['Unitats', unit])
        writer.writerow([])

        sizes_list = list(sizes)
        size_labels = [s.etiqueta for s in sizes_list]
        writer.writerow(['Talles'] + size_labels)
        if any(s.body_bust_cm for s in sizes_list):
            writer.writerow(['Bust corporal (cm)'] + [s.body_bust_cm or '' for s in sizes_list])
        if any(s.body_height_cm for s in sizes_list):
            writer.writerow(['Alcada corporal (cm)'] + [s.body_height_cm or '' for s in sizes_list])
        writer.writerow([])

        writer.writerow(['POM', 'Nom', 'Categoria', 'Logica', f'Increment ({unit.lower()})/talla'])
        for r in rules:
            writer.writerow([
                _pom_codi(r.pom),
                _pom_name_en(r.pom),
                _category_name(r.pom),
                r.logica,
                cv(r.increment, unit),
            ])
        return response
    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_size_set_csv error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_fitting_csv_view(request, pf_id):
    """GET /api/v1/fittings/peca/{pf_id}/export/csv/

    Exports a PieceFitting: per line spec=valor_teoric, mesurat=valor_real, Δ=val-spec.
    Asymmetric tolerance from BaseMeasurement(model, pom) with 0.6 fallback;
    PASS iff -tol_minus <= Δ <= tol_plus.
    """
    unit = get_unit(request)
    TOL_FALLBACK = 0.6
    try:
        from fhort.fitting.models import PieceFitting, PieceFittingLine
        from fhort.models_app.models import BaseMeasurement

        pf = PieceFitting.objects.select_related('model').get(pk=pf_id)
        model = pf.model
        lines = PieceFittingLine.objects.filter(
            piece_fitting=pf
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client', 'size_label')

        tol_map = {}
        for bm in BaseMeasurement.objects.filter(model=model, is_active=True):
            tm = float(bm.tolerancia_minus) if bm.tolerancia_minus is not None else TOL_FALLBACK
            tp = float(bm.tolerancia_plus) if bm.tolerancia_plus is not None else TOL_FALLBACK
            tol_map[bm.pom_id] = (tm, tp)

        nom_model = str(model) if model else f'piece_{pf_id}'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="fitting_peca_{pf_id}.csv"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['FHORT Textile Tech — Fitting Report'])
        writer.writerow(['Model', nom_model])
        writer.writerow(['PieceFitting', pf_id])
        writer.writerow(['Unitats', unit])
        writer.writerow([])
        writer.writerow(['POM', 'Nom', 'Talla', f'Spec ({unit.lower()})',
                         f'Mesurat ({unit.lower()})', f'Δ ({unit.lower()})',
                         f'Tolerancia ({unit.lower()})', 'Resultat'])

        for line in lines:
            spec = float(line.valor_teoric) if line.valor_teoric is not None else None
            val = float(line.valor_real) if line.valor_real is not None else None
            desv = round(val - spec, 2) if (val is not None and spec is not None) else None
            tol_minus, tol_plus = tol_map.get(line.pom_id, (TOL_FALLBACK, TOL_FALLBACK))
            passa = ((-tol_minus) <= desv <= tol_plus) if desv is not None else None

            writer.writerow([
                _pom_codi(line.pom),
                _pom_name_en(line.pom),
                line.size_label,
                cv(spec, unit) if spec is not None else '—',
                cv(val, unit) if val is not None else '—',
                (f'+{cv(desv, unit)}' if desv and desv > 0 else cv(desv, unit)) if desv is not None else '—',
                f'-{cv(tol_minus, unit)}/+{cv(tol_plus, unit)}',
                'PASS' if passa else 'FAIL' if passa is False else '—',
            ])
        return response
    except PieceFitting.DoesNotExist:
        return Response({'error': 'PieceFitting no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_fitting_csv error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_model_spec_pdf_view(request, model_id):
    """GET /api/v1/models/{id}/export/pdf/ — model tech sheet with BaseMeasurements."""
    unit = get_unit(request)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from fhort.models_app.models import Model, BaseMeasurement

        model = Model.objects.get(pk=model_id)
        bms = BaseMeasurement.objects.filter(
            model=model, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        gold = colors.HexColor('#C27A2A')
        dark = colors.HexColor('#1D1D1B')
        gray = colors.HexColor('#868685')

        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                     fontSize=16, textColor=gold, spaceAfter=4)
        sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                   fontSize=9, textColor=gray, spaceAfter=12)
        label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                     fontSize=8, textColor=gray)

        story = []
        story.append(Paragraph('FHORT Textile Tech', label_style))
        story.append(Paragraph(
            f'{model.nom_prenda or ""} — {model.codi_intern or ""}', title_style
        ))
        story.append(Paragraph(
            f'Temporada {model.temporada or ""}{model.any or ""} · '
            f'Estat: {model.estat or ""} · Unitats: {unit}',
            sub_style
        ))

        info_data = [
            ['Codi intern', model.codi_intern or '—', 'Codi client', model.codi_client or '—'],
            ['Nom prenda', model.nom_prenda or '—', 'Temporada', f'{model.temporada or ""}{model.any or ""}'],
            ['Garment type', str(model.garment_type) if model.garment_type_id else '—',
             'Talla base', model.base_size_label or '—'],
            ['Size run', model.size_run_model or '—',
             'Grading', str(model.grading_rule_set) if model.grading_rule_set_id else '—'],
        ]
        info_table = Table(info_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAF8')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), gray),
            ('TEXTCOLOR', (2, 0), (2, -1), gray),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0D5C5')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1),
             [colors.white, colors.HexColor('#FDF9F5')]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        if bms.exists():
            story.append(Paragraph(f'MESURES TALLA BASE ({unit})', ParagraphStyle(
                'SectionTitle', parent=styles['Heading2'],
                fontSize=10, textColor=gold, spaceBefore=12, spaceAfter=6
            )))
            rows = [['POM', 'Nom', 'Categoria', f'Valor ({unit.lower()})']]
            for bm in bms:
                val = float(bm.base_value_cm) if bm.base_value_cm is not None else 0.0
                if unit == 'INCH':
                    val = round(val * CM_TO_INCH, 3)
                rows.append([
                    _pom_codi(bm.pom),
                    _pom_name_en(bm.pom),
                    _category_name(bm.pom),
                    str(val),
                ])
            t = Table(rows, colWidths=[2.5*cm, 6*cm, 5*cm, 4.5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), gold),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0D5C5')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#FDF9F5')]),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]))
            story.append(t)

        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            'Generat per FHORT Textile Tech · fhorttextile.tech',
            ParagraphStyle('Footer', parent=styles['Normal'],
                           fontSize=7, textColor=gray, alignment=1)
        ))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="spec_{model.codi_intern or model_id}.pdf"'
        )
        return response
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    except ImportError:
        return Response({'error': 'ReportLab no instal·lat'}, status=500)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('export_model_spec_pdf error')
        return Response({'error': str(e)}, status=500)
