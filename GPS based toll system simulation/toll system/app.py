from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_wtf.csrf import CSRFProtect
from flask import make_response
import sqlite3
import random
import csv
from werkzeug.security import generate_password_hash, check_password_hash
import math
import os
import time
from threading import Thread
import logging
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'cbc9d3dadc84ae82b9670bf1148beda7' 
csrf = CSRFProtect(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Vehicle simulation tracker
vehicle_simulations = {}

# Toll and fine rates
vehicle_tolls = {
    "Cars and Jeeps": 3.37,
    "Minibuses and Tempos": 5.21,
    "Two-Axle Trucks": 7.21,
    "Buses": 9.89,
    "Three-Axle Trucks": 17.16,
    "Multi-Axle Trucks and Machinery Vehicles": 22.79
}

fine_rates = {
    "Cars and Jeeps": 500,
    "Minibuses and Tempos": 1000,
    "Two-Axle Trucks": 1500,
    "Buses": 2000,
    "Three-Axle Trucks": 2500,
    "Multi-Axle Trucks and Machinery Vehicles": 3000
}

# Helper Functions
def calculate_toll(vehicle_type, distance_km):
    return max(vehicle_tolls.get(vehicle_type, 0) * distance_km, 10)

def calculate_fine(vehicle_type):
    return fine_rates.get(vehicle_type, 0)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_db_connection():
    try:
        conn = sqlite3.connect('vehicle.db')
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def load_toll_plazas():
    csv_path = r"D:\GPS based toll system simulation\mum pune shapefiles\toll_plazas.csv"
    try:
        if not os.path.exists(csv_path):
            logger.error(f"Toll plazas file not found at: {csv_path}")
            raise FileNotFoundError(f"Toll plazas CSV file not found at {csv_path}")
        
        toll_plazas = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    toll_plazas.append({
                        'name': row['Name'].strip(),
                        'latitude': float(row['Latitude']),
                        'longitude': float(row['Longitude'])
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row in toll plazas: {row}. Error: {str(e)}")
                    continue
        
        if not toll_plazas:
            raise ValueError("No valid toll plazas found in the CSV file")
            
        return toll_plazas
        
    except Exception as e:
        logger.error(f"Error loading toll plazas: {str(e)}")
        return [
            {'name': 'Khalapur Toll Plaza', 'latitude': 18.79, 'longitude': 73.2816},
            {'name': 'Talegaon Toll Plaza', 'latitude': 18.735, 'longitude': 73.675},
            {'name': 'Urse Toll Plaza', 'latitude': 18.72, 'longitude': 73.62}
        ]

def load_route_coordinates():
    csv_path = r"D:\GPS based toll system simulation\mum pune shapefiles\route.csv"
    route_coords = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    route_coords.append({
                        'latitude': float(row['Latitude']),
                        'longitude': float(row['Longitude'])
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row in route coordinates: {row}. Error: {str(e)}")
                    continue
        
        if not route_coords:
            raise ValueError("No valid coordinates found in route CSV")
            
        return route_coords
        
    except Exception as e:
        logger.error(f"Error loading route coordinates: {str(e)}")
        return None

def find_closest_point_idx(route_coords, lat, lng):
    closest_idx = 0
    min_distance = float('inf')
    
    for i, point in enumerate(route_coords):
        distance = haversine(lat, lng, point['latitude'], point['longitude'])
        if distance < min_distance:
            min_distance = distance
            closest_idx = i
            
    return closest_idx

def save_completed_trip(vehicle_id, user_id, vehicle_type, start_point, end_plaza, distance, toll, fine):
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO transactions (user_id, vehicle_id, vehicle_type, distance, toll, fine, 
            start_longitude, start_latitude, end_longitude, end_latitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, vehicle_id, vehicle_type, distance, toll, fine,
            start_point['longitude'], start_point['latitude'],
            end_plaza['longitude'], end_plaza['latitude'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Database error saving trip: {str(e)}")
        raise
    finally:
        conn.close()

def save_route_to_db(vehicle_id, route_coords):
    """Store the route coordinates in database"""
    try:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO simulation_routes (vehicle_id, route_coordinates)
            VALUES (?, ?)
        ''', (vehicle_id, json.dumps(route_coords)))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving route to DB: {str(e)}")
    finally:
        conn.close()

def simulate_straight_line_progress(vehicle_id, user_id, vehicle_type, start_point, end_plaza):
    try:
        total_distance = haversine(start_point['latitude'], start_point['longitude'],
                                 end_plaza['latitude'], end_plaza['longitude'])
        steps = 20
        current_step = 0
        
        lat_step = (end_plaza['latitude'] - start_point['latitude']) / steps
        lon_step = (end_plaza['longitude'] - start_point['longitude']) / steps
        
        while current_step <= steps:
            current_lat = start_point['latitude'] + (lat_step * current_step)
            current_lon = start_point['longitude'] + (lon_step * current_step)
            
            distance_covered = haversine(start_point['latitude'], start_point['longitude'],
                                       current_lat, current_lon)
            
            toll = calculate_toll(vehicle_type, distance_covered)
            fine = calculate_fine(vehicle_type) if (current_step == steps and random.random() < 0.1) else 0
            
            vehicle_simulations[vehicle_id] = {
                'current_position': {
                    'latitude': current_lat,
                    'longitude': current_lon
                },
                'distance_covered': round(distance_covered, 2),
                'toll': round(toll, 2),
                'fine': fine,
                'progress': int((current_step/steps)*100),
                'completed': current_step == steps,
                'vehicle_type': vehicle_type,
                'total_distance': round(total_distance, 2)
            }
            
            current_step += 1
            time.sleep(1)
            
            if current_step == steps:
                save_completed_trip(vehicle_id, user_id, vehicle_type, 
                                  start_point, end_plaza, 
                                  total_distance, toll, fine)
                
    except Exception as e:
        logger.error(f"Straight line simulation error: {str(e)}")
    finally:
        if vehicle_id in vehicle_simulations and vehicle_simulations[vehicle_id]['completed']:
            del vehicle_simulations[vehicle_id]

def simulate_vehicle_progress(vehicle_id, user_id, vehicle_type, start_point, end_plaza):
    global vehicle_simulations
    
    try:
        route_coords = load_route_coordinates()
        traveled_route = []
        
        if not route_coords:
            return simulate_straight_line_progress(vehicle_id, user_id, vehicle_type, start_point, end_plaza)
            
        start_idx = find_closest_point_idx(route_coords, start_point['latitude'], start_point['longitude'])
        end_idx = find_closest_point_idx(route_coords, end_plaza['latitude'], end_plaza['longitude'])
        
        if start_idx > end_idx:
            route_segment = route_coords[end_idx:start_idx+1]
            route_segment.reverse()
        else:
            route_segment = route_coords[start_idx:end_idx+1]
        
        save_route_to_db(vehicle_id, route_segment)
        
        total_distance = 0
        for i in range(1, len(route_segment)):
            total_distance += haversine(
                route_segment[i-1]['latitude'], route_segment[i-1]['longitude'],
                route_segment[i]['latitude'], route_segment[i]['longitude']
            )
        
        steps = len(route_segment)
        current_step = 0
        
        while current_step < steps:
            current_point = route_segment[current_step]
            traveled_route.append(current_point)
            
            if current_step % 5 == 0:
                save_route_to_db(vehicle_id, traveled_route)
            
            distance_covered = 0
            for i in range(1, current_step+1):
                distance_covered += haversine(
                    route_segment[i-1]['latitude'], route_segment[i-1]['longitude'],
                    route_segment[i]['latitude'], route_segment[i]['longitude']
                )
            
            toll = calculate_toll(vehicle_type, distance_covered)
            fine = calculate_fine(vehicle_type) if (current_step == steps-1 and random.random() < 0.1) else 0
            
            vehicle_simulations[vehicle_id] = {
                'current_position': current_point,
                'distance_covered': round(distance_covered, 2),
                'toll': round(toll, 2),
                'fine': fine,
                'progress': int((current_step/steps)*100),
                'completed': current_step == steps-1,
                'vehicle_type': vehicle_type,
                'total_distance': round(total_distance, 2)
            }
            
            current_step += 1
            time.sleep(1)
            
            if current_step == steps:
                save_completed_trip(vehicle_id, user_id, vehicle_type, 
                                  start_point, end_plaza, 
                                  total_distance, toll, fine)
                save_route_to_db(vehicle_id, traveled_route)
                
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
    finally:
        if vehicle_id in vehicle_simulations and vehicle_simulations[vehicle_id]['completed']:
            del vehicle_simulations[vehicle_id]

def get_simulation_route(vehicle_id):
    """Get the stored route coordinates from a simulation"""
    try:
        conn = get_db_connection()
        route = conn.execute('''
            SELECT route_coordinates FROM simulation_routes 
            WHERE vehicle_id = ?
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (vehicle_id,)).fetchone()
        
        if route and route['route_coordinates']:
            return json.loads(route['route_coordinates'])
        return []
    except Exception as e:
        logger.error(f"Error getting simulation route: {str(e)}")
        return []
    finally:
        conn.close()

# Routes
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('login'))

        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
@csrf.exempt
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        vehicle_id = request.form.get('vehicle_id')
        vehicle_name = request.form.get('vehicle_name')
        vehicle_type = request.form.get('vehicle_type')
        
        if not all([username, password, vehicle_id, vehicle_name, vehicle_type]):
            flash('All fields are required!', 'error')
            return redirect(url_for('signup'))

        try:
            hashed_password = generate_password_hash(password)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                         (username, hashed_password, 'user'))
            user_id = cursor.lastrowid
            cursor.execute('''
                INSERT INTO vehicles (user_id, vehicle_id, vehicle_name, vehicle_type)
                VALUES (?, ?, ?, ?)
            ''', (user_id, vehicle_id, vehicle_name, vehicle_type))
            conn.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or vehicle ID already exists.', 'error')
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            flash('An error occurred during signup', 'error')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE user_id = ?', (session['user_id'],)).fetchone()
        last_5_transactions = conn.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''', (session['user_id'],)).fetchall()

        total_transactions = conn.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', 
                                        (session['user_id'],)).fetchone()[0] or 0
        total_toll = conn.execute('SELECT SUM(toll) FROM transactions WHERE user_id = ?', 
                                 (session['user_id'],)).fetchone()[0] or 0
        total_fine = conn.execute('SELECT SUM(fine) FROM transactions WHERE user_id = ?', 
                                 (session['user_id'],)).fetchone()[0] or 0
        total_distance = sum(t['distance'] for t in last_5_transactions) if last_5_transactions else 0

        conn.close()

        if not vehicle:
            flash('No vehicle registered. Please sign up again.', 'error')
            return redirect(url_for('signup'))

        return render_template('dashboard.html', 
                               vehicle=vehicle,
                               transactions=last_5_transactions,
                               username=session.get('username'),
                               total_transactions=total_transactions,
                               total_toll=total_toll,
                               total_fine=total_fine,
                               total_distance=total_distance)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('An error occurred while loading dashboard', 'error')
        return redirect(url_for('login'))

@app.route('/get_last_route')
def get_last_route():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    try:
        conn = get_db_connection()
        last_route = conn.execute('''
            SELECT start_latitude, start_longitude, end_latitude, end_longitude 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (session['user_id'],)).fetchone()
        
        if not last_route:
            return jsonify({"error": "No routes found"}), 404
            
        start_name = get_plaza_name(last_route['start_latitude'], last_route['start_longitude'])
        end_name = get_plaza_name(last_route['end_latitude'], last_route['end_longitude'])
        
        return jsonify({
            "start_plaza": {
                "name": start_name,
                "latitude": last_route['start_latitude'],
                "longitude": last_route['start_longitude']
            },
            "end_plaza": {
                "name": end_name,
                "latitude": last_route['end_latitude'],
                "longitude": last_route['end_longitude']
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/get_route_coordinates')
def get_route_coordinates():
    try:
        route_coords = load_route_coordinates()
        if not route_coords:
            return jsonify({"error": "Route coordinates not available"}), 404
            
        return jsonify(route_coords)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401

    vehicle_id = request.form.get('vehicle_id')
    if not vehicle_id:
        return jsonify({"error": "Vehicle ID required"}), 400

    try:
        conn = get_db_connection()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE vehicle_id = ? AND user_id = ?',
                             (vehicle_id, session['user_id'])).fetchone()
        conn.close()

        if not vehicle:
            return jsonify({"error": "Vehicle not found"}), 404

        toll_plazas = load_toll_plazas()
        start_point, end_plaza = random.sample(toll_plazas, 2)
        
        if vehicle_id in vehicle_simulations:
            return jsonify({
                "error": "Simulation already in progress",
                "solution": "Please wait for current simulation to complete"
            }), 400

        thread = Thread(
            target=simulate_vehicle_progress,
            args=(vehicle_id, session['user_id'], vehicle['vehicle_type'], start_point, end_plaza),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "message": "Simulation started successfully",
            "start_point": start_point,
            "end_plaza": end_plaza,
            "vehicle_type": vehicle['vehicle_type']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/simulation_status/<vehicle_id>')
def simulation_status(vehicle_id):
    if vehicle_id in vehicle_simulations:
        status = vehicle_simulations[vehicle_id]
        return jsonify({
            "status": "in_progress",
            "current_position": status['current_position'],
            "distance_covered": status['distance_covered'],
            "toll": status['toll'],
            "fine": status['fine'],
            "progress": status['progress'],
            "completed": status['completed'],
            "vehicle_type": status['vehicle_type'],
            "total_distance": status['total_distance']
        })
    return jsonify({"status": "not_running"})

@app.route('/map_view')
def map_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE user_id = ?', (session['user_id'],)).fetchone()
        last_transaction = conn.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (session['user_id'],)).fetchone()
        
        # Get all coordinates
        full_route = []
        traveled_route = []
        if last_transaction and 'vehicle_id' in last_transaction:
            # Get the full planned route
            full_route = get_full_route(
                last_transaction['start_latitude'], 
                last_transaction['start_longitude'],
                last_transaction['end_latitude'],
                last_transaction['end_longitude']
            )
            # Get the actual traveled route
            traveled_route = get_simulation_route(last_transaction['vehicle_id'])
        
        conn.close()

        if not vehicle:
            flash('No vehicle registered', 'error')
            return redirect(url_for('signup'))
        
        return render_template('map_view.html',
                            start_plaza={
                                'longitude': last_transaction['start_longitude'],
                                'latitude': last_transaction['start_latitude']
                            },
                            end_plaza={
                                'longitude': last_transaction['end_longitude'],
                                'latitude': last_transaction['end_latitude']
                            },
                            full_route=full_route,
                            traveled_route=traveled_route,
                            vehicle=vehicle,
                            last_transaction=last_transaction,
                            username=session.get('username'))
    except Exception as e:
        logger.error(f"Map view error: {str(e)}")
        flash('An error occurred while loading map', 'error')
        return redirect(url_for('dashboard'))
        
def get_full_route(start_lat, start_lng, end_lat, end_lng):
    """Get the full planned route between two points"""
    try:
        route_coords = load_route_coordinates()
        if not route_coords:
            return []
            
        start_idx = find_closest_point_idx(route_coords, start_lat, start_lng)
        end_idx = find_closest_point_idx(route_coords, end_lat, end_lng)
        
        if start_idx > end_idx:
            return route_coords[end_idx:start_idx+1][::-1]  # Reverse the slice
        return route_coords[start_idx:end_idx+1]
    except Exception as e:
        logger.error(f"Error getting full route: {str(e)}")
        return []       

@app.route('/payment')
def payment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        transactions = conn.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        ''', (session['user_id'],)).fetchall()
        
        # Calculate totals safely
        total_toll = sum(t['toll'] for t in transactions if t['toll'] is not None) or 0
        total_fine = sum(t['fine'] for t in transactions if t['fine'] is not None) or 0
        total_amount = total_toll + total_fine
        
        conn.close()
        
        return render_template('payment.html',
                             transactions=transactions,
                             total_toll=round(total_toll, 2),
                             total_fine=round(total_fine, 2),
                             total_amount=round(total_amount, 2),
                             username=session.get('username'))
    except Exception as e:
        logger.error(f"Payment page error: {str(e)}")
        flash('An error occurred while loading payment information', 'error')
        return redirect(url_for('dashboard'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE user_id = ?', (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or not vehicle:
            flash('User or vehicle not found', 'error')
            return redirect(url_for('dashboard'))
            
        return render_template('profile.html', 
                             user=user, 
                             vehicle=vehicle,
                             username=session.get('username'))
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        flash('An error occurred while loading profile', 'error')
        return redirect(url_for('dashboard'))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback_text = request.form.get('feedback')
        if feedback_text:
            try:
                conn = get_db_connection()
                conn.execute('INSERT INTO feedback (user_id, feedback, timestamp) VALUES (?, ?, ?)',
                           (session['user_id'], feedback_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                conn.close()
                flash('Thank you for your feedback!', 'success')
            except Exception as e:
                logger.error(f"Feedback error: {str(e)}")
                flash('Failed to submit feedback', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('feedback.html', username=session.get('username'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        vehicle_name = request.form.get('vehicle_name')
        
        try:
            conn = get_db_connection()
            # Update user info
            conn.execute('''
                UPDATE users SET email = ?, phone = ? 
                WHERE id = ?
            ''', (email, phone, session['user_id']))
            
            # Update vehicle info
            conn.execute('''
                UPDATE vehicles SET vehicle_name = ?
                WHERE user_id = ?
            ''', (vehicle_name, session['user_id']))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            logger.error(f"Profile update error: {str(e)}")
            flash('Failed to update profile', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('profile'))
    
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        vehicle = conn.execute('SELECT * FROM vehicles WHERE user_id = ?', (session['user_id'],)).fetchone()
        return render_template('edit_profile.html', user=user, vehicle=vehicle)
    except Exception as e:
        logger.error(f"Profile edit error: {str(e)}")
        flash('Error loading profile editor', 'error')
        return redirect(url_for('profile'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('change_password'))
        
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('change_password'))
            
            hashed_password = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', 
                        (hashed_password, session['user_id']))
            conn.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            flash('Failed to change password', 'error')
        finally:
            conn.close()
    
    return render_template('change_password.html')

@app.route('/receipt/<int:transaction_id>')
def view_receipt(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        transaction = conn.execute('''
            SELECT * FROM transactions 
            WHERE id = ? AND user_id = ?
        ''', (transaction_id, session['user_id'])).fetchone()
        conn.close()

        if not transaction:
            flash('Transaction not found', 'error')
            return redirect(url_for('payment'))

        return render_template('receipt.html',
                            transaction=transaction,
                            username=session.get('username'))
    except Exception as e:
        logger.error(f"Receipt error: {str(e)}")
        flash('An error occurred while loading receipt', 'error')
        return redirect(url_for('payment'))

@app.route('/receipt/<int:transaction_id>/download')
def download_receipt(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        transaction = conn.execute('''
            SELECT * FROM transactions 
            WHERE id = ? AND user_id = ?
        ''', (transaction_id, session['user_id'])).fetchone()
        conn.close()

        if not transaction:
            flash('Transaction not found', 'error')
            return redirect(url_for('payment'))

        # Generate PDF receipt (simplified example)
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Add receipt content
        pdf.cell(200, 10, txt="GPS Toll Collection Receipt", ln=1, align='C')
        pdf.cell(200, 10, txt=f"Transaction ID: {transaction['id']}", ln=1)
        pdf.cell(200, 10, txt=f"Date: {transaction['timestamp']}", ln=1)
        pdf.cell(200, 10, txt=f"Vehicle: {transaction['vehicle_type']} ({transaction['vehicle_id']})", ln=1)
        pdf.cell(200, 10, txt=f"Distance: {transaction['distance']} km", ln=1)
        pdf.cell(200, 10, txt=f"Toll: ₹{transaction['toll']:.2f}", ln=1)
        pdf.cell(200, 10, txt=f"Fine: ₹{transaction['fine']:.2f}", ln=1)
        pdf.cell(200, 10, txt=f"Total: ₹{transaction['toll'] + transaction['fine']:.2f}", ln=1)
        
        response = make_response(pdf.output(dest='S').encode('latin1'))
        response.headers.set('Content-Disposition', 'attachment', filename=f'receipt_{transaction_id}.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response

    except Exception as e:
        logger.error(f"Receipt download error: {str(e)}")
        flash('An error occurred while generating receipt', 'error')
        return redirect(url_for('payment'))

@app.route('/payment_methods', methods=['GET', 'POST'])
def payment_methods():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Handle adding new payment method
        card_number = request.form.get('card_number')
        expiry = request.form.get('expiry')
        cvv = request.form.get('cvv')
        
        # Validate and store payment method (simplified example)
        last_four = card_number[-4:] if card_number else ''
        
        try:
            conn = get_db_connection()
            conn.execute('''
                INSERT INTO payment_methods (user_id, card_type, last_four, expiry, is_default)
                VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], 'VISA', last_four, expiry, 1))
            conn.commit()
            flash('Payment method added successfully!', 'success')
        except Exception as e:
            logger.error(f"Payment method error: {str(e)}")
            flash('Failed to add payment method', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('payment_methods'))
    
    try:
        conn = get_db_connection()
        methods = conn.execute('''
            SELECT * FROM payment_methods 
            WHERE user_id = ?
            ORDER BY is_default DESC
        ''', (session['user_id'],)).fetchall()
        return render_template('payment_methods.html', payment_methods=methods)
    except Exception as e:
        logger.error(f"Payment methods error: {str(e)}")
        flash('Error loading payment methods', 'error')
        return redirect(url_for('dashboard'))

@app.route('/process_payment', methods=['POST'])
def process_payment():
    if 'user_id' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    transaction_ids = request.form.getlist('transaction_ids[]')
    payment_method_id = request.form.get('payment_method_id')
    
    if not transaction_ids:
        return jsonify({"error": "No transactions selected"}), 400
    
    try:
        conn = get_db_connection()
        
        # Calculate total amount
        total = conn.execute('''
            SELECT SUM(toll + fine) as total 
            FROM transactions 
            WHERE id IN ({seq}) AND user_id = ? AND payment_status = 'pending'
        '''.format(seq=','.join(['?']*len(transaction_ids))), 
        [*transaction_ids, session['user_id']]).fetchone()['total']
        
        if not total:
            return jsonify({"error": "No payable transactions found"}), 400
        
        payment_id = f"PYMT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        conn.execute('''
            UPDATE transactions 
            SET payment_status = 'paid', transaction_id = ?
            WHERE id IN ({seq}) AND user_id = ?
        '''.format(seq=','.join(['?']*len(transaction_ids))), 
        [payment_id, *transaction_ids, session['user_id']])
        
        conn.commit()
        
        return jsonify({
            "success": True,
            "payment_id": payment_id,
            "amount": total
        })
        
    except Exception as e:
        logger.error(f"Payment processing error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/login', methods=['GET', 'POST'])
@csrf.exempt
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            conn = get_db_connection()
            admin = conn.execute('SELECT * FROM users WHERE username = ? AND role = "admin"', 
                               (username,)).fetchone()
            conn.close()

            if admin:
                if check_password_hash(admin['password'], password):
                    session['user_id'] = admin['id']
                    session['username'] = admin['username']
                    session['role'] = admin['role']
                    flash('Admin login successful!', 'success')
                    
                    # Debug output
                    print(f"Admin logged in: {admin['username']}")
                    print(f"Session data: {session}")
                    
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Invalid password', 'error')
            else:
                flash('Admin user not found', 'error')
        except Exception as e:
            logger.error(f"Admin login error: {str(e)}")
            flash('An error occurred during login', 'error')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    print(f"Session data in admin_dashboard: {session}")
    
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('admin_login'))
    
    try:
        conn = get_db_connection()
        
        print("Testing database connection...")
        test_query = conn.execute('SELECT 1').fetchone()
        print(f"Database test result: {test_query}")
        
        total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        total_vehicles = conn.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0]
        total_transactions = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
        total_revenue = conn.execute('SELECT SUM(toll + fine) FROM transactions').fetchone()[0] or 0
        recent_feedback = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC LIMIT 5').fetchall()
        
        conn.close()
        
        print(f"Retrieved data - Users: {total_users}, Vehicles: {total_vehicles}")
        
        return render_template('admin_dashboard.html',
                            total_users=total_users,
                            total_vehicles=total_vehicles,
                            total_transactions=total_transactions,
                            total_revenue=round(total_revenue, 2),
                            recent_feedback=recent_feedback)
                            
    except sqlite3.Error as e:
        logger.error(f"Database error in admin dashboard: {str(e)}")
        flash('Database error occurred', 'error')
        return redirect(url_for('admin_login'))
    except Exception as e:
        logger.error(f"Unexpected error in admin dashboard: {str(e)}")
        flash('An unexpected error occurred', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        users = conn.execute('''
            SELECT u.*, COUNT(v.id) as vehicle_count 
            FROM users u LEFT JOIN vehicles v ON u.id = v.user_id 
            GROUP BY u.id
        ''').fetchall()
        return render_template('admin_users.html', users=users)
    except Exception as e:
        logger.error(f"Admin users error: {str(e)}")
        flash('Error loading user list', 'error')
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

@app.route('/receipt/<transaction_id>')
def generate_receipt(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        transaction = conn.execute('''
            SELECT t.*, u.username, v.vehicle_name 
            FROM transactions t 
            JOIN users u ON t.user_id = u.id 
            JOIN vehicles v ON t.vehicle_id = v.vehicle_id 
            WHERE t.transaction_id = ? AND t.user_id = ?
        ''', (transaction_id, session['user_id'])).fetchone()
        
        if not transaction:
            flash('Transaction not found', 'error')
            return redirect(url_for('payment'))
        
        return render_template('receipt.html', transaction=transaction)
    except Exception as e:
        logger.error(f"Receipt generation error: {str(e)}")
        flash('Error generating receipt', 'error')
        return redirect(url_for('payment'))
    finally:
        conn.close()

@app.route('/status')
def status():
    try:
        conn = get_db_connection()
        
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] or 0
        vehicle_count = conn.execute('SELECT COUNT(*) FROM vehicles').fetchone()[0] or 0
        transaction_count = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0] or 0
        
        conn.close()
        
        return render_template('status.html',
                             user_count=user_count,
                             vehicle_count=vehicle_count,
                             transaction_count=transaction_count,
                             username=None)  
    except Exception as e:
        logger.error(f"Status page error: {str(e)}")
        flash('Error loading status page', 'error')
        return render_template('status.html',
                             user_count=0,
                             vehicle_count=0,
                             transaction_count=0,
                             username=None)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists('vehicle.db'):
        from setup_database import create_database, create_admin_user
        create_database()
        create_admin_user()
    
    app.run(debug=True)