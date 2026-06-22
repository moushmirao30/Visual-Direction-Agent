# Environment Setup — Windows PowerShell

## One-time setup

Run these commands in PowerShell from inside the `visual-direction-agent/` folder.

### 1. Navigate to project folder
```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
```

### 2. Create virtual environment
```powershell
python -m venv venv
```

### 3. Activate the venv
```powershell
.\venv\Scripts\Activate.ps1
```
> ⚠️ If you see an error about execution policy, run this first (one-time fix):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then re-run the activate command.

### 4. Upgrade pip (avoids install warnings)
```powershell
python -m pip install --upgrade pip
```

### 5. Install all dependencies
```powershell
pip install -r requirements.txt
```
> This will take 3–5 minutes on first run. sentence-transformers downloads a model (~90MB).

### 6. Create your .env file
```powershell
Copy-Item .env.example .env
```
Then open `.env` and fill in your keys:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `TAVILY_API_KEY` — from app.tavily.com (free tier = 1000 searches/month)
- `LANGCHAIN_API_KEY` — from smith.langchain.com (free)
- `HF_TOKEN` — from huggingface.co/settings/tokens (only needed for Agent 05 fallback)

---

## Every subsequent session

```powershell
cd "C:\Users\Moushmi Rao\Claude\Projects\Capstone Project - Gen AI\visual-direction-agent"
.\venv\Scripts\Activate.ps1
```
You'll see `(venv)` in your prompt when it's active.

---

## Windows-specific gotchas flagged ahead of time

| Issue | Symptom | Fix |
|-------|---------|-----|
| Spaces in path | `cannot find path` errors | Always quote the path with `"..."` |
| Execution policy | `cannot be loaded, script is disabled` | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| ChromaDB on Windows | `Microsoft Visual C++ 14.0 required` | Install [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| sentence-transformers slow first run | Hangs on first import | Normal — it downloads the embedding model (~90MB) once |
| Long path errors | `path too long` on pip install | Enable long paths: `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force` (run as admin) |

---

## Verify installation

After install, run this to confirm everything is working:
```powershell
python -c "import crewai; import chromadb; import sentence_transformers; import tavily; print('All core dependencies OK')"
```
