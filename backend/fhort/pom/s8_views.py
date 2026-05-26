"""
fhort/pom/s8_views.py — Sprint S8: Exportació PDF/CSV
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
    if val is None: return '—'
    v = float(val)
    if unit == 'INCH': return f'{v * CM_TO_INCH:.3f}"'
    return f'{v:.1f}'


# ─── CSV ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_grading_csv_view(request, rule_set_id):
    """
    GET /api/v1/grading-rule-sets/{id}/export/csv/
    Exporta les regles de grading com a CSV.
    """
    unit = get_unit(request)
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet

        rs = GradingRuleSet.objects.get(pk=rule_set_id)
        rules = GradingRule.objects.filter(
            rule_set=rs, actiu=True
        ).select_related('pom', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_intern'
        )

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="grading_{rs.codi_sistema or rs.id}.csv"'
        response.write('﻿')  # BOM UTF-8

        writer = csv.writer(response)
        writer.writerow(['POM Code', 'POM Name EN', 'Categoria', 'Logica',
                          f'Increment ({unit.lower()})/talla', 'Notes'])
        for r in rules:
            writer.writerow([
                r.pom.codi_intern if r.pom_id else '',
                r.pom.nom_en if r.pom_id else '',
                r.pom.categoria.nom_en if (r.pom_id and r.pom.categoria_id) else '',
                r.logica,
                cv(r.increment, unit),
                r.notes or '',
            ])
        return response
    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_size_set_csv_view(request, profile_id):
    """
    GET /api/v1/sizing-profiles/{id}/export/csv/
    Exporta el size set complet (talles + grading) com a CSV per enviar al proveïdor.
    """
    unit = get_unit(request)
    try:
        from fhort.pom.models import SizingProfile, GradingRule, SizeDefinition

        profile = SizingProfile.objects.select_related(
            'target', 'construction', 'fit_type',
            'size_system', 'grading_rule_set'
        ).get(pk=profile_id)

        sizes = SizeDefinition.objects.filter(
            size_system=profile.size_system
        ).order_by('display_order')

        rules = GradingRule.objects.filter(
            rule_set=profile.grading_rule_set, actiu=True
        ).select_related('pom', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_intern'
        )

        filename = f"sizeset_{profile.size_system.codi if profile.size_system_id else profile_id}.csv"
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('﻿')

        writer = csv.writer(response)

        # Capçalera info
        writer.writerow(['FHORT Textile Tech — Size Set Export'])
        writer.writerow(['Sistema', profile.size_system.nom if profile.size_system_id else ''])
        writer.writerow(['Target', profile.target.nom_en if profile.target_id else ''])
        writer.writerow(['Construcció', profile.construction.nom_en if profile.construction_id else ''])
        writer.writerow(['Fit', profile.fit_type.nom_en if profile.fit_type_id else ''])
        writer.writerow(['Grading', profile.grading_rule_set.nom if profile.grading_rule_set_id else ''])
        writer.writerow(['Unitats', unit])
        writer.writerow([])

        # Talles
        size_labels = [s.size_label for s in sizes]
        writer.writerow(['Talles'] + size_labels)
        if any(s.body_bust_cm for s in sizes):
            writer.writerow(['Bust corporal (cm)'] + [s.body_bust_cm or '' for s in sizes])
        if any(s.body_height_cm for s in sizes):
            writer.writerow(['Alçada corporal (cm)'] + [s.body_height_cm or '' for s in sizes])
        writer.writerow([])

        # Regles de grading
        writer.writerow(['POM', 'Nom', 'Categoria', 'Lògica', f'Increment ({unit.lower()})/talla'])
        for r in rules:
            writer.writerow([
                r.pom.codi_intern if r.pom_id else '',
                r.pom.nom_en if r.pom_id else '',
                r.pom.categoria.nom_en if (r.pom_id and r.pom.categoria_id) else '',
                r.logica,
                cv(r.increment, unit),
            ])

        return response
    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_fitting_csv_view(request, fitting_id):
    """
    GET /api/v1/fittings/{id}/export/csv/
    Exporta les línies d'un fitting com a CSV amb pass/fail.
    """
    unit = get_unit(request)
    try:
        from fhort.fitting.models import SFFitting, SFFittingLinia

        fitting = SFFitting.objects.select_related('size_fitting__model').get(pk=fitting_id)
        lines = SFFittingLinia.objects.filter(
            fitting=fitting
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client')

        nom_model = str(fitting.size_fitting.model) if fitting.size_fitting_id else f'fitting_{fitting_id}'
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="fitting_{fitting_id}.csv"'
        response.write('﻿')

        writer = csv.writer(response)
        writer.writerow(['FHORT Textile Tech — Fitting Report'])
        writer.writerow(['Model', nom_model])
        writer.writerow(['Unitats', unit])
        writer.writerow([])
        writer.writerow(['POM', 'Nom', f'Spec ({unit.lower()})',
                          f'Mesurat ({unit.lower()})', f'Δ ({unit.lower()})',
                          f'Tolerància ({unit.lower()})', 'Resultat'])

        for line in lines:
            tol = float(line.pom.pom_global.tolerancia_woven_cm
                        if line.pom.pom_global_id else 0.6)
            val = float(line.value_cm) if line.value_cm else None
            spec = float(line.spec_value_cm) if line.spec_value_cm else None
            desv = round(val - spec, 2) if val and spec else None
            passa = abs(desv) <= tol if desv is not None else None

            writer.writerow([
                line.pom.codi_client,
                line.pom.pom_global.nom_en if line.pom.pom_global_id else line.pom.nom_client,
                cv(spec, unit) if spec else '—',
                cv(val, unit) if val else '—',
                f'+{cv(desv, unit)}' if desv and desv > 0 else cv(desv, unit) if desv else '—',
                f'±{cv(tol, unit)}',
                'PASS' if passa else 'FAIL' if passa is False else '—',
            ])

        return response
    except SFFitting.DoesNotExist:
        return Response({'error': 'Fitting no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_model_spec_pdf_view(request, model_id):
    """
    GET /api/v1/models/{id}/export/pdf/
    Genera un PDF de la fitxa tècnica del model amb BaseMeasurements.
    Usa ReportLab.
    """
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
        ).select_related('pom', 'pom__pom_global', 'pom__pom_global__categoria').order_by(
            'pom__pom_global__categoria__display_order', 'pom__codi_client'
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                 rightMargin=2*cm, leftMargin=2*cm,
                                 topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        gold = colors.HexColor('#C27A2A')
        dark = colors.HexColor('#1D1D1B')
        gray = colors.HexColor('#868685')
        light = colors.HexColor('#F5E6D0')

        title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                      fontSize=16, textColor=gold, spaceAfter=4)
        sub_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                    fontSize=9, textColor=gray, spaceAfter=12)
        label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                      fontSize=8, textColor=gray)
        val_style = ParagraphStyle('Val', parent=styles['Normal'],
                                    fontSize=10, textColor=dark)

        story = []

        # Títol
        story.append(Paragraph(f'FHORT Textile Tech', label_style))
        story.append(Paragraph(
            f'{model.nom_prenda} — {model.codi_intern or ""}', title_style
        ))
        story.append(Paragraph(
            f'Temporada {model.temporada}{model.any} · '
            f'Estat: {model.estat} · Unitats: {unit}', sub_style
        ))

        # Info model
        info_data = [
            ['Codi intern', model.codi_intern or '—',
             'Codi client', model.codi_client or '—'],
            ['Nom prenda', model.nom_prenda,
             'Temporada', f'{model.temporada}{model.any}'],
            ['Garment type', str(model.garment_type) if model.garment_type_id else '—',
             'Talla base', model.base_size_label or '—'],
            ['Size run', model.size_run_model or '—',
             'Grading', str(model.grading_rule_set) if model.grading_rule_set_id else '—'],
        ]
        info_table = Table(info_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFAF8')),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('TEXTCOLOR', (0,0), (0,-1), gray),
            ('TEXTCOLOR', (2,0), (2,-1), gray),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0D5C5')),
            ('ROWBACKGROUNDS', (0,0), (-1,-1),
             [colors.white, colors.HexColor('#FDF9F5')]),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        # Base measurements
        if bms.exists():
            story.append(Paragraph(f'MESURES TALLA BASE ({unit})', ParagraphStyle(
                'SectionTitle', parent=styles['Heading2'],
                fontSize=10, textColor=gold, spaceBefore=12, spaceAfter=6
            )))

            header = ['POM', 'Nom', 'Categoria', f'Valor ({unit.lower()})']
            rows = [header]
            for bm in bms:
                val = float(bm.base_value_cm)
                if unit == 'INCH': val = round(val * CM_TO_INCH, 3)
                rows.append([
                    bm.pom.codi_client,
                    bm.pom.pom_global.nom_en if bm.pom.pom_global_id else bm.pom.nom_client,
                    (bm.pom.pom_global.categoria.nom_en
                     if bm.pom.pom_global_id and bm.pom.pom_global.categoria_id else ''),
                    str(val),
                ])

            t = Table(rows, colWidths=[2.5*cm, 6*cm, 5*cm, 4.5*cm])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), gold),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0D5C5')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1),
                 [colors.white, colors.HexColor('#FDF9F5')]),
                ('PADDING', (0,0), (-1,-1), 5),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            story.append(t)

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(
            f'Generat per FHORT Textile Tech · fhorttextile.tech',
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
        return Response({'error': 'ReportLab no instal·lat. Executa: pip install reportlab'}, status=500)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("export_model_spec_pdf error")
        return Response({'error': str(e)}, status=500)
