import type { Locale } from "../app/types";

const COPY = {
  fr: {
    extensions: "Extensions",
    editor: "Éditeur", settings: "Réglages", status: "État", save: "Enregistrer", cancel: "Annuler",
    unsaved: "Modifications non enregistrées", pages: "Mes pages", addPage: "Ajouter une page", pageSettings: "Réglages de la page",
    selectSlot: "Sélectionnez un emplacement pour ajouter une action, puis personnalisez-la à droite.", addAction: "Ajouter une action",
    changeAction: "Changer l’action", emptySlot: "Ajouter", buttonSettings: "Réglages du bouton", icon: "Icône", color: "Couleur",
    action: "Action", delete: "Supprimer", page: "Page", button: "Bouton", titleFr: "Titre français", titleEn: "Titre anglais",
    labelFr: "Libellé français", labelEn: "Libellé anglais", technicalId: "Identifiant technique", dashboard: "Écran supérieur",
    layout: "Disposition", source: "Contenu automatique", grid: "Grille 3 × 2", list: "Liste", manual: "Boutons configurés ici",
    windows: "Fenêtres ouvertes", searchActions: "Rechercher une action…", available: "Disponible", setup: "Configuration requise",
    connection: "Connexion", features: "Fonctionnalités", appearance: "Langue & apparence", obs: "OBS Studio", advanced: "Avancé",
    connectionTitle: "Connexion de la console", connectionHelp: "Votre 3DS détecte automatiquement cet ordinateur sur le réseau local.", copy: "Copier",
    copied: "Copié", security: "Sécurité du réseau", tokenHelp: "Exige un code à usage unique pour chaque nouvelle console.",
    enabled: "Activé", disabled: "Désactivé", featureTitle: "Fonctionnalités de la console", featureHelp: "Choisissez précisément les données que 3Decks peut lire et transmettre.",
    unavailablePlatform: "Indisponible sur cette plateforme", setupPermission: "Une autorisation système pourra être demandée à l’activation.",
    permissionRequired: "Une autorisation macOS est nécessaire pour lire ces informations.", openPermissions: "Ouvrir les autorisations", openingPermissions: "Ouverture…", permissionsOpened: "Réglages système ouverts. Autorisez 3Decks (ou votre Terminal), puis revenez ici.",
    language: "Langue de l’interface", french: "Français", english: "English", obsTitle: "Connexion à OBS Studio", obsHelp: "Activez OBS WebSocket pour changer de scène depuis la console.",
    test: "Tester la connexion", testing: "Connexion…", connected: "Connecté", scenes: "Scènes détectées", host: "Adresse", port: "Port", password: "Mot de passe", timeout: "Délai maximal",
    statusTitle: "État de 3Decks", statusHelp: "Diagnostic local, consoles connectées et derniers événements.", noConsole: "Aucune console", consoles: "{count} console(s)",
    online: "3Decks disponible", offline: "3Decks injoignable", capabilities: "Fonctions disponibles", logs: "Journal récent", version: "Version", platform: "Plateforme", listen: "Écoute", address: "Adresse 3DS",
    saved: "Configuration enregistrée. La console sera mise à jour automatiquement.", loadError: "Chargement impossible : {message}", saveError: "Enregistrement refusé : {message}",
    appearanceHelp: "Choisissez la langue de l’interface et personnalisez la présence de Decky.",
    actionHelp: "Choisissez une action compréhensible : les champs nécessaires apparaîtront automatiquement.", selected: "Sélectionné", close: "Fermer",
  },
  en: {
    extensions: "Extensions",
    editor: "Editor", settings: "Settings", status: "Status", save: "Save", cancel: "Cancel", unsaved: "Unsaved changes",
    pages: "My pages", addPage: "Add a page", pageSettings: "Page settings", selectSlot: "Select a slot to add an action, then customise it on the right.",
    addAction: "Add an action", changeAction: "Change action", emptySlot: "Add", buttonSettings: "Button settings", icon: "Icon", color: "Colour",
    action: "Action", delete: "Delete", page: "Page", button: "Button", titleFr: "French title", titleEn: "English title", labelFr: "French label", labelEn: "English label",
    technicalId: "Technical ID", dashboard: "Top screen", layout: "Layout", source: "Automatic content", grid: "3 × 2 grid", list: "List", manual: "Buttons configured here", windows: "Open windows",
    searchActions: "Search actions…", available: "Available", setup: "Setup required", connection: "Connection", features: "Features", appearance: "Language & appearance", obs: "OBS Studio", advanced: "Advanced",
    connectionTitle: "Console connection", connectionHelp: "Your 3DS automatically finds this computer on the local network.", copy: "Copy", copied: "Copied", security: "Network security", tokenHelp: "Requires a one-time code for every new console. ",
    enabled: "Enabled", disabled: "Disabled", featureTitle: "Console features", featureHelp: "Choose exactly which data 3Decks may read and send.", unavailablePlatform: "Unavailable on this platform", setupPermission: "A system permission may be requested when enabled.",
    permissionRequired: "A system permission is required to read this information.", openPermissions: "Open permissions", openingPermissions: "Opening…", permissionsOpened: "System Settings opened. Allow 3Decks (or your Terminal), then return here.",
    language: "Interface language", french: "Français", english: "English", obsTitle: "OBS Studio connection", obsHelp: "Enable OBS WebSocket to switch scenes from the console.",
    test: "Test connection", testing: "Connecting…", connected: "Connected", scenes: "Detected scenes", host: "Host", port: "Port", password: "Password", timeout: "Timeout",
    statusTitle: "3Decks status", statusHelp: "Local diagnostics, connected consoles and recent events.", noConsole: "No console", consoles: "{count} console(s)", online: "3Decks available", offline: "3Decks unreachable",
    capabilities: "Available features", logs: "Recent log", version: "Version", platform: "Platform", listen: "Listening", address: "3DS address",
    saved: "Configuration saved. The console will update automatically.", loadError: "Could not load: {message}", saveError: "Could not save: {message}",
    appearanceHelp: "Choose the interface language and customize Decky’s presence.", actionHelp: "Choose a clear action: the required fields will appear automatically.", selected: "Selected", close: "Close",
  },
} as const;

export type CopyKey = keyof typeof COPY.fr;

export function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem("deck3ds.locale");
    if (saved === "fr" || saved === "en") return saved;
  } catch { /* Fall back to the system/browser language. */ }
  return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
}

export function translate(locale: Locale, key: CopyKey, values: Record<string, string | number> = {}): string {
  let text: string = COPY[locale][key];
  for (const [name, value] of Object.entries(values)) text = text.replaceAll(`{${name}}`, String(value));
  return text;
}

/** Save explicit choices so onboarding and the editor share one preference. */
export function saveLocale(locale: Locale): void {
  try { localStorage.setItem("deck3ds.locale", locale); } catch { /* Session-only choice. */ }
}
