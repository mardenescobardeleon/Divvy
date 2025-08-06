# app/utils/receipt_helpers.py
from collections import defaultdict
from ..models import User

def normalize_items(raw_parsed):
    """
    Convert raw Donut output into clean LineItemDTOs and overall totals.
    """
    items = []
    idx = 1
    for entry in raw_parsed:
        raw_price = entry.get("price", "").replace("$", "").replace(",", "")
        raw_qty   = entry.get("cnt") or entry.get("quantity") or "1"
        try:
            price = float(raw_price)
            qty   = int(float(raw_qty))
        except ValueError:
            continue

        items.append({
            "id":         idx,
            "name":       entry.get("nm", entry.get("name", "")).strip(),
            "quantity":   qty,
            "unitPrice":  round(price / qty, 2),
            "totalPrice": price,
            "selected":   False
        })
        idx += 1

    # 1) Compute subTotal
    sub_total = sum(item["totalPrice"] for item in items)

    # 2) Default other fields to zero (or pull from raw_parsed if you enhance later)
    taxes       = 0.0
    service_fee = 0.0
    tip         = 0.0

    # 3) Total is the sum of everything
    total = sub_total + taxes + service_fee + tip

    return {
        "items":      items,
        "subTotal":   sub_total,
        "taxes":      taxes,
        "serviceFee": service_fee,
        "tip":        tip,
        "total":      total
    }

def compute_splits(receipt, taxes=0.0, service_fee=0.0, tip=0.0):
    """
    Given a Receipt (with items and selected_by), returns a list of:
      { user_id, username, subtotal, tax, service_fee, tip, total }
    """
    # 1) Total up each user's item subtotal (unselected items go to the host)
    user_subtotals = defaultdict(float)
    for item in receipt.items:
        uid = item.selected_by or receipt.user_id
        user_subtotals[uid] += item.total_price

    # 2) Receipt-level subtotal
    receipt_subtotal = sum(user_subtotals.values())

    splits = []
    for uid, subtotal in user_subtotals.items():
        # 3) pro-rata shares
        ratio = (subtotal / receipt_subtotal) if receipt_subtotal else 0
        tax_share        = round(taxes       * ratio, 2)
        service_share    = round(service_fee * ratio, 2)
        tip_share        = round(tip         * ratio, 2)
        total_due        = round(subtotal + tax_share + service_share + tip_share, 2)

        user = User.query.get(uid)
        splits.append({
            "user_id":    uid,
            "username":   user.username if user else None,
            "subtotal":   round(subtotal, 2),
            "tax":        tax_share,
            "service_fee":service_share,
            "tip":        tip_share,
            "total":      total_due
        })

    return splits