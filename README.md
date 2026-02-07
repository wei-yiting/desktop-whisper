# Desktop Whisper

Desktop Whisper 是一款 macOS 桌面語音輸入工具。透過全域快捷鍵錄音，使用 [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) 模型進行語音辨識，並將辨識結果自動貼上至當前游標所在的文字欄位。

## Architecture

應用程式採用**事件驅動狀態機**架構，以 PyQt6 為核心事件迴圈，各模組職責分離：

```
┌─────────────────────────────────────────────────────┐
│                   VoiceInputApp                      │
│               (app.py - 主控制器)                     │
│                                                      │
│   狀態機: IDLE ──▶ RECORDING ──▶ TRANSCRIBING ──▶ IDLE │
│              (快捷鍵)       (快捷鍵)          (完成)    │
└───┬──────────┬──────────┬──────────┬────────────┬────┘
    │          │          │          │            │
    ▼          ▼          ▼          ▼            ▼
 hotkey.py  recorder.py  asr.py   output.py    ui.py
 全域快捷鍵   音訊錄製    語音辨識   文字貼上   浮動視窗
 (pynput)  (sounddevice) (Qwen3)  (pyperclip  (PyQt6)
                                  + pyautogui)
```

### 模組說明

| 模組 | 檔案 | 說明 |
|------|------|------|
| 主控制器 | `src/app.py` | 狀態機、系統列圖示、整合各模組。透過 Qt Signal/Slot 機制在背景執行緒與主執行緒間安全通訊 |
| 語音辨識 | `src/asr.py` | 封裝 Qwen3-ASR 模型，Singleton 模式延遲載入，自動偵測最佳運算裝置 (MPS > CUDA > CPU) |
| 音訊錄製 | `src/recorder.py` | 使用 sounddevice 非阻塞錄音，16 kHz 取樣率、單聲道、float32 格式，錄製完成後存為暫存 WAV 檔 |
| 全域快捷鍵 | `src/hotkey.py` | 基於 pynput 的鍵盤監聽，在 daemon thread 中運行，支援組合鍵設定 |
| 文字貼上 | `src/output.py` | 透過剪貼簿 + 鍵盤模擬 (Cmd+V / Ctrl+V) 將辨識結果貼至目標應用程式 |
| 浮動視窗 | `src/ui.py` | 無邊框、半透明、置頂的浮動視窗，錄音時顯示聲波動畫，辨識時顯示旋轉載入動畫 |

### 執行緒模型

- **主執行緒**：PyQt6 事件迴圈，負責所有 UI 操作
- **快捷鍵執行緒**：pynput daemon thread，監聽全域鍵盤事件
- **ASR 執行緒**：模型載入與推論在背景 daemon thread 執行，完成後透過 `pyqtSignal` 通知主執行緒

### 目錄結構

```
desktop-whisper/
└── voice-input-tool/
    ├── run.py                  # 程式進入點
    ├── pyproject.toml          # 專案設定與依賴
    ├── uv.lock                 # 依賴鎖定檔
    ├── VoiceInput.spec         # PyInstaller 打包設定
    ├── src/
    │   ├── app.py              # 主控制器
    │   ├── asr.py              # 語音辨識引擎
    │   ├── recorder.py         # 音訊錄製
    │   ├── hotkey.py           # 全域快捷鍵
    │   ├── ui.py               # 浮動視窗 UI
    │   └── output.py           # 文字貼上
    ├── tests/
    │   └── test_asr.py         # 單元測試
    ├── scripts/
    │   ├── build_macos.sh      # macOS .app 打包腳本
    │   ├── create_icon.py      # 圖示生成
    │   └── entitlements.plist  # macOS 權限設定
    └── assets/                 # 應用程式資源
```

## Tech Stack

