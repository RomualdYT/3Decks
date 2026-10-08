import { invoke } from "@tauri-apps/api/core";
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import type { AgentState, DeckConfig, Locale, Schema } from "../../frontend/src/app/types";
import { DeckIcon } from "../../frontend/src/components/DeckIcon";
import { Decky, DeckyLogo } from "../../frontend/src/components/Decky";
import { initialLocale, saveLocale } from "../../frontend/src/i18n/copy";
import { notificationPermissionError } from "../../frontend/src/utils/notificationPermission";
import { ConsoleConnectionPreview } from "./ConsoleConnectionPreview";
const PageTemplatePreview = lazy(() => import("../../frontend/src/editor/PageTemplatePreview").then((module) => ({ default: module.PageTemplatePreview })));
const StarterPagePreferences = lazy(() => import("./StarterPagePreferences").then((module) => ({ default: module.StarterPagePreferences })));
import { pageFromTemplate, suggestedFavorites } from "../../frontend/src/editor/pageTemplates";
import { ConsoleFeaturePreview } from "./ConsoleFeaturePreview";
import { agentApi } from "../tauri-api";
import { WindowControls } from "../../frontend/src/components/WindowControls";
import type { OnboardingProgress } from "../DesktopRoot";

type FeatureKey = "lyrics_online" | "media" | "windows" | "system_stats" | "notifications" | "media_artwork";
type PermissionStatus = {
  platform: string;
  local_network: boolean;
  accessibility: boolean;
  notifications: { access?: string; available?: boolean; enabled?: boolean; error?: string };
  automation: string;
};

const featureRows: { key: FeatureKey; icon: string; fr: string; en: string; descriptionFr: string; descriptionEn: string }[] = [
  { key: "media", icon: "play", fr: "Contrôles multimédias", en: "Media controls", descriptionFr: "Lecture et volume de votre musique.", descriptionEn: "Playback and volume for your music." },
  { key: "lyrics_online", icon: "music", fr: "Paroles synchronisées", en: "Synced lyrics", descriptionFr: "Paroles synchronisées. Envoie le titre, l’artiste, l’album et la durée à LRCLIB pour les rechercher.", descriptionEn: "Synced lyrics. Sends the title, artist, album and duration to LRCLIB to find them." },
  { key: "windows", icon: "app", fr: "Applications ouvertes", en: "Open applications", descriptionFr: "Affichez et sélectionnez vos fenêtres.", descriptionEn: "View and select your windows." },
  { key: "system_stats", icon: "status", fr: "Statistiques système", en: "System statistics", descriptionFr: "CPU, mémoire et stockage sur la console.", descriptionEn: "CPU, memory and storage on the console." },
  { key: "notifications", icon: "bell", fr: "Notifications", en: "Notifications", descriptionFr: "Consultez les alertes récentes du système.", descriptionEn: "See recent system alerts." },
  { key: "media_artwork", icon: "artwork", fr: "Pochettes d’album", en: "Album artwork", descriptionFr: "Affichez la pochette du morceau en cours.", descriptionEn: "Show artwork for the current track." },
];

