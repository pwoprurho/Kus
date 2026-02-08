# DeepSeek Coder Local Setup Guide

## Quick Start (5 minutes)

### Step 1: Install Ollama
1. Download: https://ollama.com/download/windows
2. Run `OllamaSetup.exe`
3. Ollama will start automatically in the background

### Step 2: Pull DeepSeek Coder Model
Open PowerShell or Command Prompt and run:

```powershell
ollama pull deepseek-coder:1.3b
```

**Expected output:**
```
pulling manifest
pulling 8b8c7a7f... 100% ▕████████████████▏ 1.3 GB
pulling 8ab4849b... 100% ▕████████████████▏  254 B
pulling 577073ff... 100% ▕████████████████▏  11 KB
pulling ad70a5d9... 100% ▕████████████████▏  483 B
verifying sha256 digest
writing manifest
success
```

**Download size:** ~1.3GB  
**Time:** 2-5 minutes (depending on internet speed)

### Step 3: Test the Model
```powershell
ollama run deepseek-coder:1.3b "Write a simple Three.js cube"
```

If you see code output, it's working! Press `Ctrl+D` or type `/bye` to exit.

### Step 4: Verify Integration
Your Flask app will automatically detect Ollama when you generate an experiment.

Check the console logs for:
```
[STEM AI] Using local DeepSeek Coder 1.3B...
```

If Ollama isn't running, you'll see:
```
[STEM AI] Falling back to Gemini 3.0 Flash...
```

---

## Troubleshooting

### Ollama Not Found
**Error:** `ollama: command not found`

**Fix:** Restart your terminal or add Ollama to PATH:
```powershell
$env:Path += ";C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama"
```

### Model Download Stuck
**Fix:** Cancel (`Ctrl+C`) and retry:
```powershell
ollama pull deepseek-coder:1.3b
```

### Port Already in Use
**Error:** `Error: listen tcp 127.0.0.1:11434: bind: address already in use`

**Fix:** Ollama is already running! Just pull the model.

---

## Usage

### Check Running Models
```powershell
ollama list
```

### Stop Ollama Service
```powershell
# Windows: Stop from Task Manager or
taskkill /F /IM ollama.exe
```

### Start Ollama Service
```powershell
# It auto-starts on Windows boot, or run:
ollama serve
```

---

## Performance Expectations

| Hardware | Generation Speed | Quality |
|----------|------------------|---------|
| Your HP ZBook (i5-8365U, 8GB RAM) | 5-15 seconds | Good (70%+ accuracy) |
| With RTX 4090 (future) | 2-5 seconds | Excellent (85%+ accuracy) |

---

## Next Steps

Once Ollama is installed and the model is pulled:

1. ✅ Restart your Flask app (it will auto-detect Ollama)
2. ✅ Generate an experiment in the STEM Sandbox
3. ✅ Check console logs to confirm local model is being used
4. ✅ Compare speed/quality vs Gemini

**Fallback:** If local model is slow or unavailable, the system automatically uses Gemini 3.0 Flash!
