from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
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
        return f'<User {self.employee_code}>'