export function Onboarding({ initialStep, onComplete }: { initialStep: number; onComplete: (value: OnboardingProgress) => void }) {
  const [step, setStep] = useState(Math.max(0, Math.min(4, initialStep)));
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const setLocale = (next: Locale) => {
    setLocaleState(next);
    saveLocale(next);
  };
  const [config, setConfig] = useState<DeckConfig | null>(null);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [agent, setAgent] = useState<AgentState | null>(null);
  const [permissions, setPermissions] = useState<PermissionStatus | null>(null);
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [apps, setApps] = useState<string[]>([]);
  const [favorites, setFavorites] = useState<string[]>([]);
  const [musicView, setMusicView] = useState("media");
  const [previewPage, setPreviewPage] = useState<"home" | "music">("home");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const fr = locale === "fr";
  const copy = (french: string, english: string) => fr ? french : english;

  const refresh = useCallback(() => {
    void Promise.all([agentApi.state(), invoke<PermissionStatus>("get_permission_status")])
      .then(([state, permissionState]) => { setAgent(state); setPermissions(permissionState); })
      .catch((reason) => setError(String(reason)));
  }, []);
  useEffect(() => {
    void Promise.all([agentApi.config(), agentApi.schema(), agentApi.apps().catch(() => ({ apps: [] as string[] }))])
      .then(([document, catalog, installed]) => {
        setConfig(document.config);
        setFeatures({ ...document.config.features });
        setSchema(catalog);
        setApps(installed.apps);
        setFavorites(suggestedFavorites(installed.apps));
        const music = document.config.pages.find((page) => page.id === "sound");
        if (["media", "lyrics", "frame"].includes(music?.dashboard ?? "")) setMusicView(music!.dashboard!);
      })
      .catch((reason) => setError(String(reason)));
    refresh();
  }, [refresh]);
  useEffect(() => {
    if (step < 3) return;
    const timer = window.setInterval(refresh, 2000);
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", onFocus); };
  }, [refresh, step]);
  useEffect(() => { document.title = `3Decks — ${copy("Configuration initiale", "Setup")}`; document.documentElement.lang = locale; }, [locale, fr]);

  const chosenMusicView = (musicView === "lyrics" && !features.lyrics_online) || (musicView === "frame" && !features.media_artwork) ? "media" : musicView;
  const saveStep = async (next: number, completed = false) => {
    const value = await invoke<OnboardingProgress>("save_onboarding", { step: next, completed });
    if (completed) onComplete(value);
    else setStep(value.step);
  };
  const next = async () => {
    if (busy) return;
    setBusy(true); setError("");
    try {
      if (step === 1) {
        const latest = (await agentApi.config()).config;
        const updated = { ...latest, features: { ...latest.features } };
        for (const row of featureRows) updated.features[row.key] = features[row.key] === true;
        if (!updated.features.media) {
          updated.features.media_artwork = false;
          updated.features.lyrics_online = false;
        }
        const saved = await agentApi.save(updated);
        setConfig(saved.config);
      }
      if (step === 2) {
        const latest = (await agentApi.config()).config;
        const updated = { ...latest };
        if (!schema) throw new Error(copy("Le catalogue est encore en cours de chargement.", "The catalog is still loading."));
        updated.pages = latest.pages.map((page) => {
          if (page.id === "main" && apps.length > 0) {
            const selected = pageFromTemplate(latest, schema, "home", { apps, favorites, platform: agent?.platform });
            return { ...page, buttons: page.buttons.map((button) => selected.buttons.find((candidate) => candidate.slot === button.slot && [1, 2].includes(button.slot)) ?? button) };
          }
          if (page.id === "sound") return { ...page, dashboard: chosenMusicView, ...(chosenMusicView === "lyrics" ? { lyrics_lines: 3 } : {}) };
          return page;
        });
        const saved = await agentApi.save(updated);
        setConfig(saved.config);
      }
      if (step === 4) {
        if (features.notifications && permissions?.notifications.available && schema) {
          const latest = (await agentApi.config()).config;
          if (!latest.pages.some((page) => page.dashboard === "notifications") && latest.pages.length < schema.limits.pages) {
            await agentApi.save({ ...latest, pages: [...latest.pages, pageFromTemplate(latest, schema, "notifications", { apps, platform: agent?.platform })] });
          }
        }
        await saveStep(4, true);
      }
      else await saveStep(step + 1);
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  };
  const back = async () => {
    if (busy || step === 0) return;
    setBusy(true); setError("");
    try { await saveStep(step - 1); }
    catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  };
  const skip = async () => {
    if (busy) return;
    setBusy(true); setError("");
    try { await saveStep(step, true); }
    catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  };
  const openPermission = async (permission: string) => {
    setError("");
    try { await agentApi.openPermissionSettings(permission); }
    catch (reason) { setError(String(reason)); }
  };
  const requestWindowsNotifications = async () => {
    setError("");
    try {
      await invoke("request_notification_access");
      refresh();
    } catch (reason) { setError(String(reason)); }
  };
  const rotateCode = async () => {
    setError("");
    try {
      const pairing = await agentApi.rotatePairing();
      setAgent((previous) => previous ? { ...previous, pairing } : previous);
    } catch (reason) { setError(String(reason)); }
  };
  const platform = permissions?.platform || agent?.platform || "unknown";
  const isMac = platform === "darwin";
  const isWindows = platform === "win32";
  const available = (key: FeatureKey) => {
    const feature = schema?.features.find((item) => item.key === key);
    if (!feature) return false;
    if (key === "notifications") return platform === "darwin" || (platform === "win32" && permissions?.notifications.access !== "Unavailable");
    return feature.available && (!["media_artwork", "lyrics_online"].includes(key) || features.media === true);
  };
  const code = agent?.pairing.code || "······";
  const connected = (agent?.clients.length ?? 0) > 0;

  return <div className="onboarding-shell">
    <header className="onboarding-header" data-tauri-drag-region="deep">
      <div className="onboarding-brand"><DeckyLogo /><strong>3Decks</strong></div>
      <div className="onboarding-header-end">
        <div className="onboarding-progress"><span>{copy("Étape", "Step")} {step + 1} {copy("sur", "of")} 5</span><div>{[0, 1, 2, 3, 4].map((index) => <i key={index} className={index <= step ? "is-active" : ""} />)}</div></div>
        <div className="onboarding-language"><button type="button" className={fr ? "is-active" : ""} onClick={() => setLocale("fr")}>FR</button><button type="button" className={!fr ? "is-active" : ""} onClick={() => setLocale("en")}>EN</button></div>
        <WindowControls locale={locale} />
      </div>
    </header>

    <main className={`onboarding-main onboarding-step-${step}`}>
      {step === 0 && <div className="onboarding-columns">
        <div className="onboarding-copy onboarding-welcome">
          <h1>{copy("Bienvenue dans 3Decks", "Welcome to 3Decks")}</h1>
          <p className="onboarding-lead">{copy("Transformez votre console en surface de contrôle pour votre ordinateur.", "Turn your console into a control surface for your computer.")}</p>
          <ol className="onboarding-timeline">
            <li><span>1</span><div><strong>{copy("Choisir les fonctions", "Choose your features")}</strong><p>{copy("Sélectionnez les informations et contrôles utiles.", "Select the information and controls you need.")}</p></div></li>
            <li><span>2</span><div><strong>{copy("Personnaliser les pages", "Personalize your pages")}</strong><p>{copy("Choisissez vos favoris et l’affichage de votre musique.", "Choose your favorites and music display.")}</p></div></li>
            <li><span>3</span><div><strong>{copy("Autoriser les accès", "Allow access")}</strong><p>{copy("Accordez uniquement les autorisations nécessaires.", "Grant only the permissions your choices need.")}</p></div></li>
            <li><span>4</span><div><strong>{copy("Connecter la console", "Connect your console")}</strong><p>{copy("Reliez votre Nintendo 3DS ou 2DS à cet ordinateur.", "Link your Nintendo 3DS or 2DS to this computer.")}</p></div></li>
          </ol>
        </div>
        <div className="onboarding-visual onboarding-decky-panel"><div className="onboarding-decky-glow" /><Decky mood="wave" size={310} /></div>
      </div>}

      {step === 1 && <div className="onboarding-columns">
        <div className="onboarding-copy">
          <div className="onboarding-title"><span>2</span><div><h1>{copy("Choisissez vos fonctions", "Choose your features")}</h1><p className="onboarding-lead">{copy("Sélectionnez les informations et contrôles à afficher sur votre console.", "Choose what your console displays and controls.")}</p></div></div>
          <div className="onboarding-feature-list">{featureRows.map((row) => {
            const enabled = features[row.key] === true && (!["media_artwork", "lyrics_online"].includes(row.key) || features.media === true);
            const supported = available(row.key);
            return <button type="button" role="switch" aria-checked={enabled} aria-label={fr ? row.fr : row.en} disabled={!supported || !config || busy} className={`onboarding-feature${enabled ? " is-selected" : ""}`} key={row.key} onClick={() => setFeatures((previous) => ({ ...previous, [row.key]: !enabled, ...(row.key === "media" && enabled ? { media_artwork: false, lyrics_online: false } : {}) }))}>
              <span className="onboarding-feature-icon"><DeckIcon name={row.icon} size={22} /></span>
              <span className="onboarding-feature-text"><strong>{fr ? row.fr : row.en}</strong><small>{supported ? (fr ? row.descriptionFr : row.descriptionEn) : copy("Indisponible sur cette plateforme", "Unavailable on this platform")}</small></span>
              <span className="onboarding-switch" aria-hidden="true"><i /></span>
            </button>;
          })}</div>

        </div>
        <div className="onboarding-visual onboarding-preview-panel"><ConsoleFeaturePreview features={featureRows.filter((row) => features[row.key] && available(row.key))} locale={locale} /><p>{copy("Vous pourrez modifier ces choix plus tard.", "You can change these choices later.")}</p></div>
      </div>}

      {step === 2 && <div className="onboarding-columns">
        <div className="onboarding-copy">
          <div className="onboarding-title"><span>3</span><div><h1>{copy("Personnalisez vos pages", "Make your pages yours")}</h1><p className="onboarding-lead">{copy("Choisissez vos favoris et l’affichage de Musique. Vous pourrez les modifier dans l’éditeur.", "Choose your favorites and Music display. You can change them later in the editor.")}</p></div></div>
          <Suspense fallback={null}><StarterPagePreferences locale={locale} apps={apps} favorites={favorites} onFavorite={(slot, app) => { setPreviewPage("home"); setFavorites((previous) => { const next = [...previous]; next[slot] = app; return next; }); }} musicView={chosenMusicView} onMusicView={(view) => { setMusicView(view); setPreviewPage("music"); }} media={features.media === true} lyrics={features.lyrics_online === true} artwork={features.media_artwork === true} /></Suspense>
        </div>
        <div className="onboarding-visual onboarding-pages-panel">
          <div className="onboarding-preview-tabs" role="group" aria-label={copy("Page à prévisualiser", "Page to preview")}>
            <button type="button" aria-pressed={previewPage === "home"} onClick={() => setPreviewPage("home")}>{copy("Accueil", "Home")}</button>
            <button type="button" aria-pressed={previewPage === "music"} onClick={() => setPreviewPage("music")}>{copy("Musique", "Music")}</button>
          </div>
          {config && schema && <Suspense fallback={null}><PageTemplatePreview config={config} page={pageFromTemplate(config, schema, previewPage, { apps, favorites, variant: chosenMusicView, platform: agent?.platform })} status={agent} locale={locale} /></Suspense>}
        </div>
      </div>}

      {step === 3 && <div className="onboarding-columns">
        <div className="onboarding-copy">
          <div className="onboarding-title"><span>4</span><div><h1>{isMac ? copy("Autorisations macOS", "macOS permissions") : isWindows ? copy("Accès Windows", "Windows access") : copy("Autorisations système", "System permissions")}</h1><p className="onboarding-lead">{copy("3Decks demande seulement les accès nécessaires aux fonctions choisies.", "3Decks only asks for access needed by your selected features.")}</p></div></div>
          <div className="onboarding-permission-list">
            <PermissionRow icon="wifi" title={copy("Réseau local", "Local network")} description={copy("Connexion à la console sur votre Wi‑Fi.", "Connect to your console over Wi‑Fi.")} status={permissions?.local_network ? copy("Serveur actif", "Server active") : copy("En attente", "Waiting")} tone={permissions?.local_network ? "good" : "quiet"} />
            {isMac && <>
              <PermissionRow icon="keyboard" title={copy("Accessibilité", "Accessibility")} description={copy("Raccourcis et sélection de fenêtres.", "Shortcuts and window selection.")} status={permissions?.accessibility ? copy("Autorisé", "Allowed") : copy("À autoriser", "Needs access")} tone={permissions?.accessibility ? "good" : "warning"} action={!permissions?.accessibility ? copy("Ouvrir les réglages", "Open settings") : undefined} onAction={() => void openPermission("accessibility")} />
              <PermissionRow icon="gear" title={copy("Automatisation", "Automation")} description={copy("Contrôle de Spotify et Apple Music.", "Control Spotify and Apple Music.")} status={copy("Au premier usage", "On first use")} tone="quiet" />
              {features.notifications && <PermissionRow icon="lock" title={copy("Accès complet au disque", "Full Disk Access")} description={copy("Lecture des notifications macOS.", "Read macOS notifications.")} status={permissions?.notifications.available ? copy("Disponible", "Available") : copy("À vérifier", "Check access")} tone={permissions?.notifications.available ? "good" : "warning"} action={copy("Ouvrir les réglages", "Open settings")} onAction={() => void openPermission("notifications")} />}
            </>}
            {isWindows && features.notifications && <PermissionRow icon="bell" title={copy("Accès aux notifications", "Notification access")} description={notificationPermissionError(permissions?.notifications.access, permissions?.notifications.error, locale) || copy("Autorisez 3Decks à lire les notifications conservées dans le centre Windows.", "Allow 3Decks to read notifications retained in Windows Notification Center.")} status={permissions?.notifications.access === "Allowed" ? copy("Autorisé", "Allowed") : permissions?.notifications.access === "Denied" ? copy("Refusé", "Denied") : permissions?.notifications.access === "Unavailable" ? copy("Nécessite un paquet compatible", "Requires a compatible package") : copy("À autoriser", "Needs access")} tone={permissions?.notifications.access === "Allowed" ? "good" : permissions?.notifications.access === "Unavailable" ? "quiet" : "warning"} action={permissions?.notifications.access === "Unspecified" ? copy("Autoriser", "Allow") : permissions?.notifications.access === "Denied" ? copy("Ouvrir les réglages", "Open settings") : undefined} onAction={permissions?.notifications.access === "Denied" ? () => void openPermission("notifications") : () => void requestWindowsNotifications()} />}
            {isWindows && <PermissionRow icon="keyboard" title={copy("Contrôles Windows", "Windows controls")} description={copy("Audio, médias et raccourcis utilisent les API Windows. Certaines applications peuvent limiter la focalisation ou les touches simulées.", "Audio, media and shortcuts use Windows APIs. Some applications may limit focus or simulated keys.")} status={copy("Aucun accès à accorder", "No extra permission")} tone="quiet" />}
          </div>
        </div>
        <div className="onboarding-visual onboarding-permission-panel"><div className="onboarding-settings-symbol"><DeckIcon name="gear" size={94} /><span><DeckIcon name="check" size={38} /></span></div><strong>{isMac ? copy("Un redémarrage peut être nécessaire.", "A restart may be required.") : copy("Vous gardez le contrôle.", "You stay in control.")}</strong><p>{isMac ? copy("macOS peut demander de quitter puis rouvrir 3Decks. Votre progression sera conservée.", "macOS may ask you to quit and reopen 3Decks. Your progress will be saved.") : isWindows ? copy("Windows peut demander l’accès au réseau local. Si vous changez une autorisation, revenez ici pour vérifier son état.", "Windows may ask for local network access. If you change a permission, return here to check its status.") : copy("Vous pourrez revoir les fonctions et les accès dans les réglages.", "You can review features and access in Settings.")}</p></div>
      </div>}

      {step === 4 && <div className="onboarding-columns">
        <div className="onboarding-copy">
          <div className="onboarding-title"><span>5</span><div><h1>{copy("Connectez votre console", "Connect your console")}</h1><p className="onboarding-lead">{copy("Votre Nintendo 3DS ou 2DS doit être sur le même réseau Wi‑Fi que cet ordinateur.", "Your Nintendo 3DS or 2DS must be on the same Wi‑Fi network as this computer.")}</p></div></div>
          <ol className="onboarding-pair-steps"><li><DeckIcon name="wifi" /><span>{copy("Connectez la console au même réseau Wi‑Fi.", "Connect the console to the same Wi‑Fi network.")}</span></li><li><DeckIcon name="power" /><span>{copy("Ouvrez 3Decks sur la console.", "Open 3Decks on your console.")}</span></li><li><DeckIcon name="list" /><span>{copy("Sélectionnez cet ordinateur dans la liste.", "Select this computer from the list.")}</span></li><li><DeckIcon name="lock" /><span>{copy("Entrez le code d’appairage ci-dessous.", "Enter the pairing code below.")}</span></li></ol>
          <div className="onboarding-code-card"><div><small>{copy("Code d’appairage", "Pairing code")}</small><strong aria-live="polite">{code.slice(0, 3)} {code.slice(3, 6)}</strong></div><button type="button" onClick={() => void rotateCode()}><DeckIcon name="refresh" size={16} />{copy("Nouveau code", "New code")}</button></div>
          <div className={`onboarding-connection${connected ? " is-connected" : ""}`}><i /><span>{connected ? copy("Console connectée", "Console connected") : copy("En attente d’une console", "Waiting for a console")}</span></div>
        </div>
        <div className="onboarding-visual onboarding-connection-panel"><ConsoleConnectionPreview connected={connected} locale={locale} /><strong>{connected ? copy("Votre console est prête.", "Your console is ready.") : copy("En attente de la connexion…", "Waiting for connection…")}</strong><p>{copy("Vous pouvez ouvrir l’éditeur maintenant et connecter la console plus tard.", "You can open the editor now and connect the console later.")}</p></div>
      </div>}
    </main>
    {error && <div className="onboarding-error" role="alert"><DeckIcon name="info" size={18} />{error}</div>}
    <footer className="onboarding-footer"><button type="button" className="onboarding-secondary" disabled={busy} onClick={step === 0 ? () => void skip() : () => void back()}>{step === 0 ? copy("Plus tard", "Later") : copy("Retour", "Back")}</button>{step === 4 && <button type="button" className="onboarding-later" disabled={busy} onClick={() => void skip()}>{copy("Je connecterai ma console plus tard", "I'll connect my console later")}</button>}<button type="button" className="onboarding-primary" disabled={busy || ([1, 2].includes(step) && (!config || !schema))} onClick={() => void next()}>{busy ? copy("Un instant…", "One moment…") : step === 0 ? copy("Commencer", "Get started") : step === 4 ? copy("Ouvrir l’éditeur", "Open editor") : copy("Continuer", "Continue")}<DeckIcon name="next" size={19} /></button></footer>
  </div>;
}

function PermissionRow({ icon, title, description, status, tone, action, onAction }: { icon: string; title: string; description: string; status: string; tone: "good" | "warning" | "quiet"; action?: string; onAction?: () => void }) {
  return <div className="onboarding-permission"><span className="onboarding-permission-icon"><DeckIcon name={icon} size={25} /></span><div><strong>{title}</strong><small>{description}</small></div><div className="onboarding-permission-actions"><span className={`onboarding-permission-status is-${tone}`}>{status}</span>{action && <button type="button" onClick={onAction}>{action}</button>}</div></div>;
}
