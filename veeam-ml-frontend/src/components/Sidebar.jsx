import { Link, useLocation } from 'react-router-dom'
import { 
  BarChart3, 
  Database, 
  Brain, 
  Settings, 
  Menu,
  ChevronLeft,
  Activity,
  FileText
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: BarChart3 },
  { name: 'Backups', href: '/backups', icon: Database },
  { name: 'ML Jobs', href: '/ml-jobs', icon: Brain },
  { name: 'Extraction Jobs', href: '/extraction-jobs', icon: FileText },
  { name: 'Configuration', href: '/configuration', icon: Settings },
]

export const Sidebar = ({ isOpen, onToggle }) => {
  const location = useLocation()

  return (
    <div className={cn(
      "fixed inset-y-0 left-0 z-50 bg-white border-r border-gray-200 transition-all duration-300",
      isOpen ? "w-64" : "w-16"
    )}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          {isOpen && (
            <div className="flex items-center space-x-2">
              <Activity className="h-8 w-8 text-blue-600" />
              <span className="text-lg font-semibold text-gray-900">Veeam ML</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="p-2"
          >
            {isOpen ? <ChevronLeft className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            const Icon = item.icon

            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  "flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )}
              >
                <Icon className={cn("h-5 w-5", isOpen ? "mr-3" : "mx-auto")} />
                {isOpen && <span>{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200">
          <div className={cn(
            "text-xs text-gray-500",
            isOpen ? "text-center" : "hidden"
          )}>
            Veeam ML Integration v1.0
          </div>
        </div>
      </div>
    </div>
  )
}

