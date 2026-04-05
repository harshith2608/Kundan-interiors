/**
 * Kundan's Interiors – Dynamic Project Form
 * Measurements are entered as Feet + Inches and converted to decimal feet for calculation.
 */

'use strict';

// ─── State ────────────────────────────────────────────────────────────────────
let woodRates = {};
let masterRooms = [];
let masterItems = [];
let roomCounter = 0;
const rooms = {};  // { roomKey: { name, items: { itemKey: { name, lengthFt, lengthIn, widthFt, widthIn, wood_type } } } }

// ─── Custom Autocomplete ───────────────────────────────────────────────────────
// Dropdown is appended to <body> so it is never clipped by table overflow or
// any parent with overflow:hidden — works for both room-name and item-name inputs.
function initAutocomplete(input, suggestions) {
  const ul = document.createElement('ul');
  ul.className = 'ki-ac-dropdown';
  ul.setAttribute('role', 'listbox');
  document.body.appendChild(ul);
  input._acDropdown = ul;   // keep ref for cleanup when row/room is removed

  let activeIdx = -1;

  function reposition() {
    const r = input.getBoundingClientRect();
    ul.style.top   = r.bottom + 'px';
    ul.style.left  = r.left + 'px';
    ul.style.width = Math.max(r.width, 180) + 'px';
  }

  function showSuggestions(query) {
    ul.innerHTML = '';
    activeIdx = -1;
    const q = (query || '').toLowerCase().trim();
    const matches = q
      ? suggestions.filter(s => s.toLowerCase().includes(q)).slice(0, 12)
      : suggestions.slice(0, 12);

    if (!matches.length) { ul.style.display = 'none'; return; }

    matches.forEach(s => {
      const li = document.createElement('li');
      li.textContent = s;
      li.setAttribute('role', 'option');

      // Mouse: preventDefault stops the input losing focus before selection
      li.addEventListener('mousedown', function (e) {
        e.preventDefault();
        input.value = s;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        ul.style.display = 'none';
      });

      // Touch: only select on touchend if finger didn't scroll (dy < 8px)
      let touchStartY = 0;
      li.addEventListener('touchstart', function (e) {
        touchStartY = e.touches[0].clientY;
      }, { passive: true });
      li.addEventListener('touchend', function (e) {
        const dy = Math.abs(e.changedTouches[0].clientY - touchStartY);
        if (dy < 8) {
          e.preventDefault();
          input.value = s;
          input.dispatchEvent(new Event('input', { bubbles: true }));
          ul.style.display = 'none';
        }
      });

      ul.appendChild(li);
    });

    reposition();
    ul.style.display = 'block';
  }

  input.addEventListener('input',  function () { showSuggestions(this.value); });
  input.addEventListener('focus',  function () { showSuggestions(this.value); });
  input.addEventListener('blur',   function () { setTimeout(() => { ul.style.display = 'none'; }, 250); });
  // Prevent scrolling inside the dropdown from closing it via blur
  ul.addEventListener('touchstart', function (e) { e.stopPropagation(); }, { passive: true });
  window.addEventListener('scroll', reposition, { passive: true });
  window.addEventListener('resize', reposition, { passive: true });

  input.addEventListener('keydown', function (e) {
    const items = ul.querySelectorAll('li');
    if (!items.length || ul.style.display === 'none') return;
    if      (e.key === 'ArrowDown')              { e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); }
    else if (e.key === 'ArrowUp')                { e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); }
    else if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); items[activeIdx].dispatchEvent(new MouseEvent('mousedown')); return; }
    else if (e.key === 'Escape')                 { ul.style.display = 'none'; return; }
    items.forEach((li, i) => li.classList.toggle('active', i === activeIdx));
    if (activeIdx >= 0) items[activeIdx].scrollIntoView({ block: 'nearest' });
  });
}

// ─── Conversion helpers ───────────────────────────────────────────────────────
function ftInToDecimal(ft, inch) {
  return parseFloat(ft || 0) + parseFloat(inch || 0) / 12;
}

function decimalToFtIn(decimal) {
  if (!decimal || isNaN(decimal)) return { ft: 0, inch: 0 };
  let ft = Math.floor(decimal);
  let inch = Math.round((decimal - ft) * 12);
  if (inch === 12) { ft++; inch = 0; }
  return { ft, inch };
}

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  try { woodRates    = JSON.parse(document.getElementById('wood-rates-data').textContent  || '{}'); } catch (e) { woodRates = {}; }
  try { masterRooms  = JSON.parse(document.getElementById('master-rooms-json').textContent || '[]'); } catch (e) { masterRooms = []; }
  try { masterItems  = JSON.parse(document.getElementById('master-items-json').textContent || '[]'); } catch (e) { masterItems = []; }

  let existingRooms = [];
  try { existingRooms = JSON.parse(document.getElementById('existing-rooms-data').textContent || '[]'); }
  catch (e) { existingRooms = []; }

  if (existingRooms && existingRooms.length > 0) {
    existingRooms.forEach(rd => {
      const rk = addRoom(rd.name);
      (rd.items || []).forEach(id => {
        // Convert stored decimal back to ft+in for display
        const lFtIn = decimalToFtIn(id.length);
        const wFtIn = decimalToFtIn(id.width);
        addItem(rk, id.name, lFtIn.ft, lFtIn.inch, wFtIn.ft, wFtIn.inch, id.wood_type);
      });
    });
  }

  updateNoRoomsHint();
  recalcAll();
});

