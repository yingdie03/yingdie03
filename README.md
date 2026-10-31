## 一、这个工具是做什么的

LiveTranslate 原本是一个「系统音频实时翻译」工具，我们把它配置成了**面试应答助手**：

```
面试官说话（腾讯会议 / 钉钉 / 浏览器 / 电话外放）
        ↓  WASAPI 抓取系统声音（不需要装虚拟声卡）
     Silero VAD 判断「这句话说完了」
        ↓
   SenseVoice 语音识别（中文）
        ↓
   通义千问 qwen-flash（按你的简历生成口语化回答）
        ↓
        悬浮字幕窗，逐字显示答案
```

延迟参考（本机 CPU 模式实测）：

| 环节 | 耗时 |
|---|---|
| 语音识别（5.6 秒音频） | 0.27 ~ 0.5 秒 |
| 大模型首字 | 约 0.3 秒 |
| 完整答案（约 120 字） | 约 1 秒 |

**注意**：它只「听」系统正在播放的声音，不会去听麦克风（除非你手动开启麦克风混音）。所以对方的声音能被识别，你自己说话不会被识别——这正是面试场景需要的。

---

## 二、前置条件

### 2.1 本机已具备（无需再操作）

| 项目 | 现状 |
|---|---|
| Python 3.12 | https://www.python.org/downloads/（虚拟环境依赖它，**不要卸载**） |
安装 ffmpeg   https://ffmpeg.org/   （Win11 自带 winget，管理员终端执行：winget install ffmpeg）
| ASR 模型 | SenseVoice Small | Silero VAD | 由 `silero-vad` 包自带，无需下载 |

### 2.2 你需要自己准备

1. **阿里云百炼（DashScope）API Key**
   - 地址：<https://bailian.console.aliyun.com/>
   - 需要**开通 qwen-flash 模型**并有可用额度
   - Key 形如 `sk-...`，填入 `config.yaml` 的 `llm.api_key`
   - ⚠️ 本机实测：**qwen-turbo 会返回 429（限流/无额度）**，qwen-flash 正常，所以配置里用的是 qwen-flash

2. **你的简历文本**（必填，否则回答会很空）
   - 打开 `config.yaml`，找到 `====简历开始====` 和 `====简历结束====`
   - 把中间那句示例替换成你的完整简历（教育背景、课程、实训、项目、技能）
   - 只保留**真实**内容：提示词里明确禁止编造项目和实习

3. **能出声的音频输出设备**
   - 面试声音必须从**默认扬声器/耳机**播放，程序抓的是默认输出设备的 loopback
   - 建议戴耳机：外放容易把环境音、回声一起收进去

4. **网络**
   - 能访问 `https://dashscope.aliyuncs.com`（国内直连即可，不需要代理）
   - 如果走代理，在「设置 → 翻译 → 代理」里选 `system` 或填自定义地址

### 2.3 磁盘空间

| 目录 | 占用 |
|---|---|
| `D:\LiveTranslate-main`（含 .venv + 模型） | 约 6.0 GB |
| 桌面副本 `interview-assistant` | 约 5.8 GB |
| 运行产生的日志/转录 | 每次几 KB ~ 几百 KB |

---

## 三、3 分钟上手

**开跑前检查清单**

- [ ] 阿里云百炼 Key 已填进 `config.yaml` 的 `llm.api_key`，且 qwen-flash 有额度
- [ ] 简历已替换到 `====简历开始====` / `====简历结束====` 之间
- [ ] 声音从默认输出设备（耳机/扬声器）播放
- [ ] 能正常访问 `dashscope.aliyuncs.com`

步骤：

1. **填简历**：编辑 `config.yaml` → `llm.system_prompt` → 替换 `====简历开始====` 与 `====简历结束====` 之间的内容 → 保存。
2. **双击 `start.bat`**（桌面副本里同样是这个文件）。
3. 等 **10 ~ 15 秒**：控制台会依次出现
   `SenseVoice loaded ... on cpu` → `ASR worker ready` → `Translator: qwen-flash`，
   随后透明的悬浮字幕窗出现，表示已就绪。
4. 播放面试音频（会议软件/网页），对方每说完一句，悬浮窗就会出现中文答案。
5. 结束：托盘图标右键 → **退出**（或悬浮窗标题栏的「退出」按钮）。

