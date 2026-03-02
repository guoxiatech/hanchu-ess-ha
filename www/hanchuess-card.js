class HanchuessCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('请指定 entity');
    }
    this.config = config;
    
    if (!this.content) {
      this.innerHTML = `
        <ha-card>
          <div class="card-content" style="cursor: pointer;">
            <div class="state-header">
              <span class="name"></span>
              <span class="state"></span>
            </div>
          </div>
        </ha-card>
      `;
      this.content = this.querySelector('.card-content');
      this.content.addEventListener('click', () => this.showDialog());
    }
  }

  set hass(hass) {
    this._hass = hass;
    const entityId = this.config.entity;
    const state = hass.states[entityId];
    
    if (!state) return;
    
    const nameEl = this.querySelector('.name');
    const stateEl = this.querySelector('.state');
    
    nameEl.textContent = state.attributes.friendly_name || entityId;
    stateEl.textContent = state.state;
  }

  showDialog() {
    const entityId = this.config.entity;
    const state = this._hass.states[entityId];
    
    if (!state) return;
    
    const attributes = state.attributes;
    
    let content = `
      <style>
        .dialog-content {
          padding: 20px;
        }
        .attr-table {
          width: 100%;
          border-collapse: collapse;
        }
        .attr-table td {
          padding: 8px;
          border-bottom: 1px solid var(--divider-color);
        }
        .attr-table td:first-child {
          font-weight: 500;
          color: var(--secondary-text-color);
          width: 40%;
        }
        .state-value {
          font-size: 24px;
          font-weight: bold;
          margin-bottom: 20px;
          color: var(--primary-text-color);
        }
      </style>
      <div class="dialog-content">
        <div class="state-value">状态: ${state.state}</div>
        <table class="attr-table">
    `;
    
    // 添加所有属性
    for (const [key, value] of Object.entries(attributes)) {
      if (key !== 'friendly_name' && key !== 'icon') {
        content += `
          <tr>
            <td>${key}</td>
            <td>${value}</td>
          </tr>
        `;
      }
    }
    
    content += `
        </table>
      </div>
    `;
    
    const dialog = document.createElement('ha-dialog');
    dialog.heading = attributes.friendly_name || entityId;
    dialog.innerHTML = content;
    
    const closeDialog = () => {
      document.body.removeChild(dialog);
    };
    
    dialog.addEventListener('closed', closeDialog);
    document.body.appendChild(dialog);
    
    // 打开对话框
    setTimeout(() => {
      dialog.open = true;
    }, 0);
  }

  getCardSize() {
    return 1;
  }
}

customElements.define('hanchuess-card', HanchuessCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'hanchuess-card',
  name: 'Hanchuess Card',
  description: '显示 Hanchuess 设备信息的自定义卡片'
});
