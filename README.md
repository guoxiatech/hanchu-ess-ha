# Hanchuess Home Assistant Integration

Home Assistant自定义集成，用于监控和控制Hanchuess设备。

## 功能特性

- 实时监控设备状态
- 显示设备版本、构建时间等信息
- 支持充电/放电控制
- 支持逆变器开关控制
- 支持多设备管理

## 安装方法

### 方法1：通过HACS安装（推荐）

1. 确保已安装[HACS](https://hacs.xyz/)
2. 在HACS中点击"集成"
3. 点击右上角菜单，选择"自定义存储库"
4. 添加此仓库URL：`https://github.com/你的用户名/hanchuess-ha`
5. 类别选择"Integration"
6. 搜索"Hanchuess"并安装
7. 重启Home Assistant

### 方法2：手动安装

1. 下载此仓库
2. 将`custom_components/device_monitor`文件夹复制到Home Assistant的`config/custom_components/`目录
3. 重启Home Assistant

## 配置

1. 进入"设置 → 设备与服务 → 添加集成"
2. 搜索"Hanchuess"
3. 输入以下信息：
   - 认证接口地址
   - 状态查询接口地址
   - API密钥
   - 设备ID
4. 点击提交完成配置

## 支持的实体

### 传感器
- 状态
- 版本号
- 构建时间
- Pod名称
- 服务名称
- 启动时间
- 当前时间

### 按钮
- 开启放电
- 开启充电

### 开关
- 逆变器开关

## 许可证

MIT License