// ─── Room Management ──────────────────────────────────────────────────────────
function addRoom(presetName) {
  roomCounter++;
  const rk = 'room_' + roomCounter;
  rooms[rk] = { name: presetName || '', items: {} };

  const container = document.getElementById('rooms-container');
  const div = document.createElement('div');
  div.className = 'card shadow-sm mb-3 room-card';
  div.id = 'room_card_' + rk;
  div.innerHTML = `
    <div class="card-header d-flex align-items-center gap-2 py-2">
      <i class="bi bi-door-open text-primary"></i>
      <input type="text"
             class="form-control form-control-sm fw-semibold"
             id="room_name_${rk}"
             placeholder="Room name (e.g. Living Room)"
             value="${escHtml(presetName || '')}"
             oninput="onRoomNameChange('${rk}', this.value)"
             autocomplete="off"
             style="max-width:280px">
      <span class="badge bg-primary ms-auto me-1" id="room_total_badge_${rk}">0.00 sqft</span>
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeRoom('${rk}')" title="Remove Room">
        <i class="bi bi-trash"></i>
      </button>
    </div>
    <div class="card-body p-2 p-md-3">
      <div class="item-table-wrap">
        <table class="table table-sm table-bordered item-table mb-2">
          <thead>
            <tr>
              <th style="min-width:150px">Item Name</th>
              <th style="min-width:155px">Length</th>
              <th style="min-width:155px">Width</th>
              <th style="min-width:120px">Wood Type</th>
              <th style="min-width:80px">Area (sqft)</th>
              <th style="width:36px"></th>
            </tr>
          </thead>
          <tbody id="items_tbody_${rk}"></tbody>
        </table>
      </div>
      <button type="button" class="btn btn-sm btn-outline-primary" onclick="addItem('${rk}')">
        <i class="bi bi-plus me-1"></i>Add Item
      </button>
    </div>
  `;
  container.appendChild(div);
  // Init autocomplete on room name input
  const roomNameEl = document.getElementById('room_name_' + rk);
  if (roomNameEl) initAutocomplete(roomNameEl, masterRooms);
  updateNoRoomsHint();
  if (!presetName) addItem(rk);
  return rk;
}

function removeRoom(rk) {
  const card = document.getElementById('room_card_' + rk);
  if (card) {
    card.querySelectorAll('input').forEach(inp => { if (inp._acDropdown) inp._acDropdown.remove(); });
    card.remove();
  }
  delete rooms[rk];
  updateNoRoomsHint();
  recalcAll();
}

function onRoomNameChange(rk, val) {
  if (rooms[rk]) rooms[rk].name = val.trim();
}

// ─── Item Management ──────────────────────────────────────────────────────────
let itemCounter = 0;

