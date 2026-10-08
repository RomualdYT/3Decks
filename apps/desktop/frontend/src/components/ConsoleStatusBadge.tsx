import { Button, Modal, toast } from "@heroui/react";
import { useState } from "react";
import type { AgentState, Locale } from "../app/types";
import { ConsoleConnectionIcon } from "./BrandIcons";
import { DeckIcon } from "./DeckIcon";
import { Decky, useDeckyPreference } from "./Decky";
import { formatDeviceName } from "../utils/devices";

interface Props {
  status: AgentState | null;
  locale: Locale;
  onOpenSettings: () => void;
}

export function ConsoleStatusBadge({ status, locale, onOpenSettings }: Props) {
  const { visible } = useDeckyPreference();
  const [open, setOpen] = useState(false);
  const count = status?.clients.length ?? 0;
  const connected = count > 0;
  const address = status?.hints[0] ?? status?.listen ?? "—";
  const fr = locale === "fr";
  return (
    <Modal isOpen={open} onOpenChange={setOpen}>
      <Button aria-label={fr ? "Voir l’état de la connexion" : "View connection status"} className={`console-status ${connected ? "connected" : ""}`} variant="ghost" size="sm">
        <ConsoleConnectionIcon connected={connected} />
        <span>{connected ? (fr ? `${count} console${count > 1 ? "s" : ""} connectée${count > 1 ? "s" : ""}` : `${count} console${count > 1 ? "s" : ""} connected`) : (fr ? "Aucune console" : "No console")}</span>
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
              {visible && <div className="decky-connection"><Decky mood={connected ? "wave" : "search"} size={80} /><div>
                <strong>{connected ? (fr ? "On est prêts !" : "Ready when you are!") : (fr ? "Faisons les présentations." : "Let’s meet your console.")}</strong>
                <p>{connected ? (fr ? "Decky a retrouvé ta console." : "Decky found your console.") : (fr ? "Decky t’accompagne. Les étapes sont juste en dessous." : "Decky is here to help. Follow the steps below.")}</p>
              </div></div>}
              {connected ? (
                <div className="connected-list">{status?.clients.map((client) => <div key={client.id}><span className="status-pulse" /><div><strong>{formatDeviceName(client.name)}</strong><small>{client.address}</small></div><span className="connected-label">{fr ? "En ligne" : "Online"}</span></div>)}</div>
              ) : (
                <ol className="connection-steps">
                  <li><span>1</span><div><strong>{fr ? "Laissez cet agent ouvert" : "Keep this agent open"}</strong><p>{fr ? "Votre ordinateur et votre console doivent utiliser le même Wi-Fi." : "Your computer and console must use the same Wi-Fi."}</p></div></li>
                  <li><span>2</span><div><strong>{fr ? "Ouvrez 3Decks sur la console" : "Open 3Decks on the console"}</strong><p>{fr ? "Sélectionnez votre ordinateur dans la liste détectée automatiquement." : "Select your computer from the automatically discovered list."}</p></div></li>
                  <li><span>3</span><div><strong>{fr ? "Validez la connexion" : "Confirm the connection"}</strong><p>{fr ? "Si un code est demandé, ouvrez les réglages de connexion ci-dessous pour le retrouver." : "If a code is requested, open connection settings below to find it."}</p></div></li>
                </ol>
              )}
              <div className="connection-address"><div><small>{fr ? "Adresse de l’agent" : "Agent address"}</small><code>{address}</code></div><Button variant="outline" size="sm" onPress={() => { void navigator.clipboard.writeText(address); toast.success(fr ? "Adresse copiée" : "Address copied"); }}><DeckIcon name="copy" size={16} />{fr ? "Copier" : "Copy"}</Button></div>
            </Modal.Body>
            <Modal.Footer><Button variant="ghost" onPress={() => { setOpen(false); onOpenSettings(); }}><DeckIcon name="gear" size={17} />{fr ? "Ouvrir les réglages de connexion" : "Open connection settings"}</Button></Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
