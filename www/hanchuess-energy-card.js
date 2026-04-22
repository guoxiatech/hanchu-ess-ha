// ===== Card Editor =====
class HanchuessEnergyCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({ entity: "", sn: "" }, config || {});
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;

    const entities = Object.keys(this._hass.states)
      .filter(eid => eid.startsWith("select.") && eid.includes("work_mode"));

    this.innerHTML = `
      <div style="padding: 16px;">
        <label style="font-weight:500;display:block;margin-bottom:8px;">设备</label>
        <select id="entity_select" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;">
          <option value="">请选择设备</option>
          ${entities.map(eid => {
            const state = this._hass.states[eid];
            const name = (state.attributes.friendly_name || eid).replace(" 工作模式", "");
            const selected = this._config.entity === eid ? "selected" : "";
            return `<option value="${eid}" ${selected}>${name}</option>`;
          }).join("")}
        </select>
      </div>
    `;

    this.querySelector("#entity_select").addEventListener("change", (e) => {
      const entityId = e.target.value;
      const state = this._hass.states[entityId];
      const sn = state && state.attributes ? (state.attributes.sn || "") : "";

      this._config = { ...this._config, entity: entityId, sn: sn };
      this.dispatchEvent(new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }));
    });
  }
}
customElements.define("hanchuess-energy-card-editor", HanchuessEnergyCardEditor);

