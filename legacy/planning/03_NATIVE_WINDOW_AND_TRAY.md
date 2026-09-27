# 03 — Spécifications : Barre des Menus & Fenêtre Native WebKit

Ce document définit l'interface graphique native de 3Decks sur macOS : l'icône de la barre des menus (`NSStatusItem`) et la fenêtre de configuration (`NSWindow` + `WKWebView`).

---

## 1. Intégration dans la Barre des Menus (`NSStatusItem`)

L'application doit résider discrètement dans la zone de droite de la barre des menus macOS (près de l'horloge et du centre de contrôle).

### A. États Visuels de l'Icône
L'icône utilise la silhouette de **Decky** (ou les deux écrans de la 3DS) avec un indicateur d'état dynamique :

| État | Couleur / Visuel | Signification |
| :--- | :--- | :--- |
| **Non connecté** | Contour monochrome neutre | L'agent tourne et attend la connexion d'une 3DS sur le réseau local. |
| **Connecté** | Pastille verte discrète | Une console 3DS est appairée et active. |
| **En pause** | Symbole pause / Gris atténué | La transmission vers la console est volontairement suspendue. |
| **Attention** | Pastille orange | Une autorisation macOS est manquante ou une erreur réseau est survenue. |

### B. Menu Contextuel de la Barre des Menus
Un clic sur l'icône déroule le menu natif macOS (`NSMenu`) :
- **En-tête d'état** : `3Decks · Prêt` ou `3DS connectée : New 3DS XL (192.168.1.125)`
- `──────`
- **Ouvrir le configurateur** (`Cmd + O`) -> Affiche ou ramène au premier plan la fenêtre native de configuration.
- **Mettre en pause** / **Reprendre** -> Suspend temporairement la communication avec les consoles.
- `──────`
- **Sous-menu Réglages rapides** :
  - Notifications : `Activées` / `Désactivées`
  - OBS Studio : `Connecté` / `Hors ligne`
  - Lancer à l'ouverture de session (case à cocher)
- **Ouvrir les autorisations macOS** -> Ouvre directement `Réglages Système → Confidentialité et sécurité`.
- `──────`
- **À propos de 3Decks**
- **Quitter 3Decks** (`Cmd + Q`) -> Arrêt propre des serveurs TCP/UDP et libération des ports.

---

## 2. Fenêtre Dédiée de Configuration (`WKWebView`)

Fini l'ouverture d'un nouvel onglet dans Chrome ou Safari ! L'utilisateur dispose d'une véritable fenêtre d'application macOS dédiée.

### A. Caractéristiques de la Fenêtre (`NSWindow`)
- **Dimensions initiales** : 1100 × 740 points (centrée sur l'écran principal).
- **Dimensions minimales** : 960 × 600 points.
- **Style de fenêtre** :
  - `NSWindowStyleMaskTitled` + `NSWindowStyleMaskClosable` + `NSWindowStyleMaskMiniaturizable` + `NSWindowStyleMaskResizable`.
  - Barre de titre intégrée : `titlebarAppearsTransparent = true` avec boutons de fermeture/réduction/plein écran standards macOS (traffic lights).
  - Gestion du thème : s'adapte automatiquement au Mode Sombre / Mode Clair de macOS.

### B. Configuration de `WKWebView`
- **Moteur** : Apple WebKit natif (`WKWebViewConfiguration`).
- **Isolation & Sécurité** :
  - Ne charge que les ressources locales servies par le serveur interne (`http://127.0.0.1:38124/`).
  - Blocage des navigations externes arbitraires (les liens externes vers GitHub ou la documentation s'ouvrent dans le navigateur par défaut de l'utilisateur via `NSWorkspace.shared.open(url)`).
  - Désactivation de l'inspection web en release (`preferences.isElementFullscreenEnabled = true`, inspecteur activable uniquement en debug).

### C. Fermeture de la Fenêtre
Lorsqu'un utilisateur clique sur la croix rouge de la fenêtre :
- La fenêtre est masquée (`window.orderOut(nil)` ou `window.close()`), mais **l'application continue de tourner en arrière-plan** dans la barre des menus pour maintenir la connexion avec la Nintendo 3DS.
- Un clic sur l'icône de la barre des menus permet de rouvrir instantanément la fenêtre sans délai de rechargement.
