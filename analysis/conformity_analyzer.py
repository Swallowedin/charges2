"""
Module d'analyse de la conformité entre les charges refacturables et les montants facturés.
"""
import streamlit as st
import json
from api.openai_client import send_openai_request, parse_json_response
from config import DEFAULT_CONFORMITY_LEVEL

def analyse_charges_conformity(refacturable_charges, charged_amounts, client):
    """
    Analyse la conformité entre les charges refacturables et les montants facturés.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
        with st.spinner("Analyse de la conformité des charges..."):
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
            
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1
            )
            
            result = parse_json_response(response_text, default_value={})
            
            # Ajouter les charges refacturables au résultat pour l'affichage complet
            if result:
                result["charges_refacturables"] = refacturable_charges
                return result
            else:
                # En cas d'échec du parsing, retourner une structure minimale
                return {
                    "charges_refacturables": refacturable_charges,
                    "charges_facturees": charged_amounts,
                    "montant_total": sum(charge.get("montant", 0) for charge in charged_amounts),
                    "analyse_globale": {
                        "taux_conformite": DEFAULT_CONFORMITY_LEVEL,
                        "conformite_detail": "Impossible d'analyser la conformité en raison d'une erreur."
                    },
                    "recommandations": ["Vérifier manuellement la conformité des charges."]
                }
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse de conformité: {str(e)}")
        return {
            "charges_refacturables": refacturable_charges,
            "charges_facturees": charged_amounts,
            "montant_total": sum(charge.get("montant", 0) for charge in charged_amounts),
            "analyse_globale": {
                "taux_conformite": DEFAULT_CONFORMITY_LEVEL,
                "conformite_detail": "Impossible d'analyser la conformité en raison d'une erreur."
            },
            "recommandations": ["Vérifier manuellement la conformité des charges."]
        }

def retry_analyse_conformity(refacturable_charges, charged_amounts, client):
    """
    Seconde tentative d'analyse de conformité avec un prompt différent.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
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
            temperature=0.1
        )
        
        result = parse_json_response(response_text, default_value={})
        
        # Ajouter les charges refacturables au résultat pour l'affichage complet
        if result:
            result["charges_refacturables"] = refacturable_charges
            return result
        else:
            # Dernière tentative avec format simplifié
            return simplify_and_retry_conformity(refacturable_charges, charged_amounts, client)
        
    except Exception as e:
        st.error(f"Erreur lors de la seconde tentative d'analyse de conformité: {str(e)}")
        return {
            "charges_refacturables": refacturable_charges,
            "charges_facturees": charged_amounts,
            "montant_total": sum(charge.get("montant", 0) for charge in charged_amounts),
            "analyse_globale": {
                "taux_conformite": DEFAULT_CONFORMITY_LEVEL,
                "conformite_detail": "Analyse partielle suite à une erreur technique."
            },
            "recommandations": ["Consulter un expert pour une analyse plus approfondie."]
        }

