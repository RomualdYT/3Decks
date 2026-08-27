/* Fonctions pures partagées par les vues et formulaires de l'éditeur. */

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]
  ));
}

export function localizedText(value, locale) {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object') return '';
  return value[locale] || value.en || value.fr || '';
}

export function setLocalizedText(value, locale, next) {
  const object = typeof value === 'object' && value
    ? { ...value }
    : { en: typeof value === 'string' ? value : '', fr: typeof value === 'string' ? value : '' };
  object[locale] = next;
  if (object.fr === object.en) return object.en;
  return object;
}

export function actionKind(value) {
  if (typeof value === 'string') return value;
  return value && typeof value === 'object' ? value.type || 'noop' : 'noop';
}

export function actionArgs(value) {
  if (!value || typeof value !== 'object') return {};
  const { type, ...rest } = value;
  return rest;
}

export function uniqueId(prefix, taken) {
  let index = 1;
  while (taken.includes(`${prefix}${index}`)) index += 1;
  return `${prefix}${index}`;
}

export function normaliseColor(value, fallback = '#3B82F6') {
  const text = String(value || fallback);
  if (/^#[0-9a-f]{3}$/i.test(text)) {
    return '#' + text.slice(1).split('').map((item) => item + item).join('');
  }
  return /^#[0-9a-f]{6}$/i.test(text) ? text : fallback;
}
