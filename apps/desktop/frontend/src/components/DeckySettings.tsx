import { Button, Switch } from "@heroui/react";
import { useState } from "react";
import type { Locale } from "../app/types";
import { Decky, deckyMoods, useDeckyPreference } from "./Decky";

export function DeckySettings({ locale }: { locale: Locale }) {
  const fr = locale === "fr";
  const { visible, setVisible } = useDeckyPreference();
  const [pose, setPose] = useState(1);
  const labels = fr ? ["Curieux", "Coucou !", "À ta recherche", "En musique", "Bonne nuit", "Hmm ?"] :
    ["Curious", "Hello!", "Looking for you", "Listening", "Sweet dreams", "Hmm?"];
  return <section className="settings-card decky-settings">
    <div className="decky-settings-heading"><div><span className="eyebrow">DECKY</span>
      <h3>{fr ? "Un peu de compagnie." : "A little company."}</h3>
      <p>{fr ? "Ton petit compagnon, dans les moments utiles. Jamais sur tes boutons." : "Your little companion, where he can help. Never on your buttons."}</p></div>
      <Switch aria-label={fr ? "Afficher Decky sur ce navigateur" : "Show Decky in this browser"} isSelected={visible} onChange={setVisible}>
        <Switch.Content><Switch.Control><Switch.Thumb /></Switch.Control></Switch.Content>
      </Switch>
    </div>
    {visible && <div className="decky-playground"><Decky mood={deckyMoods[pose]} size={120} />
      <div><strong aria-live="polite">{labels[pose]}</strong><p>{fr ? "Le même petit robot que sur ta 3DS." : "The very same little robot as on your 3DS."}</p>
        <Button variant="outline" size="sm" onPress={() => setPose((value) => (value + 1) % deckyMoods.length)}>{fr ? "Une autre expression" : "Another expression"}</Button></div>
    </div>}
    <p className="decky-preference-note">{fr ? "Appliqué immédiatement sur ce navigateur. Sur la 3DS : Réglages → Decky. Les animations respectent la préférence de mouvement réduit du système." : "Applied immediately in this browser. On 3DS: Settings → Decky. Animations respect your system’s reduced-motion preference."}</p>
  </section>;
}
