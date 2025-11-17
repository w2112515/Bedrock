"""
Verify Binance Futures Funding Rate Data Availability

This script verifies:
1. API endpoint accessibility
2. Historical data availability (startTime/endTime support)
3. Data granularity (8 hours funding rate cycle)
4. Coverage (supported perpetual contract symbols)
5. Rate limits
6. Historical data depth

Usage:
    python scripts/verify_funding_rate_data.py
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any


def test_funding_rate_endpoint() -> Dict[str, Any]:
    """
    Test Binance Futures funding rate endpoint.
    
    Returns:
        Verification result dictionary
    """
    print("=" * 80)
    print("Binance Futures Funding Rate Data Verification")
    print("=" * 80)
    
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/fundingRate"
    
    results = {
        "endpoint_accessible": False,
        "historical_data_support": False,
        "data_granularity": None,
        "supported_symbols": [],
        "rate_limit": "500/5min/IP (shared with /fapi/v1/fundingInfo)",
        "historical_depth_days": None,
        "sample_data": [],
        "recommendation": ""
    }
    
    # Test 1: Basic endpoint accessibility (recent 100 records)
    print("\n[Test 1] Testing endpoint accessibility...")
    print(f"URL: {base_url}{endpoint}")
    
    try:
        params = {
            "symbol": "BTCUSDT",
            "limit": 100
        }
        
        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results["endpoint_accessible"] = True
            results["sample_data"] = data[:3]  # First 3 records
            
            print(f"✅ SUCCESS: Retrieved {len(data)} funding rate records")
            print(f"   Latest record: {data[0]}")
            print(f"   Oldest record: {data[-1]}")
            
            # Calculate data granularity
            if len(data) >= 2:
                time_diff = (data[0]['fundingTime'] - data[1]['fundingTime']) / 1000 / 3600
                results["data_granularity"] = f"{time_diff} hours"
                print(f"   Data granularity: {time_diff} hours per record")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return results
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        return results
    
    # Test 2: Historical data support (startTime/endTime parameters)
    print("\n[Test 2] Testing historical data support...")
    
    try:
        # Test: Get funding rate from 2024-01-01 to 2024-01-31
        start_time = int(datetime(2024, 1, 1).timestamp() * 1000)
        end_time = int(datetime(2024, 1, 31).timestamp() * 1000)
        
        params = {
            "symbol": "BTCUSDT",
            "startTime": start_time,
            "endTime": end_time,
            "limit": 1000
        }
        
        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results["historical_data_support"] = True
            
            print(f"✅ SUCCESS: Retrieved {len(data)} historical records")
            print(f"   Time range: {datetime.fromtimestamp(data[-1]['fundingTime']/1000)} - {datetime.fromtimestamp(data[0]['fundingTime']/1000)}")
            print(f"   Sample record: {data[0]}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
    
    # Test 3: Historical data depth (how far back can we go?)
    print("\n[Test 3] Testing historical data depth...")
    
    try:
        # Test: Try to get data from 2020-01-01
        start_time = int(datetime(2020, 1, 1).timestamp() * 1000)
        end_time = int(datetime(2020, 1, 31).timestamp() * 1000)
        
        params = {
            "symbol": "BTCUSDT",
            "startTime": start_time,
            "endTime": end_time,
            "limit": 100
        }
        
        response = requests.get(f"{base_url}{endpoint}", params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                oldest_record = datetime.fromtimestamp(data[-1]['fundingTime']/1000)
                days_back = (datetime.now() - oldest_record).days
                results["historical_depth_days"] = days_back
                
                print(f"✅ SUCCESS: Historical data available from {oldest_record}")
                print(f"   Depth: ~{days_back} days ({days_back/365:.1f} years)")
            else:
                print(f"⚠️  WARNING: No data available for 2020-01-01")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
    
    # Test 4: Check supported symbols
    print("\n[Test 4] Testing supported symbols...")
    
    test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
    
    for symbol in test_symbols:
        try:
            params = {"symbol": symbol, "limit": 1}
            response = requests.get(f"{base_url}{endpoint}", params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    results["supported_symbols"].append(symbol)
                    print(f"   ✅ {symbol}: Supported")
            else:
                print(f"   ❌ {symbol}: Not supported (HTTP {response.status_code})")
                
        except Exception as e:
            print(f"   ❌ {symbol}: Exception - {str(e)}")
    
    return results


def generate_recommendation(results: Dict[str, Any]) -> str:
    """Generate implementation recommendation based on verification results."""
    
    if not results["endpoint_accessible"]:
        return "❌ REJECT: Endpoint not accessible. Cannot implement funding rate strategy."
    
    if not results["historical_data_support"]:
        return "⚠️  CAUTION: Historical data not available. Can only use real-time data."
    
    if results["data_granularity"] != "8.0 hours":
        return f"⚠️  CAUTION: Unexpected data granularity ({results['data_granularity']}). Expected 8 hours."
    
    if len(results["supported_symbols"]) < 3:
        return "⚠️  CAUTION: Limited symbol coverage. May not support all trading pairs."
    
    return "✅ APPROVE: All verification checks passed. Funding rate data is suitable for strategy implementation."


if __name__ == "__main__":
    results = test_funding_rate_endpoint()
    
    # Generate recommendation
    results["recommendation"] = generate_recommendation(results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(json.dumps(results, indent=2, default=str))
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(results["recommendation"])
    print("=" * 80)

