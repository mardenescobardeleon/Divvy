from flask import Blueprint, request, jsonify
from ..models import User
from ..extensions import db
from ..utils.auth_helpers import hash_password, check_password, generate_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data['email']
    username = data['username']
    password = data['password']

    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({"error": "User already exists"}), 400

    new_user = User(
        email=email,
        username=username,
        password_hash=hash_password(password)
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data['email'] if 'email' in data else data['username']
    password = data['password']

    user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user.id)
    return jsonify({"token": token}), 200
