# 桌面 App 打包方案（待决策）

当前状态：Web 应用形式，需要 `python app.py` + 浏览器访问 `localhost:8000`。
保留这份文档供未来需要"app 化"时参考。

---

## 关键限制

**从 Mac 无法直接打包 Windows 的 .exe**——PyInstaller 等工具不支持交叉编译。
要做 Windows 版本，必须有以下之一：
1. 一台 Windows 机器（队友的也行）
2. GitHub Actions 云端构建
3. Mac 上跑 Windows 虚拟机（Parallels / UTM）

Demo 是 Zoom 直播，从 Mac 共享屏幕，所以 **Mac .app 是最关键的**。

---

## 三档方案

### 🥉 方案 A：双击启动器（5 分钟）

- Mac：`start.command` 文件 — 双击启动后端 + 打开浏览器
- Windows：`start.bat` 文件 — 同上
- 本质还是浏览器网页，但**不用敲终端命令**
- 跨平台 100%，但仍需用户先装 Python + 依赖
- **零额外开发**，纯脚本

### 🥈 方案 B：pywebview 原生窗口（1 小时）

- 用 [pywebview](https://pywebview.flowrl.com/) 把 FastAPI 后端套进一个原生 OS 窗口
- 看起来就是桌面 app，**不开浏览器**
- 启动方式仍是双击 .command/.bat
- 跨平台代码相同，仍需 Python 环境
- 需要小幅改 `app.py` 加一个 launcher

### 🥇 方案 C：PyInstaller 真打包

#### Mac 部分（在本机就能做，~30 分钟）
- `pyinstaller` 打包成 `AdCampaignStudio.app`
- 双击运行，**最终用户不需要装 Python**
- 可以拖进 Applications 文件夹
- 文件大小约 100-200 MB（带 Python runtime）
- ⚠️ 未签名的 .app 在 macOS 上首次打开要右键→打开（绕过 Gatekeeper）

#### Windows 部分（需要 Windows 环境）
三选一：
1. **队友有 Windows** — 他 git clone + `pip install` + `pyinstaller` 跑一遍，5 分钟出 .exe
2. **GitHub Actions** — 配一个 workflow，push 即云端自动构建 .exe artifact
3. **Mac 上虚拟机** — 装 [UTM](https://mac.getutm.app/) (免费) 或 Parallels，里面装 Windows，再跑 PyInstaller。最折腾。

---

## 推荐路径

如果队友决定要"app 化"：

1. **先做 A 的启动器**（5 分钟），立即让任何人都能更轻松跑起来
2. **Mac .app 用方案 C**（~30 分钟，本机搞定），demo 当天双击启动更专业
3. **Windows .exe**：
   - 队友有 Windows → 让他构建（最简单）
   - 否则配 GitHub Actions（一次性投入，永久受益）

**当前不做这些的理由**：先让用户和队友实测 Web 版，确认功能稳定 + 视觉满意之后再投入打包工作。打包是"皮肤"，骨架先 OK 再换皮。

---

## 决策记录

- [ ] 队友反馈：______
- [ ] 是否需要 app 化：______
- [ ] 选择的方案：A / B / C-Mac / C-Win / 不打包
- [ ] 决策日期：______
