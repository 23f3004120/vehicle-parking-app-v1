from flask import Flask,render_template,redirect,request,url_for,session,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models.database import db
from models.models import *
from controllers import register_controllers
from datetime import datetime 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'very_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

#  User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

    if not User.query.filter_by(email='admin@gmail.com').first() :
        admin_user = User(
            email='admin@gmail.com',
            password='23f3004120',
            name='Admin',
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

register_controllers(app)

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST' :
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and password == user.password :
            login_user(user)
            if user.is_admin :
                return redirect(url_for('admin.admin_dashboard'))
            else :
                return redirect(url_for('user.user_dashboard'))
        else :
            flash('Invalid email or password', 'warning')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register',methods=['GET','POST'])
def register() :
    if request.method == 'POST' :
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user :
            flash('Email already registered', 'warning')
            return redirect(url_for('register'))
        
        new_user = User(
            email=email,
            password=password,
            name=name,
            address=address,
            pincode=pincode 
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Registration Successful! Please login', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout() :
    logout_user()
    flash('You have been logged out','success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