def simplify_and_retry_conformity(refacturable_charges, charged_amounts, client):
    """
    Dernière tentative d'analyse de conformité avec un format simplifié.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité simplifiée
    """
    try:
        # Simplifier les données d'entrée
        simple_refacturable = []
        for charge in refacturable_charges:
            simple_refacturable.append({
                "categorie": charge.get("categorie", ""),
                "description": charge.get("description", "")
            })
        
        simple_charged = []
        for charge in charged_amounts:
            simple_charged.append({
                "poste": charge.get("poste", ""),
                "montant": charge.get("montant", 0)
            })
        
        # Prompt simplifié
        prompt = f"""
        Analyse si ces charges facturées sont conformes au bail:
        
        Charges refacturables selon bail: {json.dumps(simple_refacturable)}
        
        Charges facturées: {json.dumps(simple_charged)}
        
        Donne un simple JSON avec:
        1. Taux de conformité (%)
        2. Liste des charges conformes ou non
        3. Recommandations
        """
        
        response_text = send_openai_request(
            client=client,
            prompt=prompt,
            temperature=0
        )
        
        result = parse_json_response(response_text, default_value={
            "taux_conformite": DEFAULT_CONFORMITY_LEVEL,
            "detail": "Analyse simplifiée suite à des erreurs techniques.",
            "recommandations": ["Consulter un expert pour une analyse complète."]
        })
        
        # Construire un résultat structuré à partir de la réponse
        structured_result = {
            "charges_refacturables": refacturable_charges,
            "charges_facturees": [],
            "montant_total": sum(charge.get("montant", 0) for charge in charged_amounts),
            "analyse_globale": {
                "taux_conformite": result.get("taux_conformite", DEFAULT_CONFORMITY_LEVEL),
                "conformite_detail": result.get("detail", "Analyse simplifiée suite à des erreurs techniques.")
            },
            "recommandations": result.get("recommandations", ["Consulter un expert pour une analyse complète."])
        }
        
        # Restructurer les charges facturées
        if "charges" in result and isinstance(result["charges"], list):
            for i, charge in enumerate(charged_amounts):
                if i < len(result["charges"]):
                    structured_result["charges_facturees"].append({
                        "poste": charge.get("poste", ""),
                        "montant": charge.get("montant", 0),
                        "pourcentage": (charge.get("montant", 0) / structured_result["montant_total"] * 100) if structured_result["montant_total"] > 0 else 0,
                        "conformite": result["charges"][i].get("conformite", "à vérifier"),
                        "justification": result["charges"][i].get("justification", ""),
                        "contestable": result["charges"][i].get("conformite", "") == "non conforme",
                        "raison_contestation": result["charges"][i].get("justification", "")
                    })
                else:
                    # Pour les charges sans évaluation explicite
                    structured_result["charges_facturees"].append({
                        "poste": charge.get("poste", ""),
                        "montant": charge.get("montant", 0),
                        "pourcentage": (charge.get("montant", 0) / structured_result["montant_total"] * 100) if structured_result["montant_total"] > 0 else 0,
                        "conformite": "à vérifier",
                        "justification": "Analyse incomplète",
                        "contestable": False,
                        "raison_contestation": ""
                    })
        else:
            # Ajouter les charges telles quelles si pas d'évaluation disponible
            for charge in charged_amounts:
                structured_result["charges_facturees"].append({
                    "poste": charge.get("poste", ""),
                    "montant": charge.get("montant", 0),
                    "pourcentage": (charge.get("montant", 0) / structured_result["montant_total"] * 100) if structured_result["montant_total"] > 0 else 0,
                    "conformite": "à vérifier",
                    "justification": "Analyse incomplète",
                    "contestable": False,
                    "raison_contestation": ""
                })
        
        return structured_result
        
    except Exception as e:
        st.error(f"Erreur lors de la tentative simplifiée d'analyse de conformité: {str(e)}")
        # Résultat minimal de secours
        return {
            "charges_refacturables": refacturable_charges,
            "charges_facturees": charged_amounts,
            "montant_total": sum(charge.get("montant", 0) for charge in charged_amounts),
            "analyse_globale": {
                "taux_conformite": DEFAULT_CONFORMITY_LEVEL,
                "conformite_detail": "Analyse incomplète suite à des erreurs techniques répétées."
            },
            "recommandations": ["Consulter un expert pour une analyse complète des charges."]
        }

