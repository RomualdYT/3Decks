import { Button, Spinner, toast } from "@heroui/react";
import { useCallback, useEffect, useState } from "react";
import { agentApi, type ExtensionRequest } from "../api/client";
import type { ExtensionCatalog, Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { Decky } from "../components/Decky";
import { ExtensionCard } from "./ExtensionCard";
import { ExtensionApproval } from "./ExtensionApproval";
import type { ExtensionConfirmation } from "./requests";

export function ExtensionsView({
  locale,
  onChanged,
}: {
  locale: Locale;
  onChanged: () => Promise<void>;
}) {
  const [catalog, setCatalog] = useState<ExtensionCatalog | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] =
    useState<ExtensionConfirmation | null>(null);
  const fr = locale === "fr";
  const refresh = useCallback(async () => {
    try {
      setCatalog(await agentApi.extensions());
      setError("");
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [onChanged]);
  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, [refresh]);
  const operate = async (request: ExtensionRequest) => {
    setBusy(true);
    try {
      const result = await agentApi.manageExtension(request);
      if (!result.cancelled) {
        toast.success(fr ? "Extension mise à jour" : "Extension updated");
        setConfirmation(null);
      }
      await refresh();
    } catch (reason) {
      toast.danger(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="extensions-view">
      <div className="extensions-heading">
        <div>
          <span className="eyebrow">3DECKS · EXTENSION API 1</span>
          <h1>
            {fr
              ? "Votre console, sans limites."
              : "Your console, your possibilities."}
          </h1>
          <p>
            {fr
              ? "Ajoutez les intégrations de la communauté ou créez les vôtres. Leurs actions et écrans s’intègrent naturellement à votre console."
              : "Add community integrations or build your own. Their actions and screens become part of your console."}
          </p>
        </div>
        <div className="extension-toolbar">
          <Button
            variant="outline"
            isDisabled={busy}
            onPress={() => void operate({ operation: "rescan" })}
          >
            <DeckIcon name="refresh" size={17} />
            {fr ? "Actualiser" : "Refresh"}
          </Button>
          <Button
            variant="primary"
            isDisabled={busy}
            onPress={() => void operate({ operation: "install" })}
          >
            <DeckIcon name="plus" size={17} />
            {fr ? "Importer une extension" : "Import extension"}
          </Button>
        </div>
      </div>
      <div className="extension-trust-note">
        <DeckIcon name="lock" />
        <p>
          {fr
            ? "Un paquet importé reste désactivé. Une extension activée exécute du code avec les droits de votre compte : installez uniquement des auteurs de confiance. Les accès déclarés sont informatifs, pas une restriction système."
            : "Imported packages stay disabled. Enabled extensions run code with your account’s permissions: only trust known authors. Declared access is informational, not an OS sandbox."}
        </p>
      </div>
      {error && (
        <div role="alert" className="extension-error">
          {error}
        </div>
      )}
      {catalog?.errors.map((message) => (
        <div role="alert" className="extension-error" key={message}>
          {message}
        </div>
      ))}
      {!catalog && !error && (
        <Spinner
          aria-label={fr ? "Chargement des extensions" : "Loading extensions"}
        />
      )}
      {catalog && !catalog.extensions.length && (
        <section className="extension-empty">
          <Decky mood="idle" size={80} />
          <h2>
            {fr
              ? "La prochaine intégration est la vôtre."
              : "Make room for your next integration."}
          </h2>
          <p>
            {fr
              ? "Importez un fichier .3deckext ou .zip. Vous pourrez lire sa description, renseigner ses réglages, puis choisir de lui faire confiance."
              : "Import a .3deckext or .zip file. Review its description, configure it, then decide whether to trust it."}
          </p>
          <div className="extension-steps">
            <span>1 · {fr ? "Importer" : "Import"}</span>
            <span>2 · {fr ? "Configurer" : "Configure"}</span>
            <span>3 · {fr ? "Activer" : "Enable"}</span>
          </div>
        </section>
      )}
      <div className="extension-grid">
        {catalog?.extensions.map((item) => (
          <ExtensionCard
            key={`${item.manifest.id}:${item.digest}`}
            item={item}
            locale={locale}
            busy={busy}
            onOperate={operate}
            onConfirm={(operation) => setConfirmation({ item, operation })}
          />
        ))}
      </div>
      <section className="extension-developer">
        <div>
          <DeckIcon name="terminal" size={26} />
          <h2>
            {fr ? "Créez quelque chose d’unique" : "Build something unique"}
          </h2>
          <p>
            {fr
              ? "Un manifeste, un programme et le protocole JSON. Python dispose d’un SDK ; les autres langages peuvent parler directement au protocole stdio."
              : "A manifest, a program and JSON. Python has a SDK; other languages can implement the stdio protocol directly."}
          </p>
        </div>
        <div>
          <code>
            python -m deck3ds.extensions init my-extension --id
            com.example.custom
          </code>
          <small>
            {fr
              ? "Depuis le dossier agent. Guide complet : docs/EXTENSIONS.md · Exemple : examples/extensions/focus-timer"
              : "From the agent directory. Full guide: docs/EXTENSIONS.md · Example: examples/extensions/focus-timer"}
          </small>
        </div>
      </section>
      {catalog?.directory && (
        <p className="extension-directory">
          {fr ? "Répertoire local" : "Local directory"}{" "}
          <code>{catalog.directory}</code>
        </p>
      )}
      <ExtensionApproval
        confirmation={confirmation}
        locale={locale}
        busy={busy}
        onClose={() => setConfirmation(null)}
        operate={operate}
      />
    </main>
  );
}
