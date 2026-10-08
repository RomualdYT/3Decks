import defaults from "../../../default-config.json";
import type { DeckConfig, PageConfig, Schema } from "../app/types";
import {
  actionKind,
  clone,
  defaultAction,
  newPage,
  uniqueId,
} from "../utils/config";

type Copy = { fr: string; en: string };
export type PageTemplateId =
  | "home"
  | "music"
  | "applications"
  | "computer"
  | "streaming"
  | "notifications"
  | "blank";
export interface TemplateVariant {
  id: string;
  title: Copy;
  dashboard: string;
}
interface PageTemplate {
  id: PageTemplateId;
  group: "essentials" | "optional" | "custom";
  title: Copy;
  description: Copy;
  icon: string;
  dashboard: string;
  seed?: string;
  actions?: string[];
  variants?: TemplateVariant[];
  feature?: string;
}

export const PAGE_TEMPLATES: readonly PageTemplate[] = [
  {
    id: "home",
    group: "essentials",
    title: { fr: "Accueil", en: "Home" },
    description: {
      fr: "Vos raccourcis quotidiens et les informations du moment.",
      en: "Everyday shortcuts and information for the moment.",
    },
    icon: "star",
    dashboard: "auto",
    seed: "main",
  },
  {
    id: "music",
    group: "essentials",
    title: { fr: "Musique", en: "Music" },
    description: {
      fr: "Lecture, volumes et sortie audio, avec l’affichage de votre choix.",
      en: "Playback, volume and audio output, with your choice of display.",
    },
    icon: "music",
    dashboard: "media",
    seed: "sound",
    feature: "media",
    variants: [
      {
        id: "media",
        title: { fr: "Morceau et pochette", en: "Now playing" },
        dashboard: "media",
      },
      {
        id: "lyrics",
        title: { fr: "Paroles synchronisées", en: "Synced lyrics" },
        dashboard: "lyrics",
      },
      {
        id: "frame",
        title: { fr: "Pochette plein écran", en: "Full-screen artwork" },
        dashboard: "frame",
      },
    ],
  },
  {
    id: "applications",
    group: "essentials",
    title: { fr: "Applications", en: "Applications" },
    description: {
      fr: "Passez d’une fenêtre ouverte à l’autre dans une liste automatique.",
      en: "Switch between open windows in an automatically updated list.",
    },
    icon: "app",
    dashboard: "apps",
    seed: "windows",
    feature: "windows",
  },
  {
    id: "computer",
    group: "essentials",
    title: { fr: "Ordinateur", en: "Computer" },
    description: {
      fr: "Performances en direct, fichiers, terminal et verrouillage.",
      en: "Live system statistics, files, terminal and screen lock.",
    },
    icon: "status",
    dashboard: "system",
    feature: "system_stats",
    seed: "computer",
  },
  {
    id: "streaming",
    group: "optional",
    title: { fr: "Streaming", en: "Streaming" },
    description: {
      fr: "Commandes OBS, micro et volumes, avec ou sans chat Twitch.",
      en: "OBS controls, microphone and volume, with or without Twitch chat.",
    },
    icon: "record",
    dashboard: "stream_chat",
    actions: [
      "obs.stream.toggle",
      "obs.record.toggle",
      "obs.scene.set",
      "mic.mute_toggle",
      "modal.volumes",
      "settings.open",
    ],
    variants: [
      {
        id: "chat",
        title: { fr: "Chat Twitch + OBS", en: "Twitch chat + OBS" },
        dashboard: "stream_chat",
      },
      {
        id: "obs",
        title: { fr: "OBS et performances", en: "OBS and statistics" },
        dashboard: "system",
      },
    ],
  },
  {
    id: "notifications",
    group: "optional",
    title: { fr: "Notifications", en: "Notifications" },
    description: {
      fr: "Les dernières notifications, avec des emplacements pour vos raccourcis.",
      en: "Recent notifications, with room for your own shortcuts.",
    },
    icon: "bell",
    dashboard: "notifications",
    feature: "notifications",
    actions: ["settings.open"],
  },
  {
    id: "blank",
    group: "custom",
    title: { fr: "Personnalisée", en: "Custom" },
    description: {
      fr: "Une page vierge pour vos actions et vos extensions.",
      en: "A blank page for your actions and extensions.",
    },
    icon: "page",
    dashboard: "auto",
    actions: [],
  },
];

