import { Card, Disclosure } from "@heroui/react";
import type { CSSProperties } from "react";
import type { ActionSpec, ActionValue, ButtonConfig, DeckConfig, Locale, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { actionArgs, actionKind, localized, setLocalized } from "../utils/config";
import { ColorControl } from "../components/ColorControl";
import { DeckIcon } from "../components/DeckIcon";
import { ComboControl, NumberControl, SelectControl, TextControl } from "../components/FormControls";
import { IconPicker } from "../components/IconPicker";
import { HotkeyInput } from "../components/HotkeyInput";
import { PathPicker } from "../components/PathPicker";
import { ApplicationPicker } from "../components/ApplicationPicker";
import { InspectorDeleteAction, InspectorPreviewNote, InspectorSection, LocalizedInspectorField } from "./InspectorControls";
import { ExtensionField } from "../extensions/ExtensionFields";

export interface ButtonInspectorProps {
  config: DeckConfig;
  schema: Schema;
  button: ButtonConfig;
  locale: Locale;
  platform?: string;
  scenes: string[];
  apps: string[];
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onUpdateButton: (update: (button: ButtonConfig) => void) => void;
  onChangeAction: () => void;
  onDeleteButton: () => void;
  onDeselect: () => void;
}

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

export function ButtonInspector({ config, schema, button, locale, platform, scenes, apps, t, onUpdateButton, onChangeAction, onDeleteButton, onDeselect }: ButtonInspectorProps) {
  const fr = locale === "fr";
  const otherLocale = fr ? "en" : "fr";
  const updateLabel = (language: Locale, value: string) => onUpdateButton((item) => { item.label = setLocalized(item.label, language, value); });
  const kind = actionKind(button.action);
  const spec = schema.actions.find((action) => action.kind === kind);
  const args = actionArgs(button.action);
  const setArg = (name: string, value: string | number | boolean) => onUpdateButton((item) => { item.action = { type: kind, ...actionArgs(item.action), [name]: value } as ActionValue; });
  return (
    <aside className="inspector inspector-essential button-inspector">
      <div className="inspector-title inspector-heading">
        <span className="selection-icon"><DeckIcon name={button.icon} /></span>
        <div><button className="back-link" type="button" onClick={onDeselect}>‹ {t("pageSettings")}</button><span className="inspector-context">{t("buttonSettings")}</span><h2>{localized(button.label, locale) || button.id}</h2></div>
      </div>
      <div className="inspector-scroll">
        <InspectorSection title={fr ? "Identité" : "Identity"}>
          <LocalizedInspectorField value={button.label} locale={locale} maxLength={schema.limits.label} label={fr ? "Libellé du bouton" : "Button label"} onChange={(value) => updateLabel(locale, value)} />
          <IconPicker locale={locale} icons={schema.icons} value={button.icon} label={t("icon")} onChange={(icon) => onUpdateButton((item) => { item.icon = icon; })} />
          <ColorControl label={t("color")} value={button.color} onChange={(color) => onUpdateButton((item) => { item.color = color; })} />
          <Disclosure className="inspector-translation">
            <Disclosure.Heading><Disclosure.Trigger>{fr ? "Traduction anglaise" : "French translation"}<Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
            <Disclosure.Content><Disclosure.Body>
              <LocalizedInspectorField value={button.label} locale={otherLocale} maxLength={schema.limits.label} label={fr ? "Libellé du bouton" : "Button label"} onChange={(value) => updateLabel(otherLocale, value)} />
            </Disclosure.Body></Disclosure.Content>
          </Disclosure>
        </InspectorSection>
        <InspectorSection title={t("action")} icon="workflow">
          <button className="current-action" type="button" aria-label={t("changeAction")} onClick={onChangeAction}><span style={{ "--action-color": spec?.color ?? button.color } as CSSProperties}><DeckIcon name={spec?.icon ?? button.icon} /></span><span><strong>{spec?.title[locale] ?? kind}</strong><small>{spec?.description[locale] ?? kind}</small></span><DeckIcon name="down" /></button>
          {!spec?.supported && <Card variant="secondary" className="support-warning"><Card.Content><DeckIcon name="info" /><p>{kind.startsWith("ext:") ? (fr ? "Vérifiez que cette intégration est installée et activée dans Extensions. Ses paramètres sont conservés." : "Check that this integration is installed and enabled in Extensions. Its parameters are preserved.") : (fr ? "Cette action nécessite une fonctionnalité désactivée. Vous pouvez l’activer dans Réglages → Fonctionnalités." : "This action needs a disabled feature. Enable it in Settings → Features.")}</p></Card.Content></Card>}
          {spec?.arguments.map((argument) => spec.extension ? <ExtensionField key={argument.name} field={argument} value={args[argument.name] ?? argument.default} locale={locale} onChange={(value) => setArg(argument.name, value)} /> : <ActionArgumentControl key={argument.name} argument={argument} spec={spec} value={String(args[argument.name] ?? "")} locale={locale} platform={platform} config={config} scenes={scenes} apps={apps} schema={schema} onChange={(value) => setArg(argument.name, value)} />)}
        </InspectorSection>
        <Disclosure className="inspector-advanced">
          <Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="gear" size={16} />{fr ? "Avancé et actions du bouton" : "Advanced & button actions"}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
          <Disclosure.Content><Disclosure.Body>
            <TextControl label={t("technicalId")} value={button.id} maxLength={schema.limits.id} description={fr ? "Identifiant du bouton dans la configuration." : "Button identifier in the configuration."} onChange={(value) => onUpdateButton((item) => { item.id = value; })} />
            <InspectorDeleteAction kind="button" locale={locale} name={localized(button.label, locale) || button.id} onDelete={onDeleteButton} />
          </Disclosure.Body></Disclosure.Content>
        </Disclosure>
      </div>
      <InspectorPreviewNote locale={locale} />
    </aside>
  );
}

function ActionArgumentControl({ argument, spec, value, locale, platform, config, scenes, apps, schema, onChange }: { argument: ActionSpec["arguments"][number]; spec: ActionSpec; value: string; locale: Locale; platform?: string; config: DeckConfig; scenes: string[]; apps: string[]; schema: Schema; onChange: (value: string | number) => void }) {
  const copy = argumentCopy(argument.name, spec.kind, locale);
  const fr = locale === "fr";
  if (argument.type === "page") return <SelectControl label={copy.label} value={value} description={copy.description} choices={config.pages.map((item) => ({ id: item.id, label: localized(item.title, locale) || item.id, icon: item.icon }))} onChange={onChange} />;
  if (argument.type === "script") return <SelectControl label={copy.label} value={value} choices={Object.keys(config.scripts ?? {}).map((script) => ({ id: script, label: script, icon: "workflow" }))} onChange={onChange} />;
  if (argument.type === "hotkey") return <div className="ui-field"><span className="field-label">{copy.label}</span><HotkeyInput value={value} catalog={schema.keys} locale={locale} platform={platform} onChange={onChange} /></div>;
  if (argument.name === "path" && spec.kind === "path.open") return <PathPicker value={value} locale={locale} onChange={(next) => onChange(next)} />;
  if (argument.name === "scene") return <SelectControl label={copy.label} value={value} description={copy.description} choices={(scenes.length ? scenes : [value].filter(Boolean)).map((scene) => ({ id: scene, label: scene, icon: "video", description: scenes.length ? undefined : (fr ? "Testez la connexion OBS pour charger vos scènes." : "Test OBS to load your scenes.") }))} onChange={onChange} />;
  if (argument.type === "number") return <NumberControl label={copy.label} value={Number(value || argument.min || 0)} min={argument.min ?? 0} max={argument.max ?? 100} description={copy.description} onChange={onChange} />;
  if (argument.name === "target" && spec.kind === "app.launch") return <ApplicationPicker value={value} choices={apps} locale={locale} onChange={onChange} />;
  if (argument.name === "target" && spec.kind.startsWith("app.")) return <ComboControl label={copy.label} value={value} choices={apps} description={copy.description} placeholder={fr ? "Nom de l’application…" : "Application name…"} onChange={onChange} />;
  return <TextControl label={copy.label} value={value} description={copy.description} placeholder={argument.name === "url" ? "youtube.com" : undefined} type={argument.name === "url" ? "url" : "text"} isRequired={argument.required} maxLength={argument.max_length ?? undefined} onChange={(next) => onChange(next)} />;
}