> 启动后 **0.5 秒**自动开始采集音频，不需要额外点「开始」。

---

## 四、config.yaml 配置说明

### 4.1 当前生效内容

```yaml
audio:
  loopback: true          # 抓系统声音（固定行为，保留兼容）
  sample_rate: 16000
  vad_threshold: 0.5      # 判定「有人说话」的灵敏度，越高越不容易被噪音触发
  silence_duration: 1.2   # 停顿多久算一句说完（秒），越大句子越长
  chunk_duration: 0.2

asr:
  provider: sensevoice    # 识别引擎：sensevoice / whisper / funasr-nano / anime-whisper
  device: cpu             # cpu 或 cuda（本机 CPU 已够快，且省显存）
  language: "zh"          # ⚠️ 语言提示：只接受中文，见 4.4
  vad_threshold: 0.5
  min_speech_duration: 0.3
  max_speech_duration: 15
  model_size: "base"

translation:
  target_language: "zh"   # 输出语言
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "sk-..."       # 与 llm.api_key 保持一致
  model: "qwen-flash"

llm:
  enable: true            # 开启「应答模式」：中文问 → 中文答，不会因为语言相同而跳过
  api_key: "sk-..."
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-flash"
  temperature: 0.3        # 越低越稳，越高越发散
  max_tokens: 600         # 答案长度上限（约 300 汉字）
  system_prompt: |
    你是王鑫朋，机械电子工程本科应届生，应聘CAD绘图实习生。
    只能使用简历里面真实经历作答，严禁编造项目、实习经历。
    回答口语化，适合面试口头口述，控制在100‑200字以内。
    ====简历开始====
    【在这里删掉括号，粘贴你的完整简历文本】
    ====简历结束====

subtitle:                 # 悬浮窗外观与位置
  always_on_top: true
  click_through: true     # 鼠标穿透（开着就没法点悬浮窗，见 5.2）
  font_size: 14
  window_x: 100
  window_y: 100
  window_width: 520
  window_height: 300

global:
  debug_log: false        # true 会输出大量调试日志
```

> 说明：为便于阅读，上面把 `system_prompt` 展开成了多行；实际文件里它是 `>` 折叠写法。
> 其中「简历」一段目前是一句示例（机械电子工程专业应届生…），**请替换成你的完整简历**。

### 4.2 两种写法都支持

程序内部原本要求「扁平」写法（`asr.asr_engine`、`translation.max_tokens`、`subtitle.font_size` 等）。
为了让上面这份「分组」写法能用，新增了兼容层 `config_compat.py`：

- `llm.*` 会自动展开成 `translation.*`
- `asr.provider: sensevoice` → `asr_engine: funasr` + `funasr_model: sensevoice-small`
- `audio.vad_threshold` / `audio.silence_duration` → 写入运行时设置
- `overlay.*` 或 `subtitle.window_*` → 悬浮窗位置/尺寸

**优先级规则**：`config.yaml` 里显式写过的键，会覆盖 `user_settings.json` 中的旧值（每次启动时合并）。
也就是说——**想改参数，改 config.yaml 最省事**；在界面里改的同类参数，下次启动会被 config.yaml 覆盖。

### 4.3 常见修改

| 想做什么 | 改哪里 |
|---|---|
| 换模型（更强表达） | `llm.model` 和 `translation.model` 一起改成 `qwen-plus` |
| 答案更长 | `llm.max_tokens: 900`，并在提示词里放宽字数 |
| 回答更稳/更活 | `llm.temperature` 0.1 ~ 0.8 |
| 句子切得更快 | `audio.silence_duration: 0.8` |
| 噪音多、误触发 | `audio.vad_threshold: 0.6 ~ 0.7` |
| 长句被截断 | `asr.max_speech_duration: 20` |
| 用显卡加速 | `asr.device: cuda`（需显存 ≥ 2 GB） |
| 悬浮窗位置 | `subtitle.window_x / window_y` |

### 4.4 语言设置的两个坑

- `asr.language: "zh"` 是**硬过滤**：识别出来的语言不是中文，这一句会被直接丢弃。
  如果面试里可能出现英文提问，改成 `language: "auto"`（自动检测）。
- `llm.enable: true` 触发「应答模式」。如果关掉它，中文问句会因为「源语言 = 目标语言」被跳过、只剩原文没有答案。

---

## 五、启动与界面

