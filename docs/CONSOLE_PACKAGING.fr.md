# Paquets console et visuels du menu HOME

[Documentation](README.fr.md) · [English](CONSOLE_PACKAGING.md)

## Choisir un format

| Fichier | Utilisation |
|---|---|
| `deck3ds.cia` | Installation avec FBI sur une console avec firmware personnalisé, puis lancement depuis HOME. |
| `deck3ds.3dsx` | Homebrew Launcher ou envoi par 3dslink, sans installation HOME. |

Les deux formats embarquent la même application C et la police Inter. Le CIA
est autonome : il n’a **pas** besoin du `.3dsx` sur la carte SD. Les réglages et
l’appairage restent communs dans `sdmc:/3ds/deck3ds/settings.cfg`. Sauvegardez ce
fichier de façon privée : il contient le secret de la console.

## Installer sur HOME

1. Téléchargez `deck3ds.cia` depuis une Release 3Decks de confiance.
2. Copiez-le dans `sdmc:/cias/deck3ds.cia` (créez `cias` si nécessaire).
3. Dans FBI : **SD → cias → deck3ds.cia → Install CIA**, puis confirmez.
4. Revenez à HOME, déballez la nouvelle application si demandé, puis ouvrez **3Decks**.

L’icône Decky et la bannière charbon/verte s’affichent à la sélection. La bannière
est fixe et volontairement silencieuse ; l’animation de réveil de Decky apparaît
**dans l’application**, après son lancement.

Il faut une console déjà équipée d’un firmware personnalisé, par exemple Luma3DS.
Copier un CIA sur la SD ne suffit pas à l’installer. 3dslink envoie des `.3dsx`,
mais n’installe pas les CIA. Le projet n’installe pas de firmware personnalisé et
ne contourne pas les confirmations de l’installateur.

Pour mettre à jour, installez le nouveau CIA par-dessus, sans désinstallation
préalable. Pour le retirer, utilisez **Paramètres de la console → Gestion des
données → Nintendo 3DS → Logiciels**. Les réglages partagés du dossier
`sdmc:/3ds/deck3ds/` restent sur la SD ; les supprimer séparément efface aussi
l’appairage enregistré côté console.

## Compiler

Depuis la racine, avec Docker lancé :

```sh
./build.sh          # 3DSX, comme avant
./build.sh cia      # CIA et 3DSX
./build.sh all      # les deux formats
```

L’image de packaging compile [makerom](https://github.com/3DSGuy/Project_CTR) et
[bannertool](https://github.com/diasurgical/bannertool) à des révisions fixées dans
[le Dockerfile](../apps/console/packaging/Dockerfile). Aucun SDK Nintendo ni clé privée de
signature n’est nécessaire. Ces paquets homebrew ne sont pas signés officiellement.
L’image devkitPro et les paquets Debian restent évolutifs : le build n’est pas
garanti identique bit à bit dans le temps.

Avec devkitPro local, `make -C apps/console cia` ou `release` demande également makerom,
bannertool et Python 3 dans PATH. Les PNG versionnés permettent de conserver un
build 3DSX normal sans ces outils de packaging.

L’identifiant **`000400000F3D3C00`** est fixé dans
[application.rsf](../apps/console/packaging/application.rsf) : le conserver permet les mises
à jour. C’est un identifiant homebrew privé, pas une attribution Nintendo garantie
sans collision. Les forks doivent choisir un autre identifiant et adapter le
vérificateur. N’écrasez jamais un autre logiciel portant cet identifiant.

La version CIA encode `vMAJOR.MINOR.PATCH` en `major × 1024 + minor × 16 + patch`.
Les limites sont respectivement 63, 63 et 15 ; les tags invalides ou de préversion
sont refusés. Le workflow de Release calcule la valeur automatiquement. En local,
`APP_VERSION=16 ./build.sh cia` remplace la valeur par défaut 1.

## Visuels et vérifications

Les dessins originaux viennent de `apps/console/source/graphics/decky.c`.
[L’exporteur](../tools/export_home_menu.c) produit une icône 48 × 48 et une bannière
256 × 128 ; librsvg utilise Inter pour le texte. Pour les régénérer :

```sh
docker run --rm -v "$PWD":/repo -w /repo 3decks-console-packaging:local \
  bash apps/console/packaging/generate_artwork.sh
```

Ajoutez `--check` pour comparer sans remplacer les PNG. Les visuels suivent la
licence du projet ; celle d’Inter reste dans [le dossier des polices](../tools/fonts).
Les sources et licences des outils tiers restent dans l’image de compilation.

Le build vérifie l’identifiant, les empreintes des sections exécutables, l’icône,
la bannière, la police embarquée et les permissions noyau utilisées par l’ELF.
La CI compile tous les formats et teste le rejet de paquets altérés.

Avant publication, vérifiez sur console : installation, icône/bannière, lancement,
appairage, persistance SD, découverte réseau, audio, retour HOME/reprise,
veille/réveil, sortie avec START et mise à jour d’un CIA précédent. Les tests sur
ordinateur ne remplacent pas ces essais matériels.
