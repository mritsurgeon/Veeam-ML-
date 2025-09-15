#!/usr/bin/env python3
"""
Debug script to check restore point validity
"""
import requests
import json
import urllib3
from src.services.veeam_api import VeeamDataIntegrationAPI

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_restore_point():
    """Debug the restore point to see if it's valid."""
    
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
    
    # Try to get restore point details
    print(f"\n🔍 Checking restore point: {restore_point_id}")
    
    # Try different endpoints to validate the restore point
    endpoints_to_try = [
        f"/api/v1/restorePoints/{restore_point_id}",
        f"/api/v1/backupObjects",
        f"/api/v1/dataIntegration"
    ]
    
    headers = {
        'accept': 'application/json',
        'x-api-version': '1.2-rev0',
        'Authorization': f'Bearer {veeam_api.auth_token}'
    }
    
    for endpoint in endpoints_to_try:
        url = f"{veeam_api.base_url}{endpoint}"
        print(f"\n📤 Testing endpoint: {endpoint}")
        
        try:
            response = veeam_api.session.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"💥 Exception: {str(e)}")

if __name__ == "__main__":
    debug_restore_point()
