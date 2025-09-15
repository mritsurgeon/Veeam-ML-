# Veeam ML Integration Platform

A comprehensive platform that integrates Veeam Backup & Replication with machine learning capabilities for intelligent backup management, predictive analytics, and automated optimization.

## 🚀 Features

- **Veeam API Integration**: Connect to Veeam Backup & Replication servers
- **Machine Learning Pipeline**: Automated ML job creation and execution
- **Data Extraction**: Extract data from mounted backup files
- **Predictive Analytics**: Backup success prediction and failure analysis
- **Modern Web Interface**: React-based dashboard with real-time monitoring
- **Comprehensive Testing**: Full test suite for both backend and frontend

## 🏗️ Architecture

### Backend (Python/Flask)
- **Flask API**: RESTful API endpoints for Veeam integration
- **SQLAlchemy Models**: Database models for backups, ML jobs, and data extraction
- **ML Services**: Scikit-learn based machine learning processors
- **Data Extraction**: Multiple extractors for different data types

### Frontend (React/Vite)
- **Modern React App**: Built with Vite for fast development
- **UI Components**: Comprehensive component library with shadcn/ui
- **Real-time Updates**: Live monitoring of backup and ML job status
- **Responsive Design**: Mobile-friendly interface

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- Veeam Backup & Replication server with API access
- Git

## 🛠️ Installation

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mritsurgeon/Veeam-ML-.git
   cd Veeam-ML-
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python src/main.py
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd veeam-ml-frontend
   ```

2. **Install dependencies**
   ```bash
   npm install --legacy-peer-deps
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## 🚀 Quick Start

1. **Start the backend server**
   ```bash
   # Terminal 1
   source venv/bin/activate
   python src/main.py
   ```

2. **Start the frontend server**
   ```bash
   # Terminal 2
   cd veeam-ml-frontend
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:5001

## 🔧 Configuration

### Veeam Server Configuration

1. Navigate to the Configuration Panel in the web interface
2. Enter your Veeam server details:
   - **Server URL**: `https://your-veeam-server:9419`
   - **Username**: Your Veeam username
   - **Password**: Your Veeam password

### SSL Certificate Handling

The platform handles self-signed certificates automatically. For production environments, ensure proper SSL certificates are configured.

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_veeam_routes.py
```

### Frontend Tests
```bash
cd veeam-ml-frontend

# Run tests
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage
```

## 📊 API Endpoints

### Veeam Integration
- `POST /api/veeam/config` - Configure Veeam server
- `GET /api/veeam/backups` - List available backups
- `POST /api/veeam/mount` - Mount backup for data access
- `POST /api/veeam/unmount` - Unmount backup

### ML Jobs
- `GET /api/veeam/ml-jobs` - List ML jobs
- `POST /api/veeam/ml-jobs` - Create new ML job
- `GET /api/veeam/ml-jobs/{id}` - Get ML job details
- `POST /api/veeam/ml-jobs/{id}/run` - Execute ML job

### Data Extraction
- `POST /api/veeam/extract` - Extract data from mounted backup
- `GET /api/veeam/extractions` - List data extractions

## 🔍 Usage Examples

### Creating an ML Job
```python
import requests

# Create ML job for backup analysis
response = requests.post('http://localhost:5001/api/veeam/ml-jobs', json={
    'name': 'Backup Success Prediction',
    'algorithm': 'random_forest',
    'parameters': {
        'n_estimators': 100,
        'max_depth': 10
    },
    'backup_id': 1
})
```

### Extracting Data
```python
# Extract data from mounted backup
response = requests.post('http://localhost:5001/api/veeam/extract', json={
    'backup_id': 1,
    'extractors': ['log_files', 'database', 'config_files'],
    'target_paths': ['/var/log', '/etc', '/var/lib/mysql']
})
```

## 📁 Project Structure

```
Veeam-ML-/
├── src/                          # Backend source code
│   ├── main.py                   # Flask application entry point
│   ├── models/                   # Database models
│   │   ├── user.py              # User model
│   │   └── veeam_backup.py      # Veeam and ML models
│   ├── routes/                   # API routes
│   │   ├── user.py              # User routes
│   │   └── veeam_routes.py      # Veeam integration routes
│   ├── services/                 # Business logic services
│   │   ├── veeam_api.py         # Veeam API client
│   │   ├── data_extractor.py    # Data extraction services
│   │   └── ml_processor.py      # ML processing services
│   └── database/                # SQLite database
├── veeam-ml-frontend/           # Frontend React application
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom React hooks
│   │   └── lib/                 # Utility functions
│   └── dist/                    # Built frontend assets
├── tests/                       # Backend tests
├── requirements.txt             # Python dependencies
└── README.md                   # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the [SOLUTION_DOCUMENTATION.md](SOLUTION_DOCUMENTATION.md) for detailed documentation

## 🔮 Roadmap

- [ ] Docker containerization
- [ ] Kubernetes deployment support
- [ ] Advanced ML algorithms integration
- [ ] Real-time backup monitoring
- [ ] Automated backup optimization
- [ ] Multi-tenant support

## 🙏 Acknowledgments

- Veeam Software for the Backup & Replication API
- React and Flask communities
- Open source contributors

---

**Made with ❤️ for intelligent backup management**
