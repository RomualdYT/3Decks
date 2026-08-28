import { Button, Card, Disclosure, DisclosureGroup, Switch, toast } from "@heroui/react";
import { useState } from "react";
import { agentApi } from "../api/client";
import type { AgentState, DeckConfig, FeatureSpec, Locale, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { DeckIcon } from "../components/DeckIcon";
import { AppleMusicIcon, SpotifyIcon } from "../components/BrandIcons";
import { NumberControl, TextControl } from "../components/FormControls";

type Section = "connection" | "features" | "appearance" | "obs" | "advanced";

const SECTIONS: Array<[Section, string]> = [
  ["connection", "link"], ["features", "sliders"], ["appearance", "language"], ["obs", "video"], ["advanced", "gear"],
];

function tokenValue(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
}

interface Props {
  config: DeckConfig;
  schema: Schema;
  status: AgentState | null;
  locale: Locale;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  update: (recipe: (draft: DeckConfig) => void) => void;
  onLocale: (locale: Locale) => void;
  scenes: string[];
  onScenes: (scenes: string[]) => void;
}

export function SettingsView({ config, schema, status, locale, t, update, onLocale, scenes, onScenes }: Props) {
  const [section, setSection] = useState<Section>("connection");
  const [copied, setCopied] = useState(false);
  const [testing, setTesting] = useState(false);
  const [obsResult, setObsResult] = useState("");
  const address = status?.hints[0] ?? `127.0.0.1:${config.server.port}`;
  const portRange = schema.limits.port as number[];
  const pollRange = schema.limits.poll_interval as number[];
  const volumeRange = schema.limits.volume_step as number[];
  const obsTimeoutRange = schema.limits.obs_timeout as number[];
  return (
    <div className="settings-layout">
      <aside className="settings-sidebar">
        <div className="sidebar-heading"><div><span className="eyebrow">3Decks</span><h2>{t("settings")}</h2></div></div>
        <nav>{SECTIONS.map(([id, icon]) => <button key={id} type="button" aria-label={t(id === "features" ? "features" : id === "appearance" ? "appearance" : id === "obs" ? "obs" : id === "advanced" ? "advanced" : "connection")} className={section === id ? "active" : ""} onClick={() => setSection(id)}><span><DeckIcon name={icon} /></span>{t(id === "features" ? "features" : id === "appearance" ? "appearance" : id === "obs" ? "obs" : id === "advanced" ? "advanced" : "connection")}{id === "obs" && !config.integrations.obs.enabled ? <small>{t("disabled")}</small> : null}</button>)}</nav>
        <div className="settings-platform"><span className="connection-dot connected" /><div><strong>{status?.platform ?? "3Decks Agent"}</strong><small>{status ? t("online") : t("offline")}</small></div></div>
      </aside>
      <main className="settings-workspace">
        {section === "features" && <FeatureSettings config={config} schema={schema} status={status} locale={locale} t={t} update={update} />}
        {section === "connection" && <div className="settings-content"><SettingsHeading icon="link" title={t("connectionTitle")} help={t("connectionHelp")} />
          <Card className="address-card" variant="secondary"><Card.Content><div><span className="field-label">{t("address")}</span><code>{address}</code><small>{locale === "fr" ? "À saisir dans Réglages → Agent sur votre Nintendo 3DS." : "Enter this in Settings → Agent on your Nintendo 3DS."}</small></div><Button variant="outline" onPress={() => { void navigator.clipboard.writeText(address); setCopied(true); toast.success(locale === "fr" ? "Adresse copiée" : "Address copied"); window.setTimeout(() => setCopied(false), 1600); }}><DeckIcon name="copy" size={16} />{copied ? t("copied") : t("copy")}</Button></Card.Content></Card>
          <section className="settings-card"><div className="setting-row"><div className="setting-icon"><DeckIcon name="lock" /></div><div><h3>{t("security")}</h3><p>{t("tokenHelp")}</p></div><Switch aria-label={t("security")} isSelected={Boolean(config.server.token)} onChange={(enabled) => update((draft) => { draft.server.token = enabled ? tokenValue() : ""; })}><Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content></Switch></div><div className={`token-panel ${config.server.token ? "" : "token-empty"}`}><div><small>{locale === "fr" ? "Jeton de sécurité" : "Security token"}</small>{config.server.token ? <code>{config.server.token}</code> : <p>{locale === "fr" ? "Aucun jeton actif. Générez-en un pour autoriser uniquement votre console." : "No active token. Generate one to authorize only your console."}</p>}</div><div>{config.server.token ? <><Button size="sm" variant="outline" onPress={() => { void navigator.clipboard.writeText(config.server.token); toast.success(locale === "fr" ? "Jeton copié" : "Token copied"); }}><DeckIcon name="copy" size={15} />{t("copy")}</Button><Button size="sm" variant="ghost" onPress={() => update((draft) => { draft.server.token = tokenValue(); })}>{locale === "fr" ? "Régénérer" : "Regenerate"}</Button></> : <Button size="sm" variant="outline" onPress={() => update((draft) => { draft.server.token = tokenValue(); })}><DeckIcon name="lock" size={15} />{locale === "fr" ? "Activer et générer" : "Enable and generate"}</Button>}</div></div></section>
        </div>}
        {section === "appearance" && <div className="settings-content"><SettingsHeading icon="language" title={t("appearance")} help={t("detailsHelp")} />
          <section className="settings-card"><h3>{t("language")}</h3><div className="language-cards"><button type="button" className={locale === "fr" ? "active" : ""} onClick={() => onLocale("fr")}><span>FR</span><strong>{t("french")}</strong>{locale === "fr" && <DeckIcon name="sparkle" />}</button><button type="button" className={locale === "en" ? "active" : ""} onClick={() => onLocale("en")}><span>EN</span><strong>{t("english")}</strong>{locale === "en" && <DeckIcon name="sparkle" />}</button></div></section>
        </div>}
        {section === "obs" && <div className="settings-content"><SettingsHeading icon="video" title={t("obsTitle")} help={t("obsHelp")} />
          <section className="settings-card"><div className="setting-row"><div className="setting-icon"><DeckIcon name="video" /></div><div><h3>{t("obs")}</h3><p>OBS WebSocket 5.x · {config.integrations.obs.host}:{config.integrations.obs.port}</p></div><Switch aria-label={t("obs")} isSelected={config.integrations.obs.enabled} onChange={(enabled) => update((draft) => { draft.integrations.obs.enabled = enabled; })}><Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content></Switch></div></section>
          <form className="settings-card form-card" onSubmit={(event) => event.preventDefault()}><div className="two-fields"><TextControl label={t("host")} value={config.integrations.obs.host} description={locale === "fr" ? "Laissez localhost si OBS tourne sur cet ordinateur." : "Keep localhost when OBS runs on this computer."} onChange={(value) => update((draft) => { draft.integrations.obs.host = value; })} /><NumberControl label={t("port")} value={config.integrations.obs.port} min={portRange[0]} max={portRange[1]} onChange={(value) => update((draft) => { draft.integrations.obs.port = value; })} /></div><TextControl label={t("password")} type="password" autoComplete="current-password" value={config.integrations.obs.password} description={locale === "fr" ? "Défini dans OBS → Outils → Paramètres du serveur WebSocket." : "Set in OBS → Tools → WebSocket Server Settings."} onChange={(value) => update((draft) => { draft.integrations.obs.password = value; })} /><NumberControl label={t("timeout")} value={config.integrations.obs.timeout} min={obsTimeoutRange[0]} max={obsTimeoutRange[1]} step={0.1} description={locale === "fr" ? "Durée maximale d’attente lors d’une action OBS." : "Maximum wait time for an OBS action."} onChange={(value) => update((draft) => { draft.integrations.obs.timeout = value; })} />
            <div className="obs-actions"><Button variant="primary" isDisabled={testing} onPress={() => { setTesting(true); setObsResult(""); void agentApi.testObs(config.integrations.obs).then((result) => { const nextScenes = result.scenes ?? []; onScenes(nextScenes); setObsResult(`${t("connected")} · ${nextScenes.length} ${t("scenes")}`); }).catch((error: Error) => setObsResult(error.message)).finally(() => setTesting(false)); }}>{testing ? t("testing") : t("test")}</Button>{obsResult && <span className={scenes.length ? "success-text" : "error-text"}>{obsResult}</span>}</div>
            {scenes.length > 0 && <div className="scene-pills">{scenes.map((scene) => <span key={scene}>{scene}</span>)}</div>}
          </form>
        </div>}
        {section === "advanced" && <div className="settings-content"><SettingsHeading icon="gear" title={t("advanced")} help={locale === "fr" ? "Ces réglages influencent la communication entre votre ordinateur et la console." : "These settings affect communication between your computer and console."} />
          <DisclosureGroup className="advanced-settings-group" allowsMultipleExpanded defaultExpandedKeys={["network"]}><Disclosure id="network"><Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="wifi" />{locale === "fr" ? "Réseau de l’agent" : "Agent network"}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading><Disclosure.Content><Disclosure.Body><p>{locale === "fr" ? "L’adresse d’écoute et le port utilisés par la 3DS. Les valeurs par défaut conviennent à la majorité des installations." : "The listen address and port used by the 3DS. Defaults suit most setups."}</p><div className="two-fields"><TextControl label={t("host")} value={config.server.host} onChange={(value) => update((draft) => { draft.server.host = value; })} /><NumberControl label={t("port")} value={config.server.port} min={portRange[0]} max={portRange[1]} onChange={(value) => update((draft) => { draft.server.port = value; })} /></div></Disclosure.Body></Disclosure.Content></Disclosure><Disclosure id="timing"><Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="status" />{locale === "fr" ? "Fréquence et volume" : "Timing and volume"}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading><Disclosure.Content><Disclosure.Body><p>{locale === "fr" ? "À modifier uniquement pour ajuster la réactivité ou l’incrément des actions de volume." : "Only change these to tune responsiveness or volume action increments."}</p><div className="two-fields"><NumberControl label={locale === "fr" ? "Intervalle de mise à jour" : "Update interval"} value={config.server.poll_interval} min={pollRange[0]} max={pollRange[1]} step={0.1} description={locale === "fr" ? "En secondes. Une valeur basse actualise plus souvent." : "In seconds. Lower values refresh more often."} onChange={(value) => update((draft) => { draft.server.poll_interval = value; })} /><NumberControl label={locale === "fr" ? "Pas de volume" : "Volume step"} value={config.server.volume_step} min={volumeRange[0]} max={volumeRange[1]} description={locale === "fr" ? "Variation appliquée par les boutons + et −." : "Change applied by + and − buttons."} onChange={(value) => update((draft) => { draft.server.volume_step = value; })} /></div></Disclosure.Body></Disclosure.Content></Disclosure></DisclosureGroup>
        </div>}
      </main>
      <aside className="settings-context"><div className="context-illustration"><img src="/3decks-logo.png" alt="" /><i /><i /><i /></div><h3>{section === "features" ? t("featureTitle") : t("settings")}</h3><p>{section === "features" ? t("setupPermission") : t("detailsHelp")}</p><div className="context-tip"><DeckIcon name="info" /><span>{locale === "fr" ? "Les changements prennent effet après enregistrement, sans relancer l’agent." : "Changes take effect after saving, without restarting the agent."}</span></div></aside>
    </div>
  );
}

function SettingsHeading({ icon, title, help }: { icon: string; title: string; help: string }) {
  return <div className="settings-title"><span><DeckIcon name={icon} size={24} /></span><div><h1>{title}</h1><p>{help}</p></div></div>;
}

function FeatureSettings({ config, schema, status, locale, t, update }: Pick<Props, "config" | "schema" | "status" | "locale" | "t" | "update">) {
  const [openingPermission, setOpeningPermission] = useState<string | null>(null);
  const openPermission = (permission: string) => {
    setOpeningPermission(permission);
    void agentApi.openPermissionSettings(permission)
      .then(() => toast.success(t("permissionsOpened")))
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setOpeningPermission(null));
  };
  const groups: Array<{ title: string; icon: string; items: FeatureSpec[] }> = [
    { title: locale === "fr" ? "Informations système" : "System information", icon: "monitor", items: schema.features.filter((item) => ["notifications", "windows", "system_stats", "audio_output"].includes(item.key)) },
    { title: locale === "fr" ? "Média et lecteurs" : "Media and players", icon: "music", items: schema.features.filter((item) => ["media", "media_artwork", "apple_music", "spotify"].includes(item.key)) },
  ];
  return <div className="settings-content"><SettingsHeading icon="sliders" title={t("featureTitle")} help={t("featureHelp")} />
    {groups.map((group) => <section className="feature-group" key={group.title}><div className="feature-group-title"><DeckIcon name={group.icon} /><h2>{group.title}</h2></div>{group.items.map((feature) => {
      const parentEnabled = !feature.parent || config.features[feature.parent] !== false;
      const enabled = config.features[feature.key] ?? feature.enabled;
      const platformAvailable = !status?.platform || feature.platforms.includes(status.platform);
      const permissionAction = feature.key === "notifications" && enabled && status?.notifications?.available === false ? status.notifications.settings_action : undefined;
      return <div className={`feature-row ${feature.parent ? "nested" : ""} ${!platformAvailable ? "unavailable" : ""}`} key={feature.key}><div className={`feature-symbol ${feature.key === "spotify" || feature.key === "apple_music" ? "brand" : ""}`}>{feature.key === "spotify" ? <SpotifyIcon /> : feature.key === "apple_music" ? <AppleMusicIcon /> : <DeckIcon name={feature.key === "notifications" ? "bell" : feature.key === "windows" ? "app" : feature.key === "system_stats" ? "status" : feature.key === "audio_output" ? "volume-up" : feature.key === "media_artwork" ? "square" : "music"} />}</div><div className="feature-copy"><h3>{feature.title[locale]}</h3><p>{feature.description[locale]}</p>{!platformAvailable && <small>{t("unavailablePlatform")}</small>}{permissionAction ? <div className="feature-permission"><span><DeckIcon name="lock" size={14} />{t("permissionRequired")}</span><Button size="sm" variant="outline" isDisabled={openingPermission === permissionAction} onPress={() => openPermission(permissionAction)}><DeckIcon name="link" size={14} />{openingPermission === permissionAction ? t("openingPermissions") : t("openPermissions")}</Button></div> : null}</div><div className="feature-state"><span>{enabled && parentEnabled ? t("enabled") : t("disabled")}</span><Switch aria-label={feature.title[locale]} isSelected={enabled && parentEnabled} isDisabled={!platformAvailable || !parentEnabled} onChange={(selected) => update((draft) => { draft.features[feature.key] = selected; if (!selected) for (const child of schema.features.filter((item) => item.parent === feature.key)) draft.features[child.key] = false; })}><Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content></Switch></div></div>;
    })}</section>)}
  </div>;
}
