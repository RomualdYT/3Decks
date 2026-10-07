import { Description, Disclosure, Label, Radio, RadioGroup } from "@heroui/react";
import type { Locale, PageConfig, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { localized, setLocalized } from "../utils/config";
import { ColorControl } from "../components/ColorControl";
import { DeckIcon } from "../components/DeckIcon";
import { NumberControl, SelectControl, TextControl } from "../components/FormControls";
import { InspectorDeleteAction, InspectorPreviewNote, InspectorSection, LocalizedInspectorField } from "./InspectorControls";
import { IconPicker } from "../components/IconPicker";

interface Props {
  page: PageConfig;
  schema: Schema;
  locale: Locale;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onUpdatePage: (update: (page: PageConfig) => void) => void;
  onDeletePage: () => void;
}

function PageTitleField({ page, locale, maxLength, label, onUpdatePage }: Pick<Props, "page" | "locale" | "onUpdatePage"> & { maxLength: number; label: string }) {
  return <LocalizedInspectorField value={page.title} locale={locale} maxLength={maxLength} label={label}
    onChange={(value) => onUpdatePage((item) => { item.title = setLocalized(item.title, locale, value); })} />;
}

function TouchLayoutPicker({ value, locale, onChange }: { value: PageConfig["layout"]; locale: Locale; onChange: (layout: "grid" | "list") => void }) {
  const fr = locale === "fr";
  const choices = [
    { id: "grid", icon: "grid", title: fr ? "Grille" : "Grid", description: fr ? "6 grands boutons" : "6 large buttons" },
    { id: "list", icon: "list", title: fr ? "Liste" : "List", description: fr ? "Plus de place pour le texte" : "More room for text" },
  ];
  return <RadioGroup className="page-layout-picker" aria-label={fr ? "Disposition de l’écran tactile" : "Touch-screen layout"}
    value={value ?? "grid"} onChange={(next) => { if (next === "grid" || next === "list") onChange(next); }}>
    {choices.map((choice) => <Radio key={choice.id} value={choice.id} className="page-layout-option">
      <Radio.Content>
        <DeckIcon name={choice.icon} size={20} />
        <Label>{choice.title}</Label>
      </Radio.Content>
      <Description>{choice.description}</Description>
    </Radio>)}
  </RadioGroup>;
}

const DASHBOARD_COPY: Record<string, { fr: string; en: string; icon: string; descriptionFr: string; descriptionEn: string }> = {
  auto: { fr: "Automatique", en: "Automatic", icon: "sparkle", descriptionFr: "Choisit le contenu le plus utile selon l’activité.", descriptionEn: "Chooses the most useful content for the current activity." },
  media: { fr: "Musique en cours", en: "Now playing", icon: "music", descriptionFr: "Titre, artiste et progression de lecture.", descriptionEn: "Track, artist and playback progress." },
  lyrics: { fr: "Paroles synchronisées", en: "Synced lyrics", icon: "music", descriptionFr: "Paroles sur l’écran supérieur, avec repli si elles sont indisponibles.", descriptionEn: "Lyrics on the top screen, with a fallback when unavailable." },
  system: { fr: "État de l’ordinateur", en: "Computer status", icon: "monitor", descriptionFr: "Utilisation du processeur, mémoire et application active.", descriptionEn: "CPU, memory and active application." },
  apps: { fr: "Applications ouvertes", en: "Open applications", icon: "app", descriptionFr: "Applications actuellement disponibles sur l’ordinateur.", descriptionEn: "Applications currently available on the computer." },
  audio: { fr: "Sorties audio", en: "Audio outputs", icon: "volume-up", descriptionFr: "Sortie audio active et volume.", descriptionEn: "Current audio output and volume." },
  frame: { fr: "Pochette plein écran", en: "Full-screen artwork", icon: "square", descriptionFr: "Met en avant la pochette du média en cours.", descriptionEn: "Highlights artwork from the current media." },
  notifications: { fr: "Notifications", en: "Notifications", icon: "bell", descriptionFr: "Affiche les notifications récentes du système.", descriptionEn: "Shows recent system notifications." },
};

export function PageInspector({ page, schema, locale, t, onUpdatePage, onDeletePage }: Props) {
  const fr = locale === "fr";
  const otherLocale = fr ? "en" : "fr";
  const sourceChoices = [
    { id: "manual", label: fr ? "Mes propres actions" : "My own actions", icon: "plus", description: fr ? "Vous choisissez chaque bouton de la page." : "You choose every button on the page." },
    { id: "windows", label: fr ? "Fenêtres disponibles" : "Available windows", icon: "app", description: fr ? "Liste automatiquement les fenêtres ouvertes." : "Automatically lists open windows." },
    ...(schema.extension_sources ?? []).map((source) => ({ id: source.name, label: localized(source.title, locale), icon: source.icon, description: source.supported ? localized(source.description, locale) : (fr ? "À activer dans Extensions." : "Enable in Extensions.") })),
  ];
  if (page.source && !sourceChoices.some((choice) => choice.id === page.source)) sourceChoices.push({ id: page.source, label: page.source, icon: "extension", description: fr ? "Extension manquante" : "Missing extension" });
  const dashboardChoices = schema.dashboards.map((dashboard) => {
    const copy = DASHBOARD_COPY[dashboard.name];
    return { id: dashboard.name, label: localized(dashboard.title, locale) || copy?.[locale] || dashboard.name, icon: dashboard.icon || copy?.icon || "extension", description: dashboard.supported ? localized(dashboard.description, locale) || copy?.[fr ? "descriptionFr" : "descriptionEn"] : dashboard.name.startsWith("ext:") ? (fr ? "À activer dans Extensions." : "Enable in Extensions.") : (fr ? "Source désactivée dans Réglages → Fonctionnalités." : "Source disabled in Settings → Features.") };
  });
  if (!dashboardChoices.some((choice) => choice.id === page.dashboard)) dashboardChoices.push({ id: page.dashboard, label: page.dashboard, icon: "extension", description: fr ? "Extension manquante" : "Missing extension" });
  return <aside className="inspector inspector-essential page-inspector">
    <div className="inspector-title inspector-heading">
      <span className="selection-icon"><DeckIcon name={page.icon || "page"} /></span>
      <div><span className="inspector-context">{t("pageSettings")}</span><h2>{localized(page.title, locale) || page.id}</h2></div>
    </div>
    <div className="inspector-scroll">
      <InspectorSection title={fr ? "Identité" : "Identity"}>
        <PageTitleField page={page} locale={locale} maxLength={schema.limits.label} label={fr ? "Nom de la page" : "Page name"} onUpdatePage={onUpdatePage} />
        <IconPicker icons={schema.icons} value={page.icon || "page"} locale={locale} label={t("icon")} onChange={(icon) => onUpdatePage((item) => { item.icon = icon; })} />
        <Disclosure className="inspector-translation">
          <Disclosure.Heading><Disclosure.Trigger>{fr ? "Traduction anglaise" : "French translation"}<Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
          <Disclosure.Content><Disclosure.Body>
            <PageTitleField page={page} locale={otherLocale} maxLength={schema.limits.label} label={fr ? "Nom de la page" : "Page name"} onUpdatePage={onUpdatePage} />
          </Disclosure.Body></Disclosure.Content>
        </Disclosure>
      </InspectorSection>
      <InspectorSection title={fr ? "Écran tactile" : "Touch screen"} icon="grid">
        <TouchLayoutPicker value={page.layout} locale={locale} onChange={(value) => onUpdatePage((item) => { item.layout = value; })} />
        <SelectControl label={fr ? "Contenu des boutons" : "Button content"} value={page.source || "manual"} choices={sourceChoices}
          onChange={(value) => onUpdatePage((item) => { item.source = value === "manual" ? "" : value; })} />
      </InspectorSection>
      <InspectorSection title={fr ? "Écran supérieur" : "Top screen"} icon="monitor">
        <SelectControl label={fr ? "Informations affichées en haut" : "Information shown on top"} value={page.dashboard || "auto"} choices={dashboardChoices}
          onChange={(value) => onUpdatePage((item) => { item.dashboard = value; })} />
        {page.dashboard === "lyrics" && <>
          <h4 className="page-lyrics-heading">{fr ? "Affichage des paroles" : "Lyrics display"}</h4>
          <NumberControl label={fr ? "Lignes visibles" : "Visible lines"} value={typeof page.lyrics_lines === "number" ? page.lyrics_lines : 3} min={2} max={5} step={1} onChange={(value) => onUpdatePage((item) => { item.lyrics_lines = value; })} />
          <SelectControl label={fr ? "Couleur d’ambiance" : "Accent colour"} value={typeof page.accent === "string" && page.accent ? "custom" : "artwork"} choices={[{ id: "artwork", label: fr ? "Selon la pochette" : "From artwork" }, { id: "custom", label: fr ? "Personnalisée" : "Custom" }]} onChange={(value) => onUpdatePage((item) => { item.accent = value === "custom" ? "#66CB10" : ""; })} />
          {typeof page.accent === "string" && page.accent && <ColorControl label={fr ? "Couleur" : "Colour"} value={page.accent} onChange={(value) => onUpdatePage((item) => { item.accent = value; })} />}
          <p className="inspector-hint">{fr ? "L’accès à LRCLIB s’active dans Réglages → Fonctionnalités. Le titre et l’artiste quittent alors le PC." : "Enable LRCLIB in Settings → Features. Track title and artist are then sent to the service."}</p>
        </>}
      </InspectorSection>
      <Disclosure className="inspector-advanced">
        <Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="gear" size={16} />{fr ? "Avancé et actions de page" : "Advanced & page actions"}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
        <Disclosure.Content><Disclosure.Body>
          <TextControl label={t("technicalId")} value={page.id} maxLength={schema.limits.id}
            description={fr ? "Utilisé par les actions qui ouvrent cette page." : "Used by actions that navigate to this page."}
            onChange={(value) => onUpdatePage((item) => { item.id = value; })} />
          <InspectorDeleteAction kind="page" locale={locale} name={localized(page.title, locale) || page.id} onDelete={onDeletePage} />
        </Disclosure.Body></Disclosure.Content>
      </Disclosure>
    </div>
    <InspectorPreviewNote locale={locale} />
  </aside>;
}
