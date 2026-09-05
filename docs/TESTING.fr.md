# Tester 3Decks

[Documentation](README.fr.md) · [English](TESTING.md)

Les tests décrivent le comportement supporté, pas l’histoire du développement.

## Commandes

Depuis `agent/` :

```sh
uv sync --locked
uv run --locked pytest --cov --cov-report=term-missing
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:frontend
pnpm api:check
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py
```

Depuis la racine : `python3 tools/check_docs.py`, `python3 -m unittest discover -s tools -p test_check_docs.py` et `./build.sh` (Docker/devkitPro).

## Organisation

Les tests HTTP vérifient les vraies réponses ASGI et complètent les essais Uvicorn. Le catalogue a ses propres tests métier : capacités, limites et libellés FR/EN. Les autres fichiers couvrent configuration/transactions, services/runtime, TCP/UDP, adaptateurs natifs, menu système, extensions et distribution. La [table anglaise](TESTING.md#test-responsibilities) donne le détail des fichiers.

Les interactions React se testent avec Vitest près du hook/composant, pas en cherchant des chaînes dans son code depuis Python. Les catalogues et contrats générés peuvent nécessiter des contrôles de cohérence entre composants.

## Règles

Utilisez plateformes fictives, fichiers temporaires, sockets loopback et processus contrôlés. Aucun test par défaut ne doit utiliser votre profil, lancer vos applications, changer vos permissions ou piloter une vraie console.

Les secrets et chemins de test sont fictifs. Gardez la capture standard pytest ; ne masquez pas les échecs. Les tests de journaux capturent leur sortie. Les benchmarks ne lisent pas votre configuration personnelle.

Un test doit nommer un contrat et vérifier son résultat : valeurs, état, erreur stable ou nettoyage. Paramétrez les variantes utiles. Ne testez pas la disparition d’anciens modules, la mise en forme ou les commentaires. Gardez la compatibilité encore réellement supportée.

Préférez les codes d’erreur au texte incident ; les tests de traduction peuvent vérifier FR/EN explicitement. Le nettoyage doit fonctionner même si le test échoue. Un timeout ne prouve pas qu’un thread est arrêté.

Le seuil combiné API/services/runtime/desktop reste **90 %**, sans abaissement pour réorganiser les tests. Comptage et couverture ne remplacent pas la pertinence. Les essais OS et console physiques restent dans la [qualification native](QUALIFICATION.fr.md).
