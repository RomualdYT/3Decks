import { useState } from "react";
import { Button, Modal } from "@heroui/react";
import type { AgentState, DeckConfig, Locale, Schema } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { PageTemplatePreview } from "./PageTemplatePreview";
import {
  PAGE_TEMPLATES,
  pageFromTemplate,
  templateSetupNotes,
  type PageTemplateId,
} from "./pageTemplates";

interface Props {
  open: boolean;
  locale: Locale;
  config: DeckConfig;
  schema: Schema;
  status: AgentState | null;
  scenes: string[];
  apps: string[];
  onChoose: (id: PageTemplateId, variant?: string) => void;
  onClose: () => void;
}

export function PageTemplateGallery({
  open,
  locale,
  config,
  schema,
  status,
  scenes,
  apps,
  onChoose,
  onClose,
}: Props) {
  const [selected, setSelected] = useState<PageTemplateId>("home");
  const [variantId, setVariantId] = useState<string>();
  const fr = locale === "fr";
  const template = PAGE_TEMPLATES.find((item) => item.id === selected)!;
  const page = pageFromTemplate(config, schema, selected, {
    scenes,
    variant: variantId,
    platform: status?.platform,
    apps,
  });
  const notes = templateSetupNotes(page, config, scenes, locale);
  const atLimit = config.pages.length >= schema.limits.pages;
  const groups = [
    { id: "essentials", title: fr ? "Les essentiels" : "Essentials" },
    {
      id: "optional",
      title: fr ? "Selon vos usages" : "More ways to use 3Decks",
    },
    { id: "custom", title: fr ? "À votre façon" : "Make it yours" },
  ];

  return (
    <Modal
      isOpen={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <Modal.Backdrop>
        <Modal.Container size="lg">
          <Modal.Dialog className="page-gallery">
            <Modal.CloseTrigger />
            <Modal.Header className="page-gallery-header">
              <Modal.Icon>
                <DeckIcon name="page" />
              </Modal.Icon>
              <Modal.Heading>
                {fr ? "Créer une page" : "Create a page"}
              </Modal.Heading>
            </Modal.Header>
            <Modal.Body className="page-gallery-body">
              <p className="page-gallery-intro">
                {fr
                  ? "Choisissez un usage, puis son affichage. Tout reste personnalisable."
                  : "Choose a purpose, then its display. Everything stays customizable."}
              </p>
              <div className="page-gallery-layout">
                <nav
                  className="page-gallery-catalog"
                  aria-label={fr ? "Modèles de page" : "Page templates"}
                >
                  {groups.map((group) => (
                    <section key={group.id}>
                      <h3>{group.title}</h3>
                      {PAGE_TEMPLATES.filter(
                        (item) => item.group === group.id,
                      ).map((item) => (
                        <Button
                          key={item.id}
                          variant="ghost"
                          className="page-gallery-option"
                          aria-pressed={selected === item.id}
                          onPress={() => {
                            setSelected(item.id);
                            setVariantId(undefined);
                          }}
                        >
                          <span className="page-gallery-icon">
                            <DeckIcon name={item.icon} size={19} />
                          </span>
                          <span>{item.title[locale]}</span>
                          <DeckIcon name="next" size={14} />
                        </Button>
                      ))}
                    </section>
                  ))}
                </nav>
                <section
                  className="page-gallery-detail"
                  aria-label={template.title[locale]}
                >
                  <div className="page-gallery-copy">
                    <h3>{template.title[locale]}</h3>
                    <p>{template.description[locale]}</p>
                  </div>
                  {template.variants && (
                    <div
                      className="page-gallery-variants"
                      role="group"
                      aria-label={
                        fr ? "Affichage supérieur" : "Top screen display"
                      }
                    >
                      {template.variants.map((variant) => (
                        <Button
                          key={variant.id}
                          variant="secondary"
                          aria-pressed={page.dashboard === variant.dashboard}
                          onPress={() => setVariantId(variant.id)}
                        >
                          {variant.title[locale]}
                        </Button>
                      ))}
                    </div>
                  )}
                  <PageTemplatePreview
                    config={config}
                    page={page}
                    status={status}
                    locale={locale}
                  />
                  <p className="page-gallery-preview-label">
                    {fr
                      ? "Aperçu avec les données actuelles de votre ordinateur"
                      : "Preview using your computer’s current data"}
                  </p>
                  {notes.length > 0 && (
                    <div className="page-gallery-setup">
                      <DeckIcon name="info" size={16} />
                      <div>
                        {notes.map((note) => (
                          <p key={note}>{note}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </section>
              </div>
            </Modal.Body>
            <Modal.Footer className="page-gallery-footer">
              <span className="page-gallery-hint">
                {atLimit
                  ? fr
                    ? "Limite de pages atteinte. Supprimez une page pour continuer."
                    : "Page limit reached. Remove a page to continue."
                  : fr
                    ? "Vos pages existantes sont conservées."
                    : "Your existing pages are preserved."}
              </span>
              <Button variant="ghost" onPress={onClose}>
                {fr ? "Annuler" : "Cancel"}
              </Button>
              <Button
                isDisabled={atLimit}
                onPress={() => onChoose(selected, variantId)}
              >
                {fr ? "Ajouter la page" : "Add page"}
              </Button>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
