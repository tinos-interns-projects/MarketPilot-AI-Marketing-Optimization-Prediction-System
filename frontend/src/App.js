import { useState } from "react";
import Dashboard from "./components/Dashboard";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="App">
      <div className="tab-container">
        <div className="tab-header">
          <button
            className={activeTab === "dashboard" ? "tab-active" : ""}
            onClick={() => setActiveTab("dashboard")}
          >
            📊 Dashboard
          </button>
        </div>

        {activeTab === "dashboard" && <Dashboard />}
      </div>
    </div>
  );
}

export default App;