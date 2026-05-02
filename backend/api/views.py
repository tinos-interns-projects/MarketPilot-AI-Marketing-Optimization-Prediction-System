from rest_framework.decorators import api_view
from rest_framework.response import Response
from .model_loader import model, scaler, FEATURE_COLS
import numpy as np

CHANNELS = ["Google", "Facebook", "Instagram", "YouTube", "LinkedIn", "Twitter"]
ALL_CHANNELS = ["Google", "Facebook", "Instagram", "YouTube", "LinkedIn", "Twitter"]

def prepare_features(spend, days):
    daily_spend = spend / (days + 1)
    return [spend, days, daily_spend]

def encode_channel(ch):
    # drop_first=True → Google is base (all zeros)
    return [
        1 if ch == "Facebook" else 0,
        1 if ch == "Instagram" else 0,
        1 if ch == "YouTube" else 0,
        1 if ch == "LinkedIn" else 0,
        1 if ch == "Twitter" else 0,
    ]

@api_view(['POST'])
def predict(request):
    spend = float(request.data["Spend"])
    days = float(request.data["Campaign_Duration"])

    results = []

    for ch in CHANNELS:
        features = prepare_features(spend, days)
        channel_vec = encode_channel(ch)
        features.extend(channel_vec)

        X = np.array(features).reshape(1, -1)
        X = scaler.transform(X)

        prob = model.predict_proba(X)[0][1]

        ctr = round(prob * 0.1, 3)
        cpc = round(spend / (prob * 100 + 1), 2)
        roi = round(prob - 0.5, 3)

        results.append({
            "channel": ch,
            "probability": round(prob, 3),
            "CTR": ctr,
            "CPC": cpc,
            "ROI": roi
        })

    best = max(results, key=lambda x: x["ROI"])

    return Response({
        "results": results,
        "best_channel": best
    })


