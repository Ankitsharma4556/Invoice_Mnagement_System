from functions import calculate_interchange_line_item, generate_invoice_line_items, get_applicable_fees
from num2words import num2words
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Biller, Client, Issuer, FeeMaster, ClientProductFeeMapping, Invoice, Product, FeeHistory, InvoiceLineItem, InterchangeFee
from forms import LoginForm, RegistrationForm, GenerateClientInvoiceForm, AddClientForm, AddIssuerForm, AddFeeForm, AddProductForm, EditIssuerForm, EditFeeForm, EditProductForm, DynamicFeeForm, InterchangeFeeForm, ClientProductFeeMappingForm
from datetime import datetime, timedelta
from flask import render_template_string
from html_to_pdf import generate_pdf_from_html
from flask import current_app
import os
from decimal import Decimal

blueprint = Blueprint('main', __name__)

@blueprint.route('/')
def home():
    return render_template('home.html')

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('main.admin_home'))
            else:
                return redirect(url_for('main.user_home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        user = User(user_id=generate_user_id(), username=form.username.data, password=hashed_password, role=form.role.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.home'))

@blueprint.route('/admin')
@login_required
def admin_home():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('admin_home.html')

@blueprint.route('/user')
@login_required
def user_home():
    if current_user.role != 'user':
        flash('Access denied. You must be a user to access this page.', 'danger')
        return redirect(url_for('main.home'))
    
    invoices = Invoice.query.all()
    
    return render_template('user_home.html', invoices=invoices)

@blueprint.route('/generate-client-invoices', methods=['GET', 'POST'])
@login_required
def generate_client_invoices():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))

    form = GenerateClientInvoiceForm()

    if form.validate_on_submit():
        client_id = form.client_id.data
        start_date = form.start_date.data
        end_date = form.end_date.data

        return redirect(url_for('main.enter_interchange_fee', client_id=client_id, start_date=start_date, end_date=end_date))

    return render_template('generate_client_invoices.html', form=form)

@blueprint.route('/enter-units', methods=['GET', 'POST'])
@login_required
def enter_units():
    client_id = request.args.get('client_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interchange_share_percentage = request.args.get('interchange_share_percentage')

    if not client_id or not start_date or not end_date:
        flash('Invalid request parameters.', 'danger')
        return redirect(url_for('main.generate_client_invoices'))

    applicable_fees = get_applicable_fees(client_id, start_date, end_date, exclude_interchange=True)

    if request.method == 'POST':
        form_data = request.form.to_dict()

        return generate_invoices(client_id, start_date, end_date, form_data, applicable_fees, interchange_share_percentage)

    return render_template('enter_units.html', applicable_fees=applicable_fees)

@blueprint.route('/enter-interchange-fee', methods=['GET', 'POST'])
@login_required
def enter_interchange_fee():
    client_id = request.args.get('client_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not client_id or not start_date or not end_date:
        flash('Invalid request parameters.', 'danger')
        return redirect(url_for('main.generate_client_invoices'))

    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))

    form = InterchangeFeeForm()

    if form.validate_on_submit():
        interchange_amt = form.interchange_amt.data or 0
        minimum_interchange = form.minimum_interchange.data or 0
        interchange_percentage = form.interchange_percentage.data or 0

        if interchange_amt == 0 and minimum_interchange == 0:
            # If both interchange_amt and minimum_interchange are 0, skip the Interchange fee
            return redirect(url_for('main.enter_units', client_id=client_id, start_date=start_date, end_date=end_date, interchange_share_percentage=0))

        interchange_fee = InterchangeFee(
            fee_name='Interchange',
            client_id=client_id,
            start_date=start_date,
            end_date=end_date,
            interchange_amt=interchange_amt,
            minimum_interchange=minimum_interchange,
            charge_date=datetime.now().date()
        )
        db.session.add(interchange_fee)
        db.session.commit()

        return redirect(url_for('main.enter_units', client_id=client_id, start_date=start_date, end_date=end_date, interchange_share_percentage=interchange_percentage))

    return render_template('enter_interchange_fee.html', form=form)

