from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Party, PartyMember, User
from ..utils.auth_helpers import decode_token

party_bp = Blueprint('party', __name__)

def get_user_from_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = decode_token(token)
    if not payload:
        return None
    return User.query.get(payload['user_id'])

@party_bp.route('/create', methods=['POST'])
def create_party():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    name = data.get('name')
    friend_usernames = data.get('friends', [])  # list of usernames

    party = Party(name=name, host_id=user.id)
    db.session.add(party)
    db.session.flush()  # to get party.id

    # Add host
    db.session.add(PartyMember(party_id=party.id, user_id=user.id))

    for uname in friend_usernames:
        friend = User.query.filter_by(username=uname).first()
        if friend:
            db.session.add(PartyMember(party_id=party.id, user_id=friend.id))

    db.session.commit()

    return jsonify({"message": "Party created", "party_id": party.id}), 201

@party_bp.route('/<int:party_id>/members', methods=['GET'])
def list_members(party_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    members = PartyMember.query.filter_by(party_id=party_id).all()
    usernames = [User.query.get(m.user_id).username for m in members]

    return jsonify({"members": usernames}), 200

@party_bp.route('/<int:party_id>/lock', methods=['POST'])
def lock_party(party_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    party = Party.query.get(party_id)
    if not party or party.host_id != user.id:
        return jsonify({"error": "Only host can lock the party"}), 403

    party.is_locked = True
    db.session.commit()
    return jsonify({"message": "Party locked"}), 200