export interface TemplateOptions {
  scenes?: string[];
  variant?: string;
  platform?: string;
  apps?: string[];
  favorites?: string[];
}

const seedPages = defaults.pages as PageConfig[];

/** Only known installed apps are offered as initial favorites. */
export function suggestedFavorites(apps: string[]): string[] {
  const preferred = [
    "Discord",
    "Spotify",
    "ChatGPT",
    "Visual Studio Code",
    "Mail",
  ];
  return [
    ...preferred.flatMap((name) =>
      apps.filter((app) => app.toLowerCase() === name.toLowerCase()),
    ),
    ...apps,
  ]
    .filter(
      (app, index, values) =>
        values.indexOf(app) === index &&
        !/^(3Decks|Safari|Microsoft Edge|Google Chrome|Terminal)$/i.test(app),
    )
    .slice(0, 2);
}

const CONTROL_COPY: Record<string, { label: Copy; icon?: string }> = {
  "obs.stream.toggle": {
    label: { fr: "Diffusion", en: "Stream" },
    icon: "record",
  },
  "obs.record.toggle": {
    label: { fr: "Enregistrer", en: "Record" },
    icon: "video",
  },
  "obs.scene.set": { label: { fr: "Scène", en: "Scene" }, icon: "app" },
  "mic.mute_toggle": { label: { fr: "Micro", en: "Mic" } },
  "modal.volumes": { label: { fr: "Volumes", en: "Volumes" } },
  "settings.open": { label: { fr: "Réglages", en: "Settings" } },
};

/** The preview and creation share this factory. Existing pages are never migrated. */
export function pageFromTemplate(
  config: DeckConfig,
  schema: Schema,
  id: PageTemplateId,
  {
    scenes = [],
    variant: variantId,
    platform = "darwin",
    apps = [],
    favorites,
  }: TemplateOptions = {},
): PageConfig {
  const template = PAGE_TEMPLATES.find((item) => item.id === id);
  if (!template) throw new Error(`Unknown page template: ${id}`);
  if (id === "blank") return newPage(config);
  const seed = seedPages.find((page) => page.id === template.seed);
  const variant =
    template.variants?.find((item) => item.id === variantId) ??
    template.variants?.[0];
  const page: PageConfig = {
    ...(seed ? clone(seed) : { buttons: [], layout: "grid", source: "" }),
    id: uniqueId(
      id,
      config.pages.map((item) => item.id),
    ),
    title: { ...template.title },
    icon: template.icon,
    dashboard: variant?.dashboard ?? template.dashboard,
  };
  if (page.dashboard === "lyrics") page.lyrics_lines = 3;
  for (const kind of template.actions ?? []) {
    if (kind === "obs.scene.set" && scenes.length === 0) continue;
    const spec = schema.actions.find((item) => item.kind === kind);
    if (!spec) continue;
    const button = {
      id: uniqueId(
        "button",
        page.buttons.map((item) => item.id),
      ),
      slot: page.buttons.length,
      label: CONTROL_COPY[kind]?.label ?? {
        fr: spec.title.fr.slice(0, 24),
        en: spec.title.en.slice(0, 24),
      },
      icon: CONTROL_COPY[kind]?.icon ?? spec.icon,
      color: spec.color,
      action: defaultAction(spec, config, scenes),
    };
    page.buttons.push({
      ...button,
      ...(kind === "mic.mute_toggle" ? { toggle: "mic_muted" } : {}),
    });
  }
  if (id === "home" && (apps.length || favorites)) {
    const chosen = favorites ?? suggestedFavorites(apps);
    chosen.slice(0, 2).forEach((target, index) => {
      if (!target) return;
      const slot = index + 1;
      page.buttons = page.buttons.filter((button) => button.slot !== slot);
      page.buttons.push({
        id: `favorite${index + 1}`,
        slot,
        label: target.slice(0, 24),
        icon: /spotify|music/i.test(target)
          ? "music"
          : /discord|messages/i.test(target)
            ? "chat"
            : "app",
        color: index === 0 ? "#5865F2" : "#1DB954",
        action: { type: "app.launch", target },
      });
    });
    page.buttons.sort((a, b) => a.slot - b.slot);
  }
  if (id === "notifications") page.layout = "list";
  if (id === "notifications" && apps.length) {
    const communicationApps = apps
      .filter((app) =>
        /^(Messages|Mail|Discord|Slack|Microsoft Teams|Outlook)$/i.test(app),
      )
      .slice(0, 3);
    page.layout = "list";
    page.buttons = communicationApps.map((target, slot) => ({
      id: `communication${slot + 1}`,
      slot,
      label: target.slice(0, 24),
      icon: "chat",
      color: "#34D399",
      action: { type: "app.launch", target },
    }));
    const spec = schema.actions.find(
      (action) => action.kind === "settings.open",
    );
    if (spec)
      page.buttons.push({
        id: "settings",
        slot: page.buttons.length,
        label: CONTROL_COPY[spec.kind].label,
        icon: spec.icon,
        color: spec.color,
        action: "settings.open",
      });
  }
  // Bundled defaults use macOS targets; freshly added Home pages must match the host.
  if (platform === "win32") {
    const targets: Record<string, string> = {
      Safari: "msedge.exe",
      Spotify: "spotify:",
      Discord: "discord:",
      Terminal: "powershell.exe",
    };
    for (const button of page.buttons) {
      if (button.action === "audio_output.cycle") {
        button.action = "volume.mute_toggle";
        button.label = { fr: "Muet", en: "Mute" };
        button.icon = "volume-mute";
        button.toggle = "muted";
      }
      if (typeof button.action !== "object") continue;
      if (
        actionKind(button.action) === "hotkey" &&
        button.action.keys === "cmd+shift+4"
      )
        button.action.keys = "win+shift+s";
      if (
        actionKind(button.action) === "app.launch" &&
        typeof button.action.target === "string"
      )
        button.action.target =
          targets[button.action.target] ?? button.action.target;
    }
  }
  return page;
}

