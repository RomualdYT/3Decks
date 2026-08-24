/* Interface locale de configuration de 3Decks, sans dépendance ni build. */

'use strict';

/* Accès à l'agent ---------------------------------------------------------- */

const TOKEN_KEY = 'deck3ds.token';
const LOCALE_KEY = 'deck3ds.locale';

function readToken() {
  const fromUrl = new URLSearchParams(location.search).get('token');
  if (fromUrl) {
    try {
      sessionStorage.setItem(TOKEN_KEY, fromUrl);
    } catch (error) {
      // Le jeton reste en mémoire si le stockage de session est refusé.
    }
    history.replaceState(null, '', location.pathname);
    return fromUrl;
  }
  try {
    return sessionStorage.getItem(TOKEN_KEY) || '';
  } catch (error) {
    return '';
  }
}

let TOKEN = readToken();

function forgetToken() {
  TOKEN = '';
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (error) { /* déjà oublié */ }
}

async function api(method, path, body) {
  const options = { method, headers: { 'X-Deck3DS-Token': TOKEN } };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`Réponse illisible de l’agent : ${text.slice(0, 200)}`);
  }

  if (response.status === 403) {
    forgetToken();
    throw new Error(
      'Le lien de configuration a expiré. Ouvrez le nouveau lien affiché par l’agent.'
    );
  }
  if (!response.ok) throw new Error(payload.error || `Erreur HTTP ${response.status}`);
  return payload;
}

/* Traductions --------------------------------------------------------------- */

const COPY = {
  fr: {
    editor: 'Éditeur', settings: 'Réglages', status: 'État de l’agent',
    save: 'Enregistrer', reload: 'Annuler', dirty: 'Modifications non enregistrées',
    noConsole: 'Aucune console', oneConsole: '1 console', consoles: '{count} consoles',
    unreachable: 'Agent injoignable', myPages: 'Mes pages', addPage: 'Ajouter une page',
    createPages: 'Créez vos pages', createPagesHelp: 'Ajoutez des pages pour organiser vos actions.',
    pageCount: '{count} / {limit} pages', pageTitle: 'Page {name}',
    chooseSlot: 'Choisissez un emplacement puis une action.',
    touchSlot: 'Touchez un emplacement pour choisir son action.',
    previewNote: 'Le visuel représente la disposition actuelle de votre console.',
    addActions: 'Ajoutez des actions', addActionsHelp: 'Sélectionnez un emplacement vide, puis choisissez une action.',
    saveConfig: 'Enregistrez', saveConfigHelp: 'La configuration est envoyée automatiquement à la console.',
    addAction: 'Ajouter une action', changeAction: 'Changer l’action',
    searchAction: 'Rechercher une action', supported: 'Disponible', unavailable: 'À configurer',
    supportNote: 'Les actions indisponibles sont signalées clairement. Vous pouvez les préparer puis configurer l’intégration correspondante.',
    pageSettings: 'Réglages de la page', buttonSettings: 'Réglages du bouton',
    selectButtonHelp: 'Sélectionnez un bouton pour modifier son texte, son apparence ou son action.',
    emptySlot: 'Ajouter un bouton ici', moveHint: 'Glissez les boutons pour les réorganiser.',
    id: 'Identifiant technique', titleEn: 'Titre anglais', titleFr: 'Titre français',
    labelEn: 'Libellé anglais', labelFr: 'Libellé français', icon: 'Icône', color: 'Couleur',
    chooseIcon: 'Choisir une icône', gridLayout: 'Grille 3 × 2', listLayout: 'Liste',
    gridLayoutHelp: 'Six boutons immédiatement accessibles.', listLayoutHelp: 'Fenêtres défilantes alimentées par l’agent.',
    listNeedsSource: 'La liste est disponible avec un contenu automatique.',
    dashboard: 'Écran supérieur', layout: 'Disposition', automaticSource: 'Contenu automatique',
    noSource: 'Boutons définis ici', windowsSource: 'Fenêtres ouvertes',
    deletePage: 'Supprimer la page', deleteButton: 'Supprimer le bouton', backToPage: 'Réglages de la page',
    action: 'Action', followedState: 'État suivi', noFollowedState: 'Aucun',
    actionUnsupported: 'Cette action nécessite une fonction qui n’est pas encore disponible ou configurée. Le bouton restera visible mais ne fera rien.',
    configureObs: 'Configurer OBS Studio', argumentMissing: 'Renseignez ce champ avant d’enregistrer.',
    connection: 'Connexion', preferences: 'Préférences', obsStudio: 'OBS Studio', notConfigured: 'Non configuré',
    connectionTitle: 'Connexion à la console',
    connectionIntro: 'Ces réglages permettent à votre 3DS de trouver cet ordinateur sur votre réseau local.',
    connectionAddress: 'Adresse de connexion', copy: 'Copier', copied: 'Adresse copiée.',
    connectionInstruction: 'Sur la 3DS, ouvrez Réglages puis saisissez cette adresse.',
    networkSecurity: 'Sécurité du réseau',
    networkSecurityHelp: 'Un jeton partagé limite le contrôle de cet ordinateur à vos consoles configurées.',
    enabledRecommended: 'Activé (recommandé)', disabled: 'Désactivé',
    securityEnabled: 'Un jeton a été généré. Reportez-le également dans les réglages de la 3DS.',
    securityDisabled: 'Sans jeton, toute console présente sur votre réseau local peut agir sur cet ordinateur.',
    advancedSettings: 'Réglages avancés', listenAddress: 'Adresse d’écoute', port: 'Port',
    refresh: 'Rafraîchissement', volumeStep: 'Pas de volume', seconds: 'secondes',
    restartNote: 'L’adresse d’écoute et le port s’appliquent au prochain démarrage de l’agent.',
    languageTitle: 'Langue de l’interface', languageHelp: 'Les boutons peuvent avoir un libellé français et anglais. La 3DS affiche la variante correspondant à sa langue.',
    french: 'Français', english: 'English',
    preferencesTitle: 'Préférences', preferencesIntro: 'Adaptez l’éditeur et les commandes à votre façon de travailler.',
    labelsLanguages: 'Langues des boutons', labelsLanguagesHelp: 'Chaque page et chaque bouton accepte un texte dans les deux langues.',
    displayLanguage: 'Langue affichée dans l’aperçu', displayLanguageHelp: 'Ce choix modifie aussi la langue de l’éditeur sur cet appareil.',
    obsTitle: 'Connexion à OBS Studio',
    obsIntro: 'Activez le serveur WebSocket d’OBS, puis testez la connexion pour récupérer vos scènes.',
    obsEnabled: 'Activer les actions OBS', obsHost: 'Adresse', obsPort: 'Port WebSocket',
    obsPassword: 'Mot de passe', obsTimeout: 'Délai maximal', testConnection: 'Tester la connexion',
    testing: 'Test en cours…', obsConnected: 'Connecté à OBS {version}. {count} scène(s) détectée(s).',
    obsScenes: 'Scènes détectées', obsSetupHelp: 'Dans OBS : Outils → Paramètres du serveur WebSocket. Le port par défaut est 4455.',
    obsPasswordHelp: 'Le mot de passe est conservé localement dans config.json.',
    aboutConnection: 'À propos de la connexion',
    connectionHelp: 'La 3DS et cet ordinateur doivent être connectés au même réseau local.',
    obsPreview: 'Préparation OBS Studio', obsPreviewHelp: 'Après un test réussi, les scènes détectées sont proposées directement dans les boutons OBS.',
    statusTitle: 'État de l’agent', statusIntro: 'Vérifiez en un coup d’œil la connexion, les fonctions disponibles et les derniers événements.',
    listening: 'Écoute', addressFor3ds: 'Adresse pour la 3DS', platform: 'Plateforme', version: 'Version',
    connectedConsoles: 'Consoles connectées', token: 'Jeton réseau', defined: 'Défini', absent: 'Absent',
    capabilities: 'Fonctions disponibles', logs: 'Journal récent', yes: 'Oui', no: 'Non',
    noStatus: 'L’état de l’agent est momentanément indisponible.', dynamicContent: 'Contenu rempli automatiquement par l’agent.',
    dynamicWindow: 'Fenêtre {number}', dynamicListHint: 'Liste mise à jour automatiquement',
    noMedia: 'Aucun média en lecture.', producedByAgent: 'Contenu « {name} » produit par l’agent.',
    saved: 'Configuration enregistrée. La console se met à jour dans un instant.',
    loadFailed: 'Chargement impossible : {message}', saveFailed: 'Enregistrement refusé : {message}',
    unsavedConfirm: 'Des modifications non enregistrées seront perdues. Continuer ?',
    deleteRefs: 'Des boutons renvoient vers cette page. Ils deviendront invalides. Supprimer quand même ?',
    pageNameDefault: 'Nouvelle page', noScripts: 'Aucun script n’est déclaré dans config.json.',
    scriptsReadonly: 'Les scripts restent en lecture seule dans cet éditeur pour éviter toute exécution de commande depuis le navigateur.',
    filterAll: 'Toutes', close: 'Fermer',
  },
  en: {
    editor: 'Editor', settings: 'Settings', status: 'Agent status',
    save: 'Save', reload: 'Cancel', dirty: 'Unsaved changes',
    noConsole: 'No console', oneConsole: '1 console', consoles: '{count} consoles',
    unreachable: 'Agent unreachable', myPages: 'My pages', addPage: 'Add a page',
    createPages: 'Create your pages', createPagesHelp: 'Add pages to organise your actions.',
    pageCount: '{count} / {limit} pages', pageTitle: '{name} page',
    chooseSlot: 'Choose a slot, then choose an action.', touchSlot: 'Tap a slot to choose its action.',
    previewNote: 'The preview reflects the current layout on your console.',
    addActions: 'Add actions', addActionsHelp: 'Select an empty slot, then choose an action.',
    saveConfig: 'Save', saveConfigHelp: 'The layout is sent to the console automatically.',
    addAction: 'Add an action', changeAction: 'Change action', searchAction: 'Search actions',
    supported: 'Available', unavailable: 'Setup needed',
    supportNote: 'Unavailable actions are clearly marked. You can prepare them now and configure the related integration later.',
    pageSettings: 'Page settings', buttonSettings: 'Button settings',
    selectButtonHelp: 'Select a button to change its text, appearance or action.',
    emptySlot: 'Add a button here', moveHint: 'Drag buttons to rearrange them.',
    id: 'Technical identifier', titleEn: 'English title', titleFr: 'French title',
    labelEn: 'English label', labelFr: 'French label', icon: 'Icon', color: 'Colour',
    chooseIcon: 'Choose an icon', gridLayout: '3 × 2 grid', listLayout: 'List',
    gridLayoutHelp: 'Six buttons available at a glance.', listLayoutHelp: 'Scrollable windows supplied by the agent.',
    listNeedsSource: 'List view is available with automatic content.',
    dashboard: 'Top screen', layout: 'Layout', automaticSource: 'Automatic content',
    noSource: 'Buttons defined here', windowsSource: 'Open windows',
    deletePage: 'Delete page', deleteButton: 'Delete button', backToPage: 'Page settings',
    action: 'Action', followedState: 'Tracked state', noFollowedState: 'None',
    actionUnsupported: 'This action needs a feature that is not available or configured yet. The button will remain visible but will not run.',
    configureObs: 'Set up OBS Studio', argumentMissing: 'Fill in this field before saving.',
    connection: 'Connection', preferences: 'Preferences', obsStudio: 'OBS Studio', notConfigured: 'Not configured',
    connectionTitle: 'Console connection',
    connectionIntro: 'These settings help your 3DS find this computer on your local network.',
    connectionAddress: 'Connection address', copy: 'Copy', copied: 'Address copied.',
    connectionInstruction: 'On the 3DS, open Settings and enter this address.',
    networkSecurity: 'Network security',
    networkSecurityHelp: 'A shared token limits control of this computer to your configured consoles.',
    enabledRecommended: 'Enabled (recommended)', disabled: 'Disabled',
    securityEnabled: 'A token was generated. Enter it in the 3DS settings as well.',
    securityDisabled: 'Without a token, any console on your local network can control this computer.',
    advancedSettings: 'Advanced settings', listenAddress: 'Listen address', port: 'Port',
    refresh: 'Refresh interval', volumeStep: 'Volume step', seconds: 'seconds',
    restartNote: 'The listen address and port apply after restarting the agent.',
    languageTitle: 'Interface language', languageHelp: 'Buttons can have French and English labels. The 3DS shows the matching variant.',
    french: 'Français', english: 'English',
    preferencesTitle: 'Preferences', preferencesIntro: 'Adapt the editor and controls to the way you work.',
    labelsLanguages: 'Button languages', labelsLanguagesHelp: 'Every page and button can provide text in both languages.',
    displayLanguage: 'Preview language', displayLanguageHelp: 'This choice also changes the editor language on this device.',
    obsTitle: 'OBS Studio connection',
    obsIntro: 'Enable the OBS WebSocket server, then test the connection to load your scenes.',
    obsEnabled: 'Enable OBS actions', obsHost: 'Address', obsPort: 'WebSocket port',
    obsPassword: 'Password', obsTimeout: 'Timeout', testConnection: 'Test connection', testing: 'Testing…',
    obsConnected: 'Connected to OBS {version}. {count} scene(s) found.', obsScenes: 'Detected scenes',
    obsSetupHelp: 'In OBS: Tools → WebSocket Server Settings. The default port is 4455.',
    obsPasswordHelp: 'The password is stored locally in config.json.',
    aboutConnection: 'About the connection', connectionHelp: 'The 3DS and this computer must be on the same local network.',
    obsPreview: 'OBS Studio setup', obsPreviewHelp: 'After a successful test, detected scenes are offered directly when configuring OBS buttons.',
    statusTitle: 'Agent status', statusIntro: 'Quickly check connectivity, available features and recent events.',
    listening: 'Listening on', addressFor3ds: '3DS address', platform: 'Platform', version: 'Version',
    connectedConsoles: 'Connected consoles', token: 'Network token', defined: 'Set', absent: 'Missing',
    capabilities: 'Available features', logs: 'Recent log', yes: 'Yes', no: 'No',
    noStatus: 'Agent status is temporarily unavailable.', dynamicContent: 'Content filled automatically by the agent.',
    dynamicWindow: 'Window {number}', dynamicListHint: 'List updated automatically',
    noMedia: 'No media is playing.', producedByAgent: '“{name}” content produced by the agent.',
    saved: 'Configuration saved. The console will update in a moment.',
    loadFailed: 'Could not load: {message}', saveFailed: 'Could not save: {message}',
    unsavedConfirm: 'Unsaved changes will be lost. Continue?',
    deleteRefs: 'Some buttons point to this page and will become invalid. Delete anyway?',
    pageNameDefault: 'New page', noScripts: 'No script is declared in config.json.',
    scriptsReadonly: 'Scripts remain read-only in this editor to prevent command execution from the browser.',
    filterAll: 'All', close: 'Close',
  },
};

