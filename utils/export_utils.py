"""
Utilitaires pour l'export des résultats d'analyse (PDF, JSON, etc.).
"""
import json
import datetime
import streamlit as st
from io import BytesIO

def export_to_json(analysis):
    """
    Exporte l'analyse au format JSON.
    
    Args:
        analysis: Dictionnaire contenant les résultats d'analyse
        
    Returns:
        Données JSON encodées en UTF-8
    """
    return json.dumps(analysis, indent=2, ensure_ascii=False).encode('utf-8')

def generate_pdf_report(analysis, document_type, text1=None, text2=None):
    """
    Génère un rapport PDF complet et précis de l'analyse des charges locatives commerciales.
    
    Args:
        analysis: Dictionnaire contenant les résultats d'analyse
        document_type: Type de document ("commercial")
        text1: Texte du bail (optionnel)
        text2: Texte de la reddition des charges (optionnel)
        
    Returns:
        Contenu du PDF sous forme de bytes
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib.units import cm
    except ImportError:
        st.error("La bibliothèque reportlab n'est pas installée. Installez-la avec 'pip install reportlab'")
        return None
    
    # Créer un buffer pour stocker le PDF
    buffer = BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Contenu du document
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', parent=styles['Heading1'], alignment=1))
    styles.add(ParagraphStyle(name='Justify', parent=styles['Normal'], alignment=4))
    styles.add(ParagraphStyle(name='Small', parent=styles['Normal'], fontSize=8))
    
    # Titre et date
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    title = f"Analyse des Charges Locatives Commerciales"
    story.append(Paragraph(title, styles['Center']))
    story.append(Paragraph(f"Rapport généré le {today}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Informations générales
    story.append(Paragraph("Informations générales", styles['Heading2']))
    
    # Préparation des données pour le tableau d'information
    info_data = [
        ["Type de bail", "Commercial"]
    ]
    
    # Ajout des informations financières si disponibles
    if "montant_total" in analysis:
        info_data.append(["Montant total des charges", f"{analysis['montant_total']:.2f}€"])
    
    if "analyse_globale" in analysis and "taux_conformite" in analysis["analyse_globale"]:
        info_data.append(["Taux de conformité", f"{analysis['analyse_globale']['taux_conformite']}%"])
    
    # Créer un tableau pour les informations
    info_table = Table(info_data, colWidths=[5*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Analyse de conformité
    if "analyse_globale" in analysis and "conformite_detail" in analysis["analyse_globale"]:
        story.append(Paragraph("Analyse de conformité", styles['Heading3']))
        story.append(Paragraph(analysis["analyse_globale"]["conformite_detail"], styles['Justify']))
        story.append(Spacer(1, 0.5*cm))
    
    # Charges refacturables selon le bail
    if "charges_refacturables" in analysis and analysis["charges_refacturables"]:
        story.append(Paragraph("Charges refacturables selon le bail", styles['Heading2']))
        
        # Création du tableau des charges refacturables
        refac_data = [["Catégorie", "Description", "Base légale / contractuelle"]]
        
        for charge in analysis["charges_refacturables"]:
            refac_data.append([
                charge.get("categorie", ""),
                charge.get("description", ""),
                charge.get("base_legale", "")
            ])
        
        refac_table = Table(refac_data, colWidths=[4*cm, 7*cm, 4*cm])
        refac_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(refac_table)
        story.append(Spacer(1, 0.5*cm))
    
    # Analyse des charges facturées
    if "charges_facturees" in analysis and analysis["charges_facturees"]:
        story.append(Paragraph("Analyse des charges facturées", styles['Heading2']))
        
        # Création du tableau des charges facturées
        charges_data = [["Poste", "Montant (€)", "% du total", "Conformité", "Contestable"]]
        
        for charge in analysis["charges_facturees"]:
            charges_data.append([
                charge.get("poste", ""),
                f"{charge.get('montant', 0):.2f}",
                f"{charge.get('pourcentage', 0):.1f}%",
                charge.get("conformite", ""),
                "Oui" if charge.get("contestable", False) else "Non"
            ])
        
        charges_table = Table(charges_data, colWidths=[6*cm, 2.5*cm, 2*cm, 2.5*cm, 2*cm])
        charges_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(charges_table)
        story.append(Spacer(1, 0.5*cm))
        
        # Charges contestables
        contestable_charges = [c for c in analysis["charges_facturees"] if c.get("contestable", False)]
        if contestable_charges:
            story.append(Paragraph("Charges potentiellement contestables", styles['Heading2']))
            
            for charge in contestable_charges:
                charge_title = f"{charge.get('poste', '')} ({charge.get('montant', 0):.2f}€)"
                story.append(Paragraph(charge_title, styles['Heading3']))
                story.append(Paragraph(f"Montant: {charge.get('montant', 0):.2f}€ ({charge.get('pourcentage', 0):.1f}% du total)", styles['Normal']))
                
                if "raison_contestation" in charge and charge["raison_contestation"]:
                    story.append(Paragraph(f"Raison: {charge['raison_contestation']}", styles['Normal']))
                
                if "justification" in charge and charge["justification"]:
                    story.append(Paragraph(f"Justification: {charge['justification']}", styles['Normal']))
                    
                story.append(Spacer(1, 0.3*cm))
    
    # Recommandations
    if "recommandations" in analysis and analysis["recommandations"]:
        story.append(PageBreak())
        story.append(Paragraph("Recommandations", styles['Heading2']))
        
        for i, rec in enumerate(analysis["recommandations"]):
            story.append(Paragraph(f"{i+1}. {rec}", styles['Normal']))
            story.append(Spacer(1, 0.2*cm))
    
    # Pied de page
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Ce rapport a été généré automatiquement et sert uniquement à titre indicatif. "
                          "Pour une analyse juridique complète, veuillez consulter un professionnel du droit.", 
                          styles['Small']))
    
    # Construire le PDF
    doc.build(story)
    
    # Récupérer le contenu du buffer
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content
