# 02 — Spécifications du Bundle macOS `3Decks.app`

Ce document spécifie la structure exacte, les métadonnées système et les règles de signature requises pour générer le bundle officiel **`3Decks.app`**.

---

## 1. Arborescence du Bundle

```text
3Decks.app/
└── Contents/
    ├── Info.plist               <- Déclaration système, bundle ID, icônes, permissions
    ├── PkgInfo                  <- Contient "APPL????"
    ├── MacOS/
    │   ├── 3Decks               <- Binaire d'entrée principal (lanceur Cocoa / Swift ou wrapper)
    │   └── runtime/             <- Interpréteur et dépendances Python isolées
    ├── Resources/
    │   ├── 3Decks.icns          <- Icône Retina multi-tailles de l'application
    │   ├── DeckyTray.png        <- Icône template pour la barre des menus (noir/blanc avec canal alpha)
    │   ├── DeckyTray@2x.png     <- Version Retina 2x de l'icône de barre des menus
    │   └── web/                 <- Ressources statiques du configurateur (HTML, JS, CSS)
    └── _CodeSignature/          <- Signature de code Apple (ad-hoc ou Developer ID)
```

---

## 2. Spécification de `Info.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Identité de l'application -->
    <key>CFBundleName</key>
    <string>3Decks</string>
    <key>CFBundleDisplayName</key>
    <string>3Decks</string>
    <key>CFBundleIdentifier</key>
    <string>com.romualdyt.3decks</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>3Decks</string>
    
    <!-- Icône officielle -->
    <key>CFBundleIconFile</key>
    <string>3Decks</string>
    <key>CFBundleIconName</key>
    <string>3Decks</string>
    
    <!-- Comportement macOS : Application de barre des menus (Agent) -->
    <!-- LSUIElement=true empêche l'apparition inutile d'une icône persistante dans le Dock -->
    <key>LSUIElement</key>
    <true/>
    
    <!-- Compatibilité écran Retina et versions système -->
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    
    <!-- Justifications d'accès système (affichées par macOS lors des demandes) -->
    <key>NSAppleEventsUsageDescription</key>
    <string>3Decks utilise Apple Events pour piloter la lecture multimédia (Spotify, Apple Music) et changer le volume système depuis votre console 3DS.</string>
    <key>NSLocalNetworkUsageDescription</key>
    <string>3Decks communique avec votre console Nintendo 3DS sur votre réseau local via TCP et UDP.</string>
    <key>NSSystemAdministrationUsageDescription</key>
    <string>3Decks a besoin d'accéder au Centre de notifications pour afficher vos alertes récentes sur l'écran supérieur de la 3DS.</string>
</dict>
</plist>
```

---

## 3. Génération de `3Decks.icns`

L'icône Mac officielle doit être produite au format `.icns` à partir du fichier source [`agent/frontend/public/3decks-logo.png`](file:///Users/romuald/Documents/GitHub/3Decks/agent/frontend/public/3decks-logo.png) (1024x1024) à l'aide de l'outil standard `iconutil` :

```bash
mkdir -p 3Decks.iconset
sips -z 16 16     3decks-logo.png --out 3Decks.iconset/icon_16x16.png
sips -z 32 32     3decks-logo.png --out 3Decks.iconset/icon_16x16@2x.png
sips -z 32 32     3decks-logo.png --out 3Decks.iconset/icon_32x32.png
sips -z 64 64     3decks-logo.png --out 3Decks.iconset/icon_32x32@2x.png
sips -z 128 128   3decks-logo.png --out 3Decks.iconset/icon_128x128.png
sips -z 256 256   3decks-logo.png --out 3Decks.iconset/icon_128x128@2x.png
sips -z 256 256   3decks-logo.png --out 3Decks.iconset/icon_256x256.png
sips -z 512 512   3decks-logo.png --out 3Decks.iconset/icon_256x256@2x.png
sips -z 512 512   3decks-logo.png --out 3Decks.iconset/icon_512x512.png
sips -z 1024 1024 3decks-logo.png --out 3Decks.iconset/icon_512x512@2x.png
iconutil -c icns 3Decks.iconset -o 3Decks.icns
```

---

## 4. Règles de Signature de Code (Code Signing)

Pour que macOS reconnaisse l'identité du bundle et retienne les autorisations TCC accordées dans les Réglages Système :
1. **Signature Ad-Hoc locale (Développement / Installation directe)** :
   ```bash
   codesign --force --deep --sign - --entitlements packaging/macos/entitlements.plist 3Decks.app
   ```
2. **Signature Developer ID (Production / Release GitHub publique)** :
   ```bash
   codesign --force --deep --options runtime --sign "Developer ID Application: ..." --entitlements packaging/macos/entitlements.plist 3Decks.app
   ```
