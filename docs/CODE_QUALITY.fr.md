# Qualité du code

[Documentation](README.fr.md) · [English](CODE_QUALITY.md)

Les routes utilisent des services typés, pas le runtime global. Fichier et HTTP partagent la validation. Les choix persistés sont séparés du contenu console généré. Le runtime possède sockets, écritures engagées, pools, dialogues et extensions ; le menu natif n’est pas un second backend.

## Contrôles

Ruff couvre Python ; mypy strict couvre API/services/runtime/desktop. Le seuil de 90 % concerne leurs lignes combinées, pas chaque fichier ni les adaptateurs natifs hors de ce périmètre. Les tests couvrent contrats HTTP/TCP/UDP, transactions, appairage, extensions, cycle de vie et propriétés de parsing. Le frontend vérifie TypeScript, Vitest, build et dérive OpenAPI. Le paquet est testé hors dépôt. Les liens locaux passent par `tools/check_docs.py`.

Le [guide de test](TESTING.fr.md) décrit les contrôles automatiques ; [Qualification](QUALIFICATION.fr.md) couvre les essais natifs.

## Maintenabilité et performances

Une taille proche de 400 lignes appelle une revue, pas un découpage artificiel. Les adaptateurs natifs et l’orchestration d’extensions restent à surveiller. Préférez des dépendances explicites et étroites ; les simulations ne prouvent pas l’accord des permissions OS.

Les tests protègent les saisies contre les réponses tardives, suspendent le polling masqué, bornent le travail du menu, conservent les préférences médias et font tourner les journaux sans redémarrage.

Mesurez d’abord coût au repos, latence d’action, reconnexion et nettoyage. L’HTTP lit un état en cache ; les opérations natives/extensions/interactives ont des capacités séparées. Utilisez les [scénarios de performance](PERFORMANCE.fr.md) pour mesurer la version actuelle.

Consultez [développement](CONTRIBUTING_AGENT.fr.md), [architecture](ARCHITECTURE.fr.md) et [publication](PUBLIC_RELEASE.fr.md). Livrez comportement, tests de régression et documentation ensemble.
