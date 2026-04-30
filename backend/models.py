"""
Project: Documents Team
Author: Dhinakaran Sekar
Email: dhinakaran.s@jubilantenterprises.in
Date: 2026-04-30 18:41
Description: Database models for the Documents Team application.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """
    User model representing a staff member or administrator.
    Stores authentication details, role, and security question for password recovery.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')
    is_initial_password = db.Column(db.Boolean, default=True)
    security_question = db.Column(db.String(255))
    security_answer = db.Column(db.String(255))
    
    def __repr__(self):
        """Returns a string representation of the User object."""
        return f'<User {self.employee_code}>'
