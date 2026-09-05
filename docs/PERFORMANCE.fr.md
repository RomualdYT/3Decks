# Mesurer les performances

[Documentation](README.fr.md) · [English](PERFORMANCE.md)

Pour cette application locale, privilégiez coût au repos, réactivité des actions, reconnexion et arrêt propre. Le débit HTTP n’est pas un score produit.

Depuis `agent/`, sans compilation ni autre benchmark en parallèle :

```sh
uv run --locked python -m tools.benchmark_state
uv run --locked python tools/benchmark_runtime.py --cycles 5 --requests 400 --populated --keep-alive
uv run --locked python tools/benchmark_runtime.py --cycles 5 --requests 400 --trace-memory
uv run --locked python tools/endurance_agent.py --duration 30 --slow-action-ms 100 --quiet
```

La préparation d’état est isolée du réseau. Le scénario runtime combine HTTP/TCP loopback réels et état fictif ; il mesure démarrage, latence, retard de boucle et ressources restantes. Le traçage mémoire est séparé : allocations Python ne signifie pas RAM totale/RSS, et l’instrumentation influence les temps.

L’endurance exerce reconnexions, sauvegardes et travail lent. Elle dure quatre heures par défaut ; indiquez une durée courte pour un contrôle rapide. Ces outils ciblent uniquement le code actuel, sans profil personnel ni collecte native. Le rapport runtime est du JSON sur stdout.

Notez commit, OS/Python, scénario, connexions et instrumentation. Comparez le même travail, conservez les valeurs atypiques et ne confondez pas percentiles par cycle et globaux. Trente secondes ne prouvent pas plusieurs heures de stabilité ; le loopback ne mesure ni le Wi-Fi 3DS ni Spotify/OBS réel.

Les tests contrôlent structure du rapport et nettoyage, pas des seuils de vitesse dépendants du runner. Avant livraison, mesurez aussi le repos avec le véritable interpréteur et les intégrations actives. Conservez protections HTTP et ressources bornées. Voir [qualification](QUALIFICATION.fr.md).
