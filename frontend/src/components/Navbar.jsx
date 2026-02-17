export default function Navbar({ page, setPage }) {
  const links = [
    { id: "marketplace", label: "Plugins" },
    { id: "builder", label: "Builder" },
    { id: "runner", label: "Runner" },
    { id: "models", label: "Models" },
  ];

  return (
    <nav className="nav">
      <div className="nav-logo">
        wasmforge<span>/</span>
      </div>
      <div className="nav-links">
        {links.map((l) => (
          <button
            key={l.id}
            className={`nav-link ${page === l.id ? "active" : ""}`}
            onClick={() => setPage(l.id)}
          >
            {l.label}
          </button>
        ))}
      </div>
    </nav>
  );
}