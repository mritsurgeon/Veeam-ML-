#!/usr/bin/env python3
"""
Debug script to get actual restore points from backup objects
"""
import requests
import json
import urllib3
from src.services.veeam_api import VeeamDataIntegrationAPI

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_actual_restore_points():
    """Get actual restore points from backup objects."""
    
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
    
    headers = {
        'accept': 'application/json',
        'x-api-version': '1.2-rev0',
        'Authorization': f'Bearer {veeam_api.auth_token}'
    }
    
    # Get backup objects
    print(f"\n📋 Getting backup objects...")
    backup_objects_url = f"{veeam_api.base_url}/api/v1/backupObjects"
    response = veeam_api.session.get(backup_objects_url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get backup objects: {response.text}")
        return
        
    backup_objects = response.json()['data']
    print(f"✅ Found {len(backup_objects)} backup objects")
    
    # Get restore points for each backup object
    for obj in backup_objects:
        obj_id = obj['id']
        obj_name = obj['name']
        print(f"\n🔍 Getting restore points for: {obj_name} ({obj_id})")
        
        restore_points_url = f"{veeam_api.base_url}/api/v1/backupObjects/{obj_id}/restorePoints"
        response = veeam_api.session.get(restore_points_url, headers=headers)
        
        if response.status_code == 200:
            restore_points_response = response.json()
            restore_points = restore_points_response.get('data', [])
            print(f"✅ Found {len(restore_points)} restore points")
            
            # Try to mount the first restore point
            if restore_points and len(restore_points) > 0:
                first_rp = restore_points[0]
                rp_id = first_rp['id']
                allowed_ops = first_rp.get('allowedOperations', [])
                print(f"\n🧪 Testing mount with restore point: {rp_id}")
                print(f"Allowed operations: {allowed_ops}")
                
                # Check if Data Integration is supported
                if 'PublishBackupContent' in allowed_ops:
                    print("✅ Data Integration API supported")
                    # Try Data Integration mount
                    mount_url = f"{veeam_api.base_url}/api/v1/dataIntegration/publish"
                    mount_data = {
                        'restorePointId': rp_id,
                        'type': 'ISCSITarget',
                        'allowedIps': ['127.0.0.1']
                    }
                elif 'StartFlrRestore' in allowed_ops:
                    print("⚠️ Only FLR supported, trying FLR mount")
                    # Try FLR mount
                    mount_url = f"{veeam_api.base_url}/api/v1/restore/flr"
                    mount_data = {
                        'restorePointId': rp_id,
                        'type': 'Windows',
                        'autoUnmount': {
                            'isEnabled': True,
                            'noActivityPeriodInMinutes': 30
                        },
                        'reason': 'ML Data Analysis'
                    }
                else:
                    print(f"❌ No supported mount operations: {allowed_ops}")
                    continue
                
                mount_response = veeam_api.session.post(mount_url, json=mount_data, headers=headers)
                print(f"Mount status: {mount_response.status_code}")
                print(f"Mount response: {mount_response.text}")
                
                if mount_response.status_code in [200, 201]:
                    print(f"🎉 SUCCESS! Mount worked with restore point: {rp_id}")
                    return rp_id
        else:
            print(f"❌ Failed to get restore points: {response.text}")

if __name__ == "__main__":
    get_actual_restore_points()
