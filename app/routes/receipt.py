from flask import Blueprint, request, jsonify
import os
from ..models import User, Receipt, LineItem
from ..utils.auth_helpers import decode_token
from ..utils.donut_wrapper import DonutOCR
from ..extensions import db
from ..utils.receipt_helpers import normalize_items
from ..utils.receipt_helpers import normalize_items, compute_splits


receipt_bp = Blueprint('receipt', __name__)
UPLOAD_FOLDER = 'uploads/'

donut = DonutOCR()

def get_user_from_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    payload = decode_token(token)
    if not payload:
        return None
    return User.query.get(payload['user_id'])

@receipt_bp.route('/upload', methods=['POST'])
def upload_receipt():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # must include party_id in form data
    party_id = request.form.get('party_id')
    if not party_id:
        return jsonify({"error": "Missing party_id"}), 400

    if 'receipt' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # save to disk
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # 1) call Donut (raw list)
    try:
        raw_list = donut.extract_receipt_data(filepath)
    except Exception as e:
        return jsonify({"error": f"Donut failed: {e}"}), 500

    # 2) normalize into our DTO shape
    clean = normalize_items(raw_list)

    # 3) persist Receipt + LineItems
    receipt = Receipt(
        filename    = file.filename,
        filepath    = filepath,
        user_id     = user.id,
        party_id    = int(party_id)
    )
    db.session.add(receipt)
    # flush to get receipt.id
    db.session.flush()

    for li in clean['items']:
        line_item = LineItem(
            receipt_id  = receipt.id,
            name        = li['name'],
            quantity    = li['quantity'],
            unit_price  = li['unitPrice'],
            total_price = li['totalPrice']
        )
        db.session.add(line_item)

    db.session.commit()

    # 4) return the DTO + receipt_id
    return jsonify({
        "receipt_id": receipt.id,
        **clean
    }), 200


@receipt_bp.route('/<int:receipt_id>/items', methods=['GET'])
def list_items(receipt_id):
    user = get_user_from_token() or abort(401)
    receipt = Receipt.query.get_or_404(receipt_id)
    items = [{
        "id":         it.id,
        "name":       it.name,
        "quantity":   it.quantity,
        "unitPrice":  it.unit_price,
        "totalPrice": it.total_price,
        "selectedBy": it.selected_by
    } for it in receipt.items]
    return jsonify(items), 200

@receipt_bp.route('/<int:receipt_id>/items/<int:item_id>/select', methods=['POST'])
def select_item(receipt_id, item_id):
    user = get_user_from_token() or abort(401)
    item = LineItem.query.filter_by(id=item_id, receipt_id=receipt_id).first_or_404()
    item.selected_by = user.id
    db.session.commit()
    return jsonify({"message":"Item selected","item_id":item.id}), 200

@receipt_bp.route('/<int:receipt_id>/items/<int:item_id>/unselect', methods=['POST'])
def unselect_item(receipt_id, item_id):
    user = get_user_from_token() or abort(401)
    item = LineItem.query.filter_by(id=item_id, receipt_id=receipt_id).first_or_404()
    if item.selected_by == user.id:
        item.selected_by = None
        db.session.commit()
    return jsonify({"message":"Item unselected","item_id":item.id}), 200

@receipt_bp.route('/<int:receipt_id>/split', methods=['GET'])
def split_receipt(receipt_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    receipt = Receipt.query.get_or_404(receipt_id)

    # (Optional) ensure the user is in this Party:
    # if user.id not in [m.id for m in receipt.party.members]:
    #     return jsonify({"error": "Forbidden"}), 403

    # Compute splits. 
    # NOTE: if you later add taxes, service_fee, tip to Receipt, pull them here:
    taxes       = 0.0
    service_fee = 0.0
    tip         = 0.0

    splits = compute_splits(receipt, taxes, service_fee, tip)
    return jsonify({"splits": splits}), 200