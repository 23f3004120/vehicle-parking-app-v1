
from flask import Blueprint, render_template,request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.models import *

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
def admin_dashboard() :
    if not current_user.is_admin:
        flash('Access Denied: Admins only', 'danger')
        return redirect(url_for('login'))
    
    parking_lots = ParkingLot.query.all()

    return render_template('admin_dashboard.html',user=current_user,parking_lots=parking_lots)

@admin_bp.route('/add-lot', methods=['GET','POST'])
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
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('add_lot.html')

@admin_bp.route('/edit-lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot.prime_location = request.form['prime_location']
        lot.address = request.form['address']
        lot.pincode = request.form['pincode']
        lot.price_per_hour = request.form['price_per_hour']
        
        new_spots = int(request.form['total_spots'])
        old_spots = len(lot.spots)
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
        return redirect(url_for('admin.admin_dashboard'))

    return render_template('edit_lot.html', lot=lot)


@admin_bp.route('/delete-lot/<int:lot_id>', methods=['GET', 'POST', 'DELETE'])
def delete_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # Check for any occupied spots
    if any(spot.status == 'O' for spot in lot.spots):
        flash('Occupied parking lots cannot be deleted.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(lot)
    db.session.commit()
    
    flash('Parking lot deleted successfully!', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/users')
def view_users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_users.html', users=users)


@admin_bp.route('/spot/<int:spot_id>')
def view_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'A':
        return render_template('available_spot.html', spot=spot)
    else:
        reservation = Reservation.query.filter_by(spot_id=spot_id, leaving_time=None).first()
        return render_template('occupied_spot.html', spot=spot, reservation=reservation)
    
@admin_bp.route('/delete-spot/<int:spot_id>', methods=['POST','DELETE'])
def delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status == 'O':
        flash('Cannot delete an occupied spot.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    db.session.delete(spot)
    db.session.commit()
    flash(f'Spot {spot_id} deleted successfully.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/search')
def search():
    search_type = request.args.get('type')
    query = request.args.get('query')

    if not search_type or not query:
        # No search performed yet, just show the form
        return render_template('search_results.html')

    if search_type == 'user':
        user = User.query.filter_by(id=query).first()
        return render_template('search_results.html', user=user)

    elif search_type == 'lot':
        parking_lots = ParkingLot.query.filter(
            ParkingLot.prime_location.ilike(f"%{query}%")
        ).all()
        return render_template('search_results.html', parking_lots=parking_lots)

    else:
        flash("Invalid search type", "warning")
        return redirect(url_for('admin.admin_dashboard'))