function initialLocale() {
  try {
    const saved = localStorage.getItem(LOCALE_KEY);
    if (saved === 'fr' || saved === 'en') return saved;
  } catch (error) { /* langue du navigateur ci-dessous */ }
  return navigator.language.toLowerCase().startsWith('fr') ? 'fr' : 'en';
}

function t(key, values = {}) {
  const table = COPY[state.locale] || COPY.fr;
  let text = table[key] || COPY.fr[key] || key;
  Object.entries(values).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, String(value));
  });
  return text;
}

/* Catalogue d'actions ------------------------------------------------------ */

const CATEGORIES = [
  ['essential', { fr: 'Essentiels', en: 'Essentials' }],
  ['audio', { fr: 'Audio', en: 'Audio' }],
  ['media', { fr: 'Média', en: 'Media' }],
  ['apps', { fr: 'Applications', en: 'Applications' }],
  ['obs', { fr: 'OBS Studio', en: 'OBS Studio' }],
  ['navigation', { fr: 'Navigation', en: 'Navigation' }],
  ['advanced', { fr: 'Avancé', en: 'Advanced' }],
];

const ACTIONS = {
  'app.launch': action('essential', 'app', '#4F8DF7', 'Ouvrir une application', 'Open an application', 'Lance ou remet au premier plan un programme.', 'Launches or focuses a program.'),
  'hotkey': action('essential', 'star', '#7C6BF2', 'Raccourci clavier', 'Keyboard shortcut', 'Déclenche une combinaison de touches.', 'Runs a keyboard shortcut.'),
  'url.open': action('essential', 'browser', '#36A6D8', 'Ouvrir un site web', 'Open a website', 'Ouvre une adresse dans le navigateur.', 'Opens an address in the browser.'),
  'path.open': action('essential', 'folder', '#D99B46', 'Ouvrir un fichier ou dossier', 'Open a file or folder', 'Ouvre un élément dans l’explorateur de fichiers.', 'Opens an item in the file explorer.'),
  'volume.up': action('audio', 'volume-up', '#3B82F6', 'Monter le volume', 'Volume up', 'Augmente le volume de l’ordinateur.', 'Raises the computer volume.'),
  'volume.down': action('audio', 'volume-down', '#3B82F6', 'Baisser le volume', 'Volume down', 'Baisse le volume de l’ordinateur.', 'Lowers the computer volume.'),
  'volume.set': action('audio', 'volume-up', '#3B82F6', 'Régler le volume', 'Set volume', 'Applique un niveau précis.', 'Sets a precise volume level.'),
  'volume.mute_toggle': action('audio', 'volume-mute', '#F59E0B', 'Couper / rétablir le son', 'Mute / unmute', 'Bascule le son général.', 'Toggles system sound.'),
  'mic.mute_toggle': action('audio', 'mic', '#F59E0B', 'Couper / activer le micro', 'Mute / unmute mic', 'Bascule le microphone système.', 'Toggles the system microphone.'),
  'mic.mute': action('audio', 'mic-off', '#EF6A71', 'Couper le micro', 'Mute microphone', 'Force le microphone en sourdine.', 'Forces the microphone off.'),
  'mic.unmute': action('audio', 'mic', '#45C995', 'Activer le micro', 'Unmute microphone', 'Force le microphone actif.', 'Forces the microphone on.'),
  'audio_output.cycle': action('audio', 'volume-up', '#8B78EA', 'Changer de sortie audio', 'Cycle audio output', 'Passe au casque, aux enceintes ou à l’écran suivant.', 'Cycles headphones, speakers and displays.'),
  'audio_output.set': action('audio', 'volume-up', '#8B78EA', 'Choisir une sortie audio', 'Choose audio output', 'Sélectionne une sortie par son nom.', 'Selects an output by name.'),
  'app_volume.up': action('audio', 'music', '#8B78EA', 'Monter le volume du lecteur', 'Player volume up', 'Ajuste uniquement le lecteur musical.', 'Adjusts only the music player.'),
  'app_volume.down': action('audio', 'music', '#8B78EA', 'Baisser le volume du lecteur', 'Player volume down', 'Ajuste uniquement le lecteur musical.', 'Adjusts only the music player.'),
  'app_volume.set': action('audio', 'music', '#8B78EA', 'Régler le volume du lecteur', 'Set player volume', 'Applique un niveau précis au lecteur.', 'Sets a precise player volume.'),
  'media.play_pause': action('media', 'play', '#5C8DFF', 'Lecture / pause', 'Play / pause', 'Pilote la lecture en cours.', 'Controls current playback.'),
  'media.next': action('media', 'next', '#5C8DFF', 'Piste suivante', 'Next track', 'Passe au média suivant.', 'Skips to the next item.'),
  'media.previous': action('media', 'previous', '#5C8DFF', 'Piste précédente', 'Previous track', 'Revient au média précédent.', 'Returns to the previous item.'),
  'app.quit': action('apps', 'power', '#EF6A71', 'Fermer une application', 'Quit an application', 'Ferme le programme indiqué.', 'Quits the selected program.'),
  'window.focus': action('apps', 'app', '#58B69B', 'Afficher une fenêtre', 'Focus a window', 'Ramène une fenêtre ouverte au premier plan.', 'Brings an open window to the front.'),
  'obs.scene.set': action('obs', 'video', '#7D73F1', 'Changer de scène OBS', 'Change OBS scene', 'Passe à une scène précise dans OBS Studio.', 'Switches to a specific OBS Studio scene.'),
  'obs.stream.toggle': action('obs', 'record', '#EF6A71', 'Démarrer / arrêter le stream', 'Start / stop stream', 'Bascule la diffusion en direct dans OBS.', 'Toggles live streaming in OBS.'),
  'obs.record.toggle': action('obs', 'record', '#EF6A71', 'Démarrer / arrêter l’enregistrement', 'Start / stop recording', 'Bascule l’enregistrement dans OBS.', 'Toggles recording in OBS.'),
  'obs.source.toggle': action('obs', 'video', '#7D73F1', 'Afficher / masquer une source', 'Show / hide a source', 'Bascule la visibilité d’une source dans une scène.', 'Toggles a source inside a scene.'),
  'page.open': action('navigation', 'page', '#43A6CF', 'Ouvrir une autre page', 'Open another page', 'Affiche une page de boutons sur la 3DS.', 'Opens another button page on the 3DS.'),
  'settings.open': action('navigation', 'gear', '#6D88AA', 'Ouvrir les réglages 3DS', 'Open 3DS settings', 'Affiche les réglages directement sur la console.', 'Opens settings directly on the console.'),
  'modal.volumes': action('navigation', 'volume-up', '#6D88AA', 'Ouvrir le panneau des volumes', 'Open volume panel', 'Affiche les volumes sur la console.', 'Shows volume controls on the console.'),
  'frame.toggle': action('navigation', 'video', '#6D88AA', 'Basculer le plein écran', 'Toggle full screen', 'Agrandit ou réduit l’affichage supérieur.', 'Toggles the top display full screen.'),
  'system.lock': action('advanced', 'lock', '#E98D54', 'Verrouiller l’ordinateur', 'Lock computer', 'Verrouille immédiatement la session.', 'Locks the current session.'),
  'script.run': action('advanced', 'terminal', '#E98D54', 'Exécuter un script autorisé', 'Run an allowed script', 'Lance un script déclaré dans config.json.', 'Runs a script declared in config.json.'),
  'noop': action('advanced', 'app', '#63758D', 'Ne rien faire', 'Do nothing', 'Laisse volontairement le bouton sans effet.', 'Intentionally leaves the button inactive.'),
};

