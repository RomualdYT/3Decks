# Bilan de qualification

[Documentation](README.fr.md) · [English](QUALIFICATION.md) · [Publication](PUBLIC_RELEASE.fr.md)

## Passe de stabilisation du 5 septembre 2026

Ces résultats décrivent le code testé à cette date, pas une certification automatique des commits suivants.

| Contrôle | Résultat local |
|---|---|
| Python macOS/3.12 | 533 tests et 80 sous-tests réussis |
| Couverture API/services/runtime/desktop | 91,92 % globalement ; seuil 90 %, pas une garantie par fichier |
| Qualité | Ruff et mypy strict sur 38 modules réussis |
| Frontend | 17 tests Vitest, TypeScript et build réussis |
| Contrats | OpenAPI et types générés concordants |
| Distribution | Wheel/sdist construits ; CLI, assets, HTTP, TCP et extension testés hors dépôt |
| Menu macOS réel | Démarrage temporaire, disponibilité UI, arrêt CLI coopératif et nettoyage vérifiés |
| Configuration publique | Document courant et cinq versions historiques sans anomalie dans les catégories inspectées |
| CI distante | Préparée ; matrice complète non déclarée exécutée ici |
| Windows natif/MSIX | Reste à qualifier |

Les tests protègent notamment les saisies face aux réponses lentes, les onglets masqués, les préférences médias, l’absence de fchmod Windows, la rotation UTF-8, les opérations bornées et l’arrêt propre. Les autres contrats couvrent transactions, processus, protocoles et extensions avec des adaptateurs simulés.

## Endurance courte et performances

Essai de 30 secondes avec adaptateur fictif : **183 reconnexions, 9 sauvegardes, ping maximal 0,89 ms**, croissance tracée 0,201 Mio et pic 0,594 Mio. Aucun worker `3decks-` restant ; deux threads au total dans le processus.

Ce n’est ni une mesure RSS, ni une mesure Wi-Fi sur 3DS, ni un essai de quatre heures.

```sh
# Depuis agent/
uv run --locked python tools/endurance_agent.py --duration 30 --slow-action-ms 100 --quiet
```

Les [mesures initiales](performance/fastapi-2026-08-31.json) et [mesures chargées](performance/local-state-2026-08-31.json) sont historiques et non directement comparables. La référence initiale donnait un p95 HTTP typique de 1,008 ms contre 1,803 ms avec FastAPI ; **FastAPI n’était pas plus rapide**. Les bénéfices portent sur les contrats et le cycle de vie. Une série instrumentée conservait 18,742 à 18,763 Mio sur cinq cycles après correction d’une rétention. Voir les tableaux, hypothèses et commandes détaillés dans la [référence anglaise](QUALIFICATION.md).

## Avant publication

- [ ] Matrice distante complète sur le commit candidat.
- [ ] Installation macOS/Windows, toutes les vues, polices, PNG et responsive.
- [ ] Création/sauvegarde/conflits, capture clavier, tri des pages et réglages rapides.
- [ ] Permissions macOS avec le Python distribué, notifications, Spotify/Musique, dialogues et OBS.
- [ ] Actions/médias/dialogues Windows et notifications MSIX : refus puis accord.
- [ ] Vraie 3DS : découverte, appairage/révocation, FR/EN, veille/réveil et reconnexion.
- [ ] Extension : import, approbation, configuration, activation/retrait et affichage console.
- [ ] Arrêt pendant sauvegarde, dialogue et extension lente ; processus résiduels.
- [ ] Ouverture de session, second lancement, redémarrage, mise à jour, retrait et retour arrière.

Les vérifications ciblées antérieures ne remplacent pas cette passe complète. Rejouez également les audits de dépendances : aucun résultat historique ne garantit l’absence actuelle de vulnérabilité.
