# 06 — Backlog d'Exécution & Tâches pour les Agents

Ce document répartit les tâches à accomplir entre différents agents spécialisés. Chaque tâche dispose de critères d'acceptation précis pour faciliter la relecture et la validation indépendante.

---

## 🏗️ Pôle 1 : Ingénieur Système macOS & Packaging (Agent Système)
*Rôle : Création du bundle `.app`, structure des fichiers, script de génération d'icônes, signature.*

- [ ] **Tâche 1.1 — Générateur d'icônes `3Decks.icns`**
  - **Fichier** : `tools/generate_macos_icon.sh`
  - **Détail** : Script bash utilisant `sips` et `iconutil` pour générer toutes les résolutions Retina (16x16 jusqu'à 512x512@2x) à partir de `agent/frontend/public/3decks-logo.png`.
  - **Critère de succès** : Le fichier `3Decks.icns` s'ouvre proprement dans Aperçu avec toutes ses couches sans artefact.

- [ ] **Tâche 1.2 — Modèle `Info.plist` & Entitlements**
  - **Fichiers** : `packaging/macos/Info.plist`, `packaging/macos/entitlements.plist`
  - **Détail** : Configuration de l'identifiant `com.romualdyt.3decks`, du mode barre de menus (`LSUIElement=true`), et des descriptions d'autorisations Apple Events et réseau local.
  - **Critère de succès** : `plutil -lint packaging/macos/Info.plist` retourne `OK`.

- [ ] **Tâche 1.3 — Script d'assemblage `tools/package_macos_app.sh`**
  - **Détail** : Assemblage d'un bundle `3Decks.app` complet prêt à l'emploi. Signature ad-hoc avec `codesign --force --deep --sign -`.
  - **Critère de succès** : Le bundle créé est immédiatement reconnu dans Finder avec son icône officielle et son nom.

---

## 🎨 Pôle 2 : Développeur Cocoa / Interface Native (Agent UI)
*Rôle : Gestion de la barre des menus et de la fenêtre WebKit native.*

- [ ] **Tâche 2.1 — Contrôleur de Barre des Menus (`NSStatusItem`)**
  - **Fichier** : `agent/backend/deck3ds/desktop/tray.py` ou module natif Cocoa.
  - **Détail** : Amélioration de l'icône de statut avec indicateurs de couleur dynamiques (connecté/attente/pause) et actions du menu contextuel.
  - **Critère de succès** : L'icône change d'état dès qu'une 3DS se connecte ou se déconnecte.

- [ ] **Tâche 2.2 — Fenêtre de Configuration Dédiée (`WKWebView`)**
  - **Détail** : Création d'une fenêtre native macOS avec `WKWebView` pour remplacer l'ouverture dans le navigateur externe. Barre de titre intégrée avec boutons de contrôle natifs.
  - **Critère de succès** : Cliquer sur « Ouvrir le configurateur » ouvre la fenêtre dédiée instantanément sans ouvrir Safari ou Chrome. La fermeture de la fenêtre masque simplement la vue sans couper l'agent.

---

## 🔒 Pôle 3 : Sécurité & Permissions TCC (Agent Sécurité)
*Rôle : Fluidité de l'onboarding et validation des autorisations macOS.*

- [ ] **Tâche 3.1 — Détecteur d'accès temps réel pour les Notifications**
  - **Fichier** : `agent/backend/deck3ds/platforms/macos_notifications.py`
  - **Détail** : Vérification non bloquante de la lecture sur `~/Library/Group Containers/group.com.apple.usernoted/db2/db`.
  - **Critère de succès** : Dès que l'utilisateur accorde l'Accès complet au disque à `3Decks.app` dans les Réglages Système, le statut passe immédiatement à « Actif » sans nécessiter de redémarrer l'application.

- [ ] **Tâche 3.2 — Validation du dialogue d'ouverture directe des réglages**
  - **Détail** : Le bouton dans l'interface ouvre la section exacte `Privacy_AllFiles` dans Réglages Système avec un message guidé mentionnant bien **3Decks**.
  - **Critère de succès** : `3Decks` apparaît dans la liste des applications pouvant être cochées.

---

## 🚀 Pôle 4 : DevOps & Distribution (Agent CI/CD)
*Rôle : Automatisation GitHub Actions et production des images disque `.dmg`.*

- [ ] **Tâche 4.1 — Créateur d'image disque `.dmg`**
  - **Fichier** : `tools/create_dmg.sh`
  - **Détail** : Script de création d'une image disque `.dmg` avec lien symbolique vers `/Applications` pour une installation par glisser-déposer.
  - **Critère de succès** : Le montage du `.dmg` affiche l'application et le dossier Applications côte à côte.

- [ ] **Tâche 4.2 — Workflow GitHub Actions macOS**
  - **Fichier** : `.github/workflows/macos-app.yml`
  - **Détail** : Intégration du build du `.app` et du `.dmg` dans la CI sur chaque push et release.
  - **Critère de succès** : La CI produit un artefact `.dmg` téléchargeable et testable.

---

## 🔮 Pôle 5 : Recherche & Prototypage Cœur Rust (Agent V2 / Performance)
*Rôle : Préparation de la transition long terme vers Tauri 2.0.*

- [ ] **Tâche 5.1 — Benchmark de faisabilité Tauri 2.0**
  - **Détail** : Évaluation d'un module Rust minimal pour la gestion du socket TCP 3DS avec le protocole binaire actuel (4 octets de taille + JSON).
  - **Critère de succès** : Mesure de la consommation mémoire au repos (< 30 MB) et de la latence de traitement des paquets.

---

## 🪟 Pôle 6 : Ingénieur Windows & Packaging (Agent Windows)
*Rôle : Expérience native sans console, intégration MSIX et fenêtre WebView2.*

- [ ] **Tâche 6.1 — Binaire Win32 sans console (`3Decks.exe`)**
  - **Fichier** : `packaging/windows/launcher.c`
  - **Détail** : Compilation du lanceur C avec `CREATE_NO_WINDOW` pour éliminer l'invite de commande noire.
  - **Critère de succès** : Double-cliquer sur `3Decks.exe` lance l'agent avec uniquement l'icône dans la zone de notification (System Tray).

- [ ] **Tâche 6.2 — Fenêtre native Windows WebView2**
  - **Détail** : Remplacer l'ouverture du navigateur par une fenêtre native Windows exploitant Microsoft Edge WebView2.
  - **Critère de succès** : L'éditeur s'ouvre dans une fenêtre d'application Windows avec sa propre icône dans la barre des tâches.

- [ ] **Tâche 6.3 — Packaging MSIX & Déblocage des Notifications**
  - **Fichier** : `packaging/windows/build-store-package.ps1`
  - **Détail** : Fournir l'identité de package requise pour débloquer `UserNotificationListener` sur Windows 10/11.
  - **Critère de succès** : Les notifications Windows s'affichent en temps réel sur l'écran supérieur de la 3DS.

