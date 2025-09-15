#!/usr/bin/env python3
"""
Advanced Proof of Concept: Veeam ML Integration with Authentication
This script demonstrates authenticated access to the Veeam Backup Server API.
"""

import requests
import json
import sys
import os
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for testing
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class VeeamAuthenticatedPoC:
    """Advanced PoC with authentication capabilities."""
    
    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # For testing only
        self.access_token = None
        self.refresh_token = None
        
    def authenticate(self):
        """Authenticate with the Veeam API server."""
        print("🔐 Attempting authentication...")
        
        if not self.username or not self.password:
            print("⚠️ No credentials provided. Testing unauthenticated endpoints only.")
            return False
        
        try:
            # OAuth2 token endpoint
            token_url = f"{self.base_url}/api/oauth2/token"
            
            # Prepare authentication data
            auth_data = {
                'grant_type': 'password',
                'username': self.username,
                'password': self.password,
                'scope': 'api'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            print(f"📡 Sending authentication request to: {token_url}")
            response = self.session.post(token_url, data=auth_data, headers=headers, timeout=10)
            
            print(f"📊 Authentication response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                
                if self.access_token:
                    print("✅ Authentication successful!")
                    print(f"🎫 Access token obtained: {self.access_token[:20]}...")
                    
                    # Set authorization header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    
                    return True
                else:
                    print("❌ No access token in response")
                    return False
            else:
                print(f"❌ Authentication failed. Status: {response.status_code}")
                print(f"📄 Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication error: {str(e)}")
            return False
    
    def test_authenticated_endpoints(self):
        """Test endpoints that require authentication."""
        print("\n🧪 Testing authenticated endpoints...")
        
        if not self.access_token:
            print("⚠️ No access token available. Skipping authenticated tests.")
            return []
        
        # Key endpoints to test
        test_endpoints = [
            ('/api/v1/jobs', 'GET', 'Get all backup jobs'),
            ('/api/v1/backupInfrastructure/managedServers', 'GET', 'Get managed servers'),
            ('/api/v1/repositories', 'GET', 'Get backup repositories'),
            ('/api/v1/backups', 'GET', 'Get backup files'),
            ('/api/v1/sessions', 'GET', 'Get active sessions'),
            ('/api/v1/statistics', 'GET', 'Get system statistics')
        ]
        
        working_endpoints = []
        
        for endpoint, method, description in test_endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=10)
                elif method.upper() == 'POST':
                    response = self.session.post(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ {endpoint} - {description}")
                    
                    # Try to parse response
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   📊 Found {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"   📊 Response contains {len(data)} fields")
                    except:
                        print(f"   📄 Response length: {len(response.text)} characters")
                    
                    working_endpoints.append(endpoint)
                    
                elif response.status_code == 401:
                    print(f"🔐 {endpoint} - Authentication required")
                elif response.status_code == 403:
                    print(f"🚫 {endpoint} - Access forbidden")
                elif response.status_code == 404:
                    print(f"❓ {endpoint} - Not found")
                else:
                    print(f"⚠️ {endpoint} - Status: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {endpoint} - Error: {str(e)}")
        
        return working_endpoints
    
    def discover_backup_data(self):
        """Discover available backup data for ML processing."""
        print("\n🔍 Discovering backup data for ML processing...")
        
        if not self.access_token:
            print("⚠️ Authentication required for backup discovery.")
            return None
        
        backup_data = {
            'jobs': [],
            'repositories': [],
            'backups': [],
            'servers': []
        }
        
        try:
            # Get backup jobs
            jobs_url = f"{self.base_url}/api/v1/jobs"
            response = self.session.get(jobs_url, timeout=10)
            
            if response.status_code == 200:
                jobs_data = response.json()
                backup_data['jobs'] = jobs_data
                print(f"📋 Found {len(jobs_data)} backup jobs")
                
                # Show job details
                for job in jobs_data[:3]:  # Show first 3 jobs
                    job_name = job.get('name', 'Unknown')
                    job_type = job.get('type', 'Unknown')
                    print(f"   🔧 Job: {job_name} (Type: {job_type})")
            
            # Get repositories
            repos_url = f"{self.base_url}/api/v1/repositories"
            response = self.session.get(repos_url, timeout=10)
            
            if response.status_code == 200:
                repos_data = response.json()
                backup_data['repositories'] = repos_data
                print(f"🗄️ Found {len(repos_data)} repositories")
                
                # Show repository details
                for repo in repos_data[:3]:  # Show first 3 repos
                    repo_name = repo.get('name', 'Unknown')
                    repo_type = repo.get('type', 'Unknown')
                    print(f"   📦 Repository: {repo_name} (Type: {repo_type})")
            
            # Get managed servers
            servers_url = f"{self.base_url}/api/v1/backupInfrastructure/managedServers"
            response = self.session.get(servers_url, timeout=10)
            
            if response.status_code == 200:
                servers_data = response.json()
                backup_data['servers'] = servers_data
                print(f"🖥️ Found {len(servers_data)} managed servers")
                
                # Show server details
                for server in servers_data[:3]:  # Show first 3 servers
                    server_name = server.get('name', 'Unknown')
                    server_type = server.get('type', 'Unknown')
                    print(f"   🖥️ Server: {server_name} (Type: {server_type})")
            
            return backup_data
            
        except Exception as e:
            print(f"❌ Error discovering backup data: {str(e)}")
            return None
    
    def test_data_mounting_capabilities(self):
        """Test if we can mount backup data for ML processing."""
        print("\n💾 Testing data mounting capabilities...")
        
        if not self.access_token:
            print("⚠️ Authentication required for mounting tests.")
            return False
        
        try:
            # Look for mounting-related endpoints
            mount_endpoints = [
                '/api/v1/backups/mount',
                '/api/v1/repositories/mount',
                '/api/v1/dataIntegration/mount',
                '/api/v1/backups/{id}/mount'
            ]
            
            mount_capabilities = []
            
            for endpoint in mount_endpoints:
                try:
                    # Test if endpoint exists (should return 404 if not, 405 if method not allowed, etc.)
                    url = f"{self.base_url}{endpoint}"
                    response = self.session.get(url, timeout=5)
                    
                    if response.status_code == 404:
                        print(f"❓ {endpoint} - Not found")
                    elif response.status_code == 405:
                        print(f"🔧 {endpoint} - Method not allowed (endpoint exists)")
                        mount_capabilities.append(endpoint)
                    elif response.status_code == 200:
                        print(f"✅ {endpoint} - Available")
                        mount_capabilities.append(endpoint)
                    else:
                        print(f"⚠️ {endpoint} - Status: {response.status_code}")
                        
                except requests.exceptions.RequestException:
                    print(f"❌ {endpoint} - Connection error")
            
            if mount_capabilities:
                print(f"🎉 Found {len(mount_capabilities)} potential mounting endpoints!")
                return True
            else:
                print("⚠️ No obvious mounting endpoints found")
                return False
                
        except Exception as e:
            print(f"❌ Error testing mounting capabilities: {str(e)}")
            return False
    
    def generate_ml_integration_plan(self, backup_data):
        """Generate a plan for ML integration based on discovered data."""
        print("\n" + "="*60)
        print("🤖 ML INTEGRATION PLAN")
        print("="*60)
        
        if not backup_data:
            print("⚠️ No backup data available for ML integration planning.")
            return
        
        print("📊 Available Data Sources:")
        
        # Analyze jobs for ML opportunities
        jobs = backup_data.get('jobs', [])
        if jobs:
            print(f"\n🔧 Backup Jobs ({len(jobs)} found):")
            for job in jobs[:5]:  # Show first 5
                job_name = job.get('name', 'Unknown')
                job_type = job.get('type', 'Unknown')
                print(f"   • {job_name} - Potential for {job_type} analysis")
        
        # Analyze repositories
        repos = backup_data.get('repositories', [])
        if repos:
            print(f"\n🗄️ Repositories ({len(repos)} found):")
            for repo in repos[:5]:  # Show first 5
                repo_name = repo.get('name', 'Unknown')
                repo_type = repo.get('type', 'Unknown')
                print(f"   • {repo_name} - {repo_type} storage")
        
        # Analyze servers
        servers = backup_data.get('servers', [])
        if servers:
            print(f"\n🖥️ Managed Servers ({len(servers)} found):")
            for server in servers[:5]:  # Show first 5
                server_name = server.get('name', 'Unknown')
                server_type = server.get('type', 'Unknown')
                print(f"   • {server_name} - {server_type} server")
        
        print("\n🎯 Recommended ML Use Cases:")
        print("1. 📈 Backup Performance Analysis - Analyze job success rates and timing")
        print("2. 🔍 Anomaly Detection - Identify unusual backup patterns")
        print("3. 📊 Capacity Planning - Predict storage growth trends")
        print("4. 🛡️ Security Analysis - Detect suspicious backup activities")
        print("5. ⚡ Optimization - Recommend backup schedule improvements")
        
        print("\n🛠️ Implementation Steps:")
        print("1. Set up data extraction pipeline")
        print("2. Implement backup mounting functionality")
        print("3. Create ML feature extraction")
        print("4. Deploy classification models")
        print("5. Build real-time monitoring dashboard")


def main():
    """Main function for authenticated PoC."""
    print("🚀 Veeam ML Integration - Advanced Proof of Concept")
    print("="*60)
    
    # Veeam server details
    veeam_server = "https://172.21.234.6:9419"
    
    # For this PoC, we'll test without credentials first
    # In production, you would provide actual credentials
    username = None  # os.getenv('VEEAM_USERNAME')
    password = None  # os.getenv('VEEAM_PASSWORD')
    
    print(f"🌐 Target Server: {veeam_server}")
    print(f"👤 Username: {'Provided' if username else 'Not provided (testing unauthenticated)'}")
    
    # Create PoC instance
    poc = VeeamAuthenticatedPoC(veeam_server, username, password)
    
    # Test authentication
    auth_success = poc.authenticate()
    
    # Test authenticated endpoints
    working_endpoints = poc.test_authenticated_endpoints()
    
    # Discover backup data
    backup_data = poc.discover_backup_data()
    
    # Test mounting capabilities
    mount_available = poc.test_data_mounting_capabilities()
    
    # Generate ML integration plan
    poc.generate_ml_integration_plan(backup_data)
    
    print("\n" + "="*60)
    print("📋 ADVANCED POC SUMMARY")
    print("="*60)
    print(f"🔐 Authentication: {'SUCCESS' if auth_success else 'SKIPPED'}")
    print(f"🧪 Working Endpoints: {len(working_endpoints)}")
    print(f"💾 Backup Data Available: {'YES' if backup_data else 'NO'}")
    print(f"🔧 Mounting Capabilities: {'AVAILABLE' if mount_available else 'UNKNOWN'}")
    
    if auth_success and working_endpoints:
        print("\n🎉 Advanced PoC completed successfully!")
        print("The Veeam API is ready for full ML integration!")
    else:
        print("\n⚠️ PoC completed with limited functionality.")
        print("Consider providing authentication credentials for full testing.")


if __name__ == "__main__":
    main()
