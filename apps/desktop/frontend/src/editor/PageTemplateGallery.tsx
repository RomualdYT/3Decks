import { Button, Card, Modal } from "@heroui/react";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { PAGE_TEMPLATES, type PageTemplateId } from "./pageTemplates";

interface Props { open: boolean; locale: Locale; onChoose: (id: PageTemplateId) => void; onClose: () => void }

const templateDetails: Record<PageTemplateId, { fr: string; en: string }> = {
  blank: { fr: "Partir de zéro", en: "Start from scratch" },
  lyrics: { fr: "6 commandes", en: "6 controls" },
  notifications: { fr: "Accès rapide", en: "Quick access" },
  windows: { fr: "Liste dynamique", en: "Live list" },
  obs: { fr: "Commandes OBS", en: "OBS controls" },
  streaming: { fr: "Chat + OBS", en: "Chat + OBS" },
  system: { fr: "4 commandes", en: "4 controls" },
};

export function PageTemplateGallery({ open, locale, onChoose, onClose }: Props) {
  const fr = locale === "fr";
  const templates = PAGE_TEMPLATES;

  return <Modal isOpen={open} onOpenChange={(next) => { if (!next) onClose(); }}>
    <Modal.Backdrop><Modal.Container size="lg"><Modal.Dialog className="page-gallery">
      <Modal.CloseTrigger />
      <Modal.Header className="page-gallery-header">
        <Modal.Icon><DeckIcon name="page" /></Modal.Icon>
        <div className="page-gallery-heading">
          <span className="page-gallery-eyebrow">{fr ? "NOUVELLE PAGE" : "NEW PAGE"}</span>
          <Modal.Heading>{fr ? "Créer une page" : "Create a page"}</Modal.Heading>
        </div>
      </Modal.Header>
      <Modal.Body className="page-gallery-body">
        <p className="page-gallery-intro">{fr ? "Choisissez un modèle pour démarrer. Vous pourrez tout personnaliser ensuite." : "Choose a template to get started. You can customize everything later."}</p>
        <div className="page-gallery-grid" role="group" aria-label={fr ? "Modèles de page" : "Page templates"}>
          {templates.map((template) => <Card<"button">
            key={template.id}
            variant="secondary"
            className="page-gallery-card"
            render={(props) => <button {...props} type="button" onClick={() => onChoose(template.id)} aria-label={`${template.title[locale]} — ${template.description[locale]}`} />}
          >
            <span className="page-gallery-card-content">
              <span className="page-gallery-card-topline">
                <span className="page-gallery-icon" data-template={template.id}><DeckIcon name={template.icon} size={19} /></span>
              </span>
              <Card.Content className="page-gallery-copy">
                <Card.Title>{template.title[locale]}</Card.Title>
                <Card.Description>{template.description[locale]}</Card.Description>
              </Card.Content>
              <span className="page-gallery-action"><span>{fr ? "Utiliser ce modèle" : "Use this template"}</span><span className="page-gallery-meta">{templateDetails[template.id][locale]}</span></span>
            </span>
          </Card>)}
        </div>
      </Modal.Body>
      <Modal.Footer className="page-gallery-footer">
        <span className="page-gallery-hint">{fr ? "Chaque modèle reste entièrement modifiable." : "Every template stays fully editable."}</span>
        <Button variant="ghost" onPress={onClose}>{fr ? "Annuler" : "Cancel"}</Button>
      </Modal.Footer>
    </Modal.Dialog></Modal.Container></Modal.Backdrop>
  </Modal>;
}
