import { Button, Modal, toast } from "@heroui/react";
import type { AgentState, Locale } from "../app/types";
import { ConsoleConnectionIcon } from "./BrandIcons";
import { DeckIcon } from "./DeckIcon";

interface Props {
  status: AgentState | null;
  locale: Locale;
  onOpenSettings: () => void;
}

export function ConsoleStatusBadge({ status, locale, onOpenSettings }: Props) {
  const count = status?.clients.length ?? 0;
  const connected = count > 0;
  const address = status?.hints[0] ?? status?.listen ?? "127.0.0.1:8765";
  const fr = locale === "fr";
  return (
    <Modal>
      <Button aria-label={fr ? "Voir l’état de la connexion" : "View connection status"} className={`console-status ${connected ? "connected" : ""}`} variant="ghost" size="sm">
        <ConsoleConnectionIcon connected={connected} />
        <span>{connected ? (fr ? `${count} console${count > 1 ? "s" : ""} connectée${count > 1 ? "s" : ""}` : `${count} console${count > 1 ? "s" : ""} connected`) : (fr ? "Aucune console" : "No console")}</span>
        <span className="status-pulse" />
      </Button>
      <Modal.Backdrop>
        <Modal.Container size="md">
          <Modal.Dialog className="connection-modal">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon><ConsoleConnectionIcon connected={connected} size={28} /></Modal.Icon>
              <div><Modal.Heading>{connected ? (fr ? "Votre console est connectée" : "Your console is connected") : (fr ? "Connecter votre console" : "Connect your console")}</Modal.Heading><p>{connected ? (fr ? "Les changements enregistrés sont envoyés automatiquement." : "Saved changes are sent automatically.") : (fr ? "Cela ne prend qu’une minute, sans câble USB." : "It only takes a minute, with no USB cable.")}</p></div>
            </Modal.Header>
            <Modal.Body>
              {connected ? (
                <div className="connected-list">{status?.clients.map((client) => <div key={client.id}><span className="status-pulse" /><div><strong>Nintendo 3DS</strong><small>{client.address}</small></div><span className="connected-label">{fr ? "En ligne" : "Online"}</span></div>)}</div>
              ) : (
                <ol className="connection-steps">
                  <li><span>1</span><div><strong>{fr ? "Laissez cet agent ouvert" : "Keep this agent open"}</strong><p>{fr ? "Votre ordinateur et votre console doivent utiliser le même Wi-Fi." : "Your computer and console must use the same Wi-Fi."}</p></div></li>
                  <li><span>2</span><div><strong>{fr ? "Ouvrez 3Decks sur la console" : "Open 3Decks on the console"}</strong><p>{fr ? "Choisissez Réglages, puis saisissez l’adresse ci-dessous." : "Choose Settings, then enter the address below."}</p></div></li>
                  <li><span>3</span><div><strong>{fr ? "Validez la connexion" : "Confirm the connection"}</strong><p>{fr ? "Le badge passera au vert dès que la console sera reconnue." : "This badge turns green as soon as the console is recognized."}</p></div></li>
                </ol>
              )}
              <div className="connection-address"><div><small>{fr ? "Adresse de l’agent" : "Agent address"}</small><code>{address}</code></div><Button variant="outline" size="sm" onPress={() => { void navigator.clipboard.writeText(address); toast.success(fr ? "Adresse copiée" : "Address copied"); }}><DeckIcon name="copy" size={16} />{fr ? "Copier" : "Copy"}</Button></div>
            </Modal.Body>
            <Modal.Footer><Button variant="ghost" onPress={onOpenSettings}><DeckIcon name="gear" size={17} />{fr ? "Ouvrir les réglages de connexion" : "Open connection settings"}</Button></Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
