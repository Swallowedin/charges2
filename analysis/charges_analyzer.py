"""
Module d'analyse des charges facturées dans la reddition des charges.
"""
import streamlit as st
from api.openai_client import send_openai_request, parse_json_response
from config import MAX_CHARGES_CHARS

def extract_charged_amounts_from_reddition(charges_text, client):
    """
    Extrait les montants des charges facturées mentionnées dans la reddition.
    
    Args:
        charges_text: Texte de la reddition des charges
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    st.write("### Analyse du relevé de charges")
    st.write("Extraction des données du relevé en cours...")
    
    prompt = f"""
    ## EXTRACTION PRÉCISE DES CHARGES LOCATIVES
    
    Le document suivant est un relevé de charges locatives refacturées au preneur.
    
    ```
    {charges_text[:MAX_CHARGES_CHARS]}
    ```
    
    ## INSTRUCTIONS
    
    1. Identifie les différentes charges dans le document qui liste les charges et leur quote-part
    2. extraits précisément
       - Le nom exact de la charge (ex: "NETTOYAGE EXTERIEUR")
       - Le montant facturé (HT et TTC si il y ales deux )
    3. Identifie également le montant TOTAL des charges en HT et TTC
    4. Continue tant que tu n'identifies pas de charges. Il y en a toujours.
    
    ATTENTION: Assure-toi que les montants sont des nombres décimaux sans symbole € ou autres caractères.
    """
    
    response_text = send_openai_request(
        client=client,
        prompt=prompt,
        temperature=0.1
    )
    
    try:
        result = parse_json_response(response_text, default_value={})
        
        if "charges" in result and isinstance(result["charges"], list):
            # Afficher un résumé formaté des charges extraites
            st.success(f"✅ Extraction réussie - {len(result['charges'])} postes de charges identifiés")
            
            # Créer un tableau récapitulatif des charges pour vérification visuelle
            import pandas as pd
            
            table_data = []
            total = 0
            
            for charge in result["charges"]:
                table_data.append([charge["poste"], f"{charge['montant']:.2f} €"])
                total += charge["montant"]
            
            # Ajouter une ligne de total
            table_data.append(["**TOTAL**", f"**{total:.2f} €**"])
            
            # Afficher le tableau
            df = pd.DataFrame(table_data, columns=["Poste de charge", "Montant"])
            st.table(df)
            
            # Format pour le reste de l'application
            formatted_charges = []
            for charge in result["charges"]:
                formatted_charges.append({
                    "poste": charge["poste"],
                    "montant": charge["montant"],
                    "texte_original": f"{charge['poste']} - {charge['montant']}€"
                })
            return formatted_charges
        else:
            st.warning("Format de réponse non standard")
            # Afficher le contenu brut pour débogage
            st.code(response_text)
            return []
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des charges: {str(e)}")
        st.code(response_text)
        return []

def extract_charged_amounts_fallback(charges_text, client):
    """
    Méthode alternative pour extraire les montants facturés en cas d'échec 
    de la méthode principale.
    
    Args:
        charges_text: Texte de la reddition des charges
        client: Client OpenAI
        
    Returns:
        Liste de dictionnaires contenant les charges facturées
    """
    prompt = f"""
    ## EXTRACTION SIMPLIFIÉE DES CHARGES LOCATIVES
    
    Ce document est un relevé de charges locatives commercial. Extrais uniquement:
    
    1. Chaque ligne de charge avec son montant exact
    2. Ignore tout autre élément qui n'est pas une charge avec un montant
    
    Document:
    ```
    {charges_text[:5000]}
    ```
    
    Format JSON requis:
    {{
      "charges": [
        {{ "poste": "Nom de la charge", "montant": montant_numérique }},
        ...
      ]
    }}
    """
    
    response_text = send_openai_request(
        client=client,
        prompt=prompt,
        temperature=0
    )
    
    result = parse_json_response(response_text, default_value={"charges": []})
    
    # Normalisation du résultat pour garantir la structure attendue
    if "charges" in result and isinstance(result["charges"], list):
        return result["charges"]
    else:
        return []
