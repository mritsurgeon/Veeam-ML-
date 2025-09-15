import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import BackupManager from '../components/BackupManager'

// Mock the useVeeamAPI hook
const mockUseVeeamAPI = {
  backups: [
    {
      id: 'backup-1',
      name: 'Test Backup 1',
      size: 1024000,
      created: '2024-01-01T00:00:00Z',
      status: 'Success',
      repository: 'Test Repository'
    },
    {
      id: 'backup-2',
      name: 'Test Backup 2',
      size: 2048000,
      created: '2024-01-02T00:00:00Z',
      status: 'Success',
      repository: 'Test Repository'
    }
  ],
  mountedBackups: ['backup-1'],
  isLoading: false,
  error: null,
  mountBackup: vi.fn(),
  unmountBackup: vi.fn(),
  fetchBackups: vi.fn()
}

vi.mock('../hooks/useVeeamAPI', () => ({
  useVeeamAPI: () => mockUseVeeamAPI
}))

const BackupManagerWrapper = () => (
  <BrowserRouter>
    <BackupManager />
  </BrowserRouter>
)

describe('BackupManager Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders backup manager title', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Backup Manager')).toBeInTheDocument()
  })

  it('displays backup list', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Test Backup 1')).toBeInTheDocument()
    expect(screen.getByText('Test Backup 2')).toBeInTheDocument()
  })

  it('shows backup details', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Test Repository')).toBeInTheDocument()
    expect(screen.getByText('1.0 MB')).toBeInTheDocument() // Formatted size
    expect(screen.getByText('2.0 MB')).toBeInTheDocument()
  })

  it('shows mount status', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Mounted')).toBeInTheDocument()
    expect(screen.getByText('Not Mounted')).toBeInTheDocument()
  })

  it('has mount buttons for unmounted backups', () => {
    render(<BackupManagerWrapper />)
    const mountButtons = screen.getAllByRole('button', { name: /mount/i })
    expect(mountButtons).toHaveLength(1) // Only for backup-2
  })

  it('has unmount buttons for mounted backups', () => {
    render(<BackupManagerWrapper />)
    const unmountButtons = screen.getAllByRole('button', { name: /unmount/i })
    expect(unmountButtons).toHaveLength(1) // Only for backup-1
  })

  it('calls mountBackup when mount button is clicked', async () => {
    mockUseVeeamAPI.mountBackup.mockResolvedValue({ success: true, mount_path: '/tmp/mount-123' })
    
    render(<BackupManagerWrapper />)
    
    const mountButton = screen.getByRole('button', { name: /mount/i })
    fireEvent.click(mountButton)
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.mountBackup).toHaveBeenCalledWith('backup-2')
    })
  })

  it('calls unmountBackup when unmount button is clicked', async () => {
    mockUseVeeamAPI.unmountBackup.mockResolvedValue({ success: true })
    
    render(<BackupManagerWrapper />)
    
    const unmountButton = screen.getByRole('button', { name: /unmount/i })
    fireEvent.click(unmountButton)
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.unmountBackup).toHaveBeenCalledWith('backup-1')
    })
  })

  it('shows loading state', () => {
    mockUseVeeamAPI.isLoading = true
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays error messages', () => {
    mockUseVeeamAPI.error = 'Failed to load backups'
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Error: Failed to load backups')).toBeInTheDocument()
  })

  it('shows success message after mounting', async () => {
    mockUseVeeamAPI.mountBackup.mockResolvedValue({ success: true, mount_path: '/tmp/mount-123' })
    
    render(<BackupManagerWrapper />)
    
    const mountButton = screen.getByRole('button', { name: /mount/i })
    fireEvent.click(mountButton)
    
    await waitFor(() => {
      expect(screen.getByText('Backup mounted successfully')).toBeInTheDocument()
    })
  })

  it('shows success message after unmounting', async () => {
    mockUseVeeamAPI.unmountBackup.mockResolvedValue({ success: true })
    
    render(<BackupManagerWrapper />)
    
    const unmountButton = screen.getByRole('button', { name: /unmount/i })
    fireEvent.click(unmountButton)
    
    await waitFor(() => {
      expect(screen.getByText('Backup unmounted successfully')).toBeInTheDocument()
    })
  })

  it('handles mount errors', async () => {
    mockUseVeeamAPI.mountBackup.mockResolvedValue({ success: false, error: 'Mount failed' })
    
    render(<BackupManagerWrapper />)
    
    const mountButton = screen.getByRole('button', { name: /mount/i })
    fireEvent.click(mountButton)
    
    await waitFor(() => {
      expect(screen.getByText('Failed to mount backup: Mount failed')).toBeInTheDocument()
    })
  })

  it('handles unmount errors', async () => {
    mockUseVeeamAPI.unmountBackup.mockResolvedValue({ success: false, error: 'Unmount failed' })
    
    render(<BackupManagerWrapper />)
    
    const unmountButton = screen.getByRole('button', { name: /unmount/i })
    fireEvent.click(unmountButton)
    
    await waitFor(() => {
      expect(screen.getByText('Failed to unmount backup: Unmount failed')).toBeInTheDocument()
    })
  })

  it('formats file sizes correctly', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('1.0 MB')).toBeInTheDocument()
    expect(screen.getByText('2.0 MB')).toBeInTheDocument()
  })

  it('formats dates correctly', () => {
    render(<BackupManagerWrapper />)
    expect(screen.getByText('Jan 1, 2024')).toBeInTheDocument()
    expect(screen.getByText('Jan 2, 2024')).toBeInTheDocument()
  })
})
