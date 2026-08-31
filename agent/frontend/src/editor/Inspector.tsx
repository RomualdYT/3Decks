import { Button, Card, Disclosure } from "@heroui/react";
import type { ActionSpec, ActionValue, ButtonConfig, DeckConfig, Locale, PageConfig, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { actionArgs, actionKind, localized } from "../utils/config";
import { ColorControl } from "../components/ColorControl";
import { DeckIcon } from "../components/DeckIcon";
import { ComboControl, NumberControl, SelectControl, TextControl } from "../components/FormControls";
import { IconPicker } from "../components/IconPicker";
import { HotkeyInput } from "../components/HotkeyInput";
import { PathPicker } from "../components/PathPicker";
import { ExtensionField } from "../extensions/ExtensionFields";

interface Props {
  config: DeckConfig;
  schema: Schema;
  page: PageConfig;
  button: ButtonConfig | null;
  locale: Locale;
  scenes: string[];
  apps: string[];
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onUpdatePage: (update: (page: PageConfig) => void) => void;
  onUpdateButton: (update: (button: ButtonConfig) => void) => void;
  onChangeAction: () => void;
  onDeletePage: () => void;
  onDeleteButton: () => void;
  onDeselect: () => void;
}

function updateLocalized(value: PageConfig["title"], locale: Locale, text: string) {
  return { ...(typeof value === "string" ? { fr: value, en: value } : value), [locale]: text };
}

const DASHBOARD_COPY: Record<string, { fr: string; en: string; icon: string; descriptionFr: string; descriptionEn: string }> = {
  auto: { fr: "Automatique", en: "Automatic", icon: "sparkle", descriptionFr: "Choisit le contenu le plus utile selon l’activité.", descriptionEn: "Chooses the most useful content for the current activity." },
  media: { fr: "Musique en cours", en: "Now playing", icon: "music", descriptionFr: "Titre, artiste et progression de lecture.", descriptionEn: "Track, artist and playback progress." },
  system: { fr: "État de l’ordinateur", en: "Computer status", icon: "monitor", descriptionFr: "Utilisation du processeur, mémoire et application active.", descriptionEn: "CPU, memory and active application." },
  apps: { fr: "Applications ouvertes", en: "Open applications", icon: "app", descriptionFr: "Applications actuellement disponibles sur l’ordinateur.", descriptionEn: "Applications currently available on the computer." },
  audio: { fr: "Sorties audio", en: "Audio outputs", icon: "volume-up", descriptionFr: "Sortie audio active et volume.", descriptionEn: "Current audio output and volume." },
  frame: { fr: "Pochette plein écran", en: "Full-screen artwork", icon: "square", descriptionFr: "Met en avant la pochette du média en cours.", descriptionEn: "Highlights artwork from the current media." },
  notifications: { fr: "Notifications", en: "Notifications", icon: "bell", descriptionFr: "Affiche les notifications récentes du système.", descriptionEn: "Shows recent system notifications." },
};

function argumentCopy(name: string, kind: string, locale: Locale) {
  const fr = locale === "fr";
  const values: Record<string, [string, string]> = {
    target: kind.startsWith("app.") ? ["Application", "Application"] : ["Nom ou destination", "Name or target"],
    value: ["Niveau", "Level"],
    keys: ["Raccourci", "Shortcut"],
    url: ["Adresse du site", "Website address"],
    path: ["Fichier ou dossier", "File or folder"],
    scene: ["Scène OBS", "OBS scene"],
    source: ["Source OBS", "OBS source"],
    page: ["Page à ouvrir", "Page to open"],
    script: ["Automatisation", "Automation"],
  };
  const descriptions: Record<string, [string, string]> = {
    target: kind.startsWith("app.") ? ["Choisissez une application détectée, ou saisissez son nom si elle n’apparaît pas.", "Choose a detected app, or type its name if it is missing."] : ["Nom reconnu par votre ordinateur.", "A name recognized by your computer."],
    value: ["Valeur comprise entre 0 et 100.", "A value between 0 and 100."],
    url: ["Exemple : youtube.com. HTTPS est ajouté automatiquement.", "Example: youtube.com. HTTPS is added automatically."],
    path: ["Choisissez l’élément directement sur cet ordinateur.", "Choose the item directly on this computer."],
    scene: ["Les scènes apparaissent après avoir testé OBS dans les réglages.", "Scenes appear after testing OBS in Settings."],
    source: ["Nom exact de la source tel qu’il apparaît dans OBS.", "Exact source name as shown in OBS."],
  };
  return { label: (values[name] ?? [name, name])[fr ? 0 : 1], description: descriptions[name]?.[fr ? 0 : 1] };
}

function SectionTitle({ icon, title, description }: { icon: string; title: string; description?: string }) {
  return <div className={`inspector-section-title ${description ? "" : "compact"}`}><span><DeckIcon name={icon} size={16} /></span><div><strong>{title}</strong>{description && <small>{description}</small>}</div></div>;
}

function LocalizedFields({ label, frValue, enValue, maxLength, onFrChange, onEnChange }: { label: string; frValue: string; enValue: string; maxLength: number; onFrChange: (value: string) => void; onEnChange: (value: string) => void }) {
  return <div className="localized-fields"><div className="localized-field"><span className="language-badge">FR</span><TextControl label={label} value={frValue} maxLength={maxLength} onChange={onFrChange} /></div><div className="localized-field"><span className="language-badge">EN</span><TextControl label={label} value={enValue} maxLength={maxLength} onChange={onEnChange} /></div></div>;
}

export function Inspector({ config, schema, page, button, locale, scenes, apps, t, onUpdatePage, onUpdateButton, onChangeAction, onDeletePage, onDeleteButton, onDeselect }: Props) {
  const fr = locale === "fr";
  if (!button) {
    const layoutChoices = [
      { id: "grid", label: t("grid"), icon: "grid", description: fr ? "6 grandes actions immédiatement accessibles" : "6 large, immediately accessible actions" },
      { id: "list", label: t("list"), icon: "list", description: fr ? "Des lignes lisibles avec plus de texte" : "Readable rows with more text" },
    ];
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
    return (
    <aside className="inspector">
      <div className="inspector-title"><div><span className="eyebrow">{t("page")}</span><h2>{t("pageSettings")}</h2></div><span className="selection-icon"><DeckIcon name={page.icon || "page"} /></span></div>
      <div className="inspector-scroll">
        <SectionTitle icon="edit" title={fr ? "Nom et apparence" : "Name and appearance"} />
        <LocalizedFields label={fr ? "Titre" : "Title"} frValue={localized(page.title, "fr")} enValue={localized(page.title, "en")} maxLength={schema.limits.label} onFrChange={(value) => onUpdatePage((item) => { item.title = updateLocalized(item.title, "fr", value); })} onEnChange={(value) => onUpdatePage((item) => { item.title = updateLocalized(item.title, "en", value); })} />
        <IconPicker icons={schema.icons} value={page.icon || "page"} label={t("icon")} onChange={(icon) => onUpdatePage((item) => { item.icon = icon; })} />
        <div className="form-divider" />
        <SectionTitle icon="grid" title={fr ? "Organisation" : "Layout"} />
        <SelectControl label={fr ? "Disposition de l’écran tactile" : "Touch-screen layout"} value={page.layout ?? "grid"} choices={layoutChoices} description={fr ? "La grille 3 × 2 est disponible sur toutes les pages." : "The 3 × 2 grid is available on every page."} onChange={(value) => onUpdatePage((item) => { item.layout = value as PageConfig["layout"]; })} />
        <div className="form-divider" />
        <SectionTitle icon="app" title={fr ? "Contenu des boutons" : "Button content"} />
        <SelectControl label={fr ? "Que doit afficher cette page ?" : "What should this page show?"} value={page.source || "manual"} choices={sourceChoices} onChange={(value) => onUpdatePage((item) => { item.source = value === "manual" ? "" : value; })} />
        <div className="form-divider" />
        <SectionTitle icon="monitor" title={fr ? "Écran supérieur" : "Top screen"} />
        <SelectControl label={fr ? "Informations affichées en haut" : "Information shown on top"} value={page.dashboard || "auto"} choices={dashboardChoices} description={fr ? "L’aperçu de la console se met à jour immédiatement." : "The console preview updates immediately."} onChange={(value) => onUpdatePage((item) => { item.dashboard = value; })} />
        <Disclosure className="advanced-disclosure">
          <Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="gear" size={16} />{t("advanced")}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
          <Disclosure.Content><Disclosure.Body><Card variant="secondary" className="technical-help"><Card.Content><DeckIcon name="info" size={16} /><p>{fr ? "L’identifiant relie cette page aux actions de navigation. Ne le changez que si vous savez qu’une intégration externe l’utilise." : "The identifier links this page to navigation actions. Only change it when an external integration relies on it."}</p></Card.Content></Card><TextControl label={t("technicalId")} value={page.id} maxLength={schema.limits.id} onChange={(value) => onUpdatePage((item) => { item.id = value; })} /></Disclosure.Body></Disclosure.Content>
        </Disclosure>
      </div>
      <div className="inspector-footer"><Button fullWidth variant="danger-soft" onPress={onDeletePage}><DeckIcon name="trash" size={17} />{t("delete")}</Button></div>
    </aside>
    );
  }

  const kind = actionKind(button.action);
  const spec = schema.actions.find((action) => action.kind === kind);
  const args = actionArgs(button.action);
  const setArg = (name: string, value: string | number | boolean) => onUpdateButton((item) => { item.action = { type: kind, ...actionArgs(item.action), [name]: value } as ActionValue; });
  return (
    <aside className="inspector">
      <div className="inspector-title"><div><button className="back-link" type="button" onClick={onDeselect}>‹ {t("pageSettings")}</button><h2>{t("buttonSettings")}</h2></div><span className="selection-icon"><DeckIcon name={button.icon} /></span></div>
      <div className="inspector-scroll">
        <SectionTitle icon="edit" title={fr ? "Texte et apparence" : "Text and appearance"} />
        <LocalizedFields label={fr ? "Libellé" : "Label"} frValue={localized(button.label, "fr")} enValue={localized(button.label, "en")} maxLength={schema.limits.label} onFrChange={(value) => onUpdateButton((item) => { item.label = updateLocalized(item.label, "fr", value); })} onEnChange={(value) => onUpdateButton((item) => { item.label = updateLocalized(item.label, "en", value); })} />
        <IconPicker icons={schema.icons} value={button.icon} label={t("icon")} onChange={(icon) => onUpdateButton((item) => { item.icon = icon; })} />
        <ColorControl label={t("color")} value={button.color} onChange={(color) => onUpdateButton((item) => { item.color = color; })} />
        <div className="form-divider" />
        <SectionTitle icon="workflow" title={t("action")} description={fr ? "Ce que fera le bouton lorsqu’on le touchera sur la console." : "What happens when this button is tapped on the console."} />
        <button className="current-action" type="button" onClick={onChangeAction}><span style={{ "--action-color": spec?.color ?? button.color } as React.CSSProperties}><DeckIcon name={spec?.icon ?? button.icon} /></span><span><strong>{spec?.title[locale] ?? kind}</strong><small>{spec?.description[locale] ?? kind}</small></span><DeckIcon name="down" /></button>
        {!spec?.supported && <Card variant="secondary" className="support-warning"><Card.Content><DeckIcon name="info" /><p>{kind.startsWith("ext:") ? (fr ? "Vérifiez que cette intégration est installée et activée dans Extensions. Ses paramètres sont conservés." : "Check that this integration is installed and enabled in Extensions. Its parameters are preserved.") : (fr ? "Cette action nécessite une fonctionnalité désactivée. Vous pouvez l’activer dans Réglages → Fonctionnalités." : "This action needs a disabled feature. Enable it in Settings → Features.")}</p></Card.Content></Card>}
        {spec?.arguments.map((argument) => spec.extension ? <ExtensionField key={argument.name} field={argument} value={args[argument.name] ?? argument.default} locale={locale} onChange={(value) => setArg(argument.name, value)} /> : <ActionArgumentControl key={argument.name} argument={argument} spec={spec} value={String(args[argument.name] ?? "")} locale={locale} config={config} scenes={scenes} apps={apps} schema={schema} onChange={(value) => setArg(argument.name, value)} />)}
        <Button fullWidth variant="outline" onPress={onChangeAction}>{t("changeAction")}</Button>
        <Disclosure className="advanced-disclosure"><Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="gear" size={16} />{t("advanced")}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading><Disclosure.Content><Disclosure.Body><Card variant="secondary" className="technical-help"><Card.Content><DeckIcon name="info" size={16} /><p>{fr ? "Cet identifiant est utilisé par le fichier de configuration et la console. Il n’affecte pas le texte affiché." : "This identifier is used by the configuration file and console. It does not change the displayed label."}</p></Card.Content></Card><TextControl label={t("technicalId")} value={button.id} maxLength={schema.limits.id} onChange={(value) => onUpdateButton((item) => { item.id = value; })} /></Disclosure.Body></Disclosure.Content></Disclosure>
      </div>
      <div className="inspector-footer"><Button fullWidth variant="danger-soft" onPress={onDeleteButton}><DeckIcon name="trash" size={17} />{t("delete")}</Button></div>
    </aside>
  );
}

function ActionArgumentControl({ argument, spec, value, locale, config, scenes, apps, schema, onChange }: { argument: ActionSpec["arguments"][number]; spec: ActionSpec; value: string; locale: Locale; config: DeckConfig; scenes: string[]; apps: string[]; schema: Schema; onChange: (value: string | number) => void }) {
  const copy = argumentCopy(argument.name, spec.kind, locale);
  const fr = locale === "fr";
  if (argument.type === "page") return <SelectControl label={copy.label} value={value} description={copy.description} choices={config.pages.map((item) => ({ id: item.id, label: localized(item.title, locale) || item.id, icon: item.icon }))} onChange={onChange} />;
  if (argument.type === "script") return <SelectControl label={copy.label} value={value} choices={Object.keys(config.scripts ?? {}).map((script) => ({ id: script, label: script, icon: "workflow" }))} onChange={onChange} />;
  if (argument.type === "hotkey") return <div className="ui-field"><span className="field-label">{copy.label}</span><HotkeyInput value={value} catalog={schema.keys} locale={locale} onChange={onChange} /></div>;
  if (argument.name === "path" && spec.kind === "path.open") return <PathPicker value={value} locale={locale} onChange={(next) => onChange(next)} />;
  if (argument.name === "scene") return <SelectControl label={copy.label} value={value} description={copy.description} choices={(scenes.length ? scenes : [value].filter(Boolean)).map((scene) => ({ id: scene, label: scene, icon: "video", description: scenes.length ? undefined : (fr ? "Testez la connexion OBS pour charger vos scènes." : "Test OBS to load your scenes.") }))} onChange={onChange} />;
  if (argument.type === "number") return <NumberControl label={copy.label} value={Number(value || 0)} min={0} max={100} description={copy.description} onChange={onChange} />;
  if (argument.name === "target" && spec.kind.startsWith("app.")) return <ComboControl label={copy.label} value={value} choices={apps} description={copy.description} placeholder={fr ? "Ex. Safari, Spotify, OBS Studio…" : "e.g. Safari, Spotify, OBS Studio…"} onChange={onChange} />;
  return <TextControl label={copy.label} value={value} description={copy.description} placeholder={argument.name === "url" ? "youtube.com" : undefined} type={argument.name === "url" ? "url" : "text"} isRequired={argument.required} onChange={(next) => onChange(next)} />;
}
