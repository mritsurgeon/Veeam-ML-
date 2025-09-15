#!/usr/bin/env python3
"""
Compare direct mount vs Flask mount to find the difference
"""
import requests
import json
import urllib3
from src.services.veeam_api import VeeamDataIntegrationAPI

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def compare_mount_requests():
    """Compare direct mount vs Flask mount requests."""
    
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
    restore_point_id = "645f7290-c812-4674-9ace-df7b9736ae71"
    
    print(f"\n🧪 Testing direct mount_backup method...")
    try:
        result = veeam_api.mount_backup(restore_point_id, "/tmp/test_mount")
        print(f"✅ Direct mount_backup SUCCESS: {result}")
    except Exception as e:
        print(f"❌ Direct mount_backup FAILED: {str(e)}")
    
    print(f"\n🧪 Testing direct API call (same as our working test)...")
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
    
    try:
        response = veeam_api.session.post(url, json=mount_data, headers=headers)
        print(f"Direct API call status: {response.status_code}")
        print(f"Direct API call response: {response.text}")
        
        if response.status_code in [200, 201]:
            print(f"✅ Direct API call SUCCESS!")
        else:
            print(f"❌ Direct API call FAILED")
            
    except Exception as e:
        print(f"💥 Direct API call exception: {str(e)}")

if __name__ == "__main__":
    compare_mount_requests()
