"""
Module amélioré d'analyse de la conformité entre les charges refacturables et les montants facturés.
Focus sur la précision et la robustesse de l'analyse juridique.
"""
import streamlit as st
import json
import re
from api.openai_client import get_openai_client, send_openai_request, parse_json_response
from config import DEFAULT_CONFORMITY_LEVEL

def standardize_charge_names(charges):
    """
    Standardise les noms des charges pour faciliter la comparaison.
    
    Args:
        charges: Liste de charges à standardiser
        
    Returns:
        Liste de charges avec noms standardisés
    """
    standardized = []
    
    for charge in charges:
        # Copier la charge
        std_charge = charge.copy()
        
        # Standardiser le nom/poste de la charge
        if "poste" in std_charge:
            name = std_charge["poste"]
        elif "categorie" in std_charge:
            name = std_charge["categorie"]
        else:
            name = ""
            
        # Convertir en minuscules
        name = name.lower()
        
        # Supprimer les caractères spéciaux et accents
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Remplacer les espaces multiples par un seul
        name = re.sub(r'\s+', ' ', name)
        
        # Supprimer les mots vides comme "de", "du", "la", etc.
        stop_words = ["de", "du", "la", "le", "les", "des", "un", "une", "et", "ou", "a", "au", "aux"]
        for word in stop_words:
            name = re.sub(r'\b' + word + r'\b', '', name)
            
        # Supprimer les espaces en début et fin
        name = name.strip()
        
        # Ajouter la version standardisée
        std_charge["standardized_name"] = name
        standardized.append(std_charge)
    
    return standardized

def find_similar_charges(refacturable_charges, charged_amounts):
    """
    Trouve les correspondances entre charges refacturables et charges facturées.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        
    Returns:
        Dictionnaire des correspondances
    """
    # Standardiser les noms
    std_refacturable = standardize_charge_names(refacturable_charges)
    std_charged = standardize_charge_names(charged_amounts)
    
    # Dictionnaire pour stocker les correspondances
    matches = {}
    
    # Pour chaque charge facturée, trouver les refacturables correspondantes
    for charged in std_charged:
        charged_name = charged["standardized_name"]
        matches[charged_name] = []
        
        # Chercher des correspondances exactes ou partielles
        for refac in std_refacturable:
            refac_name = refac["standardized_name"]
            
            # Calculer un score de similarité simple
            similarity = 0
            
            # Correspondance exacte
            if charged_name == refac_name:
                similarity = 1.0
            # Inclusion d'une chaîne dans l'autre
            elif charged_name in refac_name or refac_name in charged_name:
                # Plus longue sous-chaîne commune
                common_length = max(len(s) for s in [charged_name.split(), refac_name.split()] if s in charged_name and s in refac_name)
                similarity = common_length / max(len(charged_name), len(refac_name))
            # Mots communs
            else:
                charged_words = set(charged_name.split())
                refac_words = set(refac_name.split())
                common_words = charged_words.intersection(refac_words)
                
                if common_words:
                    similarity = len(common_words) / max(len(charged_words), len(refac_words))
            
            # Si similarité suffisante, ajouter à la liste des correspondances
            if similarity > 0.3:  # Seuil arbitraire
                matches[charged_name].append({
                    "refacturable": refac,
                    "similarity": similarity
                })
        
        # Trier par similarité décroissante
        matches[charged_name].sort(key=lambda x: x["similarity"], reverse=True)
    
    return matches

