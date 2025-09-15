import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Dashboard from '../components/Dashboard'

// Mock the useVeeamAPI hook
const mockUseVeeamAPI = {
  backups: [
    {
      id: 'backup-1',
      name: 'Test Backup',
      size: 1024000,
      created: '2024-01-01T00:00:00Z',
      status: 'Success'
    }
  ],
  mlJobs: [
    {
      id: 'job-1',
      name: 'Test ML Job',
      algorithm: 'classification',
      status: 'completed',
      created: '2024-01-01T00:00:00Z'
    }
  ],
  isLoading: false,
  error: null,
  fetchBackups: vi.fn(),
  fetchMLJobs: vi.fn(),
  createMLJob: vi.fn(),
  deleteMLJob: vi.fn()
}

vi.mock('../hooks/useVeeamAPI', () => ({
  useVeeamAPI: () => mockUseVeeamAPI
}))

const DashboardWrapper = () => (
  <BrowserRouter>
    <Dashboard />
  </BrowserRouter>
)

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard title', () => {
    render(<DashboardWrapper />)
    expect(screen.getByText('Veeam ML Integration Dashboard')).toBeInTheDocument()
  })

  it('displays backup statistics', () => {
    render(<DashboardWrapper />)
    expect(screen.getByText('Total Backups')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument() // Should show count of 1 backup
  })

  it('displays ML job statistics', () => {
    render(<DashboardWrapper />)
    expect(screen.getByText('ML Jobs')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument() // Should show count of 1 job
  })

  it('shows recent backups section', () => {
    render(<DashboardWrapper />)
    expect(screen.getByText('Recent Backups')).toBeInTheDocument()
    expect(screen.getByText('Test Backup')).toBeInTheDocument()
  })

  it('shows recent ML jobs section', () => {
    render(<DashboardWrapper />)
    expect(screen.getByText('Recent ML Jobs')).toBeInTheDocument()
    expect(screen.getByText('Test ML Job')).toBeInTheDocument()
  })

  it('handles loading state', () => {
    mockUseVeeamAPI.isLoading = true
    render(<DashboardWrapper />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('handles error state', () => {
    mockUseVeeamAPI.error = 'Test error message'
    render(<DashboardWrapper />)
    expect(screen.getByText('Error: Test error message')).toBeInTheDocument()
  })

  it('calls fetchBackups and fetchMLJobs on mount', () => {
    render(<DashboardWrapper />)
    expect(mockUseVeeamAPI.fetchBackups).toHaveBeenCalled()
    expect(mockUseVeeamAPI.fetchMLJobs).toHaveBeenCalled()
  })
})
