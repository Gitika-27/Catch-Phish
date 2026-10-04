# CatchPhish final setup

## What is included

- React frontend configured to use `https://catchphish-cef6.onrender.com` by default.
- Optional `frontend-react/.env.local` and `.env.example` for local configuration.
- Tier 1.5 Unicode-confusable/lookalike detection, including `раypal.com` vs `paypal.com`.
- Human-readable SHAP explanation headlines.
- Explanation-first visual result card with telemetry and test examples.
- Manifest V3 navigation guard connected to Render.

## Extract and open in VS Code

1. Extract the ZIP. Open the extracted `CatchPhish_final` folder in VS Code.
2. Open a terminal at the project root. Confirm `git status` works after you copy this folder into your real Git clone; this ZIP does not include `.git`.

## Run locally

### Backend terminal

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend terminal

```powershell
cd frontend-react
npm ci
npm run dev -- --port 5174
```

Open `http://localhost:5174`. The frontend uses Render by default. To use a local backend instead, edit `frontend-react/.env.local` to `VITE_API_URL=http://127.0.0.1:8000`, then restart Vite.

## Verify the new version

The new page has a `WHY THIS RESULT // SHAP + RULES` card and telemetry row. Scan:

```text
https://github.com
https://раypal.com/login
http://paypal-secure-login.tk/verify
```

The homograph test should mention trusted `paypal.com` and the Tier-1.5 guard.

## Load the extension

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer mode.
3. Choose Load unpacked.
4. Select the extracted `extension` folder.
5. Reload the extension after editing files.

The extension already calls Render. If Render is sleeping, the first request may take time to wake up.

## Push into the GitHub repository

Do not copy the ZIP folder's `.git` because it intentionally has no `.git`. The safest approach is to copy the ZIP contents into your original Git clone, preserving that clone's `.git` folder. Then run:

```powershell
cd E:\CatchPhish

git switch main
git pull --rebase origin main

git status

git add backend frontend-react extension SETUP_AND_PUSH.md
git diff --cached --check
git diff --cached --stat
git commit -m "Add explainable navigation guard and mentor-ready UI"
git push origin main
```

Before the commit, make sure `node_modules`, `venv`, `.env.local`, and `scan_history.json` are not staged.

## Vercel and Render

Vercel should use `frontend-react` as its root directory, `npm run build` as its build command, and `dist` as its output directory. Add this Vercel environment variable and redeploy:

```text
VITE_API_URL=https://catchphish-cef6.onrender.com
```

Render should use the `backend` directory, install `requirements.txt`, and start with:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```
