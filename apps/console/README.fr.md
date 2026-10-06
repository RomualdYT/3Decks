# Application 3DS / 2DS

Le client natif C communique avec l’application ordinateur par découverte UDP et
trames TCP. Son code est dans `source/`, ses tests hôtes dans `tests/`, ses
ressources embarquées dans `romfs/` et les fichiers du paquet HOME dans
`packaging/`.

Depuis la racine du dépôt :

```sh
bash tools/test_console.sh
./build.sh all
```

Le premier contrôle utilise un compilateur C local. La construction `.3dsx` et
`.cia` utilise Docker et devkitPro. Voir le [guide de compilation](../../docs/CONSOLE_PACKAGING.fr.md),
l’[architecture](../../docs/CONSOLE_ARCHITECTURE.fr.md) et le
[protocole](../../docs/PROTOCOL.md).

## Typographie sur console

Les six tailles d’Inter sont rasterisées séparément : 13, 14, 15, 17, 20 et
24 pixels par cellule. Le manifeste `source/graphics/font_faces.def` définit
les tailles partagées par le rendu et le générateur. Depuis la racine,
`./tools/make-font.sh` régénère les six BCFNT avec une image devkitPro fixée
par empreinte et vérifie leurs dimensions avant de remplacer les ressources.
Les assets sont versionnés : une compilation ordinaire ne les régénère pas.

Citro2D normalise les polices à 30 pixels. Les styles utilisent donc
`hauteur_native / 30`, sans correction supplémentaire. Le rendu échantillonne
alors un texel par pixel et conserve l’anticrénelage de la police, avec des
positions entières. Le cache distingue le libellé **et** la police. Une
ressource absente ou de taille incorrecte utilise la police historique,
puis la police système si nécessaire ; les échelles libres conservent le
filtrage lissé historique.

La famille native ajoute environ 3 Mio de textures et de ressources embarquées.
Les tests hôtes couvrent les tailles, les alignements, les changements de police
dans le cache, le repli et la libération des ressources. L’aspect final reste
à apprécier sur les écrans physiques, notamment pour les petits caractères et
les informations secondaires sous les reflets.

## Icônes de marque

Le logo Spotify est rasterisé à sa taille native de 16 × 16 pixels depuis
`packaging/brands/spotify.svg`, puis stocké en RGBA8 dans RomFS. L’anticrénelage
est intégré à la texture ; le rendu conserve une échelle de 1:1 et aligne sa
position sur les pixels après le décalage stéréoscopique.

Pour le régénérer depuis la racine du dépôt :

```sh
docker build -t 3decks-console-packaging:local -f apps/console/packaging/Dockerfile .
bash tools/make-brand-icons.sh
```

Le fichier `.t3x` est versionné : la compilation normale ne nécessite aucune
rasterisation SVG. Si son chargement échoue, une icône musicale générique prend
le relais.
## Icônes des boutons sur console

Les 22 icônes de la console utilisent les mêmes composants Lucide et le même
trait de 1,9 pixel que `frontend/src/components/DeckIcon.tsx`.
`source/graphics/icon_assets.def` relie les identifiants 3DS aux noms de
l'éditeur et fixe l'ordre des atlas. Six atlas RGBA couvrent les tailles natives
de 12 à 52 pixels ; Citro2D applique la couleur et l'état de chaque bouton.
Les anciens dessins restent disponibles si un atlas ne se charge pas.

Après une modification des icônes PC, régénérer et versionner les atlas avec
`node tools/build_console_icons.mjs`. Il faut les dépendances du frontend et
l'image Docker de packaging décrite plus haut. Le générateur vérifie l'ordre
des indices produit par tex3ds. La licence Lucide figure dans
`packaging/icons/LUCIDE-LICENSE`.
