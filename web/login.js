'use strict';

const form = document.querySelector('#login-form');
const fields = document.querySelector('#login-fields');
const submitButton = document.querySelector('#login-submit');
const errorMessage = document.querySelector('#login-error');
const statusMessage = document.querySelector('#login-status');
const retryButton = document.querySelector('#session-retry');

// La sesión vive en una cookie HttpOnly; el token CSRF solo vive en esta página.
let csrfToken = '';
let busy = false;

function setBusy(value, label = 'Entrando…') {
  busy = value;
  form.setAttribute('aria-busy', String(value));
  fields.disabled = value || !csrfToken;
  submitButton.disabled = value || !csrfToken;
  submitButton.textContent = value ? label : 'Entrar';
}

async function api(path, method = 'GET', data) {
  const headers = {};
  if (method !== 'GET') headers['X-CSRF-Token'] = csrfToken;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  let response;
  try {
    response = await fetch(path, {
      method,
      credentials: 'same-origin',
      headers,
      ...(data !== undefined ? {body: JSON.stringify(data)} : {}),
    });
  } catch {
    throw new Error('No se pudo conectar. Comprueba tu conexión y vuelve a intentar.');
  }
  const result = await response.json();
  if (!response.ok) {
    const fallback = response.status === 429
      ? 'Demasiados intentos. Espera unos minutos antes de volver a intentar.'
      : 'No se pudo iniciar sesión. Vuelve a intentar.';
    throw new Error(result.error || fallback);
  }
  return result;
}

async function initialize() {
  errorMessage.textContent = '';
  retryButton.hidden = true;
  statusMessage.textContent = 'Comprobando sesión…';
  setBusy(true, 'Preparando acceso…');
  try {
    const session = await api('/api/sesion');
    if (session.modo_demo || session.usuario) {
      window.location.replace('/');
      return;
    }
    csrfToken = session.csrf_token;
    if (!csrfToken) throw new Error('No se pudo preparar el acceso. Vuelve a intentar.');
  } catch (error) {
    csrfToken = '';
    errorMessage.textContent = error.message;
    retryButton.hidden = false;
  } finally {
    statusMessage.textContent = '';
    setBusy(false);
  }
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (busy || !csrfToken) return;
  errorMessage.textContent = '';
  setBusy(true);
  try {
    const session = await api('/api/login', 'POST', {
      nombre: form.elements.nombre.value.trim(),
      clave: form.elements.clave.value,
    });
    csrfToken = session.csrf_token;
    window.location.replace('/');
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    form.elements.clave.value = '';
    setBusy(false);
  }
});

retryButton.addEventListener('click', initialize);
initialize();
