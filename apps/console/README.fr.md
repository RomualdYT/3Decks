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
