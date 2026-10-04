# CatchPhish — React Frontend Setup

This is a full React (Vite) rewrite of the frontend, styled after the "Ledger"
reference: dark charcoal theme, bold condensed headline type, gold accent,
and a live "code editor" panel showing real scan data as syntax-highlighted
pseudo-code.

It talks to the **same FastAPI backend** you already have running — nothing
on the backend needs to change.

## Setup

```powershell
cd CatchPhish\frontend-react
npm install
npm run dev
```

Open **http://localhost:5173**

Keep your backend running separately in another terminal, exactly as before:
```powershell
cd CatchPhish\backend
venv\Scripts\activate
uvicorn main:app --reload
```
(Backend stays on port 8000, this new frontend runs on port 5173, and they
talk to each other over CORS — already enabled in `main.py`.)

## Adding your logo
Open `src/components/Navbar.jsx` and find this block:
```jsx
<div className="nav-logo-mark">C</div>
```
Replace it with:
```jsx
<img src="/logo.svg" alt="CatchPhish" />
```
Then drop your logo file into `frontend-react/public/logo.svg` (create the
`public` folder if it doesn't exist — Vite serves anything in there at the
site root automatically). PNG works too, just update the filename/extension.

## What's different from the old vanilla frontend
- Built with React (components in `src/components/`) instead of plain JS
- New "Ledger"-inspired visual language: `Anton` for the huge bold headline,
  `JetBrains Mono` for the code panel and nav, gold (`#E8B928`) + red (`#E24B36`)
  accents on a dark charcoal background
- The right-hand panel renders your **actual live scan result** as a
  syntax-highlighted pseudo-code block (not decorative — real API data)
- Two custom cursors: a scanning reticle (default) and a small gold fish
  hook on anything clickable — defined in `src/index.css` under
  `CUSTOM CURSORS`, as base64-encoded inline SVGs. Swap the SVGs there if
  you want to tweak the shape/color later.

## Folder structure
```
frontend-react/
  index.html
  package.json
  vite.config.js
  src/
    main.jsx
    App.jsx            <- state + API calls live here
    api.js              <- fetch wrappers for /api/scan, /api/history, /api/health
    index.css           <- all design tokens + styles + cursors
    components/
      Navbar.jsx
      Hero.jsx           <- big dynamic headline + scan form
      CodePanel.jsx       <- the live "code editor" result panel
      HistoryPanel.jsx
  public/                <- put logo.svg here (create this folder)
```

## Old vanilla frontend
Your original `frontend/` folder (plain HTML/CSS/JS) still works and is
untouched — the backend serves it automatically at `http://127.0.0.1:8000`
if you ever want to compare the two or fall back to it. The new React
version at `:5173` is the one to show your mentor.
