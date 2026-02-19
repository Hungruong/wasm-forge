# WasmForge Frontend

React app for building, deploying, and running AI plugins. Talks to the backend API over HTTP.

## Quick start (just want to use it?)

The backend is deployed on a Linode server. You don't need to install Python, Ollama, PostgreSQL, or WasmEdge. Just run the frontend:

```bash
git clone <repo-url>
cd wasm-forge/frontend
npm install
npm run dev
```

Make sure `src/api/api.js` has:
```js
const USE_MOCK = false;
const API_URL = "http://172.234.27.110:8000";
```

Open `http://localhost:5173`. That's it. Builder, Runner, Plugins, Models — all working.

Only need Node.js 18+ installed. Get it from https://nodejs.org if you don't have it.

**If the backend is down** (pages load but models/plugins don't show up), someone needs to start the server. See the [backend README](../backend/README.md) "Starting the server" section — just SSH in and run one command.

---

## Pages

**Landing** — explains what WasmForge is, architecture diagram, quick start.

**Plugins (Marketplace)** — lists everything deployed in the database. Each card shows the plugin name, what kind of input it takes, how many AI calls it makes. Click "Run" to jump straight to the Runner.

**Builder** — a web code editor with autocomplete for SDK functions and model names. Pick a template, edit the code, fill in name/description/input type, hit Deploy. The plugin goes to PostgreSQL and shows up in the marketplace immediately.

**Runner** — pick a plugin from the dropdown, paste your input, hit Run. The backend executes it inside WasmEdge and streams the result back. Shows execution time and error messages if something goes wrong.

**Models** — shows what AI models are loaded in Ollama. Green dot = running and available, grey = not pulled or not loaded.

## Setup

Needs Node.js 18+.

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`.

## Connecting to the backend

Edit `src/api/api.js`:

```js
const USE_MOCK = false;
const API_URL = "http://172.234.27.110:8000";
```

With `USE_MOCK = true`, everything runs off local mock data — useful for working on the UI without a server. Set it to `false` and point `API_URL` to your backend to go live.

## Structure

```
src/
├── api/
│   ├── api.js          — all backend calls (getModels, runPlugin, etc.)
│   └── mock.js         — fake data for offline dev
├── components/
│   └── Navbar.jsx
├── pages/
│   ├── Landing.jsx
│   ├── Builder.jsx     — code editor + autocomplete + deploy form
│   ├── Marketplace.jsx — plugin grid
│   ├── Runner.jsx      — execute plugins
│   └── Models.jsx      — AI model status
├── App.jsx             — routing between pages
├── main.jsx            — React entry
└── index.css           — all styles (dark theme, custom properties)
```

No Tailwind, no component library. Everything is plain CSS with custom properties in `index.css`:

```css
--bg:      #0a0a0f;
--surface: #12121a;
--accent:  #6c5ce7;
--green:   #2ecc71;
--red:     #e74c3c;
```

Fonts: DM Sans for body, JetBrains Mono for code.

## API calls

All in `src/api/api.js`. The functions:

```js
getModels()                          // GET /api/models/list
getPlugins()                         // GET /api/plugins/list
getPluginCode(name)                  // GET /api/plugins/{name}/code
uploadPlugin(name, code, metadata)   // POST /api/plugins/upload
deletePlugin(name)                   // DELETE /api/plugins/{name}
runPlugin(pluginName, inputData)     // POST /api/plugins/run
```

`uploadPlugin` sends a multipart form with the `.py` file blob + metadata fields (description, input_type, input_hint).

`runPlugin` returns `{ success, output, error, error_type }`.

## Building for production

```bash
npm run build
```

Static files land in `dist/`. Serve with nginx, Apache, or any static file server.

## Testing

With mock data (no backend needed):
```bash
# set USE_MOCK = true in api.js
npm run dev
# click through all pages, everything works offline
```

With real backend:
```bash
# set USE_MOCK = false, point API_URL to your server
npm run dev
```

Things to check:
- Models page loads 4 models with correct availability
- Builder autocomplete triggers when typing `call_ai`, `get_input`, etc.
- Deploying a plugin from Builder shows up in Plugins page
- Running a plugin in Runner shows output and execution time
- Running a malicious plugin shows an error (sandbox blocked it)

## Common issues

**Page is blank after switching to real API** — open browser console (F12), look for CORS errors. Backend must have CORS configured for your frontend origin.

**Models not loading** — check that `API_URL` is correct and the backend is actually running. Try `curl.exe http://your-server:8000/api/models/list` from PowerShell.

**Still seeing mock data** — make sure `USE_MOCK = false` and restart the dev server (`npm run dev` again).

**`npm run dev` fails** — check Node version with `node -v`, needs 18+. If modules are broken, delete `node_modules` and `npm install` again.