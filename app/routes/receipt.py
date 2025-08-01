from flask import Blueprint, request, jsonify
import os
from ..models import User
from ..utils.auth_helpers import decode_token
from ..utils.donut_wrapper import DonutOCR

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

    if 'receipt' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['receipt']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    print(f"🔍 Saved file to: {filepath}")
    try:
        result = donut.extract_receipt_data(filepath)
        print(f"🔍 Donut raw output: {repr(result)}")
    except Exception as e:
        print(f"❌ Donut exception trace:", flush=True)
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Donut failed: {e}"}), 500
    # try:
    #     result = donut.extract_receipt_data(filepath)
    # except Exception as e:
    #     return jsonify({"error": f"Donut failed: {str(e)}"}), 500

    return jsonify({"parsed": result}), 200
