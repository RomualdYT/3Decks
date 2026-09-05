# 3Decks : une application locale PC–3DS

[Documentation](README.fr.md) · [English](LOCAL_APP.md)

L'architecture actuelle convient à cet usage : le PC exécute un agent unique, la 3DS lui parle directement sur le réseau local et l'éditeur React utilise une API accessible uniquement depuis ce PC. FastAPI est embarqué dans l'agent, pas un serveur supplémentaire que l'utilisateur doit installer ou administrer.

## Les limites à conserver

- Un seul processus agent et une seule boucle événementielle. Les processus d'extensions et de dialogues sont des ressources locales contrôlées, pas des services à déployer.
- L'HTTP de configuration écoute uniquement sur `127.0.0.1`. Il ne sert pas à transporter les appuis de la console : ceux-ci passent par le TCP existant.
- Pas de compte distant, service cloud, base de données, Redis ni workers HTTP multiples.
- La configuration reste un fichier ; les extensions restent à côté de ce fichier. L'interface et ses images/polices sont fournies localement.
- La sécurité de l'API locale reste utile : une page web malveillante ne doit pas pouvoir modifier la configuration ou exécuter une action locale. Session, Host, Origin et limites ne sont pas supprimés pour gagner quelques microsecondes.
- Les appels natifs lents restent hors de la boucle qui traite les messages de la console.

FastAPI n'est pas indispensable à toute application locale. Ici, ses contrats typés, son export OpenAPI et ses protections testées permettent de conserver une API maintenable. Revenir à un parseur HTTP maison ne serait pas justifié par les seules différences de quelques millisecondes mesurées.

## Priorité produit : masquer la technique

Le wheel est la source de vérité de la distribution. Les lanceurs GitHub vérifient ce wheel, installent un Python privé avec `uv`, initialisent seulement un profil absent et créent un raccourci sans terminal. Une future application autonome pourra réutiliser le même backend. L’icône désormais intégrée à la barre des menus/zone de notification fournit le point d’entrée permanent : état de connexion, suspension, réglages rapides, diagnostic, démarrage de session, redémarrage et arrêt.

Le menu natif n’est pas un second agent. Il conserve la boucle graphique sur le
thread principal exigé par macOS/Windows et exécute l’unique boucle `asyncio` du
runtime dans un thread dédié. Les échanges passent par des instantanés
immuables et `run_coroutine_threadsafe`; aucune route HTTP ne dépend du menu.
Les changements rapides passent par la transaction de configuration existante,
et l’éditeur recharge une révision externe seulement s’il n’a aucune saisie non
enregistrée.

L'éditeur actuel s'ouvre dans le navigateur local. Une fenêtre native embarquant une vue web est une possibilité distincte, pas une obligation pour utiliser React ou FastAPI. Elle ne doit pas imposer un second backend ou démarrer plusieurs agents.

Windows nécessite toujours l'identité et les permissions MSIX pour les notifications ; les permissions macOS doivent être qualifiées avec l'identité réellement distribuée. Le workflow Store produit un artefact MSIX non signé depuis le même wheel, exclusivement destiné à Partner Center. Aucun contournement de permissions n'est ajouté.

Pour ce produit, consommation **au repos**, réactivité des actions natives, reconnexion, fiabilité de l'arrêt et simplicité d'installation comptent davantage qu'un classement de débit HTTP. Les mesures ci-dessous ne remplacent pas un essai natif au repos avec médias et extensions activés.

## Optimisation effectuée

L'état destiné à l'éditeur était copié profondément par le fournisseur de snapshot, puis à nouveau lors de l'assemblage de la réponse. Le runtime fournit désormais une vue interne empruntée ; le service effectue **une seule copie complète à la frontière de sortie**, de manière synchrone.

La méthode publique `last_state_payload()` continue à fournir une copie indépendante pour ses autres consommateurs. La validation Pydantic de la réponse reste active. Aucun cache temporel de réponse HTTP n'a été ajouté : notifications, musique, appairage et état des extensions restent immédiatement relus depuis l'état courant en mémoire.

Quatre tests vérifient :

1. Une seule copie de chaque nœud du snapshot par lecture.
2. L'indépendance des médias, notifications, métadonnées et aperçus d'extensions retournés.
3. La fraîcheur des lectures suivantes et la stabilité d'une réponse précédente.
4. La réutilisation effective d'une connexion HTTP, avec authentification à chaque requête et `no-store`.

## Résultats mesurés

[données complètes avant/après](performance/local-state-2026-08-31.json), macOS arm64 / Python 3.12.12.

État synthétique de **11 075 octets** : huit applications, six sorties audio, quatre notifications, une piste média, vingt lignes de journal et quatre extensions avec aperçus et listes. Aucun processus d'extension ni adaptateur natif réel n'est utilisé.

Le microbenchmark réalise sept séries de 1 000 lectures. Les tests réseau réalisent cinq cycles de 400 requêtes HTTP avec quatre clients et 100 ping/pong TCP par cycle. Les valeurs HTTP sont les médianes des médianes/p95 de chaque cycle, pas des percentiles globaux.

| Mesure | Avant | Après |
|---|---:|---:|
| Préparation d'état, sans réseau ni validation HTTP | 323,356 µs | 283,992 µs |
| HTTP persistant, médiane | 2,666 ms | 2,527 ms |
| HTTP persistant, p95 typique | 3,485 ms | 3,387 ms |
| HTTP nouvelles connexions, médiane | 3,116 ms | 3,228 ms |
| HTTP nouvelles connexions, p95 typique | 3,902 ms | 3,714 ms |
| Ping TCP sous charge HTTP persistante, p95 typique | 2,977 ms | 2,780 ms |
| Ping TCP sous charge HTTP nouvelles connexions, p95 typique | 0,545 ms | 1,403 ms |
| Retard de boucle sous HTTP persistant, p95 typique | 1,284 ms | 1,544 ms |
| Retard de boucle sous nouvelles connexions, p95 typique | 1,835 ms | 1,563 ms |
| Tâches restantes après chaque arrêt | 0 | 0 |
| Threads après chaque arrêt, principal compris | 1 | 1 |

Le gain isolé de préparation d'état est d'environ **12,2 %**. En revanche, les différences réseau sont modestes et certains indicateurs se dégradent dans cette série ; elles ne permettent pas d'affirmer une accélération générale. L'ordonnancement des requêtes en rafale influence aussi le moment où les pings sont traités. Il faut conserver ces chiffres, pas sélectionner uniquement les améliorations.

La connexion persistante était **déjà prise en charge** par Uvicorn ; elle est désormais mesurée et testée. Elle utilise quatre connexions pour 400 requêtes, contre 400 connexions dans l'autre scénario. Le benchmark ne reproduit pas la cadence réelle de l'éditeur ni le Wi-Fi de la console.

Le [bilan initial de migration](QUALIFICATION.fr.md) utilisait un état minimal et un lecteur HTTP différent : ne pas comparer directement ses millisecondes aux séries chargées de cette page. Les mesures mémoire initiales sont des allocations Python instrumentées, pas la consommation RAM totale du PC.

### Reproduire les mesures finales

Depuis `agent/`, sans compilation/tests simultanés :

```sh
uv run --locked python -m tools.benchmark_state
uv run --locked python tools/benchmark_runtime.py --populated
uv run --locked python tools/benchmark_runtime.py --populated --keep-alive
```

Les outils affichent leurs mesures sans démarrer l'agent personnel ni lire son fichier de configuration. Les simulations sont communes à macOS/Windows ; les chiffres ci-dessus proviennent seulement du Mac de qualification.
