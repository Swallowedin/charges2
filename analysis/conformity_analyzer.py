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
    sans recourir à l'API OpenAI.
    
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
        
        return resultat
    
    except Exception as e:
        st.error(f"Erreur lors de l'analyse de conformité locale: {str(e)}")
        return None

def analyse_charges_conformity(refacturable_charges, charged_amounts, client):
    """
    Analyse la conformité entre les charges refacturables et les montants facturés.
    Combine analyse locale et IA.
    
    Args:
        refacturable_charges: Liste des charges refacturables selon le bail
        charged_amounts: Liste des charges facturées
        client: Client OpenAI
        
    Returns:
        Dictionnaire contenant l'analyse de conformité
    """
    try:
        with st.spinner("Analyse de la conformité des charges..."):
            # D'abord essayer l'analyse locale
            local_analysis = analyse_charges_conformity_local(refacturable_charges, charged_amounts)
            
            # Si l'analyse locale a réussi
            if local_analysis:
                return local_analysis
                
            # Sinon, recourir à l'IA
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
