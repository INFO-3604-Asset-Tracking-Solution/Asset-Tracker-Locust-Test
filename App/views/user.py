from flask import Blueprint, render_template, jsonify, request, send_from_directory, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from.index import index_views

from App.controllers import (
    create_user,
    get_all_users,
    get_all_users_json,
    get_user,
    delete_user,
    jwt_required
)

user_views = Blueprint('user_views', __name__, template_folder='../templates')

@user_views.route('/users', methods=['GET'])
def get_user_page():
    users = get_all_users()
    return render_template('users.html', users=users)

@user_views.route('/users', methods=['POST'])
def create_user_action():
    data = request.form
    flash(f"User {data['username']} created!")
    create_user(data['username'], data['password'])
    return redirect(url_for('user_views.get_user_page'))

@user_views.route('/api/users', methods=['GET'])
def get_users_action():
    users = get_all_users_json()
    return jsonify(users)

@user_views.route('/api/users/create', methods=['POST'])
@jwt_required()
def create_user_endpoint():
    """Create a new user (requires authentication)"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not all(key in data for key in ['email', 'username', 'password']):
            return jsonify({
                'success': False, 
                'message': 'Email, username, and password are required'
            }), 400
            
        # Create the user
        user = create_user(data['email'], data['username'], data['password'])
        
        if user:
            return jsonify({
                'success': True,
                'message': f"User {user.username} created successfully",
                'user': user.get_json()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create user. Email may already be in use.'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error creating user: {str(e)}'
        }), 500

@user_views.route('/api/users/<int:user_id>/delete', methods=['POST'])
@jwt_required()
def delete_user_endpoint(user_id):
    """Delete a user by ID (requires authentication)"""
    try:
        # Prevent deleting the current user
        if int(jwt_current_user.id) == user_id:
            return jsonify({
                'success': False,
                'message': 'You cannot delete your own account'
            }), 400
            
        # Delete the user
        result = delete_user(user_id)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'User not found or could not be deleted'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}'
        }), 500

@user_views.route('/static/users', methods=['GET'])
def static_user_page():
  return send_from_directory('static', 'static-user.html')