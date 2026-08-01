# Google Cloud 设置指南：OAuth Client ID

这份文档记录 `dashboard/` 里 Google 登录（Sign in with Google）和读取 Google Drive 文件所需要的凭证——**OAuth 2.0 Client ID**——怎么从零开始建。

> 涉及的 env 变量（对应 `dashboard/.env.example`）：
> ```
> VITE_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
> ```

---

## 0. 前置：确认/创建 Google Cloud 项目

1. 打开 https://console.cloud.google.com/
2. 页面顶部左侧的项目下拉框——确认选中的是你要用的项目（或者点 "New Project" 新建一个）

---

## 1. 配置 OAuth 同意屏幕（第一次用这个项目做 OAuth 必做）

1. 左侧菜单 → **APIs & Services → OAuth consent screen**
2. User Type 选 **External**（除非你有 Google Workspace 组织账号，一般个人项目选 External）
3. 填基本信息：App name（比如 "Personal Finance Dashboard"）、User support email、Developer contact email
4. Scopes 页面：可以先跳过，代码里用到的 scope（`drive.readonly`、`drive.file`、`openid`、`email`、`profile`）会在请求登录时动态申请，不需要在这里预先配置
5. Test users 页面（如果 App 还在 "Testing" 发布状态）：把你自己的 Google 账号邮箱加进去，否则登录会被拒绝
6. 保存

---

## 2. 创建 OAuth 2.0 Client ID（用于 Sign in with Google）

1. 左侧菜单 → **APIs & Services → Credentials**
2. 点击顶部 **"+ CREATE CREDENTIALS"** → 选 **"OAuth client ID"**
3. Application type 选 **Web application**
4. Name 随便起一个方便识别的名字，比如 "Dashboard Web Client"
5. 找到 **"Authorized JavaScript origins"** 这一栏，点 "+ ADD URI"，加两条：
   ```
   http://localhost:5173
   https://<你的 GitHub 用户名>.github.io
   ```
   注意：
   - 这里**不要**加路径、**不要**加 `/*` 通配符——只要协议+域名+端口
   - 端口号要跟你本地 `vite --port` 实际用的端口一致（本项目默认是 5173）
6. "Authorized redirect URIs" 可以留空——本项目用的是 GIS 的隐式 token flow（`initTokenClient`），不需要 redirect URI
7. 点 **CREATE**，会弹出一个对话框显示 **Client ID**（形如 `xxxxxxxx.apps.googleusercontent.com`），复制它

**填到哪里**：

本地开发：
```
dashboard/.env.local
---
VITE_GOOGLE_CLIENT_ID=刚才复制的 Client ID
```

线上部署：GitHub 仓库 → **Settings → Secrets and variables → Actions → New repository secret**
```
Name:  VITE_GOOGLE_CLIENT_ID
Value: 同一个 Client ID
```
（`.github/workflows/deploy.yml` 会从这个 secret 读取并注入构建环境）

---

## 3. 启用 Google Drive API

1. 左侧菜单 → **APIs & Services → Library**
2. 搜索 **"Google Drive API"** → 点进去 → 点 **Enable**
   （应用登录后读取 `Finance/` 文件夹下的 CSV 文件要用到）

---

## 4. 验证配置

1. 改完 `.env.local` 后，**重启 dev server**（Vite 只在启动时读取 `.env.local`，不会热更新）：
   ```
   cd dashboard
   npm run dev
   ```
2. 打开 `http://localhost:5173/`，点 **Sign in with Google** —— 应该弹出 Google 账号选择/授权窗口，同意后应用会自动检查你 Drive 里的 `Finance/` 文件夹
3. 如果哪一步报错，对照下面的排查表

---

## 5. 常见报错排查

| 报错 | 可能原因 |
|---|---|
| `Missing VITE_GOOGLE_CLIENT_ID` | `.env.local` 没配好，或者改了之后没重启 dev server |
| Sign in 弹窗提示 `redirect_uri_mismatch` 或直接被拒绝 | Authorized JavaScript origins 里没加对当前访问的地址（协议/域名/端口要完全匹配） |
| Drive 请求报 403 / API 未启用 | 检查 Google Drive API 是否已启用（第 3 节） |
| 登录能进去，但一直卡在 "Test users" 相关的拒绝提示 | App 还在 OAuth consent screen 的 Testing 状态，需要把当前登录的 Google 账号加进 Test users 名单（第 1 节） |
