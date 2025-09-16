import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { 
  Play, 
  Pause, 
  Square, 
  Settings, 
  FileText, 
  Database, 
  BarChart3,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'

const ExtractionJobManager = () => {
  const [jobs, setJobs] = useState([])
  const [templates, setTemplates] = useState([])
  const [activeJobs, setActiveJobs] = useState([])
  const [selectedJob, setSelectedJob] = useState(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [showTemplateForm, setShowTemplateForm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Form state
  const [jobForm, setJobForm] = useState({
    name: '',
    description: '',
    extraction_level: 'metadata_only',
    file_type_filter: 'all_files',
    custom_file_types: [],
    backup_id: '',
    directory_path: '/',
    max_depth: 3,
    max_file_size: 52428800, // 50MB
    chunk_size: 2000,
    include_attributes: false,
    parallel_processing: true,
    max_workers: 4,
    enable_document_parsing: true,
    enable_spreadsheet_parsing: true,
    enable_presentation_parsing: true,
    enable_log_parsing: true,
    enable_config_parsing: true,
    enable_sqlite_extraction: true,
    enable_sql_dump_parsing: true,
    enable_enterprise_db_extraction: false,
    max_db_rows_per_table: 1000,
    output_format: 'json',
    include_raw_content: true,
    include_chunks: true,
    include_embeddings: false
  })

  const [extractionLevels, setExtractionLevels] = useState([])
  const [fileFilters, setFileFilters] = useState([])
  const [supportedFileTypes, setSupportedFileTypes] = useState({})

  useEffect(() => {
    loadData()
    loadConfiguration()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [jobsRes, templatesRes, activeJobsRes] = await Promise.all([
        fetch('/api/extraction/jobs'),
        fetch('/api/extraction/templates'),
        fetch('/api/extraction/active-jobs')
      ])

      if (jobsRes.ok) {
        const jobsData = await jobsRes.json()
        setJobs(jobsData.jobs)
      }

      if (templatesRes.ok) {
        const templatesData = await templatesRes.json()
        setTemplates(templatesData.templates)
      }

      if (activeJobsRes.ok) {
        const activeJobsData = await activeJobsRes.json()
        setActiveJobs(activeJobsData.active_jobs)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const loadConfiguration = async () => {
    try {
      const [levelsRes, filtersRes, fileTypesRes] = await Promise.all([
        fetch('/api/extraction/config/levels'),
        fetch('/api/extraction/config/file-filters'),
        fetch('/api/extraction/config/file-types')
      ])

      if (levelsRes.ok) {
        const levelsData = await levelsRes.json()
        setExtractionLevels(levelsData.extraction_levels)
      }

      if (filtersRes.ok) {
        const filtersData = await filtersRes.json()
        setFileFilters(filtersData.file_filters)
      }

      if (fileTypesRes.ok) {
        const fileTypesData = await fileTypesRes.json()
        setSupportedFileTypes(fileTypesData.file_types)
      }
    } catch (err) {
      console.error('Failed to load configuration:', err)
    }
  }

  const createJob = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/extraction/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(jobForm)
      })

      if (response.ok) {
        await loadData()
        setShowCreateForm(false)
        setJobForm({
          name: '',
          description: '',
          extraction_level: 'metadata_only',
          file_type_filter: 'all_files',
          custom_file_types: [],
          backup_id: '',
          directory_path: '/',
          max_depth: 3,
          max_file_size: 52428800,
          chunk_size: 2000,
          include_attributes: false,
          parallel_processing: true,
          max_workers: 4,
          enable_document_parsing: true,
          enable_spreadsheet_parsing: true,
          enable_presentation_parsing: true,
          enable_log_parsing: true,
          enable_config_parsing: true,
          enable_sqlite_extraction: true,
          enable_sql_dump_parsing: true,
          enable_enterprise_db_extraction: false,
          max_db_rows_per_table: 1000,
          output_format: 'json',
          include_raw_content: true,
          include_chunks: true,
          include_embeddings: false
        })
      } else {
        const errorData = await response.json()
        setError(errorData.error)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const createJobFromTemplate = async (templateId) => {
    try {
      setLoading(true)
      const response = await fetch('/api/extraction/jobs/from-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: templateId,
          name: `${templates.find(t => t.id === templateId)?.name} - ${new Date().toLocaleString()}`,
          backup_id: jobForm.backup_id
        })
      })

      if (response.ok) {
        await loadData()
      } else {
        const errorData = await response.json()
        setError(errorData.error)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const executeJob = async (jobId) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/extraction/jobs/${jobId}/execute`, {
        method: 'POST'
      })

      if (response.ok) {
        await loadData()
      } else {
        const errorData = await response.json()
        setError(errorData.error)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const cancelJob = async (jobId) => {
    try {
      setLoading(true)
      const response = await fetch(`/api/extraction/jobs/${jobId}/cancel`, {
        method: 'POST'
      })

      if (response.ok) {
        await loadData()
      } else {
        const errorData = await response.json()
        setError(errorData.error)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />
      case 'running': return <Clock className="h-4 w-4 text-blue-500" />
      case 'pending': return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default: return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'running': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Extraction Job Manager</h1>
          <p className="text-gray-600">Create and manage configurable data extraction jobs</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowTemplateForm(true)} variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            Templates
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <FileText className="h-4 w-4 mr-2" />
            Create Job
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="jobs" className="space-y-4">
        <TabsList>
          <TabsTrigger value="jobs">Jobs</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="active">Active Jobs</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs" className="space-y-4">
          <div className="grid gap-4">
            {jobs.map((job) => (
              <Card key={job.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        {getStatusIcon(job.status)}
                        {job.name}
                      </CardTitle>
                      <CardDescription>{job.description}</CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Badge className={getStatusColor(job.status)}>
                        {job.status.replace('_', ' ')}
                      </Badge>
                      {job.status === 'running' && (
                        <Badge variant="outline">
                          {job.progress_percentage.toFixed(1)}%
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <Label className="text-gray-500">Extraction Level</Label>
                      <p className="font-medium">{job.extraction_level.replace('_', ' ')}</p>
                    </div>
                    <div>
                      <Label className="text-gray-500">File Filter</Label>
                      <p className="font-medium">{job.file_type_filter.replace('_', ' ')}</p>
                    </div>
                    <div>
                      <Label className="text-gray-500">Files Processed</Label>
                      <p className="font-medium">{job.processed_files} / {job.total_files}</p>
                    </div>
                    <div>
                      <Label className="text-gray-500">Created</Label>
                      <p className="font-medium">{new Date(job.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                  
                  {job.status === 'running' && (
                    <div className="mt-4">
                      <Progress value={job.progress_percentage} className="w-full" />
                    </div>
                  )}

                  <div className="flex gap-2 mt-4">
                    {job.status === 'pending' && (
                      <Button onClick={() => executeJob(job.id)} size="sm">
                        <Play className="h-4 w-4 mr-2" />
                        Execute
                      </Button>
                    )}
                    {job.status === 'running' && (
                      <Button onClick={() => cancelJob(job.id)} variant="destructive" size="sm">
                        <Square className="h-4 w-4 mr-2" />
                        Cancel
                      </Button>
                    )}
                    <Button 
                      onClick={() => setSelectedJob(job)} 
                      variant="outline" 
                      size="sm"
                    >
                      View Details
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <div className="grid gap-4">
            {templates.map((template) => (
              <Card key={template.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle>{template.name}</CardTitle>
                      <CardDescription>{template.description}</CardDescription>
                    </div>
                    <Badge variant="outline">{template.category}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center">
                    <div className="text-sm text-gray-500">
                      Used {template.usage_count} times
                    </div>
                    <Button 
                      onClick={() => createJobFromTemplate(template.id)}
                      disabled={!jobForm.backup_id}
                      size="sm"
                    >
                      Use Template
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="active" className="space-y-4">
          <div className="grid gap-4">
            {activeJobs.map((activeJob) => (
              <Card key={activeJob.job_id} className="border-blue-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-blue-500" />
                    {activeJob.job_name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress</span>
                      <span>{activeJob.progress.toFixed(1)}%</span>
                    </div>
                    <Progress value={activeJob.progress} className="w-full" />
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>Runtime: {Math.round(activeJob.runtime)}s</span>
                      <span>Started: {new Date(activeJob.start_time).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Job Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Create Extraction Job</CardTitle>
              <CardDescription>Configure a new data extraction job</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Tabs defaultValue="basic" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="basic">Basic</TabsTrigger>
                  <TabsTrigger value="scope">Scope</TabsTrigger>
                  <TabsTrigger value="processing">Processing</TabsTrigger>
                  <TabsTrigger value="output">Output</TabsTrigger>
                </TabsList>

                <TabsContent value="basic" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Job Name</Label>
                      <Input
                        id="name"
                        value={jobForm.name}
                        onChange={(e) => setJobForm({...jobForm, name: e.target.value})}
                        placeholder="Enter job name"
                      />
                    </div>
                    <div>
                      <Label htmlFor="backup_id">Backup ID</Label>
                      <Input
                        id="backup_id"
                        value={jobForm.backup_id}
                        onChange={(e) => setJobForm({...jobForm, backup_id: e.target.value})}
                        placeholder="Enter backup ID"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={jobForm.description}
                      onChange={(e) => setJobForm({...jobForm, description: e.target.value})}
                      placeholder="Enter job description"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="extraction_level">Extraction Level</Label>
                      <Select 
                        value={jobForm.extraction_level} 
                        onValueChange={(value) => setJobForm({...jobForm, extraction_level: value})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {extractionLevels.map((level) => (
                            <SelectItem key={level.value} value={level.value}>
                              {level.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="file_type_filter">File Type Filter</Label>
                      <Select 
                        value={jobForm.file_type_filter} 
                        onValueChange={(value) => setJobForm({...jobForm, file_type_filter: value})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {fileFilters.map((filter) => (
                            <SelectItem key={filter.value} value={filter.value}>
                              {filter.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="scope" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="directory_path">Directory Path</Label>
                      <Input
                        id="directory_path"
                        value={jobForm.directory_path}
                        onChange={(e) => setJobForm({...jobForm, directory_path: e.target.value})}
                        placeholder="/"
                      />
                    </div>
                    <div>
                      <Label htmlFor="max_depth">Max Depth</Label>
                      <Input
                        id="max_depth"
                        type="number"
                        value={jobForm.max_depth}
                        onChange={(e) => setJobForm({...jobForm, max_depth: parseInt(e.target.value)})}
                        min="1"
                        max="10"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <Label htmlFor="max_file_size">Max File Size (bytes)</Label>
                    <Input
                      id="max_file_size"
                      type="number"
                      value={jobForm.max_file_size}
                      onChange={(e) => setJobForm({...jobForm, max_file_size: parseInt(e.target.value)})}
                      placeholder="52428800"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Switch
                      id="include_attributes"
                      checked={jobForm.include_attributes}
                      onCheckedChange={(checked) => setJobForm({...jobForm, include_attributes: checked})}
                    />
                    <Label htmlFor="include_attributes">Include Extended File Attributes</Label>
                  </div>
                </TabsContent>

                <TabsContent value="processing" className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="chunk_size">Chunk Size</Label>
                      <Input
                        id="chunk_size"
                        type="number"
                        value={jobForm.chunk_size}
                        onChange={(e) => setJobForm({...jobForm, chunk_size: parseInt(e.target.value)})}
                        placeholder="2000"
                      />
                    </div>
                    <div>
                      <Label htmlFor="max_workers">Max Workers</Label>
                      <Input
                        id="max_workers"
                        type="number"
                        value={jobForm.max_workers}
                        onChange={(e) => setJobForm({...jobForm, max_workers: parseInt(e.target.value)})}
                        min="1"
                        max="16"
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium">Content Parsing Options</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_document_parsing"
                          checked={jobForm.enable_document_parsing}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_document_parsing: checked})}
                        />
                        <Label htmlFor="enable_document_parsing">Documents</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_spreadsheet_parsing"
                          checked={jobForm.enable_spreadsheet_parsing}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_spreadsheet_parsing: checked})}
                        />
                        <Label htmlFor="enable_spreadsheet_parsing">Spreadsheets</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_presentation_parsing"
                          checked={jobForm.enable_presentation_parsing}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_presentation_parsing: checked})}
                        />
                        <Label htmlFor="enable_presentation_parsing">Presentations</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_log_parsing"
                          checked={jobForm.enable_log_parsing}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_log_parsing: checked})}
                        />
                        <Label htmlFor="enable_log_parsing">Logs</Label>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium">Database Extraction Options</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_sqlite_extraction"
                          checked={jobForm.enable_sqlite_extraction}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_sqlite_extraction: checked})}
                        />
                        <Label htmlFor="enable_sqlite_extraction">SQLite</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="enable_sql_dump_parsing"
                          checked={jobForm.enable_sql_dump_parsing}
                          onCheckedChange={(checked) => setJobForm({...jobForm, enable_sql_dump_parsing: checked})}
                        />
                        <Label htmlFor="enable_sql_dump_parsing">SQL Dumps</Label>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="output" className="space-y-4">
                  <div>
                    <Label htmlFor="output_format">Output Format</Label>
                    <Select 
                      value={jobForm.output_format} 
                      onValueChange={(value) => setJobForm({...jobForm, output_format: value})}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="json">JSON</SelectItem>
                        <SelectItem value="csv">CSV</SelectItem>
                        <SelectItem value="parquet">Parquet</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium">Output Options</h4>
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="include_raw_content"
                          checked={jobForm.include_raw_content}
                          onCheckedChange={(checked) => setJobForm({...jobForm, include_raw_content: checked})}
                        />
                        <Label htmlFor="include_raw_content">Include Raw Content</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="include_chunks"
                          checked={jobForm.include_chunks}
                          onCheckedChange={(checked) => setJobForm({...jobForm, include_chunks: checked})}
                        />
                        <Label htmlFor="include_chunks">Include Text Chunks</Label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="include_embeddings"
                          checked={jobForm.include_embeddings}
                          onCheckedChange={(checked) => setJobForm({...jobForm, include_embeddings: checked})}
                        />
                        <Label htmlFor="include_embeddings">Include Embeddings</Label>
                      </div>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
                <Button onClick={createJob} disabled={loading || !jobForm.name || !jobForm.backup_id}>
                  Create Job
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export default ExtractionJobManager
