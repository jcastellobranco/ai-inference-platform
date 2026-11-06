-- Local development fixtures; run as migration owner.
INSERT INTO tenants(id,name) VALUES
('11111111-1111-4111-8111-111111111111','Acme Demo'),
('22222222-2222-4222-8222-222222222222','Beta Demo')
ON CONFLICT(id) DO NOTHING;
