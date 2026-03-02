# Hanchuess 自定义卡片使用说明

## 安装步骤

1. 重启 Home Assistant
2. 清除浏览器缓存（Ctrl+Shift+R 或 Cmd+Shift+R）

## 添加卡片

### 方法1：通过界面添加

1. 进入仪表盘编辑模式
2. 点击"添加卡片"
3. 向下滚动找到"自定义: Hanchuess Card"
4. 配置实体ID

### 方法2：手动配置

在仪表盘配置文件中添加：

```yaml
type: custom:hanchuess-card
entity: sensor.zhuang_tai_2
```

## 使用方法

- 卡片显示设备名称和当前状态
- **点击卡片**会弹出对话框，显示所有详细属性：
  - 电池电量
  - 电池功率
  - 负载功率
  - 光伏功率
  - 电网功率
  - 工作模式
  - 设备序列号

## 注意事项

1. 如果卡片不显示，检查浏览器控制台是否有错误
2. 确保实体ID正确（sensor.zhuang_tai_2）
3. 首次加载可能需要强制刷新浏览器缓存

## 自定义样式

可以在卡片配置中添加自定义样式：

```yaml
type: custom:hanchuess-card
entity: sensor.zhuang_tai_2
card_mod:
  style: |
    ha-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }
```
