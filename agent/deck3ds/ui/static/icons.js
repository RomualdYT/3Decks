/* Libellés et dessins vectoriels des icônes proposées par l'éditeur. */

export const ICON_LABELS = {
  app: { fr: 'Applications', en: 'Applications' }, browser: { fr: 'Navigateur', en: 'Browser' },
  folder: { fr: 'Dossier', en: 'Folder' }, terminal: { fr: 'Terminal', en: 'Terminal' },
  mic: { fr: 'Micro', en: 'Microphone' }, 'mic-off': { fr: 'Micro coupé', en: 'Microphone off' },
  'volume-up': { fr: 'Volume haut', en: 'Volume up' }, 'volume-down': { fr: 'Volume bas', en: 'Volume down' },
  'volume-mute': { fr: 'Son coupé', en: 'Muted' }, play: { fr: 'Lecture', en: 'Play' },
  pause: { fr: 'Pause', en: 'Pause' }, next: { fr: 'Suivant', en: 'Next' },
  previous: { fr: 'Précédent', en: 'Previous' }, music: { fr: 'Musique', en: 'Music' },
  chat: { fr: 'Discussion', en: 'Chat' }, video: { fr: 'Vidéo', en: 'Video' },
  record: { fr: 'Enregistrement', en: 'Record' }, lock: { fr: 'Verrouillage', en: 'Lock' },
  page: { fr: 'Page', en: 'Page' }, power: { fr: 'Marche / arrêt', en: 'Power' },
  gear: { fr: 'Réglages', en: 'Settings' }, star: { fr: 'Favori', en: 'Favourite' },
};

const ICON_PATHS = {
  app: '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
  browser: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  folder: '<path d="M3 7h7l2 2h9v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 9V6a2 2 0 0 1 2-2h5l2 3"/>',
  terminal: '<path d="m5 7 4 4-4 4M11 16h8"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6"/>',
  'mic-off': '<path d="m3 3 18 18M9 9v2a3 3 0 0 0 5 2M15 10V6a3 3 0 0 0-5.6-1.5M5 11a7 7 0 0 0 11 5.7M19 11a7 7 0 0 1-.4 2.3M12 18v3M9 21h6"/>',
  'volume-up': '<path d="M4 10v4h4l5 4V6L8 10zM17 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
  'volume-down': '<path d="M4 10v4h4l5 4V6L8 10zM17 10v4"/>',
  'volume-mute': '<path d="M4 10v4h4l5 4V6L8 10zM17 10l4 4M21 10l-4 4"/>',
  play: '<path d="m8 5 11 7-11 7z"/>',
  pause: '<path d="M8 5v14M16 5v14"/>',
  next: '<path d="m6 5 8 7-8 7zM17 5v14"/>',
  previous: '<path d="m18 5-8 7 8 7zM7 5v14"/>',
  music: '<path d="M9 18V5l10-2v13M9 10l10-2"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>',
  chat: '<path d="M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8l-5 4v-4H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"/><path d="M8 9h8M8 13h5"/>',
  video: '<rect x="3" y="5" width="14" height="14" rx="2"/><path d="m17 10 4-3v10l-4-3z"/>',
  record: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  page: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  power: '<path d="M12 3v9M7 5.5a8 8 0 1 0 10 0"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/>',
  star: '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-2.9-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h3M11 12h9M4 18h8M16 18h4"/><circle cx="16" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="14" cy="18" r="2"/>',
};

export function iconSvg(name, className = 'icon') {
  const content = ICON_PATHS[name] || ICON_PATHS.app;
  return `<span class="${className}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${content}</svg></span>`;
}
