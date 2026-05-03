# AI Ad Campaign Studio — 启动指南

## 一次性设置

1. **装 Python 依赖**（在项目目录下执行）：
   ```bash
   pip install -r requirements.txt
   ```

2. **装 ffmpeg**（用来合成视频和提取关键帧）：
   ```bash
   brew install ffmpeg
   ```
   没装也能跑，只是视频不会有配音/BGM、PDF 里没有视频关键帧页。

3. **填 API key** — 在项目目录下创建 `api_config.json`：
   ```json
   {
     "openai_api_key": "sk-...",
     "fal_api_key": "..."
   }
   ```
   - OpenAI key: https://platform.openai.com/api-keys
   - fal.ai key: https://fal.ai/dashboard/keys

## 启动

```bash
python app.py
```
或者：
```bash
uvicorn app:app --reload
```

浏览器打开 **http://localhost:8000**。

## 使用流程

1. **顶栏右侧**会显示 `● API ready`（绿色）= key OK，否则是红色警告。
2. 默认载入 `product_info.json`（McDonald's 蘑菇瑞士堡）作为示例填好。
3. 也可以在 **⚡ QUICK BRIEF** 区粘贴一段产品描述，按 "Auto-fill brief"，AI 自动抽取所有字段。
4. 在 **🎨 STYLE PRESET** 选一个风格（不选也行，AI 会自由发挥）。
5. 点 **⚡ GENERATE CAMPAIGN**。
6. 右侧 PIPELINE 面板实时显示每一步的耗时和成本，顶栏 cost 计数器累计。
7. Slogan → 海报 → 配音 → BGM → 视频 一步步出现在下方。
8. 完成后点 **📄 Export Pitch Deck (PDF)** 下载 5 页 PDF 作品集。

## Demo 演示模式

顶栏右上角切换 **Demo Mode** → 显示预生成的 case 卡片，点一下即时载入完整素材，不需要等 API。

要预生成 demo case：在 Live Mode 跑几次喜欢的 case，然后把 `outputs/campaign_*` 文件夹复制到 `presets_demo/` 即可。

## 5 月 5 日 Demo 流程建议

1. 开场让台下观众喊一个产品 + 一个风格 preset
2. 在表单里飞快填好 → 点 Generate
3. 让 PIPELINE 面板可见地跑（slogan ~5s, 海报 ~30s, 视频 ~2-5min）
4. 切到 **Demo Mode** 展示 3-4 个预生成的炫酷案例 + 讲技术架构（GPT-4o-mini / gpt-image-1 / Cassette music / Kling）
5. 讲完时切回，刚跑的现场案例已经完成，揭晓 + 撒花动画
6. 点 PDF 导出，假装"这就是给客户的提案"，结束

## 故障排查

- **"No API keys"**：检查 `api_config.json` 是否在 ad-campaign-generator-main 目录下，并且两个 key 都填了
- **海报失败但其他都成**：你的 OpenAI 账号可能没有 gpt-image-1 权限。代码会自动回退到 dall-e-3 → dall-e-2，控制台会有日志
- **视频卡住超过 10 分钟**：Kling 偶尔会失败，刷新页面重新生成
- **没声音**：检查是否装了 ffmpeg。终端会有 `ffmpeg_used: false` 的提示
- **端口 8000 被占用**：`uvicorn app:app --port 8001`

## 文件结构

```
ad-campaign-generator-main/
├── app.py                  # FastAPI 服务器
├── pipeline.py             # 异步生成流水线
├── presets.py              # 8 个风格预设
├── pdf_export.py           # PDF Pitch Deck 生成
├── social_resize.py        # 多尺寸变体
├── ad_campaign_generator.py  # 原 CLI（保留作 fallback）
├── static/index.html       # UI（单文件）
├── outputs/                # 生成的 campaign 存这
├── presets_demo/           # Demo 模式的预生成案例
├── product_info.json       # 默认产品输入
├── api_config.json         # API keys（你自己创建，不要提交！）
└── requirements.txt
```

## 成本估算（单次完整 run）

| 步骤 | 模型 | 价格 |
|---|---|---|
| Slogan + theme | GPT-4o-mini | ~$0.001 |
| 海报 | gpt-image-1 1024x1536 medium | ~$0.042 |
| 配音 | OpenAI tts-1 | ~$0.015 |
| BGM | fal.ai cassetteai | ~$0.020 |
| 10s 视频 | Kling standard | ~$0.350 |
| **合计** | | **~$0.43** |
