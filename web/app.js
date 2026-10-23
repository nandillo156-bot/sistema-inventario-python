'use strict';
const $ = selector => document.querySelector(selector);
let products = [], movements = [], view = 'productos', lowOnly = false, loaded = false;
let session = {usuario: null, modo_demo: false, csrf_token: '', permisos: []};
let sessionReady = false;
let redirecting = false;
const money = value => new Intl.NumberFormat('es-MX', {style: 'currency', currency: 'MXN'}).format(value);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

// Los permisos recibidos deciden qué acciones mostrar. El servidor los comprueba también.
const can = permission => sessionReady && !session.modo_demo && session.permisos.includes(permission);

async function api(path, method = 'GET', data) {
  const headers = {};
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRF-Token'] = session.csrf_token;
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
  if (response.status === 401 && !redirecting) {
    redirecting = true;
    window.location.replace('/login');
    throw new Error('Tu sesión terminó. Inicia sesión para continuar.');
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'No se pudo completar la operación.');
  return result;
}

function applySession(data) {
  session = data;
  sessionReady = true;
  const user = session.usuario;
  const roleLabels = {administrador: 'Administrador', admin: 'Administrador', operador: 'Operador', consulta: 'Consulta'};
  $('#user-name').textContent = session.modo_demo ? 'Inventario de muestra' : user.nombre;
  $('#user-role').textContent = session.modo_demo ? 'Solo lectura' : roleLabels[user.rol] || user.rol;
  $('#user-avatar').textContent = session.modo_demo ? 'DM' : user.nombre.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toLocaleUpperCase();
  $('#demo-banner').hidden = !session.modo_demo;
  $('#logout').hidden = session.modo_demo || !user;
  $('#new-product').hidden = view !== 'productos' || !can('gestionar_productos');
  $('#empty-add').hidden = !can('gestionar_productos');
}

async function initialize() {
  $('#refresh').disabled = true;
  $('#load-error').hidden = true;
  try {
    const data = await api('/api/sesion');
    if (!data.modo_demo && !data.usuario) {
      window.location.replace('/login');
      return;
    }
    applySession(data);
    await load();
  } catch (error) {
    $('#load-error').textContent = error.message + ' Vuelve a intentar con el botón de actualizar.';
    $('#load-error').hidden = false;
    $('#result-count').textContent = 'No se pudo comprobar la sesión';
  } finally {
    $('#refresh').disabled = false;
  }
}

let toastTimer;
function notify(message) { $('#toast').textContent = message; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 3500); }
async function load() {
  if (!sessionReady) return;
  $('#refresh').disabled = true;
  $('#load-error').hidden = true;
  try {
    [products, movements] = await Promise.all([api('/api/productos'), api('/api/movimientos')]);
    loaded = true;
    $('#total').textContent = products.length;
    $('#units').textContent = products.reduce((sum,p) => sum + p.stock, 0).toLocaleString('es-MX');
    $('#low').textContent = $('#low-count').textContent = products.filter(p => p.stock <= 5).length;
    render();
  } catch (error) { $('#load-error').textContent = error.message + ' Puedes volver a intentar con el botón de actualizar.'; $('#load-error').hidden = false; $('#result-count').textContent = 'No se pudieron actualizar los datos'; }
  finally { $('#refresh').disabled = false; }
}

function productActions(product) {
  const id = escapeHTML(product.id);
  const name = escapeHTML(product.nombre);
  const buttons = [];
  if (can('mover_stock')) buttons.push(`<button type="button" data-action="stock" data-id="${id}" aria-label="Registrar movimiento de ${name}" title="Registrar movimiento">⇄</button>`);
  if (can('gestionar_productos')) {
    buttons.push(`<button type="button" data-action="edit" data-id="${id}" aria-label="Editar ${name}" title="Editar">✎</button>`);
    buttons.push(`<button type="button" class="delete" data-action="delete" data-id="${id}" aria-label="Eliminar ${name}" title="Eliminar">×</button>`);
  }
  return buttons.length ? `<td><div class="row-actions">${buttons.join('')}</div></td>` : '';
}

