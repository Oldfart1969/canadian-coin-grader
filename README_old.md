
# Canadian Coin Grader — prototype

Prototype Streamlit pour estimer photographiquement le grade d'une pièce de monnaie canadienne à partir d'au moins deux photos (avers + revers).

## Ce que fait cette version
- Téléversement d'un avers et d'un revers.
- Identification manuelle de la dénomination, de l'année et du type de frappe.
- Analyse locale de netteté, contraste, texture/surface, marques et proxy de lustre.
- Estimation sur l'échelle numismatique 1–70 avec préfixes EF/AU/MS, ou PL/SP/PR lorsque pertinent.
- Fourchette plausible et niveau de confiance lié à la qualité des photos.
- Aucun envoi automatique des photos vers un serveur externe.

## Important
Le moteur fourni est un **prototype heuristique**, pas encore un modèle entraîné sur des dizaines de milliers de pièces certifiées. Il permet de tester l'application et le parcours utilisateur, mais son grade ne doit pas être assimilé à une certification ICCS, PCGS ou NGC.

Un grade professionnel dépend aussi d'éléments difficiles à capter sur deux photos fixes : mouvement du lustre, hairlines, nettoyage, altérations, authenticité, strike weakness, toning, problèmes de surface et eye appeal.

## Installation

Python 3.10+ recommandé.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Phase suivante recommandée : vrai modèle IA

1. Constituer un corpus sous licence/permission avec, pour chaque pièce :
   - avers;
   - revers;
   - dénomination;
   - année/variété;
   - type de frappe;
   - service de grading;
   - grade numérique;
   - désignations (Cameo, Red, etc.);
   - provenance.
2. Dédupliquer les mêmes pièces apparaissant sur plusieurs sites.
3. Séparer l'identification de la pièce et le grading.
4. Entraîner un modèle multi-vues (avers + revers), idéalement par série/dessin.
5. Utiliser une perte ordinale : MS-64 est plus proche de MS-63 que de VF-20.
6. Calibrer les probabilités et retourner une distribution, p. ex. MS-63 22 %, MS-64 55 %, MS-65 19 %.
7. Ajouter un détecteur de problèmes : cleaned, scratched, damaged, altered, questionable color.
8. Tester contre un jeu fermé de pièces certifiées jamais vues à l'entraînement.

## Sources de référence repérées
Voir `reference_sources.csv`. Le fichier contient uniquement des métadonnées et des liens; aucune image tierce n'est redistribuée avec le prototype.
