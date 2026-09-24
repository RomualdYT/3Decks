import { Button, Modal } from "@heroui/react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { PAGE_TEMPLATES, type PageTemplateId } from "./pageTemplates";

interface Props { open: boolean; locale: Locale; onChoose: (id: PageTemplateId) => void; onClose: () => void }

export function PageTemplateGallery({ open, locale, onChoose, onClose }: Props) {
  const fr = locale === "fr";
  return <Modal isOpen={open} onOpenChange={(next) => { if (!next) onClose(); }}>
    <Modal.Backdrop><Modal.Container size="lg"><Modal.Dialog className="page-gallery">
      <Modal.CloseTrigger />
      <Modal.Header><Modal.Icon><DeckIcon name="page" /></Modal.Icon><Modal.Heading>{fr ? "Créer une page" : "Create a page"}</Modal.Heading></Modal.Header>
      <Modal.Body>
        <p className="page-gallery-intro">{fr ? "Choisissez un point de départ. Vous pourrez modifier les écrans et toutes les commandes ensuite." : "Choose a starting point. You can edit both screens and every command afterward."}</p>
        <div className="page-gallery-grid">
          {PAGE_TEMPLATES.filter((template) => template.id !== "lyrics" || Boolean(window.decksDesktopControls)).map((template) => <button key={template.id} className="page-gallery-card" type="button" onClick={() => onChoose(template.id)}>
            <span className="page-gallery-preview" data-template={template.id} aria-hidden="true"><span className="page-gallery-top"><DeckIcon name={template.icon} size={23} /><span className="page-gallery-visual-lines"><i /><i /><i /></span></span><span className="page-gallery-bottom">{Array.from({ length: 6 }, (_, index) => <i key={index} className={index < template.actions.length || template.id === "windows" ? "filled" : ""} />)}</span></span>
            <strong>{template.title[locale]}</strong><small>{template.description[locale]}</small>
          </button>)}
        </div>
        <p className="page-gallery-note">{fr ? "Les pages dynamiques affichent les données disponibles sur votre ordinateur. Les fonctions absentes restent clairement indiquées." : "Dynamic pages show available computer data. Missing features remain clearly indicated."}</p>
      </Modal.Body><Modal.Footer><Button variant="ghost" onPress={onClose}>{fr ? "Annuler" : "Cancel"}</Button></Modal.Footer>
    </Modal.Dialog></Modal.Container></Modal.Backdrop>
  </Modal>;
}
