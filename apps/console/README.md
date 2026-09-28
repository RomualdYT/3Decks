# Nintendo 3DS / 2DS application

The native C client discovers the computer over UDP and communicates through
framed TCP messages. `source/` contains the application, `tests/` contains host
tests, `romfs/` contains bundled resources, and `packaging/` contains HOME Menu
package assets.

From the repository root:

```sh
bash tools/test_console.sh
./build.sh all
```

The first command uses a local C compiler. The `.3dsx` and `.cia` build uses
Docker and devkitPro. See the [build guide](../../docs/CONSOLE_PACKAGING.md),
[architecture](../../docs/CONSOLE_ARCHITECTURE.md), and
[protocol](../../docs/PROTOCOL.md). [Français](README.fr.md).
