#!/usr/bin/env python3
"""
Test script to demonstrate accessing mounted Veeam backups.
This script shows how to work with both iSCSI mounts and FLR sessions.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.veeam_api import VeeamDataIntegrationAPI, VeeamAPIError
import json

def test_iscsi_mount_access():
    """Test accessing existing iSCSI mounts."""
    print("=== Testing iSCSI Mount Access ===")
    
    # Initialize API
    veeam_api = VeeamDataIntegrationAPI(
        base_url="https://172.21.234.6:9419",
        username="administrator",
        password="Veeam123",
        verify_ssl=False
    )
    
    try:
        # Authenticate
        if not veeam_api.authenticate():
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful")
        
        # Get all mounted sessions
        mounted_sessions = veeam_api.get_mount_sessions()
        print(f"📊 Found {len(mounted_sessions)} mounted sessions")
        
        # Test with first mounted session
        if mounted_sessions:
            first_session = mounted_sessions[0]
            session_id = first_session['id']
            print(f"\n🔍 Testing session: {session_id}")
            print(f"   Backup: {first_session.get('backupName', 'Unknown')}")
            print(f"   State: {first_session.get('mountState', 'Unknown')}")
            
            # Get detailed iSCSI information
            try:
                iscsi_info = veeam_api.get_iscsi_mount_info(session_id)
                print(f"\n📋 iSCSI Mount Information:")
                print(f"   Session ID: {iscsi_info['session_id']}")
                print(f"   Mount State: {iscsi_info['mount_state']}")
                print(f"   Backup Name: {iscsi_info['backup_name']}")
                print(f"   Restore Point: {iscsi_info['restore_point_name']}")
                
                print(f"\n🎯 iSCSI Targets:")
                for i, target in enumerate(iscsi_info['iscsi_targets']):
                    print(f"   Target {i+1}:")
                    print(f"     IQN: {target['iqn']}")
                    print(f"     Server IP: {target['server_ips'][0] if target['server_ips'] else 'N/A'}")
                    print(f"     Port: {target['server_port']}")
                
                print(f"\n🛠️  Access Methods:")
                for i, method in enumerate(iscsi_info['access_methods']):
                    print(f"   Method {i+1}: {method['method']}")
                    print(f"     Description: {method['description']}")
                    if 'command' in method:
                        print(f"     Command: {method['command']}")
                    if 'unc_path' in method:
                        print(f"     UNC Path: {method['unc_path']}")
                    if 'server_path' in method:
                        print(f"     Server Path: {method['server_path']}")
                    print()
                
            except VeeamAPIError as e:
                print(f"❌ Failed to get iSCSI info: {str(e)}")
        
    except VeeamAPIError as e:
        print(f"❌ Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def test_flr_session_creation():
    """Test creating FLR sessions."""
    print("\n=== Testing FLR Session Creation ===")
    
    # Initialize API
    veeam_api = VeeamDataIntegrationAPI(
        base_url="https://172.21.234.6:9419",
        username="administrator",
        password="Veeam123",
        verify_ssl=False
    )
    
    try:
        # Authenticate
        if not veeam_api.authenticate():
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful")
        
        # Try to create FLR session for a known restore point
        restore_point_id = "8e254edc-9ffa-47ee-945d-9c0fad52e8c4"  # From our mounted sessions
        
        try:
            print(f"🔄 Creating FLR session for restore point: {restore_point_id}")
            flr_session = veeam_api.create_flr_session_for_restore_point(restore_point_id)
            
            print("✅ FLR session created successfully!")
            print(f"   Session ID: {flr_session.get('id')}")
            print(f"   State: {flr_session.get('state')}")
            print(f"   Name: {flr_session.get('name')}")
            
            # Get FLR mount points
            session_id = flr_session.get('id')
            if session_id:
                try:
                    mount_points = veeam_api.get_flr_mount_points(session_id)
                    print(f"📁 FLR Mount Points:")
                    for point in mount_points:
                        print(f"   {point}")
                except VeeamAPIError as e:
                    print(f"⚠️  Could not get mount points: {str(e)}")
            
        except VeeamAPIError as e:
            print(f"❌ Failed to create FLR session: {str(e)}")
    
    except VeeamAPIError as e:
        print(f"❌ Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

def main():
    """Main test function."""
    print("🚀 Veeam Mount Access Test")
    print("=" * 50)
    
    # Test iSCSI mount access
    test_iscsi_mount_access()
    
    # Test FLR session creation
    test_flr_session_creation()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    main()
