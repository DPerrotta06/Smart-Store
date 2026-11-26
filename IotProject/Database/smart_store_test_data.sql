-- Test Data for Smart Store Checkout System

-- 1. Insert Mock Products
-- (Includes the '0000000000000000004926' EPC you successfully scanned earlier in the terminal)
INSERT INTO Product (category, price, epc, producer_company, upc, name) VALUES
('Beverage', 1.50, '000000000000000000000001', 'Coca Cola', '123456789012', 'Coca Cola 330ml'),
('Snacks', 2.00, '000000000000000000000002', 'Frito-Lay', '123456789013', 'Lays Classic Chips'),
('Beverage', 2.50, '000000000000000000000003', 'Glaceau', '123456789014', 'Smart Water 1L'),
('Electronics', 15.99, '0000000000000000004926', 'Anker', '123456789015', 'USB-C Charging Cable');

-- 2. Insert a Mock Customer (to test the receipt email flow)
-- Note: Replace 'registered@gmail.com' with your actual testing email to see the receipt arrive in your inbox!
INSERT INTO Customer (last_name, first_name, tel_number, email, customer_address, customer_uuid, points, password) VALUES
('Doe', 'John', '555-555-5555', 'registered@gmail.com', '123 Test St, Montreal, QC', '11112222-3333-4444-5555-666677778888', 0, 'mock_password_hash_123');
