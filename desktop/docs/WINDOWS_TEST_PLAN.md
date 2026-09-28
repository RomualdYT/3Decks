# Validation Windows de 3Decks

Ce document sert à la première session d'essais sur **Windows 10 et 11**. Noter
la version de Windows, l'architecture, le type de paquet installé, la version
de WebView2, le pare-feu et les périphériques audio avant chaque session.
Consigner pour chaque ligne : résultat, message affiché, journal, capture si
utile, et numéro d'issue. Tester au moins un PC x64 ; ARM64 attend un paquet
et une compilation dédiés.

## Préparation et installation

1. Compiler sur Windows avec Rust, Node.js, les prérequis Tauri 2 et
   `pnpm install --frozen-lockfile` dans `frontend/`, puis `npm ci` et
   `npm run tauri -- build` dans `desktop/`. Vérifier le paquet réellement
   produit (NSIS/MSI), sa signature et l'identité d'application.
2. Installer sur un profil Windows neuf. Vérifier lancement, désinstallation,
   icône Decky, nom 3Decks, raccourcis Start, tray et absence de console.
3. Refaire l'essai avec WebView2 absent ou obsolète, droits utilisateur
   standards et politique d'entreprise restrictive. Noter précisément le
   comportement de l'installateur.
4. Parcourir l'onboarding puis relancer après chaque étape ; vérifier reprise,
   écriture du fichier de configuration, toggles des fonctionnalités, aspect
   de l'éditeur à 100/125/150/200 % DPI et sur deux moniteurs. L'étape des
   accès doit afficher les contrôles Windows et l'état du réseau, sans texte
   macOS ni fausse demande de permission. Sur l'installateur direct, les
   notifications doivent être signalées indisponibles sans bouton d'autorisation
   inopérant. Sur un paquet avec identité compatible, vérifier le consentement,
   son refus puis sa révocation.
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
| Volume de sortie | 0, 1, 50, 100 ; +/- ; mute ; périphérique USB/Bluetooth branché puis retiré | WASAPI agit sur la sortie multimédia par défaut et l'état 3DS suit le changement. |
| Sorties audio | Plusieurs sorties actives ; changer la sortie dans Paramètres Son puis revenir dans 3Decks ; débrancher/rebrancher USB/Bluetooth | La liste MMDevice indique la sortie par défaut. Le bouton ouvre `ms-settings:sound` ; Windows applique le changement, 3Decks ne force pas l'endpoint global. |
| Volume par application | Spotify, Apple Music, VLC et navigateur GSMTC ; deux sessions audio pour un même processus ; lecteur suspendu/fermé ; sortie changée | Les contrôles de volume affectent seulement les sessions actives qui correspondent à la source GSMTC. Vérifier le volume dans le mélangeur Windows et qu'il ne modifie pas les autres apps. |
| Notifications | Tester paquet MSIX avec capacité `userNotificationListener` ; consentement accordé/refusé ; notifications conservées, supprimées puis nouvelles ; fermer et relancer 3Decks ; désactiver la fonction et révoquer l'accès | L'accès est demandé depuis l'interface. Les items encore présents dans le centre sont lus ; alertes observées conservées dans le dossier de configuration pendant 6 h (8 entrées max), y compris après relance. Désactivation ou révocation : cache local vidé, rien envoyé à la 3DS. L'installateur MSI/NSIS actuel est sans identité de paquet et doit afficher « nécessite MSIX ». |
| Micro | mute/unmute, micro intégré et USB, changement de périphérique pendant le mute | Le mute de l'entrée multimédia par défaut est restauré ; les applications avec entrée dédiée peuvent différer. |
| Session multimédia | Spotify, navigateur avec lecture, Apple Music si installé, lecteur Windows ; deux lecteurs actifs ; pause, lecture, titre suivant | GSMTC utilise la session que Windows considère prioritaire. Vérifier le nom d'app, titre, artiste, album et état lecture ; les champs manquants du lecteur restent vides. |
| Touches média | lecture/pause, piste suivante/précédente sur plusieurs lecteurs ; lecteur suspendu ou fermé | Les commandes GSMTC ciblent la session active. Si aucun lecteur n'expose de session, la commande doit retourner une erreur compréhensible. |
| Position et pochettes | démarrer, pause, avancer/reculer avec le stylet ; piste sans pochette et grande pochette | La position dépend des contrôles GSMTC publiés par le lecteur. La pochette est lue depuis sa miniature si disponible ; vérifier mise à jour à chaque changement de piste et absence de blocage réseau/UI. |
| Paroles en ligne | activer les paroles, rechercher des titres avec accents, titre/artiste ambigus, piste sans résultat | Les paroles utilisent les métadonnées GSMTC et LRCLIB. Vérifier l'état de chargement, absence de paroles et changement de piste ; cette fonctionnalité est optionnelle. |
| Raccourcis | lettres, chiffres, Échap, Entrée, Tab, Espace, Retour arrière, Suppr, flèches, Home/End, Page Up/Down, Print Screen, F1–F12 ; Ctrl/Alt/Shift/Win ; AZERTY/QWERTY ; app normale puis élevée | Les caractères sont traduits avec la disposition clavier active de la fenêtre au premier plan. UIPI peut bloquer une app élevée ; aucun modificateur ne doit rester enfoncé après une erreur. |
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

## Contraintes et distribution

- L'API publique MMDevice ne change pas la sortie par défaut. Éviter
  `IPolicyConfig` non documenté ; ouvrir plutôt les paramètres Son Windows.
- `UserNotificationListener` requiert une identité de paquet, la capacité
  `userNotificationListener` et l'accord explicite de l'utilisateur. Il donne
  les notifications conservées par Windows, pas l'historique supprimé avant que
  3Decks ait pu les observer. Ces entrées observées sont archivées localement
  pendant six heures (huit au maximum). Le MSI/NSIS Tauri actuel ne satisfait pas cette identité : intégrer MSIX ou un
  sparse package avec manifeste avant d'activer cette fonction en distribution.
- Signature Authenticode, publication et format final de l'installateur.

Tout échec lié aux droits, au pare-feu, à UIPI ou aux règles de premier plan
doit être distingué d'un crash ou d'une action silencieusement ignorée.

## Points Windows non disponibles

- Les fonctions audio et notifications doivent encore être testées sur une
  machine Windows réelle. Sans paquet MSIX doté du manifeste requis, les
  notifications sont indisponibles et l'interface doit expliquer pourquoi.
- Avant toute release, exécuter le build complet et ces essais sur Windows 10
  et 11. Le cross-build de modules Rust ne remplace pas un build Tauri natif.
