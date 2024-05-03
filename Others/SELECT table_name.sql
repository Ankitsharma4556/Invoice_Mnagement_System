SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE';

Select * from interchange_fees;

DELETE FROM interchange_fees WHERE client_id = 'CLI000001';

Select * from invoice_line_items;

DELETE FROM invoice_line_items WHERE line_item_id BETWEEN 205 AND 225;


SELECT * from fee_history;

DELETE FROM fee_history WHERE units BETWEEN 1 AND 400;

Select * from fee_master;

SELECT * from invoices;

DELETE FROM invoices WHERE biller_id = 'BIL000001';

SELECT * from client_product_fee_mapping;


UPDATE client_product_fee_mapping
SET unit_price = 0.00
WHERE unit_price = 0.01;
k
ALTER TABLE interchange_fees ADD COLUMN charge_date DATE;

ALTER TABLE invoice_line_items ADD COLUMN description TEXT;