function action(category, icon, color, frTitle, enTitle, frDescription, enDescription) {
  return {
    category, icon, color,
    title: { fr: frTitle, en: enTitle },
    description: { fr: frDescription, en: enDescription },
  };
}

function actionMeta(kind) {
  return ACTIONS[kind] || action('advanced', 'app', '#63758D', kind, kind, 'Action avancée.', 'Advanced action.');
}

const ICON_LABELS = {
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

function iconLabel(name) {
  return ICON_LABELS[name]?.[state.locale] || name;
}

/* État et utilitaires ------------------------------------------------------ */

const state = {
  schema: null,
  config: null,
  saved: null,
  status: null,
  locale: initialLocale(),
  view: 'editor',
  settingsSection: 'connection',
  pageIndex: 0,
  selectedSlot: null,
  picker: { open: false, slot: null, mode: 'add', query: '', category: 'essential' },
  advancedOpen: false,
  obsTest: null,
  obsTesting: false,
  mobileMenu: false,
};

const el = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]
  ));
}

function currentPage() { return state.config?.pages?.[state.pageIndex] || null; }

function currentButton() {
  const page = currentPage();
  return page ? (page.buttons || []).find((item) => item.slot === state.selectedSlot) : null;
}

function isDirty() { return JSON.stringify(state.config) !== JSON.stringify(state.saved); }

function textFor(value, locale = state.locale) {
  if (typeof value === 'string') return value;
  if (value && typeof value === 'object') return value[locale] || value.en || value.fr || '';
  return '';
}

function setLocalizedText(value, locale, next) {
  const object = typeof value === 'object' && value
    ? { ...value }
    : { en: typeof value === 'string' ? value : '', fr: typeof value === 'string' ? value : '' };
  object[locale] = next;
  if (object.fr === object.en) return object.en;
  return object;
}

function actionKind(value) {
  if (typeof value === 'string') return value;
  return value && typeof value === 'object' ? value.type || 'noop' : 'noop';
}

function actionArgs(value) {
  if (!value || typeof value !== 'object') return {};
  const { type, ...rest } = value;
  return rest;
}

function actionInfo(kind) {
  return state.schema?.actions.find((item) => item.kind === kind) || null;
}

function actionSupported(value) {
  const kind = actionKind(value);
  if (kind.startsWith('obs.')) return Boolean(state.config?.integrations?.obs?.enabled);
  const info = actionInfo(kind);
  return info ? info.supported : true;
}

function uniqueId(prefix, taken) {
  let index = 1;
  while (taken.includes(`${prefix}${index}`)) index += 1;
  return `${prefix}${index}`;
}

function banner(message, kind) {
  const node = el('banner');
  node.textContent = message || '';
  node.classList.toggle('hidden', !message);
  node.classList.toggle('ok', kind === 'ok');
}

