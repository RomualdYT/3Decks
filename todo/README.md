# 3Decks — Chantier Application Native macOS & Multiplateforme

Ce dossier rassemble l'ensemble des spécifications techniques, comparatifs d'architecture et feuilles de route pour transformer **3Decks** en une **application de bureau native de premier ordre**.

Ce dossier est spécialement structuré pour permettre à plusieurs agents d'IA (ou développeurs) de relire, amender, spécialiser et implémenter chaque composant en parallèle sans conflit.

---

## 🗺️ Sommaire des Documents

| Document | Rôle & Contenu | Agents concernés |
| :--- | :--- | :--- |
| [**00_ARCHITECTURE_BENCHMARK.md**](00_ARCHITECTURE_BENCHMARK.md) | Analyse comparative poussée de 4 architectures (Swift, Tauri Rust, PyInstaller, Hôte Hybride) avec métriques de RAM, latence et viabilité. | Architecte, Lead Dev |
| [**01_RECOMMENDED_STRATEGY.md**](01_RECOMMENDED_STRATEGY.md) | Stratégie pragmatique en deux phases : Phase 1 (App bundle native & WKWebView) puis Phase 2 (Cœur Rust haute performance). | Chef de projet, Architecte |
| [**02_MACOS_BUNDLE_SPEC.md**](02_MACOS_BUNDLE_SPEC.md) | Spécifications complètes du bundle `3Decks.app` : `Info.plist`, entitlements, icônes Retina `.icns`, signature et notarisation. | Ingénieur macOS, Packaging |
| [**03_NATIVE_WINDOW_AND_TRAY.md**](03_NATIVE_WINDOW_AND_TRAY.md) | Intégration dans la barre des menus (`NSStatusItem` / Tray) et fenêtre WebKit native (`WKWebView`) avec barre de titre intégrée. | Développeur Frontend / Cocoa |
| [**04_PERMISSIONS_AND_SECURITY.md**](04_PERMISSIONS_AND_SECURITY.md) | Gestion des autorisations macOS (TCC) : Accès complet au disque pour SQLite, Apple Events pour Spotify/Musique, Réseau local (macOS 15 Sequoia). | Sécurité, Ingénieur Système |
| [**05_BUILD_AND_CI_PIPELINE.md**](05_BUILD_AND_CI_PIPELINE.md) | Scripts d'empaquetage automatisés (`package_macos_app.sh`), création d'images disque `.dmg` et workflows GitHub Actions. | DevOps / Release Manager |
| [**06_TASKS_FOR_AGENTS.md**](06_TASKS_FOR_AGENTS.md) | Backlog granulaire sous forme de cases à cocher, assignables agent par agent avec critères d'acceptation stricts. | Tous les agents |
| [**07_WINDOWS_NATIVE_SPEC.md**](07_WINDOWS_NATIVE_SPEC.md) | Spécifications de l'application native sous Windows (MSIX, Win32 sans console, WebView2). | Ingénieur Windows, Packaging |
| [**08_AUTO_UPDATER_GITHUB.md**](08_AUTO_UPDATER_GITHUB.md) | Système de mises à jour automatiques transparentes via GitHub Releases (Tauri 2.0). | DevOps, Release Manager |

---

## 🤖 Guide de Collaboration Multi-Agents

1. **Règle d'or : Isolation des responsabilités**  
   Chaque agent intervenant sur ce chantier doit se concentrer sur son domaine (ex: l'agent système sur le bundle et les permissions TCC, l'agent UI sur la fenêtre WebKit et l'intégration de la barre des menus).
2. **Cycle de modification** :
   - Lire attentivement le document de spécification correspondant.
   - Proposer ou apporter des améliorations dans les sections dédiées.
   - Cocher les tâches au fur et à mesure dans [06_TASKS_FOR_AGENTS.md](06_TASKS_FOR_AGENTS.md).
3. **Respect de l'existant** :
   Le protocole binaire 3DS (TCP big-endian + JSON), l'éditeur React 19 et les fonctionnalités multiplateformes actuelles doivent rester 100% compatibles et fonctionnels.
