import { Button, Switch, toast } from "@heroui/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { AudioOutput, NotificationPermissionStatus } from "../app/desktopControls";
import { agentApi } from "../api/client";
import type { AgentState, DeckConfig, FeatureSpec, Locale, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { DeckIcon } from "../components/DeckIcon";
import { AppleMusicIcon, SpotifyIcon } from "../components/BrandIcons";
import { notificationPermissionError } from "../utils/notificationPermission";

const FEATURE_ICONS: Record<string, string> = {
  notifications: "bell", windows: "app", system_stats: "status",
  audio_output: "volume-up", media_artwork: "square",
};

interface FeatureSettingsProps {
  config: DeckConfig;
  schema: Schema;
  status: AgentState | null;
  locale: Locale;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  update: (recipe: (draft: DeckConfig) => void) => void;
}

export function FeatureSettings({ config, schema, status, locale, t, update }: FeatureSettingsProps) {
  const native = import.meta.env.VITE_DECKS_DESKTOP === "1";
  const [openingPermission, setOpeningPermission] = useState<string | null>(null);
  const [notificationAccess, setNotificationAccess] = useState<NotificationPermissionStatus | null>(null);
  const [requestingNotifications, setRequestingNotifications] = useState(false);
  const openPermission = (permission: string) => {
    setOpeningPermission(permission);
    void agentApi.openPermissionSettings(permission)
      .then(() => toast.success(t("permissionsOpened")))
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setOpeningPermission(null));
  };
  const groups: Array<{ title: string; icon: string; items: FeatureSpec[] }> = [
    { title: locale === "fr" ? "Informations système" : "System information", icon: "monitor", items: schema.features.filter((item) => ["notifications", "windows", "system_stats", "audio_output"].includes(item.key)) },
    { title: locale === "fr" ? "Média et lecteurs" : "Media and players", icon: "music", items: schema.features.filter((item) => ["media", "lyrics_online", "media_artwork", "apple_music", "spotify"].includes(item.key)) },
  ];
  useEffect(() => setNotificationAccess(null), [status?.notifications?.access]);
  const currentNotificationAccess = notificationAccess ?? status?.notifications;
  const requestNotificationAccess = async () => {
    const controls = window.decksDesktopControls;
    if (!controls) return;
    setRequestingNotifications(true);
    try {
      const result = await controls.requestNotificationAccess();
      setNotificationAccess(result.status);
      if (result.access === "Allowed") toast.success(locale === "fr" ? "Accès aux notifications autorisé" : "Notification access allowed");
      else toast.danger(locale === "fr" ? "Accès aux notifications refusé" : "Notification access was denied");
    } catch (error) {
      toast.danger(error instanceof Error ? error.message : String(error));
    } finally {
      setRequestingNotifications(false);
    }
  };
  return (
    <div className="settings-content">
      <div className="settings-title">
        <span><DeckIcon name="sliders" size={24} /></span>
        <div><h1>{t("featureTitle")}</h1><p>{t("featureHelp")}</p></div>
      </div>
      {groups.map((group) => (
        <section className="feature-group" key={group.title}>
          <div className="feature-group-title"><DeckIcon name={group.icon} /><h2>{group.title}</h2></div>
          {group.items.map((feature) => {
            const parentEnabled = !feature.parent || config.features[feature.parent] !== false;
            const enabled = config.features[feature.key] ?? feature.enabled;
            const platformAvailable = !status?.platform || feature.platforms.includes(status.platform);
            const isNotification = feature.key === "notifications";
            const requestNotifications = native && status?.platform === "win32" && isNotification && enabled && currentNotificationAccess?.access === "Unspecified";
            const permissionAction = isNotification && enabled && currentNotificationAccess?.available === false ? currentNotificationAccess.settings_action : undefined;
            const icon = FEATURE_ICONS[feature.key] ?? "music";
            return (
              <div className={`feature-row ${feature.parent ? "nested" : ""} ${!platformAvailable ? "unavailable" : ""}`} key={feature.key}>
                <div className={`feature-symbol ${feature.key === "spotify" || feature.key === "apple_music" ? "brand" : ""}`}>
                  {feature.key === "spotify" ? <SpotifyIcon /> : feature.key === "apple_music" ? <AppleMusicIcon /> : <DeckIcon name={icon} />}
                </div>
                <div className="feature-copy">
                  <h3>{feature.title[locale]}</h3>
                  <p>{feature.description[locale]}</p>
                  {!platformAvailable && <small>{t("unavailablePlatform")}</small>}
                  {isNotification && currentNotificationAccess?.error && <small className="feature-detail-note">{notificationPermissionError(currentNotificationAccess.access, currentNotificationAccess.error, locale)}</small>}
                  {requestNotifications ? (
                    <div className="feature-permission">
                      <span><DeckIcon name="lock" size={14} />{locale === "fr" ? "Windows doit autoriser la lecture des notifications." : "Windows must allow notification access."}</span>
                      <Button size="sm" variant="outline" isDisabled={requestingNotifications} onPress={() => void requestNotificationAccess()}>
                        <DeckIcon name="lock" size={14} />{requestingNotifications ? t("openingPermissions") : locale === "fr" ? "Autoriser" : "Allow"}
                      </Button>
                    </div>
                  ) : permissionAction ? (
                    <div className="feature-permission">
                      <span><DeckIcon name="lock" size={14} />{t("permissionRequired")}</span>
                      <Button size="sm" variant="outline" isDisabled={openingPermission === permissionAction} onPress={() => openPermission(permissionAction)}>
                        <DeckIcon name="link" size={14} />{openingPermission === permissionAction ? t("openingPermissions") : t("openPermissions")}
                      </Button>
                    </div>
                  ) : null}
                  {native && platformAvailable && enabled && feature.key === "audio_output" && (
                    <AudioOutputSettings locale={locale} windows={status?.platform === "win32"} />
                  )}
                </div>
                <div className="feature-state">
                  <span>{enabled && parentEnabled ? t("enabled") : t("disabled")}</span>
                  <Switch aria-label={feature.title[locale]} isSelected={enabled && parentEnabled} isDisabled={!platformAvailable || !parentEnabled} onChange={(selected) => update((draft) => { draft.features[feature.key] = selected; })}>
                    <Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content>
                  </Switch>
                </div>
              </div>
            );
          })}
        </section>
      ))}
    </div>
  );
}

