# 00 — Analyse Comparative & Benchmark des Architectures Natives

Ce document compare rigoureusement les différentes approches techniques permettant de faire de 3Decks une application native sur macOS (avec une perspective multiplateforme pour Windows).

---

## 1. Contexte & État Actuel

Actuellement, l'agent 3Decks est articulé autour de :
- Un backend Python 3.12+ asynchrone (FastAPI + Pydantic + asyncio) de ~15 500 lignes de code, fortement testé (tests unitaires, tests de propriétés, couverture de code).
- Des serveurs réseau : TCP sur `38123` (cœur temps réel 3DS), UDP broadcast sur `38122` (découverte LAN).
- Des intégrations système natives macOS (AppleScript, SQLite sur `usernoted/db2/db`, CoreAudio, CGWindowList).
- Une interface d'édition en React 19 + HeroUI + Tailwind CSS servie localement sur HTTP (`38124`).

### Le Problème Clé
L'exécution actuelle en script CLI (`python3 -m deck3ds --ui`) fait que macOS attribue les autorisations système TCC (Full Disk Access pour les notifications, Automation pour la musique) à l'application hôte (le **Terminal** ou l'IDE), ce qui est déroutant pour l'utilisateur qui ne trouve jamais « 3Decks » dans ses réglages système.

---

## 2. Comparatif des 4 Architectures Possibles

### Option 1 : Application 100% Native Swift / SwiftUI (macOS pur)
*Remplacement complet de l'agent par une application écrite en Swift avec AppKit/SwiftUI et Network.framework.*

- **RAM** : ~20 à 30 MB au repos.
- **Démarrage** : Instantané (< 100 ms).
- **Taille du binaire** : ~15 MB.
- **Avantages** :
  - Intégration macOS parfaite (MenuBarExtra, AppKit, contrôles natifs).
  - Empreinte mémoire minimale, zéro interpréteur tiers.
  - Dialogues système et permissions TCC transparentes.
- **Inconvénients majeurs** :
  - **Coût de développement titanesque** : Réécriture complète de 15 500 lignes de logique (protocoles réseau, validation Pydantic, moteur d'actions, extensions, OBS WebSocket).
  - **Rupture multiplateforme** : Le code Swift n'est pas réutilisable sur Windows (il faudrait réécrire une seconde application en C#/WinUI).

---

### Option 2 : Tauri 2.0 (Cœur Rust + WebKit WKWebView + React 19)
*Le backend réseau et système est écrit en Rust ; l'interface graphique existante (React 19) tourne dans le WebKit natif de macOS.*

- **RAM** : ~30 à 45 MB au repos (partage la mémoire de WebKit avec l'OS).
- **Démarrage** : ~300 ms.
- **Taille du binaire** : ~15 à 20 MB.
- **Avantages** :
  - Vrai binaire compilé ultra-rapide (Rust `tokio` pour le TCP/UDP 3DS avec latence sub-milliseconde).
  - Réutilisation à 100% du frontend React 19 existant sans modification majeure.
  - Multiplateforme natif : le même code Rust tourne sur macOS (WebKit) et Windows (WebView2).
  - Gestion native du tray (icône de barre des menus) et des fenêtres natives.
- **Inconvénients** :
  - Nécessite de réécrire les services backend et connecteurs en Rust (environ 3 à 5 semaines de travail).
  - Idéal comme objectif pour la version 2.0.

---

### Option 3 : Bundle Python Autonome (PyInstaller / Briefcase / PyOxidizer)
*Empaquetage du projet Python actuel dans un bundle `3Decks.app` avec son propre interpréteur et ses dépendances embarquées.*

- **RAM** : ~65 à 85 MB.
- **Démarrage** : ~1 à 2 secondes.
- **Taille du binaire** : ~50 à 65 MB (inclut Python stdlib et packages).
- **Avantages** :
  - Conserve 100% de la base de code Python existante sans aucune régression.
  - Crée un véritable `3Decks.app` avec son Bundle ID (`com.romualdyt.3decks`) reconnu par les réglages macOS.
  - Rapide à mettre en place.
- **Inconvénients** :
  - Empreinte disque et mémoire un peu plus lourde.
  - Par défaut, ouvre l'interface dans un navigateur web externe si aucun wrapper de fenêtre natif n'est ajouté.

---

### Option 4 (Recommandée pour la Phase 1) : Hôte Hybride Swift/Cocoa + WKWebView + Daemon Python Embarqué
*Une application macOS native légère en Swift ou wrapper Cocoa qui gère la barre des menus (`NSStatusItem`) et héberge l'éditeur dans une élégante fenêtre WebKit native (`WKWebView`), tout en supervisant le serveur local 3Decks.*

- **RAM** : ~60 à 75 MB au total.
- **Démarrage** : Instantané pour la barre des menus, chargement du serveur en ~800 ms.
- **Taille du binaire** : ~45 à 55 MB.
- **Avantages** :
  - **Expérience 100% native** : Une vraie fenêtre d'application macOS (barre de titre translucide, boutons de fermeture/réduction natifs, pas d'onglet Safari/Chrome).
  - **Barre des menus native** : Icône animée de Decky dans la barre des menus avec menu contextuel fluide.
  - **Permissions TCC parfaites** : macOS associe toutes les autorisations directement à `3Decks.app`.
  - **Risque technique minimal** : Aucun besoin de réécrire les 15 500 lignes de logique Python ni le frontend React.

---

## 3. Matrice de Décision

| Critère (Pondération) | Option 1 (Swift pur) | Option 2 (Tauri Rust) | Option 3 (PyInstaller brut) | Option 4 (Hybride Swift/WebKit) |
| :--- | :---: | :---: | :---: | :---: |
| **Expérience macOS (25%)** | 10/10 | 9/10 | 6/10 | **9.5/10** |
| **Clarté Permissions TCC (20%)** | 10/10 | 10/10 | 9/10 | **10/10** |
| **Vitesse de mise en œuvre (20%)** | 2/10 | 4/10 | 8/10 | **9/10** |
| **Sobriété Mémoire/CPU (15%)** | 10/10 | 9/10 | 5/10 | **7/10** |
| **Préservation de l'existant (20%)** | 1/10 | 5/10 | 10/10 | **9.5/10** |
| **NOTE GLOBALE** | **6.4 / 10** | **7.3 / 10** | **7.5 / 10** | **9.1 / 10** |
