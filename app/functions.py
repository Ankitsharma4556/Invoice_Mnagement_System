from datetime import datetime
from models import db
from models import Client, ClientProductFeeMapping, FeeMaster, InterchangeFee, InvoiceLineItem, FeeHistory
from flask import request
from decimal import Decimal
from sqlalchemy import extract

def calculate_interchange_line_item(client_id, start_date, end_date, interchange_share_percentage):
    interchange_fee = InterchangeFee.query.filter_by(
        client_id=client_id,
        start_date=start_date,
        end_date=end_date
    ).order_by(InterchangeFee.charge_date.desc()).first()

    if interchange_fee:
        interchange_amt = interchange_fee.interchange_amt
        minimum_interchange = interchange_fee.minimum_interchange

        if interchange_amt == 0 and minimum_interchange == 0:
            return None

        higher_value = max(interchange_amt, minimum_interchange)

        if higher_value == interchange_amt:
            interchange_amount_ex_gst = interchange_amt / Decimal('1.18')
            client_share = interchange_amount_ex_gst * (Decimal(interchange_share_percentage) / 100)
            gst_amount = client_share * Decimal('0.18')
            final_amount = client_share + gst_amount
        else:
            client_share = minimum_interchange
            gst_amount = client_share * Decimal('0.18')
            final_amount = client_share + gst_amount

        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        description = f"Interchange Fee ({end_date_obj.strftime('%B %Y')})"

        line_item = InvoiceLineItem(
            fee_id=None,    
            units=1,
            unit_price=final_amount,
            total=final_amount,
            gst_amount=gst_amount,
            final_amount=final_amount,
            description=description
        )

        return line_item
    return None

def generate_invoice_line_items(client_id, start_date, end_date, applicable_fees, form_data, interchange_line_item):
    client = Client.query.get(client_id)
    line_items = []

    if interchange_line_item:
        line_items.append(interchange_line_item)

    for fee in applicable_fees:
        units = request.form.get(f'units_{fee.fee_id}', 1)
        units = int(units) if units else 0

        if units == 0:
            continue

        mapping = ClientProductFeeMapping.query.filter_by(
            client_id=client.client_id,
            fee_id=fee.fee_id
        ).first()

        if mapping:
            fee_amount = mapping.unit_price * units
            gst_amount = fee_amount * Decimal('0.18')
            final_amount = fee_amount + gst_amount

            line_item = InvoiceLineItem(
                invoice=None,  # Set invoice to None initially
                fee=fee,
                units=units,
                unit_price=mapping.unit_price,
                total=fee_amount,
                gst_amount=gst_amount,
                final_amount=final_amount
            )
            line_items.append(line_item)

            fee_history = FeeHistory(
                fee_history_id=generate_fee_history_id(),
                client_id=client.client_id,
                issuer_id=client.issuer_id,
                fee_id=fee.fee_id,
                charge_date=start_date,
                units=units,
                total=fee_amount
            )
            db.session.add(fee_history)

    return line_items

def get_applicable_fees(client_id, start_date, end_date, exclude_interchange=False):
    mappings = ClientProductFeeMapping.query.filter(
        ClientProductFeeMapping.client_id == client_id,
        ClientProductFeeMapping.start_date <= end_date,
        ClientProductFeeMapping.end_date >= start_date
    ).all()
    applicable_fees = []

    for mapping in mappings:
        fee = FeeMaster.query.get(mapping.fee_id)

        if fee.fee_name.lower() == 'interchange' and exclude_interchange:
            continue
        elif fee.fee_frequency == 'One-time' and fee_already_charged(client_id, fee.fee_id):
            continue
        elif fee.fee_frequency == 'Yearly' and fee_already_charged_yearly(client_id, fee.fee_id, start_date):
            continue
        elif fee.fee_frequency == 'Monthly':
            if not fee_already_charged_monthly(client_id, fee.fee_id, start_date):
                applicable_fees.append(fee)
        else:
            applicable_fees.append(fee)

    return applicable_fees

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
        extract('year', FeeHistory.charge_date) == start_date.year
    ).first()

    return fee_history is not None

def fee_already_charged_monthly(client_id, fee_id, start_date):
    fee_history = FeeHistory.query.filter(
        FeeHistory.client_id == client_id,
        FeeHistory.fee_id == fee_id,
        extract('year', FeeHistory.charge_date) == start_date.year,
        extract('month', FeeHistory.charge_date) == start_date.month
    ).first()

    return fee_history is not None

def generate_fee_history_id():
    return f'FEEHIST-{datetime.now().strftime("%Y%m%d")}-{FeeHistory.query.count() + 1}'