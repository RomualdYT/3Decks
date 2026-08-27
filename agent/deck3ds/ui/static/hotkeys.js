/* Analyse et capture des raccourcis, sans dépendance au DOM. */

const CODE_TO_KEY = Object.freeze({
  Escape: 'escape',
  Enter: 'return',
  NumpadEnter: 'return',
  Tab: 'tab',
  Space: 'space',
  Backspace: 'backspace',
  Delete: 'forward_delete',
  ArrowLeft: 'left',
  ArrowRight: 'right',
  ArrowUp: 'up',
  ArrowDown: 'down',
  Home: 'home',
  End: 'end',
  PageUp: 'pageup',
  PageDown: 'pagedown',
  PrintScreen: 'printscreen',
});

function modifierOrder(catalogue) {
  return (catalogue?.modifiers || []).map((modifier) => modifier.name);
}

export function splitHotkey(value, catalogue) {
  const parts = String(value || '')
    .split('+')
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
  const order = modifierOrder(catalogue);
  const known = new Set(order);
  return {
    modifiers: order.filter((name) => parts.includes(name)),
    key: parts.find((part) => !known.has(part)) || '',
  };
}

export function joinHotkey(modifiers, key, catalogue) {
  const selected = new Set(modifiers);
  const sorted = modifierOrder(catalogue).filter((name) => selected.has(name));
  return [...sorted, key].filter(Boolean).join('+');
}

export function keyLabel(name, catalogue, locale) {
  const entry = (catalogue?.keys || []).find((item) => item.name === name);
  if (entry) return locale === 'fr' ? entry.label_fr : entry.label_en;
  return String(name || '').toUpperCase();
}

export function modifierLabel(name, catalogue, locale) {
  const entry = (catalogue?.modifiers || []).find((item) => item.name === name);
  if (entry) return locale === 'fr' ? entry.label_fr : entry.label_en;
  return name;
}

export function hotkeyPreview(value, catalogue, locale, emptyLabel) {
  const { modifiers, key } = splitHotkey(value, catalogue);
  if (!key && !modifiers.length) return emptyLabel;
  return [
    ...modifiers.map((name) => modifierLabel(name, catalogue, locale)),
    key ? keyLabel(key, catalogue, locale) : '…',
  ].join(' + ');
}

export function hotkeyFromEvent(event, catalogue) {
  let key = CODE_TO_KEY[event.code] || '';
  if (!key && /^F([1-9]|1[0-2])$/.test(event.code)) key = event.code.toLowerCase();
  if (!key && /^Key[A-Z]$/.test(event.code)) key = event.code.slice(3).toLowerCase();
  if (!key && /^Digit[0-9]$/.test(event.code)) key = event.code.slice(5);
  if (!key) return '';

  const modifiers = [];
  if (event.metaKey) modifiers.push('cmd');
  if (event.ctrlKey) modifiers.push('ctrl');
  if (event.altKey) modifiers.push('alt');
  if (event.shiftKey) modifiers.push('shift');
  return joinHotkey(modifiers, key, catalogue);
}
