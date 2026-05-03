DO
$$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'data_agent') THEN
        CREATE ROLE data_agent WITH LOGIN PASSWORD 'data_agent';
    ELSE
        ALTER ROLE data_agent WITH LOGIN PASSWORD 'data_agent';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO data_agent;
GRANT TEMP ON DATABASE postgres TO data_agent;
GRANT CREATE ON DATABASE postgres TO data_agent;
GRANT USAGE, CREATE ON SCHEMA public TO data_agent;
