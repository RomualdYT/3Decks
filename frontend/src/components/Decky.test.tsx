import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Decky, DeckyLogo, DeckyProvider, deckyMoods, useDeckyPreference } from "./Decky";

let root: Root, container: HTMLDivElement;
beforeEach(() => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  localStorage.clear();
  container = document.createElement("div");
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

function Toggle() {
  const { visible, setVisible } = useDeckyPreference();
  return <button onClick={() => setVisible(!visible)}>toggle</button>;
}
it("maps the six native poses to distinct sprite rows and stays decorative", async () => {
  await act(async () => root.render(<>{deckyMoods.map(mood => <Decky key={mood} mood={mood} />)}</>));
  expect(container.querySelectorAll('.decky[aria-hidden="true"]')).toHaveLength(6);
  expect(Array.from(container.querySelectorAll<HTMLElement>('.decky')).map(node => node.style.backgroundPositionY)).toEqual(["0%", "20%", "40%", "60%", "80%", "100%"]);
});
it("hides all companions immediately and remembers the browser preference", async () => {
  await act(async () => root.render(<DeckyProvider><Toggle /><Decky /><Decky mood="search" /></DeckyProvider>));
  await act(async () => container.querySelector('button')!.click());
  expect(container.querySelector('.decky')).toBeNull();
  expect(localStorage.getItem('3decks.decky.visible.v1')).toBe('false');
  await act(async () => root.render(<DeckyProvider key="reload"><Decky /></DeckyProvider>));
  expect(container.querySelector('.decky')).toBeNull();
});
it("still works when browser storage is unavailable", async () => {
  vi.spyOn(Storage.prototype,'getItem').mockImplementation(() => { throw new Error('blocked'); });
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(() => { throw new Error('blocked'); });
  await act(async () => root.render(<DeckyProvider><Toggle /><Decky /></DeckyProvider>));
  expect(container.querySelector('.decky')).not.toBeNull();
  await act(async () => container.querySelector('button')!.click());
  expect(container.querySelector('.decky')).toBeNull();
});

it("keeps the header logo but disables its animation when Decky is hidden", async () => {
  await act(async () => root.render(<DeckyProvider><Toggle /><DeckyLogo /></DeckyProvider>));
  expect(container.querySelector('.decky-brand-mark.can-animate')).not.toBeNull();
  await act(async () => container.querySelector('button')!.click());
  expect(container.querySelector('.decky-brand-mark.can-animate')).toBeNull();
  expect(container.querySelector('img')?.getAttribute('src')).toBe('/decky-logo.svg');
});
