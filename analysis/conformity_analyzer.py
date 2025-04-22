"""
Module d'analyse de la conformité entre les charges refacturables et les montants facturés.
Dépend exclusivement de GPT-4o-mini pour l'analyse.
"""
import streamlit as st
import json
from api.openai_client import get_openai_client, send_openai_request, parse_json_response
from config import DEFAULT_CONFORMITY_LEVEL

def analyse_charges_conformity(refacturable_charges, charged_amounts, client):
    """
    Analyse la conformité entre les charges refacturables et les montants facturés.
    Utilise exclusivement GPT-4o-mini pour l'analyse.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
        with st.spinner("Analyse de la conformité des charges avec GPT-4o-mini..."):
            # Convertir les listes en JSON pour les inclure dans le prompt
            refacturable_json = json.dumps(refacturable_charges, ensure_ascii=False)
            charged_json = json.dumps(charged_amounts, ensure_ascii=False)
            
            prompt = f"""
            ## Tâche d'analyse
            Tu es un expert juridique et comptable spécialisé dans l'analyse de conformité des charges locatives commerciales.
            
            Ta tâche est d'analyser la conformité entre les charges refacturables selon le bail et les charges effectivement facturées.
            
            ## Données d'entrée
            
            ### Charges refacturables selon le bail:
            ```json
            {refacturable_json}
            ```
            
            ### Charges effectivement facturées:
            ```json
            {charged_json}
            ```
            
            ## Instructions précises
            1. Pour chaque charge facturée, détermine si elle correspond à une charge refacturable expressément prévue par le bail
            2. Évalue la conformité de chaque charge par rapport au bail
            3. Identifie les charges potentiellement contestables qui ne sont pas susceptibles d'être refacturée au preneur avec une justification précise
            4. Calcule le pourcentage que représente chaque charge par rapport au total des charges facturées
            5. Calcule le montant total des charges facturées
            6. Détermine un taux global de conformité basé sur le pourcentage des charges conformes
            
            ## Format attendu (JSON)
            ```json
            {{
                "charges_facturees": [
                    {{
                        "poste": "Intitulé exact de la charge facturée",
                        "montant": 1234.56,
                        "pourcentage": 25.5,
                        "conformite": "conforme|à vérifier|non conforme",
                        "justification": "Explication précise de la conformité ou non",
                        "contestable": true|false,
                        "raison_contestation": "Raison précise si contestable"
                    }}
                ],
                "montant_total": 5000.00,
                "analyse_globale": {{
                    "taux_conformite": 75,
                    "conformite_detail": "Explication détaillée du taux de conformité"
                }},
                "recommandations": [
                    "Recommandation précise et actionnable 1",
                    "Recommandation précise et actionnable 2"
                ]
            }}
            ```
            """
            
            # Utiliser GPT-4o-mini comme modèle
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1,
                model="gpt-4o-mini"
            )
            
            result = parse_json_response(response_text, default_value=None)
            
            # Si l'analyse a échoué, on ne propose pas d'alternative
            if not result:
                st.error("L'analyse avec GPT-4o-mini a échoué. Aucun résultat disponible.")
                return None
            
            # Ajouter les charges refacturables au résultat pour l'affichage complet
            result["charges_refacturables"] = refacturable_charges
            return result
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse de conformité avec GPT-4o-mini: {str(e)}")
        return None

def retry_analyse_conformity(refacturable_charges, charged_amounts, client):
    """
    Seconde tentative d'analyse de conformité avec un prompt différent.
    Utilise toujours GPT-4o-mini mais avec un prompt reformulé.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
        with st.spinner("Nouvelle tentative d'analyse avec GPT-4o-mini..."):
            # Convertir les listes en JSON pour les inclure dans le prompt
            refacturable_json = json.dumps(refacturable_charges, ensure_ascii=False)
            charged_json = json.dumps(charged_amounts, ensure_ascii=False)
            
            prompt = f"""
            ## Analyse détaillée de conformité des charges locatives
            
            Tu es un avocat spécialisé en baux commerciaux qui doit déterminer si les charges facturées à un locataire sont conformes au bail.
            
            ## Données d'entrée
            
            ### 1. Charges refacturables selon le bail:
            ```json
            {refacturable_json}
            ```
            
            ### 2. Charges effectivement facturées:
            ```json
            {charged_json}
            ```
            
            ## Instructions précises
            1. Compare chaque charge facturée avec les charges autorisées par le bail
            2. Pour chaque charge facturée, détermine si elle est explicitement autorisée, implicitement autorisée, ou non autorisée
            3. Calcule le pourcentage que représente chaque charge par rapport au total facturé
            4. Identifie les charges potentiellement contestables avec justification précise
            5. Détermine un taux global de conformité basé sur le pourcentage des charges conformes
            
            ## Format de réponse requis (JSON)
            {{
                "charges_facturees": [
                    {{
                        "poste": "Nom exact de la charge facturée",
                        "montant": montant_numérique,
                        "pourcentage": pourcentage_numérique,
                        "conformite": "conforme|à vérifier|non conforme",
                        "justification": "Explication précise",
                        "contestable": true|false,
                        "raison_contestation": "Raison si contestable"
                    }}
                ],
                "montant_total": montant_total_numérique,
                "analyse_globale": {{
                    "taux_conformite": pourcentage_numérique,
                    "conformite_detail": "Explication détaillée"
                }},
                "recommandations": [
                    "Recommandation actionnable 1",
                    "Recommandation actionnable 2"
                ]
            }}
            
            ATTENTION: Sois rigoureux dans ton analyse. Ne suppose pas qu'une charge est autorisée sans preuve claire dans le bail.
            """
            
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1,
                model="gpt-4o-mini"
            )
            
            result = parse_json_response(response_text, default_value=None)
            
            # Si l'analyse a échoué, on ne propose pas d'alternative
            if not result:
                st.error("La seconde tentative d'analyse avec GPT-4o-mini a échoué. Aucun résultat disponible.")
                return None
            
            # Ajouter les charges refacturables au résultat pour l'affichage complet
            result["charges_refacturables"] = refacturable_charges
            return result
    
    except Exception as e:
        st.error(f"Erreur lors de la seconde tentative d'analyse avec GPT-4o-mini: {str(e)}")
        return None

