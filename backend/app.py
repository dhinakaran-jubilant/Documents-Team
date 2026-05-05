"""
Project: Fin Report - Documents team
Author: Dhinakaran Sekar
Email: dhinakaran.s@jubilantenterprises.in
Date: 2026-04-30 18:41
Description: Main Backend Flask application for handling file uploads, PDF generation, and user authentication.
"""

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import os
import tempfile
import atexit
import shutil
import json
from utils.pdf_generator import process_excel_to_pdfs, create_zip_archive

app = Flask(__name__)
# Database Configuration (SQLite for DocumentsTeam)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///documents.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize database and seed admin user
with app.app_context():
    db.create_all()
    
    # Remove the old admin user if it exists
    old_admin = User.query.filter_by(employee_code='JC0033').first()
    if old_admin:
        db.session.delete(old_admin)
        db.session.commit()
        print("Removed old admin user: JC0033")

    # Seed the new default admin user
    admin_user = User.query.filter_by(employee_code='admin').first()
    if not admin_user:
        admin_user = User(
            employee_code='admin',
            password=generate_password_hash('Admin@123'),
            name='System Admin',
            role='admin',
            is_initial_password=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Seeded default admin user: admin / Admin@123")
    elif admin_user.is_initial_password:
        # Ensure password matches the requested default if still in initial state
        admin_user.password = generate_password_hash('Admin@123')
        db.session.commit()
        print("Updated existing admin user password to: Admin@123")

# Enable CORS for React frontend (default dev port 5173 for vite)
CORS(app, resources={r"/*": {"origins": "*", "expose_headers": ["X-Process-Time"]}})

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint for uploading Excel files and generating PDF reports.
    Returns a ZIP file containing the generated PDFs.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"error": "Only Excel files (.xlsx, .xls) are supported"}), 400

    temp_dir = tempfile.mkdtemp()
    
    import time
    start_time = time.time()
    try:
        # Process the excel file and get list of paths
        pdf_paths = process_excel_to_pdfs(file, temp_dir)
        
        if not pdf_paths:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return jsonify({"error": "No valid data found to generate reports"}), 400
            
        zip_path = os.path.join(temp_dir, "financial_reports.zip")
        create_zip_archive(pdf_paths, zip_path)
        
        duration = time.time() - start_time
        
        # Send the zip file back
        response = send_file(
            zip_path,
            as_attachment=True,
            download_name="financial_reports.zip",
            mimetype="application/zip"
        )
        response.headers['X-Process-Time'] = f"{duration:.2f}"
        return response
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

# --- Authentication Routes ---

@app.route('/api/login/', methods=['POST'])
def login():
    """
    Handles user login by verifying employee code and password.
    Returns user details including role and initial password status.
    """
    try:
        data = request.json
        emp_code = data.get('employee_code', '').strip()
        password = data.get('password', '')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if user:
            if check_password_hash(user.password, password):
                return jsonify({
                    'success': True,
                    'user': {
                        'employee_code': user.employee_code,
                        'name': user.name,
                        'role': user.role,
                        'is_initial_password': user.is_initial_password
                    }
                })
            else:
                print("Password mismatch")
        else:
            print("User not found in DB")
            
        return jsonify({'success': False, 'message': 'Invalid employee code or password'}), 401
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/users/initial-setup/', methods=['POST'])
def initial_setup():
    """
    Handles the first-time password change and security question setup for new users.
    """
    try:
        data = request.json
        emp_code = data.get('employee_code')
        new_password = data.get('new_password')
        question = data.get('q1')
        answer = data.get('a1')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
        user.password = generate_password_hash(new_password)
        user.is_initial_password = False
        user.security_question = question
        user.security_answer = generate_password_hash(answer.lower().strip())
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Setup completed successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/forgot-password/request/', methods=['POST'])
def forgot_password_request():
    """
    Retrieves the security question for a user who has forgotten their password.
    """
    try:
        data = request.json
        emp_code = data.get('employee_code')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if (user and user.security_question):
            return jsonify({'success': True, 'question': user.security_question, 'role': user.role})
        return jsonify({'success': False, 'message': 'User not found or security questions not set'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/forgot-password/reset/', methods=['POST'])
def forgot_password_reset():
    """
    Resets the user's password after verifying their security question answer.
    """
    try:
        data = request.json
        emp_code = data.get('employee_code')
        answer = data.get('answer', '').lower().strip()
        new_password = data.get('new_password')
        
        user = User.query.filter_by(employee_code=emp_code).first()
        if user and user.security_answer and check_password_hash(user.security_answer, answer):
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Password reset successful'})
        return jsonify({'success': False, 'message': 'Incorrect answer or user not found'}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=2000, ssl_context=('cert.pem', 'key.pem'))
