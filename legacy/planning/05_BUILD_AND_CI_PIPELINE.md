# 05 — Pipeline d'Empaquetage & Distribution macOS

Ce document spécifie le processus d'automatisation permettant de construire, signer, emballer et distribuer **`3Decks.app`** sous forme de paquet autonome et d'image disque `.dmg`.

---

## 1. Script d'Empaquetage Local (`tools/package_macos_app.sh`)

Ce script sera responsable de fabriquer `3Decks.app` en une seule commande :

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
APP_DIR="$DIST_DIR/3Decks.app"
CONTENTS="$APP_DIR/Contents"

echo "==> 1. Préparation de l'arborescence de 3Decks.app"
rm -rf "$APP_DIR"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"

echo "==> 2. Génération de l'icône 3Decks.icns multi-résolution"
bash "$REPO_ROOT/tools/generate_macos_icon.sh" "$CONTENTS/Resources/3Decks.icns"

echo "==> 3. Copie des métadonnées Info.plist et PkgInfo"
cp "$REPO_ROOT/packaging/macos/Info.plist" "$CONTENTS/Info.plist"
echo "APPL????" > "$CONTENTS/PkgInfo"

echo "==> 4. Assemblage du lanceur natif et du runtime"
# Copie du binaire d'entrée / runtime autonome
# ...

echo "==> 5. Signature de code ad-hoc"
codesign --force --deep --sign - --entitlements "$REPO_ROOT/packaging/macos/entitlements.plist" "$APP_DIR"

echo "==> 3Decks.app créé avec succès dans $APP_DIR"
```

---

## 2. Création de l'Image Disque d'Installation (`3Decks.dmg`)

Pour offrir une expérience de glisser-déposer standard vers `/Applications` :
- Utilisation de `create-dmg` ou de `hdiutil` :
  - Fenêtre de taille 600x400 avec fond personnalisé.
  - Positionnement de l'icône de `3Decks.app` à gauche.
  - Lien symbolique vers `/Applications` à droite avec la flèche de glissement.
- Le fichier produit est nommé `3Decks-macOS-<version>.dmg` et prêt pour publication sur les GitHub Releases.

---

## 3. Intégration GitHub Actions (`.github/workflows/macos-app.yml`)

Ajout d'un job dédié dans la CI qui s'exécute sur `macos-latest` :
1. Compilation des assets statiques React (`pnpm build`).
2. Exécution du script d'empaquetage `tools/package_macos_app.sh`.
3. Génération du `.dmg`.
4. Téléversement en tant qu'artefact de build sur chaque push, et inclusion dans les Releases lors de la publication d'une nouvelle version.
