import { Button, Modal } from "@heroui/react";
import { useState } from "react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";

const COPY = {
  en: {
    trigger: "How to connect",
    title: "Connect OBS Studio",
    intro: "Control scenes and recording from your 3DS. OBS Studio 28 or later includes everything you need.",
    steps: [
      ["Open the server settings", "In OBS, open Tools → WebSocket Server Settings and enable the WebSocket server."],
      ["Copy the connection details", "Keep authentication enabled. Note the server port (4455 by default) and copy its password."],
      ["Connect in 3Decks", "Enable OBS here. Use localhost if OBS runs on this computer, enter the matching port and password, then test the connection and save."],
    ],
    tip: "Keep OBS open while using its controls. If it runs on another computer, use that computer’s local IP address instead of localhost.",
    close: "Got it",
  },
  fr: {
    trigger: "Comment connecter OBS",
    title: "Connecter OBS Studio",
    intro: "Pilotez les scènes et l’enregistrement depuis votre 3DS. OBS Studio 28 ou plus récent inclut tout le nécessaire.",
    steps: [
      ["Ouvrez les réglages du serveur", "Dans OBS, ouvrez Outils → Paramètres du serveur WebSocket et activez le serveur WebSocket."],
      ["Copiez les informations de connexion", "Gardez l’authentification activée. Notez le port du serveur (4455 par défaut) et copiez son mot de passe."],
      ["Connectez OBS dans 3Decks", "Activez OBS ici. Utilisez localhost si OBS tourne sur cet ordinateur, saisissez le même port et le mot de passe, puis testez la connexion et enregistrez."],
    ],
    tip: "Gardez OBS ouvert pendant l’utilisation des commandes. S’il tourne sur un autre ordinateur, utilisez son adresse IP locale à la place de localhost.",
    close: "Compris",
  },
};

export function ObsSetupHelp({ locale }: { locale: Locale }) {
  const [open, setOpen] = useState(false);
  const copy = COPY[locale];
  return (
    <Modal isOpen={open} onOpenChange={setOpen}>
      <Button variant="outline" size="sm" onPress={() => setOpen(true)}>
        <DeckIcon name="info" size={16} />{copy.trigger}
      </Button>
      <Modal.Backdrop>
        <Modal.Container size="md">
          <Modal.Dialog className="obs-setup-modal">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon><DeckIcon name="video" size={24} /></Modal.Icon>
              <div><Modal.Heading>{copy.title}</Modal.Heading><p>{copy.intro}</p></div>
            </Modal.Header>
            <Modal.Body>
              <ol className="connection-steps">
                {copy.steps.map(([title, detail], index) => (
                  <li key={title}><span>{index + 1}</span><div><strong>{title}</strong><p>{detail}</p></div></li>
                ))}
              </ol>
              <p className="obs-setup-tip">{copy.tip}</p>
            </Modal.Body>
            <Modal.Footer><Button variant="primary" onPress={() => setOpen(false)}>{copy.close}</Button></Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
