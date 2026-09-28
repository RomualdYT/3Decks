# Publier une version

[Documentation](README.fr.md) · [English](RELEASE.md)

Les workflows [Qualité](../.github/workflows/quality.yml), [Release candidate](../.github/workflows/release.yml) et [Publication](../.github/workflows/publish-release.yml) produisent l’application Tauri et les paquets 3DS. Un tag `vX.Y.Z` vérifie le code, construit les versions macOS Apple Silicon, macOS Intel et Windows x64, puis ajoute les fichiers `.3dsx` et `.cia`, `latest.json`, les signatures et les sommes SHA-256 à une Release GitHub **en brouillon**. Le push sur `main` n’effectue que les contrôles qualité.

La chaîne est écrite, mais **aucune release signée multiplateforme n’a encore été validée**. Les clés, la notarisation Apple, la signature Windows et les essais sur un vrai PC Windows sont indispensables avant la première publication.

## Configuration unique du dépôt

1. Créer une paire de clés avec `cd desktop && npm run tauri signer generate -- -w /chemin/prive/3decks.key`. Enregistrer la clé privée dans le secret GitHub `TAURI_SIGNING_PRIVATE_KEY`, son mot de passe éventuel dans `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, et la clé publique dans la variable `DECKS_UPDATER_PUBKEY`. Ne jamais versionner la clé privée. Voir la [documentation Tauri](https://v2.tauri.app/plugin/updater/#signing-updates).
2. Configurer les secrets Apple : `APPLE_CERTIFICATE` (fichier `.p12` encodé en base64), `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_PASSWORD` (mot de passe spécifique à l’application) et `APPLE_TEAM_ID`. `APPLE_SIGNING_IDENTITY` est facultatif si le certificat suffit à identifier la signature.
3. Configurer les secrets Windows : `WINDOWS_CERTIFICATE` (fichier `.pfx` encodé en base64) et `WINDOWS_CERTIFICATE_PASSWORD`. Vérifier la signature et l’horodatage de l’installateur sur Windows.
4. Autoriser GitHub Actions à créer des Releases (`contents: write`), protéger les tags de version et configurer l’environnement `production` avec des personnes chargées d’approuver la publication.

Le workflow échoue tôt si une clé obligatoire manque. La clé publique est intégrée **au build** : un DMG local non signé ne peut pas devenir compatible avec les mises à jour après coup.

## Préparer et publier

1. Mettre la même version dans `desktop/package.json`, `desktop/src-tauri/Cargo.toml` et `desktop/src-tauri/tauri.conf.json`, puis actualiser les lockfiles. Le validateur rejette un tag incohérent.
2. Faire tourner les tests, installer les candidats sur macOS et Windows, puis suivre le [plan d’essais Windows](../desktop/docs/WINDOWS_TEST_PLAN.md) et la [qualification](QUALIFICATION.fr.md).
3. Pousser le changement de version, puis créer et pousser le tag annoté `vX.Y.Z`. Examiner la Release en brouillon : paquets, signatures, notarisation, `latest.json`, sommes de contrôle et installation.
4. Tester une mise à jour depuis une version signée précédente et l’appairage sur une console réelle ou Citra. Lancer ensuite le workflow **Publish qualified release** avec le tag : il vérifie à nouveau les fichiers puis publie après approbation.

Dans **Réglages → Avancé → Mises à jour**, l’utilisateur lance lui-même la recherche. L’application lit `https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json`, vérifie la signature, installe et redémarre. Il n’y a pas encore de recherche automatique en arrière-plan. Une Release en brouillon reste invisible pour l’application. La première distribution Windows directe ne permettra pas l’historique des notifications, qui exige une identité de paquet compatible ; Linux est différé.
