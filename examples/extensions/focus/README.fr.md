# Focus pour 3Decks

[English](README.md)

Un compagnon Pomodoro hors ligne : six commandes tactiles, un écran de suivi et
une progression quotidienne sauvegardée. L'anglais et le français sont inclus ;
3Decks choisit la langue.

## Installer et créer la page

1. Dans **Extensions → Importer**, choisissez le paquet `.3deckext` de votre ordinateur.
2. Consultez le paquet et approuvez son empreinte pour activer **Focus**.
3. Dans **Éditeur**, ajoutez une page **Focus** avec l'icône étoile.
4. Dans ses réglages, choisissez la disposition **Grille** pour l'écran tactile.
5. Sélectionnez **Contenu des boutons → Commandes Focus** puis **Écran du haut → Suivi Focus**.

Les six boutons apparaissent automatiquement. L'écran du haut affiche le temps
restant, les sessions terminées du jour, le temps de travail terminé et la
prochaine phase. Les actions Focus peuvent aussi être ajoutées individuellement
à des boutons personnalisés sur une autre page.

## Utilisation

| Commande | Comportement |
| --- | --- |
| Démarrer / Suspendre / Reprendre | Lance, suspend ou reprend le temps restant. |
| Repartir | Prépare la phase actuelle depuis le début, sans effacer les statistiques. |
| Passer | Prépare la phase suivante sans compter de session inachevée. |
| Travail | Sélectionne un nouveau minuteur de concentration. |
| Pause courte | Sélectionne une nouvelle pause courte. |
| Pause longue | Sélectionne une nouvelle pause longue ; quitter celle-ci ouvre un nouveau cycle. |

Suspendez avant de changer de phase. Toucher la phase déjà sélectionnée conserve
son minuteur. Changer de phase abandonne le temps inachevé sans compter de session.

Par défaut : **25 minutes de travail**, **5 minutes de pause courte**, **15 minutes
de pause longue**, une pause longue après **4 sessions terminées** et un objectif
quotidien de **4 sessions**. Ces valeurs sont modifiables dans
**Extensions → Focus → Réglages**. Les durées, le nombre de sessions par cycle et
l'objectif quotidien sont des nombres entiers.

Les démarrages automatiques sont désactivés par défaut. Les pauses et le travail
peuvent être enchaînés automatiquement de manière indépendante. Les commandes
manuelles préparent toujours le minuteur suivant sans le démarrer.

## Sauvegarde

- Phase, temps restant, état du minuteur et progression du cycle.
- Échéance d'une session en cours, conservée pendant la veille et les redémarrages.
- Sessions terminées et leurs durées, regroupées par date locale de fin.
- Les 30 derniers jours d'activité et le nombre total de sessions terminées.

À la reprise après une interruption, seule la phase réellement lancée peut être
terminée. La phase automatique suivante démarre à la reprise : le temps passé
hors ligne ne crée pas de sessions fictives. Le temps de concentration quotidien
comprend uniquement les sessions de travail entièrement terminées.

Modifier les réglages conserve la durée d'un minuteur en cours ou suspendu. Les
minuteurs prêts et les phases suivantes utilisent les nouvelles valeurs. La
sauvegarde est atomique et ses erreurs sont signalées. Des données illisibles ou
d'une version incompatible sont conservées ; elles ne sont pas écrasées par une
sauvegarde vide.

Focus écrit uniquement `focus.json` dans le dossier privé fourni par l'application.
Aucun service en ligne ni identifiant n'est nécessaire. La fin d'une phase est
visible sur les écrans ; aucun son ni notification système n'est émis.

## Compiler un paquet importable

Depuis la racine du dépôt, avec Rust et Python 3.9 ou une version ultérieure :

```sh
python3 examples/extensions/focus/package.py
```

Le script utilise le verrouillage Cargo du dépôt et produit un paquet pour
l'ordinateur actuel dans `examples/extensions/focus/dist/`. Sur Windows, la
commande Python peut être `python`. Le script transforme
`extension.template.json` en `extension.json`, en ajoutant uniquement le binaire
de la cible compilée. Les compilations et les paquets sont ignorés par Git.

Une autre cible installée peut être choisie avec son éditeur de liens :

```sh
python3 examples/extensions/focus/package.py --target x86_64-pc-windows-msvc
```

Cibles prises en charge : macOS Apple Silicon/Intel, Windows ARM64/x64 (MSVC) et
Linux ARM64/x64 (GNU). Compilez sur la plateforme concernée ou utilisez une chaîne
de compilation croisée configurée pour celle-ci. Un paquet ne contient que la
cible effectivement compilée.

## Organisation du code

| Fichier | Rôle |
| --- | --- |
| `src/main.rs` | Cycle de vie du SDK, actions et validation des sauvegardes. |
| `src/timer.rs` | Minuteur, transitions, cycles et historique borné. |
| `src/config.rs` | Réglages typés et bornés. |
| `src/storage.rs` | Sauvegarde JSON versionnée et remplacement atomique. |
| `src/presentation.rs` | Commandes bilingues et écran à quatre cartes. |
| `package.py` | Compilation native et création du `.3deckext`. |

Utilise le [SDK Rust des extensions](../../../apps/desktop/extension-sdk/README.md)
et la licence GPL-3.0-or-later de 3Decks. Aucun changement de l'interface PC ou du
moteur de rendu de la console n'est requis.
