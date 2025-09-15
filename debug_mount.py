#!/usr/bin/env python3
"""
Debug script to test Veeam Data Integration API mount request
"""
import requests
import json
import urllib3
from src.services.veeam_api import VeeamDataIntegrationAPI

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_mount():
    """Debug the mount request to see exact error details."""
    
    # Initialize Veeam API
    veeam_api = VeeamDataIntegrationAPI(
        base_url="https://172.21.234.6:9419",
        username="administrator", 
        password="Veeam123",
        verify_ssl=False
    )
    
    # Authenticate
    print("🔐 Authenticating...")
    if not veeam_api.authenticate():
        print("❌ Authentication failed")
        return
    print("✅ Authentication successful")
    
    # Test restore point ID
    restore_point_id = "533368a9-4bfc-4c98-bba2-aab6da26239e"
    
    # Prepare mount request
    url = f"{veeam_api.base_url}/api/v1/dataIntegration/publish"
    mount_data = {
        'restorePointId': restore_point_id,
        'type': 'ISCSITarget',
        'allowedIps': ['127.0.0.1', 'localhost']
    }
    
    headers = {
        'accept': 'application/json',
        'x-api-version': '1.2-rev0',
        'Authorization': f'Bearer {veeam_api.auth_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n📤 Mount Request:")
    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Data: {json.dumps(mount_data, indent=2)}")
    
    # Make the request
    print(f"\n🚀 Sending request...")
    try:
        response = veeam_api.session.post(url, json=mount_data, headers=headers)
        
        print(f"\n📥 Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {json.dumps(dict(response.headers), indent=2)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code != 200:
            print(f"\n❌ Request failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error JSON: {json.dumps(error_data, indent=2)}")
            except:
                print("Could not parse error response as JSON")
        else:
            print(f"\n✅ Request successful!")
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
            
    except Exception as e:
        print(f"\n💥 Exception occurred: {str(e)}")

if __name__ == "__main__":
    debug_mount()
