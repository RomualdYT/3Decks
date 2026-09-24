import type { DeckConfig, PageConfig, Schema } from "../app/types";
import { defaultAction, newPage, uniqueId } from "../utils/config";

export type PageTemplateId = "blank" | "lyrics" | "notifications" | "windows" | "obs" | "system";

export const PAGE_TEMPLATES: { id: PageTemplateId; title: { fr: string; en: string }; description: { fr: string; en: string }; icon: string; dashboard: string; actions: string[] }[] = [
  { id: "blank", title: { fr: "Page vierge", en: "Blank page" }, description: { fr: "Composez chaque écran librement.", en: "Build both screens your way." }, icon: "page", dashboard: "auto", actions: [] },
  { id: "lyrics", title: { fr: "Musique et paroles", en: "Music and lyrics" }, description: { fr: "Paroles synchronisées en haut, lecture en bas.", en: "Synced lyrics above, playback below." }, icon: "music", dashboard: "lyrics", actions: ["media.previous", "media.play_pause", "media.next", "volume.down", "volume.up", "frame.toggle"] },
  { id: "notifications", title: { fr: "Notifications", en: "Notifications" }, description: { fr: "Notifications récentes et accès aux réglages.", en: "Recent notifications and quick access to settings." }, icon: "bell", dashboard: "notifications", actions: ["settings.open"] },
  { id: "windows", title: { fr: "Fenêtres", en: "Windows" }, description: { fr: "Vos fenêtres ouvertes, mises à jour automatiquement.", en: "Your open windows, updated automatically." }, icon: "app", dashboard: "apps", actions: [] },
  { id: "obs", title: { fr: "OBS Studio", en: "OBS Studio" }, description: { fr: "Enregistrement, diffusion et scènes.", en: "Recording, streaming and scenes." }, icon: "monitor", dashboard: "system", actions: ["obs.record.toggle", "obs.stream.toggle", "obs.scene.set"] },
  { id: "system", title: { fr: "Performances", en: "Performance" }, description: { fr: "CPU, mémoire et commandes utiles.", en: "CPU, memory and useful controls." }, icon: "monitor", dashboard: "system", actions: ["volume.down", "volume.mute_toggle", "volume.up", "modal.volumes"] },
];

export function pageFromTemplate(config: DeckConfig, schema: Schema, id: PageTemplateId, scenes: string[] = []): PageConfig {
  const template = PAGE_TEMPLATES.find((item) => item.id === id) ?? PAGE_TEMPLATES[0];
  if (id === "blank") return newPage(config);
  const page: PageConfig = {
    id: uniqueId(id, config.pages.map((item) => item.id)),
    title: { ...template.title }, icon: template.icon, dashboard: template.dashboard,
    layout: id === "windows" ? "list" : "grid", source: id === "windows" ? "windows" : "", buttons: [],
  };
  if (id === "lyrics") page.lyrics_lines = 3;
  for (const [slot, kind] of template.actions.entries()) {
    if (kind === "obs.scene.set" && scenes.length === 0) continue;
    const spec = schema.actions.find((item) => item.kind === kind);
    if (!spec) continue;
    page.buttons.push({
      id: uniqueId("button", page.buttons.map((item) => item.id)), slot,
      label: { fr: spec.title.fr.slice(0, 24), en: spec.title.en.slice(0, 24) },
      icon: spec.icon, color: spec.color, action: defaultAction(spec, config, scenes),
    });
  }
  return page;
}
