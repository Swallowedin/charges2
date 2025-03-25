"""
Module d'analyse des clauses de charges dans les baux commerciaux.
"""
import streamlit as st
from api.openai_client import send_openai_request, parse_json_response
from config import MAX_BAIL_CHARS

def extract_charges_clauses_with_ai(bail_text, client):
    """
    Utilise l'IA pour extraire les sections pertinentes du bail concernant les charges.
    
    Args:
        bail_text: Texte du bail commercial
        client: Client OpenAI
        
    Returns:
        Texte des clauses pertinentes concernant les charges
    """
    # Si le texte est court, pas besoin de l'optimiser
    if len(bail_text) < 5000:
        return bail_text
    
    try:
        # Prompt pour demander à l'IA d'extraire les clauses pertinentes
        prompt = f"""
        Tu es un expert juridique spécialisé dans les baux commerciaux.
        
        Ta tâche consiste à extraire uniquement les clauses et sections du bail commercial suivant qui concernent les charges locatives, leur répartition, et leur facturation.
        
        Inclus dans ta sélection uniquement les clauses concernant précisément la refacturation des charges au preneur. aide toi de la liste suivante au besoin :
        - Toute clause mentionnant les charges, frais ou dépenses
        - Les articles concernant la répartition des charges
        - Les clauses relatives aux provisions sur charges
        - Les mentions de l'article 606 du code civil
        - Les sections traitant de la reddition des charges
        - Les articles concernant les impôts et taxes refacturés
        
        Retourne uniquement le texte des clauses pertinentes dans leur intégralité, sans commentaire ni analyse. 
        Assure-toi de conserver le format original et la numérotation des articles.
        
        Bail à analyser:
        ```
        {bail_text[:MAX_BAIL_CHARS]}
        ```
        """
        
        extracted_text = send_openai_request(
            client=client,
            prompt=prompt,
            json_format=False,  # Pour ce cas spécifique, on veut le texte brut
            temperature=0.1
        )
        
        # Si l'extraction a échoué ou renvoie un texte trop court, utiliser le texte original
        if not extracted_text or len(extracted_text) < 200:
            return bail_text[:MAX_BAIL_CHARS]  # Limiter à 15000 caractères en cas d'échec
            
        return extracted_text
        
    except Exception as e:
        # En cas d'erreur, utiliser le texte original tronqué
        st.warning(f"Extraction intelligente des clauses non disponible: {str(e)}")
        return bail_text[:MAX_BAIL_CHARS]

def extract_refacturable_charges_from_bail(bail_text, client):
    """
    Extrait spécifiquement les charges refacturables mentionnées dans le bail.
    
    Args:
        bail_text: Texte du bail commercial
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges refacturables
    """
    try:
        with st.spinner("Extraction des charges refacturables du bail..."):
            # Extraction des clauses pertinentes d'abord
            relevant_bail_text = extract_charges_clauses_with_ai(bail_text, client)
            
            # Prompt spécifique pour extraire uniquement les charges refacturables
            prompt = f"""
            ## Tâche d'extraction précise
            Tu es un analyste juridique spécialisé dans les baux commerciaux.
            
            Ta seule tâche est d'extraire la liste précise des charges qui sont explicitement mentionnées comme refacturables au locataire dans le bail commercial en détaillant les différentes catégories que tu identifies dans les charges locatives.
            
            Voici les clauses du bail concernant les charges:
            ```
            {relevant_bail_text[:MAX_BAIL_CHARS]}
            ```
            
            ## Instructions précises
            1. Identifie uniquement les postes et catégories de charges expressément mentionnés comme refacturables au locataire
            2. Liste chacun de ces postes ou catégories, et ne t'arrête pas à une catégorie généraliste comme "charges locatives"
            3. N'invente aucun poste de charge qui ne serait pas explicitement mentionné
            4. Si une charge est ambiguë ou implicite, indique-le clairement
            
            ## Format attendu (JSON)
            ```
            [
                {{
                    "categorie": "Catégorie exacte mentionnée dans le bail",
                    "description": "Description exacte de la charge, telle que rédigée dans le bail",
                    "base_legale": "Article X.X ou clause Y du bail",
                    "certitude": "élevée|moyenne|faible"
                }}
            ]
            ```
            
            Si aucune charge refacturable n'est mentionnée dans le bail, retourne un tableau vide.
            """
            
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1
            )
            
            # Extraire et analyser la réponse JSON
            result = parse_json_response(response_text, default_value=[])
            
            # Vérifier si le résultat est une liste directe ou s'il est encapsulé
            if isinstance(result, dict) and any(k for k in result.keys() if "charge" in k.lower()):
                for key in result.keys():
                    if "charge" in key.lower() and isinstance(result[key], list):
                        return result[key]
            elif isinstance(result, list):
                return result
            else:
                # Cas où le format ne correspond pas à ce qui est attendu
                return []
    
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des charges refacturables: {str(e)}")
        return []

def retry_extract_refacturable_charges(bail_text, client):
    """
    Seconde tentative d'extraction des charges refacturables avec un prompt différent.
    
    Args:
        bail_text: Texte du bail commercial
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges refacturables
    """
    try:
        prompt = f"""
        ## Tâche d'extraction spécifique
        Tu es un juriste spécialisé en droit des baux commerciaux en France.
        
        Examine attentivement ce bail commercial et identifie TOUTES les charges qui peuvent être refacturées au locataire de manière précise et en détaillant chaque catégorie de charge locative que tu identifies.
        
        ```
        {bail_text[:10000]}
        ```
        
        ## Instructions critiques
        1. Recherche spécifiquement les mentions de charges locatives, frais, dépenses ou taxes
        2. Cherche les clauses qui indiquent ce qui est à la charge du preneur/locataire
        3. Identifie les articles qui mentionnent la répartition des charges
        4. Considère les mentions de l'article 606 du Code Civil (grosses réparations)
        
        ## Liste de charges typiques à identifier si elles sont mentionnées
        - Nettoyage des parties communes
        - Enlèvement des déchets/ordures
        - Entretien des espaces verts
        - Électricité des parties communes
        - Chauffage collectif
        - Eau
        - Honoraires de gestion
        - Assurances
        - Taxes foncières
        - Taxes sur les bureaux
        
        Retourne uniquement un tableau JSON structuré:
        [
            {{"categorie": "Type de charge", "description": "Description précise", "base_legale": "Article ou clause du bail", "certitude": "élevée|moyenne|faible"}}
        ]
        """
        
        response_text = send_openai_request(
            client=client,
            prompt=prompt,
            temperature=0.1
        )
        
        result = parse_json_response(response_text, default_value=[])
        
        # Extraire la liste des charges de la réponse JSON
        if isinstance(result, list):
            return result
        
        # Si le résultat est un objet contenant une liste
        for key in result:
            if isinstance(result[key], list):
                return result[key]
        
        return []
    
    except Exception as e:
        st.error(f"Erreur lors de la seconde tentative d'extraction des charges refacturables: {str(e)}")
        return []
