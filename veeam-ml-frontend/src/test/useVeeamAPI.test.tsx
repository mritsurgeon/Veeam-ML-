import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import useVeeamAPI from '../hooks/useVeeamAPI'

// Mock fetch globally
global.fetch = vi.fn()

describe('useVeeamAPI Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockClear()
  })

  it('initializes with default state', () => {
    const { result } = renderHook(() => useVeeamAPI())
    
    expect(result.current.backups).toEqual([])
    expect(result.current.mlJobs).toEqual([])
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('fetches backups successfully', async () => {
    const mockBackups = [
      {
        id: 'backup-1',
        name: 'Test Backup',
        size: 1024000,
        created: '2024-01-01T00:00:00Z',
        status: 'Success'
      }
    ]

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ backups: mockBackups })
    })

    const { result } = renderHook(() => useVeeamAPI())

    await act(async () => {
      await result.current.fetchBackups()
    })

    expect(result.current.backups).toEqual(mockBackups)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('handles backup fetch errors', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useVeeamAPI())

    await act(async () => {
      await result.current.fetchBackups()
    })

    expect(result.current.backups).toEqual([])
    expect(result.current.error).toBe('Network error')
    expect(result.current.isLoading).toBe(false)
  })

  it('fetches ML jobs successfully', async () => {
    const mockJobs = [
      {
        id: 'job-1',
        name: 'Test Job',
        algorithm: 'classification',
        status: 'completed',
        created: '2024-01-01T00:00:00Z'
      }
    ]

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ jobs: mockJobs })
    })

    const { result } = renderHook(() => useVeeamAPI())

    await act(async () => {
      await result.current.fetchMLJobs()
    })

    expect(result.current.mlJobs).toEqual(mockJobs)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('creates ML job successfully', async () => {
    const jobData = {
      name: 'New Job',
      algorithm: 'classification',
      backup_id: 'backup-1',
      parameters: { n_estimators: 100 }
    }

    const mockResponse = {
      success: true,
      job_id: 'new-job-1'
    }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.createMLJob(jobData)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith('/api/veeam/ml-jobs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(jobData)
    })
  })

  it('deletes ML job successfully', async () => {
    const jobId = 'job-1'
    const mockResponse = { success: true }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.deleteMLJob(jobId)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith(`/api/veeam/ml-jobs/${jobId}`, {
      method: 'DELETE'
    })
  })

  it('mounts backup successfully', async () => {
    const backupId = 'backup-1'
    const mockResponse = {
      success: true,
      mount_path: '/tmp/mount-123'
    }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.mountBackup(backupId)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith(`/api/veeam/backups/${backupId}/mount`, {
      method: 'POST'
    })
  })

  it('unmounts backup successfully', async () => {
    const backupId = 'backup-1'
    const mockResponse = { success: true }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.unmountBackup(backupId)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith(`/api/veeam/backups/${backupId}/unmount`, {
      method: 'POST'
    })
  })

  it('tests connection successfully', async () => {
    const configData = {
      veeam_url: 'https://test-server:9419',
      username: 'testuser',
      password: 'testpass'
    }

    const mockResponse = { success: true }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.testConnection(configData)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith('/api/veeam/configure', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(configData)
    })
  })

  it('saves configuration successfully', async () => {
    const configData = {
      veeam_url: 'https://test-server:9419',
      username: 'testuser',
      password: 'testpass'
    }

    const mockResponse = { success: true }

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    })

    const { result } = renderHook(() => useVeeamAPI())

    let response
    await act(async () => {
      response = await result.current.saveConfig(configData)
    })

    expect(response).toEqual(mockResponse)
    expect(global.fetch).toHaveBeenCalledWith('/api/veeam/configure', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(configData)
    })
  })

  it('handles HTTP errors', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server error' })
    })

    const { result } = renderHook(() => useVeeamAPI())

    await act(async () => {
      await result.current.fetchBackups()
    })

    expect(result.current.error).toBe('Server error')
  })

  it('sets loading state during operations', async () => {
    let resolvePromise
    const promise = new Promise(resolve => {
      resolvePromise = resolve
    })

    global.fetch.mockReturnValueOnce(promise)

    const { result } = renderHook(() => useVeeamAPI())

    act(() => {
      result.current.fetchBackups()
    })

    expect(result.current.isLoading).toBe(true)

    await act(async () => {
      resolvePromise({
        ok: true,
        json: async () => ({ backups: [] })
      })
    })

    expect(result.current.isLoading).toBe(false)
  })
})
