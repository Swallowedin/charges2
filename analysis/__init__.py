"""
Module d'analyse des charges locatives commerciales.
"""
import streamlit as st
from api.openai_client import get_openai_client

def analyze_with_openai(text1, text2, document_type):
    """
    Analyse les documents en suivant une approche structurée en trois étapes.
    
    Args:
        text1: Texte du bail commercial
        text2: Texte de la reddition des charges
        document_type: Type de document (commercial)
        
    Returns:
        Dictionnaire contenant l'analyse complète
    """
    # Initialiser client en dehors du bloc try
    client = None
    
    try:
        # Initialiser le client OpenAI
        client = get_openai_client()
        
        # Import à l'intérieur de la fonction pour éviter les imports circulaires
        from analysis.bail_analyzer import extract_refacturable_charges_from_bail, retry_extract_refacturable_charges
        from analysis.charges_analyzer import extract_charged_amounts_from_reddition, extract_charged_amounts_fallback
        from analysis.conformity_analyzer import analyse_charges_conformity, retry_analyse_conformity, final_attempt_complete_analysis
        
        with st.spinner("Étape 1/3: Extraction des charges refacturables du bail..."):
            # Extraire les charges refacturables mentionnées dans le bail
            refacturable_charges = extract_refacturable_charges_from_bail(text1, client)
            
            if refacturable_charges:
                st.success(f"✅ {len(refacturable_charges)} postes de charges refacturables identifiés dans le bail")
            else:
                st.warning("⚠️ Aucune charge refacturable clairement identifiée dans le bail")
                # Deuxième tentative avec un prompt différent
                refacturable_charges = retry_extract_refacturable_charges(text1, client)
        
        with st.spinner("Étape 2/3: Extraction des montants facturés..."):
            # Extraire les montants facturés mentionnés dans la reddition
            charged_amounts = extract_charged_amounts_from_reddition(text2, client)
            
            if charged_amounts:
                total = sum(charge.get("montant", 0) for charge in charged_amounts)
                st.success(f"✅ {len(charged_amounts)} postes de charges facturés identifiés, pour un total de {total:.2f}€")
            else:
                st.warning("⚠️ Aucun montant facturé clairement identifié dans la reddition des charges")
                # Deuxième tentative avec une méthode alternative
                charged_amounts = extract_charged_amounts_fallback(text2, client)
        
        with st.spinner("Étape 3/3: Analyse de la conformité..."):
            # Analyser la conformité entre les charges refacturables et facturées
            result = analyse_charges_conformity(refacturable_charges, charged_amounts, client)
            
            if result and "analyse_globale" in result and "taux_conformite" in result["analyse_globale"]:
                conformity = result["analyse_globale"]["taux_conformite"]
                st.success(f"✅ Analyse complète avec un taux de conformité de {conformity}%")
            else:
                st.warning("⚠️ Analyse de conformité incomplète - nouvelle tentative...")
                # Deuxième tentative avec approche différente
                result = retry_analyse_conformity(refacturable_charges, charged_amounts, client)
        
        return result
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse: {str(e)}")
        
        # Vérifier si client a été initialisé avant de l'utiliser
        if client:
            # Import à l'intérieur du bloc pour éviter les problèmes d'import circulaire
            from analysis.conformity_analyzer import final_attempt_complete_analysis
            return final_attempt_complete_analysis(text1, text2, client)
        else:
            # Si client n'a pas été initialisé, créer un résultat vide
            return {
                "charges_refacturables": [],
                "charges_facturees": [],
                "montant_total": 0,
                "analyse_globale": {
                    "taux_conformite": 0,
                    "conformite_detail": "L'analyse a échoué: impossible de se connecter à l'API OpenAI."
                },
                "recommandations": [
                    "Vérifiez votre clé API OpenAI et votre connexion internet.",
                    "Essayez à nouveau plus tard."
                ]
            }
