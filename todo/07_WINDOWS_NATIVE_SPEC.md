# 07 — Spécifications de l'Application Native Windows

Ce document détaille l'architecture et les spécifications requises pour offrir sur **Windows 10 et 11** une expérience native équivalente à celle de macOS, sans dépendance directe à Python pour l'utilisateur final.

---

## 1. Les Défis Spécifiques à Windows

Tout comme sur macOS, l'utilisation d'un script Python en ligne de commande pose des problèmes rédhibitoires sur Windows :
1. **La fenêtre de console noire (`cmd.exe`)** : L'utilisateur est forcé de conserver une fenêtre d'invite de commande ouverte en permanence, ce qui est laid et sujet à fermeture accidentelle.
2. **Les Notifications Windows verrouillées** : L'API moderne `UserNotificationListener` de Windows 10/11 **exige obligatoirement une identité d'application de package (MSIX)**. Un script Python standard est purement et simplement bloqué par Windows pour lire les notifications du système.
3. **Absence de fenêtre dédiée** : L'éditeur s'ouvre dans un navigateur externe plutôt que dans une application autonome avec sa propre icône dans la barre des tâches.

---

## 2. Spécification de la Solution Windows (Phase 1 & Phase 2)

### A. Phase 1 : Package MSIX / Lanceur Win32 Sans Console
Le dépôt dispose déjà des fondations :
- [`packaging/windows/launcher.c`](file:///Users/romuald/Documents/GitHub/3Decks/packaging/windows/launcher.c) : Binaire Win32 compilé en C (`wWinMain`) qui instancie le processus avec le flag `CREATE_NO_WINDOW`. Aucun terminal noir n'apparaît.
- [`agent/backend/windows/Package.appxmanifest.template`](file:///Users/romuald/Documents/GitHub/3Decks/agent/backend/windows/Package.appxmanifest.template) : Déclare l'identité MSIX requise par Windows pour débloquer la capacité `userNotificationListener`.
- [`agent/backend/deck3ds/desktop/tray.py`](file:///Users/romuald/Documents/GitHub/3Decks/agent/backend/deck3ds/desktop/tray.py) : Gère l'icône de notification près de l'horloge Windows (System Tray).

**Évolution nécessaire en Phase 1** :
- Remplacer l'ouverture dans le navigateur par une fenêtre native basée sur **Microsoft Edge WebView2** (le moteur moderne intégré par défaut dans Windows 10 et 11).
- Fournir un installeur standard `.exe` / `.msi` (ou `.msix` auto-signé avec certificat d'installation facile) en plus du Store.

---

### B. Phase 2 : Cœur Unifié Rust / Tauri 2.0 (L'expérience ultime)
L'adoption de **Tauri 2.0** prend tout son sens lorsqu'on considère Windows et macOS ensemble :
- **Moteur Web natif** :
  - Sur macOS : Apple WebKit (`WKWebView`).
  - Sur Windows : Microsoft Edge WebView2 (`WebView2Loader.dll`).
- **Tray & Fenêtre** : Composants natifs Win32/Cocoa sans aucune couche Python intermédiaire.
- **Ressources** : Moins de 35 MB de RAM sur les deux plateformes.
- **Identité MSIX / Windows App SDK** : Intégration directe des APIs WinRT pour les notifications et les contrôles multimédias (`GlobalSystemMediaTransportControls`).

---

## 3. Matrice des Fonctionnalités Windows

| Fonctionnalité | Mode Python CLI actuel | App Native Phase 1 (MSIX/Win32) | App Native Phase 2 (Tauri/Rust) |
| :--- | :---: | :---: | :---: |
| **Fenêtre de console noire** | Présente (gênante) | **Supprimée** (`CREATE_NO_WINDOW`) | **Absente** (Natif pur) |
| **Notifications Windows** | Bloquées par l'OS | **Débloquées** (Identité MSIX) | **Débloquées** (WinRT natif) |
| **Contrôle Multimédia** | Partiel / Win32 | Support complet | Support complet (GSMTC) |
| **Fenêtre de configuration** | Onglet navigateur | Fenêtre WebView2 dédiée | Fenêtre WebView2 intégrée |
| **Installation** | Complexe (uv / Python) | 1 clic (`.msix` / `.exe`) | 1 clic (`.exe` / `.msix`) |
| **RAM** | ~80 MB | ~70 MB | **~30 MB** |
