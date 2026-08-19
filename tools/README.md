# 构建脚本

这个站点是从 `data/` + `tools/src/` 生成的静态站。脚本放在这里是因为原来的工作目录
（系统临时目录）会被清理清空——2026-08 已经丢过一次全部源码。

`tools/src/` 是**桌面版源码，也是真值源**：`build_web.py` 由它派生出根目录的
`static/`、`index.html`、`sw.js`。改功能改 `tools/src/`，不要直接改根目录的 `static/`。

| 脚本 | 作用 |
|---|---|
| `build_web.py` | 主构建：解包音频、派生静态站、生成 `sw.js` |
| `build_conj_content.py` | 生成第 24-26 章（九大动词变位），基准表在 `conj_ref.py` |
| `build_themes.py` | 生成第 53-54 章（Tâche 3 主题论点库），含 A2-B1 难度正则审计 |
| `build_more_audio.py` | 扫出没有音频的法语，挂到区块的 `voice` 字段 |
| `pick_voice.py` | 挑选值得配音的句子：按 ❌/✅ 切开、**只留正确的一半** |
| `gen_audio2.py` / `gen_themes_audio.py` / `gen_more_audio.py` | edge-tts 合成，按 MP3 帧剪静音 |
| `mp3_build_manifest.py` / `mp3_synth.py` | 2026-08 把 8216 条 opus 全部重合成 mp3（见下） |
| `build_conj_index.py` | 变位反查索引（点 serions 能说出这是 être 的条件式） |
| `patch_*.py` | 一次性改码脚本，留档只为记录改了什么、以及每处改动的锚点断言 |

## 反复踩过的坑

- `app.js` 的 `rich()` 只放行 `<b> <i> <u> <br>`，正文里用别的标签会显示成字面文字。
- **`build_web.py` 里每一处 `/audio/`、`/word/` 都必须重写成 `window.CLIP(...)`**。
  漏掉一处的后果是：桌面版正常，线上版那个功能完全静音且不报错（长按整句就这样死了一个月）。
  现在构建末尾有断言，全文不允许再出现这两个前缀。
- Service Worker 的版本号必须把 `data/*.json` 一起哈希，否则「只改课文不改代码」的发布
  对老访客永远不生效。音频桶 `tcf-clip` **不带版本号**——否则改一行 CSS 就把她下载好的
  260 MB 离线音频清空。预缓存用 `cache: 'reload'`，否则发版撞上 GitHub Pages 的 10 分钟
  max-age 会把旧文件钉进新版本。
- 音频**全部是 mp3**（19,574 条）。原来 89% 是 Ogg/Opus，Safari 要 iOS 17.4 才支持，
  旧 iPhone 上三分之一的书是哑的。opus 的清单已丢，文本是从 `content.json`（`aid` /
  `aid_ex` / 表格的 `aids` 网格）和 `word_index.json` 反推出来的，见 `mp3_build_manifest.py`。
