#!/usr/bin/env python3
"""
Test Data Integration API mount with valid restore point ID
"""
import requests
import json
import urllib3
from src.services.veeam_api import VeeamDataIntegrationAPI

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_data_integration_mount():
    """Test Data Integration API mount with valid restore point ID."""
    
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
    
    # Use valid restore point ID from our debug output
    restore_point_id = "645f7290-c812-4674-9ace-df7b9736ae71"
    
    # Test Data Integration API mount
    print(f"\n🧪 Testing Data Integration API mount with restore point: {restore_point_id}")
    
    url = f"{veeam_api.base_url}/api/v1/dataIntegration/publish"
    mount_data = {
        'restorePointId': restore_point_id,
        'type': 'ISCSITarget',
        'allowedIps': ['127.0.0.1']
    }
    
    headers = {
        'accept': 'application/json',
        'x-api-version': '1.2-rev0',
        'Authorization': f'Bearer {veeam_api.auth_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"📤 Mount Request:")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(mount_data, indent=2)}")
    
    try:
        response = veeam_api.session.post(url, json=mount_data, headers=headers)
        
        print(f"\n📥 Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code in [200, 201]:
            print(f"\n🎉 SUCCESS! Data Integration API mount worked!")
            result = response.json()
            print(f"Result: {json.dumps(result, indent=2)}")
        else:
            print(f"\n❌ Mount failed with status {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error JSON: {json.dumps(error_data, indent=2)}")
            except:
                print("Could not parse error response as JSON")
                
    except Exception as e:
        print(f"\n💥 Exception occurred: {str(e)}")

if __name__ == "__main__":
    test_data_integration_mount()
