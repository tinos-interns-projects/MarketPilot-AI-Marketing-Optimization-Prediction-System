import { useState } from "react";
import axios from "axios";
import "./Predict.css";

function Predict() {
  const [form, setForm] = useState({
    Channel: "Google",
    Campaign_Duration: "",
    Spend: ""
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const duration = parseFloat(form.Campaign_Duration) || 0;
      const spend = parseFloat(form.Spend) || 0;
      const dailySpend = duration > 0 ? spend / duration : 0;

      const res = await axios.post("http://127.0.0.1:8000/api/predict/", {
        Channel: form.Channel,
        Campaign_Duration: duration,
        Spend: spend,
        Daily_Spend: dailySpend
      });

      setResult(res.data);
    } catch (error) {
      console.error("Prediction error:", error);
      alert("Error making prediction. Please check your inputs and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="predict-container">
      <div className="predict-header">
        <h2>🎯 Campaign Predictor</h2>
        <p>Get AI-powered predictions for your marketing campaign</p>
      </div>

      <div className="form-group">
        <label htmlFor="channel">Marketing Channel</label>
        <select
          id="channel"
          name="Channel"
          value={form.Channel}
          onChange={handleChange}
        >
          <option value="Google">Google Ads</option>
          <option value="Facebook">Facebook</option>
          <option value="Instagram">Instagram</option>
          <option value="YouTube">YouTube</option>
          <option value="LinkedIn">LinkedIn</option>
          <option value="Twitter">Twitter (X)</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="campaign-duration">Campaign Duration (Days)</label>
        <input
          id="campaign-duration"
          name="Campaign_Duration"
          placeholder="Enter campaign duration (e.g., 30)"
          type="number"
          min="1"
          onChange={handleChange}
          value={form.Campaign_Duration}
        />
      </div>

      <div className="form-group">
        <label htmlFor="spend">Total Budget ($)</label>
        <input
          id="spend"
          name="Spend"
          placeholder="Enter total budget (e.g., 5000)"
          type="number"
          min="0"
          step="0.01"
          onChange={handleChange}
          value={form.Spend}
        />
      </div>

      <button
        className="predict-btn"
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? "Analyzing Campaign..." : "Get Prediction"}
      </button>

      {loading && <div className="loading-text">Processing your request...</div>}

      {result && !loading && (
        <div className="result-card">
          <h3>📊 Prediction Results</h3>
          <div className="result-item">
            <span className="result-label">Recommended Channel:</span>
            <span>{result.channel}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Success Probability:</span>
            <span>{(result.probability * 100).toFixed(1)}%</span>
          </div>
          <div className="result-item">
            <span className="result-label">Decision:</span>
            <span>{result.decision}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Click-Through Rate (CTR):</span>
            <span>{result.CTR}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Cost Per Click (CPC):</span>
            <span>${result.CPC}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Return on Investment (ROI):</span>
            <span>{result.ROI}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default Predict;