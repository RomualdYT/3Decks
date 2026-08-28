# Qualité technique de 3Decks

État établi après la refonte de l’agent et du frontend d’août 2026.

## Ce qui a été amélioré

- Les notifications sont isolées par plateforme dans `platforms/macos_notifications.py` et `platforms/windows_notifications.py`. Windows utilise exclusivement les API Windows.
- La collecte des fenêtres macOS et les lecteurs Apple Music/Spotify sont sortis de l’adaptateur principal.
- Les fonctionnalités activables sont décrites par un catalogue commun au backend et à l’interface, ce qui évite deux listes divergentes.
- Le frontend est une application React TypeScript découpée par vue, composants, API, état et utilitaires.
- Les sources de l’agent sont séparées explicitement entre `agent/backend` et `agent/frontend`, tout en conservant la commande `python3 -m deck3ds`.
- Le tri des pages repose sur `dnd-kit` avec capteurs pointeur et clavier, au lieu des événements HTML natifs.
- La console et le frontend utilisent désormais la même famille Inter ; le build 3DS suit aussi les changements du fichier de police embarqué.
- Les vues Éditeur, Réglages et État sont chargées à la demande. Le bundle monolithique de 723 kB a été remplacé par un shell de 405 kB et des chunks de vue indépendants.
- Les contrôles de formulaire partagent des composants typés (`TextControl`, `SelectControl`, `ComboControl`, `NumberControl`) au lieu de variantes locales.
- Les intégrations spécifiques (OBS, applications détectées, couleurs, icônes, fonctionnalités média) sont présentées par des composants dédiés et testables.

## Validation actuelle

```text
Python : 319 tests
Frontend : 5 tests Vitest
TypeScript : vérification stricte sans erreur
Ruff : aucune erreur
Build Vite : production, code splitting actif
```

## Points chauds restants

Ces points ne bloquent pas la version actuelle, mais constituent le meilleur ordre pour une prochaine passe technique.

| Priorité | Zone | Constat | Refactor conseillé |
|---|---|---|---|
| Haute | `platforms/windows.py` | Environ 970 lignes ; `get_media` concentre WinRT, PowerShell, décodage et cache de pochette. | Créer un `WindowsMediaProvider`, symétrique à `MacMediaProvider`. |
| Haute | `config.py` | Environ 980 lignes regroupant modèles, validation, parsing et sérialisation. | Séparer modèles, parseurs de boutons/pages et migrations de révision. |
| Moyenne | `platforms/macos.py` | Le snapshot orchestre encore plusieurs sources système. | Extraire un collecteur d’état système et limiter l’adaptateur à la coordination. |
| Moyenne | `ui/api.py` | La construction du schéma reste impérative et volumineuse. | Décrire limites et options dans des structures déclaratives sérialisables. |
| Basse | Tests frontend | Les utilitaires sont couverts, les parcours visuels reposent encore sur la QA navigateur. | Ajouter des tests de composants pour l’éditeur, les réglages et la barre d’enregistrement. |

## Garde-fous recommandés

À exécuter avant chaque livraison :

```bash
cd agent
ruff check backend/deck3ds deck3ds tests
python3 -m pytest -q
pnpm typecheck
pnpm test:frontend
pnpm build
```

La priorité doit rester la lisibilité : extraire lorsqu’un module mélange plusieurs responsabilités, mais éviter les couches abstraites qui ne servent qu’un seul appel simple.
