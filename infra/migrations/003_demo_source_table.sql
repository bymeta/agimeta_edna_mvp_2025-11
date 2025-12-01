-- Demo Source Table for Customer Data
CREATE TABLE IF NOT EXISTS demo_customers (
    customer_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255),
    phone VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert sample demo data if table is empty
INSERT INTO demo_customers (customer_id, email, phone, first_name, last_name, company, status)
SELECT * FROM (VALUES
    ('CUST-001', 'alice.smith@example.com', '555-123-4567', 'Alice', 'Smith', 'Acme Corp', 'active'),
    ('CUST-002', 'bob.johnson@test.com', '555-234-5678', 'Bob', 'Johnson', 'Tech Solutions', 'active'),
    ('CUST-003', 'charlie.williams@demo.org', '555-345-6789', 'Charlie', 'Williams', 'Global Industries', 'inactive'),
    ('CUST-004', 'diana.brown@sample.net', '555-456-7890', 'Diana', 'Brown', 'Digital Services', 'active'),
    ('CUST-005', 'eve.jones@example.com', '555-567-8901', 'Eve', 'Jones', 'Innovation Labs', 'pending')
) AS v(customer_id, email, phone, first_name, last_name, company, status)
WHERE NOT EXISTS (SELECT 1 FROM demo_customers LIMIT 1);

CREATE INDEX IF NOT EXISTS idx_demo_customers_email ON demo_customers(email);
CREATE INDEX IF NOT EXISTS idx_demo_customers_phone ON demo_customers(phone);