### 5.1 启动

| 方式 | 说明 |
|---|---|
| 双击 `start.bat` | 推荐。会先检查环境，再启动 |
| 命令行 | `.venv\Scripts\python.exe main.py` |

**关于中文路径**：桌面文件夹名是「桌面」，属于非 ASCII 路径，PyTorch 在 Windows 上打开模型文件会失败（`errno 2 ... fopen`）。
桌面副本里的 `start.bat` 会自动检测：路径含中文时临时映射一个空闲盘符（`L:`、`M:`…）从英文路径启动，退出时自动解除映射。控制台会打印：

```
[INFO] Non-ASCII path detected, using drive L: for this session.
```

`D:\LiveTranslate-main\start.bat` 走纯英文路径，不需要这一步。

### 5.2 悬浮窗

标题栏一行按钮：**隐藏 / 字幕 / 暂停·继续 / 清空 / 紧凑·全屏 / 设置 / 退出**
第二行勾选框：**鼠标穿透 / 始终置顶 / 自动滚动 / 任务栏**，以及 **模型**、**目标语言** 下拉框。

- 拖动标题栏可移动窗口；位置会自动记住。
- `click_through: true` 时鼠标会穿透窗口——想点按钮，先到托盘菜单里取消「鼠标穿透」。
- 右键字幕区域可以复制 / 导出原文或译文。

### 5.3 托盘菜单（任务栏右下角图标）

- 暂停 / 继续、显示·隐藏悬浮窗
- 字幕模式（独立字幕窗，供 OBS 采集）、字幕窗鼠标穿透
- 悬浮窗子菜单：鼠标穿透、始终置顶、自动滚动、任务栏
- 翻译模型、目标语言、语言提示（快速切换）
- 显示设置、显示日志、退出

> 托盘图标可能在「^」折叠区里。

### 5.4 设置面板（7 个标签）

| 标签 | 关键项 |
|---|---|
| **VAD / ASR** | 引擎、设备（cpu/cuda）、语言提示、阈值、最短/最长语音、静音模式与时长、增量识别、麦克风混音 |
| **翻译** | 模型列表（增/删/复制）、API 地址、Key、模型名、流式、结构化输出、上下文轮数、温度、提示词、超时、代理、保存转录 |
| **样式** | 容器/头部颜色、透明度、圆角、原文字体/字号/颜色、译文字体/字号/颜色 |
| **字幕** | 独立字幕窗（OBS 用）的样式、多语言行、动画 |
| **基准测试** | 用内置句子横向比较多个翻译模型的速度与质量 |
| **缓存** | 已下载模型及占用、打开模型目录、全部删除并退出、打开转录文件夹 |
| **更新日志** | 版本变更 |

设置是**自动保存**的（改完约 0.3 秒写入 `user_settings.json`）。

---

## 六、面试场景实操建议

### 推荐参数

| 参数 | 建议值 | 理由 |
|---|---|---|
| `silence_duration` | 0.8 ~ 1.2 s | 太短会把一句话切碎，太长答案出得慢 |
| `vad_threshold` | 0.5 ~ 0.6 | 环境吵就调高 |
| `asr.language` | `zh`（纯中文面试） | 减少误识别；有英文就改 `auto` |
| `llm.model` | `qwen-flash` | 首字 0.3 s，实时性最好 |
| `max_tokens` | 600 | 约 200~300 字，够口述 |
| `temperature` | 0.3 | 稳定、不跑题 |

### 使用要点

