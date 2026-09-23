# État des plateformes du PoC Tauri

Cette matrice décrit le **code actuel**, pas une promesse de parité. Elle doit
être revue avec des builds et des essais sur chaque OS avant publication.

| Fonction | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Fenêtre Tauri, éditeur React, barre de menus/tray, onboarding | Implémenté, testé sur macOS | Code multiplateforme, essai requis | Code multiplateforme, essai requis |
| TCP 3DS, découverte UDP, appairage, configuration, OBS WebSocket, télémétrie | Implémenté | Code multiplateforme, essai requis | Code multiplateforme, essai requis |
| Extensions natives | Hôte Rust + SDK, binaire par architecture | Code multiplateforme, essai requis | Code multiplateforme, essai requis |
| Audio système et micro | CoreAudio natif ; validation sur périphériques variés requise | WASAPI/COM natif ; essai Windows requis | Non porté |
| Lecture multimédia | Commandes Spotify/Music par Apple Events natifs ; métadonnées et pochettes encore via AppleScript | Touches multimédia `SendInput`, sans métadonnées | Non porté |
| Sorties audio | CoreAudio natif | Non porté | Non porté |
| Lancer/quitter une app | `NSWorkspace`/`NSRunningApplication` natifs | Lancement via `ShellExecuteW` ; fermeture gracieuse demandée par `WM_CLOSE` | Non porté |
| Raccourcis, URL/chemins, verrouiller la session | Raccourcis et verrouillage via Quartz avec disposition clavier active ; URL/chemins via `NSWorkspace` | Raccourcis et touches média via `SendInput`, URL/chemins/app via `ShellExecuteW`, verrouillage via `LockWorkStation` ; essai Windows requis | Non porté |
| Liste et activation des fenêtres | CoreGraphics + Accessibilité/AppleScript | `EnumWindows` + `SetForegroundWindow` ; refus de premier plan possible, essai Windows requis | Non porté |
| Lecture des notifications d'autres applications | SQLite `usernoted` en lecture seule, format non documenté | Non porté ; nécessite une étude WinRT/package identity | Non porté ; D-Bus standard ne donne pas d'historique global |
| Pochettes média | Spotify/Apple Music via adaptateur macOS | Non porté | Non porté |
| Installateur, signature, mise à jour vérifiée | Bundle local ; chaîne de signature à finaliser | Packaging/signature non testés | Packaging/signature non testés |

Les capacités non implémentées sont marquées indisponibles dans le catalogue
et retournent une erreur explicite. Il serait trompeur de dire que Windows et
Linux sont « portés » aujourd'hui.

## Architecture cible

`transport/`, `app/` et l'API d'extensions restent communs. Les contrôles audio
passent par `platform/audio.rs` vers CoreAudio ou `platform/win32/audio.rs`.
Les opérations shell Windows vivent dans `platform/win32/shell.rs`, les entrées
dans `platform/win32/keyboard.rs`, et l'énumération des fenêtres dans
`platform/windowing.rs`. Les capacités remontent
à l'éditeur depuis l'adaptateur réellement disponible, puis les tests
d'intégration couvrent chaque OS en CI et sur matériel.

Sur macOS, poursuivre **AppKit/Cocoa** progressivement là où l'adaptateur actuel
appelle `osascript` : Accessibilité pour l'activation de fenêtres et Apple Events
pour les propriétés de lecteur et pochettes. CoreAudio, Quartz et Apple Events
et `NSWorkspace` couvrent maintenant l'audio système, les URL/fichiers et le
lancement/arrêt d'applications. La fenêtre et le tray restent gérés par Tauri, qui utilise déjà
les primitives natives macOS. Cocoa est une couche d'intégration macOS, pas un
nouveau frontend ni un remplacement de Tauri.

La lecture de la base privée `usernoted` reste un risque distinct : Cocoa ne
fournit pas automatiquement l'historique des notifications des autres apps.
Éviter de promettre cette fonction sur Windows/Linux avant d'avoir validé les
permissions, l'identité de package et le modèle de distribution correspondant.

Le module Windows a été vérifié par `cargo check --target x86_64-pc-windows-gnu`
dans un petit crate de contrôle qui importe les adaptateurs et `system.rs`.
Le build Tauri complet exige un compilateur MinGW ou une CI Windows ; aucun
essai d'exécution Windows n'a encore été fait. `SendInput` peut être refusé
pour une application élevée (UIPI). L'appareil de sortie WASAPI est sélectionné
avec le rôle multimédia ; la politique de changement de sortie reste à définir.
Windows limite aussi `SetForegroundWindow` selon le processus au premier plan.
Voir [le plan de validation Windows](docs/WINDOWS_TEST_PLAN.md) avant publication.