function AudioOutputSettings({ locale, windows }: { locale: Locale; windows: boolean }) {
  const [outputs, setOutputs] = useState<AudioOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(0);
  const fr = locale === "fr";
  const refresh = useCallback(async () => {
    const controls = window.decksDesktopControls;
    if (!controls) return;
    const id = ++requestId.current;
    setLoading(true);
    try {
      const next = await controls.getAudioOutputs();
      if (id === requestId.current) { setOutputs(next); setError(""); }
    } catch (reason) {
      if (id === requestId.current) setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => { requestId.current++; window.removeEventListener("focus", onFocus); };
  }, [refresh]);
  const openSettings = () => {
    setBusy(true);
    void window.decksDesktopControls?.openAudioSettings()
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setBusy(false));
  };
  const select = (id: string) => {
    setBusy(true);
    void window.decksDesktopControls?.selectAudioOutput(id)
      .then(async () => { await refresh(); toast.success(fr ? "Sortie audio modifiée" : "Audio output changed"); })
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setBusy(false));
  };
  return <div className="feature-audio-output">
    <div className="feature-audio-output-heading"><strong>{fr ? "Sorties disponibles" : "Available outputs"}</strong><div className="feature-audio-output-actions"><Button size="sm" variant="ghost" isDisabled={loading} onPress={() => void refresh()} aria-label={fr ? "Actualiser les sorties audio" : "Refresh audio outputs"}><DeckIcon name="refresh" size={14} /></Button>{windows && <Button size="sm" variant="outline" isDisabled={busy} onPress={openSettings}><DeckIcon name="gear" size={14} />{fr ? "Réglages Son" : "Sound settings"}</Button>}</div></div>
    {windows && <p className="feature-detail-note">{fr ? "Windows gère la sortie par défaut. Choisissez-la dans les réglages Son." : "Windows manages the default output. Choose it in Sound settings."}</p>}
    {error ? <small className="feature-audio-output-error" role="alert">{error}</small> : loading ? <small>{fr ? "Recherche des sorties…" : "Looking for outputs…"}</small> : outputs.length === 0 ? <small>{fr ? "Aucune sortie audio disponible." : "No audio outputs are available."}</small> : <div className="feature-audio-output-list">{outputs.map((output) => <div className="feature-audio-output-row" key={output.id}><span><DeckIcon name={output.is_default ? "volume-up" : "volume-down"} size={15} /><span>{output.name}</span></span>{output.is_default ? <small>{fr ? "Par défaut" : "Default"}</small> : windows ? null : <Button size="sm" variant="ghost" isDisabled={busy} onPress={() => select(output.id)}>{fr ? "Utiliser" : "Use"}</Button>}</div>)}</div>}
  </div>;
}
