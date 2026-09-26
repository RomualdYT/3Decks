# 04 — Gestion des Permissions macOS & Sécurité (TCC)

Ce document analyse les exigences de sécurité de macOS (système TCC : *Transparency, Consent, and Control*) et formalise les solutions pour garantir une expérience fluide à l'utilisateur.

---

## 1. Les 3 Autorisations Requises par 3Decks

| Fonctionnalité 3Decks | Ressource Système macOS | Catégorie TCC dans Réglages Système |
| :--- | :--- | :--- |
| **Notifications sur l'écran haut** | Base SQLite : `~/Library/Group Containers/group.com.apple.usernoted/db2/db` | **Accès complet au disque** (*Full Disk Access*) |
| **Contrôle Musique (Spotify / Music)** | AppleScript / Apple Events vers Spotify ou Musique | **Automatisation** (*Automation*) |
| **Découverte et connexion 3DS** | Ports UDP 38122 et TCP 38123 sur le LAN | **Réseau local** (*Local Network* — macOS 15 Sequoia+) |

---

## 2. Pourquoi l'App Bundle Résout le Problème TCC

Sous macOS :
1. **En mode script CLI** (`python3 -m deck3ds`) :
   - L'exécutable n'a pas de conteneur d'application ni de signature stable.
   - macOS remonte l'arborescence des processus jusqu'à l'application parent : c'est donc **Terminal.app**, **iTerm2** ou **VSCode** qui doit être autorisé !
   - L'utilisateur ne voit jamais « 3Decks » et se retrouve perdu.
2. **En mode Application Native (`3Decks.app`)** :
   - Le bundle possède un identifiant cryptographique stable (`com.romualdyt.3decks`).
   - macOS enregistre la permission directement sous le nom **3Decks**, avec son icône de robot Decky dans la liste des Réglages Système.
   - Si l'autorisation n'est pas encore accordée, l'utilisateur peut simplement cliquer sur **`+`** et sélectionner **3Decks** dans son dossier Applications, ou glisser-déposer l'application.

---

## 3. Déclaration des Entitlements (`packaging/macos/entitlements.plist`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Autorise la connexion réseau sortante et entrante pour le serveur 3DS -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Autorise l'envoi d'Apple Events pour contrôler Spotify, Musique et le volume -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
```

---

## 4. Assistant d'Autorisation Intégré (UX Onboarding)

Pour simplifier la vie de l'utilisateur, l'application doit intégrer un petit dialogue d'onboarding lors de la première activation des notifications :

1. Détection de l'accès :
   - L'agent tente d'ouvrir la base en lecture :
     ```python
     db_path = Path.home() / "Library/Group Containers/group.com.apple.usernoted/db2/db"
     try:
         with open(db_path, "rb"):
             has_access = True
     except PermissionError:
         has_access = False
     ```
2. Si `has_access == False` :
   - L'application affiche un encadré explicatif avec un bouton unique : **« Configurer dans Réglages Système »**.
   - Le clic exécute l'URL de préférence macOS officielle :
     ```bash
     open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
     ```
   - L'application surveille en tâche de fond (toutes les 3 secondes) le déblocage de l'accès pour faire disparaître l'alerte dès que l'utilisateur a coché la case, sans imposer de redémarrage.
