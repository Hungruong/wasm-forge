import { useState, useRef, useEffect } from "react";
import { uploadPlugin, getModels } from "../api/api";

const DEFAULT_CODE = `# ══════════════════════════════════════════════
# WasmForge Plugin Template
# ══════════════════════════════════════════════
#
# Your plugin runs inside a secure WASM sandbox.
# Use the platform SDK to access AI models.
#
# REQUIRED STRUCTURE:
#   1. Import SDK functions
#   2. Read input with get_input()
#   3. Process data (use call_ai for AI tasks)
#   4. Return result with send_output()
#
# AVAILABLE FUNCTIONS:
#   call_ai(model, prompt)  → Call AI model, returns string
#   get_input()             → Read user input
#   send_output(result)     → Return result to user
#   list_models()           → Get available model names
#
# ══════════════════════════════════════════════

from platform_sdk import call_ai, get_input, send_output

# Step 1: Read user input
text = get_input()

# Step 2: Call AI model
result = call_ai("qwen2.5:1.5b", "Summarize the following text: " + text)

# Step 3: Return result
send_output(result)
`;

const SDK_FNS = [
  { name: "call_ai(model, prompt)", desc: "Call an AI model, returns response string", insert: 'call_ai("qwen2.5:1.5b", "")' },
  { name: "get_input()", desc: "Read user-provided input", insert: "get_input()" },
  { name: "send_output(result)", desc: "Return final result to user", insert: "send_output(result)" },
  { name: "list_models()", desc: "Get list of available model names", insert: "list_models()" },
];

const TAG_CLASS = {
  text: "tag-text",
  vision: "tag-vision",
  code: "tag-code",
};

// Static autocomplete items (SDK functions + import)
const STATIC_AC_ITEMS = [
  { trigger: "call_ai", label: 'call_ai("model", "prompt")', insert: 'call_ai("", "")', type: "function" },
  { trigger: "get_input", label: "get_input()", insert: "get_input()", type: "function" },
  { trigger: "send_output", label: "send_output(result)", insert: "send_output()", type: "function" },
  { trigger: "list_models", label: "list_models()", insert: "list_models()", type: "function" },
  { trigger: "from platform_sdk", label: "from platform_sdk import ...", insert: "from platform_sdk import call_ai, get_input, send_output", type: "import" },
  { trigger: "platform_sdk", label: "from platform_sdk import ...", insert: "from platform_sdk import call_ai, get_input, send_output", type: "import" },
];

const TEMPLATES = [
  {
    name: "Simple",
    code: `from platform_sdk import call_ai, get_input, send_output

text = get_input()
result = call_ai("qwen2.5:1.5b", "Summarize the following text: " + text)
send_output(result)
`,
  },
  {
    name: "Multi-step",
    code: `from platform_sdk import call_ai, get_input, send_output
import json

text = get_input()

# Step 1: AI analysis
analysis = call_ai("qwen2.5:1.5b", "Rate this text's sentiment 0-10. Reply with just the number: " + text)

# Step 2: Your logic (no AI needed)
score = 0
for word in analysis.split():
    try:
        score = float(word)
        break
    except:
        pass

if score > 7:
    mood = "positive"
elif score > 4:
    mood = "neutral"
else:
    mood = "negative"

# Step 3: AI generates report
report = call_ai("qwen2.5:1.5b", f"Write a brief sentiment report. Text: {text}. Mood: {mood}")

send_output(json.dumps({
    "mood": mood,
    "score": score,
    "report": report
}, indent=2))
`,
  },
  {
    name: "Translate",
    code: `from platform_sdk import call_ai, get_input, send_output

text = get_input()
result = call_ai("qwen2.5:1.5b", "Translate the following text to Vietnamese: " + text)
send_output(result)
`,
  },
  {
    name: "Code review",
    code: `from platform_sdk import call_ai, get_input, send_output
import json

code = get_input()

bugs = call_ai("mistral:latest", "Find bugs in this code. Be concise: " + code)
security = call_ai("mistral:latest", "Check for security vulnerabilities. Be concise: " + code)
suggestions = call_ai("mistral:latest", "Suggest improvements. Be concise: " + code)

send_output(json.dumps({
    "bugs": bugs,
    "security": security,
    "suggestions": suggestions
}, indent=2))
`,
  },
];

