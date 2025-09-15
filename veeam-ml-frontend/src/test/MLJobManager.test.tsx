import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import MLJobManager from '../components/MLJobManager'

// Mock the useVeeamAPI hook
const mockUseVeeamAPI = {
  mlJobs: [
    {
      id: 'job-1',
      name: 'Test Classification Job',
      algorithm: 'classification',
      status: 'completed',
      created: '2024-01-01T00:00:00Z',
      parameters: { n_estimators: 100 }
    },
    {
      id: 'job-2',
      name: 'Test Clustering Job',
      algorithm: 'clustering',
      status: 'running',
      created: '2024-01-02T00:00:00Z',
      parameters: { n_clusters: 5 }
    }
  ],
  backups: [
    {
      id: 'backup-1',
      name: 'Test Backup',
      size: 1024000,
      created: '2024-01-01T00:00:00Z',
      status: 'Success'
    }
  ],
  isLoading: false,
  error: null,
  createMLJob: vi.fn(),
  deleteMLJob: vi.fn(),
  fetchMLJobs: vi.fn(),
  fetchBackups: vi.fn()
}

vi.mock('../hooks/useVeeamAPI', () => ({
  useVeeamAPI: () => mockUseVeeamAPI
}))

const MLJobManagerWrapper = () => (
  <BrowserRouter>
    <MLJobManager />
  </BrowserRouter>
)

describe('MLJobManager Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders ML job manager title', () => {
    render(<MLJobManagerWrapper />)
    expect(screen.getByText('ML Job Manager')).toBeInTheDocument()
  })

  it('displays existing ML jobs', () => {
    render(<MLJobManagerWrapper />)
    expect(screen.getByText('Test Classification Job')).toBeInTheDocument()
    expect(screen.getByText('Test Clustering Job')).toBeInTheDocument()
  })

  it('shows job status badges', () => {
    render(<MLJobManagerWrapper />)
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('running')).toBeInTheDocument()
  })

  it('has create new job button', () => {
    render(<MLJobManagerWrapper />)
    expect(screen.getByRole('button', { name: /create new job/i })).toBeInTheDocument()
  })

  it('opens job creation form when create button is clicked', () => {
    render(<MLJobManagerWrapper />)
    
    const createButton = screen.getByRole('button', { name: /create new job/i })
    fireEvent.click(createButton)
    
    expect(screen.getByText('Create ML Job')).toBeInTheDocument()
    expect(screen.getByLabelText('Job Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Algorithm')).toBeInTheDocument()
  })

  it('has algorithm selection dropdown', () => {
    render(<MLJobManagerWrapper />)
    
    const createButton = screen.getByRole('button', { name: /create new job/i })
    fireEvent.click(createButton)
    
    const algorithmSelect = screen.getByLabelText('Algorithm')
    expect(algorithmSelect).toBeInTheDocument()
    
    // Check that algorithm options are available
    fireEvent.click(algorithmSelect)
    expect(screen.getByText('Classification')).toBeInTheDocument()
    expect(screen.getByText('Regression')).toBeInTheDocument()
    expect(screen.getByText('Clustering')).toBeInTheDocument()
  })

  it('has backup selection dropdown', () => {
    render(<MLJobManagerWrapper />)
    
    const createButton = screen.getByRole('button', { name: /create new job/i })
    fireEvent.click(createButton)
    
    const backupSelect = screen.getByLabelText('Backup')
    expect(backupSelect).toBeInTheDocument()
    
    fireEvent.click(backupSelect)
    expect(screen.getByText('Test Backup')).toBeInTheDocument()
  })

  it('submits job creation form', async () => {
    mockUseVeeamAPI.createMLJob.mockResolvedValue({ success: true, job_id: 'new-job-1' })
    
    render(<MLJobManagerWrapper />)
    
    const createButton = screen.getByRole('button', { name: /create new job/i })
    fireEvent.click(createButton)
    
    // Fill out the form
    const nameInput = screen.getByLabelText('Job Name')
    fireEvent.change(nameInput, { target: { value: 'New Test Job' } })
    
    const algorithmSelect = screen.getByLabelText('Algorithm')
    fireEvent.click(algorithmSelect)
    fireEvent.click(screen.getByText('Classification'))
    
    const submitButton = screen.getByRole('button', { name: /create job/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.createMLJob).toHaveBeenCalledWith({
        name: 'New Test Job',
        algorithm: 'classification',
        backup_id: 'backup-1',
        parameters: {}
      })
    })
  })

  it('has delete job buttons', () => {
    render(<MLJobManagerWrapper />)
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    expect(deleteButtons).toHaveLength(2) // One for each job
  })

  it('calls deleteMLJob when delete button is clicked', async () => {
    mockUseVeeamAPI.deleteMLJob.mockResolvedValue({ success: true })
    
    render(<MLJobManagerWrapper />)
    
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    fireEvent.click(deleteButtons[0])
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.deleteMLJob).toHaveBeenCalledWith('job-1')
    })
  })

  it('shows loading state', () => {
    mockUseVeeamAPI.isLoading = true
    render(<MLJobManagerWrapper />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays error messages', () => {
    mockUseVeeamAPI.error = 'Failed to load jobs'
    render(<MLJobManagerWrapper />)
    expect(screen.getByText('Error: Failed to load jobs')).toBeInTheDocument()
  })

  it('validates required fields in job creation', async () => {
    render(<MLJobManagerWrapper />)
    
    const createButton = screen.getByRole('button', { name: /create new job/i })
    fireEvent.click(createButton)
    
    const submitButton = screen.getByRole('button', { name: /create job/i })
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText('Please fill in all required fields')).toBeInTheDocument()
    })
  })
})
