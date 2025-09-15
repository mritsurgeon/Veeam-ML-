import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useVeeamAPI } from '@/hooks/useVeeamAPI'
import { useToast } from '@/hooks/use-toast'
import { 
  Brain, 
  Plus, 
  Play, 
  Trash2, 
  Eye,
  RefreshCw,
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  BarChart3,
  TrendingUp,
  Users,
  Search,
  Target
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  ScatterChart,
  Scatter
} from 'recharts'

const ML_ALGORITHMS = [
  { value: 'classification', label: 'Classification', description: 'Predict categories' },
  { value: 'regression', label: 'Regression', description: 'Predict numeric values' },
  { value: 'clustering', label: 'Clustering', description: 'Discover groups' },
  { value: 'anomaly_detection', label: 'Anomaly Detection', description: 'Identify unusual cases' },
  { value: 'feature_extraction', label: 'Feature Extraction', description: 'Derive new features' }
]

export const MLJobManager = () => {
  const [jobs, setJobs] = useState([])
  const [backups, setBackups] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedJob, setSelectedJob] = useState(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showResultsDialog, setShowResultsDialog] = useState(false)
  const [newJob, setNewJob] = useState({
    job_name: '',
    ml_algorithm: '',
    backup_id: '',
    data_source_path: '',
    parameters: {}
  })

  const { getMLJobs, getBackups, createMLJob, executeMLJob, deleteMLJob, getMLJob } = useVeeamAPI()
  const { toast } = useToast()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setIsLoading(true)
      const [jobsResponse, backupsResponse] = await Promise.all([
        getMLJobs(),
        getBackups()
      ])
      setJobs(jobsResponse.ml_jobs || [])
      setBackups(backupsResponse.backups || [])
    } catch (error) {
      toast({
        title: "Error loading data",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateJob = async () => {
    try {
      if (!newJob.job_name || !newJob.ml_algorithm || !newJob.backup_id) {
        toast({
          title: "Validation error",
          description: "Please fill in all required fields",
          variant: "destructive",
        })
        return
      }

      await createMLJob(newJob)
      toast({
        title: "Job created",
        description: `ML job "${newJob.job_name}" has been created successfully`,
      })
      
      setShowCreateDialog(false)
      setNewJob({
        job_name: '',
        ml_algorithm: '',
        backup_id: '',
        data_source_path: '',
        parameters: {}
      })
      loadData()
    } catch (error) {
      toast({
        title: "Error creating job",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const handleExecuteJob = async (job) => {
    try {
      await executeMLJob(job.id)
      toast({
        title: "Job started",
        description: `ML job "${job.job_name}" has been started`,
      })
      loadData()
    } catch (error) {
      toast({
        title: "Error executing job",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const handleDeleteJob = async (job) => {
    try {
      await deleteMLJob(job.id)
      toast({
        title: "Job deleted",
        description: `ML job "${job.job_name}" has been deleted`,
      })
      loadData()
    } catch (error) {
      toast({
        title: "Error deleting job",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const handleViewResults = async (job) => {
    try {
      const jobDetails = await getMLJob(job.id)
      setSelectedJob(jobDetails)
      setShowResultsDialog(true)
    } catch (error) {
      toast({
        title: "Error loading job details",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'running':
        return <Activity className="h-4 w-4 text-blue-500 animate-spin" />
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

  const renderMLResults = (results) => {
    if (!results || !results.parsed_results) return null

    const data = results.parsed_results

    switch (data.model_type) {
      case 'classification':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Accuracy</div>
                <div className="text-2xl font-bold text-blue-600">
                  {(data.accuracy * 100).toFixed(1)}%
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Features Used</div>
                <div className="text-2xl font-bold text-green-600">
                  {data.feature_importance?.length || 0}
                </div>
              </div>
            </div>
            
            {data.feature_importance && (
              <div>
                <h4 className="font-medium mb-2">Feature Importance</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.feature_importance.slice(0, 10)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="feature" angle={-45} textAnchor="end" height={80} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="importance" fill="#3B82F6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )

      case 'regression':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">R² Score</div>
                <div className="text-2xl font-bold text-blue-600">
                  {data.r2_score?.toFixed(3) || 'N/A'}
                </div>
              </div>
              <div className="bg-red-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">RMSE</div>
                <div className="text-2xl font-bold text-red-600">
                  {data.rmse?.toFixed(3) || 'N/A'}
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Features</div>
                <div className="text-2xl font-bold text-green-600">
                  {data.feature_importance?.length || 0}
                </div>
              </div>
            </div>
            
            {data.predictions && (
              <div>
                <h4 className="font-medium mb-2">Predictions vs Actual</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="actual" name="Actual" />
                    <YAxis dataKey="predicted" name="Predicted" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter 
                      name="Predictions" 
                      data={data.predictions.y_test.map((actual, i) => ({
                        actual,
                        predicted: data.predictions.y_pred[i]
                      }))} 
                      fill="#3B82F6" 
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )

      case 'clustering':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Clusters Found</div>
                <div className="text-2xl font-bold text-purple-600">
                  {data.n_clusters}
                </div>
              </div>
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Silhouette Score</div>
                <div className="text-2xl font-bold text-blue-600">
                  {data.silhouette_score?.toFixed(3) || 'N/A'}
                </div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Algorithm</div>
                <div className="text-lg font-bold text-green-600">
                  {data.algorithm}
                </div>
              </div>
            </div>
            
            {data.cluster_analysis && (
              <div>
                <h4 className="font-medium mb-2">Cluster Distribution</h4>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.cluster_analysis}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="cluster_id" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="size" fill="#8B5CF6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )

      case 'anomaly_detection':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-red-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Anomalies Found</div>
                <div className="text-2xl font-bold text-red-600">
                  {data.anomalies_detected}
                </div>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Anomaly Rate</div>
                <div className="text-2xl font-bold text-yellow-600">
                  {data.anomaly_percentage?.toFixed(1)}%
                </div>
              </div>
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-sm text-gray-600">Total Samples</div>
                <div className="text-2xl font-bold text-blue-600">
                  {data.total_samples}
                </div>
              </div>
            </div>
            
            {data.anomaly_details && data.anomaly_details.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Top Anomalies</h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {data.anomaly_details.slice(0, 5).map((anomaly, index) => (
                    <div key={index} className="p-2 bg-red-50 rounded border">
                      <div className="text-sm">
                        <strong>Index:</strong> {anomaly.index}, 
                        <strong> Score:</strong> {anomaly.anomaly_score?.toFixed(3)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )

      default:
        return (
          <div className="text-center py-8 text-gray-500">
            Results visualization not available for this algorithm type
          </div>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-500">Loading ML jobs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">ML Job Manager</h2>
          <p className="text-gray-500">Create and manage machine learning jobs</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={loadData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Job
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Create New ML Job</DialogTitle>
                <DialogDescription>
                  Configure a new machine learning job to analyze your backup data
                </DialogDescription>
              </DialogHeader>
              
              <div className="space-y-4">
                <div>
                  <Label htmlFor="job_name">Job Name</Label>
                  <Input
                    id="job_name"
                    value={newJob.job_name}
                    onChange={(e) => setNewJob({...newJob, job_name: e.target.value})}
                    placeholder="Enter job name"
                  />
                </div>
                
                <div>
                  <Label htmlFor="ml_algorithm">ML Algorithm</Label>
                  <Select 
                    value={newJob.ml_algorithm} 
                    onValueChange={(value) => setNewJob({...newJob, ml_algorithm: value})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select algorithm" />
                    </SelectTrigger>
                    <SelectContent>
                      {ML_ALGORITHMS.map((algo) => (
                        <SelectItem key={algo.value} value={algo.value}>
                          <div>
                            <div className="font-medium">{algo.label}</div>
                            <div className="text-sm text-gray-500">{algo.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="backup_id">Backup</Label>
                  <Select 
                    value={newJob.backup_id} 
                    onValueChange={(value) => setNewJob({...newJob, backup_id: value})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select backup" />
                    </SelectTrigger>
                    <SelectContent>
                      {backups.filter(b => b.status === 'mounted').map((backup) => (
                        <SelectItem key={backup.id} value={backup.id.toString()}>
                          {backup.backup_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label htmlFor="data_source_path">Data Source Path (Optional)</Label>
                  <Input
                    id="data_source_path"
                    value={newJob.data_source_path}
                    onChange={(e) => setNewJob({...newJob, data_source_path: e.target.value})}
                    placeholder="e.g., /logs/application.log"
                  />
                </div>
                
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateJob}>
                    Create Job
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Jobs List */}
      <div className="grid gap-4">
        {jobs.length > 0 ? (
          jobs.map((job) => (
            <Card key={job.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <Brain className="h-6 w-6 text-purple-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {job.job_name}
                      </h3>
                      <p className="text-sm text-gray-500">
                        Algorithm: {job.ml_algorithm} • Created: {new Date(job.created_at).toLocaleDateString()}
                      </p>
                      {job.progress > 0 && job.status === 'running' && (
                        <div className="mt-2">
                          <div className="flex items-center space-x-2">
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                              <div 
                                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${job.progress}%` }}
                              />
                            </div>
                            <span className="text-sm text-gray-500">{job.progress.toFixed(0)}%</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(job.status)}
                      {getStatusBadge(job.status)}
                    </div>
                    
                    <div className="flex space-x-2">
                      {job.status === 'pending' && (
                        <Button
                          size="sm"
                          onClick={() => handleExecuteJob(job)}
                          className="flex items-center"
                        >
                          <Play className="h-4 w-4 mr-1" />
                          Execute
                        </Button>
                      )}
                      
                      {job.status === 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewResults(job)}
                          className="flex items-center"
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          Results
                        </Button>
                      )}
                      
                      {job.status !== 'running' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteJob(job)}
                          className="flex items-center text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Delete
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
                
                {job.error_message && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <div className="text-sm text-red-700">
                      <strong>Error:</strong> {job.error_message}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No ML jobs found</h3>
              <p className="text-gray-500 mb-4">
                Create your first machine learning job to start analyzing backup data.
              </p>
              <Button onClick={() => setShowCreateDialog(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Create First Job
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Results Dialog */}
      <Dialog open={showResultsDialog} onOpenChange={setShowResultsDialog}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>ML Job Results</DialogTitle>
            <DialogDescription>
              {selectedJob?.job_name} - {selectedJob?.ml_algorithm}
            </DialogDescription>
          </DialogHeader>
          
          {selectedJob && renderMLResults(selectedJob)}
        </DialogContent>
      </Dialog>
    </div>
  )
}

