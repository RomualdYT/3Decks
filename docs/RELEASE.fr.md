# Publier une version

[Documentation](README.fr.md) · [English](RELEASE.md)

Les workflows [Qualité](../.github/workflows/quality.yml), [Release candidate](../.github/workflows/release.yml) et [Publication](../.github/workflows/publish-release.yml) produisent l’application Tauri et les paquets 3DS. Un tag `vX.Y.Z` vérifie le code, construit les versions macOS Apple Silicon, macOS Intel et Windows x64, puis ajoute les fichiers `.3dsx` et `.cia`, `latest.json`, les signatures et les sommes SHA-256 à une Release GitHub **en brouillon**. Les pushes sur `main` et les pull requests effectuent des contrôles légers sur Linux.

Les paquets macOS utilisent une signature ad hoc, sans compte développeur Apple ni notarisation. Les installateurs Windows ne portent pas de signature Authenticode. Configurez les clés de mise à jour, puis qualifiez les installateurs et les mises à jour avant publication.

## Consommation de la CI

- **Pushes et pull requests :** les contrôles de documentation sont systématiques. Les changements de l’éditeur déclenchent aussi les contrôles frontend et le build de la webview ; ceux de la console déclenchent les tests hôtes sur Linux. Une modification limitée aux fichiers Markdown ne déclenche pas de compilation. Les exécutions remplacées par un nouveau push sont annulées.
- **Tags de release :** validation complète, avec tests Rust natifs sur macOS/Windows, tests hôtes console sur Linux/macOS, paquets 3DS et paquets Focus sur Linux/macOS/Windows. Les clés de mise à jour sont vérifiées avant de lancer ces jobs.
- **Qualification manuelle :** lancer **Quality** depuis l’onglet Actions avec `full` activé pour valider une branche avant de créer le tag.
- **Paquets temporaires :** les artefacts Actions sont conservés sept jours. Cette durée ne concerne pas les fichiers joints à une Release GitHub.

Les changements Rust natifs et les extensions sont qualifiés automatiquement lors des releases ; lancer leurs contrôles locaux ou une qualification complète manuelle pour obtenir un retour plus tôt. Les commandes sont partagées dans un même workflow entre contrôles légers et complets.

Les builds officiels intègrent le Client ID public Twitch de 3Decks. Les forks distribués comme une autre application doivent renseigner la variable de dépôt `DECKS_TWITCH_CLIENT_ID` avec le Client ID de leur propre application Twitch de type Public. Aucun Client Secret n’est requis. Voir le [chat de stream](STREAM_CHAT.fr.md).

## Configuration unique du dépôt

1. Créer une paire de clés avec `cd apps/desktop && npm run tauri -- signer generate -w /chemin/prive/3decks.key`. Enregistrer la clé privée dans le secret GitHub `TAURI_SIGNING_PRIVATE_KEY`, son mot de passe éventuel dans `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, et la clé publique dans la variable `DECKS_UPDATER_PUBKEY`. Ne jamais versionner la clé privée. Voir la [documentation Tauri](https://v2.tauri.app/plugin/updater/#signing-updates).
2. Autoriser GitHub Actions à créer des Releases (`contents: write`), protéger les tags de version et configurer des approbateurs obligatoires sur l’environnement `production`. Un environnement sans règle de protection ne demande aucune approbation.

Aucun certificat ni secret de signature de code Apple ou Windows n’est nécessaire. La configuration Tauri commune définit `bundle.macOS.signingIdentity` à `"-"` : builds locaux et releases utilisent la signature ad hoc. Le workflow échoue tôt si les clés de mise à jour manquent ou si les versions Tauri JavaScript/Rust divergent. Avant l’empaquetage, `tools/prepare_desktop_release.py` injecte la clé publique dans `plugins.updater` de la configuration de release. La même clé est intégrée **au build** : un build sans cette clé ne peut pas activer l’updater après coup. La signature de distribution est une configuration distincte.

## Préparer et publier

1. Mettre la même version dans `apps/desktop/package.json`, `apps/desktop/src-tauri/Cargo.toml` et `apps/desktop/src-tauri/tauri.conf.json`, puis actualiser les lockfiles. Le validateur rejette un tag incohérent.
2. Faire tourner les tests, installer les candidats sur macOS et Windows, puis suivre le [plan d’essais Windows](../apps/desktop/docs/WINDOWS_TEST_PLAN.md) et la [qualification](QUALIFICATION.fr.md).
3. Pousser le changement de version, puis créer et pousser le tag annoté `vX.Y.Z`. Examiner la Release en brouillon : paquets, autorisation du premier lancement macOS, avertissements d’installation Windows, `latest.json`, sommes de contrôle et installation.
4. Tester une mise à jour depuis une version précédente avec signature de mise à jour valide, si elle existe, et l’appairage sur une console réelle ou Citra. Lancer ensuite le workflow **Publish qualified release** avec le tag : il vérifie à nouveau les fichiers puis publie. GitHub demande une approbation seulement si des approbateurs obligatoires ont été configurés.

Dans **Réglages → Avancé → Mises à jour**, l’utilisateur lance lui-même la recherche. L’application lit `https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json`, vérifie la signature, installe et redémarre. L’éditeur effectue aussi une recherche après son ouverture lorsque la clé publique est configurée ; l’installation nécessite un clic. Une Release en brouillon reste invisible pour l’application. L’installateur Windows direct configuré ne fournit pas l’identité de paquet nécessaire à l’historique des notifications ; Linux est différé.

Pour un DMG local, utiliser `npm run tauri -- build --bundles dmg` depuis
`apps/desktop/` ; la configuration de base ne génère pas d’artefacts de mise à jour.
L’autorisation Gatekeeper et les demandes du Trousseau après une mise à jour sont
décrites dans [Installation](INSTALLATION.fr.md#premier-lancement-sur-macos).
La signature ad hoc est distincte de la signature obligatoire des mises à jour
Tauri. Voir la [documentation Tauri](https://v2.tauri.app/distribute/sign/macos/#ad-hoc-signing).
