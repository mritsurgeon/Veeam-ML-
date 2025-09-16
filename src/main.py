import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from datetime import datetime
from src.models.veeam_backup import db, VeeamBackup, MLJob, DataExtraction
from src.routes.user import user_bp
from src.routes.veeam_routes import veeam_bp
from src.routes.extraction_routes import extraction_bp, set_veeam_api
from flask_cors import CORS

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(veeam_bp, url_prefix='/api/veeam')
app.register_blueprint(extraction_bp, url_prefix='/api/extraction')

# uncomment if you need to use database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()
    
    # Initialize extraction job models (use same db instance)
    from src.models.extraction_job import create_default_templates
    create_default_templates()
    
    # Set up Veeam API for extraction service
    from src.services.veeam_api import VeeamDataIntegrationAPI
    veeam_api = VeeamDataIntegrationAPI(
        base_url="https://172.21.234.6:9419",
        username="administrator", 
        password="Veeam123",
        verify_ssl=False
    )
    set_veeam_api(veeam_api)
    
    # Perform automatic state reconciliation on startup
    try:
        print("Performing automatic state reconciliation on startup...")
        reconciliation_result = veeam_api.reconcile_mount_state()
        
        # Update database backup statuses based on reconciled state
        for session_id, session_info in veeam_api.mount_sessions.items():
            # Find backup in database by backup_id
            backup = VeeamBackup.query.filter_by(backup_id=session_info['backup_id']).first()
            if backup:
                if session_info['state'] == 'Working':
                    backup.status = 'mounted'
                    backup.mount_point = session_info.get('mount_point', session_id)
                else:
                    backup.status = 'available'
                    backup.mount_point = None
                backup.updated_at = datetime.utcnow()
        
        # Mark all backups as 'available' if they're not in active sessions
        active_backup_ids = {session_info['backup_id'] for session_info in veeam_api.mount_sessions.values()}
        stale_backups = VeeamBackup.query.filter(
            VeeamBackup.status == 'mounted',
            ~VeeamBackup.backup_id.in_(active_backup_ids)
        ).all()
        
        for backup in stale_backups:
            print(f"Clearing stale mount status for backup {backup.backup_id}")
            backup.status = 'available'
            backup.mount_point = None
            backup.updated_at = datetime.utcnow()
        
        db.session.commit()
        print(f"State reconciliation completed: {len(reconciliation_result.get('orphaned_sessions', []))} orphaned sessions removed, {len(stale_backups)} stale backups cleared")
        
    except Exception as e:
        print(f"Warning: State reconciliation failed on startup: {str(e)}")
        # Don't fail startup if reconciliation fails

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
