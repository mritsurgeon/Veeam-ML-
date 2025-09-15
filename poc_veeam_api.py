#!/usr/bin/env python3
"""
Proof of Concept: Veeam ML Integration with Real API Server
This script demonstrates connecting to the actual Veeam Backup Server API.
"""

import requests
import json
import sys
import os
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class VeeamAPIPoC:
    """Proof of Concept class for Veeam API integration."""
    
    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # For testing only
        self.access_token = None
        
    def test_connection(self):
        """Test basic connectivity to the Veeam server."""
        print(f"🔍 Testing connection to: {self.base_url}")
        
        try:
            # Try to access the swagger endpoint
            swagger_url = f"{self.base_url}/swagger/v1.2-rev1/swagger.json"
            response = self.session.get(swagger_url, timeout=10)
            
            if response.status_code == 200:
                print("✅ Successfully connected to Veeam API server!")
                print(f"📋 Swagger documentation available at: {swagger_url}")
                
                # Parse swagger info
                swagger_data = response.json()
                if 'info' in swagger_data:
                    info = swagger_data['info']
                    print(f"📖 API Title: {info.get('title', 'Unknown')}")
                    print(f"📝 API Version: {info.get('version', 'Unknown')}")
                    print(f"📄 Description: {info.get('description', 'No description')}")
                
                return True
            else:
                print(f"❌ Connection failed. Status code: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error: {str(e)}")
            return False
    
    def get_api_endpoints(self):
        """Get available API endpoints from swagger."""
        print("\n🔍 Discovering API endpoints...")
        
        try:
            swagger_url = f"{self.base_url}/swagger/v1.2-rev1/swagger.json"
            response = self.session.get(swagger_url)
            
            if response.status_code == 200:
                swagger_data = response.json()
                paths = swagger_data.get('paths', {})
                
                print(f"📊 Found {len(paths)} API endpoints:")
                
                # Categorize endpoints
                backup_endpoints = []
                job_endpoints = []
                repository_endpoints = []
                other_endpoints = []
                
                for path, methods in paths.items():
                    for method, details in methods.items():
                        if method.upper() in ['GET', 'POST', 'PUT', 'DELETE']:
                            endpoint_info = {
                                'path': path,
                                'method': method.upper(),
                                'summary': details.get('summary', 'No description'),
                                'tags': details.get('tags', [])
                            }
                            
                            if 'backup' in path.lower() or 'backup' in str(details.get('tags', [])).lower():
                                backup_endpoints.append(endpoint_info)
                            elif 'job' in path.lower() or 'job' in str(details.get('tags', [])).lower():
                                job_endpoints.append(endpoint_info)
                            elif 'repository' in path.lower() or 'repository' in str(details.get('tags', [])).lower():
                                repository_endpoints.append(endpoint_info)
                            else:
                                other_endpoints.append(endpoint_info)
                
                # Display categorized endpoints
                if backup_endpoints:
                    print("\n💾 Backup-related endpoints:")
                    for ep in backup_endpoints[:5]:  # Show first 5
                        print(f"  {ep['method']} {ep['path']} - {ep['summary']}")
                
                if job_endpoints:
                    print("\n⚙️ Job-related endpoints:")
                    for ep in job_endpoints[:5]:  # Show first 5
                        print(f"  {ep['method']} {ep['path']} - {ep['summary']}")
                
                if repository_endpoints:
                    print("\n🗄️ Repository-related endpoints:")
                    for ep in repository_endpoints[:5]:  # Show first 5
                        print(f"  {ep['method']} {ep['path']} - {ep['summary']}")
                
                return paths
            else:
                print(f"❌ Failed to get API endpoints. Status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting API endpoints: {str(e)}")
            return None
    
    def test_authentication_endpoints(self):
        """Test authentication-related endpoints."""
        print("\n🔐 Testing authentication endpoints...")
        
        try:
            swagger_url = f"{self.base_url}/swagger/v1.2-rev1/swagger.json"
            response = self.session.get(swagger_url)
            
            if response.status_code == 200:
                swagger_data = response.json()
                paths = swagger_data.get('paths', {})
                
                auth_endpoints = []
                for path, methods in paths.items():
                    for method, details in methods.items():
                        if method.upper() in ['POST']:
                            summary = details.get('summary', '').lower()
                            tags = str(details.get('tags', [])).lower()
                            
                            if ('token' in summary or 'auth' in summary or 
                                'login' in summary or 'token' in path.lower() or 
                                'auth' in path.lower() or 'login' in path.lower()):
                                auth_endpoints.append({
                                    'path': path,
                                    'method': method.upper(),
                                    'summary': details.get('summary', 'No description')
                                })
                
                if auth_endpoints:
                    print("🔑 Found authentication endpoints:")
                    for ep in auth_endpoints:
                        print(f"  {ep['method']} {ep['path']} - {ep['summary']}")
                else:
                    print("⚠️ No obvious authentication endpoints found in swagger")
                
                return auth_endpoints
            else:
                print(f"❌ Failed to get authentication info. Status: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error testing authentication: {str(e)}")
            return []
    
    def test_basic_endpoints(self):
        """Test basic API endpoints without authentication."""
        print("\n🧪 Testing basic API endpoints...")
        
        # Common Veeam API endpoints to test
        test_endpoints = [
            '/api/v1/version',
            '/api/v1/about',
            '/api/v1/status',
            '/api/v1/health',
            '/api/v1/info'
        ]
        
        working_endpoints = []
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = self.session.get(url, timeout=5)
                
                if response.status_code == 200:
                    print(f"✅ {endpoint} - Status: {response.status_code}")
                    working_endpoints.append(endpoint)
                elif response.status_code == 401:
                    print(f"🔐 {endpoint} - Requires authentication (401)")
                elif response.status_code == 404:
                    print(f"❓ {endpoint} - Not found (404)")
                else:
                    print(f"⚠️ {endpoint} - Status: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {endpoint} - Error: {str(e)}")
        
        return working_endpoints
    
    def generate_integration_report(self):
        """Generate a comprehensive integration report."""
        print("\n" + "="*60)
        print("📋 VEEAM ML INTEGRATION - PROOF OF CONCEPT REPORT")
        print("="*60)
        print(f"🕐 Timestamp: {datetime.now().isoformat()}")
        print(f"🌐 Target Server: {self.base_url}")
        
        # Test connection
        connection_ok = self.test_connection()
        
        if connection_ok:
            # Get API endpoints
            endpoints = self.get_api_endpoints()
            
            # Test authentication
            auth_endpoints = self.test_authentication_endpoints()
            
            # Test basic endpoints
            working_endpoints = self.test_basic_endpoints()
            
            print("\n" + "="*60)
            print("📊 INTEGRATION SUMMARY")
            print("="*60)
            print(f"✅ Connection Status: {'SUCCESS' if connection_ok else 'FAILED'}")
            print(f"📡 API Endpoints Found: {len(endpoints) if endpoints else 0}")
            print(f"🔐 Auth Endpoints Found: {len(auth_endpoints)}")
            print(f"🧪 Working Endpoints: {len(working_endpoints)}")
            
            print("\n📝 NEXT STEPS:")
            print("1. Set up authentication credentials")
            print("2. Test authenticated endpoints")
            print("3. Implement backup discovery")
            print("4. Test data mounting capabilities")
            print("5. Integrate with ML processing pipeline")
            
            return True
        else:
            print("\n❌ CONNECTION FAILED")
            print("Please check:")
            print("- Server URL is correct")
            print("- Server is accessible")
            print("- Firewall settings")
            print("- SSL/TLS configuration")
            return False


def main():
    """Main function to run the proof of concept."""
    print("🚀 Veeam ML Integration - Proof of Concept")
    print("="*50)
    
    # Veeam server details
    veeam_server = "https://172.21.234.6:9419"
    
    # Create PoC instance
    poc = VeeamAPIPoC(veeam_server)
    
    # Run comprehensive test
    success = poc.generate_integration_report()
    
    if success:
        print("\n🎉 Proof of Concept completed successfully!")
        print("The Veeam API server is accessible and ready for integration.")
    else:
        print("\n💥 Proof of Concept failed!")
        print("Please resolve connection issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
