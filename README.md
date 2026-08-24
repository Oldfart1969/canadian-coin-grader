# Canadian Coin Grader V2 — Reference-Calibrated

Cette V2 améliore le prototype initial en ajoutant un index de **473 images de référence gradées** couvrant 1¢, 5¢, 10¢, 25¢, 50¢ et 1 dollar. Les métadonnées proviennent des noms des images de référence fournies (année, dénomination, grade).

## Nouveautés
- moteur hybride: heuristiques visuelles + comparaison KNN avec références canadiennes;
- préférence pour les références de même dénomination et d'époque proche;
- barrière AU58/MS60 afin de réduire les faux «Mint State»;
- estimation séparée avers/revers et limite imposée par la face plus faible;
- comparables les plus proches affichés;
- confiance tenant compte de la qualité photo et de la proximité aux références.

## Lancer
```bash
pip install -r requirements.txt
streamlit run app_v2.py
```

## Important
Ce logiciel reste un outil expérimental. Une photo ne permet pas d'évaluer parfaitement le lustre cartwheel, les hairlines, le nettoyage, les altérations de surface ou l'authenticité. Il ne remplace pas ICCS/PCGS/NGC.
