import { createContext, useContext, useState, useCallback } from 'react'

const VeeamAPIContext = createContext()

export const useVeeamAPI = () => {
  const context = useContext(VeeamAPIContext)
  if (!context) {
    throw new Error('useVeeamAPI must be used within a VeeamAPIProvider')
  }
  return context
}

export const VeeamAPIProvider = ({ children }) => {
  const [isConfigured, setIsConfigured] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const API_BASE_URL = '/api/veeam'

  const apiCall = useCallback(async (endpoint, options = {}) => {
    try {
      setError(null)
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      return await response.json()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [])

  const configureVeeam = useCallback(async (config) => {
    setIsLoading(true)
    try {
      await apiCall('/config', {
        method: 'POST',
        body: JSON.stringify(config),
      })
      setIsConfigured(true)
      return true
    } catch (err) {
      setIsConfigured(false)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [apiCall])

  const getBackups = useCallback(async (filters = {}) => {
    const params = new URLSearchParams(filters)
    return await apiCall(`/backups?${params}`)
  }, [apiCall])

  const mountBackup = useCallback(async (backupId) => {
    return await apiCall(`/backups/${backupId}/mount`, {
      method: 'POST',
    })
  }, [apiCall])

  const unmountBackup = useCallback(async (backupId) => {
    return await apiCall(`/backups/${backupId}/unmount`, {
      method: 'POST',
    })
  }, [apiCall])

  const scanBackupFiles = useCallback(async (backupId, directoryPath = '/') => {
    return await apiCall(`/backups/${backupId}/scan`, {
      method: 'POST',
      body: JSON.stringify({ directory_path: directoryPath }),
    })
  }, [apiCall])

  const createMLJob = useCallback(async (jobData) => {
    return await apiCall('/ml-jobs', {
      method: 'POST',
      body: JSON.stringify(jobData),
    })
  }, [apiCall])

  const executeMLJob = useCallback(async (jobId) => {
    return await apiCall(`/ml-jobs/${jobId}/execute`, {
      method: 'POST',
    })
  }, [apiCall])

  const getMLJobs = useCallback(async (filters = {}) => {
    const params = new URLSearchParams(filters)
    return await apiCall(`/ml-jobs?${params}`)
  }, [apiCall])

  const getMLJob = useCallback(async (jobId) => {
    return await apiCall(`/ml-jobs/${jobId}`)
  }, [apiCall])

  const deleteMLJob = useCallback(async (jobId) => {
    return await apiCall(`/ml-jobs/${jobId}`, {
      method: 'DELETE',
    })
  }, [apiCall])

  const checkHealth = useCallback(async () => {
    return await apiCall('/health')
  }, [apiCall])

  const value = {
    isConfigured,
    isLoading,
    error,
    setError,
    configureVeeam,
    getBackups,
    mountBackup,
    unmountBackup,
    scanBackupFiles,
    createMLJob,
    executeMLJob,
    getMLJobs,
    getMLJob,
    deleteMLJob,
    checkHealth,
  }

  return (
    <VeeamAPIContext.Provider value={value}>
      {children}
    </VeeamAPIContext.Provider>
  )
}

