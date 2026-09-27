# Contribuer à 3Decks

[Documentation](README.fr.md) · [English](CONTRIBUTING_AGENT.md)

## Environnement

Utilisez Python 3.12–3.14, uv, Node.js 24 et pnpm 11.19.0. Depuis `agent/` :

```sh
uv sync --locked
pnpm install --frozen-lockfile
pnpm build
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds-ui --config config.local.json
```

Ne répétez pas l’initialisation si le fichier existe. Gardez `--config` pour éviter de modifier la démonstration suivie. Python/uv suffisent si les assets compilés sont déjà fournis ; Node sert à construire l’éditeur.

## Frontend

Arrêtez l’agent précédent avant de relancer avec le proxy de développement :

```sh
uv run --locked deck3ds --config config.local.json --ui --ui-dev-origin http://127.0.0.1:4173
```

Dans un second terminal, depuis `agent/`, lancez `pnpm dev`. Ouvrez le port 4173 avec le jeton de la **nouvelle session UI**, pas celui de la console. Vite relaie `/api` vers 38124 ; si ce port change, adaptez le proxy. Ne rendez jamais les contrôles Host/Origin permissifs pour résoudre un problème de développement.

## Vérifications

```sh
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
uv run --locked pytest --cov --cov-report=term-missing
pnpm api:check
pnpm typecheck
pnpm test:frontend
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py
```

Depuis la racine : `python3 tools/check_docs.py`, puis `./build.sh` pour la 3DS avec Docker/devkitPro. Le résultat est `3ds-app/deck3ds.3dsx`. Copiez-le sur SD ou utilisez `python3 tools/send3ds.py` lorsque Homebrew Launcher attend un transfert 3dslink. Un transfert mémoire ne remplace pas le fichier installé sur SD.

## Ajouter un comportement

Placez la logique dans un service indépendant de FastAPI, puis une route mince avec contrats typés et erreurs stables. Ajoutez tests métier/HTTP, cas d’erreur, annulation et arrêt. Régénérez OpenAPI et TypeScript ensemble ; les règles métier restent dans le validateur partagé.

Les lectures en cache restent synchrones sur la boucle ; les appels bloquants utilisent le pool borné adapté. Un timeout ne termine pas forcément le thread. Les dialogues passent par les processus possédés.

Pour une intégration indépendante, préférez [API 1](EXTENSIONS.fr.md). Pour une intégration native, complétez catalogue, dispatcher et adaptateurs de plateforme avec tests simulés Mac/Windows. Ne lancez jamais de code d’extension non approuvé.

## Livrer

Gardez `pyproject.toml` et `uv.lock` cohérents. Mypy et le seuil global 90 % couvrent API/services/runtime/desktop ; Ruff couvre Python. Une taille proche de 400 lignes appelle une revue, pas un découpage artificiel.

La CI cible les trois OS et Python 3.12–3.14 ; Linux valide le cœur portable seulement. Suivez [publication](PUBLIC_RELEASE.fr.md) et [qualification native](QUALIFICATION.fr.md). La [référence anglaise](CONTRIBUTING_AGENT.md) détaille les points d’extension du code.