function render() {
  const query = $('#search').value.trim().toLocaleLowerCase();
  $('#empty').hidden = true;
  $('.tabs').hidden = view !== 'productos';
  $('#table-note').textContent = view === 'productos' ? 'Un espacio para cada producto.' : 'Últimos 200 movimientos';
  if (view === 'productos') {
    const actionsHeading = can('gestionar_productos') || can('mover_stock') ? '<th>ACCIONES</th>' : '';
    $('#table-head').innerHTML = `<tr><th>PRODUCTO</th><th>CATEGORÍA</th><th>PRECIO</th><th>STOCK</th><th>ESTADO</th>${actionsHeading}</tr>`;
    const filtered = products.filter(p => (!lowOnly || p.stock <= 5) && `${p.nombre} ${p.categoria} ${p.descripcion}`.toLocaleLowerCase().includes(query));
    $('#rows').innerHTML = filtered.map(p => `<tr><td><div class="product-cell"><span class="product-icon">${escapeHTML(p.nombre.slice(0,1).toUpperCase())}</span><div><span class="product-name">${escapeHTML(p.nombre)}</span><small>${escapeHTML(p.descripcion)}</small></div></div></td><td><span class="category">${escapeHTML(p.categoria)}</span></td><td>${money(p.precio)}</td><td class="stock">${p.stock}<span style="font-weight:400;color:#9aa39b;font-size:10px"> uds.</span></td><td><span class="badge ${p.stock <= 5 ? 'low' : ''}">${p.stock === 0 ? 'Agotado' : p.stock <= 5 ? 'Stock bajo' : 'Disponible'}</span></td>${productActions(p)}</tr>`).join('');
    $('#result-count').textContent = `${filtered.length} de ${products.length} productos`;
    const emptyMessage = can('gestionar_productos') ? 'Agrega tu primer producto y organiza tus existencias.' : 'Los productos registrados aparecerán aquí.';
    if (!filtered.length && loaded) showEmpty(products.length ? 'Sin resultados' : 'Aquí empieza tu inventario', products.length ? 'Prueba otra búsqueda o cambia el filtro.' : emptyMessage, !products.length);
  } else {
    $('#table-head').innerHTML = '<tr><th>PRODUCTO</th><th>TIPO</th><th>CANTIDAD</th><th>STOCK ANTERIOR</th><th>STOCK ACTUAL</th><th>FECHA</th></tr>';
    const filtered = movements.filter(m => `${m.nombre} ${m.tipo}`.toLocaleLowerCase().includes(query));
    $('#rows').innerHTML = filtered.map(m => `<tr><td class="product-name">${escapeHTML(m.nombre)}</td><td><span class="badge ${m.tipo === 'Salida' ? 'low' : ''}">${escapeHTML(m.tipo)}</span></td><td>${m.tipo === 'Entrada' ? '+' : '−'}${m.cantidad}</td><td>${m.stock_anterior}</td><td>${m.stock_actual}</td><td>${escapeHTML(m.fecha)}</td></tr>`).join('');
    $('#result-count').textContent = `${filtered.length} movimientos`;
    if (!filtered.length && loaded) showEmpty(query ? 'Sin resultados' : 'Cada movimiento cuenta', query ? 'Prueba otra búsqueda.' : 'Las entradas y salidas de productos aparecerán aquí.', false);
  }
}
function showEmpty(title, message, add) { $('#empty').hidden = false; $('#empty h2').textContent = title; $('#empty p').textContent = message; $('#empty-add').hidden = !add || !can('gestionar_productos'); }
function openProduct(product) {
  if (!can('gestionar_productos')) return;
  const form = $('#product-form'); form.reset(); form.elements.id.value = ''; form.querySelector('.form-error').textContent = '';
  $('#form-title').textContent = product ? 'Editar producto' : 'Nuevo producto';
  form.elements.stock.disabled = !!product;
  form.elements.stock.parentElement.firstChild.textContent = product ? 'Stock actual (usa movimientos)' : 'Stock inicial';
  if (product) for (const field of ['id','nombre','descripcion','precio','stock','categoria']) form.elements[field].value = product[field];
  $('#product-dialog').showModal();
}
$('#new-product').onclick = $('#empty-add').onclick = () => openProduct();
$('#refresh').onclick = () => sessionReady ? load() : initialize();
$('#logout').onclick = async () => {
  $('#logout').disabled = true;
  try {
    session = await api('/api/logout', 'POST');
    window.location.replace('/login');
  } catch (error) {
    notify(error.message);
  } finally {
    $('#logout').disabled = false;
  }
};
$('#search').oninput = render;
$('#all-filter').onclick = () => { lowOnly = false; $('#all-filter').classList.add('selected'); $('#low-filter').classList.remove('selected'); render(); };
$('#low-filter').onclick = () => { lowOnly = true; $('#low-filter').classList.add('selected'); $('#all-filter').classList.remove('selected'); render(); };
document.querySelectorAll('[data-view]').forEach(button => button.onclick = () => {
  view = button.dataset.view; document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b === button));
  $('#breadcrumb').textContent = view === 'productos' ? 'Productos' : 'Movimientos';
  $('#title').innerHTML = view === 'productos' ? 'Tu inventario, al día<span>.</span>' : 'Cada movimiento, claro<span>.</span>';
  $('#subtitle').textContent = view === 'productos' ? 'Menos tareas. Más control sobre tus productos.' : 'Un registro de lo que entra y lo que sale.';
  $('#new-product').hidden = view !== 'productos' || !can('gestionar_productos'); $('#search').value = ''; $('#search').placeholder = view === 'productos' ? 'Buscar un producto…' : 'Buscar un movimiento…'; render();
});
document.querySelectorAll('.close').forEach(button => button.onclick = () => button.closest('dialog').close());
$('#rows').onclick = event => {
  const button = event.target.closest('[data-action]'); if (!button) return;
  if (!can(button.dataset.action === 'stock' ? 'mover_stock' : 'gestionar_productos')) return;
  const p = products.find(p => p.id === Number(button.dataset.id)); if (!p) return;
  if (button.dataset.action === 'edit') return openProduct(p);
  const kind = button.dataset.action === 'stock' ? 'stock' : 'delete'; const form = $(`#${kind}-form`);
  form.reset(); form.elements.id.value = p.id; form.querySelector('.form-error').textContent = '';
  if (kind === 'stock') $('#stock-product').textContent = `${p.nombre} · ${p.stock} unidades disponibles`;
  else $('#delete-name').textContent = p.nombre;
  $(`#${kind}-dialog`).showModal();
};
async function submit(form, action, success) {
  const button = form.querySelector('button[type="submit"], .dialog-actions .primary, .dialog-actions .danger');
  button.disabled = true; form.querySelector('.form-error').textContent = '';
  try { await action(); form.closest('dialog').close(); notify(success); await load(); }
  catch (error) { form.querySelector('.form-error').textContent = error.message; }
  finally { button.disabled = false; }
}
$('#product-form').onsubmit = event => {
  event.preventDefault();
  if (!can('gestionar_productos')) return;
  const form = event.currentTarget; const data = Object.fromEntries(new FormData(form));
  if (!data.id) data.stock = Number(form.elements.stock.value);
  data.precio = Number(data.precio);
  submit(form, () => api(`/api/productos${data.id ? '/'+data.id : ''}`, data.id ? 'PUT' : 'POST', data), data.id ? 'Producto actualizado' : 'Producto agregado');
};
$('#stock-form').onsubmit = event => { event.preventDefault(); if (!can('mover_stock')) return; const form = event.currentTarget; const data = Object.fromEntries(new FormData(form)); data.cantidad = Number(data.cantidad); submit(form, () => api(`/api/productos/${data.id}/movimientos`, 'POST', data), 'Movimiento registrado'); };
$('#delete-form').onsubmit = event => { event.preventDefault(); if (!can('gestionar_productos')) return; const form = event.currentTarget; submit(form, () => api(`/api/productos/${form.elements.id.value}`, 'DELETE'), 'Producto eliminado'); };
initialize();
