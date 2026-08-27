/* Accès authentifié à l'agent local 3Decks. */

const TOKEN_KEY = 'deck3ds.token';

function readToken() {
  const fromUrl = new URLSearchParams(location.search).get('token');
  if (fromUrl) {
    try {
      sessionStorage.setItem(TOKEN_KEY, fromUrl);
    } catch (error) {
      // Le jeton reste en mémoire si le stockage de session est refusé.
    }
    history.replaceState(null, '', location.pathname);
    return fromUrl;
  }
  try {
    return sessionStorage.getItem(TOKEN_KEY) || '';
  } catch (error) {
    return '';
  }
}

let token = readToken();

function forgetToken() {
  token = '';
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (error) { /* déjà oublié */ }
}

export function hasToken() {
  return Boolean(token);
}

export async function api(method, path, body) {
  const options = { method, headers: { 'X-Deck3DS-Token': token } };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`Réponse illisible de l’agent : ${text.slice(0, 200)}`);
  }

  if (response.status === 403) {
    forgetToken();
    throw new Error(
      'Le lien de configuration a expiré. Ouvrez le nouveau lien affiché par l’agent.'
    );
  }
  if (!response.ok) throw new Error(payload.error || `Erreur HTTP ${response.status}`);
  return payload;
}
