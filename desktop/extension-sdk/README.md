# API native des extensions 3Decks · v1

Une extension Tauri est un **exécutable autonome** distribué dans un paquet
`.3deckext` (ZIP). Aucun interpréteur Python ni commande du système n'est lancé.
L'exécutable s'exécute dans un processus séparé, avec les droits du compte
utilisateur. La séparation de processus évite de charger du code tiers dans
Tauri ; **elle n'est pas un bac à sable**. L'interface demande donc une
approbation explicite de l'empreinte SHA-256 du paquet avant activation.

## SDK Rust

Le crate [`three-decks-extension-sdk`](Cargo.toml) fournit `Context`,
`Snapshot`, `ActionResult`, le trait `Extension` et `serve()`. L'exemple
[`counter.rs`](examples/counter.rs) est exécutable :

```sh
cargo test --manifest-path desktop/extension-sdk/Cargo.toml
cargo build --release --manifest-path desktop/extension-sdk/Cargo.toml --example counter
```

Un projet tiers peut déclarer le SDK en dépendance Git ou par chemin pendant
le développement. Le protocole JSON Lines reste indépendant du langage :
le SDK Rust est la référence de l'API v1, sans ABI Rust partagée ni chargement
de bibliothèque dynamique.

## Manifeste et paquet

Un paquet contient `extension.json` à la racine et au moins un binaire sous
`bin/`. Exemple pour macOS Intel :

```json
{
  "api_version": 1,
  "id": "com.example.counter",
  "version": "1.0.0",
  "name": {"en": "Counter", "fr": "Compteur"},
  "description": {"en": "Counts presses", "fr": "Compte les pressions"},
  "author": "Example",
  "runtime": "native",
  "binaries": {"darwin-x86_64": "bin/counter"},
  "actions": [{"id": "increment", "title": {"en": "Increment", "fr": "Incrémenter"}, "arguments": []}],
  "sources": [],
  "dashboards": [],
  "settings": []
}
```

Les clés de `binaries` sont `darwin-aarch64`, `darwin-x86_64`,
`win32-aarch64`, `win32-x86_64`, `linux-aarch64`, `linux-x86_64`.
Déclarez uniquement les cibles réellement incluses dans le ZIP. Pour Windows,
utilisez un chemin comme `bin/counter.exe`. Le champ `platforms` est dérivé des
binaires ; il ne faut pas le gérer à la main. Un paquet peut contenir plusieurs
cibles. Le binaire local est lancé depuis le dossier extrait du paquet, jamais
depuis `PATH` ou un chemin absolu. Sur macOS et Linux, le bit exécutable est
posé à l'import pour le binaire de la cible courante.

Pour essayer l'exemple sur votre machine, créez un dossier temporaire avec
`extension.json` adapté à la cible affichée par `rustc -vV`, copiez le binaire
compilé dans `bin/`, puis archivez **le contenu du dossier** en `.3deckext`.
Dans l'app : Extensions → Importer → lire l'empreinte → Activer.

## Protocole

Le parent écrit une requête JSON suivie de `\n` sur stdin. L'extension répond
sur stdout avec le même `id` ; stderr reste libre pour les diagnostics.
Chaque ligne est limitée à 64 KiB et chaque appel à cinq secondes.

| Méthode | Paramètres | Résultat |
| --- | --- | --- |
| `initialize` | `api_version`, `extension_id`, `settings`, `data_dir`, `platform` | `{"api_version":1}` |
| `poll` | `{}` | `states`, `sources`, `dashboards` |
| `action` | `action`, `arguments` | `ok`, `message` |
| `shutdown` | `{}` | `{}` |

Le moteur valide les actions, arguments et instantanés par rapport au
manifeste. Les noms de sources et d'écrans doivent être déclarés. Les réglages
sensibles restent masqués dans l'interface, mais sont transmis au processus de
l'extension lors de `initialize`. Le champ `data_dir` fournit un dossier privé
pour ses données persistantes. Une mise à jour du contenu du paquet change son
empreinte et exige une nouvelle approbation.

## Compatibilité

L'ancien format `runtime: python` ou `runtime: command` est refusé par l'hôte
Tauri. Le serveur Python historique garde ses propres extensions tant qu'il
reste dans le dépôt ; aucun pont de compatibilité n'est embarqué dans l'app
native. API v1 n'est pas encore publiée comme contrat stable de production.

Le SDK suit actuellement la licence GPL-3.0-or-later du dépôt. Avant d'ouvrir
un écosystème d'extensions tiers, l'équipe doit décider explicitement si ce
SDK d'auteur recevra aussi une licence permissive distincte.
