# État des plateformes de l’application Tauri

Cette matrice décrit ce que le code implémente aujourd'hui. « Implémenté » ne
signifie pas encore validé sur une machine de chaque plateforme. Les actions
liées aux systèmes sont isolées sous `src-tauri/src/platform/macos/` et
`src-tauri/src/platform/windows/`; `platform/system.rs` orchestre les actions
communes sans exposer les types Cocoa, COM ou WinRT au protocole réseau.

| Fonction | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Fenêtre Tauri, éditeur React, menu et tray | Implémenté ; validation visuelle finale requise | Code partagé, essai Windows requis | Code partagé, essai Linux requis |
| TCP 3DS, découverte UDP, appairage, configuration, OBS WebSocket, télémétrie | Implémenté | Code partagé, essai Windows requis | Code partagé, essai Linux requis |
| Extensions natives | Hôte Rust + SDK | Code partagé, essai Windows requis | Code partagé, essai Linux requis |
| Audio système et micro | CoreAudio natif | WASAPI/COM natif | Non porté |
| Contrôle multimédia, métadonnées et position | Apple Events/MediaRemote selon le lecteur ; validation sur les lecteurs requis | WinRT GSMTC : session active, métadonnées, commandes, position et pochette quand le lecteur les fournit | Non porté |
| Volume du lecteur | Spotify/Music si disponible | WASAPI sessions du lecteur GSMTC actif ; à valider sur Windows | Non porté |
| Pochettes média et paroles en ligne | Adaptateur média + conversion Rust commune | Miniature GSMTC + conversion Rust commune ; paroles LRCLIB activables | Non porté |
| Sorties audio | CoreAudio : liste et sélection | MMDevice : liste/default ; ouverture des réglages Son Windows pour changer la sortie | Non porté |
| Lancer/quitter une app | `NSWorkspace`/`NSRunningApplication` | `ShellExecuteW` / demande de fermeture `WM_CLOSE` | Non porté |
| Raccourcis système | Quartz, touches spéciales et disposition active | `SendInput`, touches spéciales et touches caractères selon la disposition Windows | Non porté |
| URL, chemins, verrouiller la session | `NSWorkspace` / Quartz | `ShellExecuteW` / `LockWorkStation` | Non porté |
| Liste et activation des fenêtres | CoreGraphics + Accessibilité/Apple Events | `EnumWindows` + `SetForegroundWindow` ; refus possible par Windows | Non porté |
| Notifications des autres applications | Lecture SQLite `usernoted`, format non documenté | WinRT UserNotificationListener ; consentement requis, historique local borné des alertes observées | Non porté ; D-Bus ne fournit pas d'historique global standard |
| Installateur, signature et mises à jour vérifiées | DMG local ; chaîne CI candidate écrite, clés et notarisation à configurer et valider | Chaîne CI candidate écrite ; signature et installation à valider sur Windows | Packaging différé |

## Architecture native

Les fichiers sous `platform/macos/` contiennent les adaptateurs Cocoa, Quartz,
CoreAudio et Apple Events. `platform/windows/` contient les adaptateurs WASAPI,
WinRT GSMTC, `SendInput`, fenêtres, shell et processus. Les opérations bloquantes
passent par `tokio::task::spawn_blocking`; les objets système ne quittent pas
leur adaptateur. `platform/system.rs` conserve le contrat commun des actions,
et `platform/audio.rs` sélectionne l'implémentation selon la cible de compilation.

La conversion des pochettes est partagée et écrite en Rust : décodage borné,
redimensionnement et format de transport sont identiques sur macOS et Windows.
La source des octets reste propre à chaque système. Les notifications privées
macOS ne deviennent pas une API portable par le seul usage de Cocoa.

## Limites de validation Windows

Le code Windows n'a pas encore été exécuté sur Windows. Les adaptateurs Windows
et `platform/system.rs` passent un `cargo check --tests` croisé isolé avec la
cible GNU. La compilation Tauri complète n'a pas été vérifiée dans cet
environnement : elle est bloquée par l'absence du compilateur MinGW requis par
une dépendance native. Les comportements GSMTC varient selon le
lecteur et la session Windows active ; les essais réels listés dans
[`docs/WINDOWS_TEST_PLAN.md`](docs/WINDOWS_TEST_PLAN.md) restent nécessaires.

Les raccourcis synthétiques peuvent être bloqués par UIPI lorsqu'une application
cible tourne avec des privilèges plus élevés. `SetForegroundWindow` peut aussi
être refusé par la politique de premier plan Windows. Windows ne fournit pas
d'API publique documentée pour changer la sortie par défaut : 3Decks liste les
sorties actives et ouvre les réglages Son pour laisser l'utilisateur choisir.
Le volume applicatif cible les sessions WASAPI du processus correspondant au
lecteur GSMTC actif. Les notifications nécessitent une identité de paquet et la
capacité `userNotificationListener` ; le paquet MSI/NSIS actuel ne les rend pas
disponibles. Les notifications observées sont conservées localement six heures,
avec une limite de huit entrées, dans le dossier de configuration de 3Decks.
La désactivation de la fonction ou le retrait de l'autorisation efface ce cache.

## Références Windows

- [Session GSMTC active](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmanager.getcurrentsession)
- [Métadonnées de session](https://learn.microsoft.com/en-us/uwp/api/windows.media.control.globalsystemmediatransportcontrolssessionmediaproperties)
- [Entrée clavier et `SendInput`](https://learn.microsoft.com/en-us/windows/win32/inputdev/keyboard-input)
- [Sessions audio WASAPI](https://learn.microsoft.com/en-us/windows/win32/coreaudio/audio-sessions)
- [Volume des sessions audio](https://learn.microsoft.com/en-us/windows/win32/coreaudio/volume-controls)
- [Obtenir la sortie audio par défaut](https://learn.microsoft.com/en-us/windows/win32/coreaudio/getting-the-default-device-endpoint-for-streaming)
- [Notifications utilisateur Windows](https://learn.microsoft.com/en-us/windows/apps/develop/notifications/app-notifications/notification-listener)
