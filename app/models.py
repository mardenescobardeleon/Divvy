from .extensions import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    receipts = db.relationship('Receipt', back_populates='user')

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Party(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    receipts = db.relationship('Receipt', back_populates='party')

class PartyMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    party_id = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Receipt(db.Model):
    __tablename__ = 'receipt'
    id = db.Column(db.Integer, primary_key=True)

    # — your existing fields —
    filename     = db.Column(db.String(256), nullable=False)    # original upload name
    filepath     = db.Column(db.String(512), nullable=False)    # where we saved it under uploads/
    uploaded_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    party_id     = db.Column(db.Integer, db.ForeignKey('party.id'), nullable=False)

    # relationships
    user         = db.relationship('User', back_populates='receipts')
    party        = db.relationship('Party', back_populates='receipts')
    items        = db.relationship('LineItem', backref='receipt', cascade='all, delete-orphan')

class LineItem(db.Model):
    __tablename__   = 'line_items'
    id              = db.Column(db.Integer, primary_key=True)
    receipt_id      = db.Column(db.Integer, db.ForeignKey('receipt.id'), nullable=False)
    name            = db.Column(db.String(256), nullable=False)
    quantity        = db.Column(db.Integer, nullable=False, default=1)
    unit_price      = db.Column(db.Float, nullable=False)
    total_price     = db.Column(db.Float, nullable=False)
    selected_by     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    user = db.relationship('User', backref='selected_items')


