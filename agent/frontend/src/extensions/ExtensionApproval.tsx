import { Button, Modal } from "@heroui/react";
import type { Locale } from "../app/types";
import type { ExtensionRequest } from "../api/client";
import { approvalRequest, type ExtensionConfirmation } from "./requests";
import { DeckIcon } from "../components/DeckIcon";
import { localized } from "../utils/config";

export function ExtensionApproval({
  confirmation,
  locale,
  busy,
  onClose,
  operate,
}: {
  confirmation: ExtensionConfirmation | null;
  locale: Locale;
  busy: boolean;
  onClose: () => void;
  operate: (request: ExtensionRequest) => Promise<void>;
}) {
  const fr = locale === "fr";
  return (
    <Modal
      isOpen={confirmation !== null}
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Modal.Backdrop>
        <Modal.Container size="md">
          <Modal.Dialog className="connection-modal">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon>
                <DeckIcon
                  name={confirmation?.operation === "remove" ? "trash" : "lock"}
                />
              </Modal.Icon>
              <Modal.Heading>
                {confirmation?.operation === "remove"
                  ? fr
                    ? "Retirer cette extension ?"
                    : "Remove this extension?"
                  : fr
                    ? "Faire confiance à cette extension ?"
                    : "Trust this extension?"}
              </Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              {confirmation && (
                <>
                  <h3>{localized(confirmation.item.manifest.name, locale)}</h3>
                  <p>
                    {confirmation.operation === "remove"
                      ? fr
                        ? "Le paquet sera déplacé dans la corbeille locale des extensions. Ses réglages et données seront conservés ; ses boutons deviendront indisponibles."
                        : "The package moves to the local extension trash. Settings and data are kept; its buttons become unavailable."
                      : fr
                        ? "Ce programme pourra lire vos fichiers, utiliser le réseau et agir sur cet ordinateur. Son processus séparé limite l’impact des pannes, mais ne restreint pas ses droits ni sa consommation de ressources. Aucun code tiers ne s’exécute sur la 3DS."
                        : "This program can read files, use the network and act on this computer. A separate process contains ordinary failures but does not restrict its rights or resource usage. No third-party code runs on the 3DS."}
                  </p>
                  <p>
                    {fr ? "Auteur" : "Author"} :{" "}
                    {confirmation.item.manifest.author} · v
                    {confirmation.item.manifest.version}
                  </p>
                  <code className="extension-fingerprint">
                    SHA-256
                    <br />
                    {confirmation.item.digest}
                  </code>
                </>
              )}
            </Modal.Body>
            <Modal.Footer>
              <Button
                variant="ghost"
                isDisabled={busy}
                onPress={() => onClose()}
              >
                {fr ? "Annuler" : "Cancel"}
              </Button>
              <Button
                variant={
                  confirmation?.operation === "remove" ? "danger" : "primary"
                }
                isDisabled={busy}
                onPress={() => {
                  if (confirmation)
                    void operate(approvalRequest(confirmation));
                }}
              >
                {busy
                  ? fr
                    ? "En cours…"
                    : "Working…"
                  : confirmation?.operation === "remove"
                    ? fr
                      ? "Retirer"
                      : "Remove"
                    : fr
                      ? "Faire confiance et activer"
                      : "Trust and enable"}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
