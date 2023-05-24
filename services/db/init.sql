-- Create database
CREATE DATABASE synthetix;

-- Create roles
CREATE ROLE admin NOLOGIN;
CREATE ROLE user_read_only;

-- Grant privileges to the roles on the database
GRANT ALL PRIVILEGES ON DATABASE synthetix TO admin;
GRANT CONNECT ON DATABASE synthetix TO user_read_only;
GRANT USAGE ON SCHEMA public TO user_read_only;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO user_read_only;

-- Future permissions
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO user_read_only;

