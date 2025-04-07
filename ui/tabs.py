"""
Module pour la gestion des onglets et de la barre latérale de l'application Streamlit.
"""
import streamlit as st
from utils.file_utils import process_multiple_files, validate_file_input

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


def render_input_tabs():
    """
    Affiche les onglets d'entrée pour télécharger les documents et récupère leur contenu.
    
    Returns:
        Tuple contenant (run_analysis, text1, text2)
    """
    st.header("Téléchargement des documents")
    
    # Création des onglets
    doc1_tab, doc2_tab, analyse_tab = st.tabs([
        "Bail commercial", 
        "Reddition des charges", 
        "Lancer l'analyse"
    ])
    
    # Variables pour stocker les résultats
    doc1_files = None
    doc2_files = None
    document1_text = ""
    document2_text = ""
    run_analysis = False
    
    # Onglet 1: Bail commercial
    with doc1_tab:
        st.subheader("Téléchargez votre bail commercial")
        st.info("Formats acceptés: PDF, Word, TXT ou image")
        
        doc1_files = st.file_uploader(
            "Sélectionnez un ou plusieurs fichiers contenant le bail commercial",
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="bail_files"
        )
        
        if doc1_files:
            document1_text = process_multiple_files(doc1_files)
            st.session_state.document1_text = document1_text
            
            if document1_text:
                st.success(f"✅ {len(doc1_files)} fichier(s) traité(s) - {len(document1_text)} caractères extraits")
                with st.expander("Aperçu du texte extrait"):
                    st.text(document1_text[:1000] + "..." if len(document1_text) > 1000 else document1_text)
            else:
                st.error("❌ Aucun texte n'a pu être extrait. Vérifiez vos fichiers.")
    
    # Onglet 2: Reddition des charges
    with doc2_tab:
        st.subheader("Téléchargez votre reddition des charges")
        st.info("Formats acceptés: PDF, Word, TXT ou image")
        
        doc2_files = st.file_uploader(
            "Sélectionnez un ou plusieurs fichiers contenant la reddition des charges",
            type=["pdf", "docx", "txt", "jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="charges_files"
        )
        
        if doc2_files:
            document2_text = process_multiple_files(doc2_files)
            st.session_state.document2_text = document2_text
            
            if document2_text:
                st.success(f"✅ {len(doc2_files)} fichier(s) traité(s) - {len(document2_text)} caractères extraits")
                with st.expander("Aperçu du texte extrait"):
                    st.text(document2_text[:1000] + "..." if len(document2_text) > 1000 else document2_text)
            else:
                st.error("❌ Aucun texte n'a pu être extrait. Vérifiez vos fichiers.")
    
    # Onglet 3: Lancer l'analyse
    with analyse_tab:
        st.subheader("Lancer l'analyse des documents")
        
        # Récupérer les données de la session si disponibles
        if "document1_text" in st.session_state:
            document1_text = st.session_state.document1_text
        if "document2_text" in st.session_state:
            document2_text = st.session_state.document2_text
        
        # Vérifier si les documents sont prêts pour l'analyse
        is_valid, error_message = validate_file_input(doc1_files, doc2_files)
        
        if is_valid:
            st.success("✅ Documents prêts pour l'analyse")
            
            if st.button("Lancer l'analyse des charges"):
                run_analysis = True
        else:
            st.warning(error_message)
    
    # Retourner les résultats attendus par app.py
    return run_analysis, document1_text, document2_text
