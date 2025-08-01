from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import User, Friendship
from ..utils.auth_helpers import decode_token

friends_bp = Blueprint('friends', __name__)

def get_user_from_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = decode_token(token)
    if not payload:
        return None
    return User.query.get(payload['user_id'])

@friends_bp.route('/add', methods=['POST'])
def add_friend():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    friend_username = data['username']
    friend = User.query.filter_by(username=friend_username).first()

    if not friend or friend.id == user.id:
        return jsonify({"error": "Invalid user"}), 400

    # Prevent duplicate friendships
    existing = Friendship.query.filter_by(user_id=user.id, friend_id=friend.id).first()
    if existing:
        return jsonify({"error": "Already friends"}), 400

    f1 = Friendship(user_id=user.id, friend_id=friend.id)
    f2 = Friendship(user_id=friend.id, friend_id=user.id)
    db.session.add_all([f1, f2])
    db.session.commit()

    return jsonify({"message": "Friend added successfully"}), 200

@friends_bp.route('/list', methods=['GET'])
def list_friends():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    friendships = Friendship.query.filter_by(user_id=user.id).all()
    friends = [User.query.get(f.friend_id).username for f in friendships]

    return jsonify({"friends": friends}), 200
