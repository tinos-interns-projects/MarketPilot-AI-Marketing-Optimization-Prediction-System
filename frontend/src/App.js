import { useState } from "react";
import Dashboard from "./components/Dashboard";
import Predict from "./components/Predict";
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
          <button 
            className={activeTab === "predict" ? "tab-active" : ""}
            onClick={() => setActiveTab("predict")}
          >
            🔮 Predict Channel
          </button>
        </div>
        
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "predict" && <Predict />}
      </div>
    </div>
  );
}

export default App;