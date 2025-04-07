"""
Module pour l'affichage des résultats de l'analyse.
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.export_utils import export_to_json, generate_pdf_report

def display_results(analysis, document_type):
    """
    Affiche les résultats de l'analyse sous forme structurée.
    
    Args:
        analysis: Dictionnaire contenant les résultats d'analyse
        document_type: Type de document (commercial)
    """
    st.header("Résultats de l'analyse des charges locatives commerciales")

    # Afficher le montant total et la conformité globale
    col1, col2 = st.columns(2)
    with col1:
        if "montant_total" in analysis:
            st.metric("Montant total des charges", f"{analysis['montant_total']:.2f}€")
    with col2:
        if "analyse_globale" in analysis and "taux_conformite" in analysis["analyse_globale"]:
            st.metric("Taux de conformité", f"{analysis['analyse_globale']['taux_conformite']}%")
    
    # Détail de l'analyse de conformité
    if "analyse_globale" in analysis and "conformite_detail" in analysis["analyse_globale"]:
        st.markdown("### Analyse de conformité")
        st.info(analysis["analyse_globale"]["conformite_detail"])

    # Section 1: Charges refacturables selon le bail
    st.markdown("## Charges refacturables selon le bail")
    if "charges_refacturables" in analysis and analysis["charges_refacturables"]:
        # Créer un DataFrame restructuré pour un meilleur affichage
        refined_data = []
        for charge in analysis["charges_refacturables"]:
            refined_data.append({
                "Catégorie": charge.get("categorie", ""),
                "Description": charge.get("description", ""),
                "Base légale": charge.get("base_legale", ""),
                "Certitude": charge.get("certitude", "")
            })
        
        refacturables_df = pd.DataFrame(refined_data)
        st.dataframe(refacturables_df, use_container_width=True)
    else:
        st.warning("Aucune information sur les charges refacturables n'a été identifiée dans le bail.")

    # Section 2: Charges effectivement facturées
    st.markdown("## Charges facturées")
    if "charges_facturees" in analysis and analysis["charges_facturees"]:
        # Préparation des données pour le tableau
        charges_df = pd.DataFrame([
            {
                "Poste": charge["poste"],
                "Montant (€)": charge["montant"],
                "% du total": f"{charge['pourcentage']:.1f}%",
                "Conformité": charge["conformite"],
                "Contestable": "Oui" if charge.get("contestable", False) else "Non"
            }
            for charge in analysis["charges_facturees"]
        ])
        
        # Affichage du tableau
        st.dataframe(charges_df, use_container_width=True)
        
        # Préparation et affichage du graphique camembert avec la fonction de visualizations.py
        display_charges_chart(analysis["charges_facturees"])
    else:
        st.warning("Aucune charge facturée n'a été identifiée.")

    # Section 3: Charges contestables
    st.markdown("## Charges potentiellement contestables")
    if "charges_facturees" in analysis:
        contestable_charges = [c for c in analysis["charges_facturees"] if c.get("contestable")]
        if contestable_charges:
            for charge in contestable_charges:
                with st.expander(f"{charge['poste']} ({charge['montant']}€)"):
                    st.markdown(f"**Montant:** {charge['montant']}€ ({charge['pourcentage']}% du total)")
                    st.markdown(f"**Raison:** {charge.get('raison_contestation', 'Non spécifiée')}")
                    st.markdown(f"**Justification:** {charge.get('justification', '')}")
        else:
            st.success("Aucune charge contestable n'a été identifiée.")
    
    # Section 4: Recommandations
    st.markdown("## Recommandations")
    if "recommandations" in analysis and analysis["recommandations"]:
        for i, rec in enumerate(analysis["recommandations"]):
            st.markdown(f"{i+1}. {rec}")
    else:
        st.info("Aucune recommandation spécifique.")

    # Options d'export
    display_export_options(analysis, document_type)

def display_charges_chart(charges_facturees):
    """
    Affiche un graphique camembert des charges facturées.
    
    Args:
        charges_facturees: Liste des charges facturées
    """
    # Vérifier si la liste est vide
    if not charges_facturees:
        st.warning("Aucune charge à afficher dans le graphique.")
        return
        
    # Préparation du graphique camembert
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # S'assurer que toutes les valeurs sont positives
    labels = []
    sizes = []
    
    for charge in charges_facturees:
        # Ne prendre que les montants positifs pour le graphique
        montant = charge.get("montant", 0)
        if montant > 0:  # Ne prendre que les valeurs positives
            labels.append(charge.get("poste", ""))
            sizes.append(montant)
    
    # Vérifier s'il reste des valeurs à afficher
    if not sizes:
        st.warning("Aucune charge avec un montant positif à afficher.")
        return
    
    # Génération du graphique
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels, 
        autopct='%1.1f%%',
        textprops={'fontsize': 9},
        startangle=90
    )
    
    # Ajustements du graphique
    plt.setp(autotexts, size=9, weight='bold')
    plt.setp(texts, size=9)
    ax.axis('equal')  # Equal aspect ratio ensures the pie chart is circular
    plt.title('Répartition des charges locatives commerciales')
    
    # Affichage du graphique
    st.pyplot(fig)

def display_export_options(analysis, document_type):
    """
    Affiche les options d'export des résultats.
    
    Args:
        analysis: Dictionnaire contenant les résultats d'analyse
        document_type: Type de document (commercial)
    """
    st.header("Exporter les résultats")
    col1, col2 = st.columns(2)
    
    with col1:
        # Export JSON
        json_data = export_to_json(analysis)
        st.download_button(
            label="Télécharger l'analyse en JSON",
            data=json_data,
            file_name='analyse_charges_locatives.json',
            mime='application/json',
        )
    
    with col2:
        # Export PDF
        try:
            document1_text = st.session_state.get('document1_text', '')
            document2_text = st.session_state.get('document2_text', '')
            
            # Générer le rapport PDF
            pdf_content = generate_pdf_report(
                analysis, 
                document_type, 
                document1_text, 
                document2_text
            )
            
            if pdf_content:
                # Bouton de téléchargement pour le PDF
                st.download_button(
                    label="Télécharger le rapport PDF",
                    data=pdf_content,
                    file_name="rapport_analyse_charges_locatives.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("Impossible de générer le PDF")
        except Exception as e:
            st.error(f"Erreur lors de la génération du PDF: {str(e)}")
            st.info("Assurez-vous d'avoir installé reportlab avec 'pip install reportlab'")