def evaluate_charge_conformity(charged_amount, matching_refacturables):
    """
    Évalue la conformité d'une charge facturée par rapport aux charges refacturables.
    
    Args:
        charged_amount: Charge facturée
        matching_refacturables: Liste des charges refacturables correspondantes
        
    Returns:
        Dictionnaire avec évaluation de conformité
    """
    # Si aucune correspondance, la charge est potentiellement non conforme
    if not matching_refacturables:
        return {
            "conformite": "non conforme",
            "justification": "Aucune charge correspondante trouvée dans le bail",
            "contestable": True,
            "raison_contestation": "Charge non prévue explicitement dans le bail"
        }
    
    # Si une correspondance avec similarité élevée
    best_match = matching_refacturables[0]
    if best_match["similarity"] > 0.8:
        return {
            "conformite": "conforme",
            "justification": f"Correspondance directe avec la charge refacturable '{best_match['refacturable'].get('categorie', '')}'",
            "contestable": False,
            "raison_contestation": ""
        }
    
    # Si une correspondance avec similarité moyenne
    if best_match["similarity"] > 0.5:
        return {
            "conformite": "à vérifier",
            "justification": f"Correspondance partielle avec la charge refacturable '{best_match['refacturable'].get('categorie', '')}'",
            "contestable": False,
            "raison_contestation": "Vérifier si la charge entre bien dans cette catégorie"
        }
    
    # Correspondance faible
    return {
        "conformite": "à vérifier",
        "justification": f"Correspondance faible avec la charge refacturable '{best_match['refacturable'].get('categorie', '')}'",
        "contestable": True,
        "raison_contestation": "Correspondance insuffisante avec les charges prévues dans le bail"
    }

