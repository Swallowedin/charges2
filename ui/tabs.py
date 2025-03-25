"""
Module pour la gestion de la barre latérale (sidebar) de l'application Streamlit.
"""
import streamlit as st

def render_sidebar():
    """
    Affiche les éléments de la barre latérale de l'application.
    
    Returns:
        Tuple contenant les paramètres configurés dans la sidebar
    """
    st.sidebar.header("Configuration")
    
    # Type de document (toujours commercial)
    document_type = "commercial"
    
    st.sidebar.info("Cet outil est conçu spécifiquement pour analyser les baux commerciaux et leurs charges.")
    
    # Entrée de la surface locative
    surface = st.sidebar.text_input(
        "Surface locative (m²)",
        help="Utilisé pour calculer le ratio de charges au m²"
    )
    
    # Ajout de métriques dans la sidebar si l'analyse est complète
    if st.session_state.get('analysis_complete', False):
        analysis = st.session_state.get('analysis', {})
        
        if "montant_total" in analysis:
            st.sidebar.metric(
                "Montant total des charges", 
                f"{analysis['montant_total']:.2f}€"
            )
            
            # Calculer et afficher le ratio au m² si la surface est définie
            if surface and surface.isdigit() and int(surface) > 0:
                ratio = analysis['montant_total'] / int(surface)
                st.sidebar.metric(
                    "Ratio charges/m²", 
                    f"{ratio:.2f}€/m²"
                )
        
        if "analyse_globale" in analysis and "taux_conformite" in analysis["analyse_globale"]:
            st.sidebar.metric(
                "Taux de conformité", 
                f"{analysis['analyse_globale']['taux_conformite']}%"
            )
    
    # Ajout d'informations complémentaires
    with st.sidebar.expander("À propos de l'outil"):
        st.write("""
        Cet outil utilise l'intelligence artificielle pour analyser la conformité
        des charges locatives commerciales par rapport au bail.
        
        Il est conçu pour vous aider à identifier rapidement les charges potentiellement
        contestables et à préparer vos discussions avec le bailleur.
        
        Les résultats sont fournis à titre indicatif et ne constituent pas un avis juridique.
        """)
    
    return document_type, surface