function normaliseColor(value) {
  const text = String(value || '#3B82F6');
  if (/^#[0-9a-f]{3}$/i.test(text)) return '#' + text.slice(1).split('').map((item) => item + item).join('');
  return /^#[0-9a-f]{6}$/i.test(text) ? text : '#3B82F6';
}

function iconSvg(name, className = 'icon') {
  const paths = {
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
  const content = paths[name] || paths.app;
  return `<span class="${className}" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${content}</svg></span>`;
}

/* Chargement et enregistrement -------------------------------------------- */

async function load() {
  try {
    const [schema, config] = await Promise.all([
      api('GET', '/api/schema'),
      api('GET', '/api/config'),
    ]);
    state.schema = schema;
    state.config = structuredClone(config.config);
    state.saved = structuredClone(config.config);
    ensureConfigShape();
    state.pageIndex = Math.max(0, Math.min(state.pageIndex, state.config.pages.length - 1));
    state.selectedSlot = null;
    banner('');
    render();
  } catch (error) {
    banner(t('loadFailed', { message: error.message }));
  }
}

function ensureConfigShape() {
  state.config.integrations = state.config.integrations || {};
  state.config.integrations.obs = {
    enabled: false, host: '127.0.0.1', port: 4455, password: '', timeout: 2,
    ...(state.config.integrations.obs || {}),
  };
  state.config.server = state.config.server || {};
}

async function save() {
  try {
    const result = await api('PUT', '/api/config', state.config);
    state.config = structuredClone(result.config);
    state.saved = structuredClone(result.config);
    ensureConfigShape();
    banner(t('saved'), 'ok');
    render();
  } catch (error) {
    banner(t('saveFailed', { message: error.message }));
  }
}

async function refreshStatus() {
  try {
    state.status = await api('GET', '/api/state');
  } catch (error) {
    state.status = null;
    if (!TOKEN) banner(error.message);
  }
  renderHeader();
  if (state.view === 'status' || state.view === 'settings') {
    renderWorkspace();
    renderDetail();
    bindDynamicUi();
  } else if (state.config) {
    renderDashboard(currentPage());
  }
}

/* Rendu global ------------------------------------------------------------- */

function render() {
  if (!state.config || !state.schema) return;
  document.documentElement.lang = state.locale;
  el('app-shell').setAttribute('aria-busy', 'false');
  renderHeader();
  renderSidebar();
  renderWorkspace();
  renderDetail();
  renderDrawer();
  bindDynamicUi();
}

function renderHeader() {
  document.title = `3Decks — ${t(state.view)}`;
  el('locale').value = state.locale;
  el('save').textContent = t('save');
  el('reload').textContent = t('reload');
  el('dirty').textContent = t('dirty');
  el('save').disabled = !state.config || !isDirty();
  el('dirty').classList.toggle('hidden', !state.config || !isDirty());

  el('main-nav').querySelectorAll('[data-view]').forEach((button) => {
    button.textContent = t(button.dataset.view);
    button.classList.toggle('active', button.dataset.view === state.view);
  });
  el('main-nav').classList.toggle('open', state.mobileMenu);
  el('mobile-menu').setAttribute('aria-expanded', String(state.mobileMenu));

  const clients = state.status?.clients || [];
  const chip = el('clients');
  chip.classList.toggle('connected', clients.length > 0);
  chip.querySelector('span').textContent = state.status
    ? (clients.length === 0 ? t('noConsole') : clients.length === 1 ? t('oneConsole') : t('consoles', { count: clients.length }))
    : t('unreachable');
}

function renderSidebar() {
  if (state.view === 'editor') renderEditorSidebar();
  else if (state.view === 'settings') renderSettingsSidebar();
  else renderStatusSidebar();
}

function renderEditorSidebar() {
  const limit = state.schema.limits.pages;
  const pages = state.config.pages.map((page, index) => `
    <li class="page-item ${index === state.pageIndex ? 'active' : ''}" data-page="${index}" draggable="true">
      ${iconSvg(page.icon || 'page')}
      <span class="page-name">${escapeHtml(textFor(page.title) || page.id)}</span>
      <span class="page-index">${index + 1}</span>
    </li>`).join('');

  const progress = Math.min(100, Math.max(34, (state.config.pages.length > 1 ? 66 : 34) + (totalButtons() > 1 ? 34 : 0)));
  el('sidebar').innerHTML = `
    <div class="sidebar-title"><h2>${t('myPages')}</h2></div>
    <div class="onboarding">
      <div class="onboarding-head"><span class="step-number">1</span><strong>${t('createPages')}</strong></div>
      <p>${t('createPagesHelp')}</p><progress class="progress" max="100" value="${progress}"></progress>
    </div>
    <ul class="page-list" id="page-list">${pages}</ul>
    <button class="add-page" id="add-page" type="button" ${state.config.pages.length >= limit ? 'disabled' : ''}>+&nbsp; ${t('addPage')}</button>
    <p class="page-limit">${t('pageCount', { count: state.config.pages.length, limit })}</p>
    <div class="help-steps">
      ${helpStep(1, t('createPages'), t('createPagesHelp'), state.config.pages.length > 0)}
      ${helpStep(2, t('addActions'), t('addActionsHelp'), totalButtons() > 1)}
      ${helpStep(3, t('saveConfig'), t('saveConfigHelp'), !isDirty())}
    </div>`;
}

function helpStep(number, title, help, done) {
  return `<div class="help-step ${done ? 'done' : ''}"><span class="step-number">${done ? '✓' : number}</span><div><strong>${title}</strong>${help}</div></div>`;
}

function totalButtons() {
  return state.config.pages.reduce((sum, page) => sum + (page.buttons || []).length, 0);
}

function renderSettingsSidebar() {
  const obsEnabled = state.config.integrations.obs.enabled;
  el('sidebar').innerHTML = `
    <div class="sidebar-title"><h2>${t('settings')}</h2></div>
    <ul class="settings-nav">
      ${settingsNavButton('connection', 'link', t('connection'))}
      ${settingsNavButton('preferences', 'sliders', t('preferences'))}
      ${settingsNavButton('obs', 'video', t('obsStudio'), obsEnabled ? '' : t('notConfigured'))}
    </ul>`;
}

function settingsNavButton(section, icon, label, substatus = '') {
  return `<li><button type="button" data-settings="${section}" class="${state.settingsSection === section ? 'active' : ''}">
    ${iconSvg(icon)}<span>${label}</span>${substatus ? `<span class="substatus">${substatus}</span>` : ''}
  </button></li>`;
}

function renderStatusSidebar() {
  const clients = state.status?.clients || [];
  el('sidebar').innerHTML = `
    <div class="sidebar-title"><h2>${t('status')}</h2></div>
    <div class="help-panel">
      <h3>${clients.length ? t(clients.length === 1 ? 'oneConsole' : 'consoles', { count: clients.length }) : t('noConsole')}</h3>
      <p>${state.status ? escapeHtml(`${state.status.platform} · ${state.status.version}`) : t('noStatus')}</p>
      <button class="button secondary full" type="button" data-view-jump="settings">${t('settings')}</button>
    </div>`;
}

function renderWorkspace() {
  if (state.view === 'editor') renderEditorWorkspace();
  else if (state.view === 'settings') renderSettingsWorkspace();
  else renderStatusWorkspace();
}

function renderEditorWorkspace() {
  const page = currentPage();
  if (!page) {
    el('workspace').innerHTML = `<p>${t('addPage')}</p>`;
    return;
  }
  const name = textFor(page.title) || page.id;
  el('workspace').innerHTML = `
    <div class="page-heading">
      <div><h1>${t('pageTitle', { name: escapeHtml(name) })}</h1><p>${matchMedia('(max-width: 820px)').matches ? t('touchSlot') : t('chooseSlot')}</p></div>
      <button class="button secondary compact" type="button" data-open-page-settings>${iconSvg('gear')} ${t('pageSettings')}</button>
    </div>
    <div class="device-stage">
      <div class="device-wrap">
        <img class="device-shell" src="/device-shell.png" alt="" draggable="false">
        <div class="live-screen top-live"><div class="dash-label" id="dash-label"></div><div class="dash-body" id="dash-body"></div></div>
        <div class="live-screen bottom-live">
          <div class="console-tabbar" id="tabbar"></div>
          <div class="button-grid" id="grid"></div>
          <div class="console-botbar" id="botbar"></div>
        </div>
      </div>
    </div>
    <p class="preview-note"><span class="info-dot">i</span>${t('previewNote')} ${t('moveHint')}</p>`;
  renderPreview();
}

function renderPreview() {
  const page = currentPage();
  if (!page || !el('grid')) return;
  el('tabbar').innerHTML = state.config.pages.map((item, index) => `
    <button type="button" class="console-tab ${index === state.pageIndex ? 'active' : ''}" data-console-page="${index}">${escapeHtml(textFor(item.title) || item.id)}</button>`).join('');
  renderDashboard(page);

  if (page.layout === 'list') {
    renderDynamicListPreview();
    el('botbar').textContent = '↕ · A';
    return;
  }

  if (page.source === 'windows') {
    renderDynamicGridPreview(page);
    el('botbar').textContent = 'B · A · Y';
    return;
  }

  const buttons = page.buttons || [];
  const slots = state.schema.limits.buttons_per_page;
  let html = '';
  for (let slot = 0; slot < slots; slot += 1) {
    const button = buttons.find((item) => item.slot === slot);
    html += button ? buttonSlot(button, slot) : emptySlot(slot);
  }
  el('grid').innerHTML = html;
  el('botbar').textContent = 'B · A · Y';
}

function renderDynamicGridPreview(page) {
  const supplied = (page.buttons || []).slice(0, state.schema.limits.buttons_per_page);
  const apps = state.status?.snapshot?.apps || [];
  let html = '';
  for (let slot = 0; slot < state.schema.limits.buttons_per_page; slot += 1) {
    const button = supplied.find((item) => item.slot === slot);
    const label = button ? textFor(button.label) : (apps[slot] || t('dynamicWindow', { number: slot + 1 }));
    const icon = button?.icon || 'app';
    html += `<div class="slot dynamic" aria-label="${escapeHtml(label)}">${iconSvg(icon)}<span class="name">${escapeHtml(label)}</span></div>`;
  }
  el('grid').innerHTML = html;
}

function renderDynamicListPreview() {
  const apps = (state.status?.snapshot?.apps || []).slice(0, 3);
  const rows = apps.length ? apps : [1, 2, 3].map((number) => t('dynamicWindow', { number }));
  el('grid').innerHTML = `<div class="dynamic-list-preview">${rows.map((name, index) => `<div class="dynamic-list-row">${iconSvg(index === 0 ? 'browser' : 'app')}<span><strong>${escapeHtml(name)}</strong><small>${t('dynamicListHint')}</small></span>${index === 0 ? '<em>●</em>' : ''}</div>`).join('')}</div>`;
}

function buttonSlot(button, slot) {
  const kind = actionKind(button.action);
  const supported = actionSupported(button.action);
  return `<button type="button" class="slot ${state.selectedSlot === slot ? 'selected' : ''}" data-slot="${slot}" draggable="true" aria-label="${escapeHtml(textFor(button.label) || button.id)}">
    ${supported ? '' : '<span class="warn-dot">▲</span>'}
    ${iconSvg(button.icon || actionMeta(kind).icon)}
    <span class="name">${escapeHtml(textFor(button.label) || button.id)}</span>
    <span class="kind">${escapeHtml(actionMeta(kind).title[state.locale])}</span>
  </button>`;
}

function emptySlot(slot) {
  return `<button type="button" class="slot empty" data-empty-slot="${slot}" aria-label="${t('emptySlot')}"><span class="plus">+</span></button>`;
}

function renderDashboard(page) {
  if (!el('dash-body')) return;
  const dashboard = page?.dashboard || 'auto';
  el('dash-label').textContent = dashboard;
  const info = state.schema.dashboards.find((item) => item.name === dashboard);
  const body = el('dash-body');
  if (info && !info.supported) {
    body.innerHTML = `<div class="unsupported">▲ ${escapeHtml(info.capability || dashboard)}</div>`;
    return;
  }
  const snapshot = state.status?.snapshot || {};
  if (dashboard === 'media' || (dashboard === 'auto' && snapshot.media)) {
    const media = snapshot.media;
    body.innerHTML = media
      ? `<div class="big">${escapeHtml(media.title || '')}</div><div>${escapeHtml(media.artist || '')}</div><div>${escapeHtml(media.app || '')}</div>`
      : `<div>${t('noMedia')}</div>`;
  } else if (dashboard === 'system') {
    body.innerHTML = `<div>CPU ${snapshot.cpu ?? '—'}%</div><progress class="meter" max="100" value="${snapshot.cpu ?? 0}"></progress><div>RAM ${snapshot.memory ?? '—'}%</div><progress class="meter" max="100" value="${snapshot.memory ?? 0}"></progress>`;
  } else if (dashboard === 'audio') {
    body.innerHTML = `<div class="big">${snapshot.volume ?? '—'}%</div><progress class="meter" max="100" value="${snapshot.volume ?? 0}"></progress><div>${escapeHtml(snapshot.audio_output || '—')}</div>`;
  } else {
    body.innerHTML = `<div>${t('producedByAgent', { name: dashboard })}</div>`;
  }
}

function renderDetail() {
  if (state.view === 'editor') renderEditorDetail();
  else if (state.view === 'settings') renderSettingsHelp();
  else renderStatusDetail();
}

function renderEditorDetail() {
  const button = currentButton();
  el('detail-panel').innerHTML = button ? buttonForm(button) : pageForm();
}

function field(label, input, note = '', className = '') {
  return `<div class="field ${className}"><label>${label}</label>${input}${note ? `<p class="field-note">${note}</p>` : ''}</div>`;
}

function textInput(binding, value, options = {}) {
  return `<input type="${options.type || 'text'}" data-bind="${binding}" value="${escapeHtml(value ?? '')}" ${options.max ? `maxlength="${options.max}"` : ''} ${options.placeholder ? `placeholder="${escapeHtml(options.placeholder)}"` : ''} ${options.list ? `list="${options.list}"` : ''}>`;
}

function numberInput(binding, value, min, max, step = 1) {
  return `<input type="number" data-bind="${binding}" value="${escapeHtml(value)}" min="${min}" max="${max}" step="${step}">`;
}

function selectInput(binding, value, options) {
  return `<select data-bind="${binding}">${options.map((option) => {
    const item = typeof option === 'string' ? { value: option, label: option } : option;
    return `<option value="${escapeHtml(item.value)}" ${item.value === value ? 'selected' : ''}>${escapeHtml(item.label)}</option>`;
  }).join('')}</select>`;
}

function iconPicker(binding, value) {
  const current = state.schema.icons.includes(value) ? value : 'app';
  return `<div class="icon-picker">
    <button class="icon-picker-trigger" type="button" data-toggle-icon-picker aria-expanded="false" aria-label="${t('chooseIcon')}">
      <span class="icon-picker-preview">${iconSvg(current)}</span>
      <span>${escapeHtml(iconLabel(current))}</span><span class="chevron">⌄</span>
    </button>
    <div class="icon-picker-menu" role="listbox" aria-label="${t('chooseIcon')}">
      ${state.schema.icons.map((name) => `<button class="icon-choice ${name === current ? 'active' : ''}" type="button" data-pick-icon="${escapeHtml(name)}" data-icon-binding="${escapeHtml(binding)}" role="option" aria-selected="${name === current}" aria-label="${escapeHtml(iconLabel(name))}" title="${escapeHtml(iconLabel(name))}">${iconSvg(name)}</button>`).join('')}
    </div>
  </div>`;
}

function layoutPicker(page) {
  const listEnabled = page.source === 'windows';
  return `<div class="layout-picker">
    <button class="layout-choice ${page.layout !== 'list' ? 'active' : ''}" type="button" data-layout="grid">
      ${iconSvg('app')}<span><strong>${t('gridLayout')}</strong><small>${t('gridLayoutHelp')}</small></span>
    </button>
    <button class="layout-choice ${page.layout === 'list' ? 'active' : ''}" type="button" data-layout="list" ${listEnabled ? '' : 'disabled'}>
      ${iconSvg('page')}<span><strong>${t('listLayout')}</strong><small>${t('listLayoutHelp')}</small></span>
    </button>
  </div>`;
}

function pageForm() {
  const page = currentPage();
  if (!page) return '';
  const dashboards = state.schema.dashboards.map((item) => ({
    value: item.name,
    label: dashboardLabel(item.name) + (item.supported ? '' : ` — ${t('unavailable')}`),
  }));
  return `
    <div class="detail-head"><div><h2>${t('pageSettings')}</h2><p>${escapeHtml(textFor(page.title) || page.id)}</p></div></div>
    ${field(t('titleEn'), textInput('page.title.en', textFor(page.title, 'en'), { max: state.schema.limits.label }))}
    ${field(t('titleFr'), textInput('page.title.fr', textFor(page.title, 'fr'), { max: state.schema.limits.label }))}
    ${field(t('icon'), iconPicker('page.icon', page.icon || 'page'))}
    ${field(t('layout'), layoutPicker(page), page.source === 'windows' ? '' : t('listNeedsSource'))}
    ${field(t('dashboard'), selectInput('page.dashboard', page.dashboard || 'auto', dashboards))}
    ${field(t('automaticSource'), selectInput('page.source', page.source || '', [
      { value: '', label: t('noSource') }, { value: 'windows', label: t('windowsSource') },
    ]))}
    <details><summary>${t('advancedSettings')}</summary>
      <div class="divider"></div>
      ${field(t('id'), textInput('page.id', page.id, { max: state.schema.limits.id }), '', 'technical-field')}
    </details>
    <div class="inspector-actions"><button class="button danger" type="button" data-action="delete-page" ${state.config.pages.length <= 1 ? 'disabled' : ''}>${t('deletePage')}</button></div>`;
}

function dashboardLabel(name) {
  const labels = {
    auto: { fr: 'Automatique', en: 'Automatic' }, media: { fr: 'Média en cours', en: 'Now playing' },
    system: { fr: 'Système', en: 'System' }, apps: { fr: 'Applications', en: 'Applications' },
    audio: { fr: 'Audio', en: 'Audio' }, frame: { fr: 'Pochette plein écran', en: 'Full-screen artwork' },
    notifications: { fr: 'Notifications', en: 'Notifications' },
  };
  return labels[name]?.[state.locale] || name;
}

function buttonForm(button) {
  const kind = actionKind(button.action);
  const meta = actionMeta(kind);
  const supported = actionSupported(button.action);
  const toggleOptions = [
    { value: '', label: t('noFollowedState') },
    { value: 'mic_muted', label: state.locale === 'fr' ? 'Micro coupé' : 'Micro muted' },
    { value: 'muted', label: state.locale === 'fr' ? 'Son coupé' : 'Sound muted' },
    { value: 'playing', label: state.locale === 'fr' ? 'Lecture active' : 'Playing' },
    { value: 'media_present', label: state.locale === 'fr' ? 'Média présent' : 'Media present' },
  ];
  return `
    <div class="detail-head"><div><h2>${t('buttonSettings')}</h2><p>${escapeHtml(textFor(button.label) || button.id)}</p></div></div>
    ${field(t('labelEn'), textInput('button.label.en', textFor(button.label, 'en'), { max: state.schema.limits.label }))}
    ${field(t('labelFr'), textInput('button.label.fr', textFor(button.label, 'fr'), { max: state.schema.limits.label }))}
    <div class="form-row">
      ${field(t('icon'), iconPicker('button.icon', button.icon || meta.icon))}
      ${field(t('color'), `<input type="color" data-bind="button.color" value="${escapeHtml(normaliseColor(button.color))}">`)}
    </div>
    <div class="divider"></div>
    <span class="field-label">${t('action')}</span>
    <div class="action-summary"><span class="action-icon">${iconSvg(meta.icon)}</span><div><strong>${escapeHtml(meta.title[state.locale])}</strong><span>${escapeHtml(meta.description[state.locale])}</span></div></div>
    ${renderActionArguments(button.action)}
    ${supported ? '' : `<div class="support-note">${iconSvg('info')}<span>${t('actionUnsupported')} ${kind.startsWith('obs.') ? `<button class="button ghost compact" type="button" data-configure-obs>${t('configureObs')}</button>` : ''}</span></div>`}
    <button class="button secondary full" type="button" data-change-action>${t('changeAction')}</button>
    <div class="divider"></div>
    ${field(t('followedState'), selectInput('button.toggle', button.toggle || '', toggleOptions))}
    <details><summary>${t('advancedSettings')}</summary><div class="divider"></div>${field(t('id'), textInput('button.id', button.id, { max: state.schema.limits.id }), '', 'technical-field')}</details>
    <div class="inspector-actions"><button class="button danger" type="button" data-action="delete-button">${t('deleteButton')}</button><button class="button secondary" type="button" data-action="deselect">${t('backToPage')}</button></div>`;
}

function renderActionArguments(actionValue) {
  const kind = actionKind(actionValue);
  const args = actionArgs(actionValue);
  const info = actionInfo(kind);
  const fields = info?.arguments || [];
  if (!fields.length) return '';
  return fields.map((argument) => {
    const name = argument.name;
    const value = args[name] ?? '';
    let input;
    if (argument.type === 'page') {
      input = selectInput(`action.arg.${name}`, value, state.config.pages.map((page) => ({ value: page.id, label: textFor(page.title) || page.id })));
    } else if (argument.type === 'script') {
      const scripts = Object.keys(state.config.scripts || {});
      if (!scripts.length) return `<p class="field-note warn">${t('noScripts')} ${t('scriptsReadonly')}</p>`;
      input = selectInput(`action.arg.${name}`, value, scripts);
    } else if (argument.type === 'number') {
      input = numberInput(`action.arg.${name}`, value || 50, 0, 100);
    } else {
      const isScene = name === 'scene';
      input = textInput(`action.arg.${name}`, value, {
        placeholder: argumentPlaceholder(name),
        list: isScene && state.obsTest?.scenes?.length ? 'obs-scenes' : '',
      });
      if (isScene && state.obsTest?.scenes?.length) {
        input += `<datalist id="obs-scenes">${state.obsTest.scenes.map((scene) => `<option value="${escapeHtml(scene)}"></option>`).join('')}</datalist>`;
      }
    }
    const note = argument.required && !String(value).trim() ? t('argumentMissing') : '';
    return field(argumentLabel(name), input, note);
  }).join('');
}

function argumentLabel(name) {
  const labels = {
    target: { fr: 'Application ou cible', en: 'Application or target' }, url: { fr: 'Adresse web', en: 'Web address' },
    path: { fr: 'Fichier ou dossier', en: 'File or folder' }, keys: { fr: 'Touches', en: 'Keys' },
    page: { fr: 'Page cible', en: 'Target page' }, script: { fr: 'Script autorisé', en: 'Allowed script' },
    value: { fr: 'Valeur (0 à 100)', en: 'Value (0 to 100)' }, scene: { fr: 'Scène OBS', en: 'OBS scene' },
    source: { fr: 'Source OBS', en: 'OBS source' }, app: { fr: 'Application', en: 'Application' }, title: { fr: 'Titre de fenêtre', en: 'Window title' },
  };
  return labels[name]?.[state.locale] || name;
}

function argumentPlaceholder(name) {
  const placeholders = {
    scene: { fr: 'Ex. Caméra', en: 'e.g. Camera' }, source: { fr: 'Ex. Webcam', en: 'e.g. Webcam' },
    keys: { fr: 'Ex. cmd+shift+4', en: 'e.g. cmd+shift+4' }, target: { fr: 'Ex. Safari', en: 'e.g. Safari' },
  };
  return placeholders[name]?.[state.locale] || '';
}

/* Réglages ----------------------------------------------------------------- */

function renderSettingsWorkspace() {
  if (state.settingsSection === 'preferences') renderPreferences();
  else if (state.settingsSection === 'obs') renderObsSettings();
  else renderConnectionSettings();
}

function renderConnectionSettings() {
  const server = state.config.server;
  const address = state.status?.hints?.[0] || `127.0.0.1:${server.port || 38123}`;
  const secured = Boolean(server.token);
  el('workspace').innerHTML = `<div class="settings-content">
    <h1>${t('connectionTitle')}</h1><p class="settings-intro">${t('connectionIntro')}</p>
    <section class="settings-section">
      <span class="field-label">${t('connectionAddress')}</span>
      <div class="address-box"><code id="connection-address">${escapeHtml(address)}</code><button class="button secondary" type="button" data-copy-address>${iconSvg('link')} ${t('copy')}</button></div>
      <div class="instruction-line"><span class="step-number">1</span><span>${t('connectionInstruction')}</span></div>
    </section>
    <section class="settings-section">
      <h2>${t('networkSecurity')}</h2><p>${t('networkSecurityHelp')}</p>
      <div class="segmented"><button type="button" data-security="on" class="${secured ? 'active' : ''}">${t('enabledRecommended')}</button><button type="button" data-security="off" class="${secured ? '' : 'active'}">${t('disabled')}</button></div>
      <p class="field-note ${secured ? 'ok' : 'warn'}">${secured ? t('securityEnabled') : t('securityDisabled')}</p>
    </section>
    <section class="settings-section">
      <button class="disclosure" type="button" data-toggle-advanced><span>${t('advancedSettings')}</span><span>${state.advancedOpen ? '⌃' : '⌄'}</span></button>
      <div class="advanced-fields ${state.advancedOpen ? '' : 'collapsed'}">
        ${field(t('listenAddress'), textInput('server.host', server.host || '0.0.0.0'))}
        <div class="form-row">${field(t('port'), numberInput('server.port', server.port || 38123, 1, 65535))}${field(t('refresh'), numberInput('server.poll_interval', server.poll_interval || 1, .2, 30, .1), t('seconds'))}</div>
        ${field(t('volumeStep'), numberInput('server.volume_step', server.volume_step || 5, 1, 50))}
        <p class="field-note">${t('restartNote')}</p>
      </div>
    </section>
  </div>`;
}

function renderPreferences() {
  el('workspace').innerHTML = `<div class="settings-content">
    <h1>${t('preferencesTitle')}</h1><p class="settings-intro">${t('preferencesIntro')}</p>
    <section class="settings-section"><h2>${t('displayLanguage')}</h2><p>${t('displayLanguageHelp')}</p>
      <div class="segmented"><button type="button" data-set-locale="fr" class="${state.locale === 'fr' ? 'active' : ''}">${t('french')}</button><button type="button" data-set-locale="en" class="${state.locale === 'en' ? 'active' : ''}">${t('english')}</button></div>
    </section>
    <section class="settings-section"><h2>${t('labelsLanguages')}</h2><p>${t('labelsLanguagesHelp')}</p>
      <div class="help-panel"><h3>${t('languageTitle')}</h3><p>${t('languageHelp')}</p></div>
    </section>
  </div>`;
}

function renderObsSettings() {
  const obs = state.config.integrations.obs;
  let result = '';
  if (state.obsTesting) result = `<div class="obs-test-result">${t('testing')}</div>`;
  else if (state.obsTest?.connected) {
    result = `<div class="obs-test-result ok">${t('obsConnected', { version: escapeHtml(state.obsTest.obs_version || ''), count: state.obsTest.scenes?.length || 0 })}${state.obsTest.scenes?.length ? `<div class="scene-list">${state.obsTest.scenes.map((scene) => `<span>${escapeHtml(scene)}</span>`).join('')}</div>` : ''}</div>`;
  } else if (state.obsTest?.error) result = `<div class="obs-test-result error">${escapeHtml(state.obsTest.error)}</div>`;

  el('workspace').innerHTML = `<div class="settings-content">
    <h1>${t('obsTitle')}</h1><p class="settings-intro">${t('obsIntro')}</p>
    <section class="settings-section">
      <div class="toggle-row"><div><h2>${t('obsEnabled')}</h2><p class="field-note">${t('obsSetupHelp')}</p></div><label class="switch"><input type="checkbox" data-bind-check="obs.enabled" ${obs.enabled ? 'checked' : ''}><span></span></label></div>
    </section>
    <section class="settings-section">
      <div class="form-row">${field(t('obsHost'), textInput('obs.host', obs.host || '127.0.0.1'))}${field(t('obsPort'), numberInput('obs.port', obs.port || 4455, 1, 65535))}</div>
      ${field(t('obsPassword'), textInput('obs.password', obs.password || '', { type: 'password' }), t('obsPasswordHelp'))}
      ${field(t('obsTimeout'), numberInput('obs.timeout', obs.timeout || 2, .2, 15, .1), t('seconds'))}
      <button class="button primary" type="button" data-test-obs ${state.obsTesting ? 'disabled' : ''}>${iconSvg('video')} ${state.obsTesting ? t('testing') : t('testConnection')}</button>
      ${result}
    </section>
  </div>`;
}

async function testObs() {
  state.obsTesting = true;
  state.obsTest = null;
  render();
  try {
    state.obsTest = await api('POST', '/api/obs/test', state.config.integrations.obs);
  } catch (error) {
    state.obsTest = { error: error.message };
  } finally {
    state.obsTesting = false;
    render();
  }
}

function renderSettingsHelp() {
  const content = state.settingsSection === 'obs'
    ? `<h3>${t('obsPreview')}</h3><p>${t('obsPreviewHelp')}</p><p>${t('obsSetupHelp')}</p>`
    : `<h3>${t('aboutConnection')}</h3><p>${t('connectionHelp')}</p><div class="divider"></div><h3>${t('obsPreview')}</h3><p>${t('obsPreviewHelp')}</p>`;
  el('detail-panel').innerHTML = `<div class="help-panel">${content}</div>`;
}

/* État --------------------------------------------------------------------- */

function renderStatusWorkspace() {
  const status = state.status;
  if (!status) {
    el('workspace').innerHTML = `<div class="status-content"><h1>${t('statusTitle')}</h1><p class="settings-intro">${t('noStatus')}</p></div>`;
    return;
  }
  const clients = status.clients || [];
  el('workspace').innerHTML = `<div class="status-content">
    <h1>${t('statusTitle')}</h1><p class="settings-intro">${t('statusIntro')}</p>
    <div class="status-grid">
      ${statusRow(t('listening'), status.listen, true)}
      ${statusRow(t('addressFor3ds'), (status.hints || []).join(' · ') || '—', true)}
      ${statusRow(t('platform'), status.platform)}
      ${statusRow(t('version'), status.version)}
      ${statusRow(t('connectedConsoles'), clients.length ? String(clients.length) : t('noConsole'))}
      ${statusRow(t('token'), status.token_set ? t('defined') : t('absent'))}
    </div>
    <section class="settings-section"><h2>${t('logs')}</h2><pre class="logs">${escapeHtml((status.logs || []).slice(-80).join('\n'))}</pre></section>
  </div>`;
}

function statusRow(label, value, code = false) {
  return `<div class="status-row"><span>${label}</span>${code ? `<code>${escapeHtml(value)}</code>` : `<strong>${escapeHtml(value)}</strong>`}</div>`;
}

function renderStatusDetail() {
  const capabilities = state.status?.capabilities || {};
  el('detail-panel').innerHTML = `<div class="detail-head"><div><h2>${t('capabilities')}</h2><p>${escapeHtml(state.status?.platform || '')}</p></div></div><div class="capability-list">${Object.entries(capabilities).map(([name, available]) => `<div class="capability"><span>${escapeHtml(capabilityLabel(name))}</span><b class="${available ? 'yes' : ''}">${available ? t('yes') : t('no')}</b></div>`).join('')}</div>`;
}

function capabilityLabel(name) {
  const labels = {
    volume: { fr: 'Volume', en: 'Volume' }, mute: { fr: 'Son coupé', en: 'Mute' }, mic: { fr: 'Microphone', en: 'Microphone' },
    app_volume: { fr: 'Volume du lecteur', en: 'Player volume' }, audio_output: { fr: 'Sorties audio', en: 'Audio outputs' },
    media: { fr: 'Contrôles média', en: 'Media controls' }, media_artwork: { fr: 'Pochettes', en: 'Artwork' }, apps: { fr: 'Applications', en: 'Applications' },
    windows: { fr: 'Fenêtres', en: 'Windows' }, hotkey: { fr: 'Raccourcis', en: 'Shortcuts' }, open_url: { fr: 'Liens web', en: 'Web links' },
    open_path: { fr: 'Fichiers', en: 'Files' }, lock: { fr: 'Verrouillage', en: 'Lock' }, notifications: { fr: 'Notifications', en: 'Notifications' },
    system_stats: { fr: 'État système', en: 'System status' }, obs: { fr: 'OBS Studio', en: 'OBS Studio' },
  };
  return labels[name]?.[state.locale] || name;
}

/* Catalogue d'actions ------------------------------------------------------ */

function openPicker(slot, mode = 'add') {
  state.picker = { open: true, slot, mode, query: '', category: mode === 'replace' ? actionMeta(actionKind(currentButton()?.action)).category : 'essential' };
  renderDrawer();
  bindDrawer();
  requestAnimationFrame(() => el('action-search')?.focus());
}

function closePicker() {
  state.picker.open = false;
  renderDrawer();
}

function renderDrawer() {
  const drawer = el('action-drawer');
  const backdrop = el('drawer-backdrop');
  drawer.classList.toggle('hidden', !state.picker.open);
  backdrop.classList.toggle('hidden', !state.picker.open);
  if (!state.picker.open) {
    drawer.innerHTML = '';
    return;
  }
  const query = state.picker.query.trim().toLowerCase();
  const availableKinds = state.schema.actions.map((item) => item.kind).filter((kind) => kind !== 'noop');
  const matches = availableKinds.filter((kind) => {
    const meta = actionMeta(kind);
    const haystack = `${kind} ${meta.title.fr} ${meta.title.en} ${meta.description.fr} ${meta.description.en}`.toLowerCase();
    return (!query && meta.category === state.picker.category) || (query && haystack.includes(query));
  });
  drawer.innerHTML = `
    <div class="drawer-head"><h2 id="action-drawer-title">${state.picker.mode === 'replace' ? t('changeAction') : t('addAction')}</h2><button class="drawer-close" type="button" data-close-drawer aria-label="${t('close')}">×</button></div>
    <div class="drawer-search">${iconSvg('search')}<input id="action-search" type="search" value="${escapeHtml(state.picker.query)}" placeholder="${t('searchAction')}"></div>
    <div class="action-browser">
      <div class="category-list">${CATEGORIES.map(([id, label]) => `<button type="button" data-category="${id}" class="${state.picker.category === id && !query ? 'active' : ''}">${label[state.locale]}</button>`).join('')}</div>
      <div class="action-list">${matches.length ? matches.map(actionItem).join('') : `<div class="no-actions">${t('searchAction')}</div>`}</div>
    </div>
    <div class="drawer-note">${iconSvg('info')}<span>${t('supportNote')}</span></div>`;
}

function actionItem(kind) {
  const meta = actionMeta(kind);
  const supported = actionSupported(kind);
  return `<button class="action-item" type="button" data-pick-action="${escapeHtml(kind)}"><span class="action-icon">${iconSvg(meta.icon)}</span><span><strong>${escapeHtml(meta.title[state.locale])}</strong><p>${escapeHtml(meta.description[state.locale])}</p></span><span class="support-tag ${supported ? '' : 'off'}">${t(supported ? 'supported' : 'unavailable')}</span></button>`;
}

function bindDrawer() {
  el('drawer-backdrop').onclick = closePicker;
  el('action-drawer').querySelector('[data-close-drawer]')?.addEventListener('click', closePicker);
  el('action-search')?.addEventListener('input', (event) => {
    state.picker.query = event.target.value;
    renderDrawer();
    bindDrawer();
    const search = el('action-search');
    search?.focus();
    search?.setSelectionRange(search.value.length, search.value.length);
  });
  el('action-drawer').querySelectorAll('[data-category]').forEach((button) => {
    button.onclick = () => { state.picker.category = button.dataset.category; state.picker.query = ''; renderDrawer(); bindDrawer(); };
  });
  el('action-drawer').querySelectorAll('[data-pick-action]').forEach((button) => {
    button.onclick = () => chooseAction(button.dataset.pickAction);
  });
}

function chooseAction(kind) {
  if (state.picker.mode === 'replace') {
    const button = currentButton();
    if (button) button.action = defaultAction(kind);
  } else {
    addButton(state.picker.slot, kind);
  }
  state.picker.open = false;
  render();
}

function defaultAction(kind) {
  const fields = actionInfo(kind)?.arguments || [];
  if (!fields.length) return kind;
  const value = { type: kind };
  fields.forEach((argument) => {
    if (argument.type === 'number') value[argument.name] = 50;
    else if (argument.type === 'page') value[argument.name] = state.config.pages[0]?.id || '';
    else if (argument.type === 'script') value[argument.name] = Object.keys(state.config.scripts || {})[0] || '';
    else if (argument.name === 'scene') value[argument.name] = state.obsTest?.current_scene || state.obsTest?.scenes?.[0] || '';
    else value[argument.name] = '';
  });
  return value;
}

/* Liaison et actions ------------------------------------------------------- */

function bindDynamicUi() {
  bindNavigation();
  bindEditorUi();
  bindForms();
  bindSettingsUi();
  if (state.picker.open) bindDrawer();
}

function bindNavigation() {
  el('sidebar').querySelectorAll('[data-settings]').forEach((button) => {
    button.onclick = () => { state.settingsSection = button.dataset.settings; render(); };
  });
  el('sidebar').querySelectorAll('[data-view-jump]').forEach((button) => {
    button.onclick = () => setView(button.dataset.viewJump);
  });
}

function bindEditorUi() {
  el('add-page')?.addEventListener('click', addPage);
  el('sidebar').querySelectorAll('[data-page]').forEach((item) => {
    const index = Number(item.dataset.page);
    item.onclick = () => { state.pageIndex = index; state.selectedSlot = null; render(); };
    item.ondragstart = (event) => event.dataTransfer.setData('text/page', String(index));
    item.ondragover = (event) => { if (event.dataTransfer.types.includes('text/page')) { event.preventDefault(); item.classList.add('drop-target'); } };
    item.ondragleave = () => item.classList.remove('drop-target');
    item.ondrop = (event) => {
      event.preventDefault(); item.classList.remove('drop-target');
      const from = Number(event.dataTransfer.getData('text/page'));
      if (Number.isNaN(from) || from === index) return;
      const [moved] = state.config.pages.splice(from, 1);
      state.config.pages.splice(index, 0, moved);
      state.pageIndex = index;
      render();
    };
  });
  el('workspace').querySelectorAll('[data-console-page]').forEach((button) => {
    button.onclick = () => { state.pageIndex = Number(button.dataset.consolePage); state.selectedSlot = null; render(); };
  });
  el('workspace').querySelectorAll('[data-empty-slot]').forEach((button) => {
    button.onclick = () => openPicker(Number(button.dataset.emptySlot));
  });
  el('workspace').querySelectorAll('[data-slot]').forEach((button) => {
    const slot = Number(button.dataset.slot);
    button.onclick = () => { state.selectedSlot = slot; render(); };
    attachSlotDrag(button, slot);
  });
  el('workspace').querySelector('[data-open-page-settings]')?.addEventListener('click', () => { state.selectedSlot = null; render(); });
  el('detail-panel').querySelector('[data-change-action]')?.addEventListener('click', () => openPicker(state.selectedSlot, 'replace'));
  el('detail-panel').querySelector('[data-configure-obs]')?.addEventListener('click', () => { state.view = 'settings'; state.settingsSection = 'obs'; render(); });
  el('detail-panel').querySelectorAll('[data-action]').forEach((button) => {
    button.onclick = () => {
      if (button.dataset.action === 'delete-page') deletePage();
      else if (button.dataset.action === 'delete-button') deleteButton();
      else if (button.dataset.action === 'deselect') { state.selectedSlot = null; render(); }
    };
  });
}

function attachSlotDrag(node, slot) {
  node.ondragstart = (event) => { event.dataTransfer.setData('text/slot', String(slot)); node.classList.add('dragging'); };
  node.ondragend = () => node.classList.remove('dragging');
  node.ondragover = (event) => { if (event.dataTransfer.types.includes('text/slot')) { event.preventDefault(); node.classList.add('drop-target'); } };
  node.ondragleave = () => node.classList.remove('drop-target');
  node.ondrop = (event) => {
    event.preventDefault(); node.classList.remove('drop-target');
    const from = Number(event.dataTransfer.getData('text/slot'));
    if (Number.isNaN(from) || from === slot) return;
    const buttons = currentPage().buttons || [];
    const source = buttons.find((item) => item.slot === from);
    const target = buttons.find((item) => item.slot === slot);
    if (!source) return;
    source.slot = slot;
    if (target) target.slot = from;
    state.selectedSlot = slot;
    render();
  };
}

function bindForms() {
  document.querySelectorAll('[data-bind]').forEach((node) => {
    node.addEventListener('change', () => { applyBinding(node.dataset.bind, node.value); render(); });
  });
  document.querySelectorAll('[data-bind-check]').forEach((node) => {
    node.addEventListener('change', () => { applyBinding(node.dataset.bindCheck, node.checked); render(); });
  });
  document.querySelectorAll('[data-toggle-icon-picker]').forEach((node) => {
    node.addEventListener('click', (event) => {
      event.stopPropagation();
      const picker = node.closest('.icon-picker');
      const wasOpen = picker.classList.contains('open');
      document.querySelectorAll('.icon-picker.open').forEach((item) => item.classList.remove('open'));
      picker.classList.toggle('open', !wasOpen);
      node.setAttribute('aria-expanded', String(!wasOpen));
    });
  });
  document.querySelectorAll('[data-pick-icon]').forEach((node) => {
    node.addEventListener('click', () => { applyBinding(node.dataset.iconBinding, node.dataset.pickIcon); render(); });
  });
  document.querySelectorAll('[data-layout]').forEach((node) => {
    node.addEventListener('click', () => { applyBinding('page.layout', node.dataset.layout); render(); });
  });
}

function bindSettingsUi() {
  el('workspace').querySelector('[data-toggle-advanced]')?.addEventListener('click', () => { state.advancedOpen = !state.advancedOpen; render(); });
  el('workspace').querySelectorAll('[data-security]').forEach((button) => {
    button.onclick = () => {
      if (button.dataset.security === 'on' && !state.config.server.token) state.config.server.token = randomToken();
      if (button.dataset.security === 'off') state.config.server.token = '';
      render();
    };
  });
  el('workspace').querySelectorAll('[data-set-locale]').forEach((button) => {
    button.onclick = () => setLocale(button.dataset.setLocale);
  });
  el('workspace').querySelector('[data-copy-address]')?.addEventListener('click', async () => {
    const address = el('connection-address')?.textContent || '';
    try { await navigator.clipboard.writeText(address); banner(t('copied'), 'ok'); }
    catch (error) { banner(address); }
  });
  el('workspace').querySelector('[data-test-obs]')?.addEventListener('click', testObs);
}

function applyBinding(path, raw) {
  const page = currentPage();
  const button = currentButton();
  const value = typeof raw === 'string' ? raw.trim() : raw;
  switch (path) {
    case 'page.id': updatePageId(page.id, value); page.id = value; break;
    case 'page.title.en': page.title = setLocalizedText(page.title, 'en', value); break;
    case 'page.title.fr': page.title = setLocalizedText(page.title, 'fr', value); break;
    case 'page.icon': page.icon = value; break;
    case 'page.layout': page.layout = value; break;
    case 'page.dashboard': page.dashboard = value; break;
    case 'page.source': page.source = value; if (!value && page.layout === 'list') page.layout = 'grid'; break;
    case 'button.id': button.id = value; break;
    case 'button.label.en': button.label = setLocalizedText(button.label, 'en', value); break;
    case 'button.label.fr': button.label = setLocalizedText(button.label, 'fr', value); break;
    case 'button.icon': button.icon = value; break;
    case 'button.color': button.color = String(value).toUpperCase(); break;
    case 'button.toggle': if (value) button.toggle = value; else delete button.toggle; break;
    case 'server.host': state.config.server.host = value; break;
    case 'server.port': state.config.server.port = Number(value); break;
    case 'server.poll_interval': state.config.server.poll_interval = Number(value); break;
    case 'server.volume_step': state.config.server.volume_step = Number(value); break;
    case 'obs.enabled': state.config.integrations.obs.enabled = Boolean(value); break;
    case 'obs.host': state.config.integrations.obs.host = value; state.obsTest = null; break;
    case 'obs.port': state.config.integrations.obs.port = Number(value); state.obsTest = null; break;
    case 'obs.password': state.config.integrations.obs.password = value; state.obsTest = null; break;
    case 'obs.timeout': state.config.integrations.obs.timeout = Number(value); state.obsTest = null; break;
    default:
      if (path.startsWith('action.arg.') && button) {
        const name = path.slice('action.arg.'.length);
        const info = actionInfo(actionKind(button.action));
        const spec = info?.arguments?.find((item) => item.name === name);
        const next = spec?.type === 'number' ? Number(value) : value;
        button.action = { type: actionKind(button.action), ...actionArgs(button.action), [name]: next };
      }
  }
}

function updatePageId(previous, next) {
  state.config.pages.forEach((page) => (page.buttons || []).forEach((button) => {
    ['action', 'hold_action'].forEach((key) => {
      const target = button[key];
      if (target && typeof target === 'object' && target.type === 'page.open' && target.page === previous) target.page = next;
    });
  }));
}

function randomToken() {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
}

function addButton(slot, kind) {
  const page = currentPage();
  page.buttons = page.buttons || [];
  const taken = state.config.pages.flatMap((item) => (item.buttons || []).map((entry) => entry.id));
  const meta = actionMeta(kind);
  page.buttons.push({
    id: uniqueId('button', taken), slot,
    label: { en: meta.title.en.slice(0, state.schema.limits.label), fr: meta.title.fr.slice(0, state.schema.limits.label) },
    icon: meta.icon, color: meta.color, action: defaultAction(kind),
  });
  state.selectedSlot = slot;
}

function addPage() {
  const taken = state.config.pages.map((page) => page.id);
  state.config.pages.push({
    id: uniqueId('page', taken),
    title: { en: 'New page', fr: t('pageNameDefault') },
    icon: 'page', dashboard: 'auto', buttons: [],
  });
  state.pageIndex = state.config.pages.length - 1;
  state.selectedSlot = null;
  render();
}

function deleteButton() {
  const page = currentPage();
  page.buttons = (page.buttons || []).filter((button) => button.slot !== state.selectedSlot);
  state.selectedSlot = null;
  render();
}

function deletePage() {
  if (state.config.pages.length <= 1) return;
  const removed = currentPage().id;
  const referenced = state.config.pages.some((page) => (page.buttons || []).some((button) =>
    ['action', 'hold_action'].some((key) => button[key] && typeof button[key] === 'object' && button[key].type === 'page.open' && button[key].page === removed)
  ));
  if (referenced && !confirm(t('deleteRefs'))) return;
  state.config.pages.splice(state.pageIndex, 1);
  state.pageIndex = Math.max(0, state.pageIndex - 1);
  state.selectedSlot = null;
  render();
}

function setLocale(locale) {
  if (locale !== 'fr' && locale !== 'en') return;
  state.locale = locale;
  try { localStorage.setItem(LOCALE_KEY, locale); } catch (error) { /* non bloquant */ }
  render();
}

function setView(view) {
  state.view = view;
  state.mobileMenu = false;
  state.picker.open = false;
  render();
}

/* Démarrage ---------------------------------------------------------------- */

el('brand').onclick = () => setView('editor');
el('main-nav').querySelectorAll('[data-view]').forEach((button) => {
  button.onclick = () => setView(button.dataset.view);
});
el('mobile-menu').onclick = () => { state.mobileMenu = !state.mobileMenu; renderHeader(); };
el('locale').onchange = (event) => setLocale(event.target.value);
el('save').onclick = save;
el('reload').onclick = () => {
  if (isDirty() && !confirm(t('unsavedConfirm'))) return;
  load();
};

document.addEventListener('click', (event) => {
  if (event.target.closest('.icon-picker')) return;
  document.querySelectorAll('.icon-picker.open').forEach((picker) => {
    picker.classList.remove('open');
    picker.querySelector('[data-toggle-icon-picker]')?.setAttribute('aria-expanded', 'false');
  });
});

window.addEventListener('beforeunload', (event) => {
  if (state.config && isDirty()) event.preventDefault();
});

window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && state.picker.open) closePicker();
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
    event.preventDefault();
    if (state.config && isDirty()) save();
  }
});

if (!TOKEN) {
  banner('Jeton absent. Ouvrez le lien complet affiché par l’agent.');
} else {
  load().then(refreshStatus);
  const timer = setInterval(() => {
    if (!TOKEN) return clearInterval(timer);
    refreshStatus();
  }, 2500);
}