@api_view(['POST'])
def optimize_budget(request):
    """
    Optimize budget allocation across multiple channels to maximize ROI.
    
    Request body:
    {
        "total_budget": 10000,
        "channels": [
            {
                "name": "Google",
                "duration": 30,
                "spend": 5000,
                "conversions": 50
            },
            {
                "name": "Facebook",
                "duration": 30,
                "spend": 3000,
                "conversions": 30
            }
        ]
    }
    
    Returns optimized allocation with expected outcomes.
    """
    try:
        data = request.data
        total_budget = float(data.get('total_budget', 10000))
        channels = data.get('channels', [])
        
        if not channels:
            return Response(
                {"error": "No channels provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate performance metrics for each channel
        channel_metrics = []
        for channel in channels:
            name = channel.get('name', 'Unknown')
            duration = channel.get('duration', 30)
            spend = channel.get('spend', 0)
            conversions = channel.get('conversions', 0)
            
            # Calculate daily spend
            daily_spend = spend / (duration + 1) if duration > 0 else 0
            
            # Predict success probability for this channel
            predict_data = {
                "Spend": spend,
                "Campaign_Duration": duration,
                "Daily_Spend": daily_spend
            }
            
            # Add channel indicator
            predict_data[f"Channel_{name}"] = 1.0
            
            prob, decision = predict_campaign(predict_data)
            
            # Calculate ROI
            avg_conversion_value = 100
            revenue = conversions * avg_conversion_value
            current_roi = (revenue - spend) / (spend + 1)
            
            # Efficiency score: combines probability and ROI
            efficiency_score = prob * (1 + max(0, current_roi))
            
            channel_metrics.append({
                'name': name,
                'duration': duration,
                'current_spend': spend,
                'daily_spend': round(daily_spend, 2),
                'conversions': conversions,
                'current_roi': round(current_roi, 3),
                'success_probability': round(prob, 3),
                'decision': decision,
                'efficiency_score': round(efficiency_score, 4)
            })
        
        # Sort channels by efficiency score (descending)
        channel_metrics.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
        # Allocate budget proportionally to efficiency
        total_efficiency = sum(c['efficiency_score'] for c in channel_metrics)
        
        if total_efficiency == 0:
            # Equal allocation if no efficiency
            equal_share = total_budget / len(channel_metrics)
            for cm in channel_metrics:
                cm['recommended_spend'] = round(equal_share, 2)
        else:
            # Allocate proportionally
            for cm in channel_metrics:
                allocation_ratio = cm['efficiency_score'] / total_efficiency
                recommended = total_budget * allocation_ratio
                
                # Apply constraints
                min_spend = 500
                max_spend = total_budget * 0.6
                
                if recommended < min_spend:
                    recommended = min_spend
                elif recommended > max_spend:
                    recommended = max_spend
                
                cm['recommended_spend'] = round(recommended, 2)
        
        # Normalize to match total budget
        total_recommended = sum(c['recommended_spend'] for c in channel_metrics)
        if total_recommended > 0:
            adjustment_factor = total_budget / total_recommended
            for cm in channel_metrics:
                cm['recommended_spend'] = round(cm['recommended_spend'] * adjustment_factor, 2)
        
        # Calculate expected outcomes
        total_current_spend = sum(c['current_spend'] for c in channel_metrics)
        total_expected_revenue = 0
        
        optimized_allocation = []
        for cm in channel_metrics:
            recommended = cm['recommended_spend']
            
            # Estimate expected conversions based on efficiency gain
            efficiency_factor = recommended / (cm['current_spend'] + 1)
            efficiency_factor = min(efficiency_factor, 3.0)  # Cap at 3x
            
            expected_conversions = cm['conversions'] * efficiency_factor * cm['success_probability']
            expected_revenue = expected_conversions * 100
            total_expected_revenue += expected_revenue
            
            expected_roi = (expected_revenue - recommended) / (recommended + 1)
            
            # Determine priority
            if cm['efficiency_score'] > 0.5:
                priority = 'high'
            elif cm['efficiency_score'] > 0.2:
                priority = 'medium'
            else:
                priority = 'low'
            
            optimized_allocation.append({
                'channel': cm['name'],
                'duration': cm['duration'],
                'current_spend': round(cm['current_spend'], 2),
                'recommended_spend': recommended,
                'daily_spend': round(recommended / cm['duration'], 2),
                'current_roi': cm['current_roi'],
                'expected_roi': round(expected_roi, 3),
                'success_probability': cm['success_probability'],
                'decision': cm['decision'],
                'priority': priority,
                'efficiency_score': cm['efficiency_score']
            })
        
        total_expected_roi = (total_expected_revenue - total_budget) / (total_budget + 1)
        waste_reduction = max(0, total_current_spend - total_budget)
        
        return Response({
            'total_budget': round(total_budget, 2),
            'optimized_allocation': optimized_allocation,
            'summary': {
                'total_current_spend': round(total_current_spend, 2),
                'total_recommended_spend': round(total_budget, 2),
                'total_expected_revenue': round(total_expected_revenue, 2),
                'expected_total_roi': round(total_expected_roi, 3),
                'waste_reduction': round(waste_reduction, 2),
                'num_channels': len(channel_metrics)
            }
        })
        
    except Exception as e:
        logger.error(f"Optimize budget error: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'POST'])
def channel_performance(request):
    """
    Analyze channel performance and provide insights.
    
    Request body:
    {
        "channels": [
            {
                "name": "Google",
                "campaigns": [
                    {
                        "duration": 30,
                        "spend": 5000,
                        "conversions": 50
                    }
                ]
            }
        ]
    }
    
    Returns performance insights and recommendations.
    """
    try:
        data = request.data
        channels_data = data.get('channels', [])
        
        if not channels_data:
            return Response({
                'overall_metrics': {
                    'total_spend': 0,
                    'total_conversions': 0,
                    'average_daily_spend': 0,
                    'average_roi': 0
                },
                'channel_insights': [],
                'top_performers': [],
                'recommendations': ['Add channel data to analyze']
            })
        
        all_campaigns = []
        channel_insights = []
        
        for channel_data in channels_data:
            channel_name = channel_data.get('name', 'Unknown')
            campaigns = channel_data.get('campaigns', [])
            
            channel_spend = 0
            channel_duration = 0
            channel_conversions = 0
            channel_probs = []
            
            for campaign in campaigns:
                duration = campaign.get('duration', 30)
                spend = campaign.get('spend', 0)
                conversions = campaign.get('conversions', 0)
                
                channel_spend += spend
                channel_duration += duration
                channel_conversions += conversions
                
                # Predict
                daily_spend = spend / (duration + 1) if duration > 0 else 0
                predict_data = {
                    "Spend": spend,
                    "Campaign_Duration": duration,
                    "Daily_Spend": daily_spend,
                    f"Channel_{channel_name}": 1.0
                }
                prob, decision = predict_campaign(predict_data)
                channel_probs.append(prob)
                
                all_campaigns.append({
                    'channel': channel_name,
                    'duration': duration,
                    'spend': spend,
                    'conversions': conversions,
                    'probability': round(prob, 3),
                    'decision': decision
                })
            
            # Calculate metrics
            avg_daily_spend = channel_spend / (channel_duration + 1) if channel_duration > 0 else 0
            avg_conversion_value = 100
            revenue = channel_conversions * avg_conversion_value
            roi = (revenue - channel_spend) / (channel_spend + 1)
            avg_probability = np.mean(channel_probs) if channel_probs else 0
            
            channel_insights.append({
                'channel': channel_name,
                'total_spend': round(channel_spend, 2),
                'total_duration': channel_duration,
                'total_conversions': channel_conversions,
                'average_daily_spend': round(avg_daily_spend, 2),
                'average_duration': round(channel_duration / len(campaigns), 1) if campaigns else 0,
                'roi': round(roi, 3),
                'revenue': round(revenue, 2),
                'avg_success_probability': round(avg_probability, 3),
                'num_campaigns': len(campaigns)
            })
        
        # Overall metrics
        total_spend = sum(c['total_spend'] for c in channel_insights)
        total_conversions = sum(c['total_conversions'] for c in channel_insights)
        total_duration = sum(c['total_duration'] for c in channel_insights)
        
        avg_daily_spend = total_spend / (total_duration + 1) if total_duration > 0 else 0
        total_revenue = total_conversions * 100
        avg_roi = (total_revenue - total_spend) / (total_spend + 1)
        
        # Sort by ROI
        channel_insights.sort(key=lambda x: x['roi'], reverse=True)
        
        # Top performers (top 3)
        top_performers = channel_insights[:3]
        
        # Recommendations
        recommendations = []
        for ci in channel_insights:
            if ci['roi'] > 1.0:
                recommendations.append(
                    f"Increase budget for {ci['channel']} (ROI: {ci['roi']})"
                )
            elif ci['roi'] < 0:
                recommendations.append(
                    f"Reduce spending on {ci['channel']} (negative ROI)"
                )
            elif ci['avg_success_probability'] > 0.6:
                recommendations.append(
                    f"Scale {ci['channel']} - high success rate ({ci['avg_success_probability']})"
                )
        
        if not recommendations:
            recommendations.append("All channels performing within normal range")
        
        return Response({
            'overall_metrics': {
                'total_spend': round(total_spend, 2),
                'total_conversions': total_conversions,
                'total_duration': total_duration,
                'average_daily_spend': round(avg_daily_spend, 2),
                'average_roi': round(avg_roi, 3)
            },
            'channel_insights': channel_insights,
            'top_performers': top_performers,
            'recommendations': recommendations,
            'all_campaigns': all_campaigns
        })
        
    except Exception as e:
        logger.error(f"Channel performance error: {e}")
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
def optimize_budget(request):
    """
    Optimize budget allocation across multiple channels to maximize ROI.
    
    Accepts a list of channels with their current performance metrics
    and returns recommended budget allocation.
    
    Request body:
    {
        "total_budget": 10000,
        "channels": [
            {
                "name": "Google Ads",
                "impressions": 50000,
                "clicks": 2500,
                "spend": 5000,
                "conversions": 150
            },
            {
                "name": "Facebook",
                "impressions": 30000,
                "clicks": 1500,
                "spend": 3000,
                "conversions": 90
            }
        ]
    }
    
    Returns:
    {
        "total_budget": 10000,
        "optimized_allocation": [
            {
                "channel": "Google Ads",
                "current_spend": 5000,
                "recommended_spend": 6500,
                "current_roi": 1.5,
                "expected_roi": 1.65,
                "priority": "high"
            },
            ...
        ],
        "summary": {
            "total_current_spend": 8000,
            "total_recommended_spend": 10000,
            "expected_total_roi": 1.62,
            "waste_reduction": 1200
        }
    }
    """
    try:
        data = request.data
        total_budget = float(data.get('total_budget', 10000))
        channels = data.get('channels', [])
        
        if not channels:
            return Response(
                {"error": "No channels provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate performance metrics for each channel
        channel_metrics = []
        for channel in channels:
            name = channel.get('name', 'Unknown')
            impressions = channel.get('impressions', 0)
            clicks = channel.get('clicks', 0)
            spend = channel.get('spend', 0)
            conversions = channel.get('conversions', 0)
            
            # Calculate KPIs
            ctr = clicks / (impressions + 1)
            cpc = spend / (clicks + 1)
            conversion_rate = conversions / (clicks + 1)
            
            # Calculate current ROI
            avg_conversion_value = 100
            current_revenue = conversions * avg_conversion_value
            current_roi = (current_revenue - spend) / (spend + 1)
            
            # Predict success probability
            campaign_data = {
                "Impressions": impressions,
                "Clicks": clicks,
                "Spend": spend
            }
            prob, decision = predict_campaign(campaign_data)
            
            # Calculate efficiency score (higher = better)
            efficiency_score = prob * (current_revenue / (spend + 1))
            
            channel_metrics.append({
                'name': name,
                'current_spend': spend,
                'impressions': impressions,
                'clicks': clicks,
                'conversions': conversions,
                'ctr': ctr,
                'cpc': cpc,
                'conversion_rate': conversion_rate,
                'current_roi': round(current_roi, 3),
                'success_probability': round(prob, 3),
                'decision': decision,
                'efficiency_score': round(efficiency_score, 4)
            })
        
        # Sort channels by efficiency score (descending)
        channel_metrics.sort(key=lambda x: x['efficiency_score'], reverse=True)
        
        # Allocate budget based on efficiency
        # Top performers get more budget
        total_efficiency = sum(c['efficiency_score'] for c in channel_metrics)
        
        if total_efficiency == 0:
            # Equal allocation if no efficiency
            equal_share = total_budget / len(channel_metrics)
            for cm in channel_metrics:
                cm['recommended_spend'] = round(equal_share, 2)
        else:
            # Allocate proportionally to efficiency
            for cm in channel_metrics:
                allocation_ratio = cm['efficiency_score'] / total_efficiency
                recommended = total_budget * allocation_ratio
                
                # Apply minimum/maximum constraints
                min_spend = 500  # Minimum spend per channel
                max_spend = total_budget * 0.6  # Max 60% to one channel
                
                if recommended < min_spend:
                    recommended = min_spend
                elif recommended > max_spend:
                    recommended = max_spend
                
                cm['recommended_spend'] = round(recommended, 2)
        
        # Normalize to match total budget exactly
        total_recommended = sum(c['recommended_spend'] for c in channel_metrics)
        if total_recommended > 0:
            adjustment_factor = total_budget / total_recommended
            for cm in channel_metrics:
                cm['recommended_spend'] = round(cm['recommended_spend'] * adjustment_factor, 2)
        
        # Calculate expected ROI after reallocation
        total_current_spend = sum(c['current_spend'] for c in channel_metrics)
        total_expected_revenue = 0
        
        optimized_allocation = []
        for cm in channel_metrics:
            recommended = cm['recommended_spend']
            
            # Estimate expected conversions based on efficiency
            efficiency_factor = recommended / (cm['current_spend'] + 1)
            expected_conversions = cm['conversions'] * min(efficiency_factor, 2.0)  # Cap at 2x
            expected_revenue = expected_conversions * 100
            expected_roi = (expected_revenue - recommended) / (recommended + 1)
            
            total_expected_revenue += expected_revenue
            
            # Determine priority
            if cm['efficiency_score'] > 0.5:
                priority = 'high'
            elif cm['efficiency_score'] > 0.2:
                priority = 'medium'
            else:
                priority = 'low'
            
            optimized_allocation.append({
                'channel': cm['name'],
                'current_spend': round(cm['current_spend'], 2),
                'recommended_spend': recommended,
                'current_roi': cm['current_roi'],
                'expected_roi': round(expected_roi, 3),
                'success_probability': cm['success_probability'],
                'decision': cm['decision'],
                'priority': priority,
                'efficiency_score': cm['efficiency_score']
            })
        
        total_expected_roi = (total_expected_revenue - total_budget) / (total_budget + 1)
        waste_reduction = max(0, total_current_spend - total_budget)
        
        return Response({
            'total_budget': round(total_budget, 2),
            'optimized_allocation': optimized_allocation,
            'summary': {
                'total_current_spend': round(total_current_spend, 2),
                'total_recommended_spend': round(total_budget, 2),
                'total_expected_revenue': round(total_expected_revenue, 2),
                'expected_total_roi': round(total_expected_roi, 3),
                'waste_reduction': round(waste_reduction, 2),
                'num_channels': len(channel_metrics)
            }
        })
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'POST'])
def channel_performance(request):
    """
    Analyze channel performance and provide insights.
    
    Accepts data from multiple campaigns/channels and returns
    comparative performance metrics and recommendations.
    
    Request body:
    {
        "channels": [
            {
                "name": "Google Ads",
                "campaigns": [
                    {
                        "impressions": 50000,
                        "clicks": 2500,
                        "spend": 5000,
                        "conversions": 150
                    }
                ]
            }
        ]
    }
    
    Returns:
    {
        "overall_metrics": {...},
        "channel_insights": [...],
        "top_performers": [...],
        "recommendations": [...]
    }
    """
    try:
        data = request.data
        channels_data = data.get('channels', [])
        
        if not channels_data:
            # Return sample data for GET request
            return Response({
                'overall_metrics': {
                    'total_impressions': 0,
                    'total_clicks': 0,
                    'total_spend': 0,
                    'total_conversions': 0,
                    'average_ctr': 0,
                    'average_cpc': 0,
                    'average_conversion_rate': 0
                },
                'channel_insights': [],
                'top_performers': [],
                'recommendations': ['Add channel data to analyze']
            })
        
        all_campaigns = []
        channel_insights = []
        
        for channel_data in channels_data:
            channel_name = channel_data.get('name', 'Unknown')
            campaigns = channel_data.get('campaigns', [])
            
            channel_impressions = 0
            channel_clicks = 0
            channel_spend = 0
            channel_conversions = 0
            channel_probs = []
            
            for campaign in campaigns:
                impressions = campaign.get('impressions', 0)
                clicks = campaign.get('clicks', 0)
                spend = campaign.get('spend', 0)
                conversions = campaign.get('conversions', 0)
                
                channel_impressions += impressions
                channel_clicks += clicks
                channel_spend += spend
                channel_conversions += conversions
                
                # Get prediction
                campaign_data = {
                    "Impressions": impressions,
                    "Clicks": clicks,
                    "Spend": spend
                }
                prob, decision = predict_campaign(campaign_data)
                channel_probs.append(prob)
                
                all_campaigns.append({
                    'channel': channel_name,
                    'impressions': impressions,
                    'clicks': clicks,
                    'spend': spend,
                    'conversions': conversions,
                    'probability': round(prob, 3),
                    'decision': decision
                })
            
            # Calculate channel metrics
            ctr = channel_clicks / (channel_impressions + 1)
            cpc = channel_spend / (channel_clicks + 1)
            conversion_rate = channel_conversions / (channel_clicks + 1)
            avg_conversion_value = 100
            revenue = channel_conversions * avg_conversion_value
            roi = (revenue - channel_spend) / (channel_spend + 1)
            avg_probability = np.mean(channel_probs) if channel_probs else 0
            
            channel_insights.append({
                'channel': channel_name,
                'total_impressions': channel_impressions,
                'total_clicks': channel_clicks,
                'total_spend': round(channel_spend, 2),
                'total_conversions': channel_conversions,
                'ctr': round(ctr, 4),
                'cpc': round(cpc, 2),
                'conversion_rate': round(conversion_rate, 4),
                'roi': round(roi, 3),
                'revenue': round(revenue, 2),
                'avg_success_probability': round(avg_probability, 3),
                'num_campaigns': len(campaigns)
            })
        
        # Calculate overall metrics
        total_impressions = sum(c['total_impressions'] for c in channel_insights)
        total_clicks = sum(c['total_clicks'] for c in channel_insights)
        total_spend = sum(c['total_spend'] for c in channel_insights)
        total_conversions = sum(c['total_conversions'] for c in channel_insights)
        
        overall_ctr = total_clicks / (total_impressions + 1)
        overall_cpc = total_spend / (total_clicks + 1)
        overall_conversion_rate = total_conversions / (total_clicks + 1)
        
        # Sort channels by ROI
        channel_insights.sort(key=lambda x: x['roi'], reverse=True)
        
        # Identify top performers (top 3)
        top_performers = channel_insights[:3]
        
        # Generate recommendations
        recommendations = []
        for ci in channel_insights:
            if ci['roi'] > 1.0:
                recommendations.append(
                    f"Increase budget for {ci['channel']} (ROI: {ci['roi']})"
                )
            elif ci['roi'] < 0:
                recommendations.append(
                    f"Reduce or pause spending on {ci['channel']} (negative ROI: {ci['roi']})"
                )
            elif ci['conversion_rate'] > 0.1:
                recommendations.append(
                    f"Scale {ci['channel']} - high conversion rate ({ci['conversion_rate']})"
                )
        
        if not recommendations:
            recommendations.append("All channels performing within normal range")
        
        return Response({
            'overall_metrics': {
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'total_spend': round(total_spend, 2),
                'total_conversions': total_conversions,
                'average_ctr': round(overall_ctr, 4),
                'average_cpc': round(overall_cpc, 2),
                'average_conversion_rate': round(overall_conversion_rate, 4)
            },
            'channel_insights': channel_insights,
            'top_performers': top_performers,
            'recommendations': recommendations
        })
        
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )