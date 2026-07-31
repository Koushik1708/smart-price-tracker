from typing import List, Dict, Any
from backend.models import Product, PriceSnapshot

def calculate_statistics(snapshots: List[PriceSnapshot]) -> Dict[str, float]:
    if not snapshots:
        return {
            "current_price": 0.0,
            "lowest_price": 0.0,
            "highest_price": 0.0,
            "average_price": 0.0
        }
        
    prices = [s.price for s in snapshots if s.price is not None and s.price > 0]
    
    if not prices:
        return {
            "current_price": 0.0,
            "lowest_price": 0.0,
            "highest_price": 0.0,
            "average_price": 0.0
        }
        
    current = prices[-1]
    lowest = min(prices)
    highest = max(prices)
    average = sum(prices) / len(prices)
    
    return {
        "current_price": round(float(current), 2),
        "lowest_price": round(float(lowest), 2),
        "highest_price": round(float(highest), 2),
        "average_price": round(float(average), 2)
    }

def analyze_trend(snapshots: List[PriceSnapshot]) -> Dict[str, str]:
    if not snapshots or len(snapshots) < 2:
        return {
            "trend": "STABLE",
            "explanation": "Not enough data to determine a trend."
        }
        
    prices = [s.price for s in snapshots if s.price is not None and s.price > 0]
    if len(prices) < 2:
        return {
            "trend": "STABLE",
            "explanation": "Not enough valid price points."
        }
        
    current = prices[-1]
    oldest_recent = prices[0] # compare against oldest in snapshot list (which might be just last few days if filtered, but usually it's all history. Let's compare last to the one before it for a simple trend, or last vs average.)
    
    # Let's compare the current price to the average of the previous 5 snapshots or simply the previous snapshot
    recent_history = prices[:-1]
    recent_avg = sum(recent_history) / len(recent_history)
    
    if current < recent_avg * 0.95:
        return {
            "trend": "DOWN",
            "explanation": f"Price dropped recently compared to its average of ₹{round(float(recent_avg), 2)}."
        }
    elif current > recent_avg * 1.05:
        return {
            "trend": "UP",
            "explanation": f"Price increased recently compared to its average of ₹{round(float(recent_avg), 2)}."
        }
    else:
        return {
            "trend": "STABLE",
            "explanation": "Price has been relatively stable recently."
        }

def calculate_deal_score(product: Product, snapshots: List[PriceSnapshot], is_fake_discount: bool) -> Dict[str, Any]:
    stats = calculate_statistics(snapshots)
    trend_info = analyze_trend(snapshots)
    
    if not snapshots or stats["average_price"] == 0:
        return {
            "deal_score": 0,
            "deal_rating": "★☆☆☆☆",
            "deal_reason": "Insufficient data to calculate a deal score."
        }
        
    score = 50.0  # Base score
    
    current = stats["current_price"]
    avg = stats["average_price"]
    lowest = stats["lowest_price"]
    
    # 1. Current vs Average (Max +25, Min -25)
    # If current is 20% lower than avg, full +25
    if current < avg:
        diff_pct = (avg - current) / avg
        score += min(25, diff_pct * 125) # 20% drop = +25
    elif current > avg:
        diff_pct = (current - avg) / avg
        score -= min(25, diff_pct * 125)
        
    # 2. Current vs Lowest (Max +20, Min -10)
    if current <= lowest:
        score += 20
    else:
        # Penalize slightly if far from lowest
        diff_from_lowest = (current - lowest) / lowest
        score -= min(10, diff_from_lowest * 50)
        
    # 3. Fake discount penalty
    if is_fake_discount:
        score -= 30
        
    # 4. Recent trend
    if trend_info["trend"] == "DOWN":
        score += 5
    elif trend_info["trend"] == "UP":
        score -= 5
        
    # Clamp score
    final_score = max(0, min(100, int(score)))
    
    # Rating stars
    if final_score >= 90:
        stars = "★★★★★"
    elif final_score >= 70:
        stars = "★★★★☆"
    elif final_score >= 50:
        stars = "★★★☆☆"
    elif final_score >= 30:
        stars = "★★☆☆☆"
    else:
        stars = "★☆☆☆☆"
        
    # Reason
    if is_fake_discount:
        reason = "Score penalized due to suspected fake discount."
    elif current <= lowest and final_score >= 80:
        reason = "Excellent deal! At or near its lowest historical price."
    elif final_score >= 70:
        reason = "Good deal. Price is below its historical average."
    elif final_score < 40:
        reason = "Poor deal. Price is higher than usual."
    else:
        reason = "Fair deal. Price is around its historical average."
        
    return {
        "deal_score": final_score,
        "deal_rating": stars,
        "deal_reason": reason
    }
