# Publier une version

[Documentation](README.fr.md) · [English](RELEASE.md)

Les workflows [Qualité](../.github/workflows/quality.yml), [Release candidate](../.github/workflows/release.yml) et [Publication](../.github/workflows/publish-release.yml) produisent l’application Tauri et les paquets 3DS. Un tag `vX.Y.Z` vérifie le code, construit les versions macOS Apple Silicon, macOS Intel et Windows x64, puis ajoute les fichiers `.3dsx` et `.cia`, `latest.json`, les signatures et les sommes SHA-256 à une Release GitHub **en brouillon**. Les pushes sur `main` et les pull requests effectuent des contrôles légers sur Linux.

Configurez les clés, la notarisation Apple et la signature Windows, puis qualifiez les installateurs et les mises à jour avant de publier un candidat.

## Consommation de la CI

- **Pushes et pull requests :** les contrôles de documentation sont systématiques. Les changements de l’éditeur déclenchent aussi les contrôles frontend et le build de la webview ; ceux de la console déclenchent les tests hôtes sur Linux. Une modification limitée aux fichiers Markdown ne déclenche pas de compilation. Les exécutions remplacées par un nouveau push sont annulées.
- **Tags de release :** validation complète, avec tests Rust natifs sur macOS/Windows, tests hôtes console sur Linux/macOS, paquets 3DS et paquets Focus sur Linux/macOS/Windows. Les paramètres de signature sont vérifiés avant de lancer ces jobs.
- **Qualification manuelle :** lancer **Quality** depuis l’onglet Actions avec `full` activé pour valider une branche avant de créer le tag.
- **Paquets temporaires :** les artefacts Actions sont conservés sept jours. Cette durée ne concerne pas les fichiers joints à une Release GitHub.

Les changements Rust natifs et les extensions sont qualifiés automatiquement lors des releases ; lancer leurs contrôles locaux ou une qualification complète manuelle pour obtenir un retour plus tôt. Les commandes sont partagées dans un même workflow entre contrôles légers et complets.

Les builds officiels intègrent le Client ID public Twitch de 3Decks. Les forks distribués comme une autre application doivent renseigner la variable de dépôt `DECKS_TWITCH_CLIENT_ID` avec le Client ID de leur propre application Twitch de type Public. Aucun Client Secret n’est requis. Voir le [chat de stream](STREAM_CHAT.fr.md).

## Configuration unique du dépôt

1. Créer une paire de clés avec `cd apps/desktop && npm run tauri -- signer generate -w /chemin/prive/3decks.key`. Enregistrer la clé privée dans le secret GitHub `TAURI_SIGNING_PRIVATE_KEY`, son mot de passe éventuel dans `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, et la clé publique dans la variable `DECKS_UPDATER_PUBKEY`. Ne jamais versionner la clé privée. Voir la [documentation Tauri](https://v2.tauri.app/plugin/updater/#signing-updates).
2. Configurer les secrets Apple : `APPLE_CERTIFICATE` (fichier `.p12` encodé en base64), `APPLE_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_PASSWORD` (mot de passe spécifique à l’application) et `APPLE_TEAM_ID`. `APPLE_SIGNING_IDENTITY` est facultatif si le certificat suffit à identifier la signature.
3. Configurer les secrets Windows : `WINDOWS_CERTIFICATE` (fichier `.pfx` encodé en base64) et `WINDOWS_CERTIFICATE_PASSWORD`. Vérifier la signature et l’horodatage de l’installateur sur Windows.
4. Autoriser GitHub Actions à créer des Releases (`contents: write`), protéger les tags de version et configurer des approbateurs obligatoires sur l’environnement `production`. Un environnement sans règle de protection ne demande aucune approbation.

Le workflow échoue tôt si une clé obligatoire manque. La clé publique est intégrée **au build** : un build sans cette clé ne peut pas activer l’updater après coup. La signature de distribution est une configuration distincte.

## Préparer et publier

1. Mettre la même version dans `apps/desktop/package.json`, `apps/desktop/src-tauri/Cargo.toml` et `apps/desktop/src-tauri/tauri.conf.json`, puis actualiser les lockfiles. Le validateur rejette un tag incohérent.
2. Faire tourner les tests, installer les candidats sur macOS et Windows, puis suivre le [plan d’essais Windows](../apps/desktop/docs/WINDOWS_TEST_PLAN.md) et la [qualification](QUALIFICATION.fr.md).
3. Pousser le changement de version, puis créer et pousser le tag annoté `vX.Y.Z`. Examiner la Release en brouillon : paquets, signatures, notarisation, `latest.json`, sommes de contrôle et installation.
4. Tester une mise à jour depuis une version signée précédente, si elle existe, et l’appairage sur une console réelle ou Citra. Lancer ensuite le workflow **Publish qualified release** avec le tag : il vérifie à nouveau les fichiers puis publie. GitHub demande une approbation seulement si des approbateurs obligatoires ont été configurés.

Dans **Réglages → Avancé → Mises à jour**, l’utilisateur lance lui-même la recherche. L’application lit `https://github.com/RomualdYT/3Decks/releases/latest/download/latest.json`, vérifie la signature, installe et redémarre. L’éditeur effectue aussi une recherche après son ouverture lorsque la clé publique est configurée ; l’installation nécessite un clic. Une Release en brouillon reste invisible pour l’application. L’installateur Windows direct configuré ne fournit pas l’identité de paquet nécessaire à l’historique des notifications ; Linux est différé.
