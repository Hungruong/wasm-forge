import { useState, useEffect } from "react";
import { getPlugins } from "../api/api";

const INPUT_LABELS = {
  text: "text",
  file: "file",
  json: "JSON",
};

export default function Marketplace({ onRun }) {
  const [plugins, setPlugins] = useState([]);

  useEffect(() => {
    getPlugins().then(setPlugins);
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Plugins</h1>
        <p className="page-desc">
          Browse deployed plugins. Each plugin shows what input it expects and
          how many AI calls it makes.
        </p>
      </div>

      {plugins.length === 0 ? (
        <div className="empty">
          No plugins deployed yet. Create one in Builder.
        </div>
      ) : (
        <div className="card-grid">
          {plugins.map((p) => (
            <div key={p.name} className="card">
              <div className="card-info">
                <div className="card-name">{p.name}</div>
                <div className="card-desc">{p.description}</div>
                <div className="card-tags">
                  <span className="tag tag-input">
                    {INPUT_LABELS[p.input_type] || p.input_type}
                  </span>
                  <span className="tag tag-calls">
                    {p.calls} AI call{p.calls > 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <div className="card-meta">
                <button
                  className="btn btn-ghost"
                  onClick={() => onRun(p.name)}
                >
                  Run
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}