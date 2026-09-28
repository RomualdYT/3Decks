import { createContext, useContext, useState, type CSSProperties, type ReactNode } from "react";

export const deckyMoods = ["idle", "wave", "search", "music", "sleep", "confused"] as const;
export type DeckyMood = typeof deckyMoods[number];
type Preference = { visible: boolean; setVisible: (value: boolean) => void };
const DeckyContext = createContext<Preference>({ visible: true, setVisible: () => {} });
const preferenceKey = "3decks.decky.visible.v1";

export function DeckyProvider({ children }: { children: ReactNode }) {
  const [visible, setValue] = useState(() => {
    try { return localStorage.getItem(preferenceKey) !== "false"; } catch { return true; }
  });
  const setVisible = (value: boolean) => {
    setValue(value);
    try { localStorage.setItem(preferenceKey, String(value)); } catch { /* Session-only preference. */ }
  };
  return <DeckyContext.Provider value={{ visible, setVisible }}>{children}</DeckyContext.Provider>;
}

export const useDeckyPreference = () => useContext(DeckyContext);

/** Header identity remains visible even when decorative appearances are hidden. */
export function DeckyLogo() {
  const { visible } = useDeckyPreference();
  return <span aria-hidden="true" className={`decky-brand-mark${visible ? " can-animate" : ""}`}>
    <img className="decky-brand" src="/decky-logo.svg" alt="" />
    <span className="decky-brand-sprite" />
  </span>;
}

/** Decorative, silent sprite. Artwork is generated from the native C renderer.
 * CSS handles animation without React timers; reduced-motion displays frame zero.
 */
export function Decky({ mood = "idle", size = 80 }: { mood?: DeckyMood; size?: number }) {
  const { visible } = useDeckyPreference();
  if (!visible) return null;
  return <span aria-hidden="true" className="decky" data-mood={mood} style={{
    "--decky-size": `${size}px`, backgroundPositionY: `${deckyMoods.indexOf(mood) * 20}%`,
  } as CSSProperties} />;
}