@blueprint.route('/generate-invoices', methods=['GET', 'POST'])
@login_required
def generate_invoices(client_id, start_date, end_date, form_data, applicable_fees, interchange_percentage):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))

    client = Client.query.get(client_id)
    interchange_line_item = calculate_interchange_line_item(client_id, start_date, end_date, interchange_percentage)

    line_items = generate_invoice_line_items(client_id, start_date, end_date, applicable_fees, form_data, interchange_line_item)

    current_app.logger.info(f"Generating invoice for client: {client_id}")
    biller = Biller.query.first()

    invoice = Invoice(
        invoice_id=generate_invoice_id(),
        biller_id=biller.biller_id,
        client_id=client.client_id,
        issuer_id=client.issuer_id,
        invoice_number=generate_invoice_number(),
        invoice_date=datetime.now().date(),
        invoice_amount=0,
        tax_rate=18,
        tax_amount=0,
        total_amount=0,
        invoice_type='client',
        invoice_month=start_date,
        charge_date=datetime.now().date()
    )

    invoice.line_items = line_items

    total_tax_amount = Decimal(0)
    total_amount = Decimal(0)

    for line_item in line_items:
        total_tax_amount += line_item.gst_amount
        total_amount += line_item.final_amount

    invoice.invoice_amount = sum(item.total for item in line_items)
    invoice.tax_amount = total_tax_amount
    invoice.total_amount = total_amount

    taxable_amount = invoice.total_amount - invoice.tax_amount
    grand_total = invoice.total_amount

    rounded_grand_total = Decimal(grand_total).quantize(Decimal('0.10'), rounding='ROUND_HALF_UP')
    round_off = rounded_grand_total - grand_total

    invoice.taxable_amount = taxable_amount
    invoice.rounding_up = round_off
    invoice.grand_total = rounded_grand_total
    invoice.invoice_amount_in_words = num2words(rounded_grand_total, lang='en_IN', to='currency', currency='INR')

    db.session.add(invoice)
    db.session.commit()
    current_app.logger.info(f"Invoice generated: {invoice.invoice_number}")

    if not applicable_fees:
        flash('No applicable fees found for the selected client.', 'warning')
        return redirect(url_for('main.generate_client_invoices'))

    html = render_template('invoice_template.html', invoice=invoice, client=client, line_items=invoice.line_items)

    pdf_data = generate_pdf_from_html(html)

    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
    return response

@blueprint.route('/invoice-history')
@login_required
def invoice_history():
    if current_user.role == 'admin':
        invoices = Invoice.query.all()
    else:
        client = Client.query.filter_by(client_email=current_user.username).first()
        if client:
            invoices = Invoice.query.filter_by(client_id=client.client_id).all()
        else:
            invoices = []

    return render_template('invoice_history.html', invoices=invoices)

@blueprint.route('/manage-clients')
@login_required
def manage_clients():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    clients = Client.query.all()
    return render_template('manage_clients.html', clients=clients)

