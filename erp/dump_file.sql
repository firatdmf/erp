--
-- PostgreSQL database dump
--

-- Dumped from database version 15.6
-- Dumped by pg_dump version 15.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: auth; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA auth;


ALTER SCHEMA auth OWNER TO supabase_admin;

--
-- Name: extensions; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA extensions;


ALTER SCHEMA extensions OWNER TO postgres;

--
-- Name: graphql; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA graphql;


ALTER SCHEMA graphql OWNER TO supabase_admin;

--
-- Name: graphql_public; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA graphql_public;


ALTER SCHEMA graphql_public OWNER TO supabase_admin;

--
-- Name: pgbouncer; Type: SCHEMA; Schema: -; Owner: pgbouncer
--

CREATE SCHEMA pgbouncer;


ALTER SCHEMA pgbouncer OWNER TO pgbouncer;

--
-- Name: pgsodium; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA pgsodium;


ALTER SCHEMA pgsodium OWNER TO supabase_admin;

--
-- Name: pgsodium; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgsodium WITH SCHEMA pgsodium;


--
-- Name: EXTENSION pgsodium; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgsodium IS 'Pgsodium is a modern cryptography library for Postgres.';


--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- Name: realtime; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA realtime;


ALTER SCHEMA realtime OWNER TO supabase_admin;

--
-- Name: storage; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA storage;


ALTER SCHEMA storage OWNER TO supabase_admin;

--
-- Name: vault; Type: SCHEMA; Schema: -; Owner: supabase_admin
--

CREATE SCHEMA vault;


ALTER SCHEMA vault OWNER TO supabase_admin;

--
-- Name: pg_graphql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_graphql WITH SCHEMA graphql;


--
-- Name: EXTENSION pg_graphql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_graphql IS 'pg_graphql: GraphQL support';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA extensions;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: pgjwt; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgjwt WITH SCHEMA extensions;


--
-- Name: EXTENSION pgjwt; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgjwt IS 'JSON Web Token API for Postgresql';


--
-- Name: supabase_vault; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;


--
-- Name: EXTENSION supabase_vault; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION supabase_vault IS 'Supabase Vault Extension';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA extensions;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aal_level; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.aal_level AS ENUM (
    'aal1',
    'aal2',
    'aal3'
);


ALTER TYPE auth.aal_level OWNER TO supabase_auth_admin;

--
-- Name: code_challenge_method; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.code_challenge_method AS ENUM (
    's256',
    'plain'
);


ALTER TYPE auth.code_challenge_method OWNER TO supabase_auth_admin;

--
-- Name: factor_status; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.factor_status AS ENUM (
    'unverified',
    'verified'
);


ALTER TYPE auth.factor_status OWNER TO supabase_auth_admin;

--
-- Name: factor_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.factor_type AS ENUM (
    'totp',
    'webauthn',
    'phone'
);


ALTER TYPE auth.factor_type OWNER TO supabase_auth_admin;

--
-- Name: one_time_token_type; Type: TYPE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TYPE auth.one_time_token_type AS ENUM (
    'confirmation_token',
    'reauthentication_token',
    'recovery_token',
    'email_change_token_new',
    'email_change_token_current',
    'phone_change_token'
);


ALTER TYPE auth.one_time_token_type OWNER TO supabase_auth_admin;

--
-- Name: action; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.action AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'TRUNCATE',
    'ERROR'
);


ALTER TYPE realtime.action OWNER TO supabase_admin;

--
-- Name: equality_op; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.equality_op AS ENUM (
    'eq',
    'neq',
    'lt',
    'lte',
    'gt',
    'gte',
    'in'
);


ALTER TYPE realtime.equality_op OWNER TO supabase_admin;

--
-- Name: user_defined_filter; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.user_defined_filter AS (
	column_name text,
	op realtime.equality_op,
	value text
);


ALTER TYPE realtime.user_defined_filter OWNER TO supabase_admin;

--
-- Name: wal_column; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.wal_column AS (
	name text,
	type_name text,
	type_oid oid,
	value jsonb,
	is_pkey boolean,
	is_selectable boolean
);


ALTER TYPE realtime.wal_column OWNER TO supabase_admin;

--
-- Name: wal_rls; Type: TYPE; Schema: realtime; Owner: supabase_admin
--

CREATE TYPE realtime.wal_rls AS (
	wal jsonb,
	is_rls_enabled boolean,
	subscription_ids uuid[],
	errors text[]
);


ALTER TYPE realtime.wal_rls OWNER TO supabase_admin;

--
-- Name: email(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.email() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$$;


ALTER FUNCTION auth.email() OWNER TO supabase_auth_admin;

--
-- Name: FUNCTION email(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.email() IS 'Deprecated. Use auth.jwt() -> ''email'' instead.';


--
-- Name: jwt(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.jwt() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$$;


ALTER FUNCTION auth.jwt() OWNER TO supabase_auth_admin;

--
-- Name: role(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.role() RETURNS text
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$$;


ALTER FUNCTION auth.role() OWNER TO supabase_auth_admin;

--
-- Name: FUNCTION role(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.role() IS 'Deprecated. Use auth.jwt() -> ''role'' instead.';


--
-- Name: uid(); Type: FUNCTION; Schema: auth; Owner: supabase_auth_admin
--

CREATE FUNCTION auth.uid() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$$;


ALTER FUNCTION auth.uid() OWNER TO supabase_auth_admin;

--
-- Name: FUNCTION uid(); Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON FUNCTION auth.uid() IS 'Deprecated. Use auth.jwt() -> ''sub'' instead.';


--
-- Name: grant_pg_cron_access(); Type: FUNCTION; Schema: extensions; Owner: postgres
--

CREATE FUNCTION extensions.grant_pg_cron_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_cron'
  )
  THEN
    grant usage on schema cron to postgres with grant option;

    alter default privileges in schema cron grant all on tables to postgres with grant option;
    alter default privileges in schema cron grant all on functions to postgres with grant option;
    alter default privileges in schema cron grant all on sequences to postgres with grant option;

    alter default privileges for user supabase_admin in schema cron grant all
        on sequences to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on tables to postgres with grant option;
    alter default privileges for user supabase_admin in schema cron grant all
        on functions to postgres with grant option;

    grant all privileges on all tables in schema cron to postgres with grant option;
    revoke all on table cron.job from postgres;
    grant select on table cron.job to postgres with grant option;
  END IF;
END;
$$;


ALTER FUNCTION extensions.grant_pg_cron_access() OWNER TO postgres;

--
-- Name: FUNCTION grant_pg_cron_access(); Type: COMMENT; Schema: extensions; Owner: postgres
--

COMMENT ON FUNCTION extensions.grant_pg_cron_access() IS 'Grants access to pg_cron';


--
-- Name: grant_pg_graphql_access(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.grant_pg_graphql_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    func_is_graphql_resolve bool;
BEGIN
    func_is_graphql_resolve = (
        SELECT n.proname = 'resolve'
        FROM pg_event_trigger_ddl_commands() AS ev
        LEFT JOIN pg_catalog.pg_proc AS n
        ON ev.objid = n.oid
    );

    IF func_is_graphql_resolve
    THEN
        -- Update public wrapper to pass all arguments through to the pg_graphql resolve func
        DROP FUNCTION IF EXISTS graphql_public.graphql;
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language sql
        as $$
            select graphql.resolve(
                query := query,
                variables := coalesce(variables, '{}'),
                "operationName" := "operationName",
                extensions := extensions
            );
        $$;

        -- This hook executes when `graphql.resolve` is created. That is not necessarily the last
        -- function in the extension so we need to grant permissions on existing entities AND
        -- update default permissions to any others that are created after `graphql.resolve`
        grant usage on schema graphql to postgres, anon, authenticated, service_role;
        grant select on all tables in schema graphql to postgres, anon, authenticated, service_role;
        grant execute on all functions in schema graphql to postgres, anon, authenticated, service_role;
        grant all on all sequences in schema graphql to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on tables to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on functions to postgres, anon, authenticated, service_role;
        alter default privileges in schema graphql grant all on sequences to postgres, anon, authenticated, service_role;

        -- Allow postgres role to allow granting usage on graphql and graphql_public schemas to custom roles
        grant usage on schema graphql_public to postgres with grant option;
        grant usage on schema graphql to postgres with grant option;
    END IF;

END;
$_$;


ALTER FUNCTION extensions.grant_pg_graphql_access() OWNER TO supabase_admin;

--
-- Name: FUNCTION grant_pg_graphql_access(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION extensions.grant_pg_graphql_access() IS 'Grants access to pg_graphql';


--
-- Name: grant_pg_net_access(); Type: FUNCTION; Schema: extensions; Owner: postgres
--

CREATE FUNCTION extensions.grant_pg_net_access() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_event_trigger_ddl_commands() AS ev
    JOIN pg_extension AS ext
    ON ev.objid = ext.oid
    WHERE ext.extname = 'pg_net'
  )
  THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_roles
      WHERE rolname = 'supabase_functions_admin'
    )
    THEN
      CREATE USER supabase_functions_admin NOINHERIT CREATEROLE LOGIN NOREPLICATION;
    END IF;

    GRANT USAGE ON SCHEMA net TO supabase_functions_admin, postgres, anon, authenticated, service_role;

    ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
    ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

    ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
    ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

    REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
    REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

    GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
    GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
  END IF;
END;
$$;


ALTER FUNCTION extensions.grant_pg_net_access() OWNER TO postgres;

--
-- Name: FUNCTION grant_pg_net_access(); Type: COMMENT; Schema: extensions; Owner: postgres
--

COMMENT ON FUNCTION extensions.grant_pg_net_access() IS 'Grants access to pg_net';


--
-- Name: pgrst_ddl_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.pgrst_ddl_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN SELECT * FROM pg_event_trigger_ddl_commands()
  LOOP
    IF cmd.command_tag IN (
      'CREATE SCHEMA', 'ALTER SCHEMA'
    , 'CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO', 'ALTER TABLE'
    , 'CREATE FOREIGN TABLE', 'ALTER FOREIGN TABLE'
    , 'CREATE VIEW', 'ALTER VIEW'
    , 'CREATE MATERIALIZED VIEW', 'ALTER MATERIALIZED VIEW'
    , 'CREATE FUNCTION', 'ALTER FUNCTION'
    , 'CREATE TRIGGER'
    , 'CREATE TYPE', 'ALTER TYPE'
    , 'CREATE RULE'
    , 'COMMENT'
    )
    -- don't notify in case of CREATE TEMP table or other objects created on pg_temp
    AND cmd.schema_name is distinct from 'pg_temp'
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


ALTER FUNCTION extensions.pgrst_ddl_watch() OWNER TO supabase_admin;

--
-- Name: pgrst_drop_watch(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.pgrst_drop_watch() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  obj record;
BEGIN
  FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects()
  LOOP
    IF obj.object_type IN (
      'schema'
    , 'table'
    , 'foreign table'
    , 'view'
    , 'materialized view'
    , 'function'
    , 'trigger'
    , 'type'
    , 'rule'
    )
    AND obj.is_temporary IS false -- no pg_temp objects
    THEN
      NOTIFY pgrst, 'reload schema';
    END IF;
  END LOOP;
END; $$;


ALTER FUNCTION extensions.pgrst_drop_watch() OWNER TO supabase_admin;

--
-- Name: set_graphql_placeholder(); Type: FUNCTION; Schema: extensions; Owner: supabase_admin
--

CREATE FUNCTION extensions.set_graphql_placeholder() RETURNS event_trigger
    LANGUAGE plpgsql
    AS $_$
    DECLARE
    graphql_is_dropped bool;
    BEGIN
    graphql_is_dropped = (
        SELECT ev.schema_name = 'graphql_public'
        FROM pg_event_trigger_dropped_objects() AS ev
        WHERE ev.schema_name = 'graphql_public'
    );

    IF graphql_is_dropped
    THEN
        create or replace function graphql_public.graphql(
            "operationName" text default null,
            query text default null,
            variables jsonb default null,
            extensions jsonb default null
        )
            returns jsonb
            language plpgsql
        as $$
            DECLARE
                server_version float;
            BEGIN
                server_version = (SELECT (SPLIT_PART((select version()), ' ', 2))::float);

                IF server_version >= 14 THEN
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql extension is not enabled.'
                            )
                        )
                    );
                ELSE
                    RETURN jsonb_build_object(
                        'errors', jsonb_build_array(
                            jsonb_build_object(
                                'message', 'pg_graphql is only available on projects running Postgres 14 onwards.'
                            )
                        )
                    );
                END IF;
            END;
        $$;
    END IF;

    END;
$_$;


ALTER FUNCTION extensions.set_graphql_placeholder() OWNER TO supabase_admin;

--
-- Name: FUNCTION set_graphql_placeholder(); Type: COMMENT; Schema: extensions; Owner: supabase_admin
--

COMMENT ON FUNCTION extensions.set_graphql_placeholder() IS 'Reintroduces placeholder function for graphql_public.graphql';


--
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: postgres
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RAISE WARNING 'PgBouncer auth request: %', p_usename;

    RETURN QUERY
    SELECT usename::TEXT, passwd::TEXT FROM pg_catalog.pg_shadow
    WHERE usename = p_usename;
END;
$$;


ALTER FUNCTION pgbouncer.get_auth(p_usename text) OWNER TO postgres;

--
-- Name: apply_rls(jsonb, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer DEFAULT (1024 * 1024)) RETURNS SETOF realtime.wal_rls
    LANGUAGE plpgsql
    AS $$
declare
-- Regclass of the table e.g. public.notes
entity_ regclass = (quote_ident(wal ->> 'schema') || '.' || quote_ident(wal ->> 'table'))::regclass;

-- I, U, D, T: insert, update ...
action realtime.action = (
    case wal ->> 'action'
        when 'I' then 'INSERT'
        when 'U' then 'UPDATE'
        when 'D' then 'DELETE'
        else 'ERROR'
    end
);

-- Is row level security enabled for the table
is_rls_enabled bool = relrowsecurity from pg_class where oid = entity_;

subscriptions realtime.subscription[] = array_agg(subs)
    from
        realtime.subscription subs
    where
        subs.entity = entity_;

-- Subscription vars
roles regrole[] = array_agg(distinct us.claims_role::text)
    from
        unnest(subscriptions) us;

working_role regrole;
claimed_role regrole;
claims jsonb;

subscription_id uuid;
subscription_has_access bool;
visible_to_subscription_ids uuid[] = '{}';

-- structured info for wal's columns
columns realtime.wal_column[];
-- previous identity values for update/delete
old_columns realtime.wal_column[];

error_record_exceeds_max_size boolean = octet_length(wal::text) > max_record_bytes;

-- Primary jsonb output for record
output jsonb;

begin
perform set_config('role', null, true);

columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'columns') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

old_columns =
    array_agg(
        (
            x->>'name',
            x->>'type',
            x->>'typeoid',
            realtime.cast(
                (x->'value') #>> '{}',
                coalesce(
                    (x->>'typeoid')::regtype, -- null when wal2json version <= 2.4
                    (x->>'type')::regtype
                )
            ),
            (pks ->> 'name') is not null,
            true
        )::realtime.wal_column
    )
    from
        jsonb_array_elements(wal -> 'identity') x
        left join jsonb_array_elements(wal -> 'pk') pks
            on (x ->> 'name') = (pks ->> 'name');

for working_role in select * from unnest(roles) loop

    -- Update `is_selectable` for columns and old_columns
    columns =
        array_agg(
            (
                c.name,
                c.type_name,
                c.type_oid,
                c.value,
                c.is_pkey,
                pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
            )::realtime.wal_column
        )
        from
            unnest(columns) c;

    old_columns =
            array_agg(
                (
                    c.name,
                    c.type_name,
                    c.type_oid,
                    c.value,
                    c.is_pkey,
                    pg_catalog.has_column_privilege(working_role, entity_, c.name, 'SELECT')
                )::realtime.wal_column
            )
            from
                unnest(old_columns) c;

    if action <> 'DELETE' and count(1) = 0 from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            -- subscriptions is already filtered by entity
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 400: Bad Request, no primary key']
        )::realtime.wal_rls;

    -- The claims role does not have SELECT permission to the primary key of entity
    elsif action <> 'DELETE' and sum(c.is_selectable::int) <> count(1) from unnest(columns) c where c.is_pkey then
        return next (
            jsonb_build_object(
                'schema', wal ->> 'schema',
                'table', wal ->> 'table',
                'type', action
            ),
            is_rls_enabled,
            (select array_agg(s.subscription_id) from unnest(subscriptions) as s where claims_role = working_role),
            array['Error 401: Unauthorized']
        )::realtime.wal_rls;

    else
        output = jsonb_build_object(
            'schema', wal ->> 'schema',
            'table', wal ->> 'table',
            'type', action,
            'commit_timestamp', to_char(
                ((wal ->> 'timestamp')::timestamptz at time zone 'utc'),
                'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'
            ),
            'columns', (
                select
                    jsonb_agg(
                        jsonb_build_object(
                            'name', pa.attname,
                            'type', pt.typname
                        )
                        order by pa.attnum asc
                    )
                from
                    pg_attribute pa
                    join pg_type pt
                        on pa.atttypid = pt.oid
                where
                    attrelid = entity_
                    and attnum > 0
                    and pg_catalog.has_column_privilege(working_role, entity_, pa.attname, 'SELECT')
            )
        )
        -- Add "record" key for insert and update
        || case
            when action in ('INSERT', 'UPDATE') then
                jsonb_build_object(
                    'record',
                    (
                        select
                            jsonb_object_agg(
                                -- if unchanged toast, get column name and value from old record
                                coalesce((c).name, (oc).name),
                                case
                                    when (c).name is null then (oc).value
                                    else (c).value
                                end
                            )
                        from
                            unnest(columns) c
                            full outer join unnest(old_columns) oc
                                on (c).name = (oc).name
                        where
                            coalesce((c).is_selectable, (oc).is_selectable)
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                    )
                )
            else '{}'::jsonb
        end
        -- Add "old_record" key for update and delete
        || case
            when action = 'UPDATE' then
                jsonb_build_object(
                        'old_record',
                        (
                            select jsonb_object_agg((c).name, (c).value)
                            from unnest(old_columns) c
                            where
                                (c).is_selectable
                                and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                        )
                    )
            when action = 'DELETE' then
                jsonb_build_object(
                    'old_record',
                    (
                        select jsonb_object_agg((c).name, (c).value)
                        from unnest(old_columns) c
                        where
                            (c).is_selectable
                            and ( not error_record_exceeds_max_size or (octet_length((c).value::text) <= 64))
                            and ( not is_rls_enabled or (c).is_pkey ) -- if RLS enabled, we can't secure deletes so filter to pkey
                    )
                )
            else '{}'::jsonb
        end;

        -- Create the prepared statement
        if is_rls_enabled and action <> 'DELETE' then
            if (select 1 from pg_prepared_statements where name = 'walrus_rls_stmt' limit 1) > 0 then
                deallocate walrus_rls_stmt;
            end if;
            execute realtime.build_prepared_statement_sql('walrus_rls_stmt', entity_, columns);
        end if;

        visible_to_subscription_ids = '{}';

        for subscription_id, claims in (
                select
                    subs.subscription_id,
                    subs.claims
                from
                    unnest(subscriptions) subs
                where
                    subs.entity = entity_
                    and subs.claims_role = working_role
                    and (
                        realtime.is_visible_through_filters(columns, subs.filters)
                        or (
                          action = 'DELETE'
                          and realtime.is_visible_through_filters(old_columns, subs.filters)
                        )
                    )
        ) loop

            if not is_rls_enabled or action = 'DELETE' then
                visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
            else
                -- Check if RLS allows the role to see the record
                perform
                    -- Trim leading and trailing quotes from working_role because set_config
                    -- doesn't recognize the role as valid if they are included
                    set_config('role', trim(both '"' from working_role::text), true),
                    set_config('request.jwt.claims', claims::text, true);

                execute 'execute walrus_rls_stmt' into subscription_has_access;

                if subscription_has_access then
                    visible_to_subscription_ids = visible_to_subscription_ids || subscription_id;
                end if;
            end if;
        end loop;

        perform set_config('role', null, true);

        return next (
            output,
            is_rls_enabled,
            visible_to_subscription_ids,
            case
                when error_record_exceeds_max_size then array['Error 413: Payload Too Large']
                else '{}'
            end
        )::realtime.wal_rls;

    end if;
end loop;

perform set_config('role', null, true);
end;
$$;


ALTER FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) OWNER TO supabase_admin;

--
-- Name: broadcast_changes(text, text, text, text, text, record, record, text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text DEFAULT 'ROW'::text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    -- Declare a variable to hold the JSONB representation of the row
    row_data jsonb := '{}'::jsonb;
BEGIN
    IF level = 'STATEMENT' THEN
        RAISE EXCEPTION 'function can only be triggered for each row, not for each statement';
    END IF;
    -- Check the operation type and handle accordingly
    IF operation = 'INSERT' OR operation = 'UPDATE' OR operation = 'DELETE' THEN
        row_data := jsonb_build_object('old_record', OLD, 'record', NEW, 'operation', operation, 'table', table_name, 'schema', table_schema);
        PERFORM realtime.send (row_data, event_name, topic_name);
    ELSE
        RAISE EXCEPTION 'Unexpected operation type: %', operation;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Failed to process the row: %', SQLERRM;
END;

$$;


ALTER FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) OWNER TO supabase_admin;

--
-- Name: build_prepared_statement_sql(text, regclass, realtime.wal_column[]); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) RETURNS text
    LANGUAGE sql
    AS $$
      /*
      Builds a sql string that, if executed, creates a prepared statement to
      tests retrive a row from *entity* by its primary key columns.
      Example
          select realtime.build_prepared_statement_sql('public.notes', '{"id"}'::text[], '{"bigint"}'::text[])
      */
          select
      'prepare ' || prepared_statement_name || ' as
          select
              exists(
                  select
                      1
                  from
                      ' || entity || '
                  where
                      ' || string_agg(quote_ident(pkc.name) || '=' || quote_nullable(pkc.value #>> '{}') , ' and ') || '
              )'
          from
              unnest(columns) pkc
          where
              pkc.is_pkey
          group by
              entity
      $$;


ALTER FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) OWNER TO supabase_admin;

--
-- Name: cast(text, regtype); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime."cast"(val text, type_ regtype) RETURNS jsonb
    LANGUAGE plpgsql IMMUTABLE
    AS $$
    declare
      res jsonb;
    begin
      execute format('select to_jsonb(%L::'|| type_::text || ')', val)  into res;
      return res;
    end
    $$;


ALTER FUNCTION realtime."cast"(val text, type_ regtype) OWNER TO supabase_admin;

--
-- Name: check_equality_op(realtime.equality_op, regtype, text, text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) RETURNS boolean
    LANGUAGE plpgsql IMMUTABLE
    AS $$
      /*
      Casts *val_1* and *val_2* as type *type_* and check the *op* condition for truthiness
      */
      declare
          op_symbol text = (
              case
                  when op = 'eq' then '='
                  when op = 'neq' then '!='
                  when op = 'lt' then '<'
                  when op = 'lte' then '<='
                  when op = 'gt' then '>'
                  when op = 'gte' then '>='
                  when op = 'in' then '= any'
                  else 'UNKNOWN OP'
              end
          );
          res boolean;
      begin
          execute format(
              'select %L::'|| type_::text || ' ' || op_symbol
              || ' ( %L::'
              || (
                  case
                      when op = 'in' then type_::text || '[]'
                      else type_::text end
              )
              || ')', val_1, val_2) into res;
          return res;
      end;
      $$;


ALTER FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) OWNER TO supabase_admin;

--
-- Name: is_visible_through_filters(realtime.wal_column[], realtime.user_defined_filter[]); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
    /*
    Should the record be visible (true) or filtered out (false) after *filters* are applied
    */
        select
            -- Default to allowed when no filters present
            $2 is null -- no filters. this should not happen because subscriptions has a default
            or array_length($2, 1) is null -- array length of an empty array is null
            or bool_and(
                coalesce(
                    realtime.check_equality_op(
                        op:=f.op,
                        type_:=coalesce(
                            col.type_oid::regtype, -- null when wal2json version <= 2.4
                            col.type_name::regtype
                        ),
                        -- cast jsonb to text
                        val_1:=col.value #>> '{}',
                        val_2:=f.value
                    ),
                    false -- if null, filter does not match
                )
            )
        from
            unnest(filters) f
            join unnest(columns) col
                on f.column_name = col.name;
    $_$;


ALTER FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) OWNER TO supabase_admin;

--
-- Name: list_changes(name, name, integer, integer); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) RETURNS SETOF realtime.wal_rls
    LANGUAGE sql
    SET log_min_messages TO 'fatal'
    AS $$
      with pub as (
        select
          concat_ws(
            ',',
            case when bool_or(pubinsert) then 'insert' else null end,
            case when bool_or(pubupdate) then 'update' else null end,
            case when bool_or(pubdelete) then 'delete' else null end
          ) as w2j_actions,
          coalesce(
            string_agg(
              realtime.quote_wal2json(format('%I.%I', schemaname, tablename)::regclass),
              ','
            ) filter (where ppt.tablename is not null and ppt.tablename not like '% %'),
            ''
          ) w2j_add_tables
        from
          pg_publication pp
          left join pg_publication_tables ppt
            on pp.pubname = ppt.pubname
        where
          pp.pubname = publication
        group by
          pp.pubname
        limit 1
      ),
      w2j as (
        select
          x.*, pub.w2j_add_tables
        from
          pub,
          pg_logical_slot_get_changes(
            slot_name, null, max_changes,
            'include-pk', 'true',
            'include-transaction', 'false',
            'include-timestamp', 'true',
            'include-type-oids', 'true',
            'format-version', '2',
            'actions', pub.w2j_actions,
            'add-tables', pub.w2j_add_tables
          ) x
      )
      select
        xyz.wal,
        xyz.is_rls_enabled,
        xyz.subscription_ids,
        xyz.errors
      from
        w2j,
        realtime.apply_rls(
          wal := w2j.data::jsonb,
          max_record_bytes := max_record_bytes
        ) xyz(wal, is_rls_enabled, subscription_ids, errors)
      where
        w2j.w2j_add_tables <> ''
        and xyz.subscription_ids[1] is not null
    $$;


ALTER FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) OWNER TO supabase_admin;

--
-- Name: quote_wal2json(regclass); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.quote_wal2json(entity regclass) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
      select
        (
          select string_agg('' || ch,'')
          from unnest(string_to_array(nsp.nspname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
        )
        || '.'
        || (
          select string_agg('' || ch,'')
          from unnest(string_to_array(pc.relname::text, null)) with ordinality x(ch, idx)
          where
            not (x.idx = 1 and x.ch = '"')
            and not (
              x.idx = array_length(string_to_array(nsp.nspname::text, null), 1)
              and x.ch = '"'
            )
          )
      from
        pg_class pc
        join pg_namespace nsp
          on pc.relnamespace = nsp.oid
      where
        pc.oid = entity
    $$;


ALTER FUNCTION realtime.quote_wal2json(entity regclass) OWNER TO supabase_admin;

--
-- Name: send(jsonb, text, text, boolean); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean DEFAULT true) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  partition_name text;
BEGIN
  partition_name := 'messages_' || to_char(NOW(), 'YYYY_MM_DD');

  IF NOT EXISTS (
    SELECT 1
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'realtime'
    AND c.relname = partition_name
  ) THEN
    EXECUTE format(
      'CREATE TABLE realtime.%I PARTITION OF realtime.messages FOR VALUES FROM (%L) TO (%L)',
      partition_name,
      NOW(),
      (NOW() + interval '1 day')::timestamp
    );
  END IF;

  INSERT INTO realtime.messages (payload, event, topic, private, extension)
  VALUES (payload, event, topic, private, 'broadcast');
END;
$$;


ALTER FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) OWNER TO supabase_admin;

--
-- Name: subscription_check_filters(); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.subscription_check_filters() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    /*
    Validates that the user defined filters for a subscription:
    - refer to valid columns that the claimed role may access
    - values are coercable to the correct column type
    */
    declare
        col_names text[] = coalesce(
                array_agg(c.column_name order by c.ordinal_position),
                '{}'::text[]
            )
            from
                information_schema.columns c
            where
                format('%I.%I', c.table_schema, c.table_name)::regclass = new.entity
                and pg_catalog.has_column_privilege(
                    (new.claims ->> 'role'),
                    format('%I.%I', c.table_schema, c.table_name)::regclass,
                    c.column_name,
                    'SELECT'
                );
        filter realtime.user_defined_filter;
        col_type regtype;

        in_val jsonb;
    begin
        for filter in select * from unnest(new.filters) loop
            -- Filtered column is valid
            if not filter.column_name = any(col_names) then
                raise exception 'invalid column for filter %', filter.column_name;
            end if;

            -- Type is sanitized and safe for string interpolation
            col_type = (
                select atttypid::regtype
                from pg_catalog.pg_attribute
                where attrelid = new.entity
                      and attname = filter.column_name
            );
            if col_type is null then
                raise exception 'failed to lookup type for column %', filter.column_name;
            end if;

            -- Set maximum number of entries for in filter
            if filter.op = 'in'::realtime.equality_op then
                in_val = realtime.cast(filter.value, (col_type::text || '[]')::regtype);
                if coalesce(jsonb_array_length(in_val), 0) > 100 then
                    raise exception 'too many values for `in` filter. Maximum 100';
                end if;
            else
                -- raises an exception if value is not coercable to type
                perform realtime.cast(filter.value, col_type);
            end if;

        end loop;

        -- Apply consistent order to filters so the unique constraint on
        -- (subscription_id, entity, filters) can't be tricked by a different filter order
        new.filters = coalesce(
            array_agg(f order by f.column_name, f.op, f.value),
            '{}'
        ) from unnest(new.filters) f;

        return new;
    end;
    $$;


ALTER FUNCTION realtime.subscription_check_filters() OWNER TO supabase_admin;

--
-- Name: to_regrole(text); Type: FUNCTION; Schema: realtime; Owner: supabase_admin
--

CREATE FUNCTION realtime.to_regrole(role_name text) RETURNS regrole
    LANGUAGE sql IMMUTABLE
    AS $$ select role_name::regrole $$;


ALTER FUNCTION realtime.to_regrole(role_name text) OWNER TO supabase_admin;

--
-- Name: topic(); Type: FUNCTION; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE FUNCTION realtime.topic() RETURNS text
    LANGUAGE sql STABLE
    AS $$
select nullif(current_setting('realtime.topic', true), '')::text;
$$;


ALTER FUNCTION realtime.topic() OWNER TO supabase_realtime_admin;

--
-- Name: can_insert_object(text, text, uuid, jsonb); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
  INSERT INTO "storage"."objects" ("bucket_id", "name", "owner", "metadata") VALUES (bucketid, name, owner, metadata);
  -- hack to rollback the successful insert
  RAISE sqlstate 'PT200' using
  message = 'ROLLBACK',
  detail = 'rollback successful insert';
END
$$;


ALTER FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) OWNER TO supabase_storage_admin;

--
-- Name: extension(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.extension(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
_filename text;
BEGIN
    select string_to_array(name, '/') into _parts;
    select _parts[array_length(_parts,1)] into _filename;
    -- @todo return the last part instead of 2
    return split_part(_filename, '.', 2);
END
$$;


ALTER FUNCTION storage.extension(name text) OWNER TO supabase_storage_admin;

--
-- Name: filename(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.filename(name text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
    select string_to_array(name, '/') into _parts;
    return _parts[array_length(_parts,1)];
END
$$;


ALTER FUNCTION storage.filename(name text) OWNER TO supabase_storage_admin;

--
-- Name: foldername(text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.foldername(name text) RETURNS text[]
    LANGUAGE plpgsql
    AS $$
DECLARE
_parts text[];
BEGIN
    select string_to_array(name, '/') into _parts;
    return _parts[1:array_length(_parts,1)-1];
END
$$;


ALTER FUNCTION storage.foldername(name text) OWNER TO supabase_storage_admin;

--
-- Name: get_size_by_bucket(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.get_size_by_bucket() RETURNS TABLE(size bigint, bucket_id text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    return query
        select sum((metadata->>'size')::int) as size, obj.bucket_id
        from "storage".objects as obj
        group by obj.bucket_id;
END
$$;


ALTER FUNCTION storage.get_size_by_bucket() OWNER TO supabase_storage_admin;

--
-- Name: list_multipart_uploads_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, next_key_token text DEFAULT ''::text, next_upload_token text DEFAULT ''::text) RETURNS TABLE(key text, id text, created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(key COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                        substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1)))
                    ELSE
                        key
                END AS key, id, created_at
            FROM
                storage.s3_multipart_uploads
            WHERE
                bucket_id = $5 AND
                key ILIKE $1 || ''%'' AND
                CASE
                    WHEN $4 != '''' AND $6 = '''' THEN
                        CASE
                            WHEN position($2 IN substring(key from length($1) + 1)) > 0 THEN
                                substring(key from 1 for length($1) + position($2 IN substring(key from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                key COLLATE "C" > $4
                            END
                    ELSE
                        true
                END AND
                CASE
                    WHEN $6 != '''' THEN
                        id COLLATE "C" > $6
                    ELSE
                        true
                    END
            ORDER BY
                key COLLATE "C" ASC, created_at ASC) as e order by key COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_key_token, bucket_id, next_upload_token;
END;
$_$;


ALTER FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, next_key_token text, next_upload_token text) OWNER TO supabase_storage_admin;

--
-- Name: list_objects_with_delimiter(text, text, text, integer, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer DEFAULT 100, start_after text DEFAULT ''::text, next_token text DEFAULT ''::text) RETURNS TABLE(name text, id uuid, metadata jsonb, updated_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $_$
BEGIN
    RETURN QUERY EXECUTE
        'SELECT DISTINCT ON(name COLLATE "C") * from (
            SELECT
                CASE
                    WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                        substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1)))
                    ELSE
                        name
                END AS name, id, metadata, updated_at
            FROM
                storage.objects
            WHERE
                bucket_id = $5 AND
                name ILIKE $1 || ''%'' AND
                CASE
                    WHEN $6 != '''' THEN
                    name COLLATE "C" > $6
                ELSE true END
                AND CASE
                    WHEN $4 != '''' THEN
                        CASE
                            WHEN position($2 IN substring(name from length($1) + 1)) > 0 THEN
                                substring(name from 1 for length($1) + position($2 IN substring(name from length($1) + 1))) COLLATE "C" > $4
                            ELSE
                                name COLLATE "C" > $4
                            END
                    ELSE
                        true
                END
            ORDER BY
                name COLLATE "C" ASC) as e order by name COLLATE "C" LIMIT $3'
        USING prefix_param, delimiter_param, max_keys, next_token, bucket_id, start_after;
END;
$_$;


ALTER FUNCTION storage.list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, start_after text, next_token text) OWNER TO supabase_storage_admin;

--
-- Name: operation(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.operation() RETURNS text
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN current_setting('storage.operation', true);
END;
$$;


ALTER FUNCTION storage.operation() OWNER TO supabase_storage_admin;

--
-- Name: search(text, text, integer, integer, integer, text, text, text); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.search(prefix text, bucketname text, limits integer DEFAULT 100, levels integer DEFAULT 1, offsets integer DEFAULT 0, search text DEFAULT ''::text, sortcolumn text DEFAULT 'name'::text, sortorder text DEFAULT 'asc'::text) RETURNS TABLE(name text, id uuid, updated_at timestamp with time zone, created_at timestamp with time zone, last_accessed_at timestamp with time zone, metadata jsonb)
    LANGUAGE plpgsql STABLE
    AS $_$
declare
  v_order_by text;
  v_sort_order text;
begin
  case
    when sortcolumn = 'name' then
      v_order_by = 'name';
    when sortcolumn = 'updated_at' then
      v_order_by = 'updated_at';
    when sortcolumn = 'created_at' then
      v_order_by = 'created_at';
    when sortcolumn = 'last_accessed_at' then
      v_order_by = 'last_accessed_at';
    else
      v_order_by = 'name';
  end case;

  case
    when sortorder = 'asc' then
      v_sort_order = 'asc';
    when sortorder = 'desc' then
      v_sort_order = 'desc';
    else
      v_sort_order = 'asc';
  end case;

  v_order_by = v_order_by || ' ' || v_sort_order;

  return query execute
    'with folders as (
       select path_tokens[$1] as folder
       from storage.objects
         where objects.name ilike $2 || $3 || ''%''
           and bucket_id = $4
           and array_length(objects.path_tokens, 1) <> $1
       group by folder
       order by folder ' || v_sort_order || '
     )
     (select folder as "name",
            null as id,
            null as updated_at,
            null as created_at,
            null as last_accessed_at,
            null as metadata from folders)
     union all
     (select path_tokens[$1] as "name",
            id,
            updated_at,
            created_at,
            last_accessed_at,
            metadata
     from storage.objects
     where objects.name ilike $2 || $3 || ''%''
       and bucket_id = $4
       and array_length(objects.path_tokens, 1) = $1
     order by ' || v_order_by || ')
     limit $5
     offset $6' using levels, prefix, search, bucketname, limits, offsets;
end;
$_$;


ALTER FUNCTION storage.search(prefix text, bucketname text, limits integer, levels integer, offsets integer, search text, sortcolumn text, sortorder text) OWNER TO supabase_storage_admin;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: storage; Owner: supabase_storage_admin
--

CREATE FUNCTION storage.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW; 
END;
$$;


ALTER FUNCTION storage.update_updated_at_column() OWNER TO supabase_storage_admin;

--
-- Name: secrets_encrypt_secret_secret(); Type: FUNCTION; Schema: vault; Owner: supabase_admin
--

CREATE FUNCTION vault.secrets_encrypt_secret_secret() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
		BEGIN
		        new.secret = CASE WHEN new.secret IS NULL THEN NULL ELSE
			CASE WHEN new.key_id IS NULL THEN NULL ELSE pg_catalog.encode(
			  pgsodium.crypto_aead_det_encrypt(
				pg_catalog.convert_to(new.secret, 'utf8'),
				pg_catalog.convert_to((new.id::text || new.description::text || new.created_at::text || new.updated_at::text)::text, 'utf8'),
				new.key_id::uuid,
				new.nonce
			  ),
				'base64') END END;
		RETURN new;
		END;
		$$;


ALTER FUNCTION vault.secrets_encrypt_secret_secret() OWNER TO supabase_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log_entries; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.audit_log_entries (
    instance_id uuid,
    id uuid NOT NULL,
    payload json,
    created_at timestamp with time zone,
    ip_address character varying(64) DEFAULT ''::character varying NOT NULL
);


ALTER TABLE auth.audit_log_entries OWNER TO supabase_auth_admin;

--
-- Name: TABLE audit_log_entries; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.audit_log_entries IS 'Auth: Audit trail for user actions.';


--
-- Name: flow_state; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.flow_state (
    id uuid NOT NULL,
    user_id uuid,
    auth_code text NOT NULL,
    code_challenge_method auth.code_challenge_method NOT NULL,
    code_challenge text NOT NULL,
    provider_type text NOT NULL,
    provider_access_token text,
    provider_refresh_token text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    authentication_method text NOT NULL,
    auth_code_issued_at timestamp with time zone
);


ALTER TABLE auth.flow_state OWNER TO supabase_auth_admin;

--
-- Name: TABLE flow_state; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.flow_state IS 'stores metadata for pkce logins';


--
-- Name: identities; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.identities (
    provider_id text NOT NULL,
    user_id uuid NOT NULL,
    identity_data jsonb NOT NULL,
    provider text NOT NULL,
    last_sign_in_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    email text GENERATED ALWAYS AS (lower((identity_data ->> 'email'::text))) STORED,
    id uuid DEFAULT gen_random_uuid() NOT NULL
);


ALTER TABLE auth.identities OWNER TO supabase_auth_admin;

--
-- Name: TABLE identities; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.identities IS 'Auth: Stores identities associated to a user.';


--
-- Name: COLUMN identities.email; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.identities.email IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


--
-- Name: instances; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.instances (
    id uuid NOT NULL,
    uuid uuid,
    raw_base_config text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


ALTER TABLE auth.instances OWNER TO supabase_auth_admin;

--
-- Name: TABLE instances; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.instances IS 'Auth: Manages users across multiple sites.';


--
-- Name: mfa_amr_claims; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_amr_claims (
    session_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    authentication_method text NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE auth.mfa_amr_claims OWNER TO supabase_auth_admin;

--
-- Name: TABLE mfa_amr_claims; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_amr_claims IS 'auth: stores authenticator method reference claims for multi factor authentication';


--
-- Name: mfa_challenges; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_challenges (
    id uuid NOT NULL,
    factor_id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    verified_at timestamp with time zone,
    ip_address inet NOT NULL,
    otp_code text,
    web_authn_session_data jsonb
);


ALTER TABLE auth.mfa_challenges OWNER TO supabase_auth_admin;

--
-- Name: TABLE mfa_challenges; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_challenges IS 'auth: stores metadata about challenge requests made';


--
-- Name: mfa_factors; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.mfa_factors (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    friendly_name text,
    factor_type auth.factor_type NOT NULL,
    status auth.factor_status NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    secret text,
    phone text,
    last_challenged_at timestamp with time zone,
    web_authn_credential jsonb,
    web_authn_aaguid uuid
);


ALTER TABLE auth.mfa_factors OWNER TO supabase_auth_admin;

--
-- Name: TABLE mfa_factors; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.mfa_factors IS 'auth: stores metadata about factors';


--
-- Name: one_time_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.one_time_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_type auth.one_time_token_type NOT NULL,
    token_hash text NOT NULL,
    relates_to text NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT one_time_tokens_token_hash_check CHECK ((char_length(token_hash) > 0))
);


ALTER TABLE auth.one_time_tokens OWNER TO supabase_auth_admin;

--
-- Name: refresh_tokens; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.refresh_tokens (
    instance_id uuid,
    id bigint NOT NULL,
    token character varying(255),
    user_id character varying(255),
    revoked boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    parent character varying(255),
    session_id uuid
);


ALTER TABLE auth.refresh_tokens OWNER TO supabase_auth_admin;

--
-- Name: TABLE refresh_tokens; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.refresh_tokens IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE; Schema: auth; Owner: supabase_auth_admin
--

CREATE SEQUENCE auth.refresh_tokens_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE auth.refresh_tokens_id_seq OWNER TO supabase_auth_admin;

--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: auth; Owner: supabase_auth_admin
--

ALTER SEQUENCE auth.refresh_tokens_id_seq OWNED BY auth.refresh_tokens.id;


--
-- Name: saml_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.saml_providers (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    entity_id text NOT NULL,
    metadata_xml text NOT NULL,
    metadata_url text,
    attribute_mapping jsonb,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    name_id_format text,
    CONSTRAINT "entity_id not empty" CHECK ((char_length(entity_id) > 0)),
    CONSTRAINT "metadata_url not empty" CHECK (((metadata_url = NULL::text) OR (char_length(metadata_url) > 0))),
    CONSTRAINT "metadata_xml not empty" CHECK ((char_length(metadata_xml) > 0))
);


ALTER TABLE auth.saml_providers OWNER TO supabase_auth_admin;

--
-- Name: TABLE saml_providers; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.saml_providers IS 'Auth: Manages SAML Identity Provider connections.';


--
-- Name: saml_relay_states; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.saml_relay_states (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    request_id text NOT NULL,
    for_email text,
    redirect_to text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    flow_state_id uuid,
    CONSTRAINT "request_id not empty" CHECK ((char_length(request_id) > 0))
);


ALTER TABLE auth.saml_relay_states OWNER TO supabase_auth_admin;

--
-- Name: TABLE saml_relay_states; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.saml_relay_states IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


--
-- Name: schema_migrations; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.schema_migrations (
    version character varying(255) NOT NULL
);


ALTER TABLE auth.schema_migrations OWNER TO supabase_auth_admin;

--
-- Name: TABLE schema_migrations; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.schema_migrations IS 'Auth: Manages updates to the auth system.';


--
-- Name: sessions; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sessions (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    factor_id uuid,
    aal auth.aal_level,
    not_after timestamp with time zone,
    refreshed_at timestamp without time zone,
    user_agent text,
    ip inet,
    tag text
);


ALTER TABLE auth.sessions OWNER TO supabase_auth_admin;

--
-- Name: TABLE sessions; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sessions IS 'Auth: Stores session data associated to a user.';


--
-- Name: COLUMN sessions.not_after; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.sessions.not_after IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';


--
-- Name: sso_domains; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sso_domains (
    id uuid NOT NULL,
    sso_provider_id uuid NOT NULL,
    domain text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "domain not empty" CHECK ((char_length(domain) > 0))
);


ALTER TABLE auth.sso_domains OWNER TO supabase_auth_admin;

--
-- Name: TABLE sso_domains; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sso_domains IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


--
-- Name: sso_providers; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.sso_providers (
    id uuid NOT NULL,
    resource_id text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    CONSTRAINT "resource_id not empty" CHECK (((resource_id = NULL::text) OR (char_length(resource_id) > 0)))
);


ALTER TABLE auth.sso_providers OWNER TO supabase_auth_admin;

--
-- Name: TABLE sso_providers; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.sso_providers IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


--
-- Name: COLUMN sso_providers.resource_id; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.sso_providers.resource_id IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


--
-- Name: users; Type: TABLE; Schema: auth; Owner: supabase_auth_admin
--

CREATE TABLE auth.users (
    instance_id uuid,
    id uuid NOT NULL,
    aud character varying(255),
    role character varying(255),
    email character varying(255),
    encrypted_password character varying(255),
    email_confirmed_at timestamp with time zone,
    invited_at timestamp with time zone,
    confirmation_token character varying(255),
    confirmation_sent_at timestamp with time zone,
    recovery_token character varying(255),
    recovery_sent_at timestamp with time zone,
    email_change_token_new character varying(255),
    email_change character varying(255),
    email_change_sent_at timestamp with time zone,
    last_sign_in_at timestamp with time zone,
    raw_app_meta_data jsonb,
    raw_user_meta_data jsonb,
    is_super_admin boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    phone text DEFAULT NULL::character varying,
    phone_confirmed_at timestamp with time zone,
    phone_change text DEFAULT ''::character varying,
    phone_change_token character varying(255) DEFAULT ''::character varying,
    phone_change_sent_at timestamp with time zone,
    confirmed_at timestamp with time zone GENERATED ALWAYS AS (LEAST(email_confirmed_at, phone_confirmed_at)) STORED,
    email_change_token_current character varying(255) DEFAULT ''::character varying,
    email_change_confirm_status smallint DEFAULT 0,
    banned_until timestamp with time zone,
    reauthentication_token character varying(255) DEFAULT ''::character varying,
    reauthentication_sent_at timestamp with time zone,
    is_sso_user boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone,
    is_anonymous boolean DEFAULT false NOT NULL,
    CONSTRAINT users_email_change_confirm_status_check CHECK (((email_change_confirm_status >= 0) AND (email_change_confirm_status <= 2)))
);


ALTER TABLE auth.users OWNER TO supabase_auth_admin;

--
-- Name: TABLE users; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON TABLE auth.users IS 'Auth: Stores user login data within a secure schema.';


--
-- Name: COLUMN users.is_sso_user; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON COLUMN auth.users.is_sso_user IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


--
-- Name: User; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."User" (
    id integer NOT NULL,
    username text NOT NULL,
    email text NOT NULL,
    password text NOT NULL,
    name text
);


ALTER TABLE public."User" OWNER TO postgres;

--
-- Name: User_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public."User_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public."User_id_seq" OWNER TO postgres;

--
-- Name: User_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public."User_id_seq" OWNED BY public."User".id;


--
-- Name: _prisma_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public._prisma_migrations (
    id character varying(36) NOT NULL,
    checksum character varying(64) NOT NULL,
    finished_at timestamp with time zone,
    migration_name character varying(255) NOT NULL,
    logs text,
    rolled_back_at timestamp with time zone,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    applied_steps_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public._prisma_migrations OWNER TO postgres;

--
-- Name: accounting_asset; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_asset (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    value numeric(10,2) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    purchase_date date NOT NULL,
    depreciating boolean NOT NULL,
    residual_value numeric(10,2),
    useful_life_in_months numeric(10,0),
    book_id bigint NOT NULL,
    category_id bigint NOT NULL,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_asset OWNER TO postgres;

--
-- Name: accounting_asset_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_asset ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_asset_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_assetcategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_assetcategory (
    id bigint NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.accounting_assetcategory OWNER TO postgres;

--
-- Name: accounting_assetcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_assetcategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_assetcategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_book; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_book (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.accounting_book OWNER TO postgres;

--
-- Name: accounting_book_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_book ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_book_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_cashaccount; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_cashaccount (
    id bigint NOT NULL,
    name character varying(12) NOT NULL,
    balance numeric(10,2) NOT NULL,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_cashaccount OWNER TO postgres;

--
-- Name: accounting_cashcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_cashaccount ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_cashcategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_currencycategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_currencycategory (
    id bigint NOT NULL,
    code character varying(3) NOT NULL,
    name character varying(50) NOT NULL,
    symbol character varying(5)
);


ALTER TABLE public.accounting_currencycategory OWNER TO postgres;

--
-- Name: accounting_currencycategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_currencycategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_currencycategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_equitycapital; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_equitycapital (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    note character varying(200),
    date_invested date NOT NULL,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    stakeholder_id bigint NOT NULL
);


ALTER TABLE public.accounting_equitycapital OWNER TO postgres;

--
-- Name: accounting_equitycapital_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_equitycapital ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_equitycapital_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_equitydivident; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_equitydivident (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    currency_id bigint,
    stakeholder_id bigint
);


ALTER TABLE public.accounting_equitydivident OWNER TO postgres;

--
-- Name: accounting_equitydivident_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_equitydivident ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_equitydivident_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_equityexpense; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_equityexpense (
    id bigint NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    book_id bigint NOT NULL,
    category_id bigint,
    currency_id bigint,
    cash_account_id bigint NOT NULL,
    account_balance numeric(10,2) NOT NULL
);


ALTER TABLE public.accounting_equityexpense OWNER TO postgres;

--
-- Name: accounting_equityrevenue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_equityrevenue (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    currency_id bigint,
    invoice_number character varying(20) NOT NULL
);


ALTER TABLE public.accounting_equityrevenue OWNER TO postgres;

--
-- Name: accounting_equityrevenue_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_equityrevenue ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_equityrevenue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_expense_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_equityexpense ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_expense_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_expensecategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_expensecategory (
    id bigint NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.accounting_expensecategory OWNER TO postgres;

--
-- Name: accounting_expensecategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_expensecategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_expensecategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_income; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_income (
    id bigint NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    book_id bigint NOT NULL,
    category_id bigint,
    company_id bigint,
    contact_id bigint,
    currency_id bigint
);


ALTER TABLE public.accounting_income OWNER TO postgres;

--
-- Name: accounting_income_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_income ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_income_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_incomecategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_incomecategory (
    id bigint NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.accounting_incomecategory OWNER TO postgres;

--
-- Name: accounting_incomecategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_incomecategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_incomecategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_liability; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_liability (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(200),
    value numeric(12,2) NOT NULL,
    due_date date NOT NULL,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_liability OWNER TO postgres;

--
-- Name: accounting_liability_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_liability ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_liability_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_sale; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_sale (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    quantity numeric(6,2) NOT NULL,
    price numeric(6,2) NOT NULL,
    book_id bigint NOT NULL,
    company_id bigint,
    contact_id bigint,
    product_id bigint NOT NULL
);


ALTER TABLE public.accounting_sale OWNER TO postgres;

--
-- Name: accounting_sale_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_sale ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_sale_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_source; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_source (
    id bigint NOT NULL,
    name character varying(100) NOT NULL
);


ALTER TABLE public.accounting_source OWNER TO postgres;

--
-- Name: accounting_source_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_source ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_stakeholder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_stakeholder (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name character varying(150) NOT NULL,
    description character varying(200),
    share numeric(5,2) NOT NULL
);


ALTER TABLE public.accounting_stakeholder OWNER TO postgres;

--
-- Name: accounting_stakeholder_books; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_stakeholder_books (
    id bigint NOT NULL,
    stakeholder_id bigint NOT NULL,
    book_id bigint NOT NULL
);


ALTER TABLE public.accounting_stakeholder_books OWNER TO postgres;

--
-- Name: accounting_stakeholder_books_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_stakeholder_books ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_stakeholder_books_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_stakeholder_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_stakeholder ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_stakeholder_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO postgres;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO postgres;

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO postgres;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO postgres;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authentication_member; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_member (
    id bigint NOT NULL,
    company_name character varying(100) NOT NULL,
    user_id integer
);


ALTER TABLE public.authentication_member OWNER TO postgres;

--
-- Name: authentication_member_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_member ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_member_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: crm_company; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crm_company (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    email character varying(254) NOT NULL,
    phone character varying(15) NOT NULL,
    address character varying(255) NOT NULL,
    country character varying(100) NOT NULL,
    website character varying(200) NOT NULL,
    "backgroundInfo" character varying(400) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.crm_company OWNER TO postgres;

--
-- Name: crm_company_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.crm_company ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.crm_company_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: crm_contact; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crm_contact (
    id bigint NOT NULL,
    name character varying(200) NOT NULL,
    email character varying(254) NOT NULL,
    address character varying(255) NOT NULL,
    birthday date,
    city character varying(100) NOT NULL,
    company_name character varying(255) NOT NULL,
    country character varying(100) NOT NULL,
    job_title character varying(100) NOT NULL,
    phone character varying(15) NOT NULL,
    state character varying(100) NOT NULL,
    zip_code character varying(10) NOT NULL,
    company_id bigint,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.crm_contact OWNER TO postgres;

--
-- Name: crm_contact_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.crm_contact ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.crm_contact_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: crm_note; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crm_note (
    id bigint NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    contact_id bigint,
    company_id bigint,
    modified_date timestamp with time zone NOT NULL
);


ALTER TABLE public.crm_note OWNER TO postgres;

--
-- Name: crm_note_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.crm_note ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.crm_note_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO postgres;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO postgres;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- Name: operating_machine; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_machine (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    max_rpm integer NOT NULL,
    domain numeric(5,2) NOT NULL,
    CONSTRAINT operating_machine_max_rpm_check CHECK ((max_rpm >= 0))
);


ALTER TABLE public.operating_machine OWNER TO postgres;

--
-- Name: operating_machine_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_machine ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_machine_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_product; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_product (
    id bigint NOT NULL,
    name character varying(50),
    cost numeric(6,2) NOT NULL,
    unit_id bigint NOT NULL,
    description character varying(250),
    sku character varying(50) NOT NULL,
    stock_quantity numeric(10,2) NOT NULL,
    variant character varying[],
    manufacturer character varying(250) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.operating_product OWNER TO postgres;

--
-- Name: operating_product_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_product ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_product_raw_materials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_product_raw_materials (
    id bigint NOT NULL,
    product_id bigint NOT NULL,
    rawmaterial_id bigint NOT NULL
);


ALTER TABLE public.operating_product_raw_materials OWNER TO postgres;

--
-- Name: operating_product_raw_materials_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_product_raw_materials ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_product_raw_materials_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_rawmaterial; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_rawmaterial (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    cost numeric(6,2) NOT NULL,
    type_id bigint NOT NULL
);


ALTER TABLE public.operating_rawmaterial OWNER TO postgres;

--
-- Name: operating_rawmaterial_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_rawmaterial ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_rawmaterial_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_rawmaterial_supplierCompany; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."operating_rawmaterial_supplierCompany" (
    id bigint NOT NULL,
    rawmaterial_id bigint NOT NULL,
    company_id bigint NOT NULL
);


ALTER TABLE public."operating_rawmaterial_supplierCompany" OWNER TO postgres;

--
-- Name: operating_rawmaterial_supplierCompany_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."operating_rawmaterial_supplierCompany" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public."operating_rawmaterial_supplierCompany_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_rawmaterial_supplierContact; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."operating_rawmaterial_supplierContact" (
    id bigint NOT NULL,
    rawmaterial_id bigint NOT NULL,
    contact_id bigint NOT NULL
);


ALTER TABLE public."operating_rawmaterial_supplierContact" OWNER TO postgres;

--
-- Name: operating_rawmaterial_supplierContact_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."operating_rawmaterial_supplierContact" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public."operating_rawmaterial_supplierContact_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_rawmaterialcategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_rawmaterialcategory (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    unit character varying(10) NOT NULL
);


ALTER TABLE public.operating_rawmaterialcategory OWNER TO postgres;

--
-- Name: operating_rawmaterialcategorys_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_rawmaterialcategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_rawmaterialcategorys_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_unitcategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_unitcategory (
    id bigint NOT NULL,
    name character varying(50) NOT NULL,
    decimals integer NOT NULL
);


ALTER TABLE public.operating_unitcategory OWNER TO postgres;

--
-- Name: operating_unitcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_unitcategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_unitcategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    name text,
    files jsonb[]
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.products ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.products_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: todo_task; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.todo_task (
    id bigint NOT NULL,
    task_name character varying(200) NOT NULL,
    due_date date NOT NULL,
    description text,
    completed boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone NOT NULL,
    company_id bigint,
    contact_id bigint
);


ALTER TABLE public.todo_task OWNER TO postgres;

--
-- Name: todo_task_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.todo_task ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.todo_task_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: messages; Type: TABLE; Schema: realtime; Owner: supabase_realtime_admin
--

CREATE TABLE realtime.messages (
    topic text NOT NULL,
    extension text NOT NULL,
    payload jsonb,
    event text,
    private boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    inserted_at timestamp without time zone DEFAULT now() NOT NULL,
    id uuid DEFAULT gen_random_uuid() NOT NULL
)
PARTITION BY RANGE (inserted_at);


ALTER TABLE realtime.messages OWNER TO supabase_realtime_admin;

--
-- Name: schema_migrations; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.schema_migrations (
    version bigint NOT NULL,
    inserted_at timestamp(0) without time zone
);


ALTER TABLE realtime.schema_migrations OWNER TO supabase_admin;

--
-- Name: subscription; Type: TABLE; Schema: realtime; Owner: supabase_admin
--

CREATE TABLE realtime.subscription (
    id bigint NOT NULL,
    subscription_id uuid NOT NULL,
    entity regclass NOT NULL,
    filters realtime.user_defined_filter[] DEFAULT '{}'::realtime.user_defined_filter[] NOT NULL,
    claims jsonb NOT NULL,
    claims_role regrole GENERATED ALWAYS AS (realtime.to_regrole((claims ->> 'role'::text))) STORED NOT NULL,
    created_at timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);


ALTER TABLE realtime.subscription OWNER TO supabase_admin;

--
-- Name: subscription_id_seq; Type: SEQUENCE; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE realtime.subscription ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME realtime.subscription_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: buckets; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.buckets (
    id text NOT NULL,
    name text NOT NULL,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    public boolean DEFAULT false,
    avif_autodetection boolean DEFAULT false,
    file_size_limit bigint,
    allowed_mime_types text[],
    owner_id text
);


ALTER TABLE storage.buckets OWNER TO supabase_storage_admin;

--
-- Name: COLUMN buckets.owner; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN storage.buckets.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: migrations; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.migrations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    hash character varying(40) NOT NULL,
    executed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE storage.migrations OWNER TO supabase_storage_admin;

--
-- Name: objects; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.objects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    bucket_id text,
    name text,
    owner uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_accessed_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    path_tokens text[] GENERATED ALWAYS AS (string_to_array(name, '/'::text)) STORED,
    version text,
    owner_id text,
    user_metadata jsonb
);


ALTER TABLE storage.objects OWNER TO supabase_storage_admin;

--
-- Name: COLUMN objects.owner; Type: COMMENT; Schema: storage; Owner: supabase_storage_admin
--

COMMENT ON COLUMN storage.objects.owner IS 'Field is deprecated, use owner_id instead';


--
-- Name: s3_multipart_uploads; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.s3_multipart_uploads (
    id text NOT NULL,
    in_progress_size bigint DEFAULT 0 NOT NULL,
    upload_signature text NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    version text NOT NULL,
    owner_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    user_metadata jsonb
);


ALTER TABLE storage.s3_multipart_uploads OWNER TO supabase_storage_admin;

--
-- Name: s3_multipart_uploads_parts; Type: TABLE; Schema: storage; Owner: supabase_storage_admin
--

CREATE TABLE storage.s3_multipart_uploads_parts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    upload_id text NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    part_number integer NOT NULL,
    bucket_id text NOT NULL,
    key text NOT NULL COLLATE pg_catalog."C",
    etag text NOT NULL,
    owner_id text,
    version text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE storage.s3_multipart_uploads_parts OWNER TO supabase_storage_admin;

--
-- Name: decrypted_secrets; Type: VIEW; Schema: vault; Owner: supabase_admin
--

CREATE VIEW vault.decrypted_secrets AS
 SELECT secrets.id,
    secrets.name,
    secrets.description,
    secrets.secret,
        CASE
            WHEN (secrets.secret IS NULL) THEN NULL::text
            ELSE
            CASE
                WHEN (secrets.key_id IS NULL) THEN NULL::text
                ELSE convert_from(pgsodium.crypto_aead_det_decrypt(decode(secrets.secret, 'base64'::text), convert_to(((((secrets.id)::text || secrets.description) || (secrets.created_at)::text) || (secrets.updated_at)::text), 'utf8'::name), secrets.key_id, secrets.nonce), 'utf8'::name)
            END
        END AS decrypted_secret,
    secrets.key_id,
    secrets.nonce,
    secrets.created_at,
    secrets.updated_at
   FROM vault.secrets;


ALTER TABLE vault.decrypted_secrets OWNER TO supabase_admin;

--
-- Name: refresh_tokens id; Type: DEFAULT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens ALTER COLUMN id SET DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass);


--
-- Name: User id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."User" ALTER COLUMN id SET DEFAULT nextval('public."User_id_seq"'::regclass);


--
-- Data for Name: audit_log_entries; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.audit_log_entries (instance_id, id, payload, created_at, ip_address) FROM stdin;
\.


--
-- Data for Name: flow_state; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.flow_state (id, user_id, auth_code, code_challenge_method, code_challenge, provider_type, provider_access_token, provider_refresh_token, created_at, updated_at, authentication_method, auth_code_issued_at) FROM stdin;
\.


--
-- Data for Name: identities; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at, id) FROM stdin;
\.


--
-- Data for Name: instances; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.instances (id, uuid, raw_base_config, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: mfa_amr_claims; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.mfa_amr_claims (session_id, created_at, updated_at, authentication_method, id) FROM stdin;
\.


--
-- Data for Name: mfa_challenges; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.mfa_challenges (id, factor_id, created_at, verified_at, ip_address, otp_code, web_authn_session_data) FROM stdin;
\.


--
-- Data for Name: mfa_factors; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.mfa_factors (id, user_id, friendly_name, factor_type, status, created_at, updated_at, secret, phone, last_challenged_at, web_authn_credential, web_authn_aaguid) FROM stdin;
\.


--
-- Data for Name: one_time_tokens; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.one_time_tokens (id, user_id, token_type, token_hash, relates_to, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.refresh_tokens (instance_id, id, token, user_id, revoked, created_at, updated_at, parent, session_id) FROM stdin;
\.


--
-- Data for Name: saml_providers; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.saml_providers (id, sso_provider_id, entity_id, metadata_xml, metadata_url, attribute_mapping, created_at, updated_at, name_id_format) FROM stdin;
\.


--
-- Data for Name: saml_relay_states; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.saml_relay_states (id, sso_provider_id, request_id, for_email, redirect_to, created_at, updated_at, flow_state_id) FROM stdin;
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.schema_migrations (version) FROM stdin;
20171026211738
20171026211808
20171026211834
20180103212743
20180108183307
20180119214651
20180125194653
00
20210710035447
20210722035447
20210730183235
20210909172000
20210927181326
20211122151130
20211124214934
20211202183645
20220114185221
20220114185340
20220224000811
20220323170000
20220429102000
20220531120530
20220614074223
20220811173540
20221003041349
20221003041400
20221011041400
20221020193600
20221021073300
20221021082433
20221027105023
20221114143122
20221114143410
20221125140132
20221208132122
20221215195500
20221215195800
20221215195900
20230116124310
20230116124412
20230131181311
20230322519590
20230402418590
20230411005111
20230508135423
20230523124323
20230818113222
20230914180801
20231027141322
20231114161723
20231117164230
20240115144230
20240214120130
20240306115329
20240314092811
20240427152123
20240612123726
20240729123726
20240802193726
20240806073726
20241009103726
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.sessions (id, user_id, created_at, updated_at, factor_id, aal, not_after, refreshed_at, user_agent, ip, tag) FROM stdin;
\.


--
-- Data for Name: sso_domains; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.sso_domains (id, sso_provider_id, domain, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: sso_providers; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.sso_providers (id, resource_id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: auth; Owner: supabase_auth_admin
--

COPY auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, invited_at, confirmation_token, confirmation_sent_at, recovery_token, recovery_sent_at, email_change_token_new, email_change, email_change_sent_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, phone, phone_confirmed_at, phone_change, phone_change_token, phone_change_sent_at, email_change_token_current, email_change_confirm_status, banned_until, reauthentication_token, reauthentication_sent_at, is_sso_user, deleted_at, is_anonymous) FROM stdin;
\.


--
-- Data for Name: key; Type: TABLE DATA; Schema: pgsodium; Owner: supabase_admin
--

COPY pgsodium.key (id, status, created, expires, key_type, key_id, key_context, name, associated_data, raw_key, raw_key_nonce, parent_key, comment, user_data) FROM stdin;
\.


--
-- Data for Name: User; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."User" (id, username, email, password, name) FROM stdin;
3	konfeksiyon	konfeksiyon@demfirat.com	$2b$12$xQrwTgs4uCM.3RLn4KYXLuneLRG27Pf6sn2rYe6alqAXvcMqFCjiG	Karven Konfeksiyon
4	firat	firatkarven@gmail.com	$2b$12$TvxsjdpixifjLZKdZRxdSeSzBfOMh7kt5eDjWalzrHT1ICRNOwnzy	Firat
5	client	client@demfirat.com	$2b$12$kEUc5NV05I6QMpS/tDAIkut1fMRuToBkFDNr/GZuOkARtks/7nVm2	Client
6	weronika	import@maxa.pl	$2b$12$pBJINtx8pwR2Q7JOfuXLRuQSPOPPNMeBezx9tuCQ2soG6u8ud8FMO	Weronika
\.


--
-- Data for Name: _prisma_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public._prisma_migrations (id, checksum, finished_at, migration_name, logs, rolled_back_at, started_at, applied_steps_count) FROM stdin;
\.


--
-- Data for Name: accounting_asset; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_asset (id, name, value, created_at, purchase_date, depreciating, residual_value, useful_life_in_months, book_id, category_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_assetcategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_assetcategory (id, name) FROM stdin;
1	Cash
2	Merchandise Inventory
3	Property
4	Furniture
5	Accounts Receivable
6	Office Supplies
\.


--
-- Data for Name: accounting_book; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_book (id, created_at, name) FROM stdin;
2	2024-10-05 21:24:20.932146+00	Karven
1	2024-10-05 21:21:36.355531+00	Pearlins LLC
3	2024-11-16 11:36:29.149535+00	new book
\.


--
-- Data for Name: accounting_cashaccount; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_cashaccount (id, name, balance, book_id, currency_id) FROM stdin;
2	CP	0.00	2	1
3	IB-USD	0.00	2	1
4	IB-EUR	0.00	2	2
5	IB-TRY	0.00	2	3
6	ZB	0.00	2	3
7	AB	0.00	2	3
8	EP	0.00	2	3
9	OnHand	0.00	2	1
11	A/P	0.00	1	1
12	A/R	0.00	1	1
10	On Hand	2980.00	1	1
1	CB	1145.00	1	1
\.


--
-- Data for Name: accounting_currencycategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_currencycategory (id, code, name, symbol) FROM stdin;
1	USD	US Dollar	$
2	EUR	Euro	€
3	TRY	Turkish Lira	₺
\.


--
-- Data for Name: accounting_equitycapital; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equitycapital (id, created_at, amount, note, date_invested, book_id, cash_account_id, stakeholder_id) FROM stdin;
1	2024-10-06 07:45:56.473681+00	1000.00	\N	2024-10-06	1	10	2
2	2024-10-15 19:44:40.06788+00	2000.00	\N	2024-10-15	1	10	2
3	2024-11-17 11:36:27.041205+00	10.00	\N	2024-11-17	1	1	2
4	2024-11-17 11:42:19.933988+00	5.00	my investment	2024-11-17	1	1	2
5	2024-11-23 13:06:22.952928+00	50.00	\N	2024-11-23	1	1	2
\.


--
-- Data for Name: accounting_equitydivident; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equitydivident (id, created_at, amount, date, description, book_id, cash_account_id, currency_id, stakeholder_id) FROM stdin;
1	2024-11-23 13:46:20.276636+00	5.00	2024-11-23		1	1	1	2
\.


--
-- Data for Name: accounting_equityexpense; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equityexpense (id, amount, date, description, created_at, book_id, category_id, currency_id, cash_account_id, account_balance) FROM stdin;
7	100.00	2024-11-17	comission to seller	2024-11-16 22:57:40.710095+00	1	3	1	1	0.00
8	20.00	2024-11-17		2024-11-16 22:59:08.632798+00	1	6	1	1	980.00
9	20.00	2024-11-23		2024-11-23 13:02:41.461368+00	1	2	1	10	2980.00
10	20.00	2024-11-23		2024-11-23 13:03:20.574424+00	1	4	1	1	1050.00
\.


--
-- Data for Name: accounting_equityrevenue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equityrevenue (id, created_at, amount, date, description, book_id, cash_account_id, currency_id, invoice_number) FROM stdin;
1	2024-11-17 20:10:47.04247+00	5.00	2024-11-17		1	1	1	
2	2024-11-23 13:05:39.974186+00	50.00	2024-11-23		1	1	1	1523
\.


--
-- Data for Name: accounting_expensecategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_expensecategory (id, name) FROM stdin;
1	Advertising
2	Car and Truck Expenses
3	Comissions and Fees
4	Contract Labor
5	Depletion
6	Depreciation
7	Employee Benefit Programs
8	Insurance
9	Interest: Mortgage
10	Interest: Other
11	Legal and Professional Services
12	Office Expense
13	Pension and Profit Sharing
14	Rent or Lease: Vehicle, Machinery, and Equipment
15	Rent or Lease: Other Business Property
16	Repairs and Maintenance
17	Supplies
18	Taxes and Licenses
19	Travel
20	Wages
\.


--
-- Data for Name: accounting_income; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_income (id, amount, date, description, created_at, book_id, category_id, company_id, contact_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_incomecategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_incomecategory (id, name) FROM stdin;
\.


--
-- Data for Name: accounting_liability; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_liability (id, name, description, value, due_date, book_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_sale; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_sale (id, created_at, quantity, price, book_id, company_id, contact_id, product_id) FROM stdin;
\.


--
-- Data for Name: accounting_source; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_source (id, name) FROM stdin;
\.


--
-- Data for Name: accounting_stakeholder; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_stakeholder (id, created_at, name, description, share) FROM stdin;
2	2024-10-06 06:57:30.672862+00	Muhammed Firat Ozturk	\N	0.85
\.


--
-- Data for Name: accounting_stakeholder_books; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_stakeholder_books (id, stakeholder_id, book_id) FROM stdin;
2	2	1
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add task	7	add_task
26	Can change task	7	change_task
27	Can delete task	7	delete_task
28	Can view task	7	view_task
29	Can add contact	8	add_contact
30	Can change contact	8	change_contact
31	Can delete contact	8	delete_contact
32	Can view contact	8	view_contact
33	Can add company	9	add_company
34	Can change company	9	change_company
35	Can delete company	9	delete_company
36	Can view company	9	view_company
37	Can add note	10	add_note
38	Can change note	10	change_note
39	Can delete note	10	delete_note
40	Can view note	10	view_note
41	Can add member	11	add_member
42	Can change member	11	change_member
43	Can delete member	11	delete_member
44	Can view member	11	view_member
45	Can add expense category	12	add_expensecategory
46	Can change expense category	12	change_expensecategory
47	Can delete expense category	12	delete_expensecategory
48	Can view expense category	12	view_expensecategory
49	Can add expense	13	add_expense
50	Can change expense	13	change_expense
51	Can delete expense	13	delete_expense
52	Can view expense	13	view_expense
53	Can add income category	14	add_incomecategory
54	Can change income category	14	change_incomecategory
55	Can delete income category	14	delete_incomecategory
56	Can view income category	14	view_incomecategory
57	Can add income	15	add_income
58	Can change income	15	change_income
59	Can delete income	15	delete_income
60	Can view income	15	view_income
61	Can add currency category	16	add_currencycategory
62	Can change currency category	16	change_currencycategory
63	Can delete currency category	16	delete_currencycategory
64	Can view currency category	16	view_currencycategory
65	Can add book	17	add_book
66	Can change book	17	change_book
67	Can delete book	17	delete_book
68	Can view book	17	view_book
69	Can add raw material categorys	18	add_rawmaterialcategorys
70	Can change raw material categorys	18	change_rawmaterialcategorys
71	Can delete raw material categorys	18	delete_rawmaterialcategorys
72	Can view raw material categorys	18	view_rawmaterialcategorys
73	Can add raw material	19	add_rawmaterial
74	Can change raw material	19	change_rawmaterial
75	Can delete raw material	19	delete_rawmaterial
76	Can view raw material	19	view_rawmaterial
77	Can add product	20	add_product
78	Can change product	20	change_product
79	Can delete product	20	delete_product
80	Can view product	20	view_product
81	Can add raw material category	18	add_rawmaterialcategory
82	Can change raw material category	18	change_rawmaterialcategory
83	Can delete raw material category	18	delete_rawmaterialcategory
84	Can view raw material category	18	view_rawmaterialcategory
85	Can add machine	21	add_machine
86	Can change machine	21	change_machine
87	Can delete machine	21	delete_machine
88	Can view machine	21	view_machine
89	Can add asset	22	add_asset
90	Can change asset	22	change_asset
91	Can delete asset	22	delete_asset
92	Can view asset	22	view_asset
93	Can add sale	23	add_sale
94	Can change sale	23	change_sale
95	Can delete sale	23	delete_sale
96	Can view sale	23	view_sale
97	Can add account	24	add_account
98	Can change account	24	change_account
99	Can delete account	24	delete_account
100	Can view account	24	view_account
101	Can add unit category	25	add_unitcategory
102	Can change unit category	25	change_unitcategory
103	Can delete unit category	25	delete_unitcategory
104	Can view unit category	25	view_unitcategory
105	Can add asset category	26	add_assetcategory
106	Can change asset category	26	change_assetcategory
107	Can delete asset category	26	delete_assetcategory
108	Can view asset category	26	view_assetcategory
109	Can add bank accounts	27	add_bankaccounts
110	Can change bank accounts	27	change_bankaccounts
111	Can delete bank accounts	27	delete_bankaccounts
112	Can view bank accounts	27	view_bankaccounts
113	Can add transaction	28	add_transaction
114	Can change transaction	28	change_transaction
115	Can delete transaction	28	delete_transaction
116	Can view transaction	28	view_transaction
117	Can add cash accounts	27	add_cashaccounts
118	Can change cash accounts	27	change_cashaccounts
119	Can delete cash accounts	27	delete_cashaccounts
120	Can view cash accounts	27	view_cashaccounts
121	Can add capital	29	add_capital
122	Can change capital	29	change_capital
123	Can delete capital	29	delete_capital
124	Can view capital	29	view_capital
125	Can add cash category	27	add_cashcategory
126	Can change cash category	27	change_cashcategory
127	Can delete cash category	27	delete_cashcategory
128	Can view cash category	27	view_cashcategory
129	Can add stake holder	30	add_stakeholder
130	Can change stake holder	30	change_stakeholder
131	Can delete stake holder	30	delete_stakeholder
132	Can view stake holder	30	view_stakeholder
133	Can add source	31	add_source
134	Can change source	31	change_source
135	Can delete source	31	delete_source
136	Can view source	31	view_source
137	Can add equity	32	add_equity
138	Can change equity	32	change_equity
139	Can delete equity	32	delete_equity
140	Can view equity	32	view_equity
141	Can add liability	33	add_liability
142	Can change liability	33	change_liability
143	Can delete liability	33	delete_liability
144	Can view liability	33	view_liability
145	Can add cash accouns	27	add_cashaccouns
146	Can change cash accouns	27	change_cashaccouns
147	Can delete cash accouns	27	delete_cashaccouns
148	Can view cash accouns	27	view_cashaccouns
149	Can add equity_ capital	34	add_equity_capital
150	Can change equity_ capital	34	change_equity_capital
151	Can delete equity_ capital	34	delete_equity_capital
152	Can view equity_ capital	34	view_equity_capital
153	Can add cash account	27	add_cashaccount
154	Can change cash account	27	change_cashaccount
155	Can delete cash account	27	delete_cashaccount
156	Can view cash account	27	view_cashaccount
157	Can add equity capital	35	add_equitycapital
158	Can change equity capital	35	change_equitycapital
159	Can delete equity capital	35	delete_equitycapital
160	Can view equity capital	35	view_equitycapital
161	Can add equity expense	13	add_equityexpense
162	Can change equity expense	13	change_equityexpense
163	Can delete equity expense	13	delete_equityexpense
164	Can view equity expense	13	view_equityexpense
165	Can add equity revenue	36	add_equityrevenue
166	Can change equity revenue	36	change_equityrevenue
167	Can delete equity revenue	36	delete_equityrevenue
168	Can view equity revenue	36	view_equityrevenue
169	Can add equity divident	37	add_equitydivident
170	Can change equity divident	37	change_equitydivident
171	Can delete equity divident	37	delete_equitydivident
172	Can view equity divident	37	view_equitydivident
173	Can add invoice	38	add_invoice
174	Can change invoice	38	change_invoice
175	Can delete invoice	38	delete_invoice
176	Can view invoice	38	view_invoice
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
3	pbkdf2_sha256$600000$Rolu3LCDzCTsyvQOzeKJhi$KGDSgHcBzVyPSnnSMBfuoyCee7wB9n6ORsnUlZtseK0=	\N	f	firat2	firat2	ozturk2	ozturk2@gmail.com	f	t	2024-03-20 05:00:08.085829+00
2	pbkdf2_sha256$600000$X7sZcEb2AhA2RWf92lDDST$xBVEXV7sWj3wAU5d0UGHhEQj02HTxMAQvSQHgOOagNg=	2024-03-31 12:44:13.125521+00	f	firatdmf	Muhammed Firat	Ozturk	firatdmf@gmail.com	f	t	2024-03-20 04:58:24.695965+00
4	pbkdf2_sha256$600000$gn69uN0TwDztXojgCryPFt$LfHNXwBZ4yMs5YNIyYh+vA59it8CzWF7JWiUrxolUdU=	2024-11-25 10:29:41.003067+00	t	firat	Firat	Ozturk	firatdmf1@gmail.com	t	t	2024-03-21 20:57:42+00
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: authentication_member; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_member (id, company_name, user_id) FROM stdin;
2	DEMFIRAT	2
3	automationChief	3
\.


--
-- Data for Name: crm_company; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_company (id, name, email, phone, address, country, website, "backgroundInfo", created_at) FROM stdin;
1	PEARLINS LLC							2024-03-31 14:12:01.941674+00
2	DEMFIRAT	demfirat@gmail.com						2024-03-31 14:12:01.941674+00
6	Ashley Wilde	info@ashleywildegroup.com	+44 (0)1707 635	Emmanuel House Travellers	UK	https://ashleywildegroup.com/contact/		2024-04-05 19:41:33.719252+00
47	Holland Haag B.V.	info@hollandhaag.nl	+31 182 569 600	Coenecoop 801  2741 PW Waddinxveen  Netherlands		www.hollandhaag.nl		2024-04-25 19:07:43.97099+00
48	Laguna Lakástextil Kft.	info@lagunatextil.com	+36 94 508 710	Szombathely, Minerva u. 3.	Hungary	https://www.lagunatextil.com/en		2024-04-25 19:15:57.017666+00
59	Edmund Bell & Co. Ltd.	sales@edmundbell.com	+44 1706 71707	John Boyd Dunlop Drive Unit E1A, Kingsway Business Park  OL16 4NG Rochdale  Great Britain and Northern Ireland		www.edmundbell.com		2024-04-25 20:35:57.450481+00
61	INDETEX	sales@indetex.be	+32 (0)56 21 88	Rue du Mont Gallois 58 B-7700 Mouscron	Spain	https://www.indetex.be/en/contact-us		2024-04-28 07:06:59.874719+00
51	Milonas Textiles SA	info@milonas.gr	+30 21 0283 402	Metamorfosi Hermou 9  14452 Attiki  Greece	Greece	www.milonas.gr		2024-04-25 19:37:13.797509+00
52	Rovitex Homedeko Kft	rovitex@rovitex.com	+36 (72) 547 10	Reménypuszta 8  7631 Pécs  Hungary		www.rovitex.com		2024-04-25 19:42:06.171906+00
53	UNLAND International GmbH	info@unland.de	+49 4492 880	Gerhard-Unland-Str. 1  26683 Saterland		www.unland.de		2024-04-25 19:53:42.243687+00
27	Chicca Orlando	info@chiccaorlando.it	+390833505037	Via Ricasoli, 11, Casarano, 73042 Lecce	Italy	https://www.chiccaorlando.eu/ww/en/contact	HomeTex 2024 Exhibitor	2024-04-19 04:30:42.582394+00
28	Danzo Tex	carlo@danzotex.it	(+39) 0445 4024	DANZO S.R.L. Via Terragli, 12, 36078 Valdagno (VI) (+39) 0445 402411 C.F. e P.IVA IT02252100249	Italy	https://danzotex.it/en/fabrics/		2024-04-22 05:30:10.353998+00
29	Casalegno Tendaggi	info@casalegno.it	+39 011 9476211	Via Galatea, 14, 10023 Chieri TO, Italia	Italy	http://www.casalegno.it/contatti.php		2024-04-22 05:32:28.377294+00
30	Castiglioni Srl	info@castiglioni.it	+39.0331.463200	Via A. Grandi, 2, 20020 Arconate – Milano (Italy)	Italy	https://www.castiglioni.it/en/contacts/		2024-04-22 05:36:04.670893+00
31	Centro Tendaggi Arredamento srl	michele@ctasrl.com	+39 080.5586884	Via Amendola, 160 Bari (BA)	Italy	https://www.ctasrl.com/contatti.htm		2024-04-22 05:37:44.278996+00
32	Gruppo Carillo S.p.A. - Via Roma 60	info@viaroma60.it	+39 081.0146003		Italy	https://www.viaroma60.it/contacts/		2024-04-22 05:38:59.483458+00
55	Wölfel & Co. GmbH & Co. KG	verkauf@woelfel-gardinen.de	+49 6257 9410	Sandwiesenstr. 1  64665 Alsbach-Hähnlein  Germany		www.woelfel-gardinen.de		2024-04-25 20:00:52.355525+00
35	Hometesis -  Tesis s.r.l.	info@hometesis.it	+39 344.2620568	CIS di Nola - Isola 5 - Lotto 507 80035 - Nola (NA)	Italy	http://www.hometesis.it/contact.php		2024-04-22 05:51:22.221952+00
34	Zenoni Colombi	web@zenoniecolombi.com	+39 035 7534	Via Raul Follerau, 8  24027 Nembro BG, Italy	Italy	https://www.zenoniecolombi.com/en-en/pages/contact		2024-04-22 05:49:01.978009+00
36	Familia Service	info@familiaservice.it	+49 3283847890	Via Tosio 1/F, 25121 Brescia (BS)	Italy	https://familiaservice.it/prodotto/tendone-margherite-200x290/		2024-04-22 05:53:45.984203+00
37	Tendaggi Paradiso srl	nofire@tendaggiparadiso.com	+39 031 881 267	VAT N° IT00694080136 Fiscal Code 00694080136 REA CO 157961 Reg. Impr. CO 075 12056 – M. CO 015420 Share Capital €208.000,00 int ver	Italy	https://www.tendaggiparadiso.com/en/contact/		2024-04-22 05:55:11.495388+00
38	Gustav Gerster GmbH & Co. KG	export@gerster.com	+49 7351 586-50	Memminger Strasse 18 88400 Biberach/Riss	GERMANY	https://www.gerster.com/en/contact/		2024-04-22 05:56:25.177963+00
39	Woelfelco	w7info@aol.com	+49 (0) 6257/94	Sandwiesenstr. 1 64665 Alsbach-Hähnlein	Germany	https://www.woelfelco.de/kontakt-und-anfahrt/		2024-04-22 05:57:50.561096+00
40	HAFT	pgrzanka@haft.com.pl	+48 62 768 66 8	62-800 Kalisz, ul. Złota 40	Poland	http://haft.com.pl/en/contact/		2024-04-22 05:59:22.172494+00
42	EuroFirany	reklamacje@sklep.eurofirany.com.pl	+48 572 661 174	street Sienkiewicza 81, 34-300 Żywiec District Court in Bielsko-Biała, 8th Department. Gosp. KRS under KRS number: 0000246287	Poland	https://www.eurofirany.com.pl/kontakt		2024-04-22 14:52:10.948603+00
43	Egger	info@eggertextiles.nl	+31(0)85 822 39	Industriestraat 19  7891 GV Klazienaveen	Netherlands	https://www.eggertextiles.nl/		2024-04-23 13:14:05.592214+00
44	Ets Albert Guegain et Fils Sas	mguegain@nordnet.fr	+33 3 27 82 01	3 rue de la République 59142 Villers-Outréaux FRANCE		https://guegain.fr/agents/		2024-04-23 13:39:35.768186+00
45	GIANNOPOULOS BROS S.A.	sales@gbtextiles.gr	2105319952	Main Office: 2 Averof Str & Iera Odos Aven. Zip code: 12244 Area: Egaleo	Greece	http://www.gbtextiles.gr/		2024-04-25 18:59:09.138522+00
46	Hohmann GmbH & Co. KG	info@hohmann-weberei.de	+49 9252 7000	Bärenbrunn 4  95233 Helmbrechts  Germany	Germany	http://www.hohmann-weberei.de/		2024-04-25 19:04:57.070608+00
49	Lyndale International Inc.	info@lyndaledecor.com	+1 905-258-0031	145 Riviera Dr. Unit 5 Markham, ON L3R 5J6 Canada	Canada	https://www.lyndaledecor.com/html/contact-us.html		2024-04-25 19:21:07.354731+00
56	Lodetex S.P.A.	info@lodetex.it	+39 0331 352211	Via Tibet 21  21052 Busto Arsizio  Italy		www.lodetex.it		2024-04-25 20:24:32.564939+00
57	PYTON SLU	pyton@pyton.com	+34 936 35 31 0	C/ Terol, 9, Pol. Ind. Les Salines  08830 Sant Boi de LLobregat  Spain	Spain	https://pytoncontract.com/en/contact/		2024-04-25 20:27:39.069147+00
58	Wintex S.r.l.	info@wintexsrl.com		Via Valsorda 9  22044 Inverigo  Italy	Italy	www.wintexsrl.com		2024-04-25 20:31:05.577874+00
60	Hijos de Antonio Ferre S.A	aferre@aferre.com	+34 966 56 74 2	Avenida les Molines 2  03450 Banyeres de Mariola  Spain		https://www.aferre.com/en/contact/		2024-04-25 20:40:17.175794+00
50	Markizeta Sp. z o.o.	k.durda@markizeta.com.pl	+48 882 625 647	Jana Pawła II 128  39-451 Skopanie  Poland		www.markizeta.com.pl		2024-04-25 19:26:26.377192+00
41	Margo Textil	biuro@margo.com.pl	+48 58 511 05 7	Rusocin, ul. Dekarska 4 83-031 Łęgowo	Poland	https://www.margo.com.pl/kontakt-2/	zamowienia@margo.com.pl	2024-04-22 06:02:37.793779+00
33	Simta	info@simtaspa.com	+39.011.7424530	10149 - Corso Svizzera, 185	Italy			2024-04-22 05:44:33.656992+00
62	Level Fabrics S.L.	info@levelfabrics.com	+34 981 06 97 2	Via de la Cierva, 5                    Poligono Ind. Del Tambre                    15890 Santiago de Compostela	Spain	https://levelfabrics.com/en_gb/#prev		2024-04-28 07:23:17.649173+00
63	Juan Campos, S.A.	info@juancampos.com	+34 965 54 05	Avenida de Elche 40  03801 Alcoy  Spain		www.juancampos.com		2024-04-28 07:30:49.26255+00
64	Batangen Textiles	batangen@online.no	0047 41202574	Batangen textiles Brannvaktsgate 2 3256 Larvik Norway		www.batangen.com		2024-04-28 07:48:20.306379+00
65	MYB Textiles (GB)	contactus@mybtextiles.com	+44 (0)1560 321	Morton Young & Borland 14 Stoneygate Road Newmilns, Ayrshire United Kingdom KA16 9AL		www.mybtextiles.com		2024-04-28 08:26:00.303669+00
66	Stieger	info@stieger.com	+41 (0) 71 858	Neuseeland 32 B 9404 Rorschacherberg Schweiz		https://www.stieger.com/de/kontakt/	Proposte 2024	2024-04-28 08:30:53.527076+00
67	Yutes	yutes@yutes.com	(34) 934 732 6	08960 Sant Just Desvern Barcelona (Spain) Delante del edificio Walden 7		https://www.yutes.com/en/contact/		2024-04-28 09:02:39.418164+00
68	Woodline Saliveros	wsaliveros@gmail.com	+30 210 9888705	47 Posidonos Ave	Greece	www.woodline.gr		2024-05-03 07:43:54.97771+00
54	Viste Tu Hogar 2013 JI, SL	vistetuhogarweb@gmail.com	+34 688 00 17 6	Grinón Paseo Del Carraperal 152  28971 Madrid  Spain		https://vistetuhogar.com/collections/cortina-de-visillo		2024-04-25 19:56:18.05915+00
69	Ozlem Firany	biuro@ozlem-firany.com	+48 692 158 587	ul. Działkowa 115 / budynek D (magazyn nr 44, biuro nr 52) 02-234 Warszawa		https://ozlem-firany.com/index.html	warsaw home textile	2024-05-08 10:55:49.500135+00
70	Firany - Jordanów		+48509834572		Poland	https://maps.app.goo.gl/sAFnFty2V9xoLFnf7		2024-05-17 09:24:28.942089+00
71	Salon Firany Dana	salonfiranydana@gmail.com				https://firanyizaslony.pl/		2024-05-17 13:04:30.961951+00
72	Salon firan Bachowice	sklep@firanybachowice.pl	+48 609 166 703					2024-05-17 13:22:30.468899+00
73	Artis Firany	biuro@artis-firany.com.pl	+48 514-47-5757	SALON FIRAN ARTI'S UL. POLSKIEJ ORGANIZACJI WOJSKOWEJ 92/94 98-200 SIERADZ	Poland	http://www.artis-firany.com.pl/		2024-05-27 05:55:14.919671+00
74	P.H. Polder i Rajder Sp. j.	info@polderrajder.pl	+48 607 448 365	98-200 Sieradz, ul. Warcka 13	Poland	www.polderrajder.pl	HOMETEX 2024	2024-05-27 09:32:23.556769+00
75	Firany Elżbieta Marciniak		+48 501 507 177	Jagiellońska 13, 98-200 Sieradz, Poland	Poland			2024-05-27 09:40:02.661404+00
77	Tanie Firany i Tkaniny Włoskie		+48815321965	Zamojska 25, 20-102 Lublin, Poland				2024-05-27 10:06:53.908513+00
78	Sklep Dekoracje Okien	jarekdrapala@wp.pl	+48509505905	Diamentowa 4, 26-900 Aleksandrówka, Poland	Poland	http://firanydlaciebie.pl/		2024-05-27 10:52:41.82946+00
79	Firanki Radom	firankiradom@wp.pl	+ 48 517 937 35	• Artystyczne Szycie Firan Małgorzata Janas.   26-600 Radom, ul. Staroopatowska 24	Poland	https://firankiradom.pl/		2024-05-27 10:55:52.861633+00
80	Hakim Group	hakim_elnemrawy@yahoo.com	+20402439363	3km el-mahala beshbish road, el-mahala el kobra,Egypt	Egypt		HOMETEX 2024	2024-05-27 11:07:29.313311+00
81	My Home Albania	tabakuxulio27@yahoo.com	+355 6969 08607				Hometex 2024	2024-05-27 11:10:39.961257+00
84	zock mock company							2024-05-27 22:08:32.892484+00
85	Ala Salon Firan	biuro@alasalonfiran.pl	+4873033368	Pustyny ​​ul. Dukielska 148         38-422 Krościenko Wyżne (Podkarpackie)	Poland	https://www.alasalonfiran.pl/oferta/firany-i-tkaniny		2024-06-03 18:38:38.789585+00
86	Sklep Bogda	sklep@bogda.com.pl	17 242 17 99	ul. Żwirki i Wigury 4   37-300 Leżajsk	Poland	https://bogda.com.pl/pl/kontakt		2024-06-05 05:38:35.123553+00
76	De'Cor Pracownia Firan	decor@de-cor.pl	+48 579 078 070	Łaska 111, 98-220 Zduńska Wola, Poland	Poland	http://www.de-cor.pl/contact.html		2024-05-27 09:42:23.037978+00
87	E-Firany Wieliczka	a_siewruk@interia.pl	505 507 632	ul. Limanowskiego 20 32-020 Wieliczka	Poland	http://e-firany-wieliczka.pl/kontakt/		2024-06-05 07:13:16.913608+00
89	Marko Firany	hurt@markofirany.pl	601995900	Osiny, ul. Częstochowska 185 42-260 Kamienica Polska	Poland	http://www.markofirany.pl/#		2024-06-05 07:27:41.133938+00
90	Salon Firan Retro		+48 510 691 360	Rybnicka 64, 44-310 Radlin	Poland			2024-06-05 07:32:02.069123+00
91	Sarelli Textile				Italy			2024-06-05 20:09:59.10455+00
92	George's Company							2024-06-23 10:05:28.431575+00
93	GINÓ Lakástextil Kis	brillant.ginotex@gmail.com				https://www.facebook.com/ginotex.kis.nagyker/?locale2=hu_HU&_rdr		2024-07-04 08:10:16.32525+00
88	Decoriva Iwona Kaczor	info@decoriva.pl	+48 606 699 044	ul. Balicka 142a 30-149 Kraków	Poland	https://www.decoriva.pl/decoriva-krakow-szycie-firan-zaslon-rolet-kontakt		2024-06-05 07:20:37.798772+00
102	Abuzer Company							2024-07-21 21:03:23.781892+00
\.


--
-- Data for Name: crm_contact; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_contact (id, name, email, address, birthday, city, company_name, country, job_title, phone, state, zip_code, company_id, created_at) FROM stdin;
4	Firat			\N								2	2024-03-31 14:12:02.310233+00
1	Muhammed	muhammed@gmail.com	18021 Sky Park Cir Ste k	\N	irvine	PEARLINS LLC	USA		3237946484	ca	92614	1	2024-03-31 14:12:02.310233+00
6	abuzer			\N								\N	2024-07-21 20:41:05.7728+00
5	George	george@george.com		\N		George's Company 3		President				\N	2024-06-23 10:05:28.758093+00
\.


--
-- Data for Name: crm_note; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_note (id, content, created_at, contact_id, company_id, modified_date) FROM stdin;
4	note1	2024-03-21 22:06:24.686833+00	1	\N	2024-03-21 22:06:24.686833+00
5	note2	2024-03-21 22:06:30.946435+00	1	\N	2024-03-21 22:06:30.946435+00
6	note 3	2024-03-21 22:06:40.887313+00	1	\N	2024-03-21 22:06:40.887313+00
78	Reached to them via whatsapp	2024-05-17 09:24:29.129321+00	\N	70	2024-05-17 09:24:29.129321+00
12	firat	2024-03-21 22:58:29.575309+00	\N	2	2024-03-21 22:58:29.575309+00
79	Contact name is: Vittorio Cerruti. They got back to me today saying they are not interested.	2024-05-17 13:06:57.834503+00	\N	29	2024-05-17 13:06:57.834503+00
80	They ordered!	2024-05-26 21:38:22.218732+00	\N	68	2024-05-26 21:38:22.218732+00
81	This is a chinese company, why bother.	2024-05-26 22:22:02.899534+00	\N	64	2024-05-26 22:22:02.899534+00
82	You can contact them via phone later.	2024-05-27 05:55:14.998622+00	\N	73	2024-05-27 05:55:14.998622+00
32	My note for Pearlins LLC	2024-03-31 12:44:46.619381+00	\N	1	2024-03-31 12:44:46.619381+00
83	Contact name is Michal Derkacz\r\nHe said they are on holiday and they will get back to me in one week.	2024-05-27 09:32:23.632645+00	\N	74	2024-05-27 09:32:23.632645+00
84	Could not reach them	2024-05-27 10:06:53.984795+00	\N	77	2024-05-27 10:06:53.984795+00
33	my note edited again	2024-03-31 12:56:06.580739+00	\N	1	2024-04-03 21:41:18.823474+00
37	my new note	2024-04-03 22:20:56.648349+00	\N	1	2024-04-03 22:20:56.648349+00
38	adding note for DEMFIRAT	2024-04-03 22:34:12.555595+00	\N	2	2024-04-03 22:34:12.555595+00
39	adding note againnnn	2024-04-03 22:58:49.534571+00	\N	1	2024-04-03 22:58:49.534571+00
40	adding another note	2024-04-04 00:07:36.716999+00	\N	2	2024-04-04 00:07:36.716999+00
57	I wrote to them today.	2024-04-18 11:07:29.328456+00	\N	6	2024-04-18 11:07:29.328456+00
58	I contacted them yesterday via email.	2024-04-19 04:30:42.711893+00	\N	27	2024-04-19 04:30:42.711893+00
59	Other email: giulia@danzotex.it	2024-04-22 05:30:10.43716+00	\N	28	2024-04-22 05:30:10.43716+00
60	I followed up with them today.	2024-04-22 05:31:04.118102+00	\N	28	2024-04-22 05:31:04.118102+00
61	Turin\r\n\r\n10149 - Corso Svizzera, 185\r\n\r\nTel. 011.7424511 - Fax 011.7424544\r\n\r\ntorino@simtaspa.com\r\n------\r\n\r\nMilan\r\n\r\n20127 - Via Varanini, 28\r\n\r\nTel. 02.2820497 - Fax 02.26111116\r\n\r\nmilano@simtaspa.com\r\n\r\n------\r\n\r\nExport Department\r\n\r\n10149 - Corso Svizzera, 185\r\n\r\nTel. +39.011.7424530 - Fax +39.011.7424533\r\n\r\nsales@simtaspa.com	2024-04-22 05:44:33.785447+00	\N	33	2024-04-22 05:44:33.785447+00
62	They have many more emails if do not respond switch to them	2024-04-22 06:02:37.874334+00	\N	41	2024-04-22 06:02:37.874334+00
63	Sent them ready-made catalog.	2024-04-22 14:52:11.037562+00	\N	42	2024-04-22 14:52:11.037562+00
64	They claim to be a big wholesaler in the region, and their product line mostly matches ours.	2024-04-25 19:15:57.121226+00	\N	48	2024-04-25 19:15:57.121226+00
65	Seems to be very good match.	2024-04-25 19:27:33.633732+00	\N	50	2024-04-25 19:27:33.633732+00
66	They very similar ready-made collection to mine.	2024-04-25 19:56:18.161868+00	\N	54	2024-04-25 19:56:18.161868+00
67	Contact at this company is Ms. Susann Ellerbrock.	2024-04-25 20:00:52.490193+00	\N	55	2024-04-25 20:00:52.490193+00
68	They do hotel contracts.	2024-04-25 20:27:39.202634+00	\N	57	2024-04-25 20:27:39.202634+00
69	My contact here is: \r\nKouroupakis Joseph	2024-05-03 07:43:55.098651+00	\N	68	2024-05-03 07:43:55.098651+00
70	Diğer websitesinin ismi curtainportal.com	2024-05-08 11:04:08.863401+00	\N	69	2024-05-08 11:04:08.863401+00
71	They got back to me saying they are not interested.	2024-05-11 20:06:58.885613+00	\N	47	2024-05-11 20:06:58.885613+00
72	They got back to me saying they did not receive the catalogs. So resent them	2024-05-14 17:00:05.099732+00	\N	43	2024-05-14 17:00:05.099732+00
73	They got back to me asking me to resend the catalogs. So I sent another email.	2024-05-14 17:03:13.759737+00	\N	59	2024-05-14 17:03:13.759737+00
74	Contact name is Kay.	2024-05-14 17:03:37.365397+00	\N	59	2024-05-14 17:03:37.365397+00
75	Contact name is Rosana.	2024-05-14 17:18:02.253851+00	\N	63	2024-05-14 17:18:02.253851+00
76	not interested at this time	2024-05-14 17:18:29.27976+00	\N	63	2024-05-14 17:18:29.27976+00
77	Their contact name is: Agnieszka Kruk. They will visit us at HomeTex 2024.	2024-05-16 14:17:50.066582+00	\N	41	2024-05-16 14:17:50.066582+00
85	Contacts:\r\n\r\nHakim Elnemrawy\r\n+2 01224511396\r\n\r\nShereen Youseif\r\n+2 01210511192	2024-05-27 11:07:29.390492+00	\N	80	2024-05-27 11:07:29.391492+00
86	Two contacts here:\r\nXulio (Julio) and Emine	2024-05-27 11:10:40.03921+00	\N	81	2024-05-27 11:10:40.03921+00
87	They will come to Istanbul and visit my shop. They do home textiles.	2024-05-27 11:18:53.664958+00	\N	81	2024-05-27 11:18:53.664958+00
88	not interested	2024-05-27 13:16:03.733346+00	\N	53	2024-05-27 13:16:03.733346+00
89	Reached for the last time	2024-06-01 06:14:19.822806+00	\N	34	2024-06-01 06:14:19.822806+00
90	reached for the last time today.	2024-06-01 06:18:12.734636+00	\N	36	2024-06-01 06:18:12.734636+00
91	weird whatsapp couple photo. I will stay away.	2024-06-01 06:44:47.402052+00	\N	75	2024-06-01 06:44:47.402052+00
92	not the best	2024-06-01 06:47:14.979736+00	\N	70	2024-06-01 06:47:14.979736+00
93	reached for the last time	2024-06-03 08:41:30.618083+00	\N	59	2024-06-03 08:41:30.618109+00
94	not interested. \r\nTheir contact info is: \r\nElsa Huguet <ehuguet@pyton.com>	2024-06-03 09:27:16.337479+00	\N	57	2024-06-03 09:27:16.337494+00
95	Hard to to follow ups on whatsapp	2024-06-05 05:40:24.191126+00	\N	76	2024-06-05 05:40:24.192116+00
96	I found their email and website address.	2024-06-05 06:56:16.462588+00	\N	76	2024-06-05 06:56:16.462588+00
97	MY NOTE edited	2024-06-23 10:09:05.13275+00	5	\N	2024-06-23 10:12:06.34297+00
98	Me and dad went to her store. She exclusively buys from polish manufacturers. She does not need us.	2024-06-30 20:20:04.715923+00	\N	71	2024-06-30 20:20:04.715923+00
99	Bugun susnun hakkinda konustuk:sdasd\r\n123	2024-07-07 11:40:05.332131+00	\N	42	2024-07-07 11:40:05.33215+00
101	280 | 3l $4.15\r\n280 | 1l $2.95\r\n160 | 2l $2.60\r\n160 | 1l $1.95\r\n\r\n1421\r\n280 | 1l 4.15 USD\r\n160 | 1l $3.60	2024-07-16 13:35:13.136194+00	\N	74	2024-07-16 13:35:13.136213+00
102	I let him know about his order status and asked if he wants us to manufacture the plain fabric	2024-07-24 08:44:02.777963+00	\N	74	2024-07-24 08:44:02.777982+00
103	Their invoice should contain:\r\n\r\nFirst send the pro forma,\r\n\r\nDesign no, quantity, color, invoice no, incoterms, bank details, composition, origin info, description, price. \r\n\r\nThen after their payment, ask for their invoice address for the commercial invoice. Your commercial invoice should also contain the same information and should be in English.	2024-09-09 08:57:03.050745+00	\N	74	2024-09-09 08:57:03.050764+00
104	Next week they will market our products to their clients, they look to get some order.	2024-09-26 18:39:39.177913+00	\N	74	2024-09-26 18:39:39.177913+00
105	bugun	2024-11-13 14:22:15.798152+00	\N	74	2024-11-13 14:22:15.798152+00
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2024-03-21 23:04:24.499209+00	3	Firat	3		8	4
2	2024-03-21 23:04:24.598809+00	2	Firat	3		8	4
3	2024-03-22 09:51:25.441702+00	4	firat	2	[{"changed": {"fields": ["First name", "Last name"]}}]	4	4
4	2024-03-22 11:54:39.469668+00	3	Firat's third company	3		9	4
5	2024-03-22 12:06:37.571381+00	3	this my new task edited for | PEARLINS LLC	2	[{"changed": {"fields": ["Due date"]}}]	7	4
6	2024-03-22 12:07:07.11002+00	3	this my new task edited for | PEARLINS LLC	2	[{"changed": {"fields": ["Due date"]}}]	7	4
7	2024-03-22 23:39:20.886156+00	3	this my new task edited for | PEARLINS LLC	2	[{"changed": {"fields": ["Due date"]}}]	7	4
8	2024-04-03 23:35:51.884205+00	4	Firat	2	[{"changed": {"fields": ["Company"]}}]	8	4
9	2024-04-07 19:36:50.388971+00	14	FIRAT5	3		9	4
10	2024-04-07 19:36:50.544909+00	13	FIRAT4	3		9	4
11	2024-04-07 19:36:50.638818+00	12	FIRAT34	3		9	4
12	2024-04-07 19:36:50.748096+00	11	firat3	3		9	4
13	2024-04-07 19:36:50.848679+00	10	FIRAT3	3		9	4
14	2024-04-07 19:36:50.957401+00	9	FIRAT2	3		9	4
15	2024-04-07 19:36:51.058139+00	8	FIRAT2	3		9	4
16	2024-04-07 19:36:51.157982+00	7	FIRAT	3		9	4
17	2024-04-07 19:37:05.270003+00	5	firat's 4th company	3		9	4
18	2024-04-07 19:37:05.370581+00	4	aa	3		9	4
19	2024-04-09 20:38:43.34334+00	23	Write to them Ashley Wilde for | Ashley Wilde	2	[]	7	4
20	2024-04-09 22:28:41.814006+00	28	future task	3		7	4
21	2024-04-09 22:28:41.919897+00	27	new task	3		7	4
22	2024-04-09 22:28:42.032998+00	26	write to them for | Lyndale International Inc.	3		7	4
23	2024-04-09 22:28:42.134017+00	24	Write to them today for | DEMFIRAT	3		7	4
24	2024-04-09 22:28:42.238591+00	23	Write to them Ashley Wilde for | Ashley Wilde	3		7	4
25	2024-04-09 22:28:42.337569+00	22	todo for demfirat for | DEMFIRAT	3		7	4
26	2024-04-09 22:28:42.438942+00	20	my new task 3 for | PEARLINS LLC	3		7	4
27	2024-04-09 22:28:42.538058+00	19	my other task for pearlins for | PEARLINS LLC	3		7	4
28	2024-04-09 22:28:42.637533+00	18	my task for pearlins EDITTT for | PEARLINS LLC	3		7	4
29	2024-04-09 22:28:42.737897+00	16	my task updated for | PEARLINS LLC	3		7	4
30	2024-04-09 22:28:42.866619+00	13	trying to add pearlins a new task for | PEARLINS LLC	3		7	4
31	2024-04-09 22:28:42.976312+00	11	new task added for | PEARLINS LLC	3		7	4
32	2024-04-09 22:28:43.078484+00	10	Another task for | PEARLINS LLC	3		7	4
33	2024-04-09 22:28:43.220603+00	8	pearlins' task for | PEARLINS LLC	3		7	4
34	2024-04-09 22:28:43.327705+00	6	task that is due today	3		7	4
35	2024-04-09 22:28:43.426928+00	5	task forn	3		7	4
36	2024-04-09 22:28:43.527625+00	4	my new task	3		7	4
37	2024-04-09 22:28:43.627121+00	3	this my new task edited for | PEARLINS LLC	3		7	4
38	2024-04-09 22:28:43.729041+00	2	did that	3		7	4
39	2024-04-09 22:28:43.828161+00	1	DO that	3		7	4
40	2024-04-09 22:28:54.307845+00	29	future task for demfirat for | DEMFIRAT	3		7	4
41	2024-04-12 20:04:16.492293+00	51	adding new task for today	3		7	4
42	2024-04-12 20:04:16.604216+00	50	future task for | PEARLINS LLC	3		7	4
43	2024-04-12 20:04:16.706967+00	49	today's task for | PEARLINS LLC	3		7	4
44	2024-04-12 20:04:16.813891+00	48	due today2 for | mock10	3		7	4
45	2024-04-12 20:04:16.917262+00	47	due yesterday2 for | mock10	3		7	4
46	2024-04-12 20:04:17.045675+00	46	Due tomorrow for | mock10	3		7	4
47	2024-04-12 20:04:17.147888+00	45	due today for | mock10	3		7	4
48	2024-04-12 20:04:17.24692+00	44	due yesterday for | mock10	3		7	4
49	2024-04-12 20:04:17.345952+00	43	task for | mock10	3		7	4
50	2024-04-12 20:04:17.446875+00	42	dwee for | mock9	3		7	4
51	2024-04-12 20:04:17.549731+00	41	dddd for | mock8	3		7	4
52	2024-04-12 20:04:17.645177+00	40	initial task for | mock7	3		7	4
53	2024-04-12 20:04:17.745747+00	39	asdsad for | mock5	3		7	4
54	2024-04-12 20:04:17.845271+00	38	asdsad for | mock5	3		7	4
55	2024-04-12 20:04:17.959909+00	37	MY TASK for | MOCK4	3		7	4
56	2024-04-12 20:04:18.064981+00	36	MY TASK for | MOCK4	3		7	4
57	2024-04-12 20:04:18.165548+00	35	future task general	3		7	4
58	2024-04-12 20:04:18.269934+00	34	present task general	3		7	4
59	2024-04-12 20:04:18.368329+00	33	past task general	3		7	4
60	2024-04-12 20:04:18.472103+00	32	future task for pearlins for | PEARLINS LLC	3		7	4
61	2024-04-12 20:04:18.692608+00	31	present task for pearlins for | PEARLINS LLC	3		7	4
62	2024-04-12 20:04:18.79554+00	30	past task for pearlins for | PEARLINS LLC	3		7	4
63	2024-04-22 05:49:43.947765+00	34	Hometesis	2	[{"changed": {"fields": ["Company Name (required)"]}}]	9	4
64	2024-04-22 05:50:17.568887+00	34	Zenoni Colombi	2	[{"changed": {"fields": ["Company Name (required)"]}}]	9	4
65	2024-04-22 05:52:25.401645+00	34	Zenoni Colombi	2	[{"changed": {"fields": ["Website"]}}]	9	4
66	2024-04-25 18:50:01.434424+00	26	mock10	3		9	4
67	2024-04-25 18:50:01.545806+00	25	mock9	3		9	4
68	2024-04-25 18:50:01.648688+00	24	mock8	3		9	4
69	2024-04-25 18:50:01.747656+00	23	mock7	3		9	4
70	2024-04-25 18:50:01.846751+00	22	mock6	3		9	4
71	2024-04-25 18:50:01.94867+00	21	mock5	3		9	4
72	2024-04-25 18:50:02.04879+00	20	MOCK4	3		9	4
73	2024-04-25 18:50:02.148698+00	19	mock3	3		9	4
74	2024-04-25 18:50:02.249443+00	18	mock2	3		9	4
75	2024-04-25 18:50:02.349451+00	17	mock	3		9	4
76	2024-04-25 20:22:34.23323+00	15	Lyndale International Inc.	3		9	4
77	2024-04-25 20:22:48.640718+00	49	Lyndale International Inc.	2	[{"changed": {"fields": ["Country"]}}]	9	4
78	2024-04-26 07:20:33.902506+00	50	Markizeta Sp. z o.o.	2	[{"changed": {"fields": ["Email"]}}]	9	4
79	2024-04-26 08:03:47.278541+00	41	Margo Textil	2	[{"changed": {"fields": ["Email", "Background info"]}}]	9	4
80	2024-04-26 08:42:45.796108+00	33	Simta	2	[{"changed": {"fields": ["Email"]}}]	9	4
81	2024-04-28 07:04:55.394636+00	16	Centro Tendaggi Arredamento srl	3		9	4
82	2024-05-06 20:16:01.370417+00	54	Viste Tu Hogar 2013 JI, SL	2	[{"changed": {"fields": ["Email"]}}]	9	4
83	2024-06-05 06:57:06.349473+00	76	De'Cor Pracownia Firan	2	[{"changed": {"fields": ["Email", "Website", "Country"]}}]	9	4
84	2024-06-29 21:54:15.300871+00	1	Muhammed	2	[{"changed": {"fields": ["Job Title"]}}]	8	4
85	2024-06-29 21:54:17.723117+00	1	Muhammed	2	[]	8	4
86	2024-06-29 22:17:09.889758+00	1	Muhammed	2	[{"changed": {"fields": ["Job Title"]}}]	8	4
87	2024-06-29 22:17:46.81009+00	1	Muhammed	2	[{"changed": {"fields": ["Job Title"]}}]	8	4
88	2024-06-29 22:18:29.227221+00	1	Muhammed	2	[{"changed": {"fields": ["Job Title"]}}]	8	4
89	2024-07-17 21:47:11.556574+00	4		3		12	4
90	2024-07-17 21:59:14.58804+00	14	- 10.00 - 2024-07-15	3		13	4
91	2024-07-17 21:59:14.706447+00	13	- 15.00 - 2024-07-15	3		13	4
92	2024-07-17 21:59:14.808426+00	12	- 5.00 - 2024-07-15	3		13	4
93	2024-07-17 21:59:14.927616+00	11	- 10.00 - 2024-07-15	3		13	4
94	2024-07-17 21:59:15.027514+00	3	past expense - 5.00 - 2024-06-30	3		13	4
95	2024-07-17 21:59:15.137848+00	2	My other expense - 5.00 - 2024-07-01	3		13	4
96	2024-07-17 21:59:15.237019+00	1	advertising - 20.20 - 2024-07-06	3		13	4
97	2024-07-19 12:18:50.911058+00	1	USD	1	[{"added": {}}]	16	4
98	2024-07-19 12:19:13.038879+00	2	EUR	1	[{"added": {}}]	16	4
99	2024-07-19 12:19:20.67022+00	3	TL	1	[{"added": {}}]	16	4
100	2024-07-19 12:43:16.301212+00	1	Advertising	1	[{"added": {}}]	12	4
101	2024-07-19 12:43:25.530467+00	2	Car and Truck Expenses	1	[{"added": {}}]	12	4
102	2024-07-19 12:43:37.550364+00	3	Comissions and fees	1	[{"added": {}}]	12	4
103	2024-07-19 12:44:31.241465+00	4	Legal and Professional Services	1	[{"added": {}}]	12	4
104	2024-07-19 12:44:44.592021+00	5	Office expense	1	[{"added": {}}]	12	4
105	2024-07-19 12:45:07.803037+00	6	Repairs and Maintanence	1	[{"added": {}}]	12	4
106	2024-07-19 12:45:29.333549+00	6	Repairs and Maintenance	2	[{"changed": {"fields": ["Name"]}}]	12	4
107	2024-07-19 12:45:52.403443+00	7	Supplies	1	[{"added": {}}]	12	4
108	2024-07-19 12:46:06.544523+00	8	Taxes and Licenses	1	[{"added": {}}]	12	4
109	2024-07-19 12:46:13.924631+00	9	Travel and Meals	1	[{"added": {}}]	12	4
110	2024-07-19 12:46:22.373952+00	10	Utilities	1	[{"added": {}}]	12	4
111	2024-07-19 12:46:33.332835+00	11	Other expenses	1	[{"added": {}}]	12	4
112	2024-07-19 19:52:09.072722+00	1	Revenue	1	[{"added": {}}]	14	4
113	2024-07-19 19:52:18.697407+00	2	Capital	1	[{"added": {}}]	14	4
114	2024-07-19 21:28:35.758719+00	11	1.00 USD - 20 July, 2024 - Revenue	3		15	4
115	2024-07-19 21:28:36.370266+00	10	0.30 USD - 20 July, 2024 - Revenue	3		15	4
116	2024-07-19 21:28:36.605732+00	9	8.56 USD - 20 July, 2024 - Revenue	3		15	4
117	2024-07-19 21:28:36.912554+00	8	3.00 USD - 20 July, 2024 - Revenue	3		15	4
118	2024-07-19 21:28:37.625591+00	7	2.00 USD - 19 July, 2024 - Revenue	3		15	4
119	2024-07-19 21:28:37.913936+00	6	10.00 USD - 19 July, 2024 - Revenue	3		15	4
120	2024-07-19 21:28:38.762538+00	5	3.00 USD - 19 July, 2024 - Revenue	3		15	4
121	2024-07-19 21:28:39.506347+00	4	2.00 USD - 19 July, 2024 - Revenue	3		15	4
122	2024-07-19 21:28:40.055746+00	3	2.00 USD - 19 July, 2024 - Revenue	3		15	4
123	2024-07-19 21:28:40.731289+00	2	2.00 USD - 19 July, 2024 - Revenue	3		15	4
124	2024-07-19 21:28:41.167607+00	1	1.00 USD - 19 July, 2024 - Revenue	3		15	4
125	2024-07-21 20:53:42.624326+00	101	abuze company	3		9	4
126	2024-07-26 21:49:04.11691+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
127	2024-07-26 22:01:23.722899+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
128	2024-07-26 22:03:04.092992+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
129	2024-07-26 22:05:00.489364+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
130	2024-07-26 22:06:36.827253+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
131	2024-07-26 22:07:59.369681+00	5	George	2	[{"changed": {"fields": ["Company"]}}]	8	4
132	2024-08-25 04:28:19.805482+00	3	All	1	[{"added": {}}]	17	4
133	2024-08-25 04:32:01.899059+00	7	Book: Karven - 1.00 USD - 24 August, 2024 - Revenue	3		15	4
134	2024-08-25 04:32:02.003625+00	4	Book: Karven - 5.00 USD - 10 August, 2024 - Revenue	3		15	4
135	2024-08-25 04:32:02.117242+00	3	Book: Karven - 300.00 USD - 10 August, 2024 - Revenue	3		15	4
136	2024-08-25 04:32:02.222699+00	2	Book: Karven - 500.00 USD - 10 August, 2024 - Revenue	3		15	4
137	2024-08-25 04:32:02.338504+00	1	Book: Karven - 5.00 USD - 10 August, 2024 - Revenue	3		15	4
138	2024-08-25 16:40:22.159156+00	3	All	3		17	4
139	2024-08-25 17:42:20.699784+00	2	Muhammed Firat Ozturk	2	[{"changed": {"fields": ["Name"]}}]	17	4
140	2024-08-25 17:42:35.289094+00	1	Pearlins LLC	2	[{"changed": {"fields": ["Name"]}}]	17	4
141	2024-09-08 14:36:18.625593+00	2	Book: Muhammed Firat Ozturk, Asset name: House	3		22	4
142	2024-09-08 14:42:00.957169+00	3	Book: Muhammed Firat Ozturk, Asset name: House	3		22	4
143	2024-09-28 23:11:19.296862+00	1	Muhammed Firat Ozturk | CB | USD	3		27	4
144	2024-09-28 23:11:39.757667+00	10	Pearlins LLC | CB | USD	1	[{"added": {}}]	27	4
145	2024-10-01 11:34:23.270208+00	1	Name: Muhammed | Book: Pearlins LLC | Share: 1.00	3		30	4
146	2024-10-01 11:48:26.889026+00	3	Name: Firat2 | Book: accounting.Book.None | Share: 1.00	3		30	4
147	2024-10-01 11:48:45.236334+00	2	Name: Firat | Book: accounting.Book.None | Share: 1.00	2	[{"changed": {"fields": ["Book"]}}]	30	4
148	2024-10-01 11:48:56.724762+00	2	Name: Muhammed | Book: accounting.Book.None | Share: 1.00	2	[{"changed": {"fields": ["Name"]}}]	30	4
149	2024-10-01 11:49:44.002269+00	2	Name: Muhammed | Book: None | Share: 1.00	2	[{"changed": {"fields": ["Book"]}}]	30	4
150	2024-10-01 11:49:54.807516+00	2	Name: Muhammed | Book: None | Share: 1.00	2	[{"changed": {"fields": ["Book"]}}]	30	4
151	2024-10-01 11:52:08.080919+00	4	Name: Muhammed | Book: accounting.Book.None | Share: 1.00	3		30	4
152	2024-10-01 11:52:08.154901+00	2	Name: Muhammed | Book: accounting.Book.None | Share: 1.00	3		30	4
153	2024-10-02 10:30:09.320793+00	2	USD5.00 | Muhammed	3		29	4
154	2024-10-06 06:01:00.501995+00	1	Muhammed	3		30	4
155	2024-10-06 06:28:34.322224+00	2	Karven	2	[{"changed": {"fields": ["Name"]}}]	17	4
156	2024-10-06 06:28:44.377042+00	1	Pearlins LLC	2	[{"changed": {"fields": ["Name"]}}]	17	4
157	2024-10-06 06:47:56.783542+00	1	CB | USD - US Dollar | balance: 0.00 (Pearlins LLC)	2	[{"changed": {"fields": ["Book"]}}]	27	4
158	2024-10-06 07:39:42.047646+00	10	onHand | USD - US Dollar | balance: 0 (Pearlins LLC)	1	[{"added": {}}]	27	4
159	2024-10-06 07:42:24.732431+00	10	On Hand | USD - US Dollar | balance: 0.00 (Pearlins LLC)	2	[{"changed": {"fields": ["Name"]}}]	27	4
160	2024-10-15 18:29:10.704821+00	2	Muhammed Firat Ozturk	2	[{"changed": {"fields": ["Share"]}}]	30	4
161	2024-10-15 19:21:18.818997+00	4	frrrre	3		30	4
162	2024-10-15 19:21:19.034017+00	3	fr	3		30	4
163	2024-10-15 19:24:39.705776+00	6	233	3		30	4
164	2024-10-15 19:24:39.949728+00	5	22	3		30	4
165	2024-11-16 12:00:11.69475+00	11	A/P | Balance: $0 (Pearlins LLC)	1	[{"added": {}}]	27	4
166	2024-11-16 12:12:51.412287+00	1	CB | Balance: $100 (Pearlins LLC)	2	[{"changed": {"fields": ["Balance"]}}]	27	4
167	2024-11-16 12:33:54.146406+00	1	Book: Pearlins LLC - 20.00 USD - US Dollar - 16 November, 2024 - Comissions and Fees	3		13	4
168	2024-11-16 22:56:13.048025+00	4	Book: Pearlins LLC - 5.00 USD - US Dollar - 17 November, 2024 - Advertising	3		13	4
169	2024-11-16 22:56:13.186122+00	3	Book: Pearlins LLC - 5.00 USD - US Dollar - 16 November, 2024 - Comissions and Fees	3		13	4
170	2024-11-16 22:56:13.338044+00	2	Book: Pearlins LLC - 20.00 USD - US Dollar - 16 November, 2024 - Office Expense	3		13	4
171	2024-11-16 22:56:30.939753+00	6	Book: Pearlins LLC - 1.00 USD - US Dollar - 17 November, 2024 - Contract Labor	3		13	4
172	2024-11-16 22:56:56.180271+00	1	CB | Balance: $100 (Pearlins LLC)	2	[{"changed": {"fields": ["Balance"]}}]	27	4
173	2024-11-16 22:58:26.330762+00	1	CB | Balance: $1000 (Pearlins LLC)	2	[{"changed": {"fields": ["Balance"]}}]	27	4
174	2024-11-17 21:12:49.501235+00	1	MT	1	[{"added": {}}]	25	4
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	todo	task
8	crm	contact
9	crm	company
10	crm	note
11	authentication	member
12	accounting	expensecategory
14	accounting	incomecategory
15	accounting	income
16	accounting	currencycategory
17	accounting	book
19	operating	rawmaterial
20	operating	product
18	operating	rawmaterialcategory
21	operating	machine
22	accounting	asset
23	accounting	sale
24	accounting	account
25	operating	unitcategory
26	accounting	assetcategory
28	accounting	transaction
29	accounting	capital
30	accounting	stakeholder
31	accounting	source
32	accounting	equity
33	accounting	liability
34	accounting	equity_capital
27	accounting	cashaccount
35	accounting	equitycapital
13	accounting	equityexpense
36	accounting	equityrevenue
37	accounting	equitydivident
38	accounting	invoice
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2024-01-25 18:31:13.086551+00
2	auth	0001_initial	2024-01-25 18:31:36.245006+00
3	admin	0001_initial	2024-01-25 18:31:42.994169+00
4	admin	0002_logentry_remove_auto_add	2024-01-25 18:31:45.643693+00
5	admin	0003_logentry_add_action_flag_choices	2024-01-25 18:31:48.352611+00
6	contenttypes	0002_remove_content_type_name	2024-01-25 18:31:52.710161+00
7	auth	0002_alter_permission_name_max_length	2024-01-25 18:31:56.765458+00
8	auth	0003_alter_user_email_max_length	2024-01-25 18:32:00.561775+00
9	auth	0004_alter_user_username_opts	2024-01-25 18:32:03.72187+00
10	auth	0005_alter_user_last_login_null	2024-01-25 18:32:07.674846+00
11	auth	0006_require_contenttypes_0002	2024-01-25 18:32:11.073219+00
12	auth	0007_alter_validators_add_error_messages	2024-01-25 18:32:14.282989+00
13	auth	0008_alter_user_username_max_length	2024-01-25 18:32:19.222305+00
14	auth	0009_alter_user_last_name_max_length	2024-01-25 18:32:22.993851+00
15	auth	0010_alter_group_name_max_length	2024-01-25 18:32:27.274966+00
16	auth	0011_update_proxy_permissions	2024-01-25 18:32:30.114891+00
17	auth	0012_alter_user_first_name_max_length	2024-01-25 18:32:33.45759+00
18	authentication	0001_initial	2024-01-25 18:32:37.713743+00
19	authentication	0002_alter_member_user	2024-01-25 18:32:44.075312+00
20	authentication	0003_rename_company_member_company_name	2024-01-25 18:32:48.55529+00
21	crm	0001_initial	2024-01-25 18:32:52.922441+00
22	crm	0002_contact_email	2024-01-25 18:32:57.768733+00
23	crm	0003_contact_address_contact_birthday_contact_city_and_more	2024-01-25 18:33:14.679842+00
24	crm	0004_company_note_contact_company	2024-01-25 18:33:22.287694+00
25	crm	0005_alter_contact_company	2024-01-25 18:33:23.754732+00
26	crm	0006_rename_text_note_content	2024-01-25 18:33:26.562506+00
27	crm	0007_note_company_alter_note_contact	2024-01-25 18:33:35.154927+00
28	crm	0008_alter_contact_options	2024-01-25 18:33:36.955114+00
29	crm	0009_note_modified_date	2024-01-25 18:33:40.804939+00
30	sessions	0001_initial	2024-01-25 18:33:46.194073+00
31	todo	0001_initial	2024-01-25 18:33:49.080203+00
32	todo	0002_task_company_task_contact	2024-01-25 18:33:55.115312+00
33	todo	0003_rename_task_name_task_name	2024-01-25 18:33:58.034836+00
34	todo	0004_alter_task_due_date	2024-01-25 18:34:00.635238+00
35	todo	0005_rename_name_task_task_name	2024-01-25 18:34:04.514203+00
36	todo	0006_task_contact_company_id	2024-01-25 18:34:08.443114+00
37	todo	0007_remove_task_contact_company_id	2024-01-25 18:34:11.874015+00
38	todo	0008_task_days_since_due	2024-01-25 18:34:15.614564+00
39	crm	0010_company_backgroundinfo_alter_company_name_and_more	2024-03-22 11:29:03.518246+00
40	todo	0009_alter_task_description	2024-03-26 19:15:55.22582+00
41	crm	0011_company_created_at_contact_created_at	2024-03-31 14:12:02.696999+00
42	crm	0012_alter_company_website	2024-04-09 20:33:57.481972+00
43	todo	0010_remove_task_days_since_due	2024-04-09 22:30:26.147854+00
44	crm	0013_remove_company_city_remove_company_state_and_more	2024-05-27 22:07:58.604653+00
63	operating	0001_initial	2024-08-10 14:38:46.774592+00
64	operating	0002_rename_rawmaterialcategorys_rawmaterialcategory	2024-08-10 14:39:40.694096+00
65	operating	0003_rawmaterial_type	2024-08-10 15:01:52.522342+00
66	operating	0004_machine	2024-08-10 15:32:34.888547+00
67	operating	0005_product_machine	2024-08-10 15:34:26.230207+00
68	operating	0006_unitcategory_remove_product_machine_and_more	2024-08-25 20:00:41.092458+00
70	operating	0007_alter_product_sku	2024-08-25 20:59:01.033591+00
172	operating	0008_product_stock_quantity_product_variant_and_more	2024-11-17 21:04:07.281785+00
175	operating	0009_alter_product_name_alter_product_sku	2024-11-29 19:28:38.632753+00
176	operating	0010_product_manufactuer	2024-11-29 19:39:20.453401+00
177	operating	0011_rename_manufactuer_product_manufacturer	2024-11-29 19:39:38.585426+00
178	operating	0012_alter_product_raw_materials	2024-11-29 19:52:53.33065+00
179	operating	0013_product_created_at_alter_product_raw_materials	2024-11-30 11:06:52.481315+00
203	accounting	0023_equitydivident	2024-11-30 12:41:31.333994+00
204	accounting	0024_equitydivident_stakeholder	2024-11-30 12:41:31.553256+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
pybqswwcyebasqv65nssqgyljh8xrqnj	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sCyz5:Q8ff9QQqk_QXkDrD2Jy7sdNksn3ScIcDM3-QeMg0OZY	2024-06-14 09:55:39.849389+00
8vvc9jnqkolnc1imo796qrrv871znzj5	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sDMFT:G7j186wgYFOEiHZqzcvJcyXMrdpwnL-OG44ewUzNmXg	2024-06-15 10:46:07.729983+00
40ncrd5wk2dlicqdul3q7dfv8opp04sf	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sDMOy:WptcjtSnhH03OWVpBiCtHsazlgsZGUs8r8nV6pROrfM	2024-06-15 10:55:56.48325+00
1b3t7oxb2hu6y0dvef2oo6n7pjf9o7n4	.eJxVjMsOwiAQRf-FtSHAlAFcuvcbyPCSqoGktCvjv2uTLnR7zzn3xTxta_XbyIufEzszxU6_W6D4yG0H6U7t1nnsbV3mwHeFH3Twa0_5eTncv4NKo35rTTmBcxJtJEQVs7ISC4mklYlobADlDAAZGXMBmjQKwDIlgQY1WMHeH9TINu4:1rmxrO:CJ9qnatYK6tydHZUgRfGA06EnLDsnrjUU7s1MZrDoh8	2024-04-03 15:28:10.377932+00
oknrr0o405swqgp0ft4vuh4jriqbtta1	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sDNig:YMPnsxKtoxVsx_Hm4W5MyO6Dh4ky8F_o4n-BKqi2Bvk	2024-06-15 12:20:22.484146+00
xhqkj2trumj9yw8mo4lyw7p5xunphc38	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sFFDT:edmMlmQ9Ksye4C0A1R-N0L7o2xBXwAKMochypFFAnxU	2024-06-20 15:39:51.574995+00
79gb3fhl71qeel7u353xvro6e0qoyy5w	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sFFDU:FcckpDFYpkPPPdpl801sprCUXVhLd6dXU5fPjEpTiJo	2024-06-20 15:39:52.651358+00
p7v0uxnuxxxfaajuih328i8i461r1wtl	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sItKF:KuH6B--Bdp-msXmWB1cg4TiQ3R-rs_soY8x5s8BZI4o	2024-06-30 17:05:55.731223+00
xza6y7u7hey2qhwbc4uifhp2pstilgne	.eJxVjMsOwiAQRf-FtSHAlAFcuvcbyPCSqoGktCvjv2uTLnR7zzn3xTxta_XbyIufEzszxU6_W6D4yG0H6U7t1nnsbV3mwHeFH3Twa0_5eTncv4NKo35rTTmBcxJtJEQVs7ISC4mklYlobADlDAAZGXMBmjQKwDIlgQY1WMHeH9TINu4:1rnbzm:3iNW3XxuEogIExs2w4UfQueWVS004aKsyJd-m7yTQQM	2024-04-05 10:19:30.145069+00
luoi3tcom3s4r23ub9jxa4liz9zyeo35	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1rnc0G:gfKaGi7L4s5mO0T0MdfuL_bS3bis64wtN8vX37WgIug	2024-04-05 10:20:00.697021+00
ik3mpv9p73dynkpak66otjkwg194ma8q	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sJyKY:eCuyRQo6Yj12CyFPURpebs4ogCL82wVdg8awnwDToaE	2024-07-03 16:38:42.812598+00
t4bqitya8vdw1wz1x6bia59e6b8yn90u	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1rnm6R:yLZbEBm_GvsgiG_LUNlK4EtvKUdwkCTIbgCvk2NmDx0	2024-04-05 21:07:03.328123+00
0mq3xlirbhh20e9w3eje1273mpg78iqf	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1rpBeg:Lg953dp1Kub_TcWx1LT7GWWLKFp53mo65yzCvw0DUPU	2024-04-09 18:36:14.903576+00
krsq2dehu6ayn4lj5610xulehcjm1bwk	.eJxVjMsOwiAQRf-FtSHAlAFcuvcbyPCSqoGktCvjv2uTLnR7zzn3xTxta_XbyIufEzszxU6_W6D4yG0H6U7t1nnsbV3mwHeFH3Twa0_5eTncv4NKo35rTTmBcxJtJEQVs7ISC4mklYlobADlDAAZGXMBmjQKwDIlgQY1WMHeH9TINu4:1rqsxQ:TafQYTpKS3G6_r_3hf4ilKo2I9zRaDEpONhXCb1b4OQ	2024-04-14 11:02:36.279358+00
w3wihyqpy3cd4tpk86m59emaqacepdf3	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1rvLTT:ZCg6vjuwEe9vGd8PJTzm8ULuTu63KBRQ5EwtVlcd7CE	2024-04-26 18:18:07.95775+00
egjhadaf24h2wcask70aklmgqpw78v89	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1rxMDv:SoHbL9WPPNcwL6zzQkKRQdnuwCKBc0GiHEDAQaqr-G4	2024-05-02 07:30:23.321134+00
h1uzn9ix6tsimwsvemob8ln7n0nfwvlj	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s0yVC:varV3rlwNkrOvrfOoTGsZ0xsJsp4g4mFYMpvqAM7D-0	2024-05-12 06:59:10.814756+00
wl5jf4apcp9j9q7zc6y7xvlezv7ofe5r	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s2UP0:DrRgLn53fj_IYCyf_ZEFPPRaPLJmUx5UljIenZQbrV8	2024-05-16 11:15:02.922742+00
3qrnv9vq571ivs1yvkgqvpnpwst87gwb	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s2nRN:P0y27Q88dJlWcKZte12expSUeWRZJ6GPT7GWSS4Jf8Y	2024-05-17 07:34:45.020866+00
7vu1v2aiuzy65tw2vb028orckia3rp87	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s2vx2:5p_ndxMi2beu4zSuXlG9_W9V7Pl8pQ493nTNio35JXw	2024-05-17 16:40:00.229993+00
y35vmyow0vpygo8pppdf51lbpan6868e	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s7c25:mAjf0t0zbTr9b6ZydqDVc4x3s5UW-YAx-tCWDJ0nyRo	2024-05-30 14:24:33.827938+00
exxbkmg2qvvqh94r6fpsrf0bj7pvt54m	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1s7taq:oaNWKXXmzMoA22ftFpiaGrchpsTXxKMiP6FfIdFPsQk	2024-05-31 09:09:36.9236+00
88i19b009qsnmxdeegzkjkw7xtltpdmw	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sBTFA:wv-c6JP9ntjMHdkHlnv3hiF5Fve0Z6DhS9bAdIKoX10	2024-06-10 05:50:00.374391+00
vjmx9nh67u5a5inwl389sftw4dzdqxjn	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sCyve:Mn9iWxzoeHXtnyMaZH6K7DZEUOvoA4zA6_--YmZ-NJE	2024-06-14 09:52:06.68019+00
lce09rojlkmby7rp2t3sjyv0zorczqf9	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sCyyW:USMAXJ9PScm2OKC5sSqhdg2ZtOrx9w4vCEGpoW_0suU	2024-06-14 09:55:04.389221+00
0pk6b9xxy7zk37fmxh0oea7mxigbwfnp	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sKGGa:HJ2Q-PkdUy13QVmwesZmknq9qdrOZVflE9SXQWTrSrI	2024-07-04 11:47:48.318731+00
3puiprkknbklelmd82gvp8sssqqqujs3	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sNzuE:0VzMOEAhXP9Xm5wZrPDnfMCgabSxjM8Bg54eDGjigjI	2024-07-14 19:08:10.555499+00
mm6crjlionhd5dusm7ck4085rypqv2pj	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sPHWT:5oFUtVhgt_A5Go3o6aierkdSZIHMcaG5IhcZzPsaIaM	2024-07-18 08:08:57.006082+00
o12o8xjyflszeakkakifdrj2ps31so5n	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sPSFX:goCD97tCbzmIJD3M0DOq2RcemT3QY_oQ88Y2EdGh4VU	2024-07-18 19:36:11.500303+00
irm03nu6rmal3jfwfaneaqkcu6wtaozh	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sPVDy:xxb_VV0mdqM6KdlvwbrnKO5vUCFvXTZMaN9H-iyrtZ0	2024-07-18 22:46:46.523555+00
fbil3xs1fvv7sycf9c6kyje88rjt1qji	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sQOdM:OndIjVzFYYnYaEeEgEfXACOZa_-VOso7GF24oVUV3_A	2024-07-21 09:56:40.48236+00
ux4sxtc2sg7spjygcf28oa05hbod9lhc	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sQOmZ:ZM3zZKP-umCzomxmlGDYExgo9uWyXS21ayJddT-KEAU	2024-07-21 10:06:11.314971+00
u8i28jt5suw0adi46f1snp0t8ivd7e94	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sQVBh:vWNBfAHlmErSF6pBK-Npku17NjIQ9LsnativC9TVark	2024-07-21 16:56:33.093732+00
24z1zh581yqdu8wsgf31l5qmmwr5fm81	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sQVBk:HloYCYsxaPv5I_xH2KyWfwHNHnYMj0xRYgIx7r3yLpo	2024-07-21 16:56:36.077691+00
j29lboqplaiatwcqpu0bhm5b036z55r7	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sTMlx:LuDzNt3eb1nIZC0gB1W1NUutdrR_4fuyaut2JXU_hA8	2024-07-29 14:33:49.010647+00
kuwgm3748m77h4z71q33sa4kry0rw9dp	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sTzmW:Psa6fnndIgPKLLCrWE1vlu_EyIsQrRimGN-PNNHfL2s	2024-07-31 08:13:00.82057+00
eslq6l2n5yr6jzb6yswm3ebfadt5s2xa	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sVaBr:Zc9NDUUJNL5OIB4Mj4_RvQdG-QhMCX8Nf5NzvX5A4FI	2024-08-04 17:17:43.429387+00
9j6lnjoik50kk7baypiqpz7t7eqno7m0	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sWF04:-9TDKod06N8zSt87IDIyNOGnEINZGGCUSGw8Zl9n2lM	2024-08-06 12:52:16.32423+00
hyfi29y3le55lvippjmbrue8vdhyqejp	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sX184:4duVqtcacNYdEWWwISEDjt7gD74XUr3Qklgol1FQt-E	2024-08-08 16:15:44.79464+00
0334n5e2b8fqtpw0tt54bpvloafw4j49	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1scZG4:uqtyY3uEpbpOIStejb_usZ0ZKpPFTOdQ1F8095kp4Nc	2024-08-23 23:42:56.188053+00
m0uyhzbn4j4jdmhvbs3fnbegxjllwaik	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1scvAG:zMaGqKogL3tMtxG6R98anAtiqbFcKURd17jqxTLAWyw	2024-08-24 23:06:24.183683+00
oy9jv69vw5i75xeu9qki60hyjw5wek9b	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1si4Ci:-dc0VuV1Av2_WICgx7DOMluVUw93i-soKfKZ6QXJXps	2024-09-08 03:46:12.320684+00
htbq0x8q8fnqaubv7ixu7wjkt8k8n1mt	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sjdvs:2TFbhSAJfvsvJ1Yi3AyG01hGUcaOXhKlltfY6Ov7l_o	2024-09-12 12:07:20.182436+00
gwv9qn3wm33m78nakhokhqvh3gc5krmm	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1snAIu:H9bC8nP5hP4mf-gFyw9wKChvLI3JjvO9oKGExP29uS0	2024-09-22 05:17:40.613411+00
16tlf0ldc0ssogqatomc3e7lzn9ldv4i	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1so5Ut:uc_GKAWBOc6eki2gucs5Y36NNxQePln3TFEPYMtXXz0	2024-09-24 18:21:51.050138+00
5guo5kuv69j6b7b5ht0v0aqhh3agk8tu	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1soJVZ:fOglwD9FLEffPL0cv9_snJ_5UDu7kZI-cLtJ7WMoDmE	2024-09-25 09:19:29.598997+00
g90xtgrdprjweri2yeuyk1ctdp6mwh1w	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sq97T:8F1sFj2qV7Bg2JlyeKvG3JDv9TfBEAqSGMHHnPT-lDk	2024-09-30 10:38:11.910019+00
an1vx3azi3jeo6pu1gakuzab18r0kvnv	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1ssWhG:OiusWQppS1EP0EsZvCAV003kklQHgec69onhJITHxss	2024-10-07 00:12:58.395623+00
eu7k7qxfg2gktvabtoo0gfm7mk3lywkt	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1stCyS:lFrkfPWd7XE_9_nTEG_YkJe185zATG6EG8MrOctXT0E	2024-10-08 21:21:32.823477+00
mvdjawt8xpfq2dzn4h42xmm5l9xivc58	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1su5DA:2zBFq-Nm2CvaiZcxGvHRzpucGMoEr9AXsiwStbHRWxk	2024-10-11 07:16:20.149804+00
3as7nb0oa289bxodoofbv3twye6ows7n	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1suCdi:dAYt6PMxWbcfFqSN1MLGGio9TACgoqG8KN1cge0Y2vY	2024-10-11 15:12:14.823529+00
qrdnm6dp7tola7q7z80nckzk1nkmbqkb	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1sw5Az:BHo3hRjWe1HU70ziMAGsKyZm4EJuFpJvUYfWzqH3ogs	2024-10-16 19:38:21.780953+00
9cgzba2xdq0jduot9kjnvylzgj6ufmnw	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1swL4w:DWBasvIINNMFZ6zhZUWai2GGeGBP8pB0Pgw2VgGK0QE	2024-10-17 12:37:10.990561+00
4hrn6mscl0jr10jeg2c7z9l2dbwebcie	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1swN4g:aTU36Vm0bD6Cc1FJskNO95RmlufCSFtStpawR2M2ssg	2024-10-17 14:45:02.44153+00
txt3twwgwzpj4zydsflrki76b7vlmgww	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1swN4g:aTU36Vm0bD6Cc1FJskNO95RmlufCSFtStpawR2M2ssg	2024-10-17 14:45:02.622465+00
ztygz455dats0evritq2bjfgnq2n2qgc	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1swN54:XzSijNKBP95J36ZL8TrjdC_llN-5FJ88YLEUjEg6odY	2024-10-17 14:45:26.872368+00
d997znzflazp6qzpa4s8k6wx2wao6puu	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1sxmPA:FhJFiMsoPEDbqsOv-_7rwuRAG57CAAmquLj3FUun8YA	2024-10-21 12:00:00.046702+00
el0xludjdbpviq30bxpwgbjndhmnp7yh	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t0M2v:Xhsp8PQSSq-36Gyk96aXnMJ9a7n4OjO00sOE7uExKP0	2024-10-28 14:27:41.788237+00
52nacdfpj13hr3ywnjnjkzzc4f428pct	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t1Unk:FvYWv3GXu3r2P08wkVJkwZzcGwVgRIPYtqoJRblS4GE	2024-10-31 18:00:44.462261+00
dz79orrxlzem2t4cwfgh4fxjmxshp9zi	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t4SJf:euaZy9gUnZ57zKQFSU7ljFMztU3u5dF23ikBnrZh6Rk	2024-11-08 21:57:55.708942+00
netalmq9riasnpra4xuj2hzspnuq971n	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t5TLE:gq49hID6HPaBssfeNM-qj-JCh6MZ0L5YtTGak4wHBwI	2024-11-11 17:15:44.065244+00
p4i0crv87l5ld5y84e84rp7mlnkjv3md	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t6xZ6:2wepUzXzEtObYz5VHYkTzOhykUDPlEf81BqhjkD89kk	2024-11-15 19:44:12.222186+00
awrdvmrpq3ki2w4gfjlnv11z4kqqxdfs	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t7Kqq:VyRbN3YPQqq1ZNDRZwAydLJtELa8X3A9W9D7T9F2XiQ	2024-11-16 20:36:04.246618+00
70cqkb64ouv9dn03xq5ip4a1m4xjdfmd	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t7qgS:3cShSfbZ5lp-mGotT3lu2B45uN5Q5_KYsDNlrga78Mw	2024-11-18 06:35:28.837964+00
jq21lmz2lxr4zqpxemq0ftg99q35sjm2	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1t90f7:DkQzncpUWTiYpN-GU_oUom4KY_1f6vTjKifFakF5hFY	2024-11-21 11:26:53.982359+00
eg75oqxzg4s9gse5ltymhxb7qismijh8	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1tA6k1:_giIMLnoFNQx0oT5zgt3dSRUwyxZ-d4Ow9YVJ3P0gps	2024-11-24 12:08:29.988087+00
43v0p1b06yh8wv3rvfba7034oid0zoqb	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1tCLyE:Pvn2nBktny-ohzQ_KQ1Kxw0Ef-1RFK1HxFvfbVBNOQI	2024-11-30 16:48:26.671864+00
67glyyz7ckt9vmo7eouq0e8stnvll04j	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1tD0Ef:9zcYUgPqyD_DQPtX3DBzq0Bkx1qxb9Ob70gZUQUaRJ8	2024-12-02 11:48:05.029094+00
4tra5anp4522wljzil00yirvgdq9x7yi	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1tESmI:JmgAQY-4VCjGCKZNo7ds9ItPAUuBoOvp4y4H0bfaEWs	2024-12-06 12:28:50.055681+00
myat04ceupp1cnb5u52jhp402ygyrgbw	.eJxVjEEOwiAQAP_C2RAotF08eu8bmmV3kaqBpLQn499Nkx70OjOZt5px3_K8N1nnhdVVeXX5ZRHpKeUQ_MByr5pq2dYl6iPRp216qiyv29n-DTK2fGydUBy6vrdJgjceOYBjBoTOBUw4DpicBRaE3oTREEKigELWeoIwqM8X7u04Rg:1tEoox:JWkKyORhfl4fBQD_L5wv2vD5pncVX07ie6M3dnVFE08	2024-12-07 12:01:03.819858+00
xely5zk8g5bhdjcx6ure0hxh41ic3es9	.eJxVjMsOwiAQRf-FtSE8BgGX7v0GwmNGqgaS0q6M_26bdKHbe865bxbiutSwDpzDVNiFATv9binmJ7YdlEds985zb8s8Jb4r_KCD33rB1_Vw_w5qHHWrDWml0BunCkbjtXYgi_UoLZCDrEkB-oyYSNPZZreJkCAJFORISMU-X9lFN74:1tFWLd:F6EuzCNoj-lx39zx8_hgiB1ZDwruX9wi-snpXDDJd8g	2024-12-09 10:29:41.077354+00
\.


--
-- Data for Name: operating_machine; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_machine (id, name, max_rpm, domain) FROM stdin;
1	Schiffli	500	21.50
2	flat	1000	11.00
\.


--
-- Data for Name: operating_product; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_product (id, name, cost, unit_id, description, sku, stock_quantity, variant, manufacturer, created_at) FROM stdin;
2	FL20160	1.45	1	\N	FL20160	400.00	{}	ALPASLAN	2024-11-30 11:06:52.060054+00
3	FL20165	1.60	1	\N	FL20165	200.00	{}	ALPASLAN	2024-11-30 11:06:52.060054+00
4	12421	3.00	1	TULLE FABRIC	12421	132.00	{}	KARVEN	2024-11-30 11:15:18.100229+00
\.


--
-- Data for Name: operating_product_raw_materials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_product_raw_materials (id, product_id, rawmaterial_id) FROM stdin;
\.


--
-- Data for Name: operating_rawmaterial; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_rawmaterial (id, name, cost, type_id) FROM stdin;
\.


--
-- Data for Name: operating_rawmaterial_supplierCompany; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."operating_rawmaterial_supplierCompany" (id, rawmaterial_id, company_id) FROM stdin;
\.


--
-- Data for Name: operating_rawmaterial_supplierContact; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public."operating_rawmaterial_supplierContact" (id, rawmaterial_id, contact_id) FROM stdin;
\.


--
-- Data for Name: operating_rawmaterialcategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_rawmaterialcategory (id, name, unit) FROM stdin;
1	fabric	m
2	yarn	kg
3	dye	kg
4	velvet	mt
5	crystal	piece
6	pearl	piece
\.


--
-- Data for Name: operating_unitcategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_unitcategory (id, name, decimals) FROM stdin;
1	MT	2
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.products (id, created_at, name, files) FROM stdin;
2911	2024-01-27 21:35:25.978+00	1002	{"{\\"name\\": \\"1002.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1002\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2913	2024-01-27 21:35:25.978+00	1014	{"{\\"name\\": \\"1014.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1014\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2922	2024-01-27 21:35:25.979+00	1013	{"{\\"name\\": \\"1013.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1013\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2919	2024-01-27 21:35:25.979+00	1008	{"{\\"name\\": \\"1008.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1008\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2929	2024-01-27 21:35:25.98+00	1064	{"{\\"name\\": \\"1064_G19.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1064\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G19\\"}"}
2910	2024-01-27 21:35:25.978+00	1003	{"{\\"name\\": \\"1003.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1003\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2931	2024-01-27 21:35:25.98+00	1069	{"{\\"name\\": \\"1069.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1069\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2916	2024-01-27 21:35:25.979+00	1009	{"{\\"name\\": \\"1009T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1009\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1009_G01.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1009\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G01\\"}","{\\"name\\": \\"1009_K07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1009\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K07\\"}","{\\"name\\": \\"1009_K49.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1009\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K49\\"}"}
2921	2024-01-27 21:35:25.979+00	1020	{"{\\"name\\": \\"1020.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1020\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2940	2024-01-27 21:35:25.981+00	1130	{"{\\"name\\": \\"1130_K20.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1130\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K20\\"}"}
2939	2024-01-27 21:35:25.981+00	1133	{"{\\"name\\": \\"1133_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1133\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2936	2024-01-27 21:35:25.981+00	1072	{"{\\"name\\": \\"1072_K17.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1072\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K17\\"}"}
2914	2024-01-27 21:35:25.979+00	1021	{"{\\"name\\": \\"1021.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1021\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2917	2024-01-27 21:35:25.979+00	1026	{"{\\"name\\": \\"1026.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1026\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2972	2024-01-27 21:35:25.983+00	1204	{"{\\"name\\": \\"1204_K62.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1204\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K62\\"}","{\\"name\\": \\"1204_K64.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1204\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K64\\"}"}
2920	2024-01-27 21:35:25.979+00	1031	{"{\\"name\\": \\"1031.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1031\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1031_K07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1031\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K07\\"}"}
2918	2024-01-27 21:35:25.979+00	1037	{"{\\"name\\": \\"1037_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1037\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2932	2024-01-27 21:35:25.98+00	1096	{"{\\"name\\": \\"1096_G06.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1096\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G06\\"}"}
2933	2024-01-27 21:35:25.981+00	1102	{"{\\"name\\": \\"1102.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1102\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2923	2024-01-27 21:35:25.98+00	1038	{"{\\"name\\": \\"1038_K08.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1038\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K08\\"}"}
2934	2024-01-27 21:35:25.981+00	1103	{"{\\"name\\": \\"1103.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1103\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2924	2024-01-27 21:35:25.98+00	1043	{"{\\"name\\": \\"1043_K07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1043\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K07\\"}"}
2930	2024-01-27 21:35:25.98+00	1045	{"{\\"name\\": \\"1045.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1045\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2938	2024-01-27 21:35:25.981+00	1114	{"{\\"name\\": \\"1114.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1114\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1114_K17.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1114\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K17\\"}"}
2925	2024-01-27 21:35:25.98+00	1049	{"{\\"name\\": \\"1049.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1049\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2937	2024-01-27 21:35:25.981+00	1126	{"{\\"name\\": \\"1126_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1126\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
2926	2024-01-27 21:35:25.98+00	1050	{"{\\"name\\": \\"1050.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1050\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2928	2024-01-27 21:35:25.98+00	1053	{"{\\"name\\": \\"1053_G05.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1053\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G05\\"}","{\\"name\\": \\"1053_G17.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1053\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G17\\"}"}
2935	2024-01-27 21:35:25.981+00	1056	{"{\\"name\\": \\"1056-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1056\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1056-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1056\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1056_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1056\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2927	2024-01-27 21:35:25.98+00	1057	{"{\\"name\\": \\"1057_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1057\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
3008	2024-01-27 21:35:25.985+00	12442	{"{\\"name\\": \\"12442.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12442\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2961	2024-01-27 21:35:25.982+00	1184	{"{\\"name\\": \\"1184_D13.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1184\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"D13\\"}"}
2960	2024-01-27 21:35:25.982+00	1172	{"{\\"name\\": \\"1172.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1172\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2963	2024-01-27 21:35:25.983+00	1185	{"{\\"name\\": \\"1185.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1185\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2958	2024-01-27 21:35:25.982+00	1173	{"{\\"name\\": \\"1173.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1173\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2956	2024-01-27 21:35:25.982+00	1151	{"{\\"name\\": \\"1151.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1151\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2992	2024-01-27 21:35:25.984+00	12349	{"{\\"name\\": \\"12349.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12349\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2942	2024-01-27 21:35:25.981+00	1136	{"{\\"name\\": \\"1136.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1136\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1136_K07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1136\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K07\\"}","{\\"name\\": \\"1136_K28.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1136\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K28\\"}"}
2969	2024-01-27 21:35:25.983+00	1193	{"{\\"name\\": \\"1193_K21-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1193\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K21\\"}","{\\"name\\": \\"1193_K21.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1193\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K21\\"}"}
2949	2024-01-27 21:35:25.982+00	1153	{"{\\"name\\": \\"1153.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1153\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2964	2024-01-27 21:35:25.983+00	1174	{"{\\"name\\": \\"1174_K50.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1174\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K50\\"}"}
2941	2024-01-27 21:35:25.981+00	1089	{"{\\"name\\": \\"1089.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1089\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1089T-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1089\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1089T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1089\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1089_K32.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1089\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K32\\"}"}
2952	2024-01-27 21:35:25.982+00	1154	{"{\\"name\\": \\"1154_K13.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1154\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K13\\"}","{\\"name\\": \\"1154_K48.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1154\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K48\\"}"}
2945	2024-01-27 21:35:25.982+00	1091	{"{\\"name\\": \\"1091_G17.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1091\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G17\\"}"}
2965	2024-01-27 21:35:25.983+00	1198	{"{\\"name\\": \\"1198.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1198\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1198_K60.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1198\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K60\\"}"}
2948	2024-01-27 21:35:25.982+00	1141	{"{\\"name\\": \\"1141_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1141\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}","{\\"name\\": \\"1141_K40.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1141\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K40\\"}"}
2951	2024-01-27 21:35:25.982+00	1159	{"{\\"name\\": \\"1159_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1159\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2955	2024-01-27 21:35:25.982+00	1164	{"{\\"name\\": \\"1164_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1164\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2970	2024-01-27 21:35:25.983+00	1199	{"{\\"name\\": \\"1199_K56.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1199\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K56\\"}"}
2968	2024-01-27 21:35:25.983+00	1176	{"{\\"name\\": \\"1176_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1176\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2971	2024-01-27 21:35:25.983+00	12131	{"{\\"name\\": \\"12131.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12131\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2943	2024-01-27 21:35:25.982+00	1142	{"{\\"name\\": \\"1142.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1142\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1142_K10.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1142\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K10\\"}"}
2950	2024-01-27 21:35:25.982+00	1169	{"{\\"name\\": \\"1169_G13.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1169\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G13\\"}"}
2959	2024-01-27 21:35:25.982+00	1179	{"{\\"name\\": \\"1179_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1179\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2947	2024-01-27 21:35:25.982+00	1143	{"{\\"name\\": \\"1143.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1143\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2962	2024-01-27 21:35:25.983+00	1181	{"{\\"name\\": \\"1181_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1181\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2957	2024-01-27 21:35:25.982+00	1109	{"{\\"name\\": \\"1109.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1109\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2946	2024-01-27 21:35:25.982+00	1144	{"{\\"name\\": \\"1144_K11-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1144\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K11\\"}","{\\"name\\": \\"1144_K11.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1144\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K11\\"}"}
2944	2024-01-27 21:35:25.982+00	1147	{"{\\"name\\": \\"1147_K10.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1147\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K10\\"}"}
2967	2024-01-27 21:35:25.983+00	1201	{"{\\"name\\": \\"1201_K14.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1201\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K14\\"}"}
2966	2024-01-27 21:35:25.983+00	1182	{"{\\"name\\": \\"1182_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1182\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
2981	2024-01-27 21:35:25.983+00	1207	{"{\\"name\\": \\"1207_K14.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1207\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K14\\"}"}
2986	2024-01-27 21:35:25.984+00	1211	{"{\\"name\\": \\"1211.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1211\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1211_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1211\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}","{\\"name\\": \\"1211_K23.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1211\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K23\\"}"}
2976	2024-01-27 21:35:25.983+00	12133	{"{\\"name\\": \\"12133.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12133\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2985	2024-01-27 21:35:25.984+00	12179	{"{\\"name\\": \\"12179.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12179\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2980	2024-01-27 21:35:25.983+00	12138	{"{\\"name\\": \\"12138.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12138\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2975	2024-01-27 21:35:25.983+00	1200	{"{\\"name\\": \\"1200_K56.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1200\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K56\\"}"}
2974	2024-01-27 21:35:25.983+00	1213	{"{\\"name\\": \\"1213_K14.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1213\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K14\\"}"}
2990	2024-01-27 21:35:25.984+00	1217	{"{\\"name\\": \\"1217_K55.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1217\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K55\\"}"}
2998	2024-01-27 21:35:25.984+00	12334	{"{\\"name\\": \\"12334_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12334\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
2994	2024-01-27 21:35:25.984+00	1218	{"{\\"name\\": \\"1218_K48.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1218\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K48\\"}"}
2997	2024-01-27 21:35:25.984+00	1236	{"{\\"name\\": \\"1236_K55.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1236\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K55\\"}"}
2996	2024-01-27 21:35:25.984+00	1219	{"{\\"name\\": \\"1219_K57.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1219\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K57\\"}"}
2991	2024-01-27 21:35:25.984+00	1220	{"{\\"name\\": \\"1220.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1220\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1220_K62.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1220\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K62\\"}"}
3002	2024-01-27 21:35:25.985+00	1237	{"{\\"name\\": \\"1237.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1237\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3006	2024-01-27 21:35:25.985+00	12400	{"{\\"name\\": \\"12400.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12400\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3000	2024-01-27 21:35:25.985+00	1241	{"{\\"name\\": \\"1241_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1241\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}"}
3004	2024-01-27 21:35:25.985+00	12430	{"{\\"name\\": \\"12430_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12430\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3007	2024-01-27 21:35:25.985+00	1249	{"{\\"name\\": \\"1249_K41.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1249\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K41\\"}"}
2977	2024-01-27 21:35:25.983+00	1215	{"{\\"name\\": \\"1215.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1215\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2979	2024-01-27 21:35:25.983+00	12150	{"{\\"name\\": \\"12150.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12150\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3001	2024-01-27 21:35:25.985+00	12456	{"{\\"name\\": \\"12456.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12456\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2984	2024-01-27 21:35:25.984+00	12152	{"{\\"name\\": \\"12152.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12152\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3005	2024-01-27 21:35:25.985+00	12459	{"{\\"name\\": \\"12459.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12459\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2978	2024-01-27 21:35:25.983+00	12156	{"{\\"name\\": \\"12156.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12156\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2983	2024-01-27 21:35:25.984+00	12160	{"{\\"name\\": \\"12160.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12160\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2987	2024-01-27 21:35:25.984+00	12174	{"{\\"name\\": \\"12174-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12174\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12174.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12174\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2995	2024-01-27 21:35:25.984+00	12207	{"{\\"name\\": \\"12207.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12207\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2989	2024-01-27 21:35:25.984+00	12175	{"{\\"name\\": \\"12175.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12175\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2999	2024-01-27 21:35:25.984+00	12219	{"{\\"name\\": \\"12219.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12219\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3003	2024-01-27 21:35:25.985+00	12226	{"{\\"name\\": \\"12226.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12226\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2988	2024-01-27 21:35:25.984+00	12266	{"{\\"name\\": \\"12266.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12266\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2993	2024-01-27 21:35:25.984+00	1228	{"{\\"name\\": \\"1228_K29.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1228\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K29\\"}"}
3023	2024-01-27 21:35:25.986+00	12148	{"{\\"name\\": \\"12148.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12148\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3013	2024-01-27 21:35:25.985+00	1246	{"{\\"name\\": \\"1246_K06.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1246\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K06\\"}"}
3026	2024-01-27 21:35:25.986+00	1214	{"{\\"name\\": \\"1214_K34.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1214\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K34\\"}"}
3018	2024-01-27 21:35:25.985+00	12522	{"{\\"name\\": \\"12522_G52.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12522\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G52\\"}"}
3032	2024-01-27 21:35:25.986+00	12533	{"{\\"name\\": \\"12533_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"12533_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3033	2024-01-27 21:35:25.986+00	12485	{"{\\"name\\": \\"12485.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12485\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3027	2024-01-27 21:35:25.986+00	12547	{"{\\"name\\": \\"12547-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12547\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12547-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12547\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}"}
3021	2024-01-27 21:35:25.986+00	12524	{"{\\"name\\": \\"12524.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12524\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3031	2024-01-27 21:35:25.986+00	12548	{"{\\"name\\": \\"12548-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12548\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12548.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12548\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3035	2024-01-27 21:35:25.986+00	12549	{"{\\"name\\": \\"12549.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12549\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3016	2024-01-27 21:35:25.985+00	12525	{"{\\"name\\": \\"12525_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12525\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"12525_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12525\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3020	2024-01-27 21:35:25.986+00	12537	{"{\\"name\\": \\"12537.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12537\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3009	2024-01-27 21:35:25.985+00	12503	{"{\\"name\\": \\"12503.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12503\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3022	2024-01-27 21:35:25.986+00	12526	{"{\\"name\\": \\"12526.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12526\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12526_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12526\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3024	2024-01-27 21:35:25.986+00	12527	{"{\\"name\\": \\"12527.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12527\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3061	2024-01-27 21:35:25.988+00	12702	{"{\\"name\\": \\"12702.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12702\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3012	2024-01-27 21:35:25.985+00	12443	{"{\\"name\\": \\"12443_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12443\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"12443_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12443\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3015	2024-01-27 21:35:25.985+00	12504	{"{\\"name\\": \\"12504-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12504\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12504.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12504\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3030	2024-01-27 21:35:25.986+00	12552	{"{\\"name\\": \\"12552.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12552\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3017	2024-01-27 21:35:25.985+00	12513	{"{\\"name\\": \\"12513.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12513\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3034	2024-01-27 21:35:25.986+00	12553	{"{\\"name\\": \\"12553_G44.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12553\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G44\\"}"}
3029	2024-01-27 21:35:25.986+00	12528	{"{\\"name\\": \\"12528-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12528\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12528.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12528\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3011	2024-01-27 21:35:25.985+00	12465	{"{\\"name\\": \\"12465-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12465\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12465.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12465\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3036	2024-01-27 21:35:25.986+00	1252	{"{\\"name\\": \\"1252_K26.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1252\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K26\\"}"}
3010	2024-01-27 21:35:25.985+00	12519	{"{\\"name\\": \\"12519.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12519\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12519_G52.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12519\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G52\\"}"}
3014	2024-01-27 21:35:25.985+00	12520	{"{\\"name\\": \\"12520_G52.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12520\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G52\\"}"}
3019	2024-01-27 21:35:25.985+00	12530	{"{\\"name\\": \\"12530.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12530\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12530_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12530\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3025	2024-01-27 21:35:25.986+00	12532	{"{\\"name\\": \\"12532-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12532\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12532.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12532\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3396	2024-01-27 21:35:26.013+00	1614	{"{\\"name\\": \\"1614.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1614\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3411	2024-01-27 21:35:26.014+00	1658	{"{\\"name\\": \\"1658_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1658\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3433	2024-01-27 21:35:26.015+00	1660	{"{\\"name\\": \\"1660.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1660\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3038	2024-01-27 21:35:25.986+00	12535	{"{\\"name\\": \\"12535_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12535\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"12535_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12535\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3037	2024-01-27 21:35:25.986+00	1248	{"{\\"name\\": \\"1248_K41.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1248\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K41\\"}"}
3042	2024-01-27 21:35:25.987+00	12536	{"{\\"name\\": \\"12536_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12536\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3040	2024-01-27 21:35:25.987+00	12492	{"{\\"name\\": \\"12492.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12492\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3043	2024-01-27 21:35:25.987+00	12550	{"{\\"name\\": \\"12550-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12550\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12550.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12550\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3050	2024-01-27 21:35:25.987+00	12551	{"{\\"name\\": \\"12551-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12551\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12551.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12551\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3065	2024-01-27 21:35:25.988+00	12697	{"{\\"name\\": \\"12697-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12697.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3062	2024-01-27 21:35:25.988+00	12668	{"{\\"name\\": \\"12668.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12668\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3039	2024-01-27 21:35:25.987+00	12558	{"{\\"name\\": \\"12558.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12558\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3053	2024-01-27 21:35:25.987+00	12708	{"{\\"name\\": \\"12708.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12708\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3044	2024-01-27 21:35:25.987+00	12559	{"{\\"name\\": \\"12559.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12559\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3058	2024-01-27 21:35:25.987+00	12709	{"{\\"name\\": \\"12709.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12709\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3064	2024-01-27 21:35:25.988+00	12711	{"{\\"name\\": \\"12711.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12711\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3047	2024-01-27 21:35:25.987+00	12563	{"{\\"name\\": \\"12563.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12563\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3049	2024-01-27 21:35:25.987+00	12699	{"{\\"name\\": \\"12699-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12699.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3067	2024-01-27 21:35:25.988+00	12713	{"{\\"name\\": \\"12713.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12713\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3100	2024-01-27 21:35:25.99+00	12729	{"{\\"name\\": \\"12729.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12729\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3054	2024-01-27 21:35:25.987+00	12564	{"{\\"name\\": \\"12564-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12564\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12564.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12564\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3052	2024-01-27 21:35:25.987+00	12700	{"{\\"name\\": \\"12700.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12700\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3056	2024-01-27 21:35:25.987+00	12701	{"{\\"name\\": \\"12701.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12701\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3060	2024-01-27 21:35:25.988+00	12565	{"{\\"name\\": \\"12565-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12565\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12565.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12565\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3066	2024-01-27 21:35:25.988+00	12703	{"{\\"name\\": \\"12703.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12703\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3063	2024-01-27 21:35:25.988+00	1257	{"{\\"name\\": \\"1257.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1257\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3046	2024-01-27 21:35:25.987+00	12680	{"{\\"name\\": \\"12680.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12680\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3051	2024-01-27 21:35:25.987+00	12688	{"{\\"name\\": \\"12688.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12688\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3055	2024-01-27 21:35:25.987+00	1269	{"{\\"name\\": \\"1269.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1269\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1269_K72.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1269\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K72\\"}"}
3059	2024-01-27 21:35:25.988+00	12696	{"{\\"name\\": \\"12696.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12696\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3045	2024-01-27 21:35:25.987+00	1261	{"{\\"name\\": \\"1261_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1261\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3048	2024-01-27 21:35:25.987+00	1264	{"{\\"name\\": \\"1264_G54.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1264\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G54\\"}"}
3073	2024-01-27 21:35:25.988+00	12544	{"{\\"name\\": \\"12544.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12544\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3081	2024-01-27 21:35:25.989+00	12546	{"{\\"name\\": \\"12546.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12546\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3071	2024-01-27 21:35:25.988+00	12720	{"{\\"name\\": \\"12720.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12720\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3087	2024-01-27 21:35:25.988+00	1266	{"{\\"name\\": \\"1266_K43-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1266\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K43\\"}","{\\"name\\": \\"1266_K43.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1266\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K43\\"}"}
3074	2024-01-27 21:35:25.988+00	12721	{"{\\"name\\": \\"12721.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12721\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3090	2024-01-27 21:35:25.989+00	12727	{"{\\"name\\": \\"12727.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12727\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3097	2024-01-27 21:35:25.99+00	12728	{"{\\"name\\": \\"12728.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12728\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3078	2024-01-27 21:35:25.989+00	12723	{"{\\"name\\": \\"12723.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12723\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3092	2024-01-27 21:35:25.989+00	1267	{"{\\"name\\": \\"1267.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1267\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3072	2024-01-27 21:35:25.988+00	12714	{"{\\"name\\": \\"12714.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12714\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3080	2024-01-27 21:35:25.989+00	12724	{"{\\"name\\": \\"12724.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12724\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3091	2024-01-27 21:35:25.989+00	12734	{"{\\"name\\": \\"12734.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12734\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3076	2024-01-27 21:35:25.988+00	12718	{"{\\"name\\": \\"12718.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12718\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3094	2024-01-27 21:35:25.99+00	12735	{"{\\"name\\": \\"12735.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12735\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3075	2024-01-27 21:35:25.988+00	12731	{"{\\"name\\": \\"12731.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12731\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3083	2024-01-27 21:35:25.989+00	12725	{"{\\"name\\": \\"12725.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12725\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3079	2024-01-27 21:35:25.989+00	12719	{"{\\"name\\": \\"12719.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12719\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3096	2024-01-27 21:35:25.99+00	12740	{"{\\"name\\": \\"12740.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12740\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3095	2024-01-27 21:35:25.99+00	1268	{"{\\"name\\": \\"1268-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1268\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1268-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1268\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1268.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1268\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3086	2024-01-27 21:35:25.989+00	12726	{"{\\"name\\": \\"12726.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12726\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3082	2024-01-27 21:35:25.989+00	12732	{"{\\"name\\": \\"12732-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12732\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12732.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12732\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12732_Etek.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12732\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Etek\\"}"}
3099	2024-01-27 21:35:25.99+00	12742	{"{\\"name\\": \\"12742.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12742\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3070	2024-01-27 21:35:25.988+00	12704	{"{\\"name\\": \\"12704-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12704\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12704.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12704\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3084	2024-01-27 21:35:25.989+00	12755	{"{\\"name\\": \\"12755.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12755\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3085	2024-01-27 21:35:25.989+00	12797	{"{\\"name\\": \\"12797-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12797\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12797.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12797\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3068	2024-01-27 21:35:25.988+00	1260	{"{\\"name\\": \\"1260-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1260\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1260.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1260\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1260_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1260\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}","{\\"name\\": \\"1260_K28.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1260\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K28\\"}"}
3088	2024-01-27 21:35:25.989+00	12756	{"{\\"name\\": \\"12756.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12756\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3093	2024-01-27 21:35:25.99+00	12761	{"{\\"name\\": \\"12761.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12761\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3098	2024-01-27 21:35:25.99+00	12819	{"{\\"name\\": \\"12819-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12819\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12819.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12819\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3089	2024-01-27 21:35:25.989+00	12802	{"{\\"name\\": \\"12802.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12802\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3103	2024-01-27 21:35:25.99+00	12730	{"{\\"name\\": \\"12730.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12730\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3106	2024-01-27 21:35:25.991+00	12752	{"{\\"name\\": \\"12752.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12752\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3102	2024-01-27 21:35:25.99+00	12770	{"{\\"name\\": \\"12770.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12770\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3110	2024-01-27 21:35:25.991+00	12753	{"{\\"name\\": \\"12753.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12753\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3119	2024-01-27 21:35:25.992+00	12782	{"{\\"name\\": \\"12782.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12782\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3105	2024-01-27 21:35:25.991+00	12771	{"{\\"name\\": \\"12771.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12771\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3113	2024-01-27 21:35:25.992+00	12754	{"{\\"name\\": \\"12754.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12754\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3122	2024-01-27 21:35:25.993+00	12793	{"{\\"name\\": \\"12793.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12793\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3104	2024-01-27 21:35:25.991+00	12744	{"{\\"name\\": \\"12744.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12744\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3108	2024-01-27 21:35:25.991+00	12773	{"{\\"name\\": \\"12773.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12773\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3111	2024-01-27 21:35:25.991+00	12774	{"{\\"name\\": \\"12774.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12774\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3115	2024-01-27 21:35:25.992+00	12781	{"{\\"name\\": \\"12781.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12781\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3101	2024-01-27 21:35:25.99+00	12820	{"{\\"name\\": \\"12820-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12820\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12820.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12820\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3117	2024-01-27 21:35:25.992+00	12841	{"{\\"name\\": \\"12841.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"12841\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3109	2024-01-27 21:35:25.991+00	12838	{"{\\"name\\": \\"12838.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12838\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3124	2024-01-27 21:35:25.993+00	12847	{"{\\"name\\": \\"12847.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"12847\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12847.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12847\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3120	2024-01-27 21:35:25.992+00	12846	{"{\\"name\\": \\"12846.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"12846\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3107	2024-01-27 21:35:25.991+00	12837	{"{\\"name\\": \\"12837.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12837\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3133	2024-01-27 21:35:25.993+00	1288	{"{\\"name\\": \\"1288.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1288\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3112	2024-01-27 21:35:25.991+00	12839	{"{\\"name\\": \\"12839.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12839\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3129	2024-01-27 21:35:25.993+00	1286	{"{\\"name\\": \\"1286.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1286\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3114	2024-01-27 21:35:25.992+00	12840	{"{\\"name\\": \\"12840.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"12840\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3127	2024-01-27 21:35:25.993+00	12821	{"{\\"name\\": \\"12821-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12821\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12821.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12821\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3118	2024-01-27 21:35:25.992+00	13034	{"{\\"name\\": \\"13034-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13034\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13034.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13034\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3121	2024-01-27 21:35:25.992+00	13036	{"{\\"name\\": \\"13036.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13036\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3123	2024-01-27 21:35:25.993+00	13045	{"{\\"name\\": \\"13045.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13045\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3131	2024-01-27 21:35:25.993+00	12822	{"{\\"name\\": \\"12822-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12822\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12822.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12822\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3128	2024-01-27 21:35:25.993+00	13063	{"{\\"name\\": \\"13063.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13063\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3136	2024-01-27 21:35:25.993+00	12823	{"{\\"name\\": \\"12823-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12823\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12823.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12823\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3116	2024-01-27 21:35:25.992+00	13030	{"{\\"name\\": \\"13030_K64.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13030\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K64\\"}"}
3134	2024-01-27 21:35:25.993+00	1314	{"{\\"name\\": \\"1314_K47.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1314\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K47\\"}"}
3125	2024-01-27 21:35:25.993+00	13247	{"{\\"name\\": \\"13247.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13247\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3130	2024-01-27 21:35:25.993+00	13271	{"{\\"name\\": \\"13271.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13271\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3132	2024-01-27 21:35:25.993+00	13288	{"{\\"name\\": \\"13288_K64.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13288\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K64\\"}"}
3135	2024-01-27 21:35:25.993+00	1328	{"{\\"name\\": \\"1328T_G02.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1328\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G02\\"}"}
3152	2024-01-27 21:35:25.995+00	12556	{"{\\"name\\": \\"12556.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12556\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3158	2024-01-27 21:35:25.995+00	12557	{"{\\"name\\": \\"12557.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12557\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3138	2024-01-27 21:35:25.994+00	12824	{"{\\"name\\": \\"12824-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12824\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12824.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12824\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3151	2024-01-27 21:35:25.995+00	12827	{"{\\"name\\": \\"12827.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12827\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3156	2024-01-27 21:35:25.995+00	12828	{"{\\"name\\": \\"12828.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12828\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3141	2024-01-27 21:35:25.994+00	12930	{"{\\"name\\": \\"12930_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12930\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3144	2024-01-27 21:35:25.994+00	12825	{"{\\"name\\": \\"12825-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12825\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12825.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12825\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3137	2024-01-27 21:35:25.994+00	1290	{"{\\"name\\": \\"1290i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"1290\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1290i_Kartela.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"1290\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3147	2024-01-27 21:35:25.994+00	12826	{"{\\"name\\": \\"12826.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12826\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3153	2024-01-27 21:35:25.995+00	12803	{"{\\"name\\": \\"12803.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12803\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3154	2024-01-27 21:35:25.995+00	13233	{"{\\"name\\": \\"13233-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13233\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13233.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13233\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3150	2024-01-27 21:35:25.994+00	13259	{"{\\"name\\": \\"13259.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13259\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3166	2024-01-27 21:35:25.995+00	1325	{"{\\"name\\": \\"1325T_G07.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1325\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}","{\\"name\\": \\"1325T_G45.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1325\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G45\\"}","{\\"name\\": \\"1325T_G47.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1325\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G47\\"}"}
3163	2024-01-27 21:35:25.995+00	13236	{"{\\"name\\": \\"13236.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13236\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3140	2024-01-27 21:35:25.994+00	1324	{"{\\"name\\": \\"1324T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1324\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1324T_G33.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1324\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G33\\"}"}
3159	2024-01-27 21:35:25.995+00	13234	{"{\\"name\\": \\"13234.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13234\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3139	2024-01-27 21:35:25.994+00	13272	{"{\\"name\\": \\"13272_K104.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13272\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3142	2024-01-27 21:35:25.994+00	13274	{"{\\"name\\": \\"13274.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13274\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3146	2024-01-27 21:35:25.994+00	13292	{"{\\"name\\": \\"13292.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13292\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3143	2024-01-27 21:35:25.994+00	13296	{"{\\"name\\": \\"13296.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13296\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3149	2024-01-27 21:35:25.994+00	13297	{"{\\"name\\": \\"13297.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13297\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3155	2024-01-27 21:35:25.995+00	13299	{"{\\"name\\": \\"13299-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13299\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13299.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13299\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3160	2024-01-27 21:35:25.995+00	13300	{"{\\"name\\": \\"13300.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13300\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3164	2024-01-27 21:35:25.995+00	13305	{"{\\"name\\": \\"13305.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13305\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3165	2024-01-27 21:35:25.995+00	13312	{"{\\"name\\": \\"13312.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13312\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3157	2024-01-27 21:35:25.995+00	13309	{"{\\"name\\": \\"13309-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13309\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13309.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13309\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3161	2024-01-27 21:35:25.995+00	13311	{"{\\"name\\": \\"13311-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13311\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13311.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13311\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3162	2024-01-27 21:35:25.995+00	13316	{"{\\"name\\": \\"13316.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13316\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3168	2024-01-27 21:35:25.995+00	12805	{"{\\"name\\": \\"12805.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12805\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3173	2024-01-27 21:35:25.996+00	13260	{"{\\"name\\": \\"13260.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13260\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3193	2024-01-27 21:35:25.997+00	13263	{"{\\"name\\": \\"13263_K104.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13263\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3187	2024-01-27 21:35:25.996+00	13262	{"{\\"name\\": \\"13262_K104.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13262\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3179	2024-01-27 21:35:25.996+00	13282	{"{\\"name\\": \\"13282_K104.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13282\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3175	2024-01-27 21:35:25.996+00	13276	{"{\\"name\\": \\"13276.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13276\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3185	2024-01-27 21:35:25.996+00	13283	{"{\\"name\\": \\"13283.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13283\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3171	2024-01-27 21:35:25.995+00	13308	{"{\\"name\\": \\"13308-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13308\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"13308.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13308\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3170	2024-01-27 21:35:25.995+00	13313	{"{\\"name\\": \\"13313.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13313\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3174	2024-01-27 21:35:25.996+00	13314	{"{\\"name\\": \\"13314.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13314\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3196	2024-01-27 21:35:25.997+00	13317	{"{\\"name\\": \\"13317.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13317\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3177	2024-01-27 21:35:25.996+00	13315	{"{\\"name\\": \\"13315.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13315\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3167	2024-01-27 21:35:25.995+00	1333	{"{\\"name\\": \\"1333.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1333\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3172	2024-01-27 21:35:25.996+00	1334	{"{\\"name\\": \\"1334.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1334\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3184	2024-01-27 21:35:25.996+00	1338	{"{\\"name\\": \\"1338.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1338\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3169	2024-01-27 21:35:25.995+00	1339	{"{\\"name\\": \\"1339.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1339\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3176	2024-01-27 21:35:25.996+00	1342	{"{\\"name\\": \\"1342-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1342\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1342.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1342\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3181	2024-01-27 21:35:25.996+00	1337	{"{\\"name\\": \\"1337-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1337\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1337-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1337\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1337-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1337\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1337.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1337\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3178	2024-01-27 21:35:25.996+00	1351	{"{\\"name\\": \\"1351.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1351\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3182	2024-01-27 21:35:25.996+00	1352	{"{\\"name\\": \\"1352.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1352\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3180	2024-01-27 21:35:25.996+00	1349	{"{\\"name\\": \\"1349-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1349\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1349-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1349\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1349.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1349\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3186	2024-01-27 21:35:25.996+00	1353	{"{\\"name\\": \\"1353.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1353\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3194	2024-01-27 21:35:25.997+00	1356	{"{\\"name\\": \\"1356.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1356\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3183	2024-01-27 21:35:25.996+00	1355	{"{\\"name\\": \\"1355.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1355\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3189	2024-01-27 21:35:25.997+00	1354	{"{\\"name\\": \\"1354.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1354\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1354_G64-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1354\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G64\\"}","{\\"name\\": \\"1354_G64.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1354\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G64\\"}"}
3188	2024-01-27 21:35:25.997+00	1361	{"{\\"name\\": \\"1361.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1361\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3190	2024-01-27 21:35:25.997+00	1359	{"{\\"name\\": \\"1359-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1359\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1359-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1359\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1359.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1359\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3195	2024-01-27 21:35:25.997+00	1362	{"{\\"name\\": \\"1362-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1362\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1362.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1362\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3197	2024-01-27 21:35:25.997+00	1368	{"{\\"name\\": \\"1368.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1368\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3192	2024-01-27 21:35:25.997+00	1358	{"{\\"name\\": \\"1358-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1358\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1358.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1358\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3217	2024-01-27 21:35:25.998+00	12808	{"{\\"name\\": \\"12808.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12808\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3215	2024-01-27 21:35:25.998+00	12817	{"{\\"name\\": \\"12817.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12817\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3214	2024-01-27 21:35:25.998+00	12809	{"{\\"name\\": \\"12809-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12809\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12809.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12809\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3213	2024-01-27 21:35:25.998+00	12815	{"{\\"name\\": \\"12815.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12815\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3216	2024-01-27 21:35:25.998+00	12818	{"{\\"name\\": \\"12818.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12818\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3201	2024-01-27 21:35:25.997+00	13267	{"{\\"name\\": \\"13267.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13267\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3208	2024-01-27 21:35:25.998+00	13269	{"{\\"name\\": \\"13269.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13269\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3218	2024-01-27 21:35:25.998+00	13285	{"{\\"name\\": \\"13285.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13285\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3202	2024-01-27 21:35:25.997+00	13318	{"{\\"name\\": \\"13318.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13318\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3207	2024-01-27 21:35:25.997+00	13319	{"{\\"name\\": \\"13319.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13319\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3210	2024-01-27 21:35:25.998+00	13320	{"{\\"name\\": \\"13320.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"13320\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3203	2024-01-27 21:35:25.997+00	1357	{"{\\"name\\": \\"1357-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1357\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1357.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1357\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3200	2024-01-27 21:35:25.997+00	1364	{"{\\"name\\": \\"1364-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1364\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1364.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1364\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3211	2024-01-27 21:35:25.998+00	1373	{"{\\"name\\": \\"1373-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1373\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1373-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1373\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1373.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1373\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3221	2024-01-27 21:35:25.999+00	1376	{"{\\"name\\": \\"1376.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1376\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3204	2024-01-27 21:35:25.997+00	1365	{"{\\"name\\": \\"1365-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365-5.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"5\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365-6.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"6\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365-7.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"7\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1365.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1365\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3220	2024-01-27 21:35:25.998+00	1370	{"{\\"name\\": \\"1370-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1370-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1370-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1370-5.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"5\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1370-6.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"6\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1370.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1370\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3219	2024-01-27 21:35:25.998+00	1375	{"{\\"name\\": \\"1375-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1375\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1375.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1375\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3209	2024-01-27 21:35:25.998+00	1367	{"{\\"name\\": \\"1367-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1367\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1367.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1367\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3205	2024-01-27 21:35:25.997+00	1371	{"{\\"name\\": \\"1371.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1371\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1371T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1371\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3206	2024-01-27 21:35:25.997+00	1372	{"{\\"name\\": \\"1372.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1372\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3198	2024-01-27 21:35:25.997+00	1369	{"{\\"name\\": \\"1369.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1369\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1369T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1369\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3283	2024-01-27 21:35:26.004+00	1488	{"{\\"name\\": \\"1488.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1488\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3226	2024-01-27 21:35:25.999+00	1384	{"{\\"name\\": \\"1384.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1384\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3228	2024-01-27 21:35:25.999+00	1389	{"{\\"name\\": \\"1389.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1389\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3223	2024-01-27 21:35:25.999+00	1379	{"{\\"name\\": \\"1379_G78-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1379\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G78\\"}","{\\"name\\": \\"1379_G78-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1379\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"G78\\"}","{\\"name\\": \\"1379_G78.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1379\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G78\\"}"}
3229	2024-01-27 21:35:25.999+00	1387	{"{\\"name\\": \\"1387.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1387\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3231	2024-01-27 21:35:26+00	1390	{"{\\"name\\": \\"1390.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1390\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3238	2024-01-27 21:35:26+00	1391	{"{\\"name\\": \\"1391-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1391\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1391.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1391\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3237	2024-01-27 21:35:26+00	1393	{"{\\"name\\": \\"1393.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1393\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3232	2024-01-27 21:35:26+00	1392	{"{\\"name\\": \\"1392.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1392\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3235	2024-01-27 21:35:26+00	1394	{"{\\"name\\": \\"1394.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1394\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3233	2024-01-27 21:35:26+00	1388	{"{\\"name\\": \\"1388-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1388\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1388.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1388\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3225	2024-01-27 21:35:25.999+00	1380	{"{\\"name\\": \\"1380-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1380\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1380.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1380\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3240	2024-01-27 21:35:26+00	1398	{"{\\"name\\": \\"1398.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1398\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3243	2024-01-27 21:35:26+00	1402	{"{\\"name\\": \\"1402.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1402\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3244	2024-01-27 21:35:26+00	1403	{"{\\"name\\": \\"1403.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1403\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3248	2024-01-27 21:35:26.001+00	1408	{"{\\"name\\": \\"1408.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1408\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3224	2024-01-27 21:35:25.999+00	1381	{"{\\"name\\": \\"1381.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1381\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3249	2024-01-27 21:35:26.001+00	1410	{"{\\"name\\": \\"1410T-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1410\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1410T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1410\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3241	2024-01-27 21:35:26+00	1399	{"{\\"name\\": \\"1399-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1399\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1399.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1399\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3246	2024-01-27 21:35:26.001+00	1405	{"{\\"name\\": \\"1405T-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1405\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1405T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1405\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3227	2024-01-27 21:35:25.999+00	1382	{"{\\"name\\": \\"1382-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1382\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1382.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1382\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3245	2024-01-27 21:35:26+00	1407	{"{\\"name\\": \\"1407.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1407\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3242	2024-01-27 21:35:26+00	1400	{"{\\"name\\": \\"1400-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1400\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1400.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1400\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3284	2024-01-27 21:35:26.004+00	1469	{"{\\"name\\": \\"1469.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1469\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3247	2024-01-27 21:35:26.001+00	1401	{"{\\"name\\": \\"1401-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1401\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1401.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1401\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1401T_G16-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1401\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G16\\"}","{\\"name\\": \\"1401T_G16.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1401\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G16\\"}"}
3234	2024-01-27 21:35:26+00	1395	{"{\\"name\\": \\"1395.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1395\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3236	2024-01-27 21:35:26+00	1396	{"{\\"name\\": \\"1396.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1396\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3239	2024-01-27 21:35:26+00	1397	{"{\\"name\\": \\"1397-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1397\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1397.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1397\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3250	2024-01-27 21:35:26.001+00	1404	{"{\\"name\\": \\"1404T-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1404\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1404T-3.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1404\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1404T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1404\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3255	2024-01-27 21:35:26.001+00	1415	{"{\\"name\\": \\"1415.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1415\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3254	2024-01-27 21:35:26.001+00	1421	{"{\\"name\\": \\"1421.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1421\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3253	2024-01-27 21:35:26.001+00	1443	{"{\\"name\\": \\"1443.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1443\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3267	2024-01-27 21:35:26.002+00	1445	{"{\\"name\\": \\"1445-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1445\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1445.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1445\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3270	2024-01-27 21:35:26.003+00	1446	{"{\\"name\\": \\"1446-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1446\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1446.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1446\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3259	2024-01-27 21:35:26.002+00	1453	{"{\\"name\\": \\"1453.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1453\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3274	2024-01-27 21:35:26.003+00	1447	{"{\\"name\\": \\"1447-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1447\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1447.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1447\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3268	2024-01-27 21:35:26.002+00	1463	{"{\\"name\\": \\"1463.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1463\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3265	2024-01-27 21:35:26.002+00	1458	{"{\\"name\\": \\"1458.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1458\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3266	2024-01-27 21:35:26.002+00	1459	{"{\\"name\\": \\"1459-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1459\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1459.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1459\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3264	2024-01-27 21:35:26.002+00	1454	{"{\\"name\\": \\"1454.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1454\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3269	2024-01-27 21:35:26.002+00	1464	{"{\\"name\\": \\"1464.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1464\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3258	2024-01-27 21:35:26.001+00	1449	{"{\\"name\\": \\"1449-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1449\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1449.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1449\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3261	2024-01-27 21:35:26.001+00	1427	{"{\\"name\\": \\"1427.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1427\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3260	2024-01-27 21:35:26.002+00	1455	{"{\\"name\\": \\"1455.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1455\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3281	2024-01-27 21:35:26.003+00	1465	{"{\\"name\\": \\"1465.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1465\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3280	2024-01-27 21:35:26.003+00	1470	{"{\\"name\\": \\"1470.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1470\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3273	2024-01-27 21:35:26.003+00	1466	{"{\\"name\\": \\"1466.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1466\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3271	2024-01-27 21:35:26.003+00	14721	{"{\\"name\\": \\"14721.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"14721\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3272	2024-01-27 21:35:26.003+00	1471	{"{\\"name\\": \\"1471.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1471\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3276	2024-01-27 21:35:26.003+00	1474	{"{\\"name\\": \\"1474.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1474\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3257	2024-01-27 21:35:26.001+00	1451	{"{\\"name\\": \\"1451.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1451\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3263	2024-01-27 21:35:26.002+00	1456	{"{\\"name\\": \\"1456.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1456\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3262	2024-01-27 21:35:26.002+00	1452	{"{\\"name\\": \\"1452.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1452\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3282	2024-01-27 21:35:26.003+00	1467	{"{\\"name\\": \\"1467.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1467\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3279	2024-01-27 21:35:26.003+00	1476	{"{\\"name\\": \\"1476.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1476\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3275	2024-01-27 21:35:26.003+00	1457	{"{\\"name\\": \\"1457.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1457\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3278	2024-01-27 21:35:26.003+00	1486	{"{\\"name\\": \\"1486.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1486\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3277	2024-01-27 21:35:26.003+00	1429	{"{\\"name\\": \\"1429.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1429\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1429_MAVİ.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1429\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"MAVİ\\"}"}
3256	2024-01-27 21:35:26.001+00	1441	{"{\\"name\\": \\"1441.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1441\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3252	2024-01-27 21:35:26.001+00	1442	{"{\\"name\\": \\"1442.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1442\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3286	2024-01-27 21:35:26.004+00	1490	{"{\\"name\\": \\"1490.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1490\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3294	2024-01-27 21:35:26.005+00	1491	{"{\\"name\\": \\"1491.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1491\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3295	2024-01-27 21:35:26.005+00	1499	{"{\\"name\\": \\"1499.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1499\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3296	2024-01-27 21:35:26.005+00	1531	{"{\\"name\\": \\"1531.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1531\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3291	2024-01-27 21:35:26.004+00	1500	{"{\\"name\\": \\"1500.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1500\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3290	2024-01-27 21:35:26.004+00	1492	{"{\\"name\\": \\"1492.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1492\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3303	2024-01-27 21:35:26.005+00	1542	{"{\\"name\\": \\"1542.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1542\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3299	2024-01-27 21:35:26.005+00	1548	{"{\\"name\\": \\"1548.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1548\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3306	2024-01-27 21:35:26.006+00	1547	{"{\\"name\\": \\"1547.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1547\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3302	2024-01-27 21:35:26.005+00	1502	{"{\\"name\\": \\"1502.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1502\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3307	2024-01-27 21:35:26.006+00	1540	{"{\\"name\\": \\"1540.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1540\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3287	2024-01-27 21:35:26.004+00	1493	{"{\\"name\\": \\"1493.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1493\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3301	2024-01-27 21:35:26.005+00	1549	{"{\\"name\\": \\"1549.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1549\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3308	2024-01-27 21:35:26.006+00	1568	{"{\\"name\\": \\"1568.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1568\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3288	2024-01-27 21:35:26.004+00	1496	{"{\\"name\\": \\"1496.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1496\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3297	2024-01-27 21:35:26.005+00	1528	{"{\\"name\\": \\"1528.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1528\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3320	2024-01-27 21:35:26.007+00	1574	{"{\\"name\\": \\"1574.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1574\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3289	2024-01-27 21:35:26.004+00	1478	{"{\\"name\\": \\"1478.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1478\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3293	2024-01-27 21:35:26.005+00	1530	{"{\\"name\\": \\"1530.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1530\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3292	2024-01-27 21:35:26.004+00	1498	{"{\\"name\\": \\"1498.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1498\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3298	2024-01-27 21:35:26.005+00	1552	{"{\\"name\\": \\"1552.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1552\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3312	2024-01-27 21:35:26.006+00	1575	{"{\\"name\\": \\"1575.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1575\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3315	2024-01-27 21:35:26.006+00	1576	{"{\\"name\\": \\"1576.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1576\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3313	2024-01-27 21:35:26.006+00	1577	{"{\\"name\\": \\"1577.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1577\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3316	2024-01-27 21:35:26.006+00	16011	{"{\\"name\\": \\"16011.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"16011\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3319	2024-01-27 21:35:26.007+00	1616	{"{\\"name\\": \\"1616.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1616\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3321	2024-01-27 21:35:26.007+00	1617	{"{\\"name\\": \\"1617.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1617\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3305	2024-01-27 21:35:26.006+00	1569	{"{\\"name\\": \\"1569.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1569\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3300	2024-01-27 21:35:26.005+00	1560	{"{\\"name\\": \\"1560.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1560\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3324	2024-01-27 21:35:26.007+00	1562	{"{\\"name\\": \\"1562.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1562\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3309	2024-01-27 21:35:26.006+00	1570	{"{\\"name\\": \\"1570.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1570\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3314	2024-01-27 21:35:26.006+00	1572	{"{\\"name\\": \\"1572.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1572\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3304	2024-01-27 21:35:26.006+00	1566	{"{\\"name\\": \\"1566.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1566\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3317	2024-01-27 21:35:26.007+00	1615	{"{\\"name\\": \\"1615.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1615\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3323	2024-01-27 21:35:26.007+00	1619	{"{\\"name\\": \\"1619.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1619\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3311	2024-01-27 21:35:26.006+00	1580	{"{\\"name\\": \\"1580.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1580\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3318	2024-01-27 21:35:26.007+00	1582	{"{\\"name\\": \\"1582.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1582\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3310	2024-01-27 21:35:26.006+00	1573	{"{\\"name\\": \\"1573.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1573\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3322	2024-01-27 21:35:26.007+00	1599	{"{\\"name\\": \\"1599.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1599\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3349	2024-01-27 21:35:26.011+00	1450	{"{\\"name\\": \\"1450-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1450\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1450.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1450\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3334	2024-01-27 21:35:26.01+00	1578	{"{\\"name\\": \\"1578.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1578\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3344	2024-01-27 21:35:26.01+00	1612	{"{\\"name\\": \\"1612.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1612\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3333	2024-01-27 21:35:26.01+00	1621	{"{\\"name\\": \\"1621.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1621\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3325	2024-01-27 21:35:26.007+00	1622	{"{\\"name\\": \\"1622.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1622\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3329	2024-01-27 21:35:26.008+00	1626	{"{\\"name\\": \\"1626.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1626\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3326	2024-01-27 21:35:26.007+00	1624	{"{\\"name\\": \\"1624.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1624\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3327	2024-01-27 21:35:26.007+00	1625	{"{\\"name\\": \\"1625.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1625\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3330	2024-01-27 21:35:26.008+00	1627	{"{\\"name\\": \\"1627.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1627\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3343	2024-01-27 21:35:26.011+00	1618	{"{\\"name\\": \\"1618.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1618\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3332	2024-01-27 21:35:26.009+00	1628	{"{\\"name\\": \\"1628.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1628\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3350	2024-01-27 21:35:26.011+00	1629	{"{\\"name\\": \\"1629.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1629\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3331	2024-01-27 21:35:26.009+00	1641	{"{\\"name\\": \\"1641.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1641\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3328	2024-01-27 21:35:26.008+00	1623	{"{\\"name\\": \\"1623.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1623\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3338	2024-01-27 21:35:26.01+00	1563	{"{\\"name\\": \\"1563.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1563\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3337	2024-01-27 21:35:26.01+00	1643	{"{\\"name\\": \\"1643.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1643\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3335	2024-01-27 21:35:26.01+00	1642	{"{\\"name\\": \\"1642.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1642\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3347	2024-01-27 21:35:26.011+00	1647	{"{\\"name\\": \\"1647.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1647\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3353	2024-01-27 21:35:26.011+00	1648	{"{\\"name\\": \\"1648T.jpeg\\", \\"annex\\": \\"T\\", \\"design\\": \\"1648\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3360	2024-01-27 21:35:26.012+00	1650	{"{\\"name\\": \\"1650.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1650\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3336	2024-01-27 21:35:26.01+00	1579	{"{\\"name\\": \\"1579.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1579\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3342	2024-01-27 21:35:26.011+00	1654	{"{\\"name\\": \\"1654.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1654\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3339	2024-01-27 21:35:26.01+00	1655	{"{\\"name\\": \\"1655.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1655\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3345	2024-01-27 21:35:26.011+00	1644	{"{\\"name\\": \\"1644T.jpeg\\", \\"annex\\": \\"T\\", \\"design\\": \\"1644\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3351	2024-01-27 21:35:26.011+00	1656	{"{\\"name\\": \\"1656.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1656\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3341	2024-01-27 21:35:26.011+00	1620	{"{\\"name\\": \\"1620.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1620\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3348	2024-01-27 21:35:26.011+00	1669	{"{\\"name\\": \\"1669_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1669\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3352	2024-01-27 21:35:26.011+00	24006	{"{\\"name\\": \\"24006.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24006\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3359	2024-01-27 21:35:26.012+00	24103	{"{\\"name\\": \\"24103.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24103\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3354	2024-01-27 21:35:26.011+00	2002	{"{\\"name\\": \\"2002_F06-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"2002\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"F06\\"}","{\\"name\\": \\"2002_F06.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"2002\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"F06\\"}"}
3358	2024-01-27 21:35:26.011+00	24143	{"{\\"name\\": \\"24143.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24143\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3346	2024-01-27 21:35:26.011+00	1661	{"{\\"name\\": \\"1661_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1661\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3357	2024-01-27 21:35:26.012+00	24146	{"{\\"name\\": \\"24146.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24146\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3355	2024-01-27 21:35:26.011+00	1662	{"{\\"name\\": \\"1662_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1662\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3356	2024-01-27 21:35:26.011+00	24147	{"{\\"name\\": \\"24147.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24147\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3361	2024-01-27 21:35:26.012+00	1666	{"{\\"name\\": \\"1666_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1666\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3369	2024-01-27 21:35:26.012+00	1651	{"{\\"name\\": \\"1651T.jpeg\\", \\"annex\\": \\"T\\", \\"design\\": \\"1651\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3375	2024-01-27 21:35:26.012+00	1652	{"{\\"name\\": \\"1652\\", \\"annex\\": \\"\\", \\"design\\": \\"1652\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3363	2024-01-27 21:35:26.012+00	1657	{"{\\"name\\": \\"1657.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1657\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3367	2024-01-27 21:35:26.012+00	1668	{"{\\"name\\": \\"1668_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1668\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3366	2024-01-27 21:35:26.012+00	24111	{"{\\"name\\": \\"24111.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24111\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3364	2024-01-27 21:35:26.012+00	1645	{"{\\"name\\": \\"1645T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1645\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3372	2024-01-27 21:35:26.012+00	24116	{"{\\"name\\": \\"24116T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"24116\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3377	2024-01-27 21:35:26.012+00	24117	{"{\\"name\\": \\"24117-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24117\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24117.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24117\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3378	2024-01-27 21:35:26.012+00	24154	{"{\\"name\\": \\"24154.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24154\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3365	2024-01-27 21:35:26.012+00	24019	{"{\\"name\\": \\"24019i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24019\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3389	2024-01-27 21:35:26.013+00	24155	{"{\\"name\\": \\"24155.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24155\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3373	2024-01-27 21:35:26.012+00	1646	{"{\\"name\\": \\"1646.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1646\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3374	2024-01-27 21:35:26.012+00	24156	{"{\\"name\\": \\"24156.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24156\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3371	2024-01-27 21:35:26.012+00	24157	{"{\\"name\\": \\"24157.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24157\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3362	2024-01-27 21:35:26.012+00	24148	{"{\\"name\\": \\"24148.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24148\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3376	2024-01-27 21:35:26.012+00	24023	{"{\\"name\\": \\"24023i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24023\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3368	2024-01-27 21:35:26.012+00	24161	{"{\\"name\\": \\"24161.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24161\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3382	2024-01-27 21:35:26.012+00	24166	{"{\\"name\\": \\"24166.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24166\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3370	2024-01-27 21:35:26.012+00	24159	{"{\\"name\\": \\"24159.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24159\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3379	2024-01-27 21:35:26.012+00	24168	{"{\\"name\\": \\"24168.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24168\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3386	2024-01-27 21:35:26.013+00	24167	{"{\\"name\\": \\"24167.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24167\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3381	2024-01-27 21:35:26.012+00	24170	{"{\\"name\\": \\"24170.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24170\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3388	2024-01-27 21:35:26.013+00	24400	{"{\\"name\\": \\"24400.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24400\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3391	2024-01-27 21:35:26.013+00	24421	{"{\\"name\\": \\"24421.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24421\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3384	2024-01-27 21:35:26.012+00	24033	{"{\\"name\\": \\"24033.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24033\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3387	2024-01-27 21:35:26.013+00	24171	{"{\\"name\\": \\"24171.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24171\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3385	2024-01-27 21:35:26.012+00	24357	{"{\\"name\\": \\"24357.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24357\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3394	2024-01-27 21:35:26.013+00	24403	{"{\\"name\\": \\"24403.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24403\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3390	2024-01-27 21:35:26.013+00	24193	{"{\\"name\\": \\"24193.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24193\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3383	2024-01-27 21:35:26.012+00	24362	{"{\\"name\\": \\"24362.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24362\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3380	2024-01-27 21:35:26.012+00	24205	{"{\\"name\\": \\"24205.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24205\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3395	2024-01-27 21:35:26.013+00	24467	{"{\\"name\\": \\"24467.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24467\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3392	2024-01-27 21:35:26.013+00	24392	{"{\\"name\\": \\"24392.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24392\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3397	2024-01-27 21:35:26.013+00	24406	{"{\\"name\\": \\"24406.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24406\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3423	2024-01-27 21:35:26.014+00	1659	{"{\\"name\\": \\"1659_ham.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"1659\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"ham\\"}"}
3424	2024-01-27 21:35:26.014+00	24207	{"{\\"name\\": \\"24207.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24207\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3403	2024-01-27 21:35:26.013+00	24470	{"{\\"name\\": \\"24470.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24470\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3399	2024-01-27 21:35:26.013+00	24473	{"{\\"name\\": \\"24473-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24473\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24473.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24473\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3401	2024-01-27 21:35:26.013+00	24477	{"{\\"name\\": \\"24477.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24477\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3404	2024-01-27 21:35:26.013+00	24448	{"{\\"name\\": \\"24448.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24448\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3402	2024-01-27 21:35:26.013+00	24504	{"{\\"name\\": \\"24504.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24504\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3425	2024-01-27 21:35:26.014+00	24496	{"{\\"name\\": \\"24496.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24496\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3406	2024-01-27 21:35:26.013+00	24491	{"{\\"name\\": \\"24491_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24491\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3405	2024-01-27 21:35:26.013+00	24516	{"{\\"name\\": \\"24516.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24516\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3414	2024-01-27 21:35:26.014+00	24520	{"{\\"name\\": \\"24520.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24520\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3408	2024-01-27 21:35:26.014+00	24518	{"{\\"name\\": \\"24518.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24518\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3439	2024-01-27 21:35:26.015+00	24553	{"{\\"name\\": \\"24553.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24553\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3409	2024-01-27 21:35:26.014+00	24515	{"{\\"name\\": \\"24515_G50-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24515\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G50\\"}","{\\"name\\": \\"24515_G50.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24515\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G50\\"}","{\\"name\\": \\"24515_K136.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24515\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K136\\"}"}
3398	2024-01-27 21:35:26.013+00	24068	{"{\\"name\\": \\"24068-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24068\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24068.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24068\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3422	2024-01-27 21:35:26.014+00	24534	{"{\\"name\\": \\"24534.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24534\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3407	2024-01-27 21:35:26.014+00	24451	{"{\\"name\\": \\"24451_G50.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24451\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G50\\"}"}
3421	2024-01-27 21:35:26.014+00	24535	{"{\\"name\\": \\"24535_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24535\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3413	2024-01-27 21:35:26.014+00	24522	{"{\\"name\\": \\"24522_G50.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24522\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G50\\"}"}
3412	2024-01-27 21:35:26.014+00	24523	{"{\\"name\\": \\"24523_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24523\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3428	2024-01-27 21:35:26.014+00	24546	{"{\\"name\\": \\"24546_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24546\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3420	2024-01-27 21:35:26.014+00	24526	{"{\\"name\\": \\"24526.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24526\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3417	2024-01-27 21:35:26.014+00	24206	{"{\\"name\\": \\"24206.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24206\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3418	2024-01-27 21:35:26.014+00	24529	{"{\\"name\\": \\"24529_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24529\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3416	2024-01-27 21:35:26.014+00	24530	{"{\\"name\\": \\"24530.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24530\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3419	2024-01-27 21:35:26.014+00	24531	{"{\\"name\\": \\"24531_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24531\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3415	2024-01-27 21:35:26.014+00	24398	{"{\\"name\\": \\"24398-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24398\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24398.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24398\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24398i_G07-2.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24398\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G07\\"}","{\\"name\\": \\"24398i_G07.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24398\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3426	2024-01-27 21:35:26.014+00	24542	{"{\\"name\\": \\"24542.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24542\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3455	2024-01-27 21:35:26.016+00	24577	{"{\\"name\\": \\"24577.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24577\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3427	2024-01-27 21:35:26.014+00	24544	{"{\\"name\\": \\"24544.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24544\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3410	2024-01-27 21:35:26.014+00	24407	{"{\\"name\\": \\"24407_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24407\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24407_Kartela-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24407\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24407_Kartela-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24407\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24407_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24407\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3454	2024-01-27 21:35:26.016+00	24539	{"{\\"name\\": \\"24539-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24539\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24539.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24539\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3436	2024-01-27 21:35:26.015+00	24536	{"{\\"name\\": \\"24536-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24536\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24536.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24536\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3431	2024-01-27 21:35:26.015+00	24545	{"{\\"name\\": \\"24545.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24545\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24545_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24545\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3429	2024-01-27 21:35:26.015+00	24533	{"{\\"name\\": \\"24533-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24533-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24533.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24533_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24533\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3434	2024-01-27 21:35:26.015+00	24547	{"{\\"name\\": \\"24547_G07-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24547\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G07\\"}","{\\"name\\": \\"24547_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24547\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3435	2024-01-27 21:35:26.015+00	24550	{"{\\"name\\": \\"24550.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24550\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3437	2024-01-27 21:35:26.015+00	24551	{"{\\"name\\": \\"24551.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24551\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3443	2024-01-27 21:35:26.015+00	24559	{"{\\"name\\": \\"24559.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24559\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3442	2024-01-27 21:35:26.015+00	24560	{"{\\"name\\": \\"24560.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24560\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3430	2024-01-27 21:35:26.015+00	24540	{"{\\"name\\": \\"24540.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24540\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24540_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24540\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3447	2024-01-27 21:35:26.015+00	24563	{"{\\"name\\": \\"24563.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24563\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3453	2024-01-27 21:35:26.015+00	24565	{"{\\"name\\": \\"24565.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24565\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3438	2024-01-27 21:35:26.015+00	24552	{"{\\"name\\": \\"24552.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24552\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3445	2024-01-27 21:35:26.015+00	24561	{"{\\"name\\": \\"24561.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24561\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3448	2024-01-27 21:35:26.015+00	24564	{"{\\"name\\": \\"24564.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24564\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24564i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24564\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24564T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"24564\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3450	2024-01-27 21:35:26.015+00	24567	{"{\\"name\\": \\"24567.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24567\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3440	2024-01-27 21:35:26.015+00	24554	{"{\\"name\\": \\"24554.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24554\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3444	2024-01-27 21:35:26.015+00	24541	{"{\\"name\\": \\"24541-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24541\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24541.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24541\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3451	2024-01-27 21:35:26.015+00	24555	{"{\\"name\\": \\"24555.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24555\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24555_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24555\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3452	2024-01-27 21:35:26.016+00	24570	{"{\\"name\\": \\"24570.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24570\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3441	2024-01-27 21:35:26.015+00	24557	{"{\\"name\\": \\"24557.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24557\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3432	2024-01-27 21:35:26.015+00	24543	{"{\\"name\\": \\"24543_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24543\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3449	2024-01-27 21:35:26.015+00	24558	{"{\\"name\\": \\"24558-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24558\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24558-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24558\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24558.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24558\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24558_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24558\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3459	2024-01-27 21:35:26.016+00	24574	{"{\\"name\\": \\"24574.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24574\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3464	2024-01-27 21:35:26.016+00	24562	{"{\\"name\\": \\"24562-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24562\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24562.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24562\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24562_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24562\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3467	2024-01-27 21:35:26.016+00	24581	{"{\\"name\\": \\"24581.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24581\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3466	2024-01-27 21:35:26.016+00	24585	{"{\\"name\\": \\"24585.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24585\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3478	2024-01-27 21:35:26.017+00	24582	{"{\\"name\\": \\"24582.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24582\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3471	2024-01-27 21:35:26.016+00	24586	{"{\\"name\\": \\"24586.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24586\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3470	2024-01-27 21:35:26.016+00	24587	{"{\\"name\\": \\"24587.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24587\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3468	2024-01-27 21:35:26.016+00	24589	{"{\\"name\\": \\"24589.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24589\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3481	2024-01-27 21:35:26.017+00	24588	{"{\\"name\\": \\"24588-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24588\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24588-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24588\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24588.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24588\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3463	2024-01-27 21:35:26.016+00	24569	{"{\\"name\\": \\"24569.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24569\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3488	2024-01-27 21:35:26.017+00	24592	{"{\\"name\\": \\"24592.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24592\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3462	2024-01-27 21:35:26.016+00	24583	{"{\\"name\\": \\"24583.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24583\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3473	2024-01-27 21:35:26.016+00	24591	{"{\\"name\\": \\"24591.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24591\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3474	2024-01-27 21:35:26.016+00	24596	{"{\\"name\\": \\"24596-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24596\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24596.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24596\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3475	2024-01-27 21:35:26.016+00	24602	{"{\\"name\\": \\"24602.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24602\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3465	2024-01-27 21:35:26.016+00	24532	{"{\\"name\\": \\"24532.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24532\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3483	2024-01-27 21:35:26.017+00	24601	{"{\\"name\\": \\"24601.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24601\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3456	2024-01-27 21:35:26.016+00	24576	{"{\\"name\\": \\"24576.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24576\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3477	2024-01-27 21:35:26.017+00	24604	{"{\\"name\\": \\"24604-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24604\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24604.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24604\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3486	2024-01-27 21:35:26.017+00	24605	{"{\\"name\\": \\"24605-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24605\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24605.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24605\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3479	2024-01-27 21:35:26.017+00	24612	{"{\\"name\\": \\"24612.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24612\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3460	2024-01-27 21:35:26.016+00	24571	{"{\\"name\\": \\"24571.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24571\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3480	2024-01-27 21:35:26.017+00	24608	{"{\\"name\\": \\"24608-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24608\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24608.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24608\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3487	2024-01-27 21:35:26.017+00	24615	{"{\\"name\\": \\"24615.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24615\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3458	2024-01-27 21:35:26.016+00	24572	{"{\\"name\\": \\"24572.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24572\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3457	2024-01-27 21:35:26.016+00	24579	{"{\\"name\\": \\"24579.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24579\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3482	2024-01-27 21:35:26.017+00	24598	{"{\\"name\\": \\"24598.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24598\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3484	2024-01-27 21:35:26.017+00	24580	{"{\\"name\\": \\"24580.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24580\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24580_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24580\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3472	2024-01-27 21:35:26.016+00	24599	{"{\\"name\\": \\"24599.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24599\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3485	2024-01-27 21:35:26.017+00	24613	{"{\\"name\\": \\"24613-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24613\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24613.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24613\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3476	2024-01-27 21:35:26.016+00	24600	{"{\\"name\\": \\"24600.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24600\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3491	2024-01-27 21:35:26.017+00	24620	{"{\\"name\\": \\"24620.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24620\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3493	2024-01-27 21:35:26.017+00	24614	{"{\\"name\\": \\"24614-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24614\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24614.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24614\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3496	2024-01-27 21:35:26.017+00	24621	{"{\\"name\\": \\"24621-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24621\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24621.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24621\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3489	2024-01-27 21:35:26.017+00	24628	{"{\\"name\\": \\"24628.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24628\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3506	2024-01-27 21:35:26.018+00	24629	{"{\\"name\\": \\"24629-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24629\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24629.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24629\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3494	2024-01-27 21:35:26.017+00	24632	{"{\\"name\\": \\"24632-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24632\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24632.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24632\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3503	2024-01-27 21:35:26.018+00	24635	{"{\\"name\\": \\"24635-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24635\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24635.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24635\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3498	2024-01-27 21:35:26.017+00	24633	{"{\\"name\\": \\"24633-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24633\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24633-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24633\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24633.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24633\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3510	2024-01-27 21:35:26.018+00	24636	{"{\\"name\\": \\"24636-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24636\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24636.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24636\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3495	2024-01-27 21:35:26.017+00	24638	{"{\\"name\\": \\"24638.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24638\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3499	2024-01-27 21:35:26.017+00	24641	{"{\\"name\\": \\"24641.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24641\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3497	2024-01-27 21:35:26.017+00	24637	{"{\\"name\\": \\"24637-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24637\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24637.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24637\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3504	2024-01-27 21:35:26.018+00	24639	{"{\\"name\\": \\"24639-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24639\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24639.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24639\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3500	2024-01-27 21:35:26.018+00	24631	{"{\\"name\\": \\"24631.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24631\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3501	2024-01-27 21:35:26.018+00	24644	{"{\\"name\\": \\"24644-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24644\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24644.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24644\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3507	2024-01-27 21:35:26.018+00	24647	{"{\\"name\\": \\"24647.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24647\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3505	2024-01-27 21:35:26.018+00	24649	{"{\\"name\\": \\"24649.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24649\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3509	2024-01-27 21:35:26.018+00	24650	{"{\\"name\\": \\"24650-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24650\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24650.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24650\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3514	2024-01-27 21:35:26.018+00	24640	{"{\\"name\\": \\"24640-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24640\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24640.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24640\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3492	2024-01-27 21:35:26.017+00	24630	{"{\\"name\\": \\"24630-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24630\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24630-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24630\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}"}
3502	2024-01-27 21:35:26.018+00	24645	{"{\\"name\\": \\"24645.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24645\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3508	2024-01-27 21:35:26.018+00	24651	{"{\\"name\\": \\"24651.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24651\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3516	2024-01-27 21:35:26.018+00	24656	{"{\\"name\\": \\"24656.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24656\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3511	2024-01-27 21:35:26.018+00	24659	{"{\\"name\\": \\"24659.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24659\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3515	2024-01-27 21:35:26.018+00	24660	{"{\\"name\\": \\"24660.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24660\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3513	2024-01-27 21:35:26.018+00	24664	{"{\\"name\\": \\"24664.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24664\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3512	2024-01-27 21:35:26.018+00	24663	{"{\\"name\\": \\"24663.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24663\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24663_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24663\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3517	2024-01-27 21:35:26.018+00	24669	{"{\\"name\\": \\"24669.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24669\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3593	2024-01-27 21:35:26.021+00	24709	{"{\\"name\\": \\"24709.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24709\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3520	2024-01-27 21:35:26.019+00	24625	{"{\\"name\\": \\"24625.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24625\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3527	2024-01-27 21:35:26.019+00	24626	{"{\\"name\\": \\"24626.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24626\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3543	2024-01-27 21:35:26.019+00	24643	{"{\\"name\\": \\"24643.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24643\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3531	2024-01-27 21:35:26.019+00	24642	{"{\\"name\\": \\"24642.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24642\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3522	2024-01-27 21:35:26.019+00	24648	{"{\\"name\\": \\"24648.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24648\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3534	2024-01-27 21:35:26.019+00	24654	{"{\\"name\\": \\"24654.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24654\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3546	2024-01-27 21:35:26.019+00	24655	{"{\\"name\\": \\"24655.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24655\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3532	2024-01-27 21:35:26.019+00	24658	{"{\\"name\\": \\"24658.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24658\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3524	2024-01-27 21:35:26.019+00	24662	{"{\\"name\\": \\"24662.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24662\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3533	2024-01-27 21:35:26.019+00	24672	{"{\\"name\\": \\"24672.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24672\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3521	2024-01-27 21:35:26.019+00	24671	{"{\\"name\\": \\"24671-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24671\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24671.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24671\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3544	2024-01-27 21:35:26.019+00	24684	{"{\\"name\\": \\"24684i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24684\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3526	2024-01-27 21:35:26.019+00	24697	{"{\\"name\\": \\"24697-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24697.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3523	2024-01-27 21:35:26.019+00	24698	{"{\\"name\\": \\"24698.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24698\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3530	2024-01-27 21:35:26.019+00	24699	{"{\\"name\\": \\"24699-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24699.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3518	2024-01-27 21:35:26.018+00	24653	{"{\\"name\\": \\"24653.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24653\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24653_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24653\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3529	2024-01-27 21:35:26.019+00	24704	{"{\\"name\\": \\"24704.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24704\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3542	2024-01-27 21:35:26.019+00	24706	{"{\\"name\\": \\"24706.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24706\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3554	2024-01-27 21:35:26.02+00	24707	{"{\\"name\\": \\"24707.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24707\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3525	2024-01-27 21:35:26.019+00	24657	{"{\\"name\\": \\"24657.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24657\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3528	2024-01-27 21:35:26.019+00	24713	{"{\\"name\\": \\"24713.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24713\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3535	2024-01-27 21:35:26.019+00	24718	{"{\\"name\\": \\"24718.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24718\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3549	2024-01-27 21:35:26.019+00	24722	{"{\\"name\\": \\"24722.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24722\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3541	2024-01-27 21:35:26.019+00	24721	{"{\\"name\\": \\"24721.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24721\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3537	2024-01-27 21:35:26.019+00	24724	{"{\\"name\\": \\"24724.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24724\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3536	2024-01-27 21:35:26.019+00	24723	{"{\\"name\\": \\"24723.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24723\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3538	2024-01-27 21:35:26.019+00	24725	{"{\\"name\\": \\"24725.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24725\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3550	2024-01-27 21:35:26.02+00	24730	{"{\\"name\\": \\"24730.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24730\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3553	2024-01-27 21:35:26.02+00	24731	{"{\\"name\\": \\"24731.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24731\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3539	2024-01-27 21:35:26.019+00	24733	{"{\\"name\\": \\"24733.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24733\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3545	2024-01-27 21:35:26.019+00	24726	{"{\\"name\\": \\"24726.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24726\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3547	2024-01-27 21:35:26.019+00	24735	{"{\\"name\\": \\"24735.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24735\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3552	2024-01-27 21:35:26.02+00	24744	{"{\\"name\\": \\"24744.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24744\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3548	2024-01-27 21:35:26.019+00	24742	{"{\\"name\\": \\"24742.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24742\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3551	2024-01-27 21:35:26.02+00	24743	{"{\\"name\\": \\"24743.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24743\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3540	2024-01-27 21:35:26.019+00	24734	{"{\\"name\\": \\"24734.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24734\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3560	2024-01-27 21:35:26.02+00	24666	{"{\\"name\\": \\"24666i.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24666\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3564	2024-01-27 21:35:26.02+00	24667	{"{\\"name\\": \\"24667.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24667\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3570	2024-01-27 21:35:26.02+00	24668	{"{\\"name\\": \\"24668.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24668\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3589	2024-01-27 21:35:26.021+00	24695	{"{\\"name\\": \\"24695-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24695\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24695.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24695\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3574	2024-01-27 21:35:26.02+00	24685	{"{\\"name\\": \\"24685.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24685\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3580	2024-01-27 21:35:26.02+00	24708	{"{\\"name\\": \\"24708.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24708\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3557	2024-01-27 21:35:26.02+00	24732	{"{\\"name\\": \\"24732.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24732\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3568	2024-01-27 21:35:26.02+00	24741	{"{\\"name\\": \\"24741.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24741\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3567	2024-01-27 21:35:26.02+00	24745	{"{\\"name\\": \\"24745.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24745\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3582	2024-01-27 21:35:26.021+00	24746	{"{\\"name\\": \\"24746.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24746\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3565	2024-01-27 21:35:26.02+00	24750	{"{\\"name\\": \\"24750.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24750\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3577	2024-01-27 21:35:26.02+00	24754	{"{\\"name\\": \\"24754.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24754\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3572	2024-01-27 21:35:26.02+00	24753	{"{\\"name\\": \\"24753.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24753\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3587	2024-01-27 21:35:26.021+00	24755	{"{\\"name\\": \\"24755.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24755\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3558	2024-01-27 21:35:26.02+00	24758	{"{\\"name\\": \\"24758.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24758\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3578	2024-01-27 21:35:26.02+00	24763	{"{\\"name\\": \\"24763.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24763\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3592	2024-01-27 21:35:26.021+00	24764	{"{\\"name\\": \\"24764.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24764\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3561	2024-01-27 21:35:26.02+00	24773	{"{\\"name\\": \\"24773.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24773\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3559	2024-01-27 21:35:26.02+00	24771	{"{\\"name\\": \\"24771.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24771\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3556	2024-01-27 21:35:26.02+00	24767	{"{\\"name\\": \\"24767.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24767\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3581	2024-01-27 21:35:26.021+00	24779	{"{\\"name\\": \\"24779.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24779\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3576	2024-01-27 21:35:26.02+00	24787	{"{\\"name\\": \\"24787.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24787\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3566	2024-01-27 21:35:26.02+00	24762	{"{\\"name\\": \\"24762.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24762\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3562	2024-01-27 21:35:26.02+00	24791	{"{\\"name\\": \\"24791.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24791\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3563	2024-01-27 21:35:26.02+00	24782	{"{\\"name\\": \\"24782.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24782\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3573	2024-01-27 21:35:26.02+00	24793	{"{\\"name\\": \\"24793.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24793\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3575	2024-01-27 21:35:26.02+00	24810	{"{\\"name\\": \\"24810.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24810\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3584	2024-01-27 21:35:26.021+00	24781	{"{\\"name\\": \\"24781.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24781\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3571	2024-01-27 21:35:26.02+00	24784	{"{\\"name\\": \\"24784.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24784\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3579	2024-01-27 21:35:26.02+00	24828	{"{\\"name\\": \\"24828.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24828\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3583	2024-01-27 21:35:26.021+00	24829	{"{\\"name\\": \\"24829.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24829\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3588	2024-01-27 21:35:26.021+00	24833	{"{\\"name\\": \\"24833.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24833\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3586	2024-01-27 21:35:26.021+00	24836	{"{\\"name\\": \\"24836.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24836\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3585	2024-01-27 21:35:26.021+00	24832	{"{\\"name\\": \\"24832-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24832\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24832.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24832\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3590	2024-01-27 21:35:26.021+00	24838	{"{\\"name\\": \\"24838.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24838\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3591	2024-01-27 21:35:26.021+00	24842	{"{\\"name\\": \\"24842.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24842\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3569	2024-01-27 21:35:26.02+00	24774	{"{\\"name\\": \\"24774.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24774\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3609	2024-01-27 21:35:26.022+00	24813	{"{\\"name\\": \\"24813.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24813\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3602	2024-01-27 21:35:26.021+00	24811	{"{\\"name\\": \\"24811.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24811\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3606	2024-01-27 21:35:26.021+00	24844	{"{\\"name\\": \\"24844.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24844\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3612	2024-01-27 21:35:26.022+00	24846	{"{\\"name\\": \\"24846.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24846\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3595	2024-01-27 21:35:26.021+00	24848	{"{\\"name\\": \\"24848.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24848\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3618	2024-01-27 21:35:26.022+00	24855	{"{\\"name\\": \\"24855.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24855\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3605	2024-01-27 21:35:26.021+00	24854	{"{\\"name\\": \\"24854.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24854\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3600	2024-01-27 21:35:26.021+00	24856	{"{\\"name\\": \\"24856.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24856\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3599	2024-01-27 21:35:26.021+00	24852	{"{\\"name\\": \\"24852-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24852\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24852.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24852\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3596	2024-01-27 21:35:26.021+00	24847	{"{\\"name\\": \\"24847.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24847\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3597	2024-01-27 21:35:26.021+00	24849	{"{\\"name\\": \\"24849.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24849\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3611	2024-01-27 21:35:26.022+00	24857	{"{\\"name\\": \\"24857-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24857\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24857.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24857\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3603	2024-01-27 21:35:26.021+00	24766	{"{\\"name\\": \\"24766.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24766\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3623	2024-01-27 21:35:26.022+00	24858	{"{\\"name\\": \\"24858-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24858\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24858.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24858\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3601	2024-01-27 21:35:26.021+00	24859	{"{\\"name\\": \\"24859.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24859\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3598	2024-01-27 21:35:26.021+00	24790	{"{\\"name\\": \\"24790.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24790\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3615	2024-01-27 21:35:26.022+00	24860	{"{\\"name\\": \\"24860-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24860\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24860.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24860\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3604	2024-01-27 21:35:26.021+00	24869	{"{\\"name\\": \\"24869.jpeg\\", \\"annex\\": \\"\\", \\"design\\": \\"24869\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3624	2024-01-27 21:35:26.022+00	24861	{"{\\"name\\": \\"24861-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24861\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24861.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24861\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3627	2024-01-27 21:35:26.022+00	24862	{"{\\"name\\": \\"24862-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24862\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24862.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24862\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3607	2024-01-27 21:35:26.021+00	25030	{"{\\"name\\": \\"25030_D10.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25030\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"D10\\"}"}
3608	2024-01-27 21:35:26.022+00	25130	{"{\\"name\\": \\"25130.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25130\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3614	2024-01-27 21:35:26.022+00	25184	{"{\\"name\\": \\"25184.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25184\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3616	2024-01-27 21:35:26.022+00	25209	{"{\\"name\\": \\"25209.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25209\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3613	2024-01-27 21:35:26.022+00	25208	{"{\\"name\\": \\"25208.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25208\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3610	2024-01-27 21:35:26.022+00	25153	{"{\\"name\\": \\"25153.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25153\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3622	2024-01-27 21:35:26.022+00	25204	{"{\\"name\\": \\"25204.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25204\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3625	2024-01-27 21:35:26.022+00	25212	{"{\\"name\\": \\"25212.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25212\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3619	2024-01-27 21:35:26.022+00	25211	{"{\\"name\\": \\"25211.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25211\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3620	2024-01-27 21:35:26.022+00	25215	{"{\\"name\\": \\"25215.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25215\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3617	2024-01-27 21:35:26.022+00	25216	{"{\\"name\\": \\"25216.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25216\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3621	2024-01-27 21:35:26.022+00	25217	{"{\\"name\\": \\"25217.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25217\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3626	2024-01-27 21:35:26.022+00	25226	{"{\\"name\\": \\"25226-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25226\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25226.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25226\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3659	2024-01-27 21:35:26.028+00	25300	{"{\\"name\\": \\"25300.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25300\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3639	2024-01-27 21:35:26.023+00	24748	{"{\\"name\\": \\"24748.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24748\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3643	2024-01-27 21:35:26.025+00	24749	{"{\\"name\\": \\"24749.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24749\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3644	2024-01-27 21:35:26.026+00	24818	{"{\\"name\\": \\"24818.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24818\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3630	2024-01-27 21:35:26.022+00	24816	{"{\\"name\\": \\"24816.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24816\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3638	2024-01-27 21:35:26.023+00	25205	{"{\\"name\\": \\"25205.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25205\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3646	2024-01-27 21:35:26.026+00	25213	{"{\\"name\\": \\"25213-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25213\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25213-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25213\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25213.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25213\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3647	2024-01-27 21:35:26.023+00	25218	{"{\\"name\\": \\"25218-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25218\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25218-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25218\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25218.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25218\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3629	2024-01-27 21:35:26.022+00	25227	{"{\\"name\\": \\"25227.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25227\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3628	2024-01-27 21:35:26.022+00	25228	{"{\\"name\\": \\"25228-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25228\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25228.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25228\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3665	2024-01-27 21:35:26.028+00	25295	{"{\\"name\\": \\"25295.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25295\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3657	2024-01-27 21:35:26.027+00	25219	{"{\\"name\\": \\"25219-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25219\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25219-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25219\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25219.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25219\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3632	2024-01-27 21:35:26.023+00	25229	{"{\\"name\\": \\"25229-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25229\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25229.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25229\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3648	2024-01-27 21:35:26.026+00	25231	{"{\\"name\\": \\"25231-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25231\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25231.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25231\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3654	2024-01-27 21:35:26.027+00	25233	{"{\\"name\\": \\"25233.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25233\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3649	2024-01-27 21:35:26.027+00	25237	{"{\\"name\\": \\"25237T_K104.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"25237\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3633	2024-01-27 21:35:26.023+00	25254	{"{\\"name\\": \\"25254.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25254\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3634	2024-01-27 21:35:26.023+00	25263	{"{\\"name\\": \\"25263.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25263\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3635	2024-01-27 21:35:26.023+00	25264	{"{\\"name\\": \\"25264.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25264\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3637	2024-01-27 21:35:26.023+00	25268	{"{\\"name\\": \\"25268.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25268\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3636	2024-01-27 21:35:26.023+00	25265	{"{\\"name\\": \\"25265.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25265\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3642	2024-01-27 21:35:26.025+00	25270	{"{\\"name\\": \\"25270.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25270\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3641	2024-01-27 21:35:26.024+00	25272	{"{\\"name\\": \\"25272.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25272\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3640	2024-01-27 21:35:26.024+00	25269	{"{\\"name\\": \\"25269.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25269\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3655	2024-01-27 21:35:26.027+00	25278	{"{\\"name\\": \\"25278.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25278\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3645	2024-01-27 21:35:26.026+00	25279	{"{\\"name\\": \\"25279.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25279\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3651	2024-01-27 21:35:26.027+00	25286	{"{\\"name\\": \\"25286-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25286\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25286.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25286\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3652	2024-01-27 21:35:26.027+00	25287	{"{\\"name\\": \\"25287-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25287\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25287.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25287\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3653	2024-01-27 21:35:26.027+00	25289	{"{\\"name\\": \\"25289.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25289\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3658	2024-01-27 21:35:26.027+00	25299	{"{\\"name\\": \\"25299.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25299\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3656	2024-01-27 21:35:26.027+00	25292	{"{\\"name\\": \\"25292-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25292\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25292-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25292\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25292.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25292\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3682	2024-01-27 21:35:26.029+00	25221	{"{\\"name\\": \\"25221-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25221\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25221.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25221\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3662	2024-01-27 21:35:26.028+00	25234	{"{\\"name\\": \\"25234.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25234\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3671	2024-01-27 21:35:26.028+00	25235	{"{\\"name\\": \\"25235.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25235\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3677	2024-01-27 21:35:26.029+00	25236	{"{\\"name\\": \\"25236.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25236\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3661	2024-01-27 21:35:26.028+00	25238	{"{\\"name\\": \\"25238.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25238\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3675	2024-01-27 21:35:26.028+00	25257	{"{\\"name\\": \\"25257_G88-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25257\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G88\\"}","{\\"name\\": \\"25257_G88.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25257\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G88\\"}"}
3684	2024-01-27 21:35:26.029+00	25260	{"{\\"name\\": \\"25260-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25260\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25260.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25260\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3667	2024-01-27 21:35:26.026+00	25266	{"{\\"name\\": \\"25266-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25266\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25266-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25266\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25266.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25266\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3689	2024-01-27 21:35:26.029+00	25274	{"{\\"name\\": \\"25274.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25274\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3663	2024-01-27 21:35:26.028+00	25273	{"{\\"name\\": \\"25273.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25273\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3676	2024-01-27 21:35:26.029+00	25282	{"{\\"name\\": \\"25282.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25282\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3669	2024-01-27 21:35:26.026+00	25281	{"{\\"name\\": \\"25281.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25281\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3683	2024-01-27 21:35:26.029+00	25283	{"{\\"name\\": \\"25283.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25283\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3680	2024-01-27 21:35:26.029+00	25296	{"{\\"name\\": \\"25296.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25296\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3685	2024-01-27 21:35:26.029+00	25298	{"{\\"name\\": \\"25298.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25298\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3660	2024-01-27 21:35:26.028+00	25293	{"{\\"name\\": \\"25293-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25293\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25293.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25293\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3666	2024-01-27 21:35:26.028+00	25301	{"{\\"name\\": \\"25301.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25301\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3664	2024-01-27 21:35:26.028+00	25302	{"{\\"name\\": \\"25302.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25302\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3672	2024-01-27 21:35:26.028+00	25304	{"{\\"name\\": \\"25304.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25304\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3668	2024-01-27 21:35:26.028+00	25303	{"{\\"name\\": \\"25303.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25303\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3673	2024-01-27 21:35:26.028+00	25306	{"{\\"name\\": \\"25306.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25306\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3674	2024-01-27 21:35:26.028+00	25312	{"{\\"name\\": \\"25312.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25312\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3679	2024-01-27 21:35:26.029+00	36008	{"{\\"name\\": \\"36008.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"36008\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3678	2024-01-27 21:35:26.029+00	32009	{"{\\"name\\": \\"32009.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"32009\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3681	2024-01-27 21:35:26.029+00	36010	{"{\\"name\\": \\"36010.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"36010\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3687	2024-01-27 21:35:26.029+00	36013	{"{\\"name\\": \\"36013-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"36013\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"36013.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"36013\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3686	2024-01-27 21:35:26.029+00	48052	{"{\\"name\\": \\"48052.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48052\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3691	2024-01-27 21:35:26.029+00	48053	{"{\\"name\\": \\"48053.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48053\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48053_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48053\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3688	2024-01-27 21:35:26.029+00	48055	{"{\\"name\\": \\"48055-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48055\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48055.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48055\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3692	2024-01-27 21:35:26.029+00	48057	{"{\\"name\\": \\"48057.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48057\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3690	2024-01-27 21:35:26.029+00	48056	{"{\\"name\\": \\"48056.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48056\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48056_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48056\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3720	2024-01-27 21:35:26.031+00	25248	{"{\\"name\\": \\"25248.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25248\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3707	2024-01-27 21:35:26.03+00	25242	{"{\\"name\\": \\"25242.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25242\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3721	2024-01-27 21:35:26.031+00	25261	{"{\\"name\\": \\"25261.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25261\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3700	2024-01-27 21:35:26.03+00	25275	{"{\\"name\\": \\"25275.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25275\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3708	2024-01-27 21:35:26.03+00	25276	{"{\\"name\\": \\"25276.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25276\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3717	2024-01-27 21:35:26.031+00	25277	{"{\\"name\\": \\"25277.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25277\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3695	2024-01-27 21:35:26.029+00	25284	{"{\\"name\\": \\"25284.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25284\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3706	2024-01-27 21:35:26.03+00	25285	{"{\\"name\\": \\"25285-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25285\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25285.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25285\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3694	2024-01-27 21:35:26.029+00	36014	{"{\\"name\\": \\"36014.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"36014\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3710	2024-01-27 21:35:26.03+00	48013	{"{\\"name\\": \\"48013-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48013\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48013.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48013\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3716	2024-01-27 21:35:26.03+00	48054	{"{\\"name\\": \\"48054-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48054\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48054.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48054\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3696	2024-01-27 21:35:26.029+00	48058	{"{\\"name\\": \\"48058-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48058\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48058.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48058\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3697	2024-01-27 21:35:26.029+00	48059	{"{\\"name\\": \\"48059.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48059\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48059_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48059\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3714	2024-01-27 21:35:26.03+00	48060	{"{\\"name\\": \\"48060-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48060\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48060.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48060\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3698	2024-01-27 21:35:26.03+00	48068	{"{\\"name\\": \\"48068-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48068\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48068.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48068\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3703	2024-01-27 21:35:26.03+00	48077	{"{\\"name\\": \\"48077-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48077\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48077.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48077\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3701	2024-01-27 21:35:26.03+00	48073	{"{\\"name\\": \\"48073.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48073\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3702	2024-01-27 21:35:26.03+00	48078	{"{\\"name\\": \\"48078-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48078\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48078.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48078\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3709	2024-01-27 21:35:26.03+00	48079	{"{\\"name\\": \\"48079.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48079\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3718	2024-01-27 21:35:26.031+00	48082	{"{\\"name\\": \\"48082.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48082\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3704	2024-01-27 21:35:26.03+00	49054	{"{\\"name\\": \\"49054.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49054\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3705	2024-01-27 21:35:26.03+00	49055	{"{\\"name\\": \\"49055.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49055\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3715	2024-01-27 21:35:26.03+00	49057	{"{\\"name\\": \\"49057-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49057\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49057.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49057\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3712	2024-01-27 21:35:26.03+00	49056	{"{\\"name\\": \\"49056-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49056\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49056.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49056\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3711	2024-01-27 21:35:26.03+00	49058	{"{\\"name\\": \\"49058-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49058\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49058.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49058\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3713	2024-01-27 21:35:26.03+00	49059	{"{\\"name\\": \\"49059-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49059\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49059.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49059\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3699	2024-01-27 21:35:26.03+00	48072	{"{\\"name\\": \\"48072-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48072\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48072.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48072\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3719	2024-01-27 21:35:26.031+00	8154	{"{\\"name\\": \\"8154_S02-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8154\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"S02\\"}","{\\"name\\": \\"8154_S02.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8154\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"S02\\"}"}
3731	2024-01-27 21:35:26.031+00	25262	{"{\\"name\\": \\"25262.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25262\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3745	2024-01-27 21:35:26.032+00	48034	{"{\\"name\\": \\"48034.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48034\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3741	2024-01-27 21:35:26.031+00	48062	{"{\\"name\\": \\"48062.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48062\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3730	2024-01-27 21:35:26.031+00	48061	{"{\\"name\\": \\"48061-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48061\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48061.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48061\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3747	2024-01-27 21:35:26.032+00	49047	{"{\\"name\\": \\"49047-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49047\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49047.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49047\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3732	2024-01-27 21:35:26.031+00	48088	{"{\\"name\\": \\"48088.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48088\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3733	2024-01-27 21:35:26.031+00	49062	{"{\\"name\\": \\"49062.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49062\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3723	2024-01-27 21:35:26.031+00	49061	{"{\\"name\\": \\"49061.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49061\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3722	2024-01-27 21:35:26.031+00	49060	{"{\\"name\\": \\"49060.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49060\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3725	2024-01-27 21:35:26.031+00	8590	{"{\\"name\\": \\"8590.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8590\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3724	2024-01-27 21:35:26.031+00	8570	{"{\\"name\\": \\"8570.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8570\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3729	2024-01-27 21:35:26.031+00	8594	{"{\\"name\\": \\"8594.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8594\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3743	2024-01-27 21:35:26.032+00	49063	{"{\\"name\\": \\"49063-1.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49063\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"49063-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49063\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}"}
3752	2024-01-27 21:35:26.032+00	8653	{"{\\"name\\": \\"8653.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8653\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3728	2024-01-27 21:35:26.031+00	8649	{"{\\"name\\": \\"8649.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8649\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3735	2024-01-27 21:35:26.031+00	8678	{"{\\"name\\": \\"8678_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8678\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3727	2024-01-27 21:35:26.031+00	8645	{"{\\"name\\": \\"8645.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8645\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3738	2024-01-27 21:35:26.031+00	8682	{"{\\"name\\": \\"8682.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8682\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3726	2024-01-27 21:35:26.031+00	8644	{"{\\"name\\": \\"8644.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8644\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3739	2024-01-27 21:35:26.031+00	8679	{"{\\"name\\": \\"8679_K18-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8679\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K18\\"}","{\\"name\\": \\"8679_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8679\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3734	2024-01-27 21:35:26.031+00	8674	{"{\\"name\\": \\"8674_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8674\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"8674_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8674\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3742	2024-01-27 21:35:26.032+00	8651	{"{\\"name\\": \\"8651.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8651\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8651_K18-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8651\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K18\\"}","{\\"name\\": \\"8651_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8651\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3737	2024-01-27 21:35:26.031+00	8677	{"{\\"name\\": \\"8677_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8677\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3740	2024-01-27 21:35:26.031+00	8696	{"{\\"name\\": \\"8696.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8696\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3746	2024-01-27 21:35:26.032+00	8697	{"{\\"name\\": \\"8697-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8697.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8697\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3748	2024-01-27 21:35:26.032+00	8698	{"{\\"name\\": \\"8698-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8698\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8698.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8698\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3750	2024-01-27 21:35:26.032+00	8699	{"{\\"name\\": \\"8699-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8699.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8699\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3751	2024-01-27 21:35:26.032+00	8701	{"{\\"name\\": \\"8701.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8701\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3749	2024-01-27 21:35:26.032+00	8707	{"{\\"name\\": \\"8707.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8707\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3753	2024-01-27 21:35:26.032+00	8700	{"{\\"name\\": \\"8700-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8700\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8700.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8700\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3769	2024-01-27 21:35:26.033+00	48039	{"{\\"name\\": \\"48039_K243.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48039\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K243\\"}"}
3783	2024-01-27 21:35:26.033+00	48043	{"{\\"name\\": \\"48043.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48043\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3789	2024-01-27 21:35:26.033+00	48065	{"{\\"name\\": \\"48065.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48065\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3755	2024-01-27 21:35:26.032+00	48063	{"{\\"name\\": \\"48063.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48063\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48063_T04.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48063\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"T04\\"}"}
3767	2024-01-27 21:35:26.033+00	48064	{"{\\"name\\": \\"48064.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48064\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3759	2024-01-27 21:35:26.032+00	49049	{"{\\"name\\": \\"49049.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49049\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3776	2024-01-27 21:35:26.033+00	49051	{"{\\"name\\": \\"49051.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49051\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3787	2024-01-27 21:35:26.033+00	49052	{"{\\"name\\": \\"49052.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49052\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3757	2024-01-27 21:35:26.032+00	49064	{"{\\"name\\": \\"49064.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49064\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3782	2024-01-27 21:35:26.033+00	72007	{"{\\"name\\": \\"72007.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"72007\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3771	2024-01-27 21:35:26.033+00	62005	{"{\\"name\\": \\"62005.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"62005\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3781	2024-01-27 21:35:26.033+00	8665	{"{\\"name\\": \\"8665-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8665\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8665.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8665\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3768	2024-01-27 21:35:26.033+00	8664	{"{\\"name\\": \\"8664_K18.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8664\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K18\\"}"}
3754	2024-01-27 21:35:26.031+00	8683	{"{\\"name\\": \\"8683.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8683\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3770	2024-01-27 21:35:26.033+00	8687	{"{\\"name\\": \\"8687-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8687\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8687.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8687\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3788	2024-01-27 21:35:26.033+00	8690	{"{\\"name\\": \\"8690-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8690\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8690.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8690\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3756	2024-01-27 21:35:26.032+00	8715	{"{\\"name\\": \\"8715.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8715\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3758	2024-01-27 21:35:26.032+00	8717	{"{\\"name\\": \\"8717.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8717\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3772	2024-01-27 21:35:26.033+00	8720	{"{\\"name\\": \\"8720.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8720\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3784	2024-01-27 21:35:26.033+00	8721	{"{\\"name\\": \\"8721.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8721\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3762	2024-01-27 21:35:26.032+00	8737	{"{\\"name\\": \\"8737.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8737\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3761	2024-01-27 21:35:26.032+00	8736	{"{\\"name\\": \\"8736.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8736\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3765	2024-01-27 21:35:26.032+00	8738	{"{\\"name\\": \\"8738.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8738\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3763	2024-01-27 21:35:26.032+00	8742	{"{\\"name\\": \\"8742.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8742\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3766	2024-01-27 21:35:26.032+00	8739	{"{\\"name\\": \\"8739.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8739\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3775	2024-01-27 21:35:26.033+00	8743	{"{\\"name\\": \\"8743.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8743\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3764	2024-01-27 21:35:26.032+00	8741	{"{\\"name\\": \\"8741.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8741\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3773	2024-01-27 21:35:26.033+00	8744	{"{\\"name\\": \\"8744.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8744\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3774	2024-01-27 21:35:26.033+00	8745	{"{\\"name\\": \\"8745.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8745\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3778	2024-01-27 21:35:26.033+00	8746	{"{\\"name\\": \\"8746.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8746\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3777	2024-01-27 21:35:26.033+00	8747	{"{\\"name\\": \\"8747.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8747\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3785	2024-01-27 21:35:26.033+00	8751	{"{\\"name\\": \\"8751.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8751\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3780	2024-01-27 21:35:26.033+00	8749	{"{\\"name\\": \\"8749.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8749\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3779	2024-01-27 21:35:26.033+00	8748	{"{\\"name\\": \\"8748.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8748\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3790	2024-01-27 21:35:26.033+00	8752	{"{\\"name\\": \\"8752.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8752\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3786	2024-01-27 21:35:26.033+00	8750	{"{\\"name\\": \\"8750.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8750\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3795	2024-01-27 21:35:26.034+00	48050	{"{\\"name\\": \\"48050.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48050\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48050_G07.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48050\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}"}
3811	2024-01-27 21:35:26.034+00	48051	{"{\\"name\\": \\"48051-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48051\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48051.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48051\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3814	2024-01-27 21:35:26.034+00	48067	{"{\\"name\\": \\"48067.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48067\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"48067T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"48067\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3808	2024-01-27 21:35:26.034+00	48066	{"{\\"name\\": \\"48066.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48066\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3805	2024-01-27 21:35:26.034+00	72010	{"{\\"name\\": \\"72010.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"72010\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3792	2024-01-27 21:35:26.033+00	72009	{"{\\"name\\": \\"72009.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"72009\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3793	2024-01-27 21:35:26.033+00	8668	{"{\\"name\\": \\"8668.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8668\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3798	2024-01-27 21:35:26.034+00	49053	{"{\\"name\\": \\"49053.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49053\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3801	2024-01-27 21:35:26.034+00	8672	{"{\\"name\\": \\"8672.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8672\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3807	2024-01-27 21:35:26.034+00	8673	{"{\\"name\\": \\"8673.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8673\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3816	2024-01-27 21:35:26.035+00	8692	{"{\\"name\\": \\"8692.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8692\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3817	2024-01-27 21:35:26.035+00	8694	{"{\\"name\\": \\"8694-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8694\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8694.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8694\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3818	2024-01-27 21:35:26.035+00	8695	{"{\\"name\\": \\"8695-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8695\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8695.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8695\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3796	2024-01-27 21:35:26.034+00	8727	{"{\\"name\\": \\"8727.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8727\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3813	2024-01-27 21:35:26.034+00	8735	{"{\\"name\\": \\"8735.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8735\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3794	2024-01-27 21:35:26.033+00	8759	{"{\\"name\\": \\"8759.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8759\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3791	2024-01-27 21:35:26.033+00	8754	{"{\\"name\\": \\"8754.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8754\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3820	2024-01-27 21:35:26.035+00	97001	{"{\\"name\\": \\"97001T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"97001\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3799	2024-01-27 21:35:26.034+00	12011	{"{\\"name\\": \\"AP12011.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12011\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3797	2024-01-27 21:35:26.034+00	12020	{"{\\"name\\": \\"AP12020-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12020\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP12020.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12020\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3806	2024-01-27 21:35:26.034+00	24009	{"{\\"name\\": \\"AP24009.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24009\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3803	2024-01-27 21:35:26.034+00	12001	{"{\\"name\\": \\"AP12001-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12001\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP12001-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12001\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP12001.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12001\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3804	2024-01-27 21:35:26.034+00	25001	{"{\\"name\\": \\"AP25001.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25001\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3800	2024-01-27 21:35:26.034+00	24008	{"{\\"name\\": \\"AP24008.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24008\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3809	2024-01-27 21:35:26.034+00	48007	{"{\\"name\\": \\"AP48007.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48007\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3802	2024-01-27 21:35:26.034+00	24010	{"{\\"name\\": \\"AP24010.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24010\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3810	2024-01-27 21:35:26.034+00	49009	{"{\\"name\\": \\"AP49009.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"49009\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3812	2024-01-27 21:35:26.034+00	48006	{"{\\"name\\": \\"AP48006-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48006\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP48006-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48006\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP48006-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48006\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"AP48006.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48006\\", \\"prefix\\": \\"AP\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2915	2024-01-27 21:35:25.979+00	1016	{"{\\"name\\": \\"1016.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1016\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2912	2024-01-27 21:35:25.978+00	1006	{"{\\"name\\": \\"1006-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1006\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1006.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1006\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3191	2024-01-27 21:35:25.997+00	1128	{"{\\"name\\": \\"1128_K22.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1128\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K22\\"}","{\\"name\\": \\"1128_K23.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1128\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K23\\"}"}
3041	2024-01-27 21:35:25.987+00	1148	{"{\\"name\\": \\"1148_K62.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1148\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K62\\"}"}
2954	2024-01-27 21:35:25.982+00	1170	{"{\\"name\\": \\"1170.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1170\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
2953	2024-01-27 21:35:25.982+00	1149	{"{\\"name\\": \\"1149_K12.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1149\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K12\\"}","{\\"name\\": \\"1149_K23.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1149\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K23\\"}","{\\"name\\": \\"1149_K62.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1149\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K62\\"}"}
2982	2024-01-27 21:35:25.984+00	1135	{"{\\"name\\": \\"1135.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1135\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1135_G30.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1135\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G30\\"}"}
2973	2024-01-27 21:35:25.983+00	1205	{"{\\"name\\": \\"1205-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1205\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1205.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1205\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1205_K14.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1205\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K14\\"}"}
3028	2024-01-27 21:35:25.986+00	12471	{"{\\"name\\": \\"12471-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12471\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12471-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12471\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12471.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12471\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12471_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12471\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"12471_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12471\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3069	2024-01-27 21:35:25.988+00	1253	{"{\\"name\\": \\"1253_K41.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1253\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K41\\"}"}
3148	2024-01-27 21:35:25.994+00	12554	{"{\\"name\\": \\"12554_G158.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12554\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G158\\"}"}
3077	2024-01-27 21:35:25.988+00	12545	{"{\\"name\\": \\"12545-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12545\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12545.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12545\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3057	2024-01-27 21:35:25.987+00	12667	{"{\\"name\\": \\"12667-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12667\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12667-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12667\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12667-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12667\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"12667.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12667\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3126	2024-01-27 21:35:25.993+00	12698	{"{\\"name\\": \\"12698.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12698\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3212	2024-01-27 21:35:25.998+00	12816	{"{\\"name\\": \\"12816.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"12816\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3145	2024-01-27 21:35:25.994+00	1321	{"{\\"name\\": \\"1321T_G07.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1321\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G07\\"}","{\\"name\\": \\"1321T_G16.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1321\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G16\\"}","{\\"name\\": \\"1321T_G23.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1321\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G23\\"}","{\\"name\\": \\"1321T_G47.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1321\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G47\\"}","{\\"name\\": \\"1321T_Kartela.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1321\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3199	2024-01-27 21:35:25.997+00	1360	{"{\\"name\\": \\"1360-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1360\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1360.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1360\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1360_G30.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1360\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G30\\"}","{\\"name\\": \\"1360_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1360\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3230	2024-01-27 21:35:26+00	1383	{"{\\"name\\": \\"1383.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1383\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3222	2024-01-27 21:35:25.999+00	1377	{"{\\"name\\": \\"1377-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1377\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1377-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1377\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1377-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1377\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1377.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1377\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3251	2024-01-27 21:35:26.001+00	1409	{"{\\"name\\": \\"1409.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1409\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1409T-2.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1409\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1409T-3.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1409\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1409T.webp\\", \\"annex\\": \\"T\\", \\"design\\": \\"1409\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3340	2024-01-27 21:35:26.01+00	1448	{"{\\"name\\": \\"1448-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1448\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"1448.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1448\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3285	2024-01-27 21:35:26.004+00	1487	{"{\\"name\\": \\"1487.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"1487\\", \\"prefix\\": \\"N\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3400	2024-01-27 21:35:26.013+00	24445	{"{\\"name\\": \\"24445-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24445\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24445.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24445\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3446	2024-01-27 21:35:26.015+00	24347	{"{\\"name\\": \\"24347_K194.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K194\\"}","{\\"name\\": \\"24347_K195.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K195\\"}","{\\"name\\": \\"24347_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24347_Kartela-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24347_Kartela-4.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"4\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24347_Kartela-5.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"5\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"24347_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24347\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}"}
3393	2024-01-27 21:35:26.013+00	24402	{"{\\"name\\": \\"24402i_G112-2.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24402\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G112\\"}","{\\"name\\": \\"24402i_G112.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24402\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G112\\"}","{\\"name\\": \\"24402i_G12.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24402\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G12\\"}","{\\"name\\": \\"24402i_G50-2.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24402\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G50\\"}","{\\"name\\": \\"24402i_G50.webp\\", \\"annex\\": \\"i\\", \\"design\\": \\"24402\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G50\\"}"}
3461	2024-01-27 21:35:26.016+00	24573	{"{\\"name\\": \\"24573.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24573\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3469	2024-01-27 21:35:26.016+00	24566	{"{\\"name\\": \\"24566-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24566\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24566.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24566\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3519	2024-01-27 21:35:26.018+00	24603	{"{\\"name\\": \\"24603.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24603\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3490	2024-01-27 21:35:26.017+00	24606	{"{\\"name\\": \\"24606.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24606\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3555	2024-01-27 21:35:26.02+00	24627	{"{\\"name\\": \\"24627-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24627\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"24627.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24627\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3631	2024-01-27 21:35:26.023+00	24747	{"{\\"name\\": \\"24747.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24747\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3594	2024-01-27 21:35:26.021+00	24757	{"{\\"name\\": \\"24757.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24757\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3815	2024-01-27 21:35:26.034+00	24819	{"{\\"name\\": \\"24819.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"24819\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3650	2024-01-27 21:35:26.027+00	25214	{"{\\"name\\": \\"25214_K104-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25214\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"K104\\"}","{\\"name\\": \\"25214_K104.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25214\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"K104\\"}"}
3670	2024-01-27 21:35:26.028+00	25220	{"{\\"name\\": \\"25220.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25220\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3693	2024-01-27 21:35:26.029+00	25222	{"{\\"name\\": \\"25222-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25222\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25222-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25222\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"25222.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25222\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3744	2024-01-27 21:35:26.032+00	25253	{"{\\"name\\": \\"25253_G88.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25253\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G88\\"}"}
3736	2024-01-27 21:35:26.031+00	25250	{"{\\"name\\": \\"25250_G88-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25250\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"G88\\"}","{\\"name\\": \\"25250_G88.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25250\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"G88\\"}"}
3821	2024-01-27 21:35:26.026+00	25280	{"{\\"name\\": \\"25280.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"25280\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3760	2024-01-27 21:35:26.032+00	48037	{"{\\"name\\": \\"48037.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"48037\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
3819	2024-01-27 21:35:26.035+00	8015	{"{\\"name\\": \\"8015_Kartela-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8015\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"8015_Kartela-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8015\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"8015_Kartela.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8015\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"Kartela\\"}","{\\"name\\": \\"8015_T16.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8015\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"T16\\"}"}
3822	2024-01-27 21:35:26.035+00	8693	{"{\\"name\\": \\"8693-2.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8693\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"2\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8693-3.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8693\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"3\\", \\"variant\\": \\"\\"}","{\\"name\\": \\"8693.webp\\", \\"annex\\": \\"\\", \\"design\\": \\"8693\\", \\"prefix\\": \\"K\\", \\"imageNo\\": \\"1\\", \\"variant\\": \\"\\"}"}
\.


--
-- Data for Name: todo_task; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.todo_task (id, task_name, due_date, description, completed, created_at, completed_at, company_id, contact_id) FROM stdin;
87	Fuar numarani ogren	2024-04-23		t	2024-04-22 14:02:35.983307+00	2024-04-25 15:35:37.00331+00	\N	\N
111	Follow up #1	2024-04-30		t	2024-04-25 20:40:17.299568+00	2024-05-06 20:09:01.513445+00	60	\N
61	Adem amca icin renkleri sor	2024-04-19		t	2024-04-18 14:34:56.52223+00	2024-04-19 08:39:06.326594+00	\N	\N
62	Mehmet gultekin ara	2024-04-19	Pazartesi veya sali gunu musaitmis	t	2024-04-18 14:36:16.248862+00	2024-04-21 07:55:25.983199+00	\N	\N
65	Kartuş al tuğçe	2024-04-21		t	2024-04-21 07:55:15.091488+00	2024-04-21 18:02:55.834957+00	\N	\N
60	48060 FIYAT YAPIN DIYOR	2024-04-19	ZUBEYDE 3.5 DOLAR FIYAT ISTIYOR\r\nMAGAZA 4 DEN ALIYORMUŞ	t	2024-04-18 11:44:14.117028+00	2024-04-21 20:31:56.780508+00	\N	\N
90	Follow up #1	2024-04-25		t	2024-04-23 13:14:05.708142+00	2024-04-25 18:46:29.428153+00	43	\N
59	Follow up #1	2024-04-20		t	2024-04-18 11:07:50.845808+00	2024-04-22 05:22:16.754391+00	6	\N
63	Follow up #1	2024-04-20	description	t	2024-04-19 04:30:42.853755+00	2024-04-22 05:24:27.043397+00	27	\N
58	Meeting with Poland Heimtextil	2024-04-22		t	2024-04-18 08:41:39.472487+00	2024-04-22 09:34:05.886392+00	\N	\N
88	kosovali perdeci ara	2024-04-23		t	2024-04-22 14:12:29.228131+00	2024-04-23 11:00:34.186335+00	\N	\N
91	Follow up #1	2024-04-25		t	2024-04-23 13:39:35.97543+00	2024-04-25 18:47:09.500295+00	44	\N
72	Follow up #2	2024-04-26		t	2024-04-22 05:37:44.35915+00	2024-04-26 08:00:30.10915+00	31	\N
82	Follow up #2	2024-04-26		t	2024-04-22 06:02:37.955147+00	2024-04-26 08:29:16.683539+00	41	\N
97	Follow up #1	2024-04-30		t	2024-04-25 19:04:57.193999+00	2024-05-06 20:01:37.946658+00	46	\N
81	Follow up #2	2024-04-26		t	2024-04-22 05:59:22.253412+00	2024-04-26 08:31:43.160464+00	40	\N
76	Follow up #2	2024-04-26		t	2024-04-22 05:51:22.301902+00	2024-04-26 08:32:28.453639+00	35	\N
77	Follow up #2	2024-04-26		t	2024-04-22 05:53:46.067065+00	2024-04-26 08:35:04.54658+00	36	\N
75	Follow up #2	2024-04-26		t	2024-04-22 05:49:02.057983+00	2024-04-26 08:35:35.945676+00	34	\N
67	Follow up #2	2024-04-26		t	2024-04-22 05:22:35.870154+00	2024-04-26 08:36:05.175513+00	6	\N
68	Follow up #2	2024-04-26		t	2024-04-22 05:24:21.775957+00	2024-04-26 08:41:02.339938+00	27	\N
69	Follow up #2	2024-04-26		t	2024-04-22 05:30:10.51811+00	2024-04-26 08:41:53.674701+00	28	\N
74	Follow up #2	2024-04-26		t	2024-04-22 05:44:33.923557+00	2024-04-26 08:43:22.664424+00	33	\N
73	Follow up #2	2024-04-26		t	2024-04-22 05:38:59.563617+00	2024-04-26 08:47:22.306175+00	32	\N
78	Follow up #2	2024-04-26		t	2024-04-22 05:55:11.581038+00	2024-04-26 08:48:06.604525+00	37	\N
70	Follow up #2	2024-04-26		t	2024-04-22 05:32:28.455315+00	2024-04-26 08:50:37.37638+00	29	\N
71	Follow up #2	2024-04-26		t	2024-04-22 05:36:04.754021+00	2024-04-26 08:51:16.38511+00	30	\N
79	Follow up #2	2024-04-26		t	2024-04-22 05:56:25.256755+00	2024-04-26 08:54:55.858071+00	38	\N
80	Follow up #2	2024-04-26		t	2024-04-22 05:57:50.640046+00	2024-04-26 08:55:39.179535+00	39	\N
128	Çinli desenci ve Taşçı bul	2024-04-26		t	2024-04-26 09:47:31.144033+00	2024-04-26 14:04:19.785728+00	\N	\N
124	Follow up #3	2024-05-06		t	2024-04-26 08:50:33.544549+00	2024-05-06 20:38:10.820244+00	29	\N
96	Follow up #1	2024-04-30		t	2024-04-25 18:59:09.274865+00	2024-05-01 14:14:14.502136+00	45	\N
139	close chase savings account	2024-05-02		t	2024-05-01 16:13:55.662905+00	2024-05-02 18:47:07.418034+00	\N	\N
142	Adem amca icin cinliler ile gorus	2024-05-03		t	2024-05-03 16:40:22.639026+00	2024-05-05 12:39:37.606755+00	\N	\N
136	Dogalgaz fatura ode	2024-04-29		t	2024-04-28 09:57:03.02078+00	2024-05-06 19:54:40.232399+00	\N	\N
92	UPS FATURA	2024-04-29		t	2024-04-25 17:21:41.491511+00	2024-05-06 19:54:54.415697+00	\N	\N
98	Follow up #1	2024-04-30		t	2024-04-25 19:07:44.083418+00	2024-05-06 20:05:53.419437+00	47	\N
104	Follow up #1	2024-04-30		t	2024-04-25 19:53:42.342739+00	2024-05-06 20:06:27.220611+00	53	\N
102	Follow up #1	2024-04-30		t	2024-04-25 19:37:13.904934+00	2024-05-06 20:07:08.43154+00	51	\N
89	Follow up #2	2024-04-30		t	2024-04-22 14:52:11.120511+00	2024-05-06 20:08:12.520102+00	42	\N
110	Follow up #1	2024-04-30		t	2024-04-25 20:35:57.57006+00	2024-05-06 20:10:11.983729+00	59	\N
109	Follow up #1	2024-04-30		t	2024-04-25 20:31:05.691485+00	2024-05-06 20:11:11.964634+00	58	\N
108	Follow up #1	2024-04-30		t	2024-04-25 20:27:39.303496+00	2024-05-06 20:11:41.316847+00	57	\N
107	Follow up #1	2024-04-30		t	2024-04-25 20:24:32.682316+00	2024-05-06 20:12:31.826622+00	56	\N
106	Follow up #1	2024-04-30		t	2024-04-25 20:00:52.592925+00	2024-05-06 20:13:18.657477+00	55	\N
145	Follow up #3	2024-05-10		t	2024-05-06 20:04:17.04823+00	2024-05-11 20:08:05.956519+00	44	\N
103	Follow up #1	2024-04-30		t	2024-04-25 19:42:06.284848+00	2024-05-06 20:17:04.47684+00	52	\N
100	Follow up #1	2024-04-30		t	2024-04-25 19:21:07.468379+00	2024-05-06 20:18:10.50137+00	49	\N
94	Follow up #2	2024-04-30		t	2024-04-25 18:46:18.988466+00	2024-05-06 20:19:07.78283+00	43	\N
129	Follow up #1	2024-05-01		t	2024-04-28 07:06:59.977368+00	2024-05-06 20:19:44.973209+00	61	\N
144	Follow up #2	2024-05-09		t	2024-05-06 20:01:56.694145+00	2024-05-11 20:19:47.539135+00	46	\N
130	Follow up #1	2024-05-01		t	2024-04-28 07:23:17.759794+00	2024-05-06 20:21:18.435044+00	62	\N
132	Follow up #1	2024-05-01		t	2024-04-28 07:48:20.409371+00	2024-05-06 20:22:17.884638+00	64	\N
133	Follow up #1	2024-05-01		t	2024-04-28 08:26:00.41524+00	2024-05-06 20:22:44.07569+00	65	\N
134	Follow up #1	2024-05-01		t	2024-04-28 08:30:53.638286+00	2024-05-06 20:23:13.922754+00	66	\N
135	Follow up #1	2024-05-01		t	2024-04-28 09:02:39.520291+00	2024-05-06 20:23:55.447684+00	67	\N
141	Dilan nakis kart cikart	2024-05-03		t	2024-05-03 09:29:58.491418+00	2024-05-06 20:24:16.906141+00	\N	\N
140	Reach out to them	2024-05-03		t	2024-05-03 07:43:55.242735+00	2024-05-06 20:26:04.939661+00	68	\N
99	Follow up #1	2024-04-30		t	2024-04-25 19:15:57.230224+00	2024-05-06 20:27:13.4114+00	48	\N
112	Follow up #3	2024-05-03		t	2024-04-26 08:00:53.780012+00	2024-05-06 20:34:59.226776+00	31	\N
138	Follow up #2	2024-05-03		t	2024-05-01 14:14:26.021633+00	2024-05-06 20:35:50.588248+00	45	\N
93	Reach out baran company again Contex	2024-05-06		t	2024-04-25 18:44:03.206795+00	2024-05-06 20:36:02.838119+00	\N	\N
122	Follow up #3	2024-05-06		t	2024-04-26 08:47:31.487775+00	2024-05-06 20:38:58.600162+00	32	\N
123	Follow up #3	2024-05-06		t	2024-04-26 08:48:01.964719+00	2024-05-06 20:39:51.571859+00	37	\N
113	Follow up #3	2024-05-06		t	2024-04-26 08:29:28.531352+00	2024-05-06 20:40:22.032467+00	41	\N
114	Follow up #3	2024-05-06		t	2024-04-26 08:31:52.485359+00	2024-05-06 20:41:18.442843+00	40	\N
117	Follow up #3	2024-05-06		t	2024-04-26 08:35:31.752494+00	2024-05-06 20:49:56.511893+00	34	\N
115	Follow up #3	2024-05-06		t	2024-04-26 08:32:36.488915+00	2024-05-06 20:50:47.202005+00	35	\N
116	Follow up #3	2024-05-06		t	2024-04-26 08:35:00.509097+00	2024-05-06 20:51:33.16264+00	36	\N
118	Follow up #3	2024-05-06		t	2024-04-26 08:36:00.900923+00	2024-05-06 20:52:02.074232+00	6	\N
119	Follow up #3	2024-05-06		t	2024-04-26 08:40:58.208419+00	2024-05-06 20:52:41.329788+00	27	\N
120	Follow up #3	2024-05-06		t	2024-04-26 08:41:49.907841+00	2024-05-06 20:53:30.712351+00	28	\N
121	Follow up #3	2024-05-06		t	2024-04-26 08:43:18.758388+00	2024-05-06 20:54:20.666389+00	33	\N
125	Follow up #3	2024-05-06		t	2024-04-26 08:51:12.558339+00	2024-05-06 20:55:08.336098+00	30	\N
127	Follow up #3	2024-05-06		t	2024-04-26 08:55:34.882925+00	2024-05-06 20:56:44.124011+00	39	\N
83	Polonya fuarı ile ilgili babayla görüş	2024-04-23		t	2024-04-22 09:34:01.756973+00	2024-05-08 12:21:06.693814+00	\N	\N
105	Follow up #1	2024-05-09		t	2024-04-25 19:56:18.284232+00	2024-05-11 20:03:08.515491+00	54	\N
101	Follow up #2	2024-05-10		t	2024-04-25 19:26:26.486249+00	2024-05-11 20:18:00.441387+00	50	\N
95	Follow up #2	2024-04-30		t	2024-04-25 18:47:05.132519+00	2024-05-06 20:04:26.479468+00	44	\N
131	Follow up #1	2024-05-01		t	2024-04-28 07:30:49.375101+00	2024-05-06 20:21:51.145426+00	63	\N
126	Follow up #3	2024-05-06		t	2024-04-26 08:54:51.27654+00	2024-05-06 20:56:17.38634+00	38	\N
162	Follow up #2	2024-05-09		t	2024-05-06 20:22:25.991428+00	2024-05-11 20:28:26.682469+00	64	\N
157	Follow up #2	2024-05-09		t	2024-05-06 20:18:21.623368+00	2024-05-11 19:58:05.459837+00	49	\N
159	Follow up #2	2024-05-09		t	2024-05-06 20:19:54.385642+00	2024-05-11 20:03:57.249703+00	61	\N
150	Follow up #2	2024-05-09		t	2024-05-06 20:08:56.957293+00	2024-05-11 20:04:45.689474+00	60	\N
160	Follow up #2	2024-05-09		t	2024-05-06 20:21:25.676767+00	2024-05-11 20:05:17.053142+00	62	\N
158	Follow up #3	2024-05-10		t	2024-05-06 20:19:17.031132+00	2024-05-11 20:05:59.874685+00	43	\N
149	Follow up #3	2024-05-10		t	2024-05-06 20:08:24.112654+00	2024-05-11 20:08:54.926366+00	42	\N
185	Follow up #1	2024-05-10		t	2024-05-08 11:04:24.287478+00	2024-05-11 20:16:07.042696+00	69	\N
168	Follow up #3	2024-05-10		t	2024-05-06 20:35:45.741677+00	2024-05-11 20:16:49.952886+00	45	\N
148	Follow up #2	2024-05-09		t	2024-05-06 20:07:16.685075+00	2024-05-11 20:19:04.203103+00	51	\N
166	Follow up #2	2024-05-09		t	2024-05-06 20:27:07.688942+00	2024-05-11 20:20:23.38996+00	48	\N
152	Follow up #2	2024-05-09		t	2024-05-06 20:11:06.087637+00	2024-05-11 20:21:09.107035+00	58	\N
165	Follow up #2	2024-05-09		t	2024-05-06 20:23:51.26943+00	2024-05-11 20:21:30.752144+00	67	\N
164	Follow up #2	2024-05-09		t	2024-05-06 20:23:21.597269+00	2024-05-11 20:21:59.687049+00	66	\N
147	Follow up #2	2024-05-09		t	2024-05-06 20:06:21.998926+00	2024-05-11 20:22:28.036651+00	53	\N
151	Follow up #2	2024-05-09		t	2024-05-06 20:10:07.854156+00	2024-05-11 20:23:11.866775+00	59	\N
153	Follow up #2	2024-05-09		t	2024-05-06 20:11:50.376992+00	2024-05-11 20:29:27.229627+00	57	\N
154	Follow up #2	2024-05-09		t	2024-05-06 20:12:26.777292+00	2024-05-11 20:30:01.118291+00	56	\N
155	Follow up #2	2024-05-09		t	2024-05-06 20:13:13.757699+00	2024-05-11 20:43:49.039997+00	55	\N
156	Follow up #2	2024-05-09		t	2024-05-06 20:16:57.541782+00	2024-05-11 20:46:39.323639+00	52	\N
161	Follow up #2	2024-05-09		t	2024-05-06 20:21:57.636732+00	2024-05-11 20:47:41.206664+00	63	\N
163	Follow up #2	2024-05-09		t	2024-05-06 20:22:51.326725+00	2024-05-11 20:48:33.24223+00	65	\N
177	Follow up #4	2024-05-13		t	2024-05-06 20:52:12.550281+00	2024-05-16 14:04:28.052289+00	6	\N
181	Follow up #4	2024-05-13		t	2024-05-06 20:55:20.688018+00	2024-05-16 14:09:45.44581+00	30	\N
179	Follow up #4	2024-05-13		t	2024-05-06 20:53:41.148065+00	2024-05-16 14:11:07.009739+00	28	\N
186	Follow up #5	2024-06-17		t	2024-05-11 20:02:27.463021+00	2024-06-20 11:47:06.942745+00	49	\N
178	Follow up #4	2024-05-13		t	2024-05-06 20:52:49.968544+00	2024-05-16 14:14:40.622456+00	27	\N
176	Follow up #4	2024-05-13		t	2024-05-06 20:51:42.758666+00	2024-05-16 14:16:16.872069+00	36	\N
194	Follow up #2	2024-05-15		t	2024-05-11 20:16:19.027297+00	2024-05-16 14:21:51.016419+00	69	\N
180	Follow up #4	2024-05-13		t	2024-05-06 20:54:33.633012+00	2024-05-16 14:23:22.407791+00	33	\N
174	Follow up #4	2024-05-13		t	2024-05-06 20:50:06.711801+00	2024-05-16 14:23:50.346223+00	34	\N
169	Follow up #4	2024-05-13		t	2024-05-06 20:38:23.31435+00	2024-05-16 14:26:10.196255+00	29	\N
170	Follow up #4	2024-05-13		t	2024-05-06 20:39:09.039752+00	2024-05-16 14:26:34.771724+00	32	\N
167	Follow up #4	2024-05-13		t	2024-05-06 20:35:08.760138+00	2024-05-16 14:27:28.430018+00	31	\N
182	Follow up #4	2024-05-13		t	2024-05-06 20:55:59.810163+00	2024-05-16 14:28:25.058292+00	38	\N
171	Follow up #4	2024-05-13		t	2024-05-06 20:39:47.303379+00	2024-05-16 14:29:13.596391+00	37	\N
173	Follow up #4	2024-05-13		t	2024-05-06 20:41:27.587017+00	2024-05-16 14:29:58.44889+00	40	\N
175	Follow up #4	2024-05-13		t	2024-05-06 20:50:42.495195+00	2024-05-16 14:30:49.239005+00	35	\N
187	Follow up #2	2024-05-15		t	2024-05-11 20:03:17.879286+00	2024-05-16 14:31:30.669345+00	54	\N
188	Follow up #3	2024-05-17		t	2024-05-11 20:04:07.028988+00	2024-05-26 21:42:12.94193+00	61	\N
189	Follow up #3	2024-05-17		t	2024-05-11 20:04:41.258715+00	2024-05-26 21:44:07.927581+00	60	\N
196	Follow up #3	2024-05-17		t	2024-05-11 20:18:16.138072+00	2024-05-26 21:54:17.562366+00	50	\N
234	Follow up #5	2024-06-17		t	2024-05-26 21:44:14.681459+00	2024-06-20 11:54:01.961352+00	60	\N
195	Follow up #5	2024-06-10		t	2024-05-11 20:16:58.006295+00	2024-06-20 12:00:08.302947+00	45	\N
211	Follow up #4	2024-06-03		t	2024-05-11 20:48:41.6634+00	2024-06-03 07:33:09.38647+00	65	\N
231	Follow up #2	2024-05-29		t	2024-05-17 13:04:31.044031+00	2024-06-01 06:48:21.000004+00	71	\N
218	Ask them to come to your stand	2025-05-20		f	2024-05-16 14:20:37.087043+00	2024-05-16 14:20:37.087043+00	41	\N
184	Follow up #5	2024-06-10		t	2024-05-06 20:56:39.80084+00	2024-06-20 11:59:18.445256+00	39	\N
233	Follow up #5	2024-06-17		t	2024-05-26 21:42:33.601263+00	2024-06-20 11:45:31.656108+00	61	\N
221	Follow up #5	2024-05-31		t	2024-05-16 14:25:21.260835+00	2024-06-01 06:14:10.104519+00	34	\N
197	Follow up #5	2024-06-17		t	2024-05-11 20:19:17.881154+00	2024-06-20 11:50:02.281468+00	51	\N
199	Follow up #4	2024-06-03		t	2024-05-11 20:20:34.628093+00	2024-06-03 07:36:41.147715+00	48	\N
202	Follow up #4	2024-06-03		t	2024-05-11 20:22:06.082284+00	2024-06-03 07:38:04.923395+00	66	\N
232	Follow up #2	2024-05-29		t	2024-05-17 13:22:30.592823+00	2024-06-01 06:47:44.809139+00	72	\N
191	Follow up #5	2024-06-10		t	2024-05-11 20:06:09.475592+00	2024-06-20 11:47:32.882125+00	43	\N
229	Follow up #5	2024-06-17		t	2024-05-16 14:31:42.599064+00	2024-06-20 11:53:20.627646+00	54	\N
204	Follow up #4	2024-06-03		t	2024-05-11 20:23:25.36224+00	2024-06-03 08:41:13.753477+00	59	\N
208	Follow up #5	2024-06-17		t	2024-05-11 20:43:58.467639+00	2024-06-20 11:52:48.246639+00	55	\N
207	Follow up #5	2024-06-17		t	2024-05-11 20:30:09.238907+00	2024-06-20 11:52:24.287595+00	56	\N
198	Follow up #5	2024-06-17		t	2024-05-11 20:19:58.423729+00	2024-06-20 11:50:32.753801+00	46	\N
209	Follow up #5	2024-06-17		t	2024-05-11 20:46:45.827996+00	2024-06-20 11:52:03.819167+00	52	\N
192	Follow up #5	2024-06-10		t	2024-05-11 20:08:16.737977+00	2024-06-20 11:58:43.385156+00	44	\N
206	Follow up #5	2024-06-17		t	2024-05-11 20:29:34.846001+00	2024-06-03 09:28:55.327024+00	57	\N
200	Follow up #5	2024-06-17		t	2024-05-11 20:21:04.392721+00	2024-06-20 11:54:25.384795+00	58	\N
217	Follow up #5	2024-05-31		t	2024-05-16 14:16:08.589428+00	2024-06-01 06:18:01.019114+00	36	\N
213	Follow up #5	2024-05-31		t	2024-05-16 14:09:38.720683+00	2024-06-01 06:19:02.6535+00	30	\N
228	Follow up #5	2024-05-31		t	2024-05-16 14:30:58.664073+00	2024-06-01 06:20:12.34807+00	35	\N
227	Follow up #5	2024-05-31		t	2024-05-16 14:30:20.726919+00	2024-06-01 06:20:46.974687+00	40	\N
220	Follow up #5	2024-05-31		t	2024-05-16 14:23:05.455284+00	2024-06-01 06:21:32.208284+00	33	\N
224	Follow up #5	2024-05-31		t	2024-05-16 14:27:40.210095+00	2024-06-01 06:21:58.330114+00	31	\N
216	Follow up #5	2024-05-31		t	2024-05-16 14:14:33.715184+00	2024-06-01 06:22:42.111983+00	27	\N
225	Follow up #5	2024-05-31		t	2024-05-16 14:28:36.326622+00	2024-06-01 06:23:54.218744+00	38	\N
223	Follow up #5	2024-05-31		t	2024-05-16 14:26:44.710531+00	2024-06-01 06:24:28.119878+00	32	\N
226	Follow up #5	2024-05-31		t	2024-05-16 14:29:24.67071+00	2024-06-01 06:27:29.267806+00	37	\N
214	Follow up #5	2024-05-31		t	2024-05-16 14:11:00.405213+00	2024-06-01 06:28:07.021852+00	28	\N
212	Follow up #5	2024-05-31		t	2024-05-16 14:04:58.090632+00	2024-06-01 06:29:31.544693+00	6	\N
230	Follow up #1	2024-05-29		t	2024-05-17 09:24:29.299216+00	2024-06-01 06:46:34.650024+00	70	\N
190	Follow up #3	2024-05-17		t	2024-05-11 20:05:13.154973+00	2024-05-26 21:47:47.085135+00	62	\N
235	Follow up #5	2024-06-17		t	2024-05-26 21:49:26.413853+00	2024-06-20 11:50:54.277501+00	62	\N
240	Reach out	2024-05-27	https://maps.app.goo.gl/gQ1qhJW3FM5SzXZv8\r\nhttps://maps.app.goo.gl/tNSxPEuZmT2eBda48\r\nArti's Salon Firan\r\nDe'Cor Pracownia Firan	t	2024-05-26 23:01:39.438306+00	2024-05-27 09:46:36.399205+00	\N	\N
239	Ercan ile 1637 desenini teyit ettir	2024-05-27		t	2024-05-26 22:32:34.123499+00	2024-05-27 10:07:21.82071+00	68	\N
237	Poland two companies search and enter	2024-05-27		t	2024-05-26 22:30:58.056469+00	2024-05-27 12:18:49.146066+00	\N	\N
250	Enes ten cinli yi ara	2024-05-28		t	2024-05-27 12:19:53.457499+00	2024-06-01 06:04:31.021791+00	\N	\N
246	Aydin Ege sim ara	2024-05-28	numunelerin durumunu sor	t	2024-05-27 10:43:52.459847+00	2024-06-01 06:04:38.473677+00	\N	\N
251	Yahya yi araNuralp	2024-05-28		t	2024-05-27 21:56:19.093984+00	2024-06-01 06:04:45.733681+00	\N	\N
238	reach to expo companies hometex 2024	2024-05-27		t	2024-05-26 22:31:09.786849+00	2024-06-01 06:04:57.64297+00	\N	\N
241	Follow up #1	2024-05-29		t	2024-05-27 05:55:15.076671+00	2024-06-01 06:31:58.52665+00	73	\N
248	Follow up #1	2024-05-29		t	2024-05-27 10:55:52.934588+00	2024-06-01 06:33:11.268007+00	79	\N
236	Follow up #5	2024-06-17		t	2024-05-26 21:54:25.111264+00	2024-06-20 11:51:38.093938+00	50	\N
244	Follow up #1	2024-05-29		t	2024-05-27 09:42:23.111421+00	2024-06-01 06:42:47.508972+00	76	\N
249	Follow up #1	2024-05-29		t	2024-05-27 11:07:29.468837+00	2024-06-01 06:43:28.176993+00	80	\N
247	Follow up #1	2024-05-29		t	2024-05-27 10:52:41.904877+00	2024-06-01 06:45:26.902682+00	78	\N
253	Follow up #2	2024-06-03		t	2024-06-01 06:33:20.281116+00	2024-06-03 07:37:31.92335+00	79	\N
263	Follow up #5	2024-06-17		t	2024-06-03 07:38:11.278424+00	2024-06-20 11:53:41.289757+00	66	\N
297	Cipi stock ucuzları soruyor diyor o neydi	2024-07-15		t	2024-07-13 11:08:52.952516+00	2024-07-16 13:32:44.662015+00	\N	\N
255	Follow up #2	2024-06-04		t	2024-06-01 06:43:37.260225+00	2024-06-05 05:39:30.313577+00	80	\N
287	Write to them regarding invoice. Give total	2024-06-25		t	2024-06-24 17:28:04.106188+00	2024-06-28 07:26:46.172518+00	68	\N
256	Follow up #2	2024-06-04		t	2024-06-01 06:45:22.426938+00	2024-06-05 06:58:47.233475+00	78	\N
267	Follow up #3	2024-06-10		t	2024-06-05 05:39:44.732778+00	2024-06-20 11:55:55.764875+00	80	\N
274	write to them inform them about production	2024-06-10		t	2024-06-08 15:34:28.293568+00	2024-06-13 16:54:35.26897+00	68	\N
242	Follow up #3	2024-06-06		t	2024-05-27 09:32:23.708983+00	2024-06-13 17:39:14.301453+00	74	\N
252	Follow up #3	2024-06-10		t	2024-06-01 06:32:16.83794+00	2024-06-20 11:56:31.263735+00	73	\N
273	Contact them again	2024-06-20		t	2024-06-05 20:09:59.179265+00	2024-06-20 11:42:57.420769+00	91	\N
260	Follow up #5	2024-06-17		t	2024-06-03 07:36:10.232995+00	2024-06-20 11:48:14.152221+00	65	\N
261	Follow up #5	2024-06-17		t	2024-06-03 07:36:50.279179+00	2024-06-20 11:49:35.452217+00	48	\N
268	Follow up #3	2024-06-10		t	2024-06-05 06:59:32.814977+00	2024-06-20 11:57:06.117355+00	78	\N
262	Follow up #3	2024-06-07		t	2024-06-03 07:37:41.097348+00	2024-06-20 12:00:37.24469+00	79	\N
266	Follow up #1	2024-06-07		t	2024-06-05 05:38:35.23527+00	2024-06-20 12:01:24.683498+00	86	\N
286	Contact them	2024-06-25		t	2024-06-22 13:36:56.949255+00	2024-06-28 22:33:09.735047+00	74	\N
289	Contact him	2024-07-03		t	2024-06-28 22:33:03.056527+00	2024-07-03 10:02:50.085122+00	74	\N
307	Send him an email	2024-07-29		t	2024-07-28 21:45:24.961232+00	2024-07-29 10:45:59.048306+00	74	\N
265	Brode desen katalogu yap gonder yeni email adrese	2024-06-04		t	2024-06-03 19:36:44.561878+00	2024-06-20 12:20:54.067593+00	42	\N
275	contact again	2024-06-21		t	2024-06-20 11:43:11.860591+00	2024-06-22 09:29:04.796121+00	91	\N
283	Follow up #2	2024-06-21		t	2024-06-20 12:01:35.695406+00	2024-06-22 09:30:59.078261+00	86	\N
300	İş bankası ara de komisyon kim kesti	2024-07-26		t	2024-07-25 16:16:04.959614+00	2024-07-26 07:57:52.868639+00	\N	\N
299	Cipi mallari yap ve aksesuarlari al (asma lik ve jakarli olan)	2024-07-26		t	2024-07-25 16:14:20.323832+00	2024-07-27 14:13:34.901769+00	\N	\N
281	Follow up #6	2024-07-21		t	2024-06-20 12:00:03.767238+00	2024-07-28 21:32:30.183586+00	45	\N
292	call usa consulate regarding fee	2024-07-05		t	2024-07-04 21:55:39.399367+00	2024-07-05 21:19:52.545445+00	\N	\N
295	They want prices for the designs	2024-07-15		t	2024-07-13 09:52:31.744535+00	2024-07-15 14:41:34.625783+00	68	\N
279	Follow up #6	2024-07-21		t	2024-06-20 11:58:38.740503+00	2024-07-28 21:33:11.860882+00	44	\N
280	Follow up #6	2024-07-21		t	2024-06-20 11:59:13.067586+00	2024-07-28 21:33:54.056984+00	39	\N
285	Follow up #4	2024-07-11		t	2024-06-22 09:30:38.447415+00	2024-07-28 21:40:53.078958+00	86	\N
254	Follow up #3	2024-07-09		t	2024-06-01 06:42:55.660677+00	2024-07-28 21:42:24.523938+00	76	\N
271	Follow up #3	2024-07-09		t	2024-06-05 07:27:41.236035+00	2024-07-28 21:43:13.983487+00	89	\N
293	Follow up #2	2024-07-09		t	2024-07-06 09:59:36.033923+00	2024-07-28 21:44:32.256552+00	93	\N
269	Follow up #3	2024-07-09		t	2024-06-05 07:13:17.014847+00	2024-07-28 21:46:48.82217+00	87	\N
264	Follow up #2	2024-06-25		t	2024-06-03 18:38:38.99594+00	2024-07-28 21:47:40.229142+00	85	\N
301	Write to kanan	2024-07-29		t	2024-07-25 16:16:29.544542+00	2024-08-05 16:30:55.415343+00	\N	\N
310	Cipi mal istiyor brode ve dokuma	2024-08-06		t	2024-08-05 14:32:22.464408+00	2024-08-09 18:31:10.493717+00	\N	\N
311	Ozcan 1773 deseni gayrat	2024-08-06		t	2024-08-05 16:28:10.438843+00	2024-08-09 18:31:23.604711+00	\N	\N
312	deger kaybi sigorta	2024-08-06		t	2024-08-05 16:31:19.558028+00	2024-08-09 18:31:28.175252+00	\N	\N
327	Harcama itirazı	2024-09-27		t	2024-09-27 15:12:41.722958+00	2024-10-01 17:21:14.834797+00	\N	\N
326	Sor bakayım görüşmeleri nasıl geçmiş	2024-10-08		t	2024-09-26 18:39:08.138526+00	2024-10-07 08:40:06.824922+00	74	\N
317	Bütün müşterilerde bir klasör olmalı	2024-09-11		t	2024-09-11 17:22:41.47898+00	2024-09-12 06:54:20.952705+00	\N	\N
313	Adem amca K24940	2024-09-11	Serpme ve daginik halini de istiyor. \r\nPudra, beyaz ve krem	t	2024-09-10 18:22:31.63517+00	2024-09-15 05:27:57.325385+00	\N	\N
320	Send him another email	2024-09-14		t	2024-09-13 21:09:29.856878+00	2024-09-16 13:08:25.245638+00	74	\N
321	Adem amca larry ara	2024-09-20		t	2024-09-19 19:21:14.108471+00	2024-09-20 08:59:36.327634+00	\N	\N
324	hdp karven logo gonder	2024-09-23		t	2024-09-23 00:15:01.400882+00	2024-09-24 21:21:47.624642+00	\N	\N
323	Adem amca 24940 nasıl yapıcaz	2024-09-21		t	2024-09-20 19:30:09.272781+00	2024-09-26 18:27:41.783126+00	\N	\N
325	Larry yazi yaz	2024-09-25		t	2024-09-24 21:22:10.973022+00	2024-09-27 13:17:17.879843+00	\N	\N
322	Banka ödeme yaptı mı?	2024-09-23		t	2024-09-20 14:01:14.259844+00	2024-09-28 21:23:44.961285+00	\N	\N
328	Türk telekom fatura Nisan 19 öde	2024-09-27		t	2024-09-27 15:13:01.864784+00	2024-09-28 21:23:58.40709+00	\N	\N
330	Write to Kanan	2024-10-07		t	2024-10-07 08:42:34.931584+00	2024-10-08 21:56:06.590526+00	\N	\N
331	Freya kızılırmak ttm ne oldu	2024-10-10		t	2024-10-09 13:09:56.427508+00	2024-10-10 09:41:44.292329+00	\N	\N
332	larry ne kadar indirmişti	2024-10-14		t	2024-10-14 15:47:35.049054+00	2024-10-14 18:44:45.718068+00	\N	\N
333	Write to Kanan with price	2024-10-17		t	2024-10-17 18:18:21.099035+00	2024-10-18 14:20:33.586847+00	\N	\N
337	Write to David	2024-10-17		t	2024-10-17 19:01:13.405664+00	2024-10-18 18:22:20.304893+00	\N	\N
342	hgs öde	2024-10-19		t	2024-10-19 05:50:21.704423+00	2024-10-21 22:58:07.842154+00	\N	\N
343	Send ready made curtains with prices to ukranian	2024-10-19		t	2024-10-19 16:08:41.069579+00	2024-10-21 22:58:16.910725+00	\N	\N
349	adem amca leri	2024-10-24		t	2024-10-24 14:01:10.228839+00	2024-10-25 08:43:05.637949+00	\N	\N
334	hazir perde hangi koliden cikti	2024-10-17		t	2024-10-17 18:45:52.377642+00	2024-10-25 09:52:43.209373+00	\N	\N
335	do cdtfa	2024-10-17		t	2024-10-17 18:55:44.826533+00	2024-10-25 21:44:58.499762+00	\N	\N
352	Contact cipi again	2024-10-25		t	2024-10-25 14:54:12.066806+00	2024-10-28 11:15:53.496717+00	\N	\N
347	hgs pay	2024-10-23		t	2024-10-23 11:34:57.797274+00	2024-10-28 11:15:58.068195+00	\N	\N
344	desenleri website yukle	2024-10-19		t	2024-10-19 16:09:08.993574+00	2024-10-28 11:16:03.74816+00	\N	\N
351	freda yazmalisin	2024-10-25		t	2024-10-25 14:27:54.929251+00	2024-10-29 11:04:07.234035+00	\N	\N
309	Follow up #3	2024-08-02		t	2024-07-28 21:47:52.592484+00	2024-10-29 13:54:40.062875+00	85	\N
306	Follow up #3	2024-08-02		t	2024-07-28 21:44:54.649697+00	2024-10-29 13:55:07.588052+00	93	\N
257	Follow up #5	2024-08-05		t	2024-06-01 06:47:55.152752+00	2024-10-29 13:55:41.138771+00	72	\N
305	Follow up #4	2024-08-05		t	2024-07-28 21:43:28.631584+00	2024-10-29 13:56:20.652619+00	89	\N
304	Follow up #4	2024-08-05		t	2024-07-28 21:42:37.842853+00	2024-10-29 13:56:49.947107+00	76	\N
308	Follow up #4	2024-08-05		t	2024-07-28 21:47:00.499859+00	2024-10-29 13:57:23.837582+00	87	\N
303	Follow up #5	2024-08-12		t	2024-07-28 21:41:21.1681+00	2024-10-29 13:57:56.413208+00	86	\N
339	çöp fişi al	2024-10-18		t	2024-10-18 14:58:51.285724+00	2024-11-02 09:30:15.778196+00	\N	\N
354	İşin olsun tekrar	2024-10-26		t	2024-10-25 21:58:08.42327+00	2024-11-02 10:05:08.996963+00	\N	\N
341	Zeliha desenleri guzel	2024-10-18		t	2024-10-18 18:30:04.026991+00	2024-11-12 09:34:24.615376+00	\N	\N
353	eleman aramiyor	2024-10-25		t	2024-10-25 18:09:43.756746+00	2024-10-28 11:15:49.069375+00	\N	\N
355	Write to kanan	2024-10-28		t	2024-10-28 13:37:27.385081+00	2024-10-28 17:15:39.335998+00	\N	\N
359	Sinan usta 60 euro7	2024-10-29		t	2024-10-29 08:15:57.211549+00	2024-11-01 19:44:50.193504+00	\N	\N
363	Irvine renew license	2025-01-01		f	2024-10-30 07:18:42.907876+00	2024-10-30 07:18:42.907892+00	\N	\N
361	Firewall	2024-10-29		t	2024-10-29 10:05:34.828623+00	2024-11-02 09:40:29.356129+00	\N	\N
360	Polder invoice	2024-10-29		t	2024-10-29 08:17:02.594569+00	2024-11-04 06:35:43.815112+00	\N	\N
365	Upload designs to website	2024-11-01		t	2024-11-01 19:54:32.766231+00	2024-11-04 12:23:17.818537+00	\N	\N
357	1129 deseni website karismis	2024-10-28		t	2024-10-28 17:52:55.571117+00	2024-11-04 14:32:49.203294+00	\N	\N
370	Call leri	2024-11-07		t	2024-11-07 11:37:54.432256+00	2024-11-08 06:58:27.768657+00	\N	\N
369	michal comm invoice, packing list, total kg and volume to, which kargo, invoice address	2024-11-06		t	2024-11-06 11:29:47.354327+00	2024-11-14 13:19:33.897539+00	\N	\N
367	8750 deseni yanlış	2024-11-04		t	2024-11-04 15:11:19.387506+00	2024-11-15 12:56:55.617654+00	\N	\N
372	michal invoice translate	2024-11-15		t	2024-11-15 12:56:46.503679+00	2024-11-21 22:49:29.327869+00	\N	\N
376	merdiven gotur	2024-11-25		t	2024-11-24 09:07:30.428682+00	2024-11-25 09:51:22.614306+00	\N	\N
377	Adem amca kz, barkod, çin	2024-11-25		t	2024-11-24 09:08:28.769587+00	2024-11-25 09:55:00.247906+00	\N	\N
378	Irvine license stop	2024-11-25		t	2024-11-24 09:08:49.575706+00	2024-11-25 11:11:59.75327+00	\N	\N
383	Isin olsun 40 yasindakiler	2024-11-25		t	2024-11-24 09:10:13.827787+00	2024-11-25 13:30:11.247066+00	\N	\N
374	Write to kanan	2024-11-25		t	2024-11-23 11:39:19.145797+00	2024-11-25 17:29:54.182618+00	\N	\N
371	Avrupa desenleri ayarla	2024-11-25		t	2024-11-14 14:32:41.261636+00	2024-11-25 17:29:59.281622+00	\N	\N
381	hometex.org ekle kendini	2024-11-25		t	2024-11-24 09:09:49.710063+00	2024-11-25 18:30:05.655695+00	\N	\N
379	Jose EDD	2024-11-26	final returns (still having sales)\r\nchase business account close	t	2024-11-24 09:09:18.595444+00	2024-11-26 13:54:42.646689+00	\N	\N
384	chase business transfer	2024-11-26	and credit card use	f	2024-11-24 09:11:01.734274+00	2024-11-24 09:11:01.734274+00	\N	\N
385	use your credit card	2024-11-28		f	2024-11-28 17:42:25.268805+00	2024-11-28 17:42:25.268805+00	\N	\N
386	yeni masaörtü kağıt sipariş	2024-11-29		f	2024-11-29 07:56:44.056581+00	2024-11-29 07:56:44.05662+00	\N	\N
375	Halil ara kalsiyum guncelle	2024-11-28		f	2024-11-24 09:07:10.572773+00	2024-11-24 09:07:10.572773+00	\N	\N
380	ups konuş	2024-12-02		f	2024-11-24 09:09:36.02356+00	2024-11-24 09:09:36.02356+00	\N	\N
387	modem al	2024-11-30		f	2024-11-30 13:33:24.494931+00	2024-11-30 13:33:24.494948+00	\N	\N
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: realtime; Owner: supabase_admin
--

COPY realtime.schema_migrations (version, inserted_at) FROM stdin;
20211116024918	2024-07-17 22:19:29
20211116045059	2024-07-17 22:19:29
20211116050929	2024-07-17 22:19:29
20211116051442	2024-07-17 22:19:29
20211116212300	2024-07-17 22:19:29
20211116213355	2024-07-17 22:19:30
20211116213934	2024-07-17 22:19:30
20211116214523	2024-07-17 22:19:30
20211122062447	2024-07-17 22:19:30
20211124070109	2024-07-17 22:19:30
20211202204204	2024-07-17 22:19:30
20211202204605	2024-07-17 22:19:30
20211210212804	2024-07-17 22:19:31
20211228014915	2024-07-17 22:19:31
20220107221237	2024-07-17 22:19:31
20220228202821	2024-07-17 22:19:31
20220312004840	2024-07-17 22:19:31
20220603231003	2024-07-17 22:19:32
20220603232444	2024-07-17 22:19:32
20220615214548	2024-07-17 22:19:32
20220712093339	2024-07-17 22:19:32
20220908172859	2024-07-17 22:19:32
20220916233421	2024-07-17 22:19:32
20230119133233	2024-07-17 22:19:32
20230128025114	2024-07-17 22:19:33
20230128025212	2024-07-17 22:19:33
20230227211149	2024-07-17 22:19:33
20230228184745	2024-07-17 22:19:33
20230308225145	2024-07-17 22:19:33
20230328144023	2024-07-17 22:19:33
20231018144023	2024-07-17 22:19:34
20231204144023	2024-07-17 22:19:34
20231204144024	2024-07-17 22:19:34
20231204144025	2024-07-17 22:19:34
20240108234812	2024-07-17 22:19:34
20240109165339	2024-07-17 22:19:34
20240227174441	2024-07-17 22:19:34
20240311171622	2024-07-17 22:19:35
20240321100241	2024-07-17 22:19:35
20240401105812	2024-07-17 22:19:35
20240418121054	2024-07-17 22:19:36
20240523004032	2024-07-17 22:19:36
20240618124746	2024-07-17 22:19:36
20240801235015	2024-08-09 23:29:32
20240805133720	2024-08-09 23:29:32
20240827160934	2024-09-08 05:18:41
20240919163303	2024-11-16 11:37:43
20240919163305	2024-11-16 11:37:43
20241019105805	2024-11-16 11:37:43
20241030150047	2024-11-16 11:37:43
20241108114728	2024-11-16 11:37:44
20241121104152	2024-11-29 19:38:33
\.


--
-- Data for Name: subscription; Type: TABLE DATA; Schema: realtime; Owner: supabase_admin
--

COPY realtime.subscription (id, subscription_id, entity, filters, claims, created_at) FROM stdin;
\.


--
-- Data for Name: buckets; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--

COPY storage.buckets (id, name, owner, created_at, updated_at, public, avif_autodetection, file_size_limit, allowed_mime_types, owner_id) FROM stdin;
embroidered_sheer_curtain_fabrics	embroidered_sheer_curtain_fabrics	\N	2024-01-21 14:46:05.599305+00	2024-01-21 14:46:05.599305+00	f	f	\N	\N	\N
\.


--
-- Data for Name: migrations; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--

COPY storage.migrations (id, name, hash, executed_at) FROM stdin;
0	create-migrations-table	e18db593bcde2aca2a408c4d1100f6abba2195df	2024-01-25 18:21:57.862732
1	initialmigration	6ab16121fbaa08bbd11b712d05f358f9b555d777	2024-01-25 18:21:57.862732
2	storage-schema	5c7968fd083fcea04050c1b7f6253c9771b99011	2024-01-25 18:21:57.862732
3	pathtoken-column	2cb1b0004b817b29d5b0a971af16bafeede4b70d	2024-01-25 18:21:57.862732
4	add-migrations-rls	427c5b63fe1c5937495d9c635c263ee7a5905058	2024-01-25 18:21:57.862732
5	add-size-functions	79e081a1455b63666c1294a440f8ad4b1e6a7f84	2024-01-25 18:21:57.862732
6	change-column-name-in-get-size	f93f62afdf6613ee5e7e815b30d02dc990201044	2024-01-25 18:21:57.862732
7	add-rls-to-buckets	e7e7f86adbc51049f341dfe8d30256c1abca17aa	2024-01-25 18:21:57.862732
8	add-public-to-buckets	fd670db39ed65f9d08b01db09d6202503ca2bab3	2024-01-25 18:21:57.862732
9	fix-search-function	3a0af29f42e35a4d101c259ed955b67e1bee6825	2024-01-25 18:21:57.862732
10	search-files-search-function	68dc14822daad0ffac3746a502234f486182ef6e	2024-01-25 18:21:57.862732
11	add-trigger-to-auto-update-updated_at-column	7425bdb14366d1739fa8a18c83100636d74dcaa2	2024-01-25 18:21:57.862732
12	add-automatic-avif-detection-flag	8e92e1266eb29518b6a4c5313ab8f29dd0d08df9	2024-01-25 18:21:57.862732
13	add-bucket-custom-limits	cce962054138135cd9a8c4bcd531598684b25e7d	2024-01-25 18:21:57.862732
14	use-bytes-for-max-size	941c41b346f9802b411f06f30e972ad4744dad27	2024-01-25 18:21:57.862732
15	add-can-insert-object-function	934146bc38ead475f4ef4b555c524ee5d66799e5	2024-01-25 18:21:57.862732
16	add-version	76debf38d3fd07dcfc747ca49096457d95b1221b	2024-01-25 18:21:57.862732
17	drop-owner-foreign-key	f1cbb288f1b7a4c1eb8c38504b80ae2a0153d101	2024-01-25 18:21:57.862732
18	add_owner_id_column_deprecate_owner	e7a511b379110b08e2f214be852c35414749fe66	2024-01-25 18:21:57.862732
19	alter-default-value-objects-id	02e5e22a78626187e00d173dc45f58fa66a4f043	2024-01-25 18:21:57.869378
20	list-objects-with-delimiter	cd694ae708e51ba82bf012bba00caf4f3b6393b7	2024-05-23 01:40:09.649051
21	s3-multipart-uploads	8c804d4a566c40cd1e4cc5b3725a664a9303657f	2024-05-23 01:40:09.705309
22	s3-multipart-uploads-big-ints	9737dc258d2397953c9953d9b86920b8be0cdb73	2024-05-23 01:40:09.760661
23	optimize-search-function	9d7e604cddc4b56a5422dc68c9313f4a1b6f132c	2024-05-23 01:40:09.834358
24	operation-function	8312e37c2bf9e76bbe841aa5fda889206d2bf8aa	2024-07-17 22:19:29.709648
25	custom-metadata	67eb93b7e8d401cafcdc97f9ac779e71a79bfe03	2024-08-24 16:38:11.37232
\.


--
-- Data for Name: objects; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--

COPY storage.objects (id, bucket_id, name, owner, created_at, updated_at, last_accessed_at, metadata, version, owner_id, user_metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--

COPY storage.s3_multipart_uploads (id, in_progress_size, upload_signature, bucket_id, key, version, owner_id, created_at, user_metadata) FROM stdin;
\.


--
-- Data for Name: s3_multipart_uploads_parts; Type: TABLE DATA; Schema: storage; Owner: supabase_storage_admin
--

COPY storage.s3_multipart_uploads_parts (id, upload_id, size, part_number, bucket_id, key, etag, owner_id, version, created_at) FROM stdin;
\.


--
-- Data for Name: secrets; Type: TABLE DATA; Schema: vault; Owner: supabase_admin
--

COPY vault.secrets (id, name, description, secret, key_id, nonce, created_at, updated_at) FROM stdin;
\.


--
-- Name: refresh_tokens_id_seq; Type: SEQUENCE SET; Schema: auth; Owner: supabase_auth_admin
--

SELECT pg_catalog.setval('auth.refresh_tokens_id_seq', 1, false);


--
-- Name: key_key_id_seq; Type: SEQUENCE SET; Schema: pgsodium; Owner: supabase_admin
--

SELECT pg_catalog.setval('pgsodium.key_key_id_seq', 1, false);


--
-- Name: User_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."User_id_seq"', 6, true);


--
-- Name: accounting_asset_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_asset_id_seq', 1, false);


--
-- Name: accounting_assetcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_assetcategory_id_seq', 6, true);


--
-- Name: accounting_book_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_book_id_seq', 3, true);


--
-- Name: accounting_cashcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_cashcategory_id_seq', 12, true);


--
-- Name: accounting_currencycategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_currencycategory_id_seq', 3, true);


--
-- Name: accounting_equitycapital_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equitycapital_id_seq', 5, true);


--
-- Name: accounting_equitydivident_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equitydivident_id_seq', 1, true);


--
-- Name: accounting_equityrevenue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equityrevenue_id_seq', 2, true);


--
-- Name: accounting_expense_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_expense_id_seq', 10, true);


--
-- Name: accounting_expensecategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_expensecategory_id_seq', 20, true);


--
-- Name: accounting_income_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_income_id_seq', 1, false);


--
-- Name: accounting_incomecategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_incomecategory_id_seq', 1, false);


--
-- Name: accounting_liability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_liability_id_seq', 1, false);


--
-- Name: accounting_sale_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_sale_id_seq', 1, false);


--
-- Name: accounting_source_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_source_id_seq', 1, false);


--
-- Name: accounting_stakeholder_books_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_stakeholder_books_id_seq', 6, true);


--
-- Name: accounting_stakeholder_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_stakeholder_id_seq', 6, true);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 176, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 1, false);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 4, true);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- Name: authentication_member_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_member_id_seq', 3, true);


--
-- Name: crm_company_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_company_id_seq', 102, true);


--
-- Name: crm_contact_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_contact_id_seq', 6, true);


--
-- Name: crm_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_note_id_seq', 105, true);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 174, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 38, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 205, true);


--
-- Name: operating_machine_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_machine_id_seq', 2, true);


--
-- Name: operating_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_product_id_seq', 4, true);


--
-- Name: operating_product_raw_materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_product_raw_materials_id_seq', 1, false);


--
-- Name: operating_rawmaterial_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_rawmaterial_id_seq', 1, false);


--
-- Name: operating_rawmaterial_supplierCompany_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."operating_rawmaterial_supplierCompany_id_seq"', 1, false);


--
-- Name: operating_rawmaterial_supplierContact_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."operating_rawmaterial_supplierContact_id_seq"', 1, false);


--
-- Name: operating_rawmaterialcategorys_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_rawmaterialcategorys_id_seq', 6, true);


--
-- Name: operating_unitcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_unitcategory_id_seq', 1, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.products_id_seq', 4735, true);


--
-- Name: todo_task_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.todo_task_id_seq', 387, true);


--
-- Name: subscription_id_seq; Type: SEQUENCE SET; Schema: realtime; Owner: supabase_admin
--

SELECT pg_catalog.setval('realtime.subscription_id_seq', 1, false);


--
-- Name: mfa_amr_claims amr_id_pk; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT amr_id_pk PRIMARY KEY (id);


--
-- Name: audit_log_entries audit_log_entries_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.audit_log_entries
    ADD CONSTRAINT audit_log_entries_pkey PRIMARY KEY (id);


--
-- Name: flow_state flow_state_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.flow_state
    ADD CONSTRAINT flow_state_pkey PRIMARY KEY (id);


--
-- Name: identities identities_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_pkey PRIMARY KEY (id);


--
-- Name: identities identities_provider_id_provider_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_provider_id_provider_unique UNIQUE (provider_id, provider);


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_authentication_method_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_authentication_method_pkey UNIQUE (session_id, authentication_method);


--
-- Name: mfa_challenges mfa_challenges_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_pkey PRIMARY KEY (id);


--
-- Name: mfa_factors mfa_factors_last_challenged_at_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_last_challenged_at_key UNIQUE (last_challenged_at);


--
-- Name: mfa_factors mfa_factors_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_pkey PRIMARY KEY (id);


--
-- Name: one_time_tokens one_time_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_unique; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_unique UNIQUE (token);


--
-- Name: saml_providers saml_providers_entity_id_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_entity_id_key UNIQUE (entity_id);


--
-- Name: saml_providers saml_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_pkey PRIMARY KEY (id);


--
-- Name: saml_relay_states saml_relay_states_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: sso_domains sso_domains_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_pkey PRIMARY KEY (id);


--
-- Name: sso_providers sso_providers_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_providers
    ADD CONSTRAINT sso_providers_pkey PRIMARY KEY (id);


--
-- Name: users users_phone_key; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_phone_key UNIQUE (phone);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: User User_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."User"
    ADD CONSTRAINT "User_pkey" PRIMARY KEY (id);


--
-- Name: _prisma_migrations _prisma_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public._prisma_migrations
    ADD CONSTRAINT _prisma_migrations_pkey PRIMARY KEY (id);


--
-- Name: accounting_asset accounting_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_asset
    ADD CONSTRAINT accounting_asset_pkey PRIMARY KEY (id);


--
-- Name: accounting_assetcategory accounting_assetcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetcategory
    ADD CONSTRAINT accounting_assetcategory_pkey PRIMARY KEY (id);


--
-- Name: accounting_book accounting_book_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_book
    ADD CONSTRAINT accounting_book_name_key UNIQUE (name);


--
-- Name: accounting_book accounting_book_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_book
    ADD CONSTRAINT accounting_book_pkey PRIMARY KEY (id);


--
-- Name: accounting_cashaccount accounting_cashcategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashcategory_name_key UNIQUE (name);


--
-- Name: accounting_cashaccount accounting_cashcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashcategory_pkey PRIMARY KEY (id);


--
-- Name: accounting_currencycategory accounting_currencycategory_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencycategory
    ADD CONSTRAINT accounting_currencycategory_code_key UNIQUE (code);


--
-- Name: accounting_currencycategory accounting_currencycategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencycategory
    ADD CONSTRAINT accounting_currencycategory_name_key UNIQUE (name);


--
-- Name: accounting_currencycategory accounting_currencycategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencycategory
    ADD CONSTRAINT accounting_currencycategory_pkey PRIMARY KEY (id);


--
-- Name: accounting_equitycapital accounting_equitycapital_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycapital_pkey PRIMARY KEY (id);


--
-- Name: accounting_equitydivident accounting_equitydivident_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydivident_pkey PRIMARY KEY (id);


--
-- Name: accounting_equityrevenue accounting_equityrevenue_invoice_number_2ddec667_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrevenue_invoice_number_2ddec667_uniq UNIQUE (invoice_number);


--
-- Name: accounting_equityrevenue accounting_equityrevenue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrevenue_pkey PRIMARY KEY (id);


--
-- Name: accounting_equityexpense accounting_expense_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_expense_pkey PRIMARY KEY (id);


--
-- Name: accounting_expensecategory accounting_expensecategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_expensecategory
    ADD CONSTRAINT accounting_expensecategory_name_key UNIQUE (name);


--
-- Name: accounting_expensecategory accounting_expensecategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_expensecategory
    ADD CONSTRAINT accounting_expensecategory_pkey PRIMARY KEY (id);


--
-- Name: accounting_income accounting_income_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_pkey PRIMARY KEY (id);


--
-- Name: accounting_incomecategory accounting_incomecategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_incomecategory
    ADD CONSTRAINT accounting_incomecategory_name_key UNIQUE (name);


--
-- Name: accounting_incomecategory accounting_incomecategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_incomecategory
    ADD CONSTRAINT accounting_incomecategory_pkey PRIMARY KEY (id);


--
-- Name: accounting_liability accounting_liability_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liability
    ADD CONSTRAINT accounting_liability_pkey PRIMARY KEY (id);


--
-- Name: accounting_sale accounting_sale_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_sale
    ADD CONSTRAINT accounting_sale_pkey PRIMARY KEY (id);


--
-- Name: accounting_source accounting_source_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_source
    ADD CONSTRAINT accounting_source_name_key UNIQUE (name);


--
-- Name: accounting_source accounting_source_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_source
    ADD CONSTRAINT accounting_source_pkey PRIMARY KEY (id);


--
-- Name: accounting_stakeholder_books accounting_stakeholder_b_stakeholder_id_book_id_a15cdfe0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholder_books
    ADD CONSTRAINT accounting_stakeholder_b_stakeholder_id_book_id_a15cdfe0_uniq UNIQUE (stakeholder_id, book_id);


--
-- Name: accounting_stakeholder_books accounting_stakeholder_books_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholder_books
    ADD CONSTRAINT accounting_stakeholder_books_pkey PRIMARY KEY (id);


--
-- Name: accounting_stakeholder accounting_stakeholder_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholder
    ADD CONSTRAINT accounting_stakeholder_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: authentication_member authentication_member_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member
    ADD CONSTRAINT authentication_member_pkey PRIMARY KEY (id);


--
-- Name: authentication_member authentication_member_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member
    ADD CONSTRAINT authentication_member_user_id_key UNIQUE (user_id);


--
-- Name: crm_company crm_company_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_company
    ADD CONSTRAINT crm_company_pkey PRIMARY KEY (id);


--
-- Name: crm_contact crm_contact_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_contact
    ADD CONSTRAINT crm_contact_pkey PRIMARY KEY (id);


--
-- Name: crm_note crm_note_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_note
    ADD CONSTRAINT crm_note_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: operating_machine operating_machine_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machine
    ADD CONSTRAINT operating_machine_name_key UNIQUE (name);


--
-- Name: operating_machine operating_machine_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machine
    ADD CONSTRAINT operating_machine_pkey PRIMARY KEY (id);


--
-- Name: operating_product operating_product_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product
    ADD CONSTRAINT operating_product_pkey PRIMARY KEY (id);


--
-- Name: operating_product_raw_materials operating_product_raw_ma_product_id_rawmaterial_i_9271b286_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product_raw_materials
    ADD CONSTRAINT operating_product_raw_ma_product_id_rawmaterial_i_9271b286_uniq UNIQUE (product_id, rawmaterial_id);


--
-- Name: operating_product_raw_materials operating_product_raw_materials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product_raw_materials
    ADD CONSTRAINT operating_product_raw_materials_pkey PRIMARY KEY (id);


--
-- Name: operating_rawmaterial operating_rawmaterial_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_rawmaterial
    ADD CONSTRAINT operating_rawmaterial_name_key UNIQUE (name);


--
-- Name: operating_rawmaterial operating_rawmaterial_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_rawmaterial
    ADD CONSTRAINT operating_rawmaterial_pkey PRIMARY KEY (id);


--
-- Name: operating_rawmaterial_supplierCompany operating_rawmaterial_su_rawmaterial_id_company_i_fe74953a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierCompany"
    ADD CONSTRAINT operating_rawmaterial_su_rawmaterial_id_company_i_fe74953a_uniq UNIQUE (rawmaterial_id, company_id);


--
-- Name: operating_rawmaterial_supplierContact operating_rawmaterial_su_rawmaterial_id_contact_i_c48bb84c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierContact"
    ADD CONSTRAINT operating_rawmaterial_su_rawmaterial_id_contact_i_c48bb84c_uniq UNIQUE (rawmaterial_id, contact_id);


--
-- Name: operating_rawmaterial_supplierCompany operating_rawmaterial_supplierCompany_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierCompany"
    ADD CONSTRAINT "operating_rawmaterial_supplierCompany_pkey" PRIMARY KEY (id);


--
-- Name: operating_rawmaterial_supplierContact operating_rawmaterial_supplierContact_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierContact"
    ADD CONSTRAINT "operating_rawmaterial_supplierContact_pkey" PRIMARY KEY (id);


--
-- Name: operating_rawmaterialcategory operating_rawmaterialcategorys_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_rawmaterialcategory
    ADD CONSTRAINT operating_rawmaterialcategorys_name_key UNIQUE (name);


--
-- Name: operating_rawmaterialcategory operating_rawmaterialcategorys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_rawmaterialcategory
    ADD CONSTRAINT operating_rawmaterialcategorys_pkey PRIMARY KEY (id);


--
-- Name: operating_unitcategory operating_unitcategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_unitcategory
    ADD CONSTRAINT operating_unitcategory_name_key UNIQUE (name);


--
-- Name: operating_unitcategory operating_unitcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_unitcategory
    ADD CONSTRAINT operating_unitcategory_pkey PRIMARY KEY (id);


--
-- Name: products products_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_name_key UNIQUE (name);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: todo_task todo_task_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.todo_task
    ADD CONSTRAINT todo_task_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE ONLY realtime.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, inserted_at);


--
-- Name: subscription pk_subscription; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.subscription
    ADD CONSTRAINT pk_subscription PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: realtime; Owner: supabase_admin
--

ALTER TABLE ONLY realtime.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: buckets buckets_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.buckets
    ADD CONSTRAINT buckets_pkey PRIMARY KEY (id);


--
-- Name: migrations migrations_name_key; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_name_key UNIQUE (name);


--
-- Name: migrations migrations_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.migrations
    ADD CONSTRAINT migrations_pkey PRIMARY KEY (id);


--
-- Name: objects objects_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT objects_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_pkey PRIMARY KEY (id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_pkey; Type: CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_pkey PRIMARY KEY (id);


--
-- Name: audit_logs_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);


--
-- Name: confirmation_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_current_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);


--
-- Name: email_change_token_new_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);


--
-- Name: factor_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);


--
-- Name: flow_state_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);


--
-- Name: identities_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);


--
-- Name: INDEX identities_email_idx; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX auth.identities_email_idx IS 'Auth: Ensures indexed queries on the email column';


--
-- Name: identities_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);


--
-- Name: idx_auth_code; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);


--
-- Name: idx_user_id_auth_method; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);


--
-- Name: mfa_challenge_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);


--
-- Name: mfa_factors_user_friendly_name_unique; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);


--
-- Name: mfa_factors_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);


--
-- Name: one_time_tokens_relates_to_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);


--
-- Name: one_time_tokens_token_hash_hash_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);


--
-- Name: one_time_tokens_user_id_token_type_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);


--
-- Name: reauthentication_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: recovery_token_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);


--
-- Name: refresh_tokens_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);


--
-- Name: refresh_tokens_instance_id_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);


--
-- Name: refresh_tokens_parent_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);


--
-- Name: refresh_tokens_session_id_revoked_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);


--
-- Name: refresh_tokens_updated_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);


--
-- Name: saml_providers_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);


--
-- Name: saml_relay_states_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);


--
-- Name: saml_relay_states_for_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);


--
-- Name: saml_relay_states_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);


--
-- Name: sessions_not_after_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);


--
-- Name: sessions_user_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);


--
-- Name: sso_domains_domain_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));


--
-- Name: sso_domains_sso_provider_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);


--
-- Name: sso_providers_resource_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));


--
-- Name: unique_phone_factor_per_user; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);


--
-- Name: user_id_created_at_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);


--
-- Name: users_email_partial_key; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);


--
-- Name: INDEX users_email_partial_key; Type: COMMENT; Schema: auth; Owner: supabase_auth_admin
--

COMMENT ON INDEX auth.users_email_partial_key IS 'Auth: A partial unique index that applies only when is_sso_user is false';


--
-- Name: users_instance_id_email_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));


--
-- Name: users_instance_id_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);


--
-- Name: users_is_anonymous_idx; Type: INDEX; Schema: auth; Owner: supabase_auth_admin
--

CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);


--
-- Name: User_email_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "User_email_key" ON public."User" USING btree (email);


--
-- Name: User_username_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "User_username_key" ON public."User" USING btree (username);


--
-- Name: accounting_asset_book_id_96ce9c3b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_asset_book_id_96ce9c3b ON public.accounting_asset USING btree (book_id);


--
-- Name: accounting_asset_category_id_ffeda4ca; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_asset_category_id_ffeda4ca ON public.accounting_asset USING btree (category_id);


--
-- Name: accounting_asset_currency_id_018a2eef; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_asset_currency_id_018a2eef ON public.accounting_asset USING btree (currency_id);


--
-- Name: accounting_book_name_6eb9bad9_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_book_name_6eb9bad9_like ON public.accounting_book USING btree (name varchar_pattern_ops);


--
-- Name: accounting_cashcategory_book_id_56033a99; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_cashcategory_book_id_56033a99 ON public.accounting_cashaccount USING btree (book_id);


--
-- Name: accounting_cashcategory_currency_id_ed9ccd42; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_cashcategory_currency_id_ed9ccd42 ON public.accounting_cashaccount USING btree (currency_id);


--
-- Name: accounting_cashcategory_name_431b4fdc_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_cashcategory_name_431b4fdc_like ON public.accounting_cashaccount USING btree (name varchar_pattern_ops);


--
-- Name: accounting_currencycategory_code_afbf6634_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencycategory_code_afbf6634_like ON public.accounting_currencycategory USING btree (code varchar_pattern_ops);


--
-- Name: accounting_currencycategory_name_62f10b06_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencycategory_name_62f10b06_like ON public.accounting_currencycategory USING btree (name varchar_pattern_ops);


--
-- Name: accounting_equitycapital_book_id_3bb7b1c9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_book_id_3bb7b1c9 ON public.accounting_equitycapital USING btree (book_id);


--
-- Name: accounting_equitycapital_cash_account_id_b51b8a10; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_cash_account_id_b51b8a10 ON public.accounting_equitycapital USING btree (cash_account_id);


--
-- Name: accounting_equitycapital_stakeholder_id_249de618; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_stakeholder_id_249de618 ON public.accounting_equitycapital USING btree (stakeholder_id);


--
-- Name: accounting_equitydivident_book_id_4784d867; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitydivident_book_id_4784d867 ON public.accounting_equitydivident USING btree (book_id);


--
-- Name: accounting_equitydivident_cash_account_id_2006fe5d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitydivident_cash_account_id_2006fe5d ON public.accounting_equitydivident USING btree (cash_account_id);


--
-- Name: accounting_equitydivident_currency_id_22acf853; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitydivident_currency_id_22acf853 ON public.accounting_equitydivident USING btree (currency_id);


--
-- Name: accounting_equitydivident_stakeholder_id_5dbb375b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitydivident_stakeholder_id_5dbb375b ON public.accounting_equitydivident USING btree (stakeholder_id);


--
-- Name: accounting_equityexpense_cash_account_id_bbe4c920; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityexpense_cash_account_id_bbe4c920 ON public.accounting_equityexpense USING btree (cash_account_id);


--
-- Name: accounting_equityrevenue_book_id_784ed443; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityrevenue_book_id_784ed443 ON public.accounting_equityrevenue USING btree (book_id);


--
-- Name: accounting_equityrevenue_cash_account_id_2fb5d4af; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityrevenue_cash_account_id_2fb5d4af ON public.accounting_equityrevenue USING btree (cash_account_id);


--
-- Name: accounting_equityrevenue_currency_id_52d19808; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityrevenue_currency_id_52d19808 ON public.accounting_equityrevenue USING btree (currency_id);


--
-- Name: accounting_equityrevenue_invoice_number_2ddec667_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityrevenue_invoice_number_2ddec667_like ON public.accounting_equityrevenue USING btree (invoice_number varchar_pattern_ops);


--
-- Name: accounting_expense_book_id_7cf396e0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_expense_book_id_7cf396e0 ON public.accounting_equityexpense USING btree (book_id);


--
-- Name: accounting_expense_category_id_4c3c6039; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_expense_category_id_4c3c6039 ON public.accounting_equityexpense USING btree (category_id);


--
-- Name: accounting_expense_currency_id_4fa319fa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_expense_currency_id_4fa319fa ON public.accounting_equityexpense USING btree (currency_id);


--
-- Name: accounting_expensecategory_name_cb9859d6_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_expensecategory_name_cb9859d6_like ON public.accounting_expensecategory USING btree (name varchar_pattern_ops);


--
-- Name: accounting_income_book_id_2f801538; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_income_book_id_2f801538 ON public.accounting_income USING btree (book_id);


--
-- Name: accounting_income_category_id_2b0c8e30; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_income_category_id_2b0c8e30 ON public.accounting_income USING btree (category_id);


--
-- Name: accounting_income_company_id_a4707f89; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_income_company_id_a4707f89 ON public.accounting_income USING btree (company_id);


--
-- Name: accounting_income_contact_id_49ff044c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_income_contact_id_49ff044c ON public.accounting_income USING btree (contact_id);


--
-- Name: accounting_income_currency_id_fbb08274; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_income_currency_id_fbb08274 ON public.accounting_income USING btree (currency_id);


--
-- Name: accounting_incomecategory_name_0a608f43_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_incomecategory_name_0a608f43_like ON public.accounting_incomecategory USING btree (name varchar_pattern_ops);


--
-- Name: accounting_liability_book_id_deedcf1e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_liability_book_id_deedcf1e ON public.accounting_liability USING btree (book_id);


--
-- Name: accounting_liability_currency_id_14ae9658; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_liability_currency_id_14ae9658 ON public.accounting_liability USING btree (currency_id);


--
-- Name: accounting_sale_book_id_5599229e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_sale_book_id_5599229e ON public.accounting_sale USING btree (book_id);


--
-- Name: accounting_sale_company_id_ebd53907; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_sale_company_id_ebd53907 ON public.accounting_sale USING btree (company_id);


--
-- Name: accounting_sale_contact_id_1b7738ca; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_sale_contact_id_1b7738ca ON public.accounting_sale USING btree (contact_id);


--
-- Name: accounting_sale_product_id_1eec5171; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_sale_product_id_1eec5171 ON public.accounting_sale USING btree (product_id);


--
-- Name: accounting_source_name_b1b99e07_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_source_name_b1b99e07_like ON public.accounting_source USING btree (name varchar_pattern_ops);


--
-- Name: accounting_stakeholder_books_book_id_f8016a55; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_stakeholder_books_book_id_f8016a55 ON public.accounting_stakeholder_books USING btree (book_id);


--
-- Name: accounting_stakeholder_books_stakeholder_id_a2305ace; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_stakeholder_books_stakeholder_id_a2305ace ON public.accounting_stakeholder_books USING btree (stakeholder_id);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: crm_contact_company_id_5104bcf2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX crm_contact_company_id_5104bcf2 ON public.crm_contact USING btree (company_id);


--
-- Name: crm_note_company_id_9ceedb83; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX crm_note_company_id_9ceedb83 ON public.crm_note USING btree (company_id);


--
-- Name: crm_note_contact_id_8d258ea9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX crm_note_contact_id_8d258ea9 ON public.crm_note USING btree (contact_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: operating_machine_name_eb93fe62_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_machine_name_eb93fe62_like ON public.operating_machine USING btree (name varchar_pattern_ops);


--
-- Name: operating_product_raw_materials_product_id_3dfc607e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_product_raw_materials_product_id_3dfc607e ON public.operating_product_raw_materials USING btree (product_id);


--
-- Name: operating_product_raw_materials_rawmaterial_id_f0003e51; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_product_raw_materials_rawmaterial_id_f0003e51 ON public.operating_product_raw_materials USING btree (rawmaterial_id);


--
-- Name: operating_product_unit_id_e80cf5d8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_product_unit_id_e80cf5d8 ON public.operating_product USING btree (unit_id);


--
-- Name: operating_rawmaterial_name_8db113a7_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_rawmaterial_name_8db113a7_like ON public.operating_rawmaterial USING btree (name varchar_pattern_ops);


--
-- Name: operating_rawmaterial_supplierCompany_company_id_8c97abaa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "operating_rawmaterial_supplierCompany_company_id_8c97abaa" ON public."operating_rawmaterial_supplierCompany" USING btree (company_id);


--
-- Name: operating_rawmaterial_supplierCompany_rawmaterial_id_32c6a12b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "operating_rawmaterial_supplierCompany_rawmaterial_id_32c6a12b" ON public."operating_rawmaterial_supplierCompany" USING btree (rawmaterial_id);


--
-- Name: operating_rawmaterial_supplierContact_contact_id_5bd68355; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "operating_rawmaterial_supplierContact_contact_id_5bd68355" ON public."operating_rawmaterial_supplierContact" USING btree (contact_id);


--
-- Name: operating_rawmaterial_supplierContact_rawmaterial_id_44202a26; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "operating_rawmaterial_supplierContact_rawmaterial_id_44202a26" ON public."operating_rawmaterial_supplierContact" USING btree (rawmaterial_id);


--
-- Name: operating_rawmaterial_type_id_7bda2e97; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_rawmaterial_type_id_7bda2e97 ON public.operating_rawmaterial USING btree (type_id);


--
-- Name: operating_rawmaterialcategorys_name_299c8e43_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_rawmaterialcategorys_name_299c8e43_like ON public.operating_rawmaterialcategory USING btree (name varchar_pattern_ops);


--
-- Name: operating_unitcategory_name_50047453_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_unitcategory_name_50047453_like ON public.operating_unitcategory USING btree (name varchar_pattern_ops);


--
-- Name: todo_task_company_id_fed9e4bc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX todo_task_company_id_fed9e4bc ON public.todo_task USING btree (company_id);


--
-- Name: todo_task_contact_id_4691b54e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX todo_task_contact_id_4691b54e ON public.todo_task USING btree (contact_id);


--
-- Name: ix_realtime_subscription_entity; Type: INDEX; Schema: realtime; Owner: supabase_admin
--

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING hash (entity);


--
-- Name: subscription_subscription_id_entity_filters_key; Type: INDEX; Schema: realtime; Owner: supabase_admin
--

CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_key ON realtime.subscription USING btree (subscription_id, entity, filters);


--
-- Name: bname; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);


--
-- Name: bucketid_objname; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);


--
-- Name: idx_multipart_uploads_list; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);


--
-- Name: idx_objects_bucket_id_name; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");


--
-- Name: name_prefix_search; Type: INDEX; Schema: storage; Owner: supabase_storage_admin
--

CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);


--
-- Name: subscription tr_check_filters; Type: TRIGGER; Schema: realtime; Owner: supabase_admin
--

CREATE TRIGGER tr_check_filters BEFORE INSERT OR UPDATE ON realtime.subscription FOR EACH ROW EXECUTE FUNCTION realtime.subscription_check_filters();


--
-- Name: objects update_objects_updated_at; Type: TRIGGER; Schema: storage; Owner: supabase_storage_admin
--

CREATE TRIGGER update_objects_updated_at BEFORE UPDATE ON storage.objects FOR EACH ROW EXECUTE FUNCTION storage.update_updated_at_column();


--
-- Name: identities identities_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.identities
    ADD CONSTRAINT identities_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: mfa_amr_claims mfa_amr_claims_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_amr_claims
    ADD CONSTRAINT mfa_amr_claims_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: mfa_challenges mfa_challenges_auth_factor_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_challenges
    ADD CONSTRAINT mfa_challenges_auth_factor_id_fkey FOREIGN KEY (factor_id) REFERENCES auth.mfa_factors(id) ON DELETE CASCADE;


--
-- Name: mfa_factors mfa_factors_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.mfa_factors
    ADD CONSTRAINT mfa_factors_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: one_time_tokens one_time_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.one_time_tokens
    ADD CONSTRAINT one_time_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: refresh_tokens refresh_tokens_session_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.refresh_tokens
    ADD CONSTRAINT refresh_tokens_session_id_fkey FOREIGN KEY (session_id) REFERENCES auth.sessions(id) ON DELETE CASCADE;


--
-- Name: saml_providers saml_providers_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_providers
    ADD CONSTRAINT saml_providers_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_flow_state_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_flow_state_id_fkey FOREIGN KEY (flow_state_id) REFERENCES auth.flow_state(id) ON DELETE CASCADE;


--
-- Name: saml_relay_states saml_relay_states_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.saml_relay_states
    ADD CONSTRAINT saml_relay_states_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;


--
-- Name: sso_domains sso_domains_sso_provider_id_fkey; Type: FK CONSTRAINT; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE ONLY auth.sso_domains
    ADD CONSTRAINT sso_domains_sso_provider_id_fkey FOREIGN KEY (sso_provider_id) REFERENCES auth.sso_providers(id) ON DELETE CASCADE;


--
-- Name: accounting_asset accounting_asset_book_id_96ce9c3b_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_asset
    ADD CONSTRAINT accounting_asset_book_id_96ce9c3b_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_asset accounting_asset_category_id_ffeda4ca_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_asset
    ADD CONSTRAINT accounting_asset_category_id_ffeda4ca_fk_accountin FOREIGN KEY (category_id) REFERENCES public.accounting_assetcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_asset accounting_asset_currency_id_018a2eef_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_asset
    ADD CONSTRAINT accounting_asset_currency_id_018a2eef_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_cashaccount accounting_cashcateg_currency_id_ed9ccd42_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashcateg_currency_id_ed9ccd42_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_cashaccount accounting_cashcategory_book_id_56033a99_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashcategory_book_id_56033a99_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycap_cash_account_id_b51b8a10_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycap_cash_account_id_b51b8a10_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycap_stakeholder_id_249de618_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycap_stakeholder_id_249de618_fk_accountin FOREIGN KEY (stakeholder_id) REFERENCES public.accounting_stakeholder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycapital_book_id_3bb7b1c9_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycapital_book_id_3bb7b1c9_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitydivident accounting_equitydiv_book_id_4784d867_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydiv_book_id_4784d867_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitydivident accounting_equitydiv_cash_account_id_2006fe5d_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydiv_cash_account_id_2006fe5d_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitydivident accounting_equitydiv_currency_id_22acf853_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydiv_currency_id_22acf853_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitydivident accounting_equitydiv_stakeholder_id_5dbb375b_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydiv_stakeholder_id_5dbb375b_fk_accountin FOREIGN KEY (stakeholder_id) REFERENCES public.accounting_stakeholder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_equityexp_cash_account_id_bbe4c920_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_equityexp_cash_account_id_bbe4c920_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityrevenue accounting_equityrev_cash_account_id_2fb5d4af_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrev_cash_account_id_2fb5d4af_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityrevenue accounting_equityrev_currency_id_52d19808_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrev_currency_id_52d19808_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityrevenue accounting_equityrevenue_book_id_784ed443_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrevenue_book_id_784ed443_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_expense_book_id_7cf396e0_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_expense_book_id_7cf396e0_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_expense_category_id_4c3c6039_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_expense_category_id_4c3c6039_fk_accountin FOREIGN KEY (category_id) REFERENCES public.accounting_expensecategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_expense_currency_id_4fa319fa_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_expense_currency_id_4fa319fa_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_income accounting_income_book_id_2f801538_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_book_id_2f801538_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_income accounting_income_category_id_2b0c8e30_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_category_id_2b0c8e30_fk_accountin FOREIGN KEY (category_id) REFERENCES public.accounting_incomecategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_income accounting_income_company_id_a4707f89_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_company_id_a4707f89_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_income accounting_income_contact_id_49ff044c_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_contact_id_49ff044c_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_income accounting_income_currency_id_fbb08274_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_income
    ADD CONSTRAINT accounting_income_currency_id_fbb08274_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_liability accounting_liability_book_id_deedcf1e_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liability
    ADD CONSTRAINT accounting_liability_book_id_deedcf1e_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_liability accounting_liability_currency_id_14ae9658_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liability
    ADD CONSTRAINT accounting_liability_currency_id_14ae9658_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_sale accounting_sale_book_id_5599229e_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_sale
    ADD CONSTRAINT accounting_sale_book_id_5599229e_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_sale accounting_sale_company_id_ebd53907_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_sale
    ADD CONSTRAINT accounting_sale_company_id_ebd53907_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_sale accounting_sale_contact_id_1b7738ca_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_sale
    ADD CONSTRAINT accounting_sale_contact_id_1b7738ca_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_sale accounting_sale_product_id_1eec5171_fk_operating_product_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_sale
    ADD CONSTRAINT accounting_sale_product_id_1eec5171_fk_operating_product_id FOREIGN KEY (product_id) REFERENCES public.operating_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_stakeholder_books accounting_stakehold_book_id_f8016a55_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholder_books
    ADD CONSTRAINT accounting_stakehold_book_id_f8016a55_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_stakeholder_books accounting_stakehold_stakeholder_id_a2305ace_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholder_books
    ADD CONSTRAINT accounting_stakehold_stakeholder_id_a2305ace_fk_accountin FOREIGN KEY (stakeholder_id) REFERENCES public.accounting_stakeholder(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_member authentication_member_user_id_af273d22_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member
    ADD CONSTRAINT authentication_member_user_id_af273d22_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crm_contact crm_contact_company_id_5104bcf2_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_contact
    ADD CONSTRAINT crm_contact_company_id_5104bcf2_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crm_note crm_note_company_id_9ceedb83_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_note
    ADD CONSTRAINT crm_note_company_id_9ceedb83_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: crm_note crm_note_contact_id_8d258ea9_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_note
    ADD CONSTRAINT crm_note_contact_id_8d258ea9_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_product_raw_materials operating_product_ra_product_id_3dfc607e_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product_raw_materials
    ADD CONSTRAINT operating_product_ra_product_id_3dfc607e_fk_operating FOREIGN KEY (product_id) REFERENCES public.operating_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_product_raw_materials operating_product_ra_rawmaterial_id_f0003e51_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product_raw_materials
    ADD CONSTRAINT operating_product_ra_rawmaterial_id_f0003e51_fk_operating FOREIGN KEY (rawmaterial_id) REFERENCES public.operating_rawmaterial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_product operating_product_unit_id_e80cf5d8_fk_operating_unitcategory_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_product
    ADD CONSTRAINT operating_product_unit_id_e80cf5d8_fk_operating_unitcategory_id FOREIGN KEY (unit_id) REFERENCES public.operating_unitcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_rawmaterial_supplierCompany operating_rawmateria_company_id_8c97abaa_fk_crm_compa; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierCompany"
    ADD CONSTRAINT operating_rawmateria_company_id_8c97abaa_fk_crm_compa FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_rawmaterial_supplierContact operating_rawmateria_contact_id_5bd68355_fk_crm_conta; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierContact"
    ADD CONSTRAINT operating_rawmateria_contact_id_5bd68355_fk_crm_conta FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_rawmaterial_supplierCompany operating_rawmateria_rawmaterial_id_32c6a12b_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierCompany"
    ADD CONSTRAINT operating_rawmateria_rawmaterial_id_32c6a12b_fk_operating FOREIGN KEY (rawmaterial_id) REFERENCES public.operating_rawmaterial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_rawmaterial_supplierContact operating_rawmateria_rawmaterial_id_44202a26_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."operating_rawmaterial_supplierContact"
    ADD CONSTRAINT operating_rawmateria_rawmaterial_id_44202a26_fk_operating FOREIGN KEY (rawmaterial_id) REFERENCES public.operating_rawmaterial(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_rawmaterial operating_rawmateria_type_id_7bda2e97_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_rawmaterial
    ADD CONSTRAINT operating_rawmateria_type_id_7bda2e97_fk_operating FOREIGN KEY (type_id) REFERENCES public.operating_rawmaterialcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: todo_task todo_task_company_id_fed9e4bc_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.todo_task
    ADD CONSTRAINT todo_task_company_id_fed9e4bc_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: todo_task todo_task_contact_id_4691b54e_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.todo_task
    ADD CONSTRAINT todo_task_contact_id_4691b54e_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: objects objects_bucketId_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.objects
    ADD CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads s3_multipart_uploads_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads
    ADD CONSTRAINT s3_multipart_uploads_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_bucket_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_bucket_id_fkey FOREIGN KEY (bucket_id) REFERENCES storage.buckets(id);


--
-- Name: s3_multipart_uploads_parts s3_multipart_uploads_parts_upload_id_fkey; Type: FK CONSTRAINT; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE ONLY storage.s3_multipart_uploads_parts
    ADD CONSTRAINT s3_multipart_uploads_parts_upload_id_fkey FOREIGN KEY (upload_id) REFERENCES storage.s3_multipart_uploads(id) ON DELETE CASCADE;


--
-- Name: audit_log_entries; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.audit_log_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: flow_state; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.flow_state ENABLE ROW LEVEL SECURITY;

--
-- Name: identities; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.identities ENABLE ROW LEVEL SECURITY;

--
-- Name: instances; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.instances ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_amr_claims; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_amr_claims ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_challenges; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_challenges ENABLE ROW LEVEL SECURITY;

--
-- Name: mfa_factors; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.mfa_factors ENABLE ROW LEVEL SECURITY;

--
-- Name: one_time_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.one_time_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: refresh_tokens; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.refresh_tokens ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.saml_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: saml_relay_states; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.saml_relay_states ENABLE ROW LEVEL SECURITY;

--
-- Name: schema_migrations; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.schema_migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: sessions; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_domains; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sso_domains ENABLE ROW LEVEL SECURITY;

--
-- Name: sso_providers; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.sso_providers ENABLE ROW LEVEL SECURITY;

--
-- Name: users; Type: ROW SECURITY; Schema: auth; Owner: supabase_auth_admin
--

ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

--
-- Name: messages; Type: ROW SECURITY; Schema: realtime; Owner: supabase_realtime_admin
--

ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY;

--
-- Name: buckets; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;

--
-- Name: migrations; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.migrations ENABLE ROW LEVEL SECURITY;

--
-- Name: objects; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.s3_multipart_uploads ENABLE ROW LEVEL SECURITY;

--
-- Name: s3_multipart_uploads_parts; Type: ROW SECURITY; Schema: storage; Owner: supabase_storage_admin
--

ALTER TABLE storage.s3_multipart_uploads_parts ENABLE ROW LEVEL SECURITY;

--
-- Name: supabase_realtime; Type: PUBLICATION; Schema: -; Owner: postgres
--

CREATE PUBLICATION supabase_realtime WITH (publish = 'insert, update, delete, truncate');


ALTER PUBLICATION supabase_realtime OWNER TO postgres;

--
-- Name: SCHEMA auth; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA auth TO anon;
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT USAGE ON SCHEMA auth TO service_role;
GRANT ALL ON SCHEMA auth TO supabase_auth_admin;
GRANT ALL ON SCHEMA auth TO dashboard_user;
GRANT ALL ON SCHEMA auth TO postgres;


--
-- Name: SCHEMA extensions; Type: ACL; Schema: -; Owner: postgres
--

GRANT USAGE ON SCHEMA extensions TO anon;
GRANT USAGE ON SCHEMA extensions TO authenticated;
GRANT USAGE ON SCHEMA extensions TO service_role;
GRANT ALL ON SCHEMA extensions TO dashboard_user;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- Name: SCHEMA realtime; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT USAGE ON SCHEMA realtime TO postgres;
GRANT USAGE ON SCHEMA realtime TO anon;
GRANT USAGE ON SCHEMA realtime TO authenticated;
GRANT USAGE ON SCHEMA realtime TO service_role;
GRANT ALL ON SCHEMA realtime TO supabase_realtime_admin;


--
-- Name: SCHEMA storage; Type: ACL; Schema: -; Owner: supabase_admin
--

GRANT ALL ON SCHEMA storage TO postgres;
GRANT USAGE ON SCHEMA storage TO anon;
GRANT USAGE ON SCHEMA storage TO authenticated;
GRANT USAGE ON SCHEMA storage TO service_role;
GRANT ALL ON SCHEMA storage TO supabase_storage_admin;
GRANT ALL ON SCHEMA storage TO dashboard_user;


--
-- Name: FUNCTION email(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.email() TO dashboard_user;
GRANT ALL ON FUNCTION auth.email() TO postgres;


--
-- Name: FUNCTION jwt(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.jwt() TO postgres;
GRANT ALL ON FUNCTION auth.jwt() TO dashboard_user;


--
-- Name: FUNCTION role(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.role() TO dashboard_user;
GRANT ALL ON FUNCTION auth.role() TO postgres;


--
-- Name: FUNCTION uid(); Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON FUNCTION auth.uid() TO dashboard_user;
GRANT ALL ON FUNCTION auth.uid() TO postgres;


--
-- Name: FUNCTION algorithm_sign(signables text, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.algorithm_sign(signables text, secret text, algorithm text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.algorithm_sign(signables text, secret text, algorithm text) TO dashboard_user;


--
-- Name: FUNCTION armor(bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.armor(bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.armor(bytea) TO dashboard_user;


--
-- Name: FUNCTION armor(bytea, text[], text[]); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.armor(bytea, text[], text[]) TO dashboard_user;


--
-- Name: FUNCTION crypt(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.crypt(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.crypt(text, text) TO dashboard_user;


--
-- Name: FUNCTION dearmor(text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.dearmor(text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.dearmor(text) TO dashboard_user;


--
-- Name: FUNCTION decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.decrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION decrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.decrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION digest(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.digest(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION digest(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.digest(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.digest(text, text) TO dashboard_user;


--
-- Name: FUNCTION encrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.encrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION encrypt_iv(bytea, bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.encrypt_iv(bytea, bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION gen_random_bytes(integer); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_random_bytes(integer) TO dashboard_user;


--
-- Name: FUNCTION gen_random_uuid(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_random_uuid() TO dashboard_user;


--
-- Name: FUNCTION gen_salt(text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_salt(text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_salt(text) TO dashboard_user;


--
-- Name: FUNCTION gen_salt(text, integer); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.gen_salt(text, integer) TO dashboard_user;


--
-- Name: FUNCTION grant_pg_cron_access(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION extensions.grant_pg_cron_access() FROM postgres;
GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.grant_pg_cron_access() TO dashboard_user;


--
-- Name: FUNCTION grant_pg_graphql_access(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.grant_pg_graphql_access() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION grant_pg_net_access(); Type: ACL; Schema: extensions; Owner: postgres
--

REVOKE ALL ON FUNCTION extensions.grant_pg_net_access() FROM postgres;
GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.grant_pg_net_access() TO dashboard_user;


--
-- Name: FUNCTION hmac(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.hmac(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION hmac(text, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.hmac(text, text, text) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO dashboard_user;


--
-- Name: FUNCTION pg_stat_statements_reset(userid oid, dbid oid, queryid bigint); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint) TO dashboard_user;


--
-- Name: FUNCTION pgp_armor_headers(text, OUT key text, OUT value text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_armor_headers(text, OUT key text, OUT value text) TO dashboard_user;


--
-- Name: FUNCTION pgp_key_id(bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_key_id(bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt(bytea, bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_decrypt_bytea(bytea, bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_decrypt_bytea(bytea, bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt(text, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt(text, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea) TO dashboard_user;


--
-- Name: FUNCTION pgp_pub_encrypt_bytea(bytea, bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_pub_encrypt_bytea(bytea, bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_decrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_decrypt_bytea(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt(text, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt(text, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text) TO dashboard_user;


--
-- Name: FUNCTION pgp_sym_encrypt_bytea(bytea, text, text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.pgp_sym_encrypt_bytea(bytea, text, text) TO dashboard_user;


--
-- Name: FUNCTION pgrst_ddl_watch(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgrst_ddl_watch() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION pgrst_drop_watch(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.pgrst_drop_watch() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION set_graphql_placeholder(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.set_graphql_placeholder() TO postgres WITH GRANT OPTION;


--
-- Name: FUNCTION sign(payload json, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.sign(payload json, secret text, algorithm text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.sign(payload json, secret text, algorithm text) TO dashboard_user;


--
-- Name: FUNCTION try_cast_double(inp text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.try_cast_double(inp text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.try_cast_double(inp text) TO dashboard_user;


--
-- Name: FUNCTION url_decode(data text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.url_decode(data text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.url_decode(data text) TO dashboard_user;


--
-- Name: FUNCTION url_encode(data bytea); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.url_encode(data bytea) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.url_encode(data bytea) TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v1(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v1mc(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v1mc() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v3(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v3(namespace uuid, name text) TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v4(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v4() TO dashboard_user;


--
-- Name: FUNCTION uuid_generate_v5(namespace uuid, name text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_generate_v5(namespace uuid, name text) TO dashboard_user;


--
-- Name: FUNCTION uuid_nil(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_nil() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_nil() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_dns(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_dns() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_oid(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_oid() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_url(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_url() TO dashboard_user;


--
-- Name: FUNCTION uuid_ns_x500(); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.uuid_ns_x500() TO dashboard_user;


--
-- Name: FUNCTION verify(token text, secret text, algorithm text); Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON FUNCTION extensions.verify(token text, secret text, algorithm text) TO postgres WITH GRANT OPTION;
GRANT ALL ON FUNCTION extensions.verify(token text, secret text, algorithm text) TO dashboard_user;


--
-- Name: FUNCTION comment_directive(comment_ text); Type: ACL; Schema: graphql; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql.comment_directive(comment_ text) TO postgres;
GRANT ALL ON FUNCTION graphql.comment_directive(comment_ text) TO anon;
GRANT ALL ON FUNCTION graphql.comment_directive(comment_ text) TO authenticated;
GRANT ALL ON FUNCTION graphql.comment_directive(comment_ text) TO service_role;


--
-- Name: FUNCTION exception(message text); Type: ACL; Schema: graphql; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql.exception(message text) TO postgres;
GRANT ALL ON FUNCTION graphql.exception(message text) TO anon;
GRANT ALL ON FUNCTION graphql.exception(message text) TO authenticated;
GRANT ALL ON FUNCTION graphql.exception(message text) TO service_role;


--
-- Name: FUNCTION get_schema_version(); Type: ACL; Schema: graphql; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql.get_schema_version() TO postgres;
GRANT ALL ON FUNCTION graphql.get_schema_version() TO anon;
GRANT ALL ON FUNCTION graphql.get_schema_version() TO authenticated;
GRANT ALL ON FUNCTION graphql.get_schema_version() TO service_role;


--
-- Name: FUNCTION increment_schema_version(); Type: ACL; Schema: graphql; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql.increment_schema_version() TO postgres;
GRANT ALL ON FUNCTION graphql.increment_schema_version() TO anon;
GRANT ALL ON FUNCTION graphql.increment_schema_version() TO authenticated;
GRANT ALL ON FUNCTION graphql.increment_schema_version() TO service_role;


--
-- Name: FUNCTION graphql("operationName" text, query text, variables jsonb, extensions jsonb); Type: ACL; Schema: graphql_public; Owner: supabase_admin
--

GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO postgres;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO anon;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO authenticated;
GRANT ALL ON FUNCTION graphql_public.graphql("operationName" text, query text, variables jsonb, extensions jsonb) TO service_role;


--
-- Name: FUNCTION lo_export(oid, text); Type: ACL; Schema: pg_catalog; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION pg_catalog.lo_export(oid, text) FROM postgres;
GRANT ALL ON FUNCTION pg_catalog.lo_export(oid, text) TO supabase_admin;


--
-- Name: FUNCTION lo_import(text); Type: ACL; Schema: pg_catalog; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION pg_catalog.lo_import(text) FROM postgres;
GRANT ALL ON FUNCTION pg_catalog.lo_import(text) TO supabase_admin;


--
-- Name: FUNCTION lo_import(text, oid); Type: ACL; Schema: pg_catalog; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION pg_catalog.lo_import(text, oid) FROM postgres;
GRANT ALL ON FUNCTION pg_catalog.lo_import(text, oid) TO supabase_admin;


--
-- Name: FUNCTION get_auth(p_usename text); Type: ACL; Schema: pgbouncer; Owner: postgres
--

REVOKE ALL ON FUNCTION pgbouncer.get_auth(p_usename text) FROM PUBLIC;
GRANT ALL ON FUNCTION pgbouncer.get_auth(p_usename text) TO pgbouncer;


--
-- Name: FUNCTION crypto_aead_det_decrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea); Type: ACL; Schema: pgsodium; Owner: pgsodium_keymaker
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_decrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea) TO service_role;


--
-- Name: FUNCTION crypto_aead_det_encrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea); Type: ACL; Schema: pgsodium; Owner: pgsodium_keymaker
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_encrypt(message bytea, additional bytea, key_uuid uuid, nonce bytea) TO service_role;


--
-- Name: FUNCTION crypto_aead_det_keygen(); Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON FUNCTION pgsodium.crypto_aead_det_keygen() TO service_role;


--
-- Name: FUNCTION apply_rls(wal jsonb, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO postgres;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO anon;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO authenticated;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO service_role;
GRANT ALL ON FUNCTION realtime.apply_rls(wal jsonb, max_record_bytes integer) TO supabase_realtime_admin;


--
-- Name: FUNCTION broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO postgres;
GRANT ALL ON FUNCTION realtime.broadcast_changes(topic_name text, event_name text, operation text, table_name text, table_schema text, new record, old record, level text) TO dashboard_user;


--
-- Name: FUNCTION build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO postgres;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO anon;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO authenticated;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO service_role;
GRANT ALL ON FUNCTION realtime.build_prepared_statement_sql(prepared_statement_name text, entity regclass, columns realtime.wal_column[]) TO supabase_realtime_admin;


--
-- Name: FUNCTION "cast"(val text, type_ regtype); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO postgres;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO dashboard_user;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO anon;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO authenticated;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO service_role;
GRANT ALL ON FUNCTION realtime."cast"(val text, type_ regtype) TO supabase_realtime_admin;


--
-- Name: FUNCTION check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO postgres;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO anon;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO authenticated;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO service_role;
GRANT ALL ON FUNCTION realtime.check_equality_op(op realtime.equality_op, type_ regtype, val_1 text, val_2 text) TO supabase_realtime_admin;


--
-- Name: FUNCTION is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO postgres;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO anon;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO authenticated;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO service_role;
GRANT ALL ON FUNCTION realtime.is_visible_through_filters(columns realtime.wal_column[], filters realtime.user_defined_filter[]) TO supabase_realtime_admin;


--
-- Name: FUNCTION list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO postgres;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO anon;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO authenticated;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO service_role;
GRANT ALL ON FUNCTION realtime.list_changes(publication name, slot_name name, max_changes integer, max_record_bytes integer) TO supabase_realtime_admin;


--
-- Name: FUNCTION quote_wal2json(entity regclass); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO postgres;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO anon;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO authenticated;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO service_role;
GRANT ALL ON FUNCTION realtime.quote_wal2json(entity regclass) TO supabase_realtime_admin;


--
-- Name: FUNCTION send(payload jsonb, event text, topic text, private boolean); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO postgres;
GRANT ALL ON FUNCTION realtime.send(payload jsonb, event text, topic text, private boolean) TO dashboard_user;


--
-- Name: FUNCTION subscription_check_filters(); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO postgres;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO dashboard_user;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO anon;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO authenticated;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO service_role;
GRANT ALL ON FUNCTION realtime.subscription_check_filters() TO supabase_realtime_admin;


--
-- Name: FUNCTION to_regrole(role_name text); Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO postgres;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO dashboard_user;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO anon;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO authenticated;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO service_role;
GRANT ALL ON FUNCTION realtime.to_regrole(role_name text) TO supabase_realtime_admin;


--
-- Name: FUNCTION topic(); Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON FUNCTION realtime.topic() TO postgres;
GRANT ALL ON FUNCTION realtime.topic() TO dashboard_user;


--
-- Name: FUNCTION can_insert_object(bucketid text, name text, owner uuid, metadata jsonb); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.can_insert_object(bucketid text, name text, owner uuid, metadata jsonb) TO postgres;


--
-- Name: FUNCTION extension(name text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.extension(name text) TO anon;
GRANT ALL ON FUNCTION storage.extension(name text) TO authenticated;
GRANT ALL ON FUNCTION storage.extension(name text) TO service_role;
GRANT ALL ON FUNCTION storage.extension(name text) TO dashboard_user;
GRANT ALL ON FUNCTION storage.extension(name text) TO postgres;


--
-- Name: FUNCTION filename(name text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.filename(name text) TO anon;
GRANT ALL ON FUNCTION storage.filename(name text) TO authenticated;
GRANT ALL ON FUNCTION storage.filename(name text) TO service_role;
GRANT ALL ON FUNCTION storage.filename(name text) TO dashboard_user;
GRANT ALL ON FUNCTION storage.filename(name text) TO postgres;


--
-- Name: FUNCTION foldername(name text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.foldername(name text) TO anon;
GRANT ALL ON FUNCTION storage.foldername(name text) TO authenticated;
GRANT ALL ON FUNCTION storage.foldername(name text) TO service_role;
GRANT ALL ON FUNCTION storage.foldername(name text) TO dashboard_user;
GRANT ALL ON FUNCTION storage.foldername(name text) TO postgres;


--
-- Name: FUNCTION get_size_by_bucket(); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.get_size_by_bucket() TO postgres;


--
-- Name: FUNCTION list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, next_key_token text, next_upload_token text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.list_multipart_uploads_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, next_key_token text, next_upload_token text) TO postgres;


--
-- Name: FUNCTION list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, start_after text, next_token text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.list_objects_with_delimiter(bucket_id text, prefix_param text, delimiter_param text, max_keys integer, start_after text, next_token text) TO postgres;


--
-- Name: FUNCTION operation(); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.operation() TO postgres;


--
-- Name: FUNCTION search(prefix text, bucketname text, limits integer, levels integer, offsets integer, search text, sortcolumn text, sortorder text); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.search(prefix text, bucketname text, limits integer, levels integer, offsets integer, search text, sortcolumn text, sortorder text) TO postgres;


--
-- Name: FUNCTION update_updated_at_column(); Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON FUNCTION storage.update_updated_at_column() TO postgres;


--
-- Name: TABLE audit_log_entries; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.audit_log_entries TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.audit_log_entries TO postgres;
GRANT SELECT ON TABLE auth.audit_log_entries TO postgres WITH GRANT OPTION;


--
-- Name: TABLE flow_state; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.flow_state TO postgres;
GRANT SELECT ON TABLE auth.flow_state TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.flow_state TO dashboard_user;


--
-- Name: TABLE identities; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.identities TO postgres;
GRANT SELECT ON TABLE auth.identities TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.identities TO dashboard_user;


--
-- Name: TABLE instances; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.instances TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.instances TO postgres;
GRANT SELECT ON TABLE auth.instances TO postgres WITH GRANT OPTION;


--
-- Name: TABLE mfa_amr_claims; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_amr_claims TO postgres;
GRANT SELECT ON TABLE auth.mfa_amr_claims TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_amr_claims TO dashboard_user;


--
-- Name: TABLE mfa_challenges; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_challenges TO postgres;
GRANT SELECT ON TABLE auth.mfa_challenges TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_challenges TO dashboard_user;


--
-- Name: TABLE mfa_factors; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.mfa_factors TO postgres;
GRANT SELECT ON TABLE auth.mfa_factors TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.mfa_factors TO dashboard_user;


--
-- Name: TABLE one_time_tokens; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.one_time_tokens TO postgres;
GRANT SELECT ON TABLE auth.one_time_tokens TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.one_time_tokens TO dashboard_user;


--
-- Name: TABLE refresh_tokens; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.refresh_tokens TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.refresh_tokens TO postgres;
GRANT SELECT ON TABLE auth.refresh_tokens TO postgres WITH GRANT OPTION;


--
-- Name: SEQUENCE refresh_tokens_id_seq; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO dashboard_user;
GRANT ALL ON SEQUENCE auth.refresh_tokens_id_seq TO postgres;


--
-- Name: TABLE saml_providers; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.saml_providers TO postgres;
GRANT SELECT ON TABLE auth.saml_providers TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.saml_providers TO dashboard_user;


--
-- Name: TABLE saml_relay_states; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.saml_relay_states TO postgres;
GRANT SELECT ON TABLE auth.saml_relay_states TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.saml_relay_states TO dashboard_user;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.schema_migrations TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.schema_migrations TO postgres;
GRANT SELECT ON TABLE auth.schema_migrations TO postgres WITH GRANT OPTION;


--
-- Name: TABLE sessions; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sessions TO postgres;
GRANT SELECT ON TABLE auth.sessions TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sessions TO dashboard_user;


--
-- Name: TABLE sso_domains; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sso_domains TO postgres;
GRANT SELECT ON TABLE auth.sso_domains TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sso_domains TO dashboard_user;


--
-- Name: TABLE sso_providers; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.sso_providers TO postgres;
GRANT SELECT ON TABLE auth.sso_providers TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE auth.sso_providers TO dashboard_user;


--
-- Name: TABLE users; Type: ACL; Schema: auth; Owner: supabase_auth_admin
--

GRANT ALL ON TABLE auth.users TO dashboard_user;
GRANT INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE auth.users TO postgres;
GRANT SELECT ON TABLE auth.users TO postgres WITH GRANT OPTION;


--
-- Name: TABLE pg_stat_statements; Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON TABLE extensions.pg_stat_statements TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE extensions.pg_stat_statements TO dashboard_user;


--
-- Name: TABLE pg_stat_statements_info; Type: ACL; Schema: extensions; Owner: supabase_admin
--

GRANT ALL ON TABLE extensions.pg_stat_statements_info TO postgres WITH GRANT OPTION;
GRANT ALL ON TABLE extensions.pg_stat_statements_info TO dashboard_user;


--
-- Name: SEQUENCE seq_schema_version; Type: ACL; Schema: graphql; Owner: supabase_admin
--

GRANT ALL ON SEQUENCE graphql.seq_schema_version TO postgres;
GRANT ALL ON SEQUENCE graphql.seq_schema_version TO anon;
GRANT ALL ON SEQUENCE graphql.seq_schema_version TO authenticated;
GRANT ALL ON SEQUENCE graphql.seq_schema_version TO service_role;


--
-- Name: TABLE decrypted_key; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.decrypted_key TO pgsodium_keyholder;


--
-- Name: TABLE masking_rule; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.masking_rule TO pgsodium_keyholder;


--
-- Name: TABLE mask_columns; Type: ACL; Schema: pgsodium; Owner: supabase_admin
--

GRANT ALL ON TABLE pgsodium.mask_columns TO pgsodium_keyholder;


--
-- Name: TABLE messages; Type: ACL; Schema: realtime; Owner: supabase_realtime_admin
--

GRANT ALL ON TABLE realtime.messages TO postgres;
GRANT ALL ON TABLE realtime.messages TO dashboard_user;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO anon;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO authenticated;
GRANT SELECT,INSERT,UPDATE ON TABLE realtime.messages TO service_role;


--
-- Name: TABLE schema_migrations; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.schema_migrations TO postgres;
GRANT ALL ON TABLE realtime.schema_migrations TO dashboard_user;
GRANT SELECT ON TABLE realtime.schema_migrations TO anon;
GRANT SELECT ON TABLE realtime.schema_migrations TO authenticated;
GRANT SELECT ON TABLE realtime.schema_migrations TO service_role;
GRANT ALL ON TABLE realtime.schema_migrations TO supabase_realtime_admin;


--
-- Name: TABLE subscription; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON TABLE realtime.subscription TO postgres;
GRANT ALL ON TABLE realtime.subscription TO dashboard_user;
GRANT SELECT ON TABLE realtime.subscription TO anon;
GRANT SELECT ON TABLE realtime.subscription TO authenticated;
GRANT SELECT ON TABLE realtime.subscription TO service_role;
GRANT ALL ON TABLE realtime.subscription TO supabase_realtime_admin;


--
-- Name: SEQUENCE subscription_id_seq; Type: ACL; Schema: realtime; Owner: supabase_admin
--

GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO postgres;
GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO dashboard_user;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO anon;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE realtime.subscription_id_seq TO service_role;
GRANT ALL ON SEQUENCE realtime.subscription_id_seq TO supabase_realtime_admin;


--
-- Name: TABLE buckets; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.buckets TO anon;
GRANT ALL ON TABLE storage.buckets TO authenticated;
GRANT ALL ON TABLE storage.buckets TO service_role;
GRANT ALL ON TABLE storage.buckets TO postgres;


--
-- Name: TABLE migrations; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.migrations TO anon;
GRANT ALL ON TABLE storage.migrations TO authenticated;
GRANT ALL ON TABLE storage.migrations TO service_role;
GRANT ALL ON TABLE storage.migrations TO postgres;


--
-- Name: TABLE objects; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.objects TO anon;
GRANT ALL ON TABLE storage.objects TO authenticated;
GRANT ALL ON TABLE storage.objects TO service_role;
GRANT ALL ON TABLE storage.objects TO postgres;


--
-- Name: TABLE s3_multipart_uploads; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.s3_multipart_uploads TO service_role;
GRANT SELECT ON TABLE storage.s3_multipart_uploads TO authenticated;
GRANT SELECT ON TABLE storage.s3_multipart_uploads TO anon;
GRANT ALL ON TABLE storage.s3_multipart_uploads TO postgres;


--
-- Name: TABLE s3_multipart_uploads_parts; Type: ACL; Schema: storage; Owner: supabase_storage_admin
--

GRANT ALL ON TABLE storage.s3_multipart_uploads_parts TO service_role;
GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO authenticated;
GRANT SELECT ON TABLE storage.s3_multipart_uploads_parts TO anon;
GRANT ALL ON TABLE storage.s3_multipart_uploads_parts TO postgres;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON SEQUENCES  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON FUNCTIONS  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: auth; Owner: supabase_auth_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_auth_admin IN SCHEMA auth GRANT ALL ON TABLES  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON SEQUENCES  TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON FUNCTIONS  TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: extensions; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA extensions GRANT ALL ON TABLES  TO postgres WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON SEQUENCES  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON FUNCTIONS  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql GRANT ALL ON TABLES  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON SEQUENCES  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON FUNCTIONS  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: graphql_public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA graphql_public GRANT ALL ON TABLES  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: pgsodium; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium GRANT ALL ON SEQUENCES  TO pgsodium_keyholder;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: pgsodium; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium GRANT ALL ON TABLES  TO pgsodium_keyholder;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON SEQUENCES  TO pgsodium_keyiduser;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON FUNCTIONS  TO pgsodium_keyiduser;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: pgsodium_masks; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA pgsodium_masks GRANT ALL ON TABLES  TO pgsodium_keyiduser;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON SEQUENCES  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON FUNCTIONS  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: realtime; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA realtime GRANT ALL ON TABLES  TO dashboard_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON SEQUENCES  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON FUNCTIONS  TO service_role;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: storage; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA storage GRANT ALL ON TABLES  TO service_role;


--
-- Name: issue_graphql_placeholder; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_graphql_placeholder ON sql_drop
         WHEN TAG IN ('DROP EXTENSION')
   EXECUTE FUNCTION extensions.set_graphql_placeholder();


ALTER EVENT TRIGGER issue_graphql_placeholder OWNER TO supabase_admin;

--
-- Name: issue_pg_cron_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_pg_cron_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_cron_access();


ALTER EVENT TRIGGER issue_pg_cron_access OWNER TO supabase_admin;

--
-- Name: issue_pg_graphql_access; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER issue_pg_graphql_access ON ddl_command_end
         WHEN TAG IN ('CREATE FUNCTION')
   EXECUTE FUNCTION extensions.grant_pg_graphql_access();


ALTER EVENT TRIGGER issue_pg_graphql_access OWNER TO supabase_admin;

--
-- Name: issue_pg_net_access; Type: EVENT TRIGGER; Schema: -; Owner: postgres
--

CREATE EVENT TRIGGER issue_pg_net_access ON ddl_command_end
         WHEN TAG IN ('CREATE EXTENSION')
   EXECUTE FUNCTION extensions.grant_pg_net_access();


ALTER EVENT TRIGGER issue_pg_net_access OWNER TO postgres;

--
-- Name: pgrst_ddl_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER pgrst_ddl_watch ON ddl_command_end
   EXECUTE FUNCTION extensions.pgrst_ddl_watch();


ALTER EVENT TRIGGER pgrst_ddl_watch OWNER TO supabase_admin;

--
-- Name: pgrst_drop_watch; Type: EVENT TRIGGER; Schema: -; Owner: supabase_admin
--

CREATE EVENT TRIGGER pgrst_drop_watch ON sql_drop
   EXECUTE FUNCTION extensions.pgrst_drop_watch();


ALTER EVENT TRIGGER pgrst_drop_watch OWNER TO supabase_admin;

--
-- PostgreSQL database dump complete
--

