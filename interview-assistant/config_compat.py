"""config.yaml 兼容层 —— 把「紧凑写法」补齐成 LiveTranslate 的原生结构。

LiveTranslate 原生（main.py / subtitle_overlay.py 硬依赖）需要的键：

    audio.{device, sample_rate, chunk_duration}
    asr.{asr_engine, funasr_model, model_size, device, compute_type, language,
         vad_threshold, min_speech_duration, max_speech_duration, ...}
    translation.{api_base, api_key, model, target_language, max_tokens,
                 temperature, streaming, system_prompt, context_window}
    subtitle.{font_family, font_size, ...}

本模块同时接受两种写法（可混用，原生键优先）：

    audio.loopback / audio.vad_threshold / audio.silence_duration
    asr.provider: sensevoice | whisper | funasr-nano | anime-whisper
    llm.{enable, api_key, base_url, model, temperature, max_tokens, system_prompt}
    overlay.{always_on_top, click_through, font_size, window_x/y, window_width/height}
    global.debug_log

除了补齐 config，normalize_config() 还会返回一份 settings_overrides：
只包含「用户在 config.yaml 里明确写过」的运行时设置（VAD、设备、模型、
字幕窗位置等），由 main.py 合并进 user_settings.json —— 这样 config.yaml
保持为唯一入口，而界面上手动改过的其它设置不会被冲掉。

「面试应答」模式：llm.enable / translation.always_translate 为真时，
即使 ASR 识别语言与目标语言相同也照常调用 LLM（默认行为是跳过翻译）。
"""

from __future__ import annotations

# ── 原生默认值（与改造前的 config.yaml 保持一致）────────────────────────────

DEFAULT_AUDIO = {
    "device": None,
    "sample_rate": 16000,
    "chunk_duration": 0.032,
    "loopback": True,
}

DEFAULT_ASR = {
    "asr_engine": "funasr",
    "model_size": "medium",
    "funasr_model": "sensevoice-small",
    "device": "cuda",
    "compute_type": "float16",
    "language": "auto",
    "min_speech_duration": 1.0,
    "max_speech_duration": 8.0,
    "vad_threshold": 0.5,
    "sensevoice_pad_seconds": 0.5,
    "whisper_pad_seconds": 0.5,
}

DEFAULT_TRANSLATION = {
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "api_key": "",
    "model": "qwen-turbo",
    "target_language": "zh",
    "source_language": "auto",
    "context_window": 10,
    "max_tokens": 256,
    "temperature": 0.3,
    "streaming": True,
    "system_prompt": None,
    "always_translate": False,
}

DEFAULT_SUBTITLE = {
    "font_family": "Microsoft YaHei",
    "font_size": 28,
    "font_color": "#FFFFFF",
    "outline_color": "#000000",
    "outline_width": 2,
    "bottom_margin": 80,
    "show_original": True,
    "original_font_size": 20,
    "original_color": "#CCCCCC",
    "display_duration": 5.0,
    "opacity": 0.95,
}

DEFAULT_GLOBAL = {"debug_log": False}

# asr.provider → (asr_engine, funasr_model)
PROVIDER_MAP = {
    "sensevoice": ("funasr", "sensevoice-small"),
    "sensevoice-small": ("funasr", "sensevoice-small"),
    "funasr": ("funasr", "sensevoice-small"),
    "funasr-nano": ("funasr", "funasr-nano-2512"),
    "funasr-nano-2512": ("funasr", "funasr-nano-2512"),
    "whisper": ("whisper", None),
    "faster-whisper": ("whisper", None),
    "anime-whisper": ("anime-whisper", None),
}

