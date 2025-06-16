from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from models.models import *
from sqlalchemy import func
import json
import plotly
import plotly.graph_objs as go

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard',methods=['GET','POST'])
@login_required
def user_dashboard() :
    if current_user.is_admin:
        flash('Admins are not allowed to access the user dashboard.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
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

@user_bp.route('/reserve/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def reserve_spot(lot_id):
    if current_user.is_admin:
        flash('Admins cannot reserve parking spots.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    lot = ParkingLot.query.get_or_404(lot_id)

    # Find the first available spot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()

    if not available_spot:
        flash('No available spots in this parking lot.', 'danger')
        return redirect(url_for('user.user_dashboard'))

    if request.method == 'POST':
        vehicle_number = request.form.get('vehicle_number').strip()

        # Check for an active reservation with the same vehicle number
        existing_reservation = Reservation.query.filter_by(
            vehicle_number=vehicle_number,
            leaving_time=None
        ).first()

        if existing_reservation:
            flash(f'Vehicle "{vehicle_number}" already has an active reservation.', 'danger')
            return render_template(
                'reserve_form.html',
                username=current_user.name,
                user=current_user,
                lot=lot,
                spot=available_spot
            )

        # Create new reservation
        reservation = Reservation(
            spot_id=available_spot.id,
            user_id=current_user.id,
            vehicle_number=vehicle_number
        )
        db.session.add(reservation)

        # Mark spot as occupied
        available_spot.status = 'O'
        db.session.commit()

        flash('Parking spot reserved successfully!', 'success')
        return redirect(url_for('user.user_dashboard'))

    return render_template(
        'reserve_form.html',
        username=current_user.name,
        user=current_user,
        lot=lot,
        spot=available_spot
    )


@user_bp.route('/release/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def release_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('user.user_dashboard'))

    if request.method == 'POST':
        reservation.leaving_time = datetime.now()
        reservation.calculate_total_cost(reservation.spot.lot.price_per_hour)
        reservation.spot.status = 'A'  
        db.session.commit()
        flash("Parking spot released successfully.", "success")
        return redirect(url_for('user.user_dashboard'))

    now = datetime.now()
    temp_leaving_time = now
    temp_duration = temp_leaving_time - reservation.parking_time
    temp_hours = temp_duration.total_seconds() / 3600
    estimated_cost = round(temp_hours * reservation.spot.lot.price_per_hour, 2)

    return render_template('release_form.html',username=current_user.name, reservation=reservation, now=now, estimated_cost=estimated_cost)

@user_bp.route('/editprofile', methods=['GET', 'POST'])
@login_required
def user_editprofile():
    user = current_user

    if request.method == 'POST':
        user.name = request.form['name']
        user.password = request.form['password'] 
        user.address = request.form['address']
        user.pincode = request.form['pincode']
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('user.user_dashboard'))

    return render_template('user_editprofile.html',username=current_user.name, user=user)

@user_bp.route('/user_summary')
def user_summary():
    user = current_user
    # Query reservation count per lot used by this user
    results = (
        db.session.query(ParkingSpot.lot_id, func.count(Reservation.id))
        .join(ParkingSpot)
        .filter(Reservation.user_id == current_user.id)
        .group_by(ParkingSpot.lot_id)
        .all()
    )

    # Format data for chart
    x = [f"Lot {lot_id}" for lot_id, i in results]
    y = [count for j, count in results]

    fig = go.Figure([go.Bar(x=x, y=y, marker_color='green')])
    fig.update_layout(xaxis_title="Parking Lot",
                      yaxis_title="Times Used")

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('user_summary.html',username=user.name, graphJSON=graphJSON)
