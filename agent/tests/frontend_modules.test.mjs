import assert from 'node:assert/strict';
import test from 'node:test';

import {
  actionArgs,
  actionKind,
  escapeHtml,
  localizedText,
  normaliseColor,
  setLocalizedText,
  uniqueId,
} from '../deck3ds/ui/static/editor-utils.js';
import {
  hotkeyFromEvent,
  hotkeyPreview,
  joinHotkey,
  splitHotkey,
} from '../deck3ds/ui/static/hotkeys.js';
import { initialLocale, translate } from '../deck3ds/ui/static/translations.js';

const catalogue = {
  modifiers: [
    { name: 'cmd', label_en: 'Cmd', label_fr: 'Cmd' },
    { name: 'ctrl', label_en: 'Ctrl', label_fr: 'Ctrl' },
    { name: 'alt', label_en: 'Alt', label_fr: 'Alt' },
    { name: 'shift', label_en: 'Shift', label_fr: 'Maj' },
  ],
  keys: [
    { name: 'escape', label_en: 'Escape', label_fr: 'Échap' },
    { name: 'return', label_en: 'Return', label_fr: 'Entrée' },
  ],
};

test('les utilitaires normalisent les valeurs de configuration', () => {
  assert.equal(escapeHtml('<button title="x">'), '&lt;button title=&quot;x&quot;&gt;');
  assert.equal(localizedText({ fr: '', en: 'Fallback' }, 'fr'), 'Fallback');
  assert.deepEqual(setLocalizedText('Same', 'fr', 'Différent'), {
    en: 'Same',
    fr: 'Différent',
  });
  assert.equal(setLocalizedText({ en: 'Same', fr: 'Différent' }, 'fr', 'Same'), 'Same');
  assert.equal(actionKind('media.play'), 'media.play');
  assert.equal(actionKind({ type: 'page.open', page: 'home' }), 'page.open');
  assert.deepEqual(actionArgs({ type: 'page.open', page: 'home' }), { page: 'home' });
  assert.equal(uniqueId('page', ['page1', 'page2']), 'page3');
  assert.equal(normaliseColor('#3af'), '#33aaff');
  assert.equal(normaliseColor('invalid', '#123456'), '#123456');
});

test('les raccourcis suivent l’ordre canonique du catalogue', () => {
  assert.deepEqual(splitHotkey(' shift + cmd + shift + a ', catalogue), {
    modifiers: ['cmd', 'shift'],
    key: 'a',
  });
  assert.equal(joinHotkey(['shift', 'cmd', 'cmd'], 'escape', catalogue), 'cmd+shift+escape');
  assert.equal(hotkeyPreview('cmd+shift+escape', catalogue, 'fr', 'Aucun'), 'Cmd + Maj + Échap');
  assert.equal(hotkeyPreview('', catalogue, 'fr', 'Aucun'), 'Aucun');
});

test('la capture clavier utilise la position physique et les modificateurs', () => {
  assert.equal(hotkeyFromEvent({ code: 'KeyA', metaKey: true, shiftKey: true }, catalogue), 'cmd+shift+a');
  assert.equal(hotkeyFromEvent({ code: 'NumpadEnter', ctrlKey: true }, catalogue), 'ctrl+return');
  assert.equal(hotkeyFromEvent({ code: 'AudioVolumeUp' }, catalogue), '');
});

test('les traductions appliquent replis, variables et préférence locale', () => {
  assert.equal(translate('en', 'pageCount', { count: 2, limit: 8 }), '2 / 8 pages');
  assert.equal(translate('unknown', 'save'), 'Enregistrer');
  assert.equal(translate('fr', 'missing.key'), 'missing.key');
  assert.equal(initialLocale({ getItem: () => 'en' }, 'fr-FR'), 'en');
  assert.equal(initialLocale({ getItem: () => null }, 'fr-FR'), 'fr');
  assert.equal(initialLocale({ getItem: () => { throw new Error('blocked'); } }, 'en-US'), 'en');
});