def analyse_charges_conformity_local(refacturable_charges, charged_amounts):
    """
    Analyse la conformité entre les charges refacturables et les montants facturés
    sans recourir à l'API OpenAI. Cette fonction sert de secours en cas d'indisponibilité de l'API.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
        # Trouver les correspondances entre charges refacturables et facturées
        charge_matches = find_similar_charges(refacturable_charges, charged_amounts)
        
        # Calculer le montant total
        montant_total = sum(charge.get("montant", 0) for charge in charged_amounts)
        
        # Analyser chaque charge facturée
        charges_analysees = []
        
        for charge in charged_amounts:
            # Obtenir le nom standardisé
            std_name = standardize_charge_names([charge])[0]["standardized_name"]
            
            # Obtenir les correspondances
            matches = charge_matches.get(std_name, [])
            
            # Évaluer la conformité
            evaluation = evaluate_charge_conformity(charge, matches)
            
            # Calculer le pourcentage
            pourcentage = (charge.get("montant", 0) / montant_total * 100) if montant_total > 0 else 0
            
            # Créer l'entrée d'analyse
            charge_analysee = {
                "poste": charge.get("poste", ""),
                "montant": charge.get("montant", 0),
                "pourcentage": pourcentage,
                "conformite": evaluation["conformite"],
                "justification": evaluation["justification"],
                "contestable": evaluation["contestable"],
                "raison_contestation": evaluation["raison_contestation"]
            }
            
            charges_analysees.append(charge_analysee)
        
        # Calculer le taux global de conformité
        charges_conformes = [c for c in charges_analysees if c["conformite"] == "conforme"]
        montant_conforme = sum(c["montant"] for c in charges_conformes)
        taux_conformite = (montant_conforme / montant_total * 100) if montant_total > 0 else 0
        
        # Générer les recommandations
        recommandations = []
        
        # Si des charges sont contestables
        charges_contestables = [c for c in charges_analysees if c["contestable"]]
        if charges_contestables:
            montant_contestable = sum(c["montant"] for c in charges_contestables)
            recommandations.append(
                f"Vérifier ou contester les {len(charges_contestables)} charges potentiellement non conformes, "
                f"représentant {montant_contestable:.2f}€ ({montant_contestable/montant_total*100:.1f}% du total)."
            )
            
            # Recommandations spécifiques pour les charges importantes
            charges_importantes = [c for c in charges_contestables if c["pourcentage"] > 5]
            for charge in charges_importantes:
                recommandations.append(
                    f"Examiner spécifiquement la charge '{charge['poste']}' ({charge['montant']:.2f}€) : {charge['raison_contestation']}"
                )
        
        # Recommandation générale si le taux de conformité est bas
        if taux_conformite < 70:
            recommandations.append(
                "Demander au bailleur une justification détaillée de la répartition des charges, "
                "car le taux de conformité global est inférieur à 70%."
            )
        
        # Constituer le résultat final
        resultat = {
            "charges_refacturables": refacturable_charges,
            "charges_facturees": charges_analysees,
            "montant_total": montant_total,
            "analyse_globale": {
                "taux_conformite": round(taux_conformite),
                "conformite_detail": (
                    f"Sur un total de {montant_total:.2f}€ de charges facturées, "
                    f"{montant_conforme:.2f}€ ({round(taux_conformite)}%) sont clairement conformes au bail. "
                    f"{len(charges_contestables)} charges représentant {sum(c['montant'] for c in charges_contestables):.2f}€ "
                    f"sont potentiellement contestables."
                )
            },
            "recommandations": recommandations
        }
        
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
        }at
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse de conformité locale: {str(e)}")
        return None

def analyse_charges_conformity(refacturable_charges, charged_amounts, client):
    """
    Analyse la conformité entre les charges refacturables et les montants facturés.
    Cette fonction utilise prioritairement GPT-4o-mini pour l'analyse.
    
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
            
            # Utiliser GPT-4o-mini comme modèle par défaut
            response_text = send_openai_request(
                client=client,
                prompt=prompt,
                temperature=0.1,
                model="gpt-4o-mini"  # Spécifier explicitement GPT-4o-mini
            )
            
            result = parse_json_response(response_text, default_value={})
            
            # Ajouter les charges refacturables au résultat pour l'affichage complet
            if result:
                result["charges_refacturables"] = refacturable_charges
                return result
            else:
                # En cas d'échec avec GPT-4o-mini, utiliser l'analyse locale comme secours
                st.warning("Analyse avec GPT-4o-mini non réussie. Tentative avec méthode alternative...")
                local_result = analyse_charges_conformity_local(refacturable_charges, charged_amounts)
                
                if local_result:
                    return local_result
                else:
                    # Structure minimale en cas d'échec total
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
        st.error(f"Erreur lors de l'analyse de conformité avec GPT-4o-mini: {str(e)}")
        
        # En cas d'erreur avec GPT-4o-mini, essayer l'analyse locale
        try:
            st.warning("Problème avec l'API OpenAI. Tentative d'analyse locale...")
            local_result = analyse_charges_conformity_local(refacturable_charges, charged_amounts)
            if local_result:
                return local_result
        except:
            pass
            
        # Structure minimale en cas d'échec total
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
    Utilise toujours GPT-4o-mini mais avec un prompt reformulé.
    
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
            temperature=0.1,
            model="gpt-4o-mini"  # Utiliser explicitement GPT-4o-mini
        )
        
        result = parse_json_response(response_text, default_value={})
        
        # Ajouter les charges refacturables au résultat pour l'affichage complet
        if result:
            result["charges_refacturables"] = refacturable_charges
            return result
        else:
            # Dernière tentative avec format simplifié
            st.warning("Second essai non concluant. Tentative avec format simplifié...")
            return simplify_and_retry_conformity(refacturable_charges, charged_amounts, client)
    
    except Exception as e:
        st.error(f"Erreur lors de la seconde tentative d'analyse de conformité: {str(e)}")
        
        # Tenter l'analyse locale comme dernier recours
        local_result = analyse_charges_conformity_local(refacturable_charges, charged_amounts)
        if local_result:
            return local_result
            
        # Structure minimale en cas d'échec total
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
    Utilise GPT-4o-mini avec un prompt très simplifié.
    
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
            temperature=0,
            model="gpt-4o-mini"  # Utiliser explicitement GPT-4o-mini
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
    Utilise GPT-4o-mini ou GPT-4o si disponible.
    
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
        
        # Essayer avec un modèle plus puissant si possible
        try:
            model = "gpt-4o-mini"  # Utiliser GPT-4o-mini par défaut
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
