from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, DateField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Length, ValidationError, Optional, InputRequired
from models import Client, Issuer, FeeMaster, Product

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=20)])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=20)])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('user', 'User')], validators=[DataRequired()])
    submit = SubmitField('Register')

class GenerateClientInvoiceForm(FlaskForm):
    client_id = SelectField('Client', coerce=str, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Generate Client Invoices')

    def __init__(self, *args, **kwargs):
        super(GenerateClientInvoiceForm, self).__init__(*args, **kwargs)
        self.client_id.choices = [(c.client_id, c.client_name) for c in Client.query.all()]

    def populate_fees(self, applicable_fees, interchange_mapping):
        for fee in applicable_fees:
            if fee.fee_type == 'Dynamic':
                self[f'units_{fee.fee_id}'] = IntegerField(f'{fee.fee_name} Units', validators=[DataRequired()], default=1)

        if interchange_mapping:
            self.interchange_amt = DecimalField('Interchange Amount', validators=[DataRequired()], default=0)
            self.minimum_interchange = DecimalField('Minimum Interchange', validators=[DataRequired()], default=0)



class EditInvoiceForm(FlaskForm):
    invoice_id = StringField('Invoice ID', validators=[DataRequired()])
    invoice_number = StringField('Invoice Number', validators=[DataRequired()])
    invoice_date = DateField('Invoice Date', validators=[DataRequired()])
    invoice_amount = DecimalField('Invoice Amount', validators=[DataRequired()])
    tax_rate = DecimalField('Tax Rate', validators=[DataRequired()])
    tax_amount = DecimalField('Tax Amount', validators=[DataRequired()])
    total_amount = DecimalField('Total Amount', validators=[DataRequired()])
    invoice_type = StringField('Invoice Type', validators=[DataRequired()])
    invoice_month = DateField('Invoice Month', validators=[DataRequired()])
    charge_date = DateField('Charge Date', validators=[DataRequired()])
    taxable_amount = DecimalField('Taxable Amount', validators=[DataRequired()])
    rounding_up = DecimalField('Rounding Up', validators=[DataRequired()])
    grand_total = DecimalField('Grand Total', validators=[DataRequired()])
    invoice_amount_in_words = StringField('Invoice Amount in Words', validators=[DataRequired()])

    submit = SubmitField('Save Changes')

class AddClientForm(FlaskForm):
    client_name = StringField('Client Name', validators=[DataRequired()])
    client_address = StringField('Client Address')
    client_gstin = StringField('Client GSTIN')
    client_email = StringField('Client Email')
    client_contact = StringField('Client Contact')
    issuer_id = SelectField('Issuer', coerce=str, validators=[DataRequired()])
    client_type = SelectField('Client Type', choices=[('TSP Model', 'TSP Model'), ('Program Manager Model', 'Program Manager Model')], validators=[DataRequired()])
    submit = SubmitField('Add Client')

    def __init__(self, *args, **kwargs):
        super(AddClientForm, self).__init__(*args, **kwargs)
        self.issuer_id.choices = [(i.issuer_id, i.issuer_name) for i in Issuer.query.all()]

class AddIssuerForm(FlaskForm):
    issuer_name = StringField('Issuer Name', validators=[DataRequired()])
    submit = SubmitField('Add Issuer')

class AddFeeForm(FlaskForm):
    fee_name = StringField('Fee Name', validators=[DataRequired()])
    fee_type = SelectField('Fee Type', choices=[('Static', 'Static'), ('Dynamic', 'Dynamic')], validators=[DataRequired()])
    fee_frequency = SelectField('Fee Frequency', choices=[('Monthly', 'Monthly'), ('Yearly', 'Yearly'), ('One-time', 'One-time')], validators=[DataRequired()])
    hsn_code = StringField('HSN Code')
    submit = SubmitField('Add Fee')

class AddProductForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    issuer_id = SelectField('Issuer', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Add Product')

    def __init__(self, *args, **kwargs):
        super(AddProductForm, self).__init__(*args, **kwargs)
        self.issuer_id.choices = [(i.issuer_id, i.issuer_name) for i in Issuer.query.all()]

class EditIssuerForm(FlaskForm):
    issuer_name = StringField('Issuer Name', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class EditFeeForm(FlaskForm):
    fee_name = StringField('Fee Name', validators=[DataRequired()])
    fee_type = SelectField('Fee Type', choices=[('Static', 'Static'), ('Dynamic', 'Dynamic')], validators=[DataRequired()])
    fee_frequency = SelectField('Fee Frequency', choices=[('Monthly', 'Monthly'), ('Yearly', 'Yearly'), ('One-time', 'One-time')], validators=[DataRequired()])
    hsn_code = StringField('HSN Code')
    submit = SubmitField('Save Changes')

class EditProductForm(FlaskForm):
    product_name = StringField('Product Name', validators=[DataRequired()])
    issuer_id = SelectField('Issuer', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Save Changes')

    def __init__(self, *args, **kwargs):
        super(EditProductForm, self).__init__(*args, **kwargs)
        self.issuer_id.choices = [(i.issuer_id, i.issuer_name) for i in Issuer.query.all()]

class DynamicFeeForm(FlaskForm):
    fee_id = SelectField('Fee', coerce=str, validators=[DataRequired()])
    units = IntegerField('Units', validators=[Optional()])
    amount = DecimalField('Amount', validators=[Optional()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(DynamicFeeForm, self).__init__(*args, **kwargs)
        self.fee_id.choices = [(f.fee_id, f.fee_name) for f in FeeMaster.query.filter_by(is_dynamic=True).all()]

class InterchangeFeeForm(FlaskForm):
    interchange_amt = DecimalField('Interchange Amount', validators=[Optional()])
    minimum_interchange = DecimalField('Minimum Interchange', validators=[Optional()])
    interchange_percentage = DecimalField('Interchange Share Percentage', validators=[Optional()])
    submit = SubmitField('Submit')

class ClientProductFeeMappingForm(FlaskForm):
    client_id = SelectField('Client', coerce=str, validators=[DataRequired()])
    product_id = SelectField('Product', coerce=str, validators=[DataRequired()])
    fee_id = SelectField('Fee', coerce=str, validators=[DataRequired()])
    unit_price = DecimalField('Unit Price', validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Save Mapping')

    def __init__(self, *args, **kwargs):
        super(ClientProductFeeMappingForm, self).__init__(*args, **kwargs)
        self.client_id.choices = [(c.client_id, c.client_name) for c in Client.query.all()]
        self.product_id.choices = [(p.product_id, p.product_name) for p in Product.query.all()]
        self.fee_id.choices = [(f.fee_id, f.fee_name) for f in FeeMaster.query.all()]   