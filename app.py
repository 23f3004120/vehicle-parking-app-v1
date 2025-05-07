from flask import Flask 
from controllers.views import views 
from model_defined import db, User, ParkingLot, ParkingSpot, Reservation

app = Flask(__name__)
app.config['SECRET_KEY'] = '23f3004120'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(views)

@app.before_first_request
def create_tables_and_admin():
    db.create_all()

    # create admin
    admin_email = 'admin@example.com'
    if not User.query.filter_by(email=admin_email).first():
        default_admin = User(
            email=admin_email,
            password='admin123', 
            name='Admin',
            is_admin=True
        )
        db.session.add(default_admin)
        db.session.commit()
        print("Default admin ({admin_email}) created.")
    else:
        print("Admin already exists.")
if __name__ == '__main__' :
    app.run(debug=True)
