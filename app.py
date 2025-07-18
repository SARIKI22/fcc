from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site_finance.db'
app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'fcc_sariki2000@yahoo.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'  # Replace with actual app password

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    name = db.Column(db.String(150))
    password = db.Column(db.String(150))
    role = db.Column(db.String(50))

class ExpenseRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site = db.Column(db.String(100))
    category = db.Column(db.String(100))
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    status_pm = db.Column(db.String(50), default='Pending')
    status_finance = db.Column(db.String(50), default='Pending')
    submitted_by = db.Column(db.String(150))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    expenses = ExpenseRequest.query.all()
    return render_template('index.html', expenses=expenses, user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/submit', methods=['POST'])
@login_required
def submit():
    if current_user.role != 'Site Engineer':
        flash("Only Site Engineers can submit requests.")
        return redirect(url_for('index'))
    new_expense = ExpenseRequest(
        site=request.form['site'],
        category=request.form['category'],
        description=request.form['description'],
        amount=float(request.form['amount']),
        submitted_by=current_user.email
    )
    db.session.add(new_expense)
    db.session.commit()

    pm_user = User.query.filter_by(role='Project Manager').first()
    if pm_user:
        msg = Message("New Expense Request Submitted",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[pm_user.email])
        msg.body = f"A new request has been submitted by {current_user.name}"
        mail.send(msg)

    return redirect(url_for('index'))

@app.route('/approve_pm/<int:id>')
@login_required
def approve_pm(id):
    if current_user.role != 'Project Manager':
        flash("Only Project Managers can approve here.")
        return redirect(url_for('index'))
    expense = ExpenseRequest.query.get_or_404(id)
    expense.status_pm = 'Approved'
    db.session.commit()

    finance_user = User.query.filter_by(role='Finance Officer').first()
    if finance_user:
        msg = Message("Request Needs Finance Approval",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[finance_user.email])
        msg.body = f"Request ID {expense.id} has been approved by PM and awaits your review."
        mail.send(msg)

    return redirect(url_for('index'))

@app.route('/approve_finance/<int:id>')
@login_required
def approve_finance(id):
    if current_user.role != 'Finance Officer':
        flash("Only Finance Officers can approve here.")
        return redirect(url_for('index'))
    expense = ExpenseRequest.query.get_or_404(id)
    if expense.status_pm == 'Approved':
        expense.status_finance = 'Approved'
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