/** Selecting a template never enables features or requests system permissions. */
export function templateSetupNotes(
  page: PageConfig,
  config: DeckConfig,
  scenes: string[],
  locale: "fr" | "en",
): string[] {
  const fr = locale === "fr";
  const template = PAGE_TEMPLATES.find(
    (item) =>
      item.dashboard === page.dashboard ||
      item.variants?.some((variant) => variant.dashboard === page.dashboard),
  );
  const notes: string[] = [];
  if (template?.feature && config.features[template.feature] === false)
    notes.push(
      fr
        ? "Activez la fonction correspondante dans Réglages → Fonctions."
        : "Enable the matching feature in Settings → Features.",
    );
  if (page.dashboard === "lyrics" && !config.features.lyrics_online)
    notes.push(
      fr
        ? "Paroles en ligne désactivées. Activez-les dans Réglages → Fonctions, ou utilisez un fichier LRC local."
        : "Online lyrics are off. Enable them in Settings → Features, or use a local LRC file.",
    );
  if (page.dashboard === "frame" && !config.features.media_artwork)
    notes.push(
      fr
        ? "Activez les pochettes dans Réglages → Fonctions."
        : "Enable album artwork in Settings → Features.",
    );
  if (page.icon === "record") {
    if (!config.integrations?.obs?.enabled)
      notes.push(
        fr
          ? "Configurez OBS dans Réglages → Intégrations."
          : "Configure OBS in Settings → Integrations.",
      );
    if (page.dashboard === "stream_chat")
      notes.push(
        fr
          ? "Connectez Twitch et choisissez une chaîne dans Réglages → Streaming."
          : "Connect Twitch and choose a channel in Settings → Streaming.",
      );
    if (!scenes.length)
      notes.push(
        fr
          ? "Aucune scène disponible : ajoutez sa commande après la connexion à OBS."
          : "No scenes available: add a scene control after connecting OBS.",
      );
  }
  if (page.dashboard === "notifications")
    notes.push(
      fr
        ? "La lecture des notifications dépend des autorisations du système."
        : "Reading notifications requires system permissions.",
    );
  return notes;
}
