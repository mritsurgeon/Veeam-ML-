import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useVeeamAPI } from '@/hooks/useVeeamAPI'
import { useToast } from '@/hooks/use-toast'
import { 
  Database, 
  Brain, 
  Activity, 
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart3
} from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

export const Dashboard = () => {
  const [stats, setStats] = useState({
    totalBackups: 0,
    mountedBackups: 0,
    totalMLJobs: 0,
    runningJobs: 0,
    completedJobs: 0,
    failedJobs: 0
  })
  const [recentJobs, setRecentJobs] = useState([])
  const [mlJobsByType, setMLJobsByType] = useState([])
  const [isLoading, setIsLoading] = useState(true)

  const { getBackups, getMLJobs, checkHealth, isConfigured } = useVeeamAPI()
  const { toast } = useToast()

  useEffect(() => {
    if (isConfigured) {
      loadDashboardData()
    }
  }, [isConfigured])

  const loadDashboardData = async () => {
    try {
      setIsLoading(true)
      
      // Load backups
      const backupsResponse = await getBackups()
      const backups = backupsResponse.backups || []
      
      // Load ML jobs
      const jobsResponse = await getMLJobs()
      const jobs = jobsResponse.ml_jobs || []
      
      // Calculate statistics
      const mountedBackups = backups.filter(b => b.status === 'mounted').length
      const runningJobs = jobs.filter(j => j.status === 'running').length
      const completedJobs = jobs.filter(j => j.status === 'completed').length
      const failedJobs = jobs.filter(j => j.status === 'failed').length
      
      setStats({
        totalBackups: backups.length,
        mountedBackups,
        totalMLJobs: jobs.length,
        runningJobs,
        completedJobs,
        failedJobs
      })
      
      // Get recent jobs (last 10)
      const sortedJobs = jobs
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
        .slice(0, 10)
      setRecentJobs(sortedJobs)
      
      // Group jobs by ML algorithm type
      const jobsByType = jobs.reduce((acc, job) => {
        const type = job.ml_algorithm
        acc[type] = (acc[type] || 0) + 1
        return acc
      }, {})
      
      const chartData = Object.entries(jobsByType).map(([type, count]) => ({
        name: type,
        value: count
      }))
      setMLJobsByType(chartData)
      
    } catch (error) {
      toast({
        title: "Error loading dashboard",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status) => {
    const variants = {
      completed: 'default',
      running: 'secondary',
      failed: 'destructive',
      pending: 'outline'
    }
    return <Badge variant={variants[status] || 'outline'}>{status}</Badge>
  }

  if (!isConfigured) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Veeam API Not Configured
          </h3>
          <p className="text-gray-500 mb-4">
            Please configure your Veeam connection in the Configuration panel.
          </p>
          <Button onClick={() => window.location.href = '/configuration'}>
            Go to Configuration
          </Button>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-gray-500">Overview of your Veeam ML integration</p>
        </div>
        <Button onClick={loadDashboardData} variant="outline">
          <Activity className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Backups</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalBackups}</div>
            <p className="text-xs text-muted-foreground">
              {stats.mountedBackups} currently mounted
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">ML Jobs</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalMLJobs}</div>
            <p className="text-xs text-muted-foreground">
              {stats.runningJobs} running
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed Jobs</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.completedJobs}</div>
            <p className="text-xs text-muted-foreground">
              Success rate: {stats.totalMLJobs > 0 ? Math.round((stats.completedJobs / stats.totalMLJobs) * 100) : 0}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Jobs</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.failedJobs}</div>
            <p className="text-xs text-muted-foreground">
              {stats.totalMLJobs > 0 ? Math.round((stats.failedJobs / stats.totalMLJobs) * 100) : 0}% failure rate
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ML Jobs by Type */}
        <Card>
          <CardHeader>
            <CardTitle>ML Jobs by Algorithm Type</CardTitle>
            <CardDescription>Distribution of machine learning algorithms used</CardDescription>
          </CardHeader>
          <CardContent>
            {mlJobsByType.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={mlJobsByType}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {mlJobsByType.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No ML jobs data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent ML Jobs</CardTitle>
            <CardDescription>Latest machine learning jobs and their status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentJobs.length > 0 ? (
                recentJobs.map((job) => (
                  <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(job.status)}
                      <div>
                        <p className="font-medium text-sm">{job.job_name}</p>
                        <p className="text-xs text-gray-500">{job.ml_algorithm}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      {getStatusBadge(job.status)}
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(job.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  No recent jobs found
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks and shortcuts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button 
              variant="outline" 
              className="h-20 flex flex-col items-center justify-center space-y-2"
              onClick={() => window.location.href = '/backups'}
            >
              <Database className="h-6 w-6" />
              <span>Manage Backups</span>
            </Button>
            
            <Button 
              variant="outline" 
              className="h-20 flex flex-col items-center justify-center space-y-2"
              onClick={() => window.location.href = '/ml-jobs'}
            >
              <Brain className="h-6 w-6" />
              <span>Create ML Job</span>
            </Button>
            
            <Button 
              variant="outline" 
              className="h-20 flex flex-col items-center justify-center space-y-2"
              onClick={() => window.location.href = '/configuration'}
            >
              <BarChart3 className="h-6 w-6" />
              <span>View Analytics</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