export default function Builder() {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [pluginName, setPluginName] = useState("");
  const [pluginDesc, setPluginDesc] = useState("");
  const [pluginInputType, setPluginInputType] = useState("text");
  const [pluginInputHint, setPluginInputHint] = useState("");
  const [status, setStatus] = useState(null);
  const [showAC, setShowAC] = useState(false);
  const [acItems, setAcItems] = useState([]);
  const [acIndex, setAcIndex] = useState(0);
  const [acPos, setAcPos] = useState({ top: 0, left: 0 });
  const [wordStart, setWordStart] = useState(0);
  const [models, setModels] = useState([]);
  const editorRef = useRef(null);

  // Fetch models from API on mount
  useEffect(() => {
    getModels()
      .then(setModels)
      .catch(() => setModels([]));
  }, []);

  // Build autocomplete items dynamically from fetched models
  const autocompleteItems = [
    ...STATIC_AC_ITEMS,
    ...models.map((m) => ({
      trigger: m.name,
      label: `"${m.name}" — ${m.description}`,
      insert: `"${m.name}"`,
      type: "model",
    })),
  ];

  function getWordAtCursor(text, cursorPos) {
    let start = cursorPos;
    while (start > 0 && /[a-zA-Z0-9_.:'"']/.test(text[start - 1])) {
      start--;
    }
    return { word: text.substring(start, cursorPos), start };
  }

  function handleInput(e) {
    const val = e.target.value;
    setCode(val);

    const el = e.target;
    const cursorPos = el.selectionStart;
    const { word, start } = getWordAtCursor(val, cursorPos);

    if (word.length >= 2) {
      const lowerWord = word.toLowerCase().replace(/"/g, "");
      const matches = autocompleteItems.filter((item) =>
        item.trigger.toLowerCase().startsWith(lowerWord)
      );

      if (matches.length > 0) {
        const lines = val.substring(0, cursorPos).split("\n");
        const lineNum = lines.length - 1;
        const colNum = lines[lineNum].length;

        setAcItems(matches);
        setAcIndex(0);
        setWordStart(start);
        setAcPos({
          top: (lineNum + 1) * 19 + 48,
          left: Math.min(colNum * 6.9 + 16, 400),
        });
        setShowAC(true);
        return;
      }
    }

    setShowAC(false);
  }

  function applyAutocomplete(item) {
    const el = editorRef.current;
    const cursorPos = el.selectionStart;
    const before = code.substring(0, wordStart);
    const after = code.substring(cursorPos);
    const newCode = before + item.insert + after;
    setCode(newCode);
    setShowAC(false);

    setTimeout(() => {
      const newPos = wordStart + item.insert.length;
      el.selectionStart = el.selectionEnd = newPos;
      el.focus();
    }, 0);
  }

  function insertAtCursor(text) {
    const el = editorRef.current;
    if (!el) return;
    const pos = el.selectionStart;
    const newCode = code.substring(0, pos) + text + code.substring(pos);
    setCode(newCode);
    setTimeout(() => {
      el.selectionStart = el.selectionEnd = pos + text.length;
      el.focus();
    }, 0);
  }

  function handleKeyDown(e) {
    if (showAC) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setAcIndex((i) => Math.min(i + 1, acItems.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setAcIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Tab" || e.key === "Enter") {
        e.preventDefault();
        applyAutocomplete(acItems[acIndex]);
        return;
      }
      if (e.key === "Escape") {
        setShowAC(false);
        return;
      }
    }

    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.target;
      const start = el.selectionStart;
      const end = el.selectionEnd;
      const newVal = code.substring(0, start) + "    " + code.substring(end);
      setCode(newVal);
      setTimeout(() => {
        el.selectionStart = el.selectionEnd = start + 4;
      }, 0);
    }
  }

  async function handleDeploy() {
    if (!pluginName.trim()) {
      setStatus({ ok: false, msg: "Enter a plugin name" });
      return;
    }
    if (!pluginDesc.trim()) {
      setStatus({ ok: false, msg: "Enter a description so users know what your plugin does" });
      return;
    }
    setStatus({ ok: null, msg: "Deploying…" });
    try {
      await uploadPlugin(pluginName.trim(), code, {
        description: pluginDesc,
        input_type: pluginInputType,
        input_hint: pluginInputHint,
      });
      setStatus({ ok: true, msg: `${pluginName}.py deployed` });
    } catch (e) {
      setStatus({ ok: false, msg: "Deploy failed" });
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Builder</h1>
        <p className="page-desc">
          Write a plugin using the platform SDK. Fill in the details below so
          users understand how to use your plugin.
        </p>
      </div>

      <div className="builder-layout">
        {/* Left: Editor */}
        <div>
          <div className="builder-editor">
            <div className="editor-toolbar">
              <span className="editor-filename">
                {pluginName || "untitled"}.py
              </span>
              <div className="template-bar">
                <span className="editor-toolbar-label">templates</span>
                {TEMPLATES.map((t) => (
                  <button
                    key={t.name}
                    className="template-btn"
                    onClick={() => setCode(t.code)}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ position: "relative" }}>
              <textarea
                ref={editorRef}
                className="editor-area"
                value={code}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                onBlur={() => setTimeout(() => setShowAC(false), 150)}
                spellCheck={false}
              />

              {showAC && acItems.length > 0 && (
                <div
                  className="ac-dropdown"
                  style={{ top: acPos.top, left: acPos.left }}
                >
                  {acItems.map((item, i) => (
                    <div
                      key={item.trigger + item.type}
                      className={`ac-item ${i === acIndex ? "ac-active" : ""}`}
                      onMouseDown={() => applyAutocomplete(item)}
                      onMouseEnter={() => setAcIndex(i)}
                    >
                      <span className={`ac-icon ac-icon-${item.type}`}>
                        {item.type === "function"
                          ? "f"
                          : item.type === "model"
                          ? "m"
                          : "i"}
                      </span>
                      <span className="ac-label">{item.label}</span>
                    </div>
                  ))}
                  <div className="ac-hint">Tab to insert</div>
                </div>
              )}
            </div>
          </div>

          {/* Deploy metadata form */}
          <div className="deploy-form">
            <div className="deploy-field">
              <label className="label">Plugin name</label>
              <input
                className="input"
                value={pluginName}
                onChange={(e) =>
                  setPluginName(
                    e.target.value.replace(/[^a-z0-9_]/gi, "").toLowerCase()
                  )
                }
                placeholder="my_plugin"
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </div>
            <div className="deploy-field">
              <label className="label">Input type</label>
              <select
                className="select"
                value={pluginInputType}
                onChange={(e) => setPluginInputType(e.target.value)}
              >
                <option value="text">Text — plain text input</option>
                <option value="file">File — image or file upload</option>
                <option value="json">JSON — structured data</option>
              </select>
            </div>
            <div className="deploy-field">
              <label className="label">&nbsp;</label>
              <button className="btn btn-primary" onClick={handleDeploy} style={{ width: "100%" }}>
                Deploy
              </button>
            </div>
            <div className="deploy-field-full">
              <label className="label">Description</label>
              <input
                className="input"
                value={pluginDesc}
                onChange={(e) => setPluginDesc(e.target.value)}
                placeholder="What does your plugin do? (shown to users in marketplace)"
              />
            </div>
            <div className="deploy-field-full">
              <label className="label">Input hint (optional)</label>
              <input
                className="input"
                value={pluginInputHint}
                onChange={(e) => setPluginInputHint(e.target.value)}
                placeholder="e.g. Paste any English text you want translated to Vietnamese"
              />
            </div>
          </div>

          {status && (
            <div
              className={`deploy-msg ${
                status.ok === true
                  ? "success"
                  : status.ok === false
                  ? "error"
                  : ""
              }`}
            >
              {status.msg}
            </div>
          )}
        </div>

        {/* Right: Sidebar */}
        <div className="builder-sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">Getting Started</div>
            <div className="sidebar-body">
              <div className="guide-steps">
                <div className="guide-step">
                  <span className="guide-num">1</span>
                  <span className="guide-text">
                    Read input with <code>get_input()</code>
                  </span>
                </div>
                <div className="guide-step">
                  <span className="guide-num">2</span>
                  <span className="guide-text">
                    Process with <code>call_ai(model, prompt)</code>
                  </span>
                </div>
                <div className="guide-step">
                  <span className="guide-num">3</span>
                  <span className="guide-text">
                    Return with <code>send_output(result)</code>
                  </span>
                </div>
                <div className="guide-step">
                  <span className="guide-num">4</span>
                  <span className="guide-text">
                    Fill in name, description, input type below editor
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">SDK Functions — click to insert</div>
            <div className="sidebar-body">
              {SDK_FNS.map((fn) => (
                <div
                  key={fn.name}
                  className="sdk-fn sdk-fn-clickable"
                  onClick={() => insertAtCursor(fn.insert)}
                >
                  <div className="sdk-fn-name">{fn.name}</div>
                  <div className="sdk-fn-desc">{fn.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">Models — click to insert</div>
            <div className="sidebar-body">
              {models.length === 0 ? (
                <div style={{ color: "var(--text-dim)", fontSize: "0.85rem", padding: "0.5rem 0" }}>
                  Loading models…
                </div>
              ) : (
                models.map((m) => (
                  <div
                    key={m.name}
                    className="model-item model-item-clickable"
                    onClick={() => insertAtCursor(`call_ai("${m.name}", "")`)}
                    style={{ opacity: m.available === false ? 0.5 : 1 }}
                  >
                    <div>
                      <span className="model-name">
                        {m.name}
                        {m.available === false && (
                          <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", marginLeft: "0.5rem" }}>
                            (unavailable)
                          </span>
                        )}
                      </span>
                      <div className="model-hint">{m.description}</div>
                    </div>
                    <span className={`tag ${TAG_CLASS[m.type] || "tag-text"}`}>
                      {m.type}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}