_GEOMETRY_KEYS = ("window_x", "window_y", "window_width", "window_height")


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _bool(value, default=False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def normalize_config(raw: dict) -> tuple[dict, dict]:
    """把用户写的 config.yaml 变成原生结构，并返回需要写入 settings 的覆盖项。"""
    raw = _dict(raw)
    audio_raw = _dict(raw.get("audio"))
    asr_raw = _dict(raw.get("asr"))
    llm_raw = _dict(raw.get("llm"))
    # 兼容把 overlay 参数写在 subtitle: 下的写法
    overlay_raw = {**_dict(raw.get("subtitle")), **_dict(raw.get("overlay"))}
    global_raw = _dict(raw.get("global"))

    config = {
        "audio": dict(DEFAULT_AUDIO),
        "asr": dict(DEFAULT_ASR),
        "translation": dict(DEFAULT_TRANSLATION),
        "subtitle": dict(DEFAULT_SUBTITLE),
        "global": dict(DEFAULT_GLOBAL),
    }
    overrides: dict = {}

    # ── audio ──
    for key in ("device", "sample_rate", "chunk_duration", "loopback"):
        if key in audio_raw:
            config["audio"][key] = audio_raw[key]
    # 紧凑写法里 VAD 参数挂在 audio 下
    if "vad_threshold" in audio_raw:
        config["asr"]["vad_threshold"] = float(audio_raw["vad_threshold"])
        overrides["vad_threshold"] = float(audio_raw["vad_threshold"])
    if "silence_duration" in audio_raw:
        silence = float(audio_raw["silence_duration"])
        config["asr"]["silence_duration"] = silence
        overrides["silence_duration"] = round(silence, 2)
        # 固定静音阈值 → 界面上 silence_mode 用 fixed，否则 auto 会覆盖用户值
        overrides["silence_mode"] = "fixed"

    # ── asr ──
    for key in (
        "asr_engine",
        "funasr_model",
        "model_size",
        "device",
        "compute_type",
        "language",
        "vad_threshold",
        "min_speech_duration",
        "max_speech_duration",
        "sensevoice_pad_seconds",
        "whisper_pad_seconds",
        "remote_asr_url",
    ):
        if key in asr_raw:
            config["asr"][key] = asr_raw[key]

    provider = asr_raw.get("provider")
    if provider:
        engine, funasr_model = PROVIDER_MAP.get(
            str(provider).strip().lower(), ("funasr", DEFAULT_ASR["funasr_model"])
        )
        config["asr"]["asr_engine"] = engine
        if funasr_model:
            config["asr"]["funasr_model"] = funasr_model
        overrides["asr_engine"] = engine
        if funasr_model:
            overrides["funasr_model"] = funasr_model

    if "device" in asr_raw:
        overrides["asr_device"] = str(asr_raw["device"])
    if "language" in asr_raw:
        overrides["asr_language"] = str(asr_raw["language"])
    if "min_speech_duration" in asr_raw:
        overrides["min_speech_duration"] = float(asr_raw["min_speech_duration"])
    if "max_speech_duration" in asr_raw:
        overrides["max_speech_duration"] = float(asr_raw["max_speech_duration"])

    # ── translation（原生写法）──
    trans_raw = _dict(raw.get("translation"))
    for key in (
        "api_base",
        "api_key",
        "model",
        "target_language",
        "source_language",
        "context_window",
        "max_tokens",
        "temperature",
        "streaming",
        "system_prompt",
        "always_translate",
        "proxy",
        "json_response",
        "no_system_role",
    ):
        if key in trans_raw:
            config["translation"][key] = trans_raw[key]

    # ── llm（紧凑写法）→ translation ──
    if llm_raw:
        base_url = llm_raw.get("base_url") or llm_raw.get("api_base")
        if base_url:
            config["translation"]["api_base"] = base_url
        for src, dst in (
            ("api_key", "api_key"),
            ("model", "model"),
            ("temperature", "temperature"),
            ("max_tokens", "max_tokens"),
            ("system_prompt", "system_prompt"),
        ):
            if llm_raw.get(src) not in (None, ""):
                config["translation"][dst] = llm_raw[src]
        # 「LLM 应答」总开关：显式 enable 才启用同语言也调用
        if "enable" in llm_raw:
            config["translation"]["always_translate"] = _bool(llm_raw["enable"])

    # ── subtitle / overlay ──
    for key in DEFAULT_SUBTITLE:
        if key in overlay_raw:
            config["subtitle"][key] = overlay_raw[key]
    if "font_size" in overlay_raw:
        # overlay.font_size 是悬浮窗正文字号，同时映射到字幕窗与样式
        config["subtitle"]["font_size"] = overlay_raw["font_size"]
        overrides["translation_font_size"] = int(overlay_raw["font_size"])

    for key in _GEOMETRY_KEYS:
        if key in overlay_raw:
            settings_key = {
                "window_x": "overlay_x",
                "window_y": "overlay_y",
                "window_width": "overlay_w",
                "window_height": "overlay_h",
            }[key]
            overrides[settings_key] = int(overlay_raw[key])

    if "click_through" in overlay_raw:
        overrides["click_through"] = _bool(overlay_raw["click_through"])
    if "always_on_top" in overlay_raw:
        overrides["always_on_top"] = _bool(overlay_raw["always_on_top"])

    # ── global ──
    for key, value in global_raw.items():
        config["global"][key] = value

    # ── 模型列表：config 里写了 api_key/model 就以 config 为准 ──
    if config["translation"]["api_key"] and config["translation"]["model"]:
        model_entry = {
            "name": config["translation"]["model"],
            "api_base": config["translation"]["api_base"],
            "api_key": config["translation"]["api_key"],
            "model": config["translation"]["model"],
            "proxy": config["translation"].get("proxy", "none"),
            "streaming": config["translation"].get("streaming", True),
        }
        overrides["models"] = [model_entry]
        overrides["active_model"] = 0

    if "target_language" in config["translation"]:
        overrides["target_language"] = config["translation"]["target_language"]

    overrides["system_prompt"] = config["translation"].get("system_prompt") or ""

    return config, overrides


def merge_overrides(saved: dict | None, overrides: dict) -> dict:
    """把 config.yaml 里的显式设置合并进 user_settings.json 的内容。"""
    merged = dict(saved or {})
    if not overrides:
        return merged

    style = dict(merged.get("style") or {})
    font_size = overrides.pop("translation_font_size", None)
    if font_size is not None:
        style["translation_font_size"] = font_size

    merged.update(overrides)
    if style:
        merged["style"] = style
    return merged