function addItem(rk, presetName, presetLFt, presetLIn, presetWFt, presetWIn, presetWood) {
  itemCounter++;
  const ik = 'item_' + itemCounter;
  if (!rooms[rk]) return;

  const lFt   = presetLFt  !== undefined ? presetLFt  : '';
  const lIn   = presetLIn  !== undefined ? presetLIn  : '';
  const wFt   = presetWFt  !== undefined ? presetWFt  : '';
  const wIn   = presetWIn  !== undefined ? presetWIn  : '';
  const wood  = presetWood || 'Laminates';
  const name  = presetName || '';

  const lDec = ftInToDecimal(lFt, lIn);
  const wDec = ftInToDecimal(wFt, wIn);
  const area  = parseFloat((lDec * wDec).toFixed(4));

  rooms[rk].items[ik] = {
    name, lengthFt: lFt, lengthIn: lIn, widthFt: wFt, widthIn: wIn,
    wood_type: wood, area
  };

  const tbody = document.getElementById('items_tbody_' + rk);
  if (!tbody) return;

  const tr = document.createElement('tr');
  tr.className = 'item-row';
  tr.id = 'item_row_' + ik;
  tr.innerHTML = `
    <td>
      <input type="text" class="form-control form-control-sm"
             id="item_name_${ik}"
             placeholder="e.g. Wardrobe"
             value="${escHtml(name)}"
             oninput="onItemField('${rk}','${ik}')"
             autocomplete="off">
    </td>
    <td>
      <div class="input-group input-group-sm">
        <input type="number" class="form-control text-center px-1"
               id="item_lft_${ik}" placeholder="0" min="0" max="999" step="1"
               value="${lFt}" oninput="onItemField('${rk}','${ik}')"
               style="max-width:52px" title="Feet">
        <span class="input-group-text px-1 small text-muted">ft</span>
        <input type="number" class="form-control text-center px-1"
               id="item_lin_${ik}" placeholder="0" min="0" max="11" step="1"
               value="${lIn}" oninput="onItemField('${rk}','${ik}')"
               style="max-width:52px" title="Inches (0–11)">
        <span class="input-group-text px-1 small text-muted">in</span>
      </div>
    </td>
    <td>
      <div class="input-group input-group-sm">
        <input type="number" class="form-control text-center px-1"
               id="item_wft_${ik}" placeholder="0" min="0" max="999" step="1"
               value="${wFt}" oninput="onItemField('${rk}','${ik}')"
               style="max-width:52px" title="Feet">
        <span class="input-group-text px-1 small text-muted">ft</span>
        <input type="number" class="form-control text-center px-1"
               id="item_win_${ik}" placeholder="0" min="0" max="11" step="1"
               value="${wIn}" oninput="onItemField('${rk}','${ik}')"
               style="max-width:52px" title="Inches (0–11)">
        <span class="input-group-text px-1 small text-muted">in</span>
      </div>
    </td>
    <td>
      <select class="form-select form-select-sm"
              id="item_wood_${ik}"
              onchange="onItemField('${rk}','${ik}')">
        ${buildWoodOptions(wood)}
      </select>
    </td>
    <td class="text-center">
      <span class="area-display fw-bold text-primary" id="item_area_${ik}">
        ${area > 0 ? area.toFixed(2) : '0.00'}
      </span>
    </td>
    <td class="text-center">
      <button type="button" class="btn btn-outline-danger btn-remove-item"
              onclick="removeItem('${rk}','${ik}')" title="Remove">
        <i class="bi bi-x-lg"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
  // Init autocomplete on item name input
  const itemNameEl = document.getElementById('item_name_' + ik);
  if (itemNameEl) initAutocomplete(itemNameEl, masterItems);

  if (area > 0) recalcAll();
}

function removeItem(rk, ik) {
  const row = document.getElementById('item_row_' + ik);
  if (row) {
    row.querySelectorAll('input').forEach(inp => { if (inp._acDropdown) inp._acDropdown.remove(); });
    row.remove();
  }
  if (rooms[rk] && rooms[rk].items) delete rooms[rk].items[ik];
  recalcAll();
}

function onItemField(rk, ik) {
  if (!rooms[rk] || !rooms[rk].items[ik]) return;

  const nameEl = document.getElementById('item_name_' + ik);
  const lFtEl  = document.getElementById('item_lft_'  + ik);
  const lInEl  = document.getElementById('item_lin_'  + ik);
  const wFtEl  = document.getElementById('item_wft_'  + ik);
  const wInEl  = document.getElementById('item_win_'  + ik);
  const woodEl = document.getElementById('item_wood_' + ik);
  const areaEl = document.getElementById('item_area_' + ik);

  // Clamp inches 0–11
  if (lInEl && parseInt(lInEl.value) > 11) lInEl.value = 11;
  if (wInEl && parseInt(wInEl.value) > 11) wInEl.value = 11;

  const lFt  = parseFloat(lFtEl?.value) || 0;
  const lIn  = parseFloat(lInEl?.value) || 0;
  const wFt  = parseFloat(wFtEl?.value) || 0;
  const wIn  = parseFloat(wInEl?.value) || 0;

  const lDec = ftInToDecimal(lFt, lIn);
  const wDec = ftInToDecimal(wFt, wIn);
  const area  = parseFloat((lDec * wDec).toFixed(4));

  rooms[rk].items[ik] = {
    name:      nameEl?.value.trim() || '',
    lengthFt:  lFt, lengthIn: lIn,
    widthFt:   wFt, widthIn:  wIn,
    wood_type: woodEl?.value || 'Laminates',
    area
  };

  if (areaEl) areaEl.textContent = area.toFixed(2);
  recalcAll();
}

// ─── Calculations ─────────────────────────────────────────────────────────────
function recalcAll() {
  const woodAreas = {};

  Object.entries(rooms).forEach(([rk, room]) => {
    let roomArea = 0;
    Object.values(room.items).forEach(item => {
      const a = item.area || 0;
      roomArea += a;
      woodAreas[item.wood_type] = (woodAreas[item.wood_type] || 0) + a;
    });
    const badge = document.getElementById('room_total_badge_' + rk);
    if (badge) badge.textContent = roomArea.toFixed(2) + ' sqft';
  });

  let grandTotal = 0;
  Object.entries(woodAreas).forEach(([wt, area]) => {
    grandTotal += area * (woodRates[wt] || 0);
  });

  renderSummary(woodAreas, grandTotal);

  const fmt = '₹' + grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const gtEl  = document.getElementById('grand-total-display');
  const gtMob = document.getElementById('grand-total-mobile');
  if (gtEl)  gtEl.textContent  = fmt;
  if (gtMob) gtMob.textContent = fmt;
}

function renderSummary(woodAreas, grandTotal) {
  const panel = document.getElementById('summary-content');
  if (!panel) return;
  const hasData = Object.values(woodAreas).some(a => a > 0);
  if (!hasData) {
    panel.innerHTML = '<p class="text-muted text-center small py-2">Add rooms and items to see cost breakdown.</p>';
    return;
  }
  const woodColors = {
    'Acrylic':   { bg:'#dbeafe', color:'#1e40af' },
    'Laminates': { bg:'#dcfce7', color:'#166534' },
    'Veneer':    { bg:'#ffedd5', color:'#9a3412' },
  };
  let html = '';
  Object.entries(woodAreas).forEach(([wt, area]) => {
    if (area <= 0) return;
    const rate     = woodRates[wt] || 0;
    const subtotal = area * rate;
    const c        = woodColors[wt] || { bg:'#f3f4f6', color:'#374151' };
    html += `
      <div class="summary-wood-row">
        <span class="summary-wood-label">
          <span class="badge me-1" style="background:${c.bg};color:${c.color}">${wt}</span>
        </span>
        <span class="text-muted small">${area.toFixed(2)} sqft</span>
        <span class="summary-wood-value">₹${subtotal.toLocaleString('en-IN',{minimumFractionDigits:0,maximumFractionDigits:0})}</span>
      </div>`;
  });
  panel.innerHTML = html;
}

// ─── Form Submission ───────────────────────────────────────────────────────────
function validateAndSubmit() {
  const nameEl   = document.getElementById('customer_name');
  const mobileEl = document.getElementById('mobile');
  let valid = true;

  [nameEl, mobileEl].forEach(el => {
    if (el && !el.value.trim()) { el.classList.add('is-invalid'); valid = false; }
    else if (el) el.classList.remove('is-invalid');
  });

  const roomsPayload = [];
  let hasItem = false;

  Object.entries(rooms).forEach(([rk, room]) => {
    const nameInput = document.getElementById('room_name_' + rk);
    const roomName  = nameInput ? nameInput.value.trim() : room.name;
    if (!roomName) return;

    const itemsPayload = [];
    Object.values(room.items).forEach(item => {
      const lDec = ftInToDecimal(item.lengthFt, item.lengthIn);
      const wDec = ftInToDecimal(item.widthFt, item.widthIn);
      if (!item.name || lDec <= 0 || wDec <= 0) return;
      itemsPayload.push({
        name:      item.name,
        length:    lDec,               // decimal feet stored in DB
        width:     wDec,               // decimal feet stored in DB
        wood_type: item.wood_type,
        area:      item.area || parseFloat((lDec * wDec).toFixed(4))
      });
      hasItem = true;
    });

    if (itemsPayload.length > 0) roomsPayload.push({ name: roomName, items: itemsPayload });
  });

  if (!hasItem) {
    showFormAlert('Please add at least one room with one complete item (name, length, width).', 'warning');
    valid = false;
  }

  if (!valid) return false;
  document.getElementById('rooms_data_field').value = JSON.stringify(roomsPayload);
  return true;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function buildWoodOptions(selected) {
  return ['Acrylic','Laminates','Veneer']
    .map(t => `<option value="${t}" ${t === selected ? 'selected' : ''}>${t}</option>`)
    .join('');
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function updateNoRoomsHint() {
  const hasRooms = Object.keys(rooms).length > 0;
  const hint = document.getElementById('no-rooms-hint');
  const addBtn = document.getElementById('add-room-btn-wrap');
  if (hint)   hint.style.display   = hasRooms ? 'none'  : 'block';
  if (addBtn) addBtn.style.display = hasRooms ? 'block' : 'none';
}

function showFormAlert(message, type) {
  const existing = document.getElementById('form-alert-dynamic');
  if (existing) existing.remove();
  const alert = document.createElement('div');
  alert.id = 'form-alert-dynamic';
  alert.className = `alert alert-${type || 'warning'} alert-dismissible fade show py-2 mt-2`;
  alert.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  const form = document.getElementById('projectForm');
  if (form) form.prepend(alert);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
