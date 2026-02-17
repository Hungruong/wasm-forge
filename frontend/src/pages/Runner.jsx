import { useState, useEffect, useRef } from "react";
import { getPlugins, runPlugin } from "../api/api";

const INPUT_TYPES = [
  { id: "text", label: "Text" },
  { id: "file", label: "File" },
  { id: "json", label: "JSON" },
];

export default function Runner({ initialPlugin }) {
  const [plugins, setPlugins] = useState([]);
  const [selected, setSelected] = useState(initialPlugin || "");
  const [inputType, setInputType] = useState("text");
  const [textInput, setTextInput] = useState("");
  const [jsonInput, setJsonInput] = useState('{\n  "text": "",\n  "language": "vi"\n}');
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    getPlugins().then(setPlugins);
  }, []);

  useEffect(() => {
    if (initialPlugin) setSelected(initialPlugin);
  }, [initialPlugin]);

  // Auto-select input type when plugin changes
  useEffect(() => {
    const plugin = plugins.find((p) => p.name === selected);
    if (plugin && plugin.input_type) {
      setInputType(plugin.input_type);
    }
  }, [selected, plugins]);

  function getSelectedPlugin() {
    return plugins.find((p) => p.name === selected);
  }

  function handleFileChange(e) {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);

    if (f.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (ev) =>
        setFilePreview({
          type: "image",
          src: ev.target.result,
          name: f.name,
          size: f.size,
        });
      reader.readAsDataURL(f);
    } else {
      const reader = new FileReader();
      reader.onload = (ev) =>
        setFilePreview({
          type: "text",
          content: ev.target.result.substring(0, 500),
          name: f.name,
          size: f.size,
        });
      reader.readAsText(f);
    }
  }

  function removeFile() {
    setFile(null);
    setFilePreview(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  function getInputData() {
    if (inputType === "text") return textInput;
    if (inputType === "json") return jsonInput;
    if (inputType === "file" && filePreview) {
      if (filePreview.type === "image") return filePreview.src;
      return filePreview.content;
    }
    return "";
  }

  function isValidJson(str) {
    try {
      JSON.parse(str);
      return true;
    } catch {
      return false;
    }
  }

  function canRun() {
    if (!selected || loading) return false;
    if (inputType === "text" && !textInput.trim()) return false;
    if (inputType === "json" && !isValidJson(jsonInput)) return false;
    if (inputType === "file" && !file) return false;
    return true;
  }

  async function handleRun() {
    if (!canRun()) return;
    setLoading(true);
    setResult(null);
    const t0 = Date.now();

    try {
      const data = getInputData();
      const res = await runPlugin(selected, data);
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1);

      if (res.status === "success") {
        setResult({ ok: true, output: res.result, time: elapsed });
      } else {
        setResult({
          ok: false,
          output: res.message || "Execution failed",
          time: elapsed,
        });
      }
    } catch (e) {
      setResult({
        ok: false,
        output: "Connection error: " + e.message,
        time: "—",
      });
    }

    setLoading(false);
  }

  const plugin = getSelectedPlugin();

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Runner</h1>
        <p className="page-desc">
          Execute a plugin with custom input. Input type is auto-selected based
          on the plugin.
        </p>
      </div>

      <div className="runner-form">
        {/* Plugin select */}
        <div>
          <label className="label">Plugin</label>
          <select
            className="select"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">Select a plugin…</option>
            {plugins.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} — {p.description}
              </option>
            ))}
          </select>
        </div>

        {/* Plugin info banner */}
        {plugin && (
          <div className="plugin-info">
            <div className="plugin-info-row">
              <span className="plugin-info-label">Description</span>
              <span className="plugin-info-value">{plugin.description}</span>
            </div>
            <div className="plugin-info-row">
              <span className="plugin-info-label">Expects</span>
              <span className="plugin-info-value">
                {plugin.input_type === "text" && "Plain text input"}
                {plugin.input_type === "file" && "File upload (image, text, CSV)"}
                {plugin.input_type === "json" && "Structured JSON data"}
              </span>
            </div>
            {plugin.input_hint && (
              <div className="plugin-info-row">
                <span className="plugin-info-label">Hint</span>
                <span className="plugin-info-value plugin-info-hint">
                  {plugin.input_hint}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Input */}
        {selected && (
          <div>
            <label className="label">Input</label>
            <div className="input-tabs">
              {INPUT_TYPES.map((t) => (
                <button
                  key={t.id}
                  className={`input-tab ${inputType === t.id ? "input-tab-active" : ""}`}
                  onClick={() => setInputType(t.id)}
                >
                  {t.label}
                  {plugin && plugin.input_type === t.id && (
                    <span className="input-tab-rec">rec</span>
                  )}
                </button>
              ))}
            </div>

            {/* Text input */}
            {inputType === "text" && (
              <textarea
                className="textarea"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={plugin?.input_hint || "Enter text for the plugin to process…"}
                rows={6}
              />
            )}

            {/* JSON input */}
            {inputType === "json" && (
              <div>
                <textarea
                  className="textarea"
                  value={jsonInput}
                  onChange={(e) => setJsonInput(e.target.value)}
                  placeholder={plugin?.input_hint || '{"key": "value"}'}
                  rows={8}
                />
                {jsonInput && !isValidJson(jsonInput) && (
                  <div className="input-error">Invalid JSON</div>
                )}
                {jsonInput && isValidJson(jsonInput) && (
                  <div className="input-valid">Valid JSON</div>
                )}
              </div>
            )}

            {/* File input */}
            {inputType === "file" && (
              <div>
                {!file ? (
                  <div
                    className="file-drop"
                    onClick={() => fileRef.current?.click()}
                  >
                    <div className="file-drop-text">Click to select a file</div>
                    <div className="file-drop-hint">
                      {plugin?.input_hint || "Images, text files, CSV, code files"}
                    </div>
                    <input
                      ref={fileRef}
                      type="file"
                      onChange={handleFileChange}
                      style={{ display: "none" }}
                      accept="image/*,.txt,.csv,.json,.py,.js,.md,.html,.xml"
                    />
                  </div>
                ) : (
                  <div className="file-preview">
                    <div className="file-preview-header">
                      <div className="file-preview-info">
                        <span className="file-preview-name">
                          {filePreview?.name}
                        </span>
                        <span className="file-preview-size">
                          {file.size < 1024
                            ? file.size + " B"
                            : (file.size / 1024).toFixed(1) + " KB"}
                        </span>
                      </div>
                      <button className="btn btn-ghost" onClick={removeFile}>
                        Remove
                      </button>
                    </div>

                    {filePreview?.type === "image" && (
                      <img
                        src={filePreview.src}
                        alt="preview"
                        className="file-preview-image"
                      />
                    )}

                    {filePreview?.type === "text" && (
                      <pre className="file-preview-text">
                        {filePreview.content}
                        {filePreview.content.length >= 500 && "…"}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Run button */}
        <div className="runner-actions">
          <button
            className="btn btn-primary"
            onClick={handleRun}
            disabled={!canRun()}
          >
            {loading && <span className="loader" />}
            {loading ? "Running…" : "Run plugin"}
          </button>
          {loading && (
            <span
              style={{
                fontSize: 12,
                color: "var(--text-tertiary)",
                fontFamily: "var(--font-mono)",
              }}
            >
              executing in sandbox
            </span>
          )}
        </div>
      </div>

      {/* Result */}
      {result && (
        <div className="result-box">
          <div className="result-header">
            <span
              className={`result-status ${result.ok ? "success" : "error"}`}
            >
              <span className={`dot ${result.ok ? "success" : "error"}`} />
              {result.ok ? "completed" : "failed"}
            </span>
            <span className="result-time">{result.time}s</span>
          </div>
          <div className="result-body">{result.output}</div>
        </div>
      )}
    </div>
  );
}