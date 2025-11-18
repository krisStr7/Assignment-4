CREATE TABLE IF NOT EXISTS app_user (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','viewer'))
);

CREATE INDEX IF NOT EXISTS idx_employee_name ON Employee(Lname, Fname);
CREATE INDEX IF NOT EXISTS idx_workson_pno ON Works_On(Pno);
-- Default admin user (created for testing and TA login)
INSERT INTO app_user (username, password_hash, role)
VALUES (
    'admin',
    'scrypt:32768:8:1$wqpqG8hGeUSQ2QIX$01fc7355ea776eab4bbcaa7e7135a518c52f70940b7b17fd4fc02808f94f158c95a2ab7bccce139b2d4e2805c87559e148d8c41d23baee2064d128b2af709a3e',
    'admin'
)
ON CONFLICT (username) DO NOTHING;

