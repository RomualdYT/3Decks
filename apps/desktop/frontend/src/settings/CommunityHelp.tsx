import { Button, Modal, toast } from "@heroui/react";
import { useState } from "react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { COMMUNITY_URL } from "../utils/community";

export function CommunityHelp({ locale }: { locale: Locale }) {
  const [open, setOpen] = useState(false);
  const fr = locale === "fr";
  const join = () => {
    if (window.decksDesktopControls) {
      void window.decksDesktopControls.openCommunity().catch(() => {
        toast.danger(fr ? "Impossible d’ouvrir le lien. Vous pouvez le copier ci-dessous." : "Could not open the link. You can copy it below.");
      });
    } else {
      window.open(COMMUNITY_URL, "_blank", "noopener,noreferrer");
    }
  };
  const copy = () => {
    void navigator.clipboard.writeText(COMMUNITY_URL)
      .then(() => toast.success(fr ? "Lien copié" : "Link copied"))
      .catch(() => toast.danger(fr ? "Copiez le lien affiché sous le QR code." : "Copy the link shown below the QR code."));
  };
  return (
    <Modal isOpen={open} onOpenChange={setOpen}>
      <Button className="community-help-button" variant="ghost" onPress={() => setOpen(true)}>
        <DeckIcon name="chat" size={18} />{fr ? "Communauté & aide" : "Community & help"}
      </Button>
      <Modal.Backdrop>
        <Modal.Container size="md">
          <Modal.Dialog className="community-modal">
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Icon><DeckIcon name="chat" size={24} /></Modal.Icon>
              <Modal.Heading>{fr ? "Rejoignez la communauté 3Decks" : "Join the 3Decks community"}</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <p>{fr
                ? "Besoin d’aide, un bug à signaler ou une idée à partager ? Retrouvez-nous sur Discord pour échanger, suivre les nouveautés et découvrir ou partager des homebrews."
                : "Need help, found a bug, or have an idea to share? Join us on Discord to chat, follow updates, and discover or share homebrew projects."}</p>
              <div className="community-qr">
                <img src="/community-qr.svg" width={185} height={185} alt={fr ? "QR code de l’invitation Discord" : "Discord invitation QR code"} />
                <span>{fr ? "Scannez avec votre téléphone" : "Scan with your phone"}</span>
                <a href={COMMUNITY_URL} onClick={(event) => { event.preventDefault(); join(); }}>{COMMUNITY_URL.replace("https://", "")}</a>
              </div>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="ghost" onPress={copy}><DeckIcon name="copy" size={16} />{fr ? "Copier le lien" : "Copy link"}</Button>
              <Button variant="primary" onPress={join}><DeckIcon name="chat" size={16} />{fr ? "Rejoindre sur Discord" : "Join on Discord"}</Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
