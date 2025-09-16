import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { useVeeamAPI } from '@/hooks/useVeeamAPI'
import { useToast } from '@/hooks/use-toast'
import { 
  Settings, 
  Server, 
  Shield, 
  CheckCircle, 
  AlertCircle,
  Activity,
  Database,
  Brain,
  BarChart3,
  HardDrive
} from 'lucide-react'

export const ConfigurationPanel = () => {
  const [config, setConfig] = useState({
    base_url: '',
    username: '',
    password: '',
    verify_ssl: true,
    mount_server_name: '',
    mount_server_username: '',
    mount_server_password: '',
    mount_host_id: '',
    reuse_api_credentials: true
  })
  const [isConnecting, setIsConnecting] = useState(false)
  const [healthStatus, setHealthStatus] = useState(null)
  const [isLoadingHealth, setIsLoadingHealth] = useState(false)

  const { configureVeeam, checkHealth, isConfigured, error } = useVeeamAPI()
  const { toast } = useToast()

  useEffect(() => {
    if (isConfigured) {
      loadHealthStatus()
    }
  }, [isConfigured])

  const loadHealthStatus = async () => {
    try {
      setIsLoadingHealth(true)
      const health = await checkHealth()
      setHealthStatus(health)
    } catch (error) {
      console.error('Health check failed:', error)
    } finally {
      setIsLoadingHealth(false)
    }
  }

  const handleConnect = async () => {
    try {
      setIsConnecting(true)
      await configureVeeam(config)
      toast({
        title: "Connection successful",
        description: "Successfully connected to Veeam API",
      })
      loadHealthStatus()
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsConnecting(false)
    }
  }

  const handleTestConnection = async () => {
    if (isConfigured) {
      loadHealthStatus()
    } else {
      toast({
        title: "Not configured",
        description: "Please configure the connection first",
        variant: "destructive",
      })
    }
  }

  const getStatusIcon = (status) => {
    if (status === 'healthy') {
      return <CheckCircle className="h-5 w-5 text-green-500" />
    } else {
      return <AlertCircle className="h-5 w-5 text-red-500" />
    }
  }

  const getStatusBadge = (status) => {
    if (status === 'healthy') {
      return <Badge className="bg-green-100 text-green-800">Healthy</Badge>
    } else {
      return <Badge variant="destructive">Unhealthy</Badge>
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Configuration</h2>
        <p className="text-gray-500">Configure your Veeam API connection and system settings</p>
      </div>

      {/* Connection Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Server className="h-5 w-5" />
            <span>Veeam API Connection</span>
          </CardTitle>
          <CardDescription>
            Configure the connection to your Veeam Backup & Replication server
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="base_url">Server URL</Label>
              <Input
                id="base_url"
                type="url"
                placeholder="https://veeam-server:9419"
                value={config.base_url}
                onChange={(e) => setConfig({...config, base_url: e.target.value})}
              />
              <p className="text-sm text-gray-500 mt-1">
                Base URL of your Veeam Backup & Replication server
              </p>
            </div>
            
            <div>
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="veeam-user"
                value={config.username}
                onChange={(e) => setConfig({...config, username: e.target.value})}
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={config.password}
                onChange={(e) => setConfig({...config, password: e.target.value})}
              />
            </div>
            
            <div className="flex items-center space-x-2 pt-6">
              <Switch
                id="verify_ssl"
                checked={config.verify_ssl}
                onCheckedChange={(checked) => setConfig({...config, verify_ssl: checked})}
              />
              <Label htmlFor="verify_ssl" className="flex items-center space-x-2">
                <Shield className="h-4 w-4" />
                <span>Verify SSL certificates</span>
              </Label>
            </div>
          </div>
          
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm text-red-700">{error}</span>
              </div>
            </div>
          )}
          
          <div className="flex space-x-2">
            <Button 
              onClick={handleConnect} 
              disabled={isConnecting || !config.base_url || !config.username || !config.password}
            >
              {isConnecting ? (
                <>
                  <Activity className="h-4 w-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Server className="h-4 w-4 mr-2" />
                  {isConfigured ? 'Update Connection' : 'Connect'}
                </>
              )}
            </Button>
            
            {isConfigured && (
              <Button variant="outline" onClick={handleTestConnection} disabled={isLoadingHealth}>
                {isLoadingHealth ? (
                  <>
                    <Activity className="h-4 w-4 mr-2 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Test Connection
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Mount Server Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <HardDrive className="h-5 w-5" />
            <span>Mount Server Configuration</span>
          </CardTitle>
          <CardDescription>
            Configure the mount server settings for iSCSI disk publishing
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="mount_server_name">Mount Server Name/IP</Label>
              <Input
                id="mount_server_name"
                type="text"
                placeholder="172.21.234.6"
                value={config.mount_server_name}
                onChange={(e) => setConfig({...config, mount_server_name: e.target.value})}
              />
              <p className="text-sm text-gray-500 mt-1">
                DNS name or IP address of the target server for iSCSI mounting
              </p>
            </div>
            
            <div>
              <Label htmlFor="mount_host_id">Mount Host ID (Optional)</Label>
              <Input
                id="mount_host_id"
                type="text"
                placeholder="00000000-0000-0000-0000-000000000000"
                value={config.mount_host_id}
                onChange={(e) => setConfig({...config, mount_host_id: e.target.value})}
              />
              <p className="text-sm text-gray-500 mt-1">
                Mount server ID (leave empty to use default)
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <Switch
              id="reuse_api_credentials"
              checked={config.reuse_api_credentials}
              onCheckedChange={(checked) => setConfig({...config, reuse_api_credentials: checked})}
            />
            <Label htmlFor="reuse_api_credentials" className="flex items-center space-x-2">
              <Shield className="h-4 w-4" />
              <span>Reuse API connection credentials for mount server</span>
            </Label>
          </div>
          
          {!config.reuse_api_credentials && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="mount_server_username">Mount Server Username</Label>
                <Input
                  id="mount_server_username"
                  type="text"
                  placeholder="mount-username"
                  value={config.mount_server_username}
                  onChange={(e) => setConfig({...config, mount_server_username: e.target.value})}
                />
              </div>
              
              <div>
                <Label htmlFor="mount_server_password">Mount Server Password</Label>
                <Input
                  id="mount_server_password"
                  type="password"
                  placeholder="••••••••"
                  value={config.mount_server_password}
                  onChange={(e) => setConfig({...config, mount_server_password: e.target.value})}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* System Status */}
      {isConfigured && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>System Status</span>
            </CardTitle>
            <CardDescription>
              Current status of the Veeam ML integration system
            </CardDescription>
          </CardHeader>
          <CardContent>
            {healthStatus ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(healthStatus.status)}
                    <span className="font-medium">Overall Status</span>
                  </div>
                  {getStatusBadge(healthStatus.status)}
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <Database className="h-4 w-4 text-blue-500" />
                      <span className="font-medium">Database</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {healthStatus.database_connected ? (
                        <>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm text-green-700">Connected</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4 text-red-500" />
                          <span className="text-sm text-red-700">Disconnected</span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <Server className="h-4 w-4 text-purple-500" />
                      <span className="font-medium">Veeam API</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      {healthStatus.veeam_api_configured ? (
                        <>
                          <CheckCircle className="h-4 w-4 text-green-500" />
                          <span className="text-sm text-green-700">Configured</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4 text-red-500" />
                          <span className="text-sm text-red-700">Not Configured</span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center space-x-2 mb-2">
                      <Brain className="h-4 w-4 text-green-500" />
                      <span className="font-medium">ML Engine</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-green-700">Ready</span>
                    </div>
                  </div>
                </div>
                
                <div className="text-xs text-gray-500">
                  Last updated: {new Date(healthStatus.timestamp).toLocaleString()}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Activity className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-gray-500">System status not available</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ML Algorithm Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5" />
            <span>Supported ML Algorithms</span>
          </CardTitle>
          <CardDescription>
            Machine learning algorithms available for analyzing backup data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-blue-600 mb-2">Classification</h4>
              <p className="text-sm text-gray-600">
                Predict categories and classify data points into predefined groups.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Supervised</Badge>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-green-600 mb-2">Regression</h4>
              <p className="text-sm text-gray-600">
                Predict continuous numerical values and forecast trends.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Supervised</Badge>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-purple-600 mb-2">Clustering</h4>
              <p className="text-sm text-gray-600">
                Discover hidden groups and patterns in your data.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Unsupervised</Badge>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-red-600 mb-2">Anomaly Detection</h4>
              <p className="text-sm text-gray-600">
                Identify unusual patterns and outliers in your backup data.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Unsupervised</Badge>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-orange-600 mb-2">Feature Extraction</h4>
              <p className="text-sm text-gray-600">
                Extract and derive meaningful features from raw data.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Preprocessing</Badge>
              </div>
            </div>
            
            <div className="p-4 border rounded-lg">
              <h4 className="font-medium text-teal-600 mb-2">Time Series</h4>
              <p className="text-sm text-gray-600">
                Analyze temporal patterns and forecast future values.
              </p>
              <div className="mt-2">
                <Badge variant="outline">Temporal</Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Getting Started */}
      {!isConfigured && (
        <Card>
          <CardHeader>
            <CardTitle>Getting Started</CardTitle>
            <CardDescription>
              Follow these steps to set up your Veeam ML integration
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                  1
                </div>
                <div>
                  <h4 className="font-medium">Configure Veeam Connection</h4>
                  <p className="text-sm text-gray-600">
                    Enter your Veeam Backup & Replication server details above
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                  2
                </div>
                <div>
                  <h4 className="font-medium">Mount Backups</h4>
                  <p className="text-sm text-gray-600">
                    Go to the Backups section to mount your backup files
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                  3
                </div>
                <div>
                  <h4 className="font-medium">Create ML Jobs</h4>
                  <p className="text-sm text-gray-600">
                    Create machine learning jobs to analyze your backup data
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                  4
                </div>
                <div>
                  <h4 className="font-medium">View Results</h4>
                  <p className="text-sm text-gray-600">
                    Monitor job progress and view insights on the Dashboard
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

