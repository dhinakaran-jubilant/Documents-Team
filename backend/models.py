"""
Project: Fin Report - Documents team
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
    email = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user')
    accessed_menus = db.Column(db.String(255), default='fin-report,documat')
    is_initial_password = db.Column(db.Boolean, default=True)
    security_question = db.Column(db.String(255))
    security_answer = db.Column(db.String(255))
    
    def __repr__(self):
        """Returns a string representation of the User object."""
        return f'<User {self.employee_code}>'


class CompanyAddress(db.Model):
    """
    CompanyAddress model storing lender/company name, PAN number, and registered address.
    Seeded from company_address_data.xlsx on application startup.
    """
    __tablename__ = 'company_addresses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    pan_number = db.Column(db.String(10))
    address = db.Column(db.Text)

    def __repr__(self):
        """Returns a string representation of the CompanyAddress object."""
        return f'<CompanyAddress {self.name}>'

