import joblib
import numpy as np
import os
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load model and scaler
try:
    model = joblib.load(os.path.join(BASE_DIR, "ml_model/model.pkl"))
    scaler = joblib.load(os.path.join(BASE_DIR, "ml_model/scaler.pkl"))
    
    # Load feature columns
    with open(os.path.join(BASE_DIR, "ml_model/feature_cols.json"), "r") as f:
        FEATURE_COLS = json.load(f)
    
    logger.info(f"Model loaded successfully. Features: {FEATURE_COLS}")
except Exception as e:
    logger.error(f"Error loading model/scaler: {e}")
    model = None
    scaler = None
    FEATURE_COLS = []


def predict_campaign(data):
    """
    Predict campaign success probability and provide budget decision.
    
    Args:
        data (dict): Dictionary containing 'Spend', 'Campaign_Duration', 
                     'Daily_Spend', and channel indicators
    
    Returns:
        tuple: (probability: float, decision: str)
    """
    try:
        # Validate input
        required_fields = ["Spend", "Campaign_Duration", "Daily_Spend"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Extract and validate values
        spend = float(data["Spend"])
        duration = float(data["Campaign_Duration"])
        daily_spend = float(data["Daily_Spend"])
        
        if spend < 0 or duration < 0 or daily_spend < 0:
            raise ValueError("All values must be non-negative")
        
        # Prepare features (must match training order)
        features = []
        for col in FEATURE_COLS:
            if col in data:
                features.append(float(data[col]))
            elif col in ["Spend", "Campaign_Duration", "Daily_Spend"]:
                # Already included above
                pass
            else:
                # Channel column not provided, default to 0
                features.append(0.0)
                logger.warning(f"Channel feature {col} not provided, defaulting to 0")
        
        # Scale features
        X = np.array(features).reshape(1, -1)
        
        if scaler is not None:
            X = scaler.transform(X)
        
        if model is not None:
            # Get prediction probability
            prob = model.predict_proba(X)[0][1]
        else:
            # Fallback heuristic if model not available
            prob = calculate_fallback_probability(spend, duration, daily_spend)
        
        # Determine decision based on probability
        if prob > 0.7:
            decision = "Increase Budget"
        elif prob > 0.4:
            decision = "Test Campaign"
        else:
            decision = "Avoid Campaign"
        
        logger.info(f"Prediction: prob={prob:.3f}, decision={decision}")
        return prob, decision
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        # Return safe defaults on error
        return 0.5, "Test Campaign"


def calculate_fallback_probability(spend, duration, daily_spend):
    """
    Calculate probability using heuristic rules when model is unavailable.
    """
    # Heuristic scoring based on spend efficiency
    score = 0.5  # Base score
    
    # Daily spend efficiency
    if daily_spend < 500:
        score += 0.2
    elif daily_spend > 5000:
        score -= 0.2
    
    # Duration factor (longer campaigns get slight bonus)
    if duration > 30:
        score += 0.1
    elif duration < 7:
        score -= 0.1
    
    # Total spend threshold
    if spend > 10000:
        score += 0.1
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, score))


def calculate_campaign_roi(spend, duration, conversions=None):
    """
    Calculate campaign ROI metrics.
    
    Args:
        spend (float): Total spend
        duration (float): Campaign duration in days
        conversions (int, optional): Number of conversions
    
    Returns:
        dict: Dictionary containing ROI metrics
    """
    daily_spend = spend / (duration + 1)
    
    metrics = {
        'daily_spend': round(daily_spend, 2),
        'spend': round(spend, 2),
        'duration': duration
    }
    
    if conversions is not None:
        avg_conversion_value = 100
        revenue = conversions * avg_conversion_value
        roi = (revenue - spend) / (spend + 1)
        metrics['ROI'] = round(roi, 3)
        metrics['revenue'] = round(revenue, 2)
        metrics['conversions'] = conversions
    
    return metrics


def check_model_health():
    """
    Check if the model and scaler are loaded correctly.
    
    Returns:
        dict: Health check results
    """
    health = {
        'model_loaded': model is not None,
        'scaler_loaded': scaler is not None,
        'features_loaded': len(FEATURE_COLS) > 0
    }
    
    if model is not None:
        health['model_type'] = type(model).__name__
        health['n_features'] = model.n_features_in_
    
    # Test prediction with sample data
    try:
        test_data = {
            "Spend": 2000,
            "Campaign_Duration": 14,
            "Daily_Spend": 142.86
        }
        prob, decision = predict_campaign(test_data)
        health['test_prediction'] = 'success'
        health['test_probability'] = prob
    except Exception as e:
        health['test_prediction'] = f'failed: {str(e)}'
    
    return health