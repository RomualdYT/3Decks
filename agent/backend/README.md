# Backend

The companion agent is split into three focused areas:

- `deck3ds/`: Python runtime and protocol implementation;
- `deck3ds/platforms/`: operating-system integrations;
- `deck3ds/ui/`: local HTTP API and compiled frontend assets;
- `windows/`: MSIX packaging metadata.

From the parent `agent/` directory, keep using `python3 -m deck3ds`. The small
compatibility package at `agent/deck3ds/` redirects imports to this directory so
development commands remain unchanged.

