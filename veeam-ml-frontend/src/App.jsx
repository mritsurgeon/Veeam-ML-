import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { Sidebar } from '@/components/Sidebar'
import { Dashboard } from '@/components/Dashboard'
import { BackupManager } from '@/components/BackupManager'
import { MLJobManager } from '@/components/MLJobManager'
import { ConfigurationPanel } from '@/components/ConfigurationPanel'
import ExtractionJobManager from '@/components/ExtractionJobManager'
import { VeeamAPIProvider } from '@/hooks/useVeeamAPI'
import './App.css'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <VeeamAPIProvider>
      <Router>
        <div className="flex h-screen bg-gray-50">
          <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          
          <div className={`flex-1 flex flex-col transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-16'}`}>
            <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
              <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">
                  Veeam ML Integration Platform
                </h1>
                <div className="flex items-center space-x-4">
                  <div className="text-sm text-gray-500">
                    Machine Learning Analytics for Backup Data
                  </div>
                </div>
              </div>
            </header>
            
            <main className="flex-1 overflow-auto p-6">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/backups" element={<BackupManager />} />
                <Route path="/ml-jobs" element={<MLJobManager />} />
                <Route path="/extraction-jobs" element={<ExtractionJobManager />} />
                <Route path="/configuration" element={<ConfigurationPanel />} />
              </Routes>
            </main>
          </div>
          
          <Toaster />
        </div>
      </Router>
    </VeeamAPIProvider>
  )
}

export default App

