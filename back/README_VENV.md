# Virtual environment setup (PowerShell)

This project currently has no detected Python files. Use this guide to create a virtual environment and install dependencies when you're ready.

Steps:

1. Create a virtual environment (PowerShell):

```powershell
python -m venv .venv
```

2. Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error, run PowerShell as Administrator and:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

3. Install dependencies from `requirements.txt`:

```powershell
pip install --upgrade pip
pip install -r .\requirements.txt
```

4. Freeze updated dependencies back into `requirements.txt` (after installing and testing):

```powershell
pip freeze > .\requirements.txt
```

Optional: use `setup_env.ps1` to automate the steps:

```powershell
# from the project `back` folder
.\setup_env.ps1
```
