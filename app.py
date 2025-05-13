from flask import Flask,render_template,redirect,request,url_for,session,flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from controllers.database import db
from controllers.models import *

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

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST' :
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and password == user.password :
            login_user(user)
            if user.is_admin :
                return redirect(url_for('admin_dashboard'))
            else :
                return redirect(url_for('user_dashboard'))
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


@app.route('/user/dashboard',methods=['GET','POST'])
@login_required
def user_dashboard() :
    if current_user.is_admin:
        flash('Admins are not allowed to access the user dashboard.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user = current_user
    query = request.args.get('query')
    search_results = []
    search_location = ''
    
    if query:
        search_results = ParkingLot.query.filter(
            (ParkingLot.prime_location.ilike(f"%{query}%")) |
            (ParkingLot.pincode.ilike(f"%{query}%"))
        ).all()
        search_location = query

    reservations = Reservation.query.filter_by(user_id=user.id, leaving_time=None).all()
    
    return render_template(
        'user_dashboard.html',
        username=user.name,
        search_results=search_results,
        query=query,
        search_location=search_location,
        reservations=reservations
        )

@app.route('/admin/dashboard')
def admin_dashboard() :
    if not current_user.is_admin:
        flash('Access Denied: Admins only', 'danger')
        return redirect(url_for('login'))
    
    parking_lots = ParkingLot.query.all()

    return render_template('admin_dashboard.html',user=current_user,parking_lots=parking_lots)

@app.route('/logout')
@login_required
def logout() :
    logout_user()
    flash('You have been logged out','success')
    return redirect(url_for('login'))

@app.route('/add-lot', methods=['GET','POST'])
def add_parking_lot():
    if request.method == 'POST':
        location = request.form['prime_location']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price_per_hour'])
        spots = int(request.form['total_spots'])

        # Create parking lot
        new_lot = ParkingLot(
            prime_location=location,
            address=address,
            pincode=pincode,
            price_per_hour=price,
            max_spots=spots
        )
        db.session.add(new_lot)
        db.session.commit()

        # Create associated parking spots (all 'A' by default)
        parking_spots = [ParkingSpot(lot_id=new_lot.id, status='A') for x in range(spots)]
        db.session.add_all(parking_spots)
        db.session.commit()

        flash('New parking lot added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_lot.html')

@app.route('/edit-lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.prime_location = request.form['prime_location']
        lot.address = request.form['address']
        lot.pincode = request.form['pincode']
        lot.price_per_hour = request.form['price_per_hour']
        
        new_spots = int(request.form['total_spots'])
        old_spots = lot.max_spots
        lot.max_spots = new_spots

        db.session.commit()  # Commit here to update lot before changing spots

        # Update parking spots based on new total
        if new_spots > old_spots:
            # Add new spots
            for x in range(new_spots - old_spots):
                new_spot = ParkingSpot(lot_id=lot.id, status='A')
                db.session.add(new_spot)

        elif new_spots < old_spots:
            # Remove excess available spots
            available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').limit(old_spots - new_spots).all()
            for spot in available_spots:
                db.session.delete(spot)

        db.session.commit()
        flash('Parking lot updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)


@app.route('/delete-lot/<int:lot_id>', methods=['GET','POST','DELETE'])
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted successfully!', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/reserve/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def reserve_spot(lot_id):
    if current_user.is_admin:
        flash('Admins cannot reserve parking spots.', 'danger')
        return redirect(url_for('admin_dashboard'))

    lot = ParkingLot.query.get_or_404(lot_id)

    # Find the first available spot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

    if not available_spot:
        flash('No available spots in this parking lot.', 'danger')
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        print("Form data received:", request.form)
        vehicle_number = request.form.get('vehicle_number')

        # Create a reservation
        reservation = Reservation(
            spot_id=available_spot.id,
            user_id=current_user.id,
            vehicle_number=vehicle_number
        )
        db.session.add(reservation)

        # Update spot status
        available_spot.status = 'O'
        db.session.commit()

        flash('Parking spot reserved successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('reserve_form.html',username=current_user.name, user=current_user, lot=lot, spot=available_spot)





if __name__ == '__main__':
    app.run(debug=True)