| 類別 | 技術 |
|------|------|
| 程式語言 | Python 3.10+ |
| 桌面框架 | PyQt6 |
| 語音辨識模型 | [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) (qwen-asr) |
| 深度學習框架 | PyTorch, Transformers, Accelerate |
| 音訊錄製 | sounddevice |
| 鍵盤監聽 | pynput |
| 剪貼簿 / 鍵盤模擬 | pyperclip, pyautogui |
| 套件管理 | [uv](https://docs.astral.sh/uv/) |
| 打包工具 | PyInstaller |

## Hardware Requirements

### 最低需求

| 項目 | 規格 |
|------|------|
| CPU | x86-64 或 ARM64 (Apple Silicon) |
| RAM | 4 GB |
| 儲存空間 | ~3.5 GB（應用程式 + 模型快取） |
| 麥克風 | 必要 |
| 作業系統 | macOS (主要支援) |

### 建議配備

| 項目 | 規格 |
|------|------|
| CPU/GPU | Apple Silicon (M1/M2/M3/M4) — 使用 MPS 加速推論 |
| RAM | 8 GB 以上 |
| 儲存空間 | 5 GB 以上可用空間 |

### 運算裝置支援

應用程式會自動偵測並選擇最佳運算裝置：

| 優先順序 | 裝置 | 精度 | 說明 |
|----------|------|------|------|
| 1 | Apple MPS | float16 | Apple Silicon GPU，推論速度最佳 |
| 2 | NVIDIA CUDA | bfloat16 | NVIDIA 獨立顯卡 |
| 3 | CPU | float32 | 通用相容，速度較慢 |

> ASR 模型約 1.2 GB，首次啟動時自動從 Hugging Face Hub 下載至 `~/.cache/huggingface/`。

## Installation

### 前置需求

- Python 3.10 或以上
- [uv](https://docs.astral.sh/uv/) 套件管理器

### 步驟

1. **Clone 此 repo**

   ```bash
   git clone <repo-url>
   cd desktop-whisper/voice-input-tool
   ```

2. **安裝依賴**

   ```bash
   uv sync
   ```

3. **執行應用程式**

   ```bash
   uv run python run.py
   ```

   首次啟動時，程式會自動下載 Qwen3-ASR-0.6B 模型（約 1.2 GB），下載完成後即可使用。

### 打包為 macOS .app

```bash
# 標準打包
./scripts/build_macos.sh

# 附帶 ad-hoc 簽署
./scripts/build_macos.sh --sign

# 附帶開發者憑證簽署
./scripts/build_macos.sh --sign "Developer ID Application: Name (TEAMID)"
```

打包完成後，`.app` 檔案位於 `dist/VoiceInput.app`，可拖曳至 `/Applications/` 資料夾安裝。

## Usage

### 基本操作

1. 啟動應用程式後，系統列會出現麥克風圖示
2. 按下快捷鍵 **Alt + Space** 開始錄音（螢幕中央會出現聲波動畫）
3. 再次按下 **Alt + Space** 停止錄音並開始辨識（動畫切換為載入旋轉）
4. 辨識完成後，文字自動貼上至當前游標位置

### 系統列選單

右鍵點擊系統列麥克風圖示，可使用以下功能：

- **開始錄音 / 停止錄音** — 手動控制錄音
- **快捷鍵** — 顯示目前設定的快捷鍵
- **關於** — 顯示應用程式資訊
- **結束** — 退出應用程式

### 環境變數設定

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `VOICE_INPUT_HOTKEY` | `<alt>+<space>` | 自訂全域快捷鍵 |
| `ASR_MODEL_ID` | `Qwen/Qwen3-ASR-0.6B` | 自訂 Hugging Face 模型 ID |

範例：

```bash
VOICE_INPUT_HOTKEY="<cmd>+<shift>+r" uv run python run.py
```

### macOS 權限設定

應用程式需要以下系統權限才能正常運作：

1. **麥克風權限** — 首次錄音時系統會自動提示授權
2. **輔助使用 (Accessibility) 權限** — 用於鍵盤模擬貼上文字
   - 前往 **系統設定** > **隱私權與安全性** > **輔助使用**
   - 將終端機應用程式（如 Terminal、iTerm2）或 `VoiceInput.app` 加入允許清單

### 執行測試

```bash
cd voice-input-tool
uv run pytest tests/
```

### 日誌位置

- **開發模式**：輸出至終端機 (stdout)
- **打包 .app 模式**：`~/Library/Logs/VoiceInput/voiceinput.log`
