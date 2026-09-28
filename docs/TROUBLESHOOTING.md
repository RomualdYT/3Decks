# Troubleshooting

- **No computer appears on the console:** check that both devices share the same trusted Wi-Fi network; guest isolation, VPNs and firewalls can block UDP discovery. Try the console's manual IP/port setting. The default ports are UDP 38122 and TCP 38123.
- **Desktop startup says a port is in use:** close the other 3Decks instance or process using UDP 38122/TCP 38123, then relaunch the desktop app.
- **A control needs permission:** revisit the setup assistant from Advanced settings and grant the OS permission requested for that feature. macOS may require quitting and reopening 3Decks.
- **Windows notifications unavailable:** the current direct installer has no package identity. Other Windows integrations should be checked with the [test plan](../apps/desktop/docs/WINDOWS_TEST_PLAN.md).
- **Update unavailable:** development builds have no embedded updater key. Public updates require a signed published Release and `latest.json`.
