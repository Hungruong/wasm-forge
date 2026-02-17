# WasmForge Frontend

React web interface for the WasmForge plugin platform.

## Pages

- **Plugins** — Browse deployed plugins, see input type and AI call count
- **Builder** — Web IDE with autocomplete, templates, SDK reference sidebar
- **Runner** — Execute plugins with text, file, or JSON input
- **Models** — View available AI models (llama3, llava, mistral)

## Setup

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Connect to Backend

Edit `src/api/api.js`:

```js
const USE_MOCK = false;
const API_URL = "http://<server-ip>:8000";
```

## Tech Stack

- React + Vite
- DM Sans + JetBrains Mono fonts
- Custom autocomplete engine
- Mock API layer (toggle with `USE_MOCK`)

## Structure

```
src/
├── api/
│   ├── api.js          # API layer (mock ↔ real switch)
│   └── mock.js         # Mock data for testing
├── components/
│   └── Navbar.jsx
├── pages/
│   ├── Builder.jsx     # IDE + autocomplete + templates
│   ├── Marketplace.jsx # Plugin list
│   ├── Runner.jsx      # Plugin execution (text/file/JSON)
│   └── Models.jsx      # AI model list
├── App.jsx
├── main.jsx
└── index.css           # Full design system
```