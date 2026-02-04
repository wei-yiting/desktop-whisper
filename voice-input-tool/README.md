# voice-input-tool

Desktop voice input tool with ASR-powered speech-to-text.

## Requirements

### macOS Accessibility Permission

On macOS, this tool requires **Accessibility** permission to simulate keyboard input (paste).

To grant permission:
1. Go to **System Preferences** > **Security & Privacy** > **Privacy** > **Accessibility**
2. Click the lock icon to make changes
3. Add your terminal app (e.g., Terminal, iTerm2) or Python interpreter to the list
4. Ensure the checkbox is enabled

Without this permission, the paste functionality will not work.

## Usage

### Test paste functionality

```bash
python -c "
from src.output import paste_text
import time
time.sleep(2)  # Switch to a text editor within 2 seconds
paste_text('Hello 你好 這是測試')
"
```
