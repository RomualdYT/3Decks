# Qualification des versions

[Documentation](README.fr.md) · [English](QUALIFICATION.md)

Avant publication, installez les paquets sur macOS Intel/Apple Silicon et Windows
x64. Consignez versions d'OS, matériel, versions des paquets et résultats.

- Vérifiez les signatures ad hoc macOS, l’autorisation du premier lancement dans Confidentialité et sécurité, les avertissements d’installation Windows et les sommes de contrôle. Aucune signature Authenticode Windows ni notarisation Apple n’est attendue.
- Vérifiez premier lancement, assistant, langue/préférences, menu et cycle de vie de la fenêtre.
- Vérifiez permissions, médias, audio, notifications disponibles, OBS et raccourcis.
- Appairez une vraie console ; vérifiez pages, reconnexion, veille/réveil et retours d'action.
- Importez Focus ; vérifiez sa source, son écran, la sauvegarde du minuteur et les traductions.
- Comparez `latest.json` aux paquets et à leurs signatures de mise à jour Tauri. Si une version précédente
  existe, vérifiez sa mise à jour, la conservation des données et le redémarrage.

Consignez les échecs non résolus dans le brouillon ; publiez après réussite des
vérifications. Voir [Publication](RELEASE.fr.md),
[vérifications Windows](../apps/desktop/docs/WINDOWS_TEST_PLAN.md),
[vérifications macOS](../apps/desktop/docs/MACOS_TRAY_AND_SHORTCUTS_TEST.md) et
[mesures de performance](PERFORMANCE.fr.md).
