import { Disclosure } from "@heroui/react";
import type { ExtensionManifest, Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { localized } from "../utils/config";

type Props = { manifest: ExtensionManifest; locale: Locale; ready: boolean };

export function ExtensionContributions({ manifest, locale, ready }: Props) {
  const fr = locale === "fr";
  const groups = [
    {
      id: "actions", icon: "workflow", title: fr ? "Actions des boutons" : "Button actions", items: manifest.actions,
      path: fr ? ["Éditeur", "Choisir un bouton", "Action", "Extensions"] : ["Editor", "Select a button", "Action", "Extensions"],
    },
    {
      id: "sources", icon: "grid", title: fr ? "Contenus des boutons" : "Button content", items: manifest.sources,
      path: fr ? ["Réglages de la page", "Écran tactile", "Contenu des boutons"] : ["Page settings", "Touch screen", "Button content"],
    },
    {
      id: "dashboards", icon: "monitor", title: fr ? "Écrans supérieurs" : "Top screens", items: manifest.dashboards,
      path: fr ? ["Réglages de la page", "Écran supérieur", "Informations affichées en haut"] : ["Page settings", "Top screen", "Information shown on top"],
    },
  ].filter((group) => group.items.length > 0);

  if (!groups.length) return null;
  return <Disclosure className="advanced-disclosure extension-catalog">
    <Disclosure.Heading>
      <Disclosure.Trigger><span><DeckIcon name="extension" size={16} />{fr ? "Utiliser dans l’éditeur" : "Use in the editor"}</span><Disclosure.Indicator /></Disclosure.Trigger>
    </Disclosure.Heading>
    <Disclosure.Content><Disclosure.Body>
      {!ready && <p className="extension-catalog-note">{fr ? "Activez l’extension pour utiliser ces éléments dans l’éditeur." : "Enable the extension to use these items in the editor."}</p>}
      {groups.map((group) => <section className="extension-catalog-group" key={group.id}>
        <h3><DeckIcon name={group.icon} size={16} />{group.title}<span>{group.items.length}</span></h3>
        <ul>
          {group.items.map((item) => {
            const title = localized(item.title, locale);
            const description = localized(item.description, locale);
            return <li key={item.id}>
              <span className="extension-catalog-icon"><DeckIcon name={typeof item.icon === "string" ? item.icon : group.icon} size={19} /></span>
              <div><strong>{title}</strong>{description && description.trim() !== title.trim() && <p>{description}</p>}</div>
            </li>;
          })}
        </ul>
        <div className="extension-catalog-path" aria-label={fr ? "Où le trouver" : "Where to find it"}>
          {group.path.map((step, index) => <span key={step}>{index > 0 && <DeckIcon name="next" size={12} />}<span>{step}</span></span>)}
        </div>
      </section>)}
    </Disclosure.Body></Disclosure.Content>
  </Disclosure>;
}