def final_attempt_complete_analysis(text1, text2, client=None):
    """
    Tentative finale d'analyse complète avec un seul appel à GPT-4o-mini.
    Cette fonction est appelée si on veut analyser directement à partir des textes bruts.
    
    Args:
        text1: Texte du bail commercial
        text2: Texte de la reddition des charges
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse complète
    """
    try:
        with st.spinner("Analyse complète avec GPT-4o-mini en cours..."):
            # Si le client n'a pas été initialisé, essayer de le créer
            if client is None:
                try:
                    client = get_openai_client()
                except Exception as e:
                    st.error(f"Impossible d'initialiser le client OpenAI: {str(e)}")
                    return None
            
            # Utiliser un seul prompt qui fait tout en une fois
            prompt = f"""
            ## ANALYSE COMPLÈTE DE CONFORMITÉ DES CHARGES LOCATIVES
            
            Tu es un expert juridique et comptable spécialisé dans l'analyse des baux commerciaux.
            
            Voici les deux documents que tu dois analyser:
            
            ### 1. BAIL COMMERCIAL (extraits pertinents):
            ```
            {text1[:7000]}
            ```
            
            ### 2. REDDITION DES CHARGES:
            ```
            {text2[:7000]}
            ```
            
            ## Ta mission en 3 étapes:
            
            ### Étape 1: Extrais les charges refacturables mentionnées dans le bail
            - Identifie les clauses spécifiant quelles charges sont refacturables au locataire
            - Recherche les mentions de charges locatives, répartition des charges, etc.
            - Vérifie les clauses concernant l'article 606 du Code Civil
            
            ### Étape 2: Extrais les charges facturées dans la reddition
            - Identifie précisément chaque poste de charge facturé
            - Note le montant exact pour chaque poste
            - Calcule le montant total des charges facturées
            
            ### Étape 3: Analyse la conformité des charges facturées
            - Compare chaque charge facturée avec les charges autorisées par le bail
            - Détermine si chaque charge est conforme ou non aux stipulations du bail
            - Calcule un taux global de conformité
            - Identifie les charges potentiellement contestables
            
            ## Format de réponse JSON requis
            Réponds UNIQUEMENT avec ce format JSON exact:
            
            {
                "charges_refacturables": [
                    {
                        "categorie": "Type de charge",
                        "description": "Description précise",
                        "base_legale": "Article ou clause du bail"
                    }
                ],
                "charges_facturees": [
                    {
                        "poste": "Nom exact de la charge facturée",
                        "montant": montant_numérique,
                        "pourcentage": pourcentage_numérique,
                        "conformite": "conforme|à vérifier|non conforme",
                        "justification": "Explication précise",
                        "contestable": true|false,
                        "raison_contestation": "Raison si contestable"
                    }
                ],
                "montant_total": montant_total_numérique,
                "analyse_globale": {
                    "taux_conformite": pourcentage_numérique,
                    "conformite_detail": "Explication détaillée"
                },
                "recommandations": [
                    "Recommandation actionnable 1",
                    "Recommandation actionnable 2"
                ]
            }
            
            IMPORTANT: La reddition des charges inclut probablement un tableau de charges avec montants.
            Pour le document 2 (reddition), CHERCHE ATTENTIVEMENT tout tableau ou liste de charges locatives.
            Une ligne typique pourrait être "NETTOYAGE EXTERIEUR ... 3242.22 €" ou similaire.
            """
            
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1,
                max_tokens=3000,
                model="gpt-4o-mini"
            )
            
            result = parse_json_response(response_text, default_value=None)
            
            # Si l'analyse a échoué, on ne propose pas d'alternative
            if not result:
                st.error("L'analyse complète avec GPT-4o-mini a échoué. Aucun résultat disponible.")
                return None
            
            return result
            
    except Exception as e:
        st.error(f"Erreur lors de l'analyse complète avec GPT-4o-mini: {str(e)}")
        return None
