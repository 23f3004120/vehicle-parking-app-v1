from models.database import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin,db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(60), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(60), nullable=False)
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    is_admin = db.Column(db.Boolean, default=False)

    reservations = db.relationship('Reservation', backref='user', lazy=True)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id = db.Column(db.Integer, primary_key=True)
    prime_location = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)

    spots = db.relationship('ParkingSpot', backref='lot', cascade='all, delete-orphan', lazy=True)

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), default='A')

    reservations = db.relationship('Reservation', backref='spot', cascade='all, delete-orphan', lazy=True)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vehicle_number = db.Column(db.String(20), nullable=False)
    parking_time = db.Column(db.DateTime, default=datetime.now)
    leaving_time = db.Column(db.DateTime, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)

    def calculate_total_cost(self, hour_rate):
        if self.leaving_time:
            duration = self.leaving_time - self.parking_time
            hours = duration.total_seconds() / 3600
            self.total_cost = round(hours * hour_rate, 2)
        else:
            self.total_cost = None