@blueprint.route('/add-client', methods=['GET', 'POST'])
@login_required
def add_client():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = AddClientForm()
    if form.validate_on_submit():
        client = Client(
            client_id=generate_client_id(),
            client_name=form.client_name.data,
            client_address=form.client_address.data,
            client_gstin=form.client_gstin.data,
            client_email=form.client_email.data,
            client_contact=form.client_contact.data,
            issuer_id=form.issuer_id.data,
            client_type=form.client_type.data
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully.', 'success')
        return redirect(url_for('main.manage_clients'))
    return render_template('add_client.html', form=form)

@blueprint.route('/edit-client/<string:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    client = Client.query.get(client_id)
    form = AddClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        flash('Client updated successfully.', 'success')
        return redirect(url_for('main.manage_clients'))
    return render_template('edit_client.html', form=form, client=client)

@blueprint.route('/delete-client/<string:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    client = Client.query.get(client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully.', 'success')
    return redirect(url_for('main.manage_clients'))

@blueprint.route('/manage-issuers')
@login_required
def manage_issuers():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    issuers = Issuer.query.all()
    return render_template('manage_issuers.html', issuers=issuers)

@blueprint.route('/add-issuer', methods=['GET', 'POST'])
@login_required
def add_issuer():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = AddIssuerForm()
    if form.validate_on_submit():
        issuer = Issuer(issuer_id=generate_issuer_id(), issuer_name=form.issuer_name.data)
        db.session.add(issuer)
        db.session.commit()
        flash('Issuer added successfully.', 'success')
        return redirect(url_for('main.manage_issuers'))
    return render_template('add_issuer.html', form=form)

@blueprint.route('/edit-issuer/<string:issuer_id>', methods=['GET', 'POST'])
@login_required
def edit_issuer(issuer_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    issuer = Issuer.query.get(issuer_id)
    form = EditIssuerForm(obj=issuer)
    if form.validate_on_submit():
        form.populate_obj(issuer)
        db.session.commit()
        flash('Issuer updated successfully.', 'success')
        return redirect(url_for('main.manage_issuers'))
    return render_template('edit_issuer.html', form=form, issuer=issuer)

@blueprint.route('/delete-issuer/<string:issuer_id>', methods=['POST'])
@login_required
def delete_issuer(issuer_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    issuer = Issuer.query.get(issuer_id)
    db.session.delete(issuer)
    db.session.commit()
    flash('Issuer deleted successfully.', 'success')
    return redirect(url_for('main.manage_issuers'))

@blueprint.route('/manage-fees')
@login_required
def manage_fees():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    fees = FeeMaster.query.all()
    return render_template('manage_fees.html', fees=fees)

@blueprint.route('/add-fee', methods=['GET', 'POST'])
@login_required
def add_fee():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = AddFeeForm()
    if form.validate_on_submit():
        fee = FeeMaster(
            fee_id=generate_fee_id(),
            fee_name=form.fee_name.data,
            fee_type=form.fee_type.data,
            fee_frequency=form.fee_frequency.data,
            hsn_code=form.hsn_code.data,
            is_dynamic=form.is_dynamic.data
        )
        db.session.add(fee)
        db.session.commit()
        flash('Fee added successfully.', 'success')
        return redirect(url_for('main.manage_fees'))
    return render_template('add_fee.html', form=form)

@blueprint.route('/edit-fee/<string:fee_id>', methods=['GET', 'POST'])
@login_required
def edit_fee(fee_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    fee = FeeMaster.query.get(fee_id)
    form = EditFeeForm(obj=fee)
    if form.validate_on_submit():
        form.populate_obj(fee)
        db.session.commit()
        flash('Fee updated successfully.', 'success')
        return redirect(url_for('main.manage_fees'))
    return render_template('edit_fee.html', form=form, fee=fee)

@blueprint.route('/delete-fee/<string:fee_id>', methods=['POST'])
@login_required
def delete_fee(fee_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    fee = FeeMaster.query.get(fee_id)
    db.session.delete(fee)
    db.session.commit()
    flash('Fee deleted successfully.', 'success')
    return redirect(url_for('main.manage_fees'))

@blueprint.route('/manage-products')
@login_required
def manage_products():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    products = Product.query.all()
    return render_template('manage_products.html', products=products)

@blueprint.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    form = AddProductForm()
    if form.validate_on_submit():
        product = Product(product_id=generate_product_id(), product_name=form.product_name.data, issuer_id=form.issuer_id.data)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('add_product.html', form=form)

@blueprint.route('/edit-product/<string:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    product = Product.query.get(product_id)
    form = EditProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('main.manage_products'))
    return render_template('edit_product.html', form=form, product=product)

@blueprint.route('/delete-product/<string:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))
    product = Product.query.get(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('main.manage_products'))

@blueprint.route('/view-invoice/<string:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('main.invoice_history'))

    client = invoice.client
    line_items = invoice.line_items

    html = render_template('invoice_template.html', invoice=invoice, client=client, line_items=line_items)

    pdf_data = generate_pdf_from_html(html)

    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=invoice_{invoice.invoice_number}.pdf'
    return response

@blueprint.route('/download-invoice/<string:invoice_id>')
@login_required
def download_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('main.invoice_history'))

    client = invoice.client
    line_items = invoice.line_items

    html = render_template_string(render_template('invoice_template.html', invoice=invoice, client=client, line_items=line_items))

    pdf_data = generate_pdf_from_html(html)

    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
    return response

@blueprint.route('/map-client-product-fees', methods=['GET', 'POST'])
@login_required
def map_client_product_fees():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))

    form = ClientProductFeeMappingForm()

    if form.validate_on_submit():
        client_id = form.client_id.data
        product_id = form.product_id.data
        fee_id = form.fee_id.data
        unit_price = form.unit_price.data or 0
        start_date = form.start_date.data
        end_date = form.end_date.data

        mapping = ClientProductFeeMapping(
            client_id=client_id,
            product_id=product_id,
            fee_id=fee_id,
            unit_price=unit_price,
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(mapping)
        db.session.commit()

        flash('Client-Product-Fee mapping added successfully.', 'success')
        return redirect(url_for('main.map_client_product_fees'))

    clients = Client.query.all()
    products = Product.query.all()
    fees = FeeMaster.query.all()

    return render_template('map_client_product_fees.html', form=form, clients=clients, products=products, fees=fees)

@blueprint.route('/manage-interchange-fees', methods=['GET', 'POST'])
@login_required
def manage_interchange_fees():
    if current_user.role != 'admin':
        flash('Access denied. You must be an admin to access this page.', 'danger')
        return redirect(url_for('main.home'))

    form = InterchangeFeeForm()
    if form.validate_on_submit():
        interchange_fee = InterchangeFee(
            fee_name='Interchange',
            client_id=form.client_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            interchange_amt=form.interchange_amt.data,
            minimum_interchange=form.minimum_interchange.data
        )
        db.session.add(interchange_fee)
        db.session.commit()
        flash('Interchange fee added successfully.', 'success')
        return redirect(url_for('main.manage_interchange_fees'))

    interchange_fees = InterchangeFee.query.all()
    return render_template('manage_interchange_fees.html', form=form, interchange_fees=interchange_fees)

def generate_invoice_id():
    return f'INV-{datetime.now().strftime("%Y%m%d")}-{Invoice.query.count() + 1}'

def generate_invoice_number():
    return f'INV-{datetime.now().strftime("%Y%m%d")}-{Invoice.query.count() + 1}'

def generate_fee_history_id():
    return f'FEEHIST-{datetime.now().strftime("%Y%m%d")}-{FeeHistory.query.count() + 1}'

def generate_user_id():
    return f'USER-{datetime.now().strftime("%Y%m%d")}-{User.query.count() + 1}'

def generate_client_id():
    return f'CLIENT-{datetime.now().strftime("%Y%m%d")}-{Client.query.count() + 1}'

def generate_issuer_id():
    return f'ISSUER-{datetime.now().strftime("%Y%m%d")}-{Issuer.query.count() + 1}'

def generate_fee_id():
    return f'FEE-{datetime.now().strftime("%Y%m%d")}-{FeeMaster.query.count() + 1}'

def generate_product_id():
    return f'PROD-{datetime.now().strftime("%Y%m%d")}-{Product.query.count() + 1}'

def fee_already_charged(client_id, fee_id):
    fee_history = FeeHistory.query.filter(
        FeeHistory.client_id == client_id,
        FeeHistory.fee_id == fee_id
    ).first()

    return fee_history is not None

def fee_already_charged_yearly(client_id, fee_id, start_date):
    fee_history = FeeHistory.query.filter(
        FeeHistory.client_id == client_id,
        FeeHistory.fee_id == fee_id,
        db.extract('year', FeeHistory.charge_date) == start_date.year
    ).first()

    return fee_history is not None

def fee_already_charged_monthly(client_id, fee_id, start_date):
    fee_history = FeeHistory.query.filter(
        FeeHistory.client_id == client_id,
        FeeHistory.fee_id == fee_id,
        db.extract('year', FeeHistory.charge_date) == start_date.year,
        db.extract('month', FeeHistory.charge_date) == start_date.month
    ).first()

    return fee_history is not None

@blueprint.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@blueprint.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500

@blueprint.app_context_processor
def inject_current_year():
    return dict(current_year=datetime.now().year)