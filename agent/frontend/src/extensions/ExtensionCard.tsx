import { Button, Disclosure } from "@heroui/react";
import { useState } from "react";
import type { InstalledExtension, Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { localized } from "../utils/config";
import { ExtensionField } from "./ExtensionFields";

const STATUS: Record<string, [string, string]> = {
  ready: ["Active", "Ready"],
  disabled: ["Désactivée", "Disabled"],
  untrusted: ["Approbation requise", "Review required"],
  starting: ["Démarrage", "Starting"],
  error: ["À vérifier", "Needs attention"],
  unsupported: ["OS incompatible", "Unsupported OS"],
};
const PERMISSIONS: Record<string, [string, string]> = {
  network: ["Réseau", "Network"],
  filesystem: ["Fichiers", "Files"],
  system: ["Système", "System"],
  notifications: ["Notifications", "Notifications"],
};

export function ExtensionCard({
  item,
  locale,
  busy,
  onOperate,
  onConfirm,
}: {
  item: InstalledExtension;
  locale: Locale;
  busy: boolean;
  onOperate: (
    operation: string,
    values?: Record<string, unknown>,
  ) => Promise<void>;
  onConfirm: (operation: "enable" | "remove") => void;
}) {
  const fr = locale === "fr";
  const manifest = item.manifest;
  const [settings, setSettings] = useState<Record<string, unknown>>(() => ({
    ...Object.fromEntries(
      manifest.settings
        .filter(
          (field) => field.type !== "password" && field.default !== undefined,
        )
        .map((field) => [field.name, field.default]),
    ),
    ...item.settings,
  }));
  return (
    <article className="extension-card">
      <div className="extension-card-heading">
        <span className="extension-mark">
          <DeckIcon name="extension" size={25} />
        </span>
        <div>
          <h2>{localized(manifest.name, locale)}</h2>
          <small>
            {manifest.author} · {manifest.version}
          </small>
        </div>
        <span className={`extension-status ${item.status}`}>
          {STATUS[item.status]?.[fr ? 0 : 1] ?? item.status}
        </span>
      </div>
      <p>{localized(manifest.description, locale)}</p>
      <div className="extension-tags">
        {manifest.platforms.map((platform) => (
          <span key={platform}>
            {platform === "darwin"
              ? "macOS"
              : platform === "win32"
                ? "Windows"
                : "Linux"}
          </span>
        ))}
        {manifest.permissions.map((permission) => (
          <span key={permission}>
            <DeckIcon name="lock" size={12} />
            {PERMISSIONS[permission]?.[fr ? 0 : 1] ?? permission}
          </span>
        ))}
      </div>
      <div className="extension-contributions">
        <span>
          <strong>{manifest.actions.length}</strong> actions
        </span>
        <span>
          <strong>{manifest.sources.length}</strong>{" "}
          {fr ? "contenus" : "sources"}
        </span>
        <span>
          <strong>{manifest.dashboards.length}</strong>{" "}
          {fr ? "écrans" : "screens"}
        </span>
      </div>
      {item.error && (
        <div role="alert" className="extension-error">
          {item.error}
        </div>
      )}
      {manifest.settings.length > 0 && (
        <Disclosure className="advanced-disclosure">
          <Disclosure.Heading>
            <Disclosure.Trigger>
              <span>
                <DeckIcon name="sliders" size={16} />
                {fr ? "Configurer l’intégration" : "Configure integration"}
              </span>
              <Disclosure.Indicator />
            </Disclosure.Trigger>
          </Disclosure.Heading>
          <Disclosure.Content>
            <Disclosure.Body>
              <form
                className="extension-settings"
                onSubmit={(event) => {
                  event.preventDefault();
                  void onOperate("configure", { id: manifest.id, settings });
                }}
              >
                {manifest.settings.map((field) => (
                  <ExtensionField
                    key={field.name}
                    field={field}
                    value={settings[field.name]}
                    locale={locale}
                    secretSet={item.secret_fields_set.includes(field.name)}
                    onChange={(value) =>
                      setSettings((current) => ({
                        ...current,
                        [field.name]: value,
                      }))
                    }
                  />
                ))}
                <Button type="submit" variant="outline" isDisabled={busy}>
                  <DeckIcon name="save" size={16} />
                  {fr ? "Appliquer les réglages" : "Apply settings"}
                </Button>
                <small>
                  {fr
                    ? "Prise en compte immédiate. Les secrets existants ne sont jamais renvoyés au navigateur."
                    : "Applied immediately. Existing secrets are never returned to the browser."}
                </small>
              </form>
            </Disclosure.Body>
          </Disclosure.Content>
        </Disclosure>
      )}
      <Disclosure className="advanced-disclosure">
        <Disclosure.Heading>
          <Disclosure.Trigger>
            <span>
              {fr
                ? "Actions et écrans disponibles"
                : "Available actions and screens"}
            </span>
            <Disclosure.Indicator />
          </Disclosure.Trigger>
        </Disclosure.Heading>
        <Disclosure.Content>
          <Disclosure.Body>
            <ul className="extension-catalog-list">
              {[
                ...manifest.actions,
                ...manifest.sources,
                ...manifest.dashboards,
              ].map((contribution, index) => (
                <li key={`${contribution.id}:${index}`}>
                  <strong>{localized(contribution.title, locale)}</strong>
                  <small>{localized(contribution.description, locale)}</small>
                </li>
              ))}
            </ul>
            <p>
              {fr
                ? "Éditeur → Ajouter une action → Extensions. Les contenus et écrans se choisissent dans les réglages de chaque page."
                : "Editor → Add action → Extensions. Select sources and top screens in each page’s settings."}
            </p>
          </Disclosure.Body>
        </Disclosure.Content>
      </Disclosure>
      <footer>
        {item.enabled && item.status !== "untrusted" ? (
          <Button
            variant="outline"
            isDisabled={busy}
            onPress={() => void onOperate("disable", { id: manifest.id })}
          >
            {fr ? "Désactiver" : "Disable"}
          </Button>
        ) : (
          <Button
            variant="primary"
            isDisabled={busy || item.status === "unsupported"}
            onPress={() => onConfirm("enable")}
          >
            {fr ? "Vérifier et activer" : "Review and enable"}
          </Button>
        )}
        {item.enabled && (
          <Button
            variant="ghost"
            isDisabled={busy}
            onPress={() => void onOperate("restart", { id: manifest.id })}
            aria-label={fr ? "Redémarrer l’extension" : "Restart extension"}
          >
            <DeckIcon name="refresh" size={17} />
          </Button>
        )}
        <Button
          variant="ghost"
          isDisabled={busy}
          onPress={() => onConfirm("remove")}
          aria-label={fr ? "Retirer l’extension" : "Remove extension"}
        >
          <DeckIcon name="trash" size={17} />
        </Button>
      </footer>
    </article>
  );
}
