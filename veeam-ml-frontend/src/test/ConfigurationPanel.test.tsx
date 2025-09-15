import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import ConfigurationPanel from '../components/ConfigurationPanel'

// Mock the useVeeamAPI hook
const mockUseVeeamAPI = {
  config: {
    veeam_url: '',
    username: '',
    password: ''
  },
  isLoading: false,
  error: null,
  testConnection: vi.fn(),
  saveConfig: vi.fn()
}

vi.mock('../hooks/useVeeamAPI', () => ({
  useVeeamAPI: () => mockUseVeeamAPI
}))

const ConfigurationPanelWrapper = () => (
  <BrowserRouter>
    <ConfigurationPanel />
  </BrowserRouter>
)

describe('ConfigurationPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders configuration form', () => {
    render(<ConfigurationPanelWrapper />)
    expect(screen.getByText('Veeam Configuration')).toBeInTheDocument()
    expect(screen.getByLabelText('Veeam Server URL')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('has test connection button', () => {
    render(<ConfigurationPanelWrapper />)
    expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument()
  })

  it('has save configuration button', () => {
    render(<ConfigurationPanelWrapper />)
    expect(screen.getByRole('button', { name: /save configuration/i })).toBeInTheDocument()
  })

  it('handles form input changes', async () => {
    render(<ConfigurationPanelWrapper />)
    
    const urlInput = screen.getByLabelText('Veeam Server URL')
    const usernameInput = screen.getByLabelText('Username')
    const passwordInput = screen.getByLabelText('Password')
    
    fireEvent.change(urlInput, { target: { value: 'https://test-server:9419' } })
    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    fireEvent.change(passwordInput, { target: { value: 'testpass' } })
    
    expect(urlInput).toHaveValue('https://test-server:9419')
    expect(usernameInput).toHaveValue('testuser')
    expect(passwordInput).toHaveValue('testpass')
  })

  it('calls testConnection when test button is clicked', async () => {
    mockUseVeeamAPI.testConnection.mockResolvedValue({ success: true })
    
    render(<ConfigurationPanelWrapper />)
    
    const testButton = screen.getByRole('button', { name: /test connection/i })
    fireEvent.click(testButton)
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.testConnection).toHaveBeenCalled()
    })
  })

  it('calls saveConfig when save button is clicked', async () => {
    mockUseVeeamAPI.saveConfig.mockResolvedValue({ success: true })
    
    render(<ConfigurationPanelWrapper />)
    
    const saveButton = screen.getByRole('button', { name: /save configuration/i })
    fireEvent.click(saveButton)
    
    await waitFor(() => {
      expect(mockUseVeeamAPI.saveConfig).toHaveBeenCalled()
    })
  })

  it('shows loading state during operations', () => {
    mockUseVeeamAPI.isLoading = true
    render(<ConfigurationPanelWrapper />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('displays error messages', () => {
    mockUseVeeamAPI.error = 'Connection failed'
    render(<ConfigurationPanelWrapper />)
    expect(screen.getByText('Error: Connection failed')).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    render(<ConfigurationPanelWrapper />)
    
    const saveButton = screen.getByRole('button', { name: /save configuration/i })
    fireEvent.click(saveButton)
    
    await waitFor(() => {
      expect(screen.getByText('Please fill in all required fields')).toBeInTheDocument()
    })
  })
})
