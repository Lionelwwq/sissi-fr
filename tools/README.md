# 构建脚本

这个站点是从 `data/` + `static/` 生成的静态站。脚本放在这里是因为原来的工作目录
（系统临时目录）会被清理清空——2026-08 已经丢过一次全部源码。

| 脚本 | 作用 |
|---|---|
| `build_web.py` | 主构建：解包音频、派生静态站、生成 `sw.js`（Service Worker 版本号对全部 shell 文件取哈希） |
| `build_conj_content.py` | 生成第 24-26 章（九大动词变位），基准表在 `conj_ref.py` |
| `build_themes.py` | 生成第 53-54 章（Tâche 3 主题论点库），含 A2-B1 难度正则审计 |
| `build_more_audio.py` | 扫出没有音频的法语，挂到区块的 `voice` 字段 |
| `pick_voice.py` | 挑选值得配音的句子：按 ❌/✅ 切开、**只留正确的一半** |
| `gen_audio2.py` / `gen_themes_audio.py` / `gen_more_audio.py` | edge-tts 合成，按 MP3 帧剪静音 |
| `build_conj_index.py` | 变位反查索引（点 serions 能说出这是 être 的条件式） |

注意：`app.js` 的 `rich()` 只放行 `<b> <i> <u> <br>`，正文里用别的标签会显示成字面文字。
