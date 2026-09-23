# Validation Windows du PoC 3Decks

Ce document sert à la première session d'essais sur **Windows 10 et 11**. Noter
la version de Windows, l'architecture, le type de paquet installé, la version
de WebView2, le pare-feu et les périphériques audio avant chaque session.
Consigner pour chaque ligne : résultat, message affiché, journal, capture si
utile, et numéro d'issue. Tester au moins un PC x64 ; ARM64 attend un paquet
et une compilation dédiés.

## Préparation et installation

1. Compiler sur Windows avec Rust, Node.js, les prérequis Tauri 2 et
   `pnpm install --frozen-lockfile` dans `agent/`, puis `npm ci` et
   `npm run tauri build` dans `desktop-poc/`. Vérifier le paquet réellement
   produit (NSIS/MSI), sa signature et l'identité d'application.
2. Installer sur un profil Windows neuf. Vérifier lancement, désinstallation,
   icône Decky, nom 3Decks, raccourcis Start, tray et absence de console.
3. Refaire l'essai avec WebView2 absent ou obsolète, droits utilisateur
   standards et politique d'entreprise restrictive. Noter précisément le
   comportement de l'installateur.
4. Parcourir l'onboarding puis relancer après chaque étape ; vérifier reprise,
   écriture du fichier de configuration, toggles des fonctionnalités, aspect
   de l'éditeur à 100/125/150/200 % DPI et sur deux moniteurs.
5. Fermer la fenêtre : le serveur doit rester accessible depuis le tray.
   Tester ouvrir/masquer, quitter, démarrage avec la session, redémarrage et
   veille/réveil. Vérifier que l'éditeur reprend sa taille et sa position.

## Réseau et 3DS

- Autoriser puis refuser le pare-feu à l'application ; vérifier l'annonce UDP
  38122, la connexion TCP 38123 et les messages utiles à l'utilisateur.
- Tester Wi-Fi seul, Ethernet seul, VPN actif, plusieurs cartes, changement de
  réseau, veille/réveil, perte de Wi-Fi et reconnexion automatique.
- Appairer une 3DS neuve, redémarrer les deux appareils, révoquer son jeton,
  refaire l'appairage et vérifier que le code n'est pas réutilisable.
- Éditer des pages, sauvegarder, changer de page depuis la console et vérifier
  les trames de configuration, les actions et leurs erreurs côté 3DS.
- Tester OBS WebSocket avec mot de passe correct/incorrect et serveur absent.

## Actions système natives

| Fonction | Essais requis | Résultat attendu / limites actuelles |
| --- | --- | --- |
| Volume de sortie | 0, 1, 50, 100 ; +/- ; mute ; périphérique USB/Bluetooth branché puis retiré | WASAPI agit sur la sortie multimédia par défaut et l'état 3DS suit le changement. La sélection de sortie n'est pas portée. |
| Micro | mute/unmute, micro intégré et USB, changement de périphérique pendant le mute | Le mute de l'entrée multimédia par défaut est restauré ; les applications avec entrée dédiée peuvent différer. |
| Touches média | lecture/pause, piste suivante/précédente avec Spotify, navigateur et Musique Windows | `SendInput` atteint le lecteur choisi par Windows. Métadonnées et pochette Windows ne sont pas portées. |
| Raccourcis | lettre et chiffre, Ctrl/Alt/Shift/Win, disposition AZERTY/QWERTY, app normale puis élevée | Le raccourci atteint l'app au premier plan ; UIPI peut bloquer l'app élevée. Aucun modificateur ne reste enfoncé après une erreur. |
| Ouvrir | `.exe`, nom d'application, URL HTTP(S), fichier, dossier, chemin avec espaces et caractères non ASCII, cible inexistante | `ShellExecuteW` utilise l'association Windows. Une cible introuvable produit une erreur visible. |
| Fermer l'app | app simple, plusieurs fenêtres, document non enregistré, app réduite, app en tray, processus élevé, deux apps de même nom | `WM_CLOSE` demande une fermeture normale aux fenêtres du processus correspondant ; l'app peut confirmer, refuser ou rester active. Aucun processus n'est tué de force. |
| Fenêtres | fenêtres multiples, minimisées, deux moniteurs, UWP, app élevée, fenêtre disparue avant clic | La liste contient les fenêtres visibles de bureau ; `SetForegroundWindow` peut être refusé par Windows. Erreur explicite si l'activation échoue. |
| Verrouiller | session locale puis session RDP | `LockWorkStation` verrouille la session courante sans fermer 3Decks. |

## Extensions, données et distribution

- Charger un paquet d'extension natif Windows x64 approuvé, vérifier les
  actions/sources/écrans, les délais, le rejet d'un binaire non approuvé et le
  redémarrage du processus d'extension après erreur.
- Vérifier les données de configuration et les secrets après mise à niveau,
  désinstallation/réinstallation et changement de compte Windows.
- Vérifier la mise à jour **signée** depuis GitHub Releases sur une version de
  préproduction : téléchargement, vérification, fermeture/reprise, migration
  des données et rollback manuel si nécessaire. Ne pas activer l'updater sans
  clé publique et artefacts signés.
- Mesurer RAM au démarrage, fenêtre fermée/tray, deux 3DS connectées et éditeur
  ouvert ; mesurer CPU au repos et lors du polling. Le seuil de 35 Mo reste un
  objectif à mesurer, pas une propriété démontrée.

## Fonctions à concevoir avant la parité Windows

- Choix de la sortie audio par défaut : l'API publique MMDevice énumère les
  périphériques mais ne fournit pas de commande documentée pour changer le
  périphérique système par défaut. Éviter `IPolicyConfig` non documenté.
- Volume d'application, état du lecteur, métadonnées et pochettes : étudier
  WASAPI sessions et `GlobalSystemMediaTransportControlsSessionManager`, puis
  valider les capacités/permissions et l'identité du paquet installé.
- Historique des notifications d'autres applications : étudier WinRT
  `UserNotificationListener` et les exigences de manifeste avant d'annoncer la
  fonctionnalité. Aucun historique global n'est livré actuellement.
- Signature Authenticode, publication et format final de l'installateur.

Tout échec lié aux droits, au pare-feu, à UIPI ou aux règles de premier plan
doit être distingué d'un crash ou d'une action silencieusement ignorée.
