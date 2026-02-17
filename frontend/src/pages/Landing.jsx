import { useState, useEffect } from "react";

export default function Landing({ onNavigate }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
  }, []);

  return (
    <div className={`landing ${visible ? "landing-visible" : ""}`}>
      {/* Hero */}
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-badge">WASM-powered AI plugin platform</div>
          <h1 className="hero-title">
            Write AI plugins.
            <br />
            <span className="hero-accent">We handle the rest.</span>
          </h1>
          <p className="hero-desc">
            WasmForge runs your Python plugins inside secure WASM sandboxes
            with access to GPU-accelerated AI models. No infrastructure, no
            DevOps, no security headaches.
          </p>
          <div className="hero-actions">
            <button
              className="btn btn-primary btn-lg"
              onClick={() => onNavigate("builder")}
            >
              Start building
            </button>
            <button
              className="btn btn-ghost btn-lg"
              onClick={() => onNavigate("marketplace")}
            >
              Browse plugins
            </button>
          </div>

          <div className="hero-code">
            <div className="hero-code-header">
              <span className="hero-code-dot"></span>
              <span className="hero-code-dot"></span>
              <span className="hero-code-dot"></span>
              <span className="hero-code-filename">summarize.py</span>
            </div>
            <pre className="hero-code-body">
              <span className="c-kw">from</span>{" "}
              <span className="c-mod">platform_sdk</span>{" "}
              <span className="c-kw">import</span> call_ai, get_input, send_output{"\n"}
              {"\n"}
              text = <span className="c-fn">get_input</span>(){"\n"}
              result = <span className="c-fn">call_ai</span>(<span className="c-str">"llama3"</span>, <span className="c-str">"Summarize: "</span> + text){"\n"}
              <span className="c-fn">send_output</span>(result)
            </pre>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="section">
        <div className="section-inner">
          <h2 className="section-title">How it works</h2>
          <p className="section-desc">
            From idea to production in three steps. Write Python, deploy with
            one click, and let users run it.
          </p>
          <div className="steps-grid">
            <div className="step">
              <div className="step-num">01</div>
              <h3 className="step-title">Write</h3>
              <p className="step-desc">
                Write a Python plugin in the browser IDE. Call AI models with
                one function.
              </p>
            </div>
            <div className="step-arrow">→</div>
            <div className="step">
              <div className="step-num">02</div>
              <h3 className="step-title">Deploy</h3>
              <p className="step-desc">
                Click deploy. Your plugin is live in the marketplace instantly.
              </p>
            </div>
            <div className="step-arrow">→</div>
            <div className="step">
              <div className="step-num">03</div>
              <h3 className="step-title">Run</h3>
              <p className="step-desc">
                Users run your plugin with their data inside a secure WASM
                sandbox.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="section section-dark">
        <div className="section-inner">
          <h2 className="section-title">Secure by design</h2>
          <p className="section-desc">
            Plugins run inside WebAssembly sandboxes with zero network access.
            AI requests flow through a controlled stdin/stdout bridge.
          </p>
          <div className="arch-diagram">
            <div className="arch-box">
              <div className="arch-label">WASM Sandbox</div>
              <div className="arch-detail">No network. No filesystem.</div>
              <div className="arch-detail">Only stdin/stdout.</div>
            </div>
            <div className="arch-arrow">
              <span className="arch-arrow-label">stdin/stdout</span>
              <span className="arch-arrow-icon">→</span>
            </div>
            <div className="arch-box">
              <div className="arch-label">API Server</div>
              <div className="arch-detail">Validates requests.</div>
              <div className="arch-detail">Rate limits. Routes.</div>
            </div>
            <div className="arch-arrow">
              <span className="arch-arrow-label">http</span>
              <span className="arch-arrow-icon">→</span>
            </div>
            <div className="arch-box">
              <div className="arch-label">GPU Instance</div>
              <div className="arch-detail">Ollama inference.</div>
              <div className="arch-detail">llama3 · llava · mistral</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="section">
        <div className="section-inner">
          <h2 className="section-title">What you get</h2>
          <p className="section-desc">
            Everything developers need to build, deploy, and run AI-powered
            plugins on the cloud.
          </p>
          <div className="features-grid">
            <div className="feature">
              <div className="feature-icon">{`{ }`}</div>
              <h3 className="feature-title">Browser IDE</h3>
              <p className="feature-desc">
                Editor with autocomplete for SDK functions and model names.
                Pre-built templates to start fast.
              </p>
            </div>
            <div className="feature">
              <div className="feature-icon">▣</div>
              <h3 className="feature-title">WASM Isolation</h3>
              <p className="feature-desc">
                Each plugin runs in its own WebAssembly sandbox. No network, no
                filesystem access.
              </p>
            </div>
            <div className="feature">
              <div className="feature-icon">◈</div>
              <h3 className="feature-title">GPU Inference</h3>
              <p className="feature-desc">
                Access llama3, llava, and mistral through a single function
                call. GPU scheduling handled.
              </p>
            </div>
            <div className="feature">
              <div className="feature-icon">⬡</div>
              <h3 className="feature-title">Marketplace</h3>
              <p className="feature-desc">
                Deploy once, run anywhere. Users browse, select, and execute
                plugins with their own data.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="section section-cta">
        <div className="section-inner">
          <h2 className="section-title">Start building</h2>
          <p className="section-desc">
            Write your first AI plugin in under 5 minutes. No setup, no
            configuration.
          </p>
          <div className="hero-actions" style={{ justifyContent: "center" }}>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => onNavigate("builder")}
            >
              Open Builder
            </button>
            <button
              className="btn btn-ghost btn-lg"
              onClick={() => onNavigate("models")}
            >
              View models
            </button>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        WasmForge — Built on Akamai Cloud
      </footer>
    </div>
  );
}