def final_attempt_complete_analysis(text1, text2, client=None):
    """
    Tentative finale d'analyse complète avec un seul appel IA intégré.
    Cette fonction est appelée en dernier recours si les autres approches échouent.
    
    Args:
        text1: Texte du bail commercial
        text2: Texte de la reddition des charges
        client: Client OpenAI (peut être None)
        
    Returns:
        Dictionnaire contenant l'analyse complète
    """
    try:
        st.warning("Tentative d'analyse unifiée en cours...")
        
        # Si le client n'a pas été initialisé, essayer de le créer
        if client is None:
            try:
                client = get_openai_client()
            except Exception as e:
                st.error(f"Impossible d'initialiser le client OpenAI: {str(e)}")
                # Retourner une structure vide
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
        
        {{
            "charges_refacturables": [
                {{
                    "categorie": "Type de charge",
                    "description": "Description précise",
                    "base_legale": "Article ou clause du bail"
                }}
            ],
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
        
        IMPORTANT: La reddition des charges inclut probablement un tableau de charges avec montants.
        Pour le document 2 (reddition), CHERCHE ATTENTIVEMENT tout tableau ou liste de charges locatives.
        Une ligne typique pourrait être "NETTOYAGE EXTERIEUR ... 3242.22 €" ou similaire.
        """
        
        # Essayer avec un modèle plus puissant si possible
        try:
            model = "gpt-4o" if any(m.id == "gpt-4o" for m in client.models.list().data) else "gpt-4o-mini"
        except:
            model = "gpt-4o-mini"
            
        response_text = send_openai_request(
            client=client,
            prompt=prompt,
            temperature=0.1,
            max_tokens=3000,
            model=model
        )
        
        result = parse_json_response(response_text, default_value={})
        
        # Vérification basique de la structure
        if "charges_facturees" not in result or not result["charges_facturees"]:
            st.warning("Aucune charge facturée identifiée dans l'analyse unifiée. Tentative de récupération spécifique...")
            
            # Extraction spécifique des charges facturées
            charges_prompt = f"""
            Extrais UNIQUEMENT la liste des charges facturées et leurs montants exacts de ce document de reddition:
            
            ```
            {text2[:10000]}
            ```
            
            ATTENTION: Ce document contient certainement un tableau de charges. Chaque ligne du tableau
            représente une charge avec un montant. Par exemple: "NETTOYAGE EXTERIEUR ... 3242.22 €"
            
            Fournis UNIQUEMENT un tableau JSON simple:
            [
                {{"poste": "Nom exact du poste", "montant": montant_numérique}},
                ...
            ]
            """
            
            charges_response = send_openai_request(
                client=client,
                prompt=charges_prompt,
                temperature=0,
                model=model
            )
            
            charges_result = parse_json_response(charges_response, default_value=[])
            
            # Récupérer les charges depuis la réponse
            extracted_charges = []
            if isinstance(charges_result, list):
                extracted_charges = charges_result
            else:
                for key in charges_result:
                    if isinstance(charges_result[key], list):
                        extracted_charges = charges_result[key]
                        break
            
            # Si des charges ont été trouvées, mettre à jour le résultat
            if extracted_charges:
                total = sum(charge.get("montant", 0) for charge in extracted_charges)
                
                # Calculer les pourcentages
                for charge in extracted_charges:
                    charge["pourcentage"] = (charge.get("montant", 0) / total * 100) if total > 0 else 0
                    charge["conformite"] = "à vérifier"
                    charge["contestable"] = False
                    charge["justification"] = "Analyse incomplète"
                    charge["raison_contestation"] = ""
                
                result["charges_facturees"] = extracted_charges
                result["montant_total"] = total
                
                # Mettre à jour l'analyse globale
                if "analyse_globale" not in result:
                    result["analyse_globale"] = {}
                
                result["analyse_globale"]["taux_conformite"] = DEFAULT_CONFORMITY_LEVEL
                result["analyse_globale"]["conformite_detail"] = "Analyse partielle des charges facturées. Vérification manuelle recommandée."
        
        return result
            
    except Exception as e:
        st.error(f"Erreur lors de la tentative finale d'analyse: {str(e)}")
        return {
            "charges_refacturables": [],
            "charges_facturees": [],
            "montant_total": 0,
            "analyse_globale": {
                "taux_conformite": 0,
                "conformite_detail": "L'analyse a échoué suite à une erreur technique. Veuillez réessayer."
            },
            "recommandations": [
                "Réessayer l'analyse avec des documents au format texte.",
                "S'assurer que les documents sont lisibles et contiennent les informations nécessaires."
            ]
        }
