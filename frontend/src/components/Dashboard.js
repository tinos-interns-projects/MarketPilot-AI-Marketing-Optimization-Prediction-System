import { useState } from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import "./dashboard.css";

function Dashboard() {
  const [form, setForm] = useState({
    Campaign_Duration: "",
    Spend: ""
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const predict = async () => {
    setLoading(true);
    try {
      const res = await axios.post("http://127.0.0.1:8000/api/predict/", {
        Spend: form.Spend,
        Campaign_Duration: form.Campaign_Duration
      });
      setResult(res.data);
    } catch (error) {
      console.error("Prediction error:", error);
      alert("Error making prediction. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const chartData = result ? result.results.map(r => ({
    channel: r.channel,
    ROI: r.ROI
  })) : [];

  return (
    <div className="dashboard">
      <div className="header">
        <h1>🚀 Marketing Intelligence Platform</h1>
        <p>AI-powered channel optimization for maximum ROI</p>
      </div>

      {/* CHART */}
      <div className="section">
        <h3>📈 ROI Prediction by Channel</h3>
        <div className="chart-container">
          {result && chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <XAxis dataKey="channel" tick={{ fontSize: 12, fill: '#555' }} />
                <YAxis tick={{ fontSize: 12, fill: '#555' }} />
                <Tooltip 
                  formatter={(value) => `${value}%`}
                  contentStyle={{ background: '#fff', border: '1px solid #eee', padding: '8px', borderRadius: '4px' }}
                  labelStyle={{ fontWeight: 600, color: '#333' }}
                  wrapperStyle={{ pointerEvents: 'none' }}
                >
                  {(props) => <div style={{ pointerEvents: 'all' }} {...props} />}
                </Tooltip>
                <Bar dataKey="ROI" 
                     fill={(props) => {
                       // Color based on ROI value
                       if (props.data.ROI > 0.1) return '#00b894';
                       if (props.data.ROI > 0) return '#fdcb6e';
                       return '#e17055';
                     }} 
                     barSize={25}
                     radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="loading">Enter campaign details to see ROI predictions</div>
          )}
        </div>
      </div>

      {/* INPUT SECTION */}
      <div className="section">
        <h3>🔮 Campaign Predictor</h3>
        <div className="input-group">
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
        
        <div className="input-group">
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
          className="btn btn-primary" 
          onClick={predict} 
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Get Channel Predictions"}
        </button>
      </div>

      {/* RESULTS GRID */}
      {result && result.results && (
        <>
          <div className="section">
            <h3>📊 Detailed Channel Analysis</h3>
            <div className="results-grid">
              {result.results.map((item, index) => (
                <div key={index} className="channel-result">
                  <h4>{item.channel}</h4>
                  <p>CTR: <span>{item.CTR}</span></p>
                  <p>CPC: <span>${item.CPC}</span></p>
                  <p>ROI: <span>{item.ROI}</span></p>
                  <p>Probability: <span>{(item.probability * 100).toFixed(1)}%</span></p>
                </div>
              ))}
            </div>
          </div>

          {/* BEST CHANNEL HIGHLIGHT */}
          <div className="section">
            <h3>🏆 Recommended Channel</h3>
            <div className="best-channel">
              <h2>{result.best_channel.channel}</h2>
              <p>Highest Predicted ROI: {result.best_channel.ROI}</p>
              <p>Success Probability: {(result.best_channel.probability * 100).toFixed(1)}%</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;