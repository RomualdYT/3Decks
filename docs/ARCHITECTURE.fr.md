# Architecture de l’application

[Documentation](README.fr.md) · [English](ARCHITECTURE.md)

3Decks comprend l’application de bureau Tauri et le client C sur la 3DS. Le processus de bureau héberge le serveur réseau local, les intégrations système, la configuration et le menu système. Sa WebView affiche l’éditeur React ; fermer cette fenêtre laisse le processus et la connexion à la console actifs.

## Repères dans le code

| Dossier | Responsabilité |
|---|---|
| [`frontend/src/`](../frontend/src/) | Éditeur, réglages, traductions, composants et types de l’API |
| [`desktop/src/`](../desktop/src/) | Entrée Tauri, assistant initial, adaptateur de commandes et styles |
| [`desktop/src-tauri/src/app/`](../desktop/src-tauri/src/app/) | Configuration, appairage, progression de l’assistant, fenêtres et menu système |
| [`desktop/src-tauri/src/transport/`](../desktop/src-tauri/src/transport/) | Découverte UDP, sessions TCP et messages 3DS |
| [`desktop/src-tauri/src/features/`](../desktop/src-tauri/src/features/) | OBS, paroles, pochettes, télémétrie, notifications et extensions |
| [`desktop/src-tauri/src/platform/`](../desktop/src-tauri/src/platform/) | Adaptateurs audio, clavier, médias, fenêtres et système par OS |
| [`3ds-app/source/`](../3ds-app/source/) | Interface console, entrées, réseau et protocole |

L’éditeur utilise la frontière typée `frontend/src/api/client.ts`. Dans le build de bureau, elle aboutit à `desktop/src/tauri-api.ts`, qui appelle les commandes Rust. L’adaptateur HTTP du frontend est isolé pour développer l’éditeur partagé et n’est pas inclus dans le paquet Tauri. Une nouvelle fonction de bureau doit passer par l’adaptateur Rust plutôt que par un appel HTTP ajouté au composant React.

## Connexion et état

1. Le bureau lance des tâches Tokio pour la découverte UDP sur 38122 et le serveur TCP sur 38123, indépendamment de la WebView.
2. La console découvre l’ordinateur ou utilise une adresse saisie manuellement. Chaque message TCP contient une longueur JSON sur quatre octets big-endian, puis le JSON. Le [protocole](PROTOCOL.fr.md) précise les limites et les messages.
3. Une nouvelle console saisit le code à six chiffres de l’application. Le bureau conserve un identifiant propre à cette console dans ses données locales ; une console reconnue se reconnecte avec lui.
4. Le bureau valide l’action, appelle l’adaptateur concerné et renvoie l’état ou le résultat. L’enregistrement d’une page augmente la révision et diffuse la nouvelle disposition aux consoles connectées.

Le réseau doit être de confiance : le transport n’est pas chiffré. Voir [Sécurité](SECURITY.fr.md). La configuration et la progression de l’assistant sont stockées séparément. L’assistant reprend à l’étape enregistrée après une relance.

## Frontières des plateformes

Le flux commun se trouve dans `features/` ou `platform/system.rs` ; les appels propres aux OS restent sous `platform/macos/` et `platform/windows/`. Les opérations bloquantes utilisent le pool de tâches bloquantes de Tokio lorsque nécessaire. macOS utilise CoreAudio, Quartz et Apple Events. Windows utilise WASAPI, GSMTC, WinRT, `SendInput` et les API Win32. Les limites sont précisées dans la [matrice des plateformes](../desktop/PLATFORM_STATUS.md) et le [plan d’essais Windows](../desktop/docs/WINDOWS_TEST_PLAN.md). La distribution Linux viendra plus tard.

Les extensions natives sont des paquets approuvés utilisant un protocole JSON Lines borné. Leur [SDK](../desktop/extension-sdk/README.md) définit le manifeste et le cycle de vie. Elles s’exécutent avec les droits de l’utilisateur.

## Builds et mises à jour

Le [workflow qualité](../.github/workflows/quality.yml) vérifie l’éditeur, Rust, la documentation et la console. Un tag de version lance le [workflow de release candidate](../.github/workflows/release.yml) et crée une Release GitHub en brouillon. Le [workflow de publication](../.github/workflows/publish-release.yml) revérifie les artefacts puis publie le brouillon après revue. Dans les réglages, l’utilisateur peut demander une recherche de mise à jour : l’application lit `latest.json` sur GitHub, vérifie la signature, installe et redémarre. La clé publique doit être intégrée lors du build de release. Voir la [procédure de publication](RELEASE.md) et ses validations restantes.
