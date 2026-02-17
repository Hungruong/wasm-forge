import { useState } from "react";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import Models from "./pages/Models";
import Marketplace from "./pages/Marketplace";
import Runner from "./pages/Runner";
import Builder from "./pages/Builder";

export default function App() {
  const [page, setPage] = useState("landing");
  const [runPlugin, setRunPlugin] = useState("");

  function handleRunFromMarketplace(name) {
    setRunPlugin(name);
    setPage("runner");
  }

  return (
    <>
      {page !== "landing" && <Navbar page={page} setPage={setPage} />}
      {page === "landing" && <Landing onNavigate={setPage} />}
      {page === "marketplace" && (
        <Marketplace onRun={handleRunFromMarketplace} />
      )}
      {page === "builder" && <Builder />}
      {page === "runner" && <Runner initialPlugin={runPlugin} />}
      {page === "models" && <Models />}
    </>
  );
}