1. **音量**：会议音量保持正常，过小会漏识别；过大会削波。
2. **别开麦克风混音**：否则你自己的回答会被再次识别，形成「自问自答」循环。
3. **提前试跑**：面试前用一段新闻/播客音频走一遍，确认答案风格和长度合适。
4. **简历要具体**：提示词里写明「只用简历内容」，简历越具体，答案越像你本人。
5. **敏感提示**：这是辅助工具，回答要自己判断后再口述；不要照读有明显错误的句子。
6. **隐私**：所有识别和回答都会写进 `transcripts\`，面试结束后建议删除。

---

## 七、目录与数据

```
D:\LiveTranslate-main\
├── start.bat                启动（桌面副本会自动处理中文路径）
├── main.py                  主程序
├── config.yaml              ★ 你的配置（简历、模型、密钥都在这）
├── config_compat.py         配置兼容层
├── user_settings.json       界面设置的运行时快照（自动维护）
├── .venv\                   虚拟环境（勿删、勿动）
├── models\                  ASR 模型缓存（约 896 MB）
├── transcripts\             ★ 每次启动生成 3 个文件：
│                              livetrans_日期_时间_all.txt         原文 + 译文
│                              livetrans_日期_时间_original.txt    仅原文
│                              livetrans_日期_时间_translation.txt 仅译文
├── logs\                    运行日志 livetrans_*.log
├── i18n\                    界面语言
└── screenshot\              README 截图
```

---

## 八、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 启动即报 `KeyError: 'max_tokens'` | 配置用了分组写法但程序是旧版 | 确认 `config_compat.py` 存在；本版本已兼容 |
| 启动报 `RuntimeError: ... fopen ... errno 2 ...silero_vad.jit` | 程序路径含中文 | 用 `start.bat` 启动（会自动映射盘符），或把整个目录移到纯英文路径 |
| 翻译报 `429 limit_requests` | 模型无额度/被限流（qwen-turbo 常见） | 改用 `qwen-flash` 或 `qwen-plus`；到百炼控制台确认额度 |
| 翻译报 `401` / `invalid_api_key` | Key 错、复制多了字符、未开通模型 | 重新复制 Key，注意别多空格/多字母；确认已开通该模型 |
| 一直没字幕 | 没声音、设备不对、音量太小 | 确认声音从**默认输出设备**播放；VAD 阈值调低到 0.4；看 `logs\` 里有没有 `ASR [zh]` |
| 蓝牙耳机识别不到/声音极小 | 蓝牙耳机默认切到「免提(HFP)」通道，loopback 几乎没声 | 在声音设置里把输出切到「立体声(A2DP)」，或改用有线耳机 |
| 有原文没答案 | 源语言=目标语言被跳过，或 `llm.enable` 关了 | 保持 `llm.enable: true` |
| 英文提问没反应 | `asr.language: "zh"` 把非中文整句丢弃 | 改成 `"auto"` |
| 答案被切得很碎 | 静音判定太短 | `silence_duration` 调到 1.2 |
| 首次启动很慢 | CPU 加载模型需 10~15 秒 | 正常，等悬浮窗出现即可 |
| 悬浮窗点不动 | 开了鼠标穿透 | 托盘菜单取消「鼠标穿透」 |
| 显存/内存占用高 | 选了 cuda 或长会话 | 切回 `device: cpu`；重启程序清缓存 |
| 桌面副本占空间 | OneDrive 同步了 5.8 GB | 把副本移出 OneDrive，或暂停同步 |

**看日志**：托盘 → 显示日志，或直接打开 `logs\livetrans_*.log`。

---

## 九、安全与隐私

- `config.yaml` 里的 API Key 是**明文**，不要把该文件或截图发到群里；换 Key 改 `llm.api_key`（优先级最高）即可。
- `transcripts\` 会完整记录识别到的对话和生成的答案，面试结束请删除。
- 程序只在本地做语音识别（模型在本机），只有**文字**会发到 DashScope 生成回答。
- 不要把这个文件夹放到公共网盘或共享目录。

---

## 十、迁移与备份

- **整体迁移**：直接复制整个目录（含 `.venv` 和 `models`）即可，约 6.0 GB。
- **路径要求**：目标路径**尽量用纯英文**；必须放在中文路径时，用 `start.bat` 启动（自动映射盘符）。
- **依赖**：`.venv` 依赖本机已安装的 **Python 3.12**（`C:\Users\hp\AppData\Local\Programs\Python\Python312`）。换到没装 Python 3.12 的电脑会启动失败——那种情况请用官方 portable 绿色版重新部署。
- **只想备份配置**：复制 `config.yaml`（含简历与 Key）和 `user_settings.json` 即可。

---

## 附：常用命令

```bat
:: 正常启动
start.bat

:: 命令行启动（英文路径）
.venv\Scripts\python.exe main.py

:: 检查依赖是否完整
.venv\Scripts\python.exe -m pip check

:: 跑单元测试
.venv\Scripts\python.exe -m pytest tests -q

:: 查看最近一次运行日志
type logs\livetrans_*.log
```

> 切换 CPU / GPU 请改 `config.yaml` 的 `asr.device`，程序没有额外的设备环境变量。
