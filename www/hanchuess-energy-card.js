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
        .time-group { display: flex; align-items: center; gap: 8px; }
        .time-group input { flex: 1; }
        .time-group span { color: var(--secondary-text-color); }
        .dynamic-field { display: none; }
        .dynamic-field.visible { display: block; }
        .section-title { font-size: 14px; font-weight: 500; margin: 16px 0 8px; color: var(--primary-color); }
        .status { font-size: 12px; color: var(--secondary-text-color); margin-top: 8px; text-align: center; }
        .status.error { color: var(--error-color); }
        .status.success { color: var(--success-color, #4caf50); }
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

    // Populate work mode options (without selecting value)
    const select = this.shadowRoot.getElementById("work_mode");
    if (!select) return;

    const options = state.attributes.options || [];
    if (select.options.length !== options.length + 1) {
      select.innerHTML = `<option value="">请选择</option>` +
        options.map(opt => `<option value="${opt}">${opt}</option>`).join("");
    }

    // Render dynamic fields
    const fields = state.attributes.energy_fields || [];
    this._renderDynamicFields(fields);

    // If data loaded, keep current values and toggle
    if (this._dataLoaded) {
      this._toggleFields(select.value);
    }
  }

  _renderDynamicFields(fields) {
    const container = this.shadowRoot.getElementById("dynamic_fields");
    if (!container || container.dataset.rendered === "true") return;

    let html = "";
    for (const field of fields) {
      const listenerAttr = field.listener_code
        ? `data-listener-code="${field.listener_code}" data-listener-show="${field.listener_show}"`
        : "";
      const hiddenClass = field.hidden || field.listener_code ? "dynamic-field" : "dynamic-field visible";

      if (field.type === "1") {
        const min = field.min || "0";
        const max = field.max || "99999";
        html += `
          <div class="${hiddenClass}" ${listenerAttr} data-signal="${field.signal}">
            <div class="field">
              <label>${field.name}</label>
              <input type="number" data-signal="${field.signal}" min="${min}" max="${max}" placeholder="[${min}, ${max}]">
            </div>
          </div>
        `;
      }

      if (field.type === "6") {
        const signals = (field.signal || "").split(",");
        const startSignal = signals[0] || "";
        const endSignal = signals[1] || "";
        html += `
          <div class="${hiddenClass}" ${listenerAttr} data-signal="${field.signal}">
            <div class="section-title">${field.name}</div>
            <div class="field">
              <div class="time-group">
                <input type="time" data-signal="${startSignal}" value="">
                <span>—</span>
                <input type="time" data-signal="${endSignal}" value="">
              </div>
            </div>
          </div>
        `;
      }
    }

    container.innerHTML = html;
    container.dataset.rendered = "true";
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

    const allFields = this.shadowRoot.querySelectorAll(".dynamic-field");
    allFields.forEach(el => {
      const listenerCode = el.dataset.listenerCode;
      const listenerShow = el.dataset.listenerShow;

      if (!listenerCode) {
        el.classList.add("visible");
        return;
      }

      if (listenerCode === "work_mode") {
        const showValues = (listenerShow || "").split(",");
        if (showValues.includes(currentValue)) {
          el.classList.add("visible");
        } else {
          el.classList.remove("visible");
        }
      }
    });
  }

  _signalToTime(val) {
    // "1100" → "11:00", "0" → "00:00"
    const s = String(val).padStart(4, "0");
    return s.slice(0, 2) + ":" + s.slice(2, 4);
  }

  _timeToSignal(timeStr) {
    return timeStr.replace(":", "");
  }

  async _loadData() {
    const loadBtn = this.shadowRoot.getElementById("load_btn");
    const statusMsg = this.shadowRoot.getElementById("status_msg");
    loadBtn.disabled = true;
    statusMsg.textContent = "加载中...";
    statusMsg.className = "status";

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    // Collect all signal keys from dynamic fields
    const keys = [];
    const fields = state.attributes.energy_fields || [];
    for (const field of fields) {
      if (field.signal) {
        const signals = field.signal.split(",");
        signals.forEach(s => { if (s) keys.push(s); });
      }
    }

    // Add work mode signal
    const wmOptions = state.attributes.work_mode_options || [];
    if (wmOptions.length > 0) {
      keys.push(wmOptions[0].signal || "WORK_MODE_CMB");
    }

    try {
      const result = await this._hass.callWS({
        type: "hanchuess/iot_get",
        sn: this._config.sn,
        dev_type: "2",
        keys: keys,
      });

      // Store original values for change detection
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
            this._toggleFields(opt.label);
            break;
          }
        }
      }

      // Fill dynamic fields
      const container = this.shadowRoot.getElementById("dynamic_fields");
      const inputs = container.querySelectorAll("input");
      inputs.forEach(input => {
        const signal = input.dataset.signal;
        if (signal && result[signal] !== undefined) {
          if (input.type === "time") {
            input.value = this._signalToTime(result[signal]);
          } else if (signal === "MIN_THRESH_CHG_DUR") {
            input.value = Math.round(Number(result[signal]) / 60);
          } else {
            input.value = result[signal];
          }
        }
      });

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
    visibleFields.forEach(fieldEl => {
      const inputs = fieldEl.querySelectorAll("input");
      inputs.forEach(input => {
        const signal = input.dataset.signal;
        if (!signal) return;

        let newVal;
        if (input.type === "time") {
          newVal = this._timeToSignal(input.value);
        } else if (signal === "MIN_THRESH_CHG_DUR") {
          newVal = String(Number(input.value) * 60);
        } else {
          newVal = input.value;
        }

        const origVal = String(this._originalValues[signal] || "");
        if (newVal !== origVal) {
          valueMap[signal] = newVal;
        }
      });
    });

    if (Object.keys(valueMap).length === 0) {
      statusMsg.textContent = "没有修改";
      statusMsg.className = "status";
      submitBtn.disabled = false;
      setTimeout(() => { statusMsg.textContent = ""; }, 2000);
      return;
    }

    try {
      const result = await this._hass.callWS({
        type: "hanchuess/iot_set",
        sn: sn,
        dev_type: "2",
        value: valueMap,
      });

      // Update original values
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
