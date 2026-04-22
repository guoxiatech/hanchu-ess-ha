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
    if (this._rendered) this._updateValues();
  }

  setConfig(config) {
    this._config = Object.assign({ entity: "", sn: "" }, config || {});
    this._rendered = false;
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
        .title { font-size: 18px; font-weight: 500; margin-bottom: 16px; }
        .title .sn { color: var(--primary-color); }
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
        .time-group { display: flex; align-items: center; gap: 8px; }
        .time-group input { flex: 1; }
        .time-group span { color: var(--secondary-text-color); }
        .dynamic-field { display: none; }
        .dynamic-field.visible { display: block; }
        .section-title { font-size: 14px; font-weight: 500; margin: 16px 0 8px; color: var(--primary-color); }
        .submit-btn {
          width: 100%; padding: 10px; margin-top: 16px; border: none; border-radius: 4px;
          background: var(--primary-color); color: white; font-size: 14px; cursor: pointer;
        }
        .submit-btn:hover { opacity: 0.9; }
        .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .status { font-size: 12px; color: var(--secondary-text-color); margin-top: 8px; text-align: center; }
        .status.error { color: var(--error-color); }
        .status.success { color: var(--success-color, #4caf50); }
      </style>
      <ha-card>
        <div class="title">储能设置 - <span id="device_sn" class="sn"></span></div>
        <div id="offline_banner" class="offline-banner" style="display:none">设备离线，无法设置</div>

        <div class="field">
          <label>工作模式</label>
          <select id="work_mode"></select>
        </div>

        <div id="dynamic_fields"></div>

        <button class="submit-btn" id="submit_btn">提交</button>
        <div class="status" id="status_msg"></div>
      </ha-card>
    `;

    this.shadowRoot.getElementById("work_mode").addEventListener("change", (e) => {
      this._toggleFields(e.target.value);
    });

    this.shadowRoot.getElementById("submit_btn").addEventListener("click", () => {
      this._submit();
    });
  }

  _updateValues() {
    if (!this._hass || !this._config || !this._config.entity) return;

    const state = this._hass.states[this._config.entity];
    if (!state) return;

    const snEl = this.shadowRoot.getElementById("device_sn");
    if (snEl) snEl.textContent = this._config.sn || "";

    const isOnline = state.state !== "unavailable";
    const offlineBanner = this.shadowRoot.getElementById("offline_banner");
    const submitBtn = this.shadowRoot.getElementById("submit_btn");
    const workModeSelect = this.shadowRoot.getElementById("work_mode");
    if (offlineBanner) offlineBanner.style.display = isOnline ? "none" : "block";
    if (submitBtn) submitBtn.disabled = !isOnline;
    if (workModeSelect) workModeSelect.disabled = !isOnline;

    const select = this.shadowRoot.getElementById("work_mode");
    if (!select) return;

    const options = state.attributes.options || [];
    const current = state.state;

    if (select.options.length !== options.length) {
      select.innerHTML = options.map(opt =>
        `<option value="${opt}" ${opt === current ? "selected" : ""}>${opt}</option>`
      ).join("");
    } else {
      select.value = current;
    }

    const fields = state.attributes.energy_fields || [];
    this._renderDynamicFields(fields);
    this._toggleFields(current);
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
              <input type="number" data-signal="${field.signal}" min="${min}" max="${max}" value="${min}">
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
                <input type="time" data-signal="${startSignal}" value="00:00">
                <span>—</span>
                <input type="time" data-signal="${endSignal}" value="00:00">
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

    // Get current work mode numeric value from work_mode_options
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

  _timeToSignal(timeStr) {
    return timeStr.replace(":", "");
  }

  async _submit() {
    const btn = this.shadowRoot.getElementById("submit_btn");
    const statusMsg = this.shadowRoot.getElementById("status_msg");
    btn.disabled = true;
    statusMsg.textContent = "提交中...";
    statusMsg.className = "status";

    const entityId = this._config.entity;
    const sn = this._config.sn;
    const workModeLabel = this.shadowRoot.getElementById("work_mode").value;

    const state = this._hass.states[entityId];
    if (!state) return;

    // Find work mode signal and value
    const wmOptions = state.attributes.work_mode_options || [];
    let wmSignal = "WORK_MODE_CMB";
    let wmValue = "";
    for (const opt of wmOptions) {
      if (opt.label === workModeLabel) {
        wmValue = String(opt.value);
        wmSignal = opt.signal || "WORK_MODE_CMB";
        break;
      }
    }

    try {
      // Build valueMap with work mode + all visible fields
      const valueMap = {};
      valueMap[wmSignal] = wmValue;

      const container = this.shadowRoot.getElementById("dynamic_fields");
      const visibleFields = container.querySelectorAll(".dynamic-field.visible");

      visibleFields.forEach(fieldEl => {
        const inputs = fieldEl.querySelectorAll("input");
        inputs.forEach(input => {
          const signal = input.dataset.signal;
          if (signal) {
            if (input.type === "time") {
              valueMap[signal] = this._timeToSignal(input.value);
            } else {
              valueMap[signal] = input.value;
            }
          }
        });
      });

      await this._hass.callService("hanchuess", "device_control", {
        sn: sn,
        value_map: valueMap,
      });

      statusMsg.textContent = "提交成功";
      statusMsg.className = "status success";
    } catch (err) {
      statusMsg.textContent = "提交失败: " + err.message;
      statusMsg.className = "status error";
    }

    btn.disabled = false;
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
