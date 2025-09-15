import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useVeeamAPI } from '@/hooks/useVeeamAPI'
import { useToast } from '@/hooks/use-toast'
import { 
  Database, 
  HardDrive, 
  Calendar, 
  Search,
  RefreshCw,
  HardDriveUpload,
  HardDriveDownload,
  FolderOpen,
  FileText,
  Activity
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export const BackupManager = () => {
  const [backups, setBackups] = useState([])
  const [filteredBackups, setFilteredBackups] = useState([])
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [scanResults, setScanResults] = useState(null)
  const [isScanning, setIsScanning] = useState(false)

  const { getBackups, mountBackup, unmountBackup, scanBackupFiles } = useVeeamAPI()
  const { toast } = useToast()

  useEffect(() => {
    loadBackups()
  }, [])

  useEffect(() => {
    // Filter backups based on search term
    const filtered = backups.filter(backup =>
      backup.backup_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      backup.backup_id.toLowerCase().includes(searchTerm.toLowerCase())
    )
    setFilteredBackups(filtered)
  }, [backups, searchTerm])

  const loadBackups = async () => {
    try {
      setIsLoading(true)
      const response = await getBackups()
      setBackups(response.backups || [])
    } catch (error) {
      toast({
        title: "Error loading backups",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleMount = async (backup) => {
    try {
      await mountBackup(backup.id)
      toast({
        title: "Backup mounted",
        description: `${backup.backup_name} has been mounted successfully`,
      })
      loadBackups() // Refresh the list
    } catch (error) {
      toast({
        title: "Mount failed",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const handleUnmount = async (backup) => {
    try {
      await unmountBackup(backup.id)
      toast({
        title: "Backup unmounted",
        description: `${backup.backup_name} has been unmounted successfully`,
      })
      loadBackups() // Refresh the list
    } catch (error) {
      toast({
        title: "Unmount failed",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  const handleScanFiles = async (backup) => {
    try {
      setIsScanning(true)
      setSelectedBackup(backup)
      const response = await scanBackupFiles(backup.id)
      setScanResults(response)
    } catch (error) {
      toast({
        title: "Scan failed",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setIsScanning(false)
    }
  }

  const getStatusBadge = (status) => {
    const variants = {
      available: 'outline',
      mounted: 'default',
      processing: 'secondary',
      error: 'destructive'
    }
    const colors = {
      available: 'text-gray-600',
      mounted: 'text-green-600',
      processing: 'text-blue-600',
      error: 'text-red-600'
    }
    return (
      <Badge variant={variants[status] || 'outline'} className={colors[status]}>
        {status}
      </Badge>
    )
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown'
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown'
    return new Date(dateString).toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-500">Loading backups...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Backup Manager</h2>
          <p className="text-gray-500">Manage and explore your Veeam backups</p>
        </div>
        <Button onClick={loadBackups} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Search and Filter</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <Label htmlFor="search">Search backups</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                <Input
                  id="search"
                  placeholder="Search by backup name or ID..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backups List */}
      <div className="grid gap-4">
        {filteredBackups.length > 0 ? (
          filteredBackups.map((backup) => (
            <Card key={backup.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Database className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">
                        {backup.backup_name}
                      </h3>
                      <p className="text-sm text-gray-500">ID: {backup.backup_id}</p>
                      <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                        <div className="flex items-center">
                          <Calendar className="h-4 w-4 mr-1" />
                          {formatDate(backup.backup_date)}
                        </div>
                        <div className="flex items-center">
                          <HardDrive className="h-4 w-4 mr-1" />
                          {formatFileSize(backup.backup_size)}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-3">
                    {getStatusBadge(backup.status)}
                    
                    <div className="flex space-x-2">
                      {backup.status === 'available' ? (
                        <Button
                          size="sm"
                          onClick={() => handleMount(backup)}
                          className="flex items-center"
                        >
                          <HardDriveUpload className="h-4 w-4 mr-1" />
                          Mount
                        </Button>
                      ) : backup.status === 'mounted' ? (
                        <>
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleScanFiles(backup)}
                                className="flex items-center"
                              >
                                <FolderOpen className="h-4 w-4 mr-1" />
                                Scan Files
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle>Backup File Scan Results</DialogTitle>
                                <DialogDescription>
                                  Extractable files found in {selectedBackup?.backup_name}
                                </DialogDescription>
                              </DialogHeader>
                              
                              {isScanning ? (
                                <div className="flex items-center justify-center py-8">
                                  <Activity className="h-6 w-6 animate-spin text-blue-500 mr-2" />
                                  Scanning backup files...
                                </div>
                              ) : scanResults ? (
                                <div className="space-y-4">
                                  <div className="grid grid-cols-3 gap-4 text-sm">
                                    <div className="bg-blue-50 p-3 rounded">
                                      <div className="font-medium">Total Files</div>
                                      <div className="text-2xl font-bold text-blue-600">
                                        {scanResults.total_files}
                                      </div>
                                    </div>
                                    <div className="bg-green-50 p-3 rounded">
                                      <div className="font-medium">Extractable</div>
                                      <div className="text-2xl font-bold text-green-600">
                                        {scanResults.extractable_count}
                                      </div>
                                    </div>
                                    <div className="bg-gray-50 p-3 rounded">
                                      <div className="font-medium">Mount Point</div>
                                      <div className="text-sm font-mono">
                                        {scanResults.mount_point}
                                      </div>
                                    </div>
                                  </div>
                                  
                                  <div className="border rounded-lg">
                                    <div className="bg-gray-50 px-4 py-2 border-b">
                                      <h4 className="font-medium">Extractable Files</h4>
                                    </div>
                                    <div className="max-h-64 overflow-y-auto">
                                      {scanResults.extractable_files
                                        .filter(file => file.extractable)
                                        .map((file, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 border-b last:border-b-0">
                                          <div className="flex items-center space-x-3">
                                            <FileText className="h-4 w-4 text-gray-400" />
                                            <div>
                                              <div className="font-medium text-sm">{file.name}</div>
                                              <div className="text-xs text-gray-500">{file.path}</div>
                                            </div>
                                          </div>
                                          <div className="text-right text-sm">
                                            <div className="text-gray-500">{formatFileSize(file.size)}</div>
                                            <Badge variant="outline" className="text-xs">
                                              {file.suggested_extractor}
                                            </Badge>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              ) : null}
                            </DialogContent>
                          </Dialog>
                          
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleUnmount(backup)}
                            className="flex items-center"
                          >
                            <HardDriveDownload className="h-4 w-4 mr-1" />
                            Unmount
                          </Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>
                
                {backup.mount_point && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="text-sm text-gray-600">
                      <strong>Mount Point:</strong> <code className="bg-white px-2 py-1 rounded">{backup.mount_point}</code>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No backups found</h3>
              <p className="text-gray-500 mb-4">
                {searchTerm ? 'No backups match your search criteria.' : 'No backups are available.'}
              </p>
              {searchTerm && (
                <Button variant="outline" onClick={() => setSearchTerm('')}>
                  Clear search
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

