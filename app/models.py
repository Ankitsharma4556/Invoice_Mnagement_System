from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.String(30), primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user', server_default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def get_id(self):
        return str(self.user_id)

class Biller(db.Model):
    __tablename__ = 'biller'
    biller_id = db.Column(db.String(30), primary_key=True)
    biller_name = db.Column(db.String(255), nullable=False)
    biller_address = db.Column(db.Text)
    biller_gstin = db.Column(db.String(15))
    biller_email = db.Column(db.String(255))
    biller_contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Issuer(db.Model):
    __tablename__ = 'issuers'
    issuer_id = db.Column(db.String(30), primary_key=True)
    issuer_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Client(db.Model):
    __tablename__ = 'clients'
    client_id = db.Column(db.String(30), primary_key=True)
    client_name = db.Column(db.String(255), nullable=False)
    issuer_id = db.Column(db.String(30), db.ForeignKey('issuers.issuer_id'))
    issuer = db.relationship('Issuer', backref='clients')
    client_address = db.Column(db.Text)
    client_gstin = db.Column(db.String(15))
    client_email = db.Column(db.String(255))
    client_contact = db.Column(db.String(20))
    client_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint(client_type.in_(['TSP Model', 'Program Manager Model'])),
    )

class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.String(30), primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    issuer_id = db.Column(db.String(30), db.ForeignKey('issuers.issuer_id'))
    issuer = db.relationship('Issuer', backref='products')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.product_name}>'

class FeeMaster(db.Model):
    __tablename__ = 'fee_master'
    fee_id = db.Column(db.String(30), primary_key=True)
    fee_name = db.Column(db.String(255), nullable=False)
    fee_type = db.Column(db.String(20), nullable=False)
    fee_frequency = db.Column(db.String(20), nullable=False)
    hsn_code = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint(fee_frequency.in_(['Monthly', 'Yearly', 'One-time'])),
        db.CheckConstraint(fee_type.in_(['Static', 'Dynamic'])),
    )

class ClientProductFeeMapping(db.Model):
    __tablename__ = 'client_product_fee_mapping'
    mapping_id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(30), db.ForeignKey('clients.client_id'))
    client = db.relationship('Client', backref='client_product_fee_mappings')
    product_id = db.Column(db.String(30), db.ForeignKey('products.product_id'))
    product = db.relationship('Product', backref='client_product_fee_mappings')
    fee_id = db.Column(db.String(30), db.ForeignKey('fee_master.fee_id'))
    fee = db.relationship('FeeMaster', backref='client_product_fee_mappings')
    unit_price = db.Column(db.Numeric(10, 2), default=0.00)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InterchangeFee(db.Model):
    __tablename__ = 'interchange_fees'
    interchange_fee_id = db.Column(db.Integer, primary_key=True)
    fee_name = db.Column(db.String(255), nullable=False)
    client_id = db.Column(db.String(30), db.ForeignKey('clients.client_id'))
    client = db.relationship('Client', backref='interchange_fees')
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    interchange_amt = db.Column(db.Numeric(10, 2))
    minimum_interchange = db.Column(db.Numeric(10, 2))
    charge_date = db.Column(db.Date)  # Add this line
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    invoice_id = db.Column(db.String(30), primary_key=True)
    biller_id = db.Column(db.String(30), db.ForeignKey('biller.biller_id'))
    biller = db.relationship('Biller', backref='invoices')
    client_id = db.Column(db.String(30), db.ForeignKey('clients.client_id'))
    client = db.relationship('Client', backref='invoices')
    issuer_id = db.Column(db.String(30), db.ForeignKey('issuers.issuer_id'))
    issuer = db.relationship('Issuer', backref='invoices')
    invoice_number = db.Column(db.String(50), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    invoice_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2))
    tax_amount = db.Column(db.Numeric(10, 2))
    total_amount = db.Column(db.Numeric(10, 2))
    invoice_type = db.Column(db.String(20))
    invoice_month = db.Column(db.Date)
    charge_date = db.Column(db.Date)
    taxable_amount = db.Column(db.Numeric(10, 2))
    rounding_up = db.Column(db.Numeric(10, 2))
    grand_total = db.Column(db.Numeric(10, 2))
    invoice_amount_in_words = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'
    line_item_id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.String(30), db.ForeignKey('invoices.invoice_id'))
    invoice = db.relationship('Invoice', backref='line_items')
    fee_id = db.Column(db.String(30), db.ForeignKey('fee_master.fee_id'))
    fee = db.relationship('FeeMaster', backref='invoice_line_items')
    units = db.Column(db.Integer)
    unit_price = db.Column(db.Numeric(10, 2))
    total = db.Column(db.Numeric(10, 2))
    gst_amount = db.Column(db.Numeric(10, 2))
    final_amount = db.Column(db.Numeric(10, 2))
    description = db.Column(db.Text)  # Add this line
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeeHistory(db.Model):
    __tablename__ = 'fee_history'
    fee_history_id = db.Column(db.String(30), primary_key=True)
    client_id = db.Column(db.String(30), db.ForeignKey('clients.client_id'))
    client = db.relationship('Client', backref='fee_history')
    issuer_id = db.Column(db.String(30), db.ForeignKey('issuers.issuer_id'))
    issuer = db.relationship('Issuer', backref='fee_history')
    fee_id = db.Column(db.String(30), db.ForeignKey('fee_master.fee_id'))
    fee = db.relationship('FeeMaster', backref='fee_history')
    charge_date = db.Column(db.Date)
    units = db.Column(db.Integer)
    total = db.Column(db.Numeric(10, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)