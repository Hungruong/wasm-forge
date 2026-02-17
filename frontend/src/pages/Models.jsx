import { useState, useEffect } from "react";
import { getModels } from "../api/api";

const TAG_CLASS = {
  text: "tag-text",
  vision: "tag-vision",
  code: "tag-code",
};

export default function Models() {
  const [models, setModels] = useState([]);

  useEffect(() => {
    getModels().then(setModels);
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Models</h1>
        <p className="page-desc">
          Available AI models on the platform. Reference these names when
          calling{" "}
          <code className="code-inline">call_ai()</code> in your plugin.
        </p>
      </div>

      {models.length === 0 ? (
        <div className="empty">Loading models…</div>
      ) : (
        <div className="card-grid">
          {models.map((m) => (
            <div key={m.name} className="card">
              <div className="card-info">
                <div className="card-name">{m.name}</div>
                <div className="card-desc">{m.description}</div>
              </div>
              <div className="card-meta">
                <span className={`tag ${TAG_CLASS[m.type] || "tag-text"}`}>
                  {m.type}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}