// ===== Card =====
class HanchuessEnergyCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._rendered && this._config && this._config.entity) {
      this._render();
      this._rendered = true;
    }
    if (this._rendered) this._updateStatus();
  }

  setConfig(config) {
    this._config = Object.assign({ entity: "", sn: "" }, config || {});
    this._rendered = false;
    this._originalValues = {};
    this._dataLoaded = false;
  }

  static getConfigElement() {
    return document.createElement("hanchuess-energy-card-editor");
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states)
      .find(eid => eid.startsWith("select.") && eid.includes("work_mode")) || "";
    const state = hass.states[entity];
    const sn = state && state.attributes ? (state.attributes.sn || "") : "";
    return { entity, sn };
  }

  _render() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { padding: 16px; }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
        .title { font-size: 18px; font-weight: 500; }
        .title .sn { color: var(--primary-color); font-size: 14px; }
        .header-btns { display: flex; gap: 8px; }
        .btn {
          padding: 6px 16px; border: none; border-radius: 4px;
          font-size: 13px; cursor: pointer; white-space: nowrap;
        }
        .btn-load { background: var(--primary-color); color: white; }
        .btn-submit { background: var(--primary-color); color: white; }
        .btn:hover { opacity: 0.9; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .offline-banner {
          background: var(--error-color, #db4437); color: white; padding: 8px 12px;
          border-radius: 4px; margin-bottom: 12px; text-align: center; font-size: 14px;
        }
        .field { margin-bottom: 12px; }
        .field label { display: block; font-size: 13px; color: var(--secondary-text-color); margin-bottom: 4px; }
        .field select, .field input {
          width: 100%; padding: 8px; border: 1px solid var(--divider-color);
          border-radius: 4px; background: var(--card-background-color);
          color: var(--primary-text-color); font-size: 14px; box-sizing: border-box;
        }
        .field input::placeholder { color: var(--secondary-text-color); opacity: 0.6; }
        .time-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .time-row input { flex: 1; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; }
        .time-row span { color: var(--secondary-text-color); }
        .time-row .time-label { font-size: 13px; color: var(--secondary-text-color); min-width: 80px; }
        .icon-btn {
          background: none; border: none; cursor: pointer; font-size: 18px; padding: 4px;
          color: var(--secondary-text-color); line-height: 1;
        }
        .icon-btn:hover { color: var(--primary-text-color); }
        .icon-btn.add { color: var(--primary-color); font-size: 20px; }
        .icon-btn.del { color: var(--error-color, #db4437); }
        .dynamic-field { display: none; }
        .dynamic-field.visible { display: block; }
        .section-title { font-size: 14px; font-weight: 500; margin: 16px 0 8px; color: var(--primary-color); }
        .status { font-size: 12px; color: var(--secondary-text-color); margin-top: 8px; text-align: center; }
        .status.error { color: var(--error-color); }
        .status.success { color: var(--success-color, #4caf50); }
        .collapse-card { border: 1px solid var(--divider-color); border-radius: 6px; margin-bottom: 10px; overflow: hidden; }
        .collapse-header { display: flex; align-items: center; padding: 10px 12px; user-select: none; gap: 8px; }
        .collapse-arrow { font-size: 10px; transition: transform .2s; color: var(--secondary-text-color); cursor: pointer; }
        .collapse-arrow.open { transform: rotate(90deg); }
        .collapse-title { flex: 1; font-size: 14px; font-weight: 500; cursor: pointer; }
        .collapse-sw-label { font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
        .collapse-body { display: none; padding: 0 12px 12px; }
        .collapse-body.open { display: block; }
        .collapse-row { display: flex; align-items: center; margin-bottom: 8px; gap: 8px; }
        .collapse-row label { min-width: 80px; font-size: 13px; color: var(--secondary-text-color); white-space: nowrap; }
        .collapse-row label .req { color: var(--error-color, #db4437); }
        .collapse-row input, .collapse-row select { flex: 1; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); font-size: 14px; box-sizing: border-box; }
        .toggle { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .toggle .slider { position: absolute; inset: 0; background: var(--divider-color); border-radius: 22px; cursor: pointer; transition: .3s; }
        .toggle .slider::before { content: ''; position: absolute; width: 16px; height: 16px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: .3s; }
        .toggle input:checked + .slider { background: var(--primary-color); }
        .toggle input:checked + .slider::before { transform: translateX(18px); }
      </style>
      <ha-card>
        <div class="header">
          <div class="title">储能设置 <span id="device_sn" class="sn"></span></div>
          <div class="header-btns">
            <button class="btn btn-load" id="load_btn">获取数据</button>
            <button class="btn btn-submit" id="submit_btn">设定</button>
          </div>
        </div>
        <div id="offline_banner" class="offline-banner" style="display:none">设备离线，无法设置</div>

        <div class="field">
          <label>工作模式</label>
          <select id="work_mode"><option value="">请选择</option></select>
        </div>

        <div id="dynamic_fields"></div>

        <div class="status" id="status_msg"></div>
      </ha-card>
    `;

    this.shadowRoot.getElementById("work_mode").addEventListener("change", (e) => {
      this._toggleFields(e.target.value);
    });

    this.shadowRoot.getElementById("load_btn").addEventListener("click", () => {
      this._loadData();
    });

    this.shadowRoot.getElementById("submit_btn").addEventListener("click", () => {
      this._submit();
    });
  }

  _updateStatus() {
    if (!this._hass || !this._config || !this._config.entity) return;

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    const snEl = this.shadowRoot.getElementById("device_sn");
    if (snEl) snEl.textContent = this._config.sn || "";

    const isOnline = state.state !== "unavailable";
    const offlineBanner = this.shadowRoot.getElementById("offline_banner");
    const submitBtn = this.shadowRoot.getElementById("submit_btn");
    const loadBtn = this.shadowRoot.getElementById("load_btn");
    if (offlineBanner) offlineBanner.style.display = isOnline ? "none" : "block";
    if (submitBtn) submitBtn.disabled = !isOnline;
    if (loadBtn) loadBtn.disabled = !isOnline;

    const select = this.shadowRoot.getElementById("work_mode");
    if (!select) return;

    const options = state.attributes.options || [];
    if (select.options.length !== options.length + 1) {
      select.innerHTML = `<option value="">请选择</option>` +
        options.map(opt => `<option value="${opt}">${opt}</option>`).join("");
    }

    const fields = state.attributes.energy_fields || [];
    this._renderDynamicFields(fields);

    if (this._dataLoaded) {
      this._toggleFields(select.value);
    }
  }

  _renderDynamicFields(fields) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    if (!container) return;
    // Re-render if fields changed
    const fieldsKey = JSON.stringify(fields.map(f => f.code + f.type));
    if (container.dataset.renderedKey === fieldsKey) return;
    container.dataset.renderedKey = fieldsKey;
    console.log("[HANCHUESS] renderDynamicFields", fields.length, "fields", fields.map(f => f.code + ":" + f.type));

    let html = "";
    for (const field of fields) {
      const la = field.listener_code
        ? `data-listener-code="${field.listener_code}" data-listener-show="${field.listener_show}"`
        : "";
      const cls = field.hidden || field.listener_code ? "dynamic-field" : "dynamic-field visible";

      if (field.type === "1") {
        const min = field.min || "0", max = field.max || "99999";
        html += `<div class="${cls}" ${la} data-signal="${field.signal}"><div class="field"><label>${field.name}</label><input type="number" data-signal="${field.signal}" min="${min}" max="${max}" placeholder="[${min}, ${max}]"></div></div>`;
      }

      if (field.type === "6") {
        const sigs = (field.signal || "").split(",");
        const code = field.code || "";
        const gk = code.startsWith("chg_tim") ? "chg" : code.startsWith("dschg_tim") ? "dschg" : code;
        const idx = (code.match(/(\d)$/) || [,"1"])[1];
        html += `<div class="${cls}" ${la} data-signal="${field.signal}" data-time-group="${gk}" data-time-index="${idx}"><div class="time-row"><span class="time-label">${field.name}</span><input type="time" data-signal="${sigs[0]||""}"><span>-</span><input type="time" data-signal="${sigs[1]||""}"><button class="icon-btn del" data-action="del-time" data-group="${gk}" data-index="${idx}">🗑</button><button class="icon-btn add" data-action="add-time" data-group="${gk}" data-index="${idx}" style="display:none">+</button></div></div>`;
      }

      if (field.type === "82" || field.type === "83") {
        const children = field.children || [];
        const sig = field.signal;
        let switchHtml = "";
        let bodyHtml = "";
        for (const c of children) {
          const ci = c.index != null ? c.index : 0;
          if (c.type === "3") {
            const opts = (c.options||[]).map(o => `<option value="${o.value}">${o.name}</option>`).join("");
            bodyHtml += `<div class="collapse-row"><label><span class="req">*</span>${c.name}</label><select data-arr-signal="${sig}" data-arr-index="${ci}">${opts}</select></div>`;
          } else if (c.type === "5") {
            bodyHtml += `<div class="collapse-row"><label><span class="req">*</span>${c.name}</label><input type="time" data-arr-signal="${sig}" data-arr-index="${ci}" data-arr-fmt="time"></div>`;
          } else if (c.type === "1") {
            const mn = c.min||"0", mx = c.max||"99999";
            bodyHtml += `<div class="collapse-row"><label><span class="req">*</span>${c.name}</label><input type="number" data-arr-signal="${sig}" data-arr-index="${ci}" min="${mn}" max="${mx}" placeholder="[${mn}, ${mx}]"></div>`;
          }
        }
        // "是否应用" from FLAG_ENABLE_CYCLE, not from array
        switchHtml = `<span class="collapse-sw-label">是否应用</span><label class="toggle"><input type="checkbox" data-enable-signal="${field.code}" data-collapse-switch="${field.code}"><span class="slider"></span></label>`;
        html += `<div class="${cls}" ${la} data-signal="${sig}" data-collapse="${field.code}"><div class="collapse-card"><div class="collapse-header"><span class="collapse-arrow" data-arrow="${field.code}" data-toggle="${field.code}">▶</span><span class="collapse-title" data-toggle="${field.code}">${field.name}</span>${switchHtml}</div><div class="collapse-body" data-body="${field.code}">${bodyHtml}</div></div></div>`;
      }
    }

    container.innerHTML = html;

    container.onclick = (e) => {
      const btn = e.target.closest("[data-action]");
      if (btn) {
        const {action, group, index} = btn.dataset;
        if (action === "del-time") this._deleteTimeSlot(group, index);
        else if (action === "add-time") this._addTimeSlot(group, index);
        return;
      }
      const hdr = e.target.closest("[data-toggle]");
      if (hdr) {
        const code = hdr.dataset.toggle;
        const body = container.querySelector(`[data-body="${code}"]`);
        const arrow = container.querySelector(`[data-arrow="${code}"]`);
        if (body) body.classList.toggle("open");
        if (arrow) arrow.classList.toggle("open");
      }
    };

    container.onchange = (e) => {
      const sw = e.target.closest("[data-collapse-switch]");
      if (sw) {
        const code = sw.dataset.collapseSwitch;
        const body = container.querySelector(`[data-body="${code}"]`);
        const arrow = container.querySelector(`[data-arrow="${code}"]`);
        if (sw.checked) {
          if (body) body.classList.add("open");
          if (arrow) arrow.classList.add("open");
        } else {
          if (body) body.classList.remove("open");
          if (arrow) arrow.classList.remove("open");
        }
      }
    };
  }

  _deleteTimeSlot(group, index) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    const allSlots = Array.from(container.querySelectorAll(`[data-time-group="${group}"]`));
    
    // Collect all visible slots' values
    const visibleValues = [];
    allSlots.forEach(slot => {
      if (slot.classList.contains("visible") && slot.dataset.timeHidden !== "true") {
        const inputs = slot.querySelectorAll("input[type='time']");
        visibleValues.push({
          start: inputs[0] ? inputs[0].value : "",
          end: inputs[1] ? inputs[1].value : "",
        });
      }
    });

    // Remove the deleted index (0-based from visible list)
    const delIdx = parseInt(index) - 1;
    // Find which visible slot corresponds to this index
    let visibleIdx = 0;
    for (let i = 0; i < allSlots.length; i++) {
      if (allSlots[i].dataset.timeIndex === index && allSlots[i].classList.contains("visible")) {
        // Find position in visible list
        visibleIdx = 0;
        for (let j = 0; j < i; j++) {
          if (allSlots[j].classList.contains("visible") && allSlots[j].dataset.timeHidden !== "true") {
            visibleIdx++;
          }
        }
        break;
      }
    }
    visibleValues.splice(visibleIdx, 1);

    // Redistribute values to slots 1, 2, 3
    allSlots.forEach((slot, i) => {
      const inputs = slot.querySelectorAll("input[type='time']");
      if (i < visibleValues.length) {
        inputs[0].value = visibleValues[i].start;
        inputs[1].value = visibleValues[i].end;
        slot.classList.add("visible");
        delete slot.dataset.timeHidden;
      } else {
        inputs[0].value = "00:00";
        inputs[1].value = "00:00";
        slot.classList.remove("visible");
        slot.dataset.timeHidden = "true";
      }
    });

    this._updateTimeButtons(group);
  }

  _addTimeSlot(group, index) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    // Find next hidden time slot in this group
    const allSlots = container.querySelectorAll(`[data-time-group="${group}"]`);
    for (const slot of allSlots) {
      if (slot.dataset.timeHidden === "true" || !slot.classList.contains("visible")) {
        slot.classList.add("visible");
        delete slot.dataset.timeHidden;
        // Clear values for new slot
        const inputs = slot.querySelectorAll("input[type='time']");
        inputs.forEach(inp => { inp.value = ""; });
        break;
      }
    }

    this._updateTimeButtons(group);
  }

  _updateTimeButtons(group) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    const allSlots = container.querySelectorAll(`[data-time-group="${group}"]`);

    const visibleSlots = [];
    const hiddenSlots = [];
    allSlots.forEach(slot => {
      if (slot.classList.contains("visible") && slot.dataset.timeHidden !== "true") {
        visibleSlots.push(slot);
      } else {
        hiddenSlots.push(slot);
      }
    });

    allSlots.forEach(slot => {
      const addBtn = slot.querySelector("[data-action='add-time']");
      const delBtn = slot.querySelector("[data-action='del-time']");
      if (addBtn) addBtn.style.display = "none";
      if (delBtn) delBtn.style.display = "";
    });

    // Only 1 visible: hide its delete button
    if (visibleSlots.length <= 1) {
      visibleSlots.forEach(slot => {
        const delBtn = slot.querySelector("[data-action='del-time']");
        if (delBtn) delBtn.style.display = "none";
      });
    }

    // Show add button on last visible slot if there are hidden slots
    if (visibleSlots.length > 0 && hiddenSlots.length > 0) {
      const lastVisible = visibleSlots[visibleSlots.length - 1];
      const addBtn = lastVisible.querySelector("[data-action='add-time']");
      if (addBtn) addBtn.style.display = "";
    }
  }

  _toggleFields(currentWorkModeLabel) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    if (!container) return;

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    const wmOptions = state.attributes.work_mode_options || [];
    let currentValue = "";
    for (const opt of wmOptions) {
      if (opt.label === currentWorkModeLabel) {
        currentValue = String(opt.value);
        break;
      }
    }

    // Determine work mode item codes for listener matching
    const wmCodes = new Set(["work_mode"]);
    for (const opt of wmOptions) {
      if (opt.signal) wmCodes.add(opt.signal);
    }
    // Also add WORK_MODE_CMB as it's used as listener code
    wmCodes.add("WORK_MODE_CMB");

    const allFields = this.shadowRoot.querySelectorAll(".dynamic-field");
    allFields.forEach(el => {
      const listenerCode = el.dataset.listenerCode;
      const listenerShow = el.dataset.listenerShow;

      if (!listenerCode) {
        el.classList.add("visible");
        return;
      }

      if (wmCodes.has(listenerCode)) {
        const showValues = (listenerShow || "").split(",");
        if (showValues.includes(currentValue)) {
          if (el.dataset.timeHidden !== "true") {
            el.classList.add("visible");
          }
        } else {
          el.classList.remove("visible");
        }
      }
    });

    // Update add/delete buttons for time groups
    const groups = new Set();
    container.querySelectorAll("[data-time-group]").forEach(el => {
      groups.add(el.dataset.timeGroup);
    });
    groups.forEach(g => this._updateTimeButtons(g));
  }

  _signalToTime(val) {
    const totalSeconds = Number(val) || 0;
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return String(hours).padStart(2, "0") + ":" + String(minutes).padStart(2, "0");
  }

  _timeToSignal(timeStr) {
    const parts = timeStr.split(":");
    const hours = Number(parts[0]) || 0;
    const minutes = Number(parts[1]) || 0;
    return String(hours * 3600 + minutes * 60);
  }

  async _loadData() {
    const loadBtn = this.shadowRoot.getElementById("load_btn");
    const statusMsg = this.shadowRoot.getElementById("status_msg");
    loadBtn.disabled = true;
    statusMsg.textContent = "加载中...";
    statusMsg.className = "status";

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    const keys = [];
    const fields = state.attributes.energy_fields || [];
    for (const field of fields) {
      if (field.signal) {
        field.signal.split(",").forEach(s => { if (s) keys.push(s); });
      }
    }

    const wmOptions = state.attributes.work_mode_options || [];
    if (wmOptions.length > 0) {
      keys.push(wmOptions[0].signal || "WORK_MODE_CMB");
    }
    // Only request FLAG_ENABLE_CYCLE if there are collapse (82/83) fields
    const hasCollapse = fields.some(f => f.type === "82" || f.type === "83");
    if (hasCollapse && !keys.includes("FLAG_ENABLE_CYCLE")) keys.push("FLAG_ENABLE_CYCLE");

    try {
      const result = await this._hass.callWS({
        type: "hanchuess/iot_get",
        sn: this._config.sn,
        dev_type: "2",
        keys: keys,
      });

      this._originalValues = { ...result };
      this._dataLoaded = true;

      // Fill work mode
      const wmSignal = wmOptions.length > 0 ? (wmOptions[0].signal || "WORK_MODE_CMB") : "WORK_MODE_CMB";
      const wmValue = result[wmSignal];
      if (wmValue !== undefined) {
        const select = this.shadowRoot.getElementById("work_mode");
        for (const opt of wmOptions) {
          if (String(opt.value) === String(wmValue)) {
            select.value = opt.label;
            break;
          }
        }
      }

      // Fill dynamic fields
      const container = this.shadowRoot.getElementById("dynamic_fields");
      const inputs = container.querySelectorAll("input[data-signal]");
      inputs.forEach(input => {
        const signal = input.dataset.signal;
        if (signal && result[signal] !== undefined) {
          if (input.type === "time") {
            const v = String(result[signal]);
            if (v.includes(":")) {
              input.value = v;
            } else if (v.length <= 4) {
              const s = v.padStart(4, "0");
              input.value = s.slice(0,2) + ":" + s.slice(2,4);
            } else {
              input.value = this._signalToTime(result[signal]);
            }
          } else if (input.type === "checkbox") {
            input.checked = String(result[signal]) === (input.dataset.on || "1");
          } else if (signal === "MIN_THRESH_CHG_DUR") {
            input.value = Math.round(Number(result[signal]) / 60);
          } else {
            input.value = result[signal];
          }
        }
      });

      // Fill selects in collapse cards
      container.querySelectorAll("select[data-signal]").forEach(sel => {
        const signal = sel.dataset.signal;
        if (signal && result[signal] !== undefined) sel.value = String(result[signal]);
      });

      // Fill collapse card array fields (82/83)
      container.querySelectorAll("[data-arr-signal]").forEach(el => {
        const sig = el.dataset.arrSignal;
        const idx = parseInt(el.dataset.arrIndex);
        if (!sig || isNaN(idx) || result[sig] === undefined) return;
        let arr;
        try { arr = JSON.parse(result[sig]); } catch { return; }
        if (!Array.isArray(arr) || idx >= arr.length) return;
        const val = arr[idx];
        if (el.type === "checkbox") {
          el.checked = String(val) === (el.dataset.on || "1");
        } else if (el.type === "time" || el.dataset.arrFmt === "time") {
          const s = String(val).padStart(4, "0");
          el.value = s.slice(0,2) + ":" + s.slice(2,4);
        } else if (el.tagName === "SELECT") {
          el.value = String(val);
        } else {
          el.value = String(val).replace(/"/g, "");
        }
      });

      // Fill collapse card expand state from FLAG_ENABLE_CYCLE
      let enableCycle = [];
      try { enableCycle = JSON.parse(result["FLAG_ENABLE_CYCLE"] || "[]"); } catch {}
      container.querySelectorAll("[data-enable-signal]").forEach(sw => {
        const code = sw.dataset.enableSignal;
        // TCT_CHG0->0, TCT_CHG1->1, TCT_CHG2->2, TCT_DISCHG0->3...
        const m = code.match(/TCT_(CHG|DISCHG)(\d)/);
        if (m && enableCycle.length) {
          const ci = m[1] === "CHG" ? Number(m[2]) : 3 + Number(m[2]);
          sw.checked = enableCycle[ci] === 1;
        }
      });

      // Handle collapse card expand state based on switch
      container.querySelectorAll("[data-collapse-switch]").forEach(sw => {
        const code = sw.dataset.collapseSwitch;
        const body = container.querySelector(`[data-body="${code}"]`);
        const arrow = container.querySelector(`[data-arrow="${code}"]`);
        if (sw.checked) {
          if (body) body.classList.add("open");
          if (arrow) arrow.classList.add("open");
        } else {
          if (body) body.classList.remove("open");
          if (arrow) arrow.classList.remove("open");
        }
      });

      // Handle time slot visibility
      const timeSlots = container.querySelectorAll("[data-time-group]");
      timeSlots.forEach(slot => {
        const timeInputs = slot.querySelectorAll("input[type='time']");
        const allZero = Array.from(timeInputs).every(inp => inp.value === "00:00");
        if (allZero) {
          slot.classList.remove("visible");
          slot.dataset.timeHidden = "true";
        } else {
          delete slot.dataset.timeHidden;
        }
      });

      // Toggle fields based on work mode and update buttons
      const select = this.shadowRoot.getElementById("work_mode");
      this._toggleFields(select.value);

      statusMsg.textContent = "数据加载成功";
      statusMsg.className = "status success";
    } catch (err) {
      statusMsg.textContent = "加载失败: " + err.message;
      statusMsg.className = "status error";
    }

    loadBtn.disabled = false;
    setTimeout(() => { statusMsg.textContent = ""; }, 3000);
  }

  async _submit() {
    const submitBtn = this.shadowRoot.getElementById("submit_btn");
    const statusMsg = this.shadowRoot.getElementById("status_msg");
    submitBtn.disabled = true;
    statusMsg.textContent = "提交中...";
    statusMsg.className = "status";

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    const sn = this._config.sn;
    const valueMap = {};

    // Check work mode change
    const wmOptions = state.attributes.work_mode_options || [];
    const wmSignal = wmOptions.length > 0 ? (wmOptions[0].signal || "WORK_MODE_CMB") : "WORK_MODE_CMB";
    const selectEl = this.shadowRoot.getElementById("work_mode");
    const selectedLabel = selectEl ? selectEl.value : "";

    if (selectedLabel) {
      for (const opt of wmOptions) {
        if (opt.label === selectedLabel) {
          const newVal = String(opt.value);
          if (newVal !== String(this._originalValues[wmSignal] || "")) {
            valueMap[wmSignal] = newVal;
          }
          break;
        }
      }
    }

    // Check visible field changes
    const container = this.shadowRoot.getElementById("dynamic_fields");
    const visibleFields = container.querySelectorAll(".dynamic-field.visible");
    const changedSignals = new Set();

    // First pass: find changed signals (for non-collapse fields)
    visibleFields.forEach(fieldEl => {
      if (fieldEl.dataset.collapse) return;
      const inputs = fieldEl.querySelectorAll("input[data-signal], select[data-signal]");
      inputs.forEach(input => {
        const signal = input.dataset.signal;
        if (!signal) return;
        let newVal;
        if (input.type === "time") {
          newVal = this._timeToSignal(input.value || "00:00");
        } else if (input.type === "checkbox") {
          newVal = input.checked ? (input.dataset.on || "1") : (input.dataset.off || "0");
        } else if (signal === "MIN_THRESH_CHG_DUR") {
          newVal = String(Number(input.value) * 60);
        } else {
          newVal = input.value;
        }
        const origVal = String(this._originalValues[signal] || "");
        if (newVal !== origVal) changedSignals.add(signal);
      });
    });

    // Also check deleted time slots (hidden but were visible before)
    const allTimeSlots = container.querySelectorAll("[data-time-group]");
    allTimeSlots.forEach(slot => {
      if (slot.dataset.timeHidden === "true") {
        const inputs = slot.querySelectorAll("input[type='time']");
        inputs.forEach(input => {
          const signal = input.dataset.signal;
          if (signal && this._originalValues[signal] && String(this._originalValues[signal]) !== "0") {
            changedSignals.add(signal);
          }
        });
      }
    });

    // Second pass: collect non-collapse values
    visibleFields.forEach(fieldEl => {
      if (fieldEl.dataset.collapse) return;
      const inputs = fieldEl.querySelectorAll("input[data-signal], select[data-signal]");
      const fieldSignals = Array.from(inputs).map(i => i.dataset.signal).filter(Boolean);
      const hasChange = fieldSignals.some(s => changedSignals.has(s));
      if (!hasChange) return;
      inputs.forEach(input => {
        const signal = input.dataset.signal;
        if (!signal) return;
        if (input.type === "time") {
          valueMap[signal] = this._timeToSignal(input.value || "00:00");
        } else if (signal === "MIN_THRESH_CHG_DUR") {
          valueMap[signal] = String(Number(input.value) * 60);
        } else {
          valueMap[signal] = input.value;
        }
      });
    });

    // Collect collapse card (82/83) array values
    const collapseFields = container.querySelectorAll(".dynamic-field.visible[data-collapse]");
    collapseFields.forEach(fieldEl => {
      const sig = fieldEl.dataset.signal;
      if (!sig) return;
      const arrEls = fieldEl.querySelectorAll("[data-arr-signal]");
      // Rebuild array from current UI values
      let origArr;
      try { origArr = JSON.parse(this._originalValues[sig] || "[]"); } catch { origArr = []; }
      const newArr = [...origArr];
      arrEls.forEach(el => {
        const idx = parseInt(el.dataset.arrIndex);
        if (isNaN(idx)) return;
        let val;
        if (el.type === "checkbox") {
          val = el.checked ? Number(el.dataset.on || 1) : Number(el.dataset.off || 0);
        } else if (el.type === "time" || el.dataset.arrFmt === "time") {
          val = (el.value || "00:00").replace(":", "");
        } else if (el.type === "number") {
          val = el.value;
        } else {
          val = el.tagName === "SELECT" ? Number(el.value) : el.value;
        }
        newArr[idx] = val;
      });
      const newStr = JSON.stringify(newArr);
      const origStr = JSON.stringify(origArr);
      if (newStr !== origStr) {
        valueMap[sig] = newStr;
      }
    });

    // Collect FLAG_ENABLE_CYCLE from all collapse switches
    this._collectEnableCycle(container, valueMap);

    // Collect deleted time slots (send 0)
    allTimeSlots.forEach(slot => {
      if (slot.dataset.timeHidden === "true") {
        const inputs = slot.querySelectorAll("input[type='time']");
        const hasOrig = Array.from(inputs).some(inp => {
          const sig = inp.dataset.signal;
          return sig && this._originalValues[sig] && String(this._originalValues[sig]) !== "0";
        });
        if (hasOrig) {
          inputs.forEach(inp => {
            const sig = inp.dataset.signal;
            if (sig) valueMap[sig] = "0";
          });
        }
      }
    });

    if (Object.keys(valueMap).length === 0) {
      statusMsg.textContent = "没有修改";
      statusMsg.className = "status";
      submitBtn.disabled = false;
      setTimeout(() => { statusMsg.textContent = ""; }, 2000);
      return;
    }

    try {
      await this._hass.callWS({
        type: "hanchuess/iot_set",
        sn: sn,
        dev_type: "2",
        value: valueMap,
      });

      Object.assign(this._originalValues, valueMap);

      statusMsg.textContent = "设定成功";
      statusMsg.className = "status success";
    } catch (err) {
      const errMsg = err.message || err.error || "未知错误";
      statusMsg.textContent = "设定失败: " + errMsg;
      statusMsg.className = "status error";
    }

    submitBtn.disabled = false;
    setTimeout(() => { statusMsg.textContent = ""; }, 3000);
  }

  _collectEnableCycle(container, valueMap) {
    if (!this._originalValues["FLAG_ENABLE_CYCLE"]) return;
    let origCycle;
    try { origCycle = JSON.parse(this._originalValues["FLAG_ENABLE_CYCLE"]); } catch { return; }
    const newCycle = [...origCycle];
    container.querySelectorAll("[data-enable-signal]").forEach(sw => {
      const code = sw.dataset.enableSignal;
      const m = code.match(/TCT_(CHG|DISCHG)(\d)/);
      if (!m) return;
      const ci = m[1] === "CHG" ? Number(m[2]) : 3 + Number(m[2]);
      newCycle[ci] = sw.checked ? 1 : 0;
    });
    const newStr = JSON.stringify(newCycle);
    if (newStr !== JSON.stringify(origCycle)) valueMap["FLAG_ENABLE_CYCLE"] = newStr;
  }

  getCardSize() {
    return 4;
  }
}
customElements.define("hanchuess-energy-card", HanchuessEnergyCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "hanchuess-energy-card",
  name: "Hanchuess 储能设置",
  description: "Hanchuess 逆变器储能设置卡片",
});
