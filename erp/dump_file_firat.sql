--
-- PostgreSQL database dump
--

-- Dumped from database version 15.6
-- Dumped by pg_dump version 15.13 (Homebrew)

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

      IF EXISTS (
        SELECT FROM pg_extension
        WHERE extname = 'pg_net'
        -- all versions in use on existing projects as of 2025-02-20
        -- version 0.12.0 onwards don't need these applied
        AND extversion IN ('0.2', '0.6', '0.7', '0.7.1', '0.8.0', '0.10.0', '0.11.0')
      ) THEN
        ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;
        ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SECURITY DEFINER;

        ALTER function net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;
        ALTER function net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) SET search_path = net;

        REVOKE ALL ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;
        REVOKE ALL ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) FROM PUBLIC;

        GRANT EXECUTE ON FUNCTION net.http_get(url text, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
        GRANT EXECUTE ON FUNCTION net.http_post(url text, body jsonb, params jsonb, headers jsonb, timeout_milliseconds integer) TO supabase_functions_admin, postgres, anon, authenticated, service_role;
      END IF;
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
-- Name: get_auth(text); Type: FUNCTION; Schema: pgbouncer; Owner: supabase_admin
--

CREATE FUNCTION pgbouncer.get_auth(p_usename text) RETURNS TABLE(username text, password text)
    LANGUAGE plpgsql SECURITY DEFINER
    AS $_$
  BEGIN
      RAISE DEBUG 'PgBouncer auth request: %', p_usename;

      RETURN QUERY
      SELECT
          rolname::text,
          CASE WHEN rolvaliduntil < now()
              THEN null
              ELSE rolpassword::text
          END
      FROM pg_authid
      WHERE rolname=$1 and rolcanlogin;
  END;
  $_$;


ALTER FUNCTION pgbouncer.get_auth(p_usename text) OWNER TO supabase_admin;

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
BEGIN
  BEGIN
    -- Set the topic configuration
    EXECUTE format('SET LOCAL realtime.topic TO %L', topic);

    -- Attempt to insert the message
    INSERT INTO realtime.messages (payload, event, topic, private, extension)
    VALUES (payload, event, topic, private, 'broadcast');
  EXCEPTION
    WHEN OTHERS THEN
      -- Capture and notify the error
      PERFORM pg_notify(
          'realtime:system',
          jsonb_build_object(
              'error', SQLERRM,
              'function', 'realtime.send',
              'event', event,
              'topic', topic,
              'private', private
          )::text
      );
  END;
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
-- Name: accounting_assetaccountsreceivable; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_assetaccountsreceivable (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    book_id bigint NOT NULL,
    company_id bigint,
    contact_id bigint,
    currency_id bigint NOT NULL,
    invoice_id bigint
);


ALTER TABLE public.accounting_assetaccountsreceivable OWNER TO postgres;

--
-- Name: accounting_assetaccountsreceivable_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_assetaccountsreceivable ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_assetaccountsreceivable_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_assetcash; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_assetcash (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    currency_balance numeric(10,2),
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL,
    transaction_id bigint
);


ALTER TABLE public.accounting_assetcash OWNER TO postgres;

--
-- Name: accounting_assetcash_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_assetcash ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_assetcash_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_assetinventorygood; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_assetinventorygood (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    modified_at date,
    name character varying(300) NOT NULL,
    unit_cost numeric(10,2) NOT NULL,
    quantity numeric(12,2) NOT NULL,
    stock_type character varying,
    status character varying NOT NULL,
    warehouse character varying,
    location character varying,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_assetinventorygood OWNER TO postgres;

--
-- Name: accounting_assetinventorygood_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_assetinventorygood ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_assetinventorygood_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_assetinventoryrawmaterial; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_assetinventoryrawmaterial (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name character varying NOT NULL,
    stock_id character varying,
    receipt_number character varying,
    unit_of_measurement character varying,
    unit_cost numeric(10,2) NOT NULL,
    quantity numeric(12,2) NOT NULL,
    warehouse character varying,
    location character varying,
    raw_type character varying NOT NULL,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL,
    supplier_id bigint
);


ALTER TABLE public.accounting_assetinventoryrawmaterial OWNER TO postgres;

--
-- Name: accounting_assetinventoryrawmaterial_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_assetinventoryrawmaterial ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_assetinventoryrawmaterial_id_seq
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
    name character varying(50) NOT NULL,
    total_shares integer NOT NULL,
    CONSTRAINT accounting_book_total_shares_check CHECK ((total_shares >= 0))
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
    name character varying(50) NOT NULL,
    balance numeric(10,2) NOT NULL,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_cashaccount OWNER TO postgres;

--
-- Name: accounting_cashaccount_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_cashaccount ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_cashaccount_id_seq
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
-- Name: accounting_currencyexchange; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_currencyexchange (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    from_amount numeric(10,2) NOT NULL,
    to_amount numeric(10,2) NOT NULL,
    date date,
    book_id bigint NOT NULL,
    from_cash_account_id bigint NOT NULL,
    to_cash_account_id bigint NOT NULL
);


ALTER TABLE public.accounting_currencyexchange OWNER TO postgres;

--
-- Name: accounting_currencyexchange_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_currencyexchange ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_currencyexchange_id_seq
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
    date_invested date NOT NULL,
    amount numeric(10,2) NOT NULL,
    new_shares_issued integer NOT NULL,
    note text,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    currency_id bigint,
    member_id bigint NOT NULL,
    CONSTRAINT accounting_equitycapital_new_shares_issued_check CHECK ((new_shares_issued >= 0))
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
    member_id bigint
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
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    category_id bigint,
    currency_id bigint NOT NULL
);


ALTER TABLE public.accounting_equityexpense OWNER TO postgres;

--
-- Name: accounting_equityexpense_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_equityexpense ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_equityexpense_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_equityrevenue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_equityrevenue (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date NOT NULL,
    description character varying(200) NOT NULL,
    invoice_number character varying(20),
    revenue_type character varying NOT NULL,
    book_id bigint NOT NULL,
    cash_account_id bigint NOT NULL,
    currency_id bigint
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
-- Name: accounting_intransfer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_intransfer (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    date date,
    description character varying(200),
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL,
    destination_id bigint NOT NULL,
    source_id bigint NOT NULL
);


ALTER TABLE public.accounting_intransfer OWNER TO postgres;

--
-- Name: accounting_intransfer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_intransfer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_intransfer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_invoice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_invoice (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    due_cate timestamp with time zone NOT NULL,
    invoice_type character varying NOT NULL,
    total numeric(10,2) NOT NULL,
    paid numeric(10,2) NOT NULL,
    book_id bigint NOT NULL,
    company_id bigint,
    contact_id bigint,
    order_id bigint
);


ALTER TABLE public.accounting_invoice OWNER TO postgres;

--
-- Name: accounting_invoice_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_invoice ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_invoice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_liabilityaccountspayable; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_liabilityaccountspayable (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    amount numeric(10,2) NOT NULL,
    receipt character varying,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL,
    supplier_id bigint
);


ALTER TABLE public.accounting_liabilityaccountspayable OWNER TO postgres;

--
-- Name: accounting_liabilityaccountspayable_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_liabilityaccountspayable ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_liabilityaccountspayable_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_metric; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_metric (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    balance numeric(12,2) NOT NULL,
    money_in numeric(12,2) NOT NULL,
    money_out numeric(12,2) NOT NULL,
    burn numeric(12,2) NOT NULL,
    inventory numeric(12,2) NOT NULL,
    accounts_receivable numeric(12,2) NOT NULL,
    accounts_payable numeric(12,2) NOT NULL,
    runway numeric(12,1) NOT NULL,
    growth_rate numeric(12,1) NOT NULL,
    default_alive boolean NOT NULL,
    book_id bigint
);


ALTER TABLE public.accounting_metric OWNER TO postgres;

--
-- Name: accounting_metric_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_metric ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_metric_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_stakeholderbook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_stakeholderbook (
    id bigint NOT NULL,
    shares integer NOT NULL,
    book_id bigint NOT NULL,
    member_id bigint,
    CONSTRAINT accounting_stakeholderbook_shares_check CHECK ((shares >= 0))
);


ALTER TABLE public.accounting_stakeholderbook OWNER TO postgres;

--
-- Name: accounting_stakeholderbook_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_stakeholderbook ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_stakeholderbook_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: accounting_transaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounting_transaction (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    value numeric(12,2) NOT NULL,
    type character varying(50),
    type_pk integer,
    account_balance numeric(12,2),
    account_id bigint,
    book_id bigint NOT NULL,
    currency_id bigint NOT NULL,
    CONSTRAINT accounting_transaction_type_pk_check CHECK ((type_pk >= 0))
);


ALTER TABLE public.accounting_transaction OWNER TO postgres;

--
-- Name: accounting_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.accounting_transaction ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.accounting_transaction_id_seq
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
-- Name: authentication_member_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_member_permissions (
    id bigint NOT NULL,
    member_id bigint NOT NULL,
    permission_id bigint NOT NULL
);


ALTER TABLE public.authentication_member_permissions OWNER TO postgres;

--
-- Name: authentication_member_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_member_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_member_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: authentication_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authentication_permission (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    description text
);


ALTER TABLE public.authentication_permission OWNER TO postgres;

--
-- Name: authentication_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.authentication_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.authentication_permission_id_seq
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
    name character varying(100) NOT NULL,
    email character varying(254) NOT NULL,
    "backgroundInfo" text NOT NULL,
    phone character varying(15) NOT NULL,
    website character varying(100) NOT NULL,
    address character varying(255) NOT NULL,
    country character varying(50) NOT NULL,
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
    name character varying(50) NOT NULL,
    email character varying(254) NOT NULL,
    phone character varying(15) NOT NULL,
    address text NOT NULL,
    country character varying(50) NOT NULL,
    birthday date,
    job_title character varying(25) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    company_id bigint,
    "backgroundInfo" text NOT NULL
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
    modified_date timestamp with time zone NOT NULL,
    company_id bigint,
    contact_id bigint
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
-- Name: crm_supplier; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crm_supplier (
    id bigint NOT NULL,
    company_name character varying(300),
    contact_name character varying(300),
    email character varying(254) NOT NULL,
    phone character varying(15) NOT NULL,
    website character varying(200) NOT NULL,
    address character varying(255) NOT NULL,
    country character varying(100) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.crm_supplier OWNER TO postgres;

--
-- Name: crm_supplier_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.crm_supplier ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.crm_supplier_id_seq
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
-- Name: marketing_product; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_product (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    sku character varying(12),
    barcode character varying(14),
    tags character varying(100)[],
    type character varying,
    unit_of_measurement character varying,
    quantity numeric(10,2),
    price numeric(10,2),
    featured boolean,
    selling_while_out_of_stock boolean,
    weight numeric(10,2),
    unit_of_weight character varying,
    category_id bigint,
    supplier_id bigint,
    datasheet_url character varying(200),
    minimum_inventory_level numeric(10,2),
    primary_image_id bigint
);


ALTER TABLE public.marketing_product OWNER TO postgres;

--
-- Name: marketing_product_collections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_product_collections (
    id bigint NOT NULL,
    product_id bigint NOT NULL,
    productcollection_id bigint NOT NULL
);


ALTER TABLE public.marketing_product_collections OWNER TO postgres;

--
-- Name: marketing_product_collections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_product_collections ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_product_collections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_product_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_product ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productcategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productcategory (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    name character varying(255),
    image character varying(200)
);


ALTER TABLE public.marketing_productcategory OWNER TO postgres;

--
-- Name: marketing_productcategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productcategory ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productcategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productcollection; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productcollection (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    title character varying(255),
    description text,
    image character varying(100)
);


ALTER TABLE public.marketing_productcollection OWNER TO postgres;

--
-- Name: marketing_productcollection_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productcollection ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productcollection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productfile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productfile (
    id bigint NOT NULL,
    product_id bigint,
    product_variant_id bigint,
    sequence integer NOT NULL,
    file_url character varying(200),
    is_primary boolean NOT NULL,
    file_path character varying(500),
    CONSTRAINT marketing_productfile_sequence_check CHECK ((sequence >= 0))
);


ALTER TABLE public.marketing_productfile OWNER TO postgres;

--
-- Name: marketing_productfile_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productfile ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productfile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productvariant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productvariant (
    id bigint NOT NULL,
    variant_sku character varying(12) NOT NULL,
    variant_barcode character varying(14),
    variant_quantity numeric(10,2),
    variant_price numeric(10,2),
    variant_cost numeric(10,2),
    variant_featured boolean NOT NULL,
    product_id bigint NOT NULL,
    variant_datasheet_url character varying(200),
    variant_minimum_inventory_level numeric(10,2)
);


ALTER TABLE public.marketing_productvariant OWNER TO postgres;

--
-- Name: marketing_productvariant_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productvariant ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productvariant_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productvariantattribute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productvariantattribute (
    id bigint NOT NULL,
    name character varying(255) NOT NULL
);


ALTER TABLE public.marketing_productvariantattribute OWNER TO postgres;

--
-- Name: marketing_productvariantattribute_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productvariantattribute ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productvariantattribute_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: marketing_productvariantattributevalue; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marketing_productvariantattributevalue (
    id bigint NOT NULL,
    product_variant_attribute_value character varying(255) NOT NULL,
    product_variant_attribute_id bigint NOT NULL,
    product_variant_id bigint NOT NULL,
    product_id bigint NOT NULL
);


ALTER TABLE public.marketing_productvariantattributevalue OWNER TO postgres;

--
-- Name: marketing_productvariantattributevalue_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.marketing_productvariantattributevalue ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.marketing_productvariantattributevalue_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_machine; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_machine (
    id bigint NOT NULL,
    name character varying(150) NOT NULL,
    max_rpm integer NOT NULL,
    domain numeric(5,2) NOT NULL,
    workstation_id bigint NOT NULL,
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
-- Name: operating_machinecredential; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_machinecredential (
    id bigint NOT NULL,
    name character varying(150) NOT NULL,
    api_key character varying(64) NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.operating_machinecredential OWNER TO postgres;

--
-- Name: operating_machinecredential_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_machinecredential ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_machinecredential_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_order; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_order (
    id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL,
    status character varying(32) NOT NULL,
    notes text,
    company_id bigint,
    contact_id bigint,
    qr_code_url character varying(200)
);


ALTER TABLE public.operating_order OWNER TO postgres;

--
-- Name: operating_order_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_order ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_orderitem; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_orderitem (
    id bigint NOT NULL,
    quantity numeric(10,2),
    price numeric(10,2) NOT NULL,
    order_id bigint NOT NULL,
    product_id bigint NOT NULL,
    description text,
    status character varying(32) NOT NULL,
    product_variant_id bigint,
    qr_code_url character varying(200)
);


ALTER TABLE public.operating_orderitem OWNER TO postgres;

--
-- Name: operating_orderitem_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_orderitem ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_orderitem_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: operating_workstation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.operating_workstation (
    id bigint NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.operating_workstation OWNER TO postgres;

--
-- Name: operating_workstation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.operating_workstation ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.operating_workstation_id_seq
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
    name character varying(200) NOT NULL,
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
1	konfeksiyon	konfeksiyon@demfirat.com	$2b$12$iJR1GRFfybA1.6TjwEQghOVqj/9FXQppCc1joZMrTFYmz/r9w1jv6	Karven Konfeksiyon
2	firat	firatkarven@gmail.com	$2b$12$Z66.D3RMZZAhSuGURXUbsugB5gCs6KnvdRX7CpvEgPYPlvo9rSpF2	Firat
3	client	client@demfirat.com	$2b$12$33n6xAf/wimD5f11DKDIuenTbWfIdW1YLevcEvtnwyVMOZ0ebX3ae	Client
\.


--
-- Data for Name: _prisma_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public._prisma_migrations (id, checksum, finished_at, migration_name, logs, rolled_back_at, started_at, applied_steps_count) FROM stdin;
329ae26b-2f52-44bd-b53a-3f60efce36b7	6e7748f047521beb2206c6c8e6ed38dc93067ede0741f77b88e9a005b21b6a67	2025-03-09 19:54:42.988337+00	0_init		\N	2025-03-09 19:54:42.988337+00	0
\.


--
-- Data for Name: accounting_assetaccountsreceivable; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_assetaccountsreceivable (id, created_at, amount, book_id, company_id, contact_id, currency_id, invoice_id) FROM stdin;
1	2025-07-15 15:07:59.489862+00	1025.00	1	\N	3	1	\N
2	2025-07-15 15:14:25.72434+00	725.00	1	\N	3	1	\N
3	2025-07-15 15:17:53.205081+00	726.00	1	\N	3	1	\N
\.


--
-- Data for Name: accounting_assetcash; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_assetcash (id, created_at, amount, currency_balance, book_id, currency_id, transaction_id) FROM stdin;
\.


--
-- Data for Name: accounting_assetinventorygood; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_assetinventorygood (id, created_at, modified_at, name, unit_cost, quantity, stock_type, status, warehouse, location, book_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_assetinventoryrawmaterial; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_assetinventoryrawmaterial (id, created_at, name, stock_id, receipt_number, unit_of_measurement, unit_cost, quantity, warehouse, location, raw_type, book_id, currency_id, supplier_id) FROM stdin;
\.


--
-- Data for Name: accounting_book; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_book (id, created_at, name, total_shares) FROM stdin;
1	2025-06-28 18:09:23.095381+00	Muhammed Firat Ozturk	10000000
\.


--
-- Data for Name: accounting_cashaccount; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_cashaccount (id, name, balance, book_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_currencycategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_currencycategory (id, code, name, symbol) FROM stdin;
1	usd	US Dollars	$
\.


--
-- Data for Name: accounting_currencyexchange; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_currencyexchange (id, created_at, from_amount, to_amount, date, book_id, from_cash_account_id, to_cash_account_id) FROM stdin;
\.


--
-- Data for Name: accounting_equitycapital; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equitycapital (id, created_at, date_invested, amount, new_shares_issued, note, book_id, cash_account_id, currency_id, member_id) FROM stdin;
\.


--
-- Data for Name: accounting_equitydivident; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equitydivident (id, created_at, amount, date, description, book_id, cash_account_id, currency_id, member_id) FROM stdin;
\.


--
-- Data for Name: accounting_equityexpense; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equityexpense (id, created_at, amount, date, description, book_id, cash_account_id, category_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_equityrevenue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_equityrevenue (id, created_at, amount, date, description, invoice_number, revenue_type, book_id, cash_account_id, currency_id) FROM stdin;
\.


--
-- Data for Name: accounting_expensecategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_expensecategory (id, name) FROM stdin;
\.


--
-- Data for Name: accounting_intransfer; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_intransfer (id, created_at, amount, date, description, book_id, currency_id, destination_id, source_id) FROM stdin;
\.


--
-- Data for Name: accounting_invoice; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_invoice (id, created_at, due_cate, invoice_type, total, paid, book_id, company_id, contact_id, order_id) FROM stdin;
\.


--
-- Data for Name: accounting_liabilityaccountspayable; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_liabilityaccountspayable (id, created_at, amount, receipt, book_id, currency_id, supplier_id) FROM stdin;
\.


--
-- Data for Name: accounting_metric; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_metric (id, created_at, balance, money_in, money_out, burn, inventory, accounts_receivable, accounts_payable, runway, growth_rate, default_alive, book_id) FROM stdin;
\.


--
-- Data for Name: accounting_stakeholderbook; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_stakeholderbook (id, shares, book_id, member_id) FROM stdin;
\.


--
-- Data for Name: accounting_transaction; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounting_transaction (id, created_at, value, type, type_pk, account_balance, account_id, book_id, currency_id) FROM stdin;
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
29	Can add company	8	add_company
30	Can change company	8	change_company
31	Can delete company	8	delete_company
32	Can view company	8	view_company
33	Can add contact	9	add_contact
34	Can change contact	9	change_contact
35	Can delete contact	9	delete_contact
36	Can view contact	9	view_contact
37	Can add supplier	10	add_supplier
38	Can change supplier	10	change_supplier
39	Can delete supplier	10	delete_supplier
40	Can view supplier	10	view_supplier
41	Can add note	11	add_note
42	Can change note	11	change_note
43	Can delete note	11	delete_note
44	Can view note	11	view_note
45	Can add book	12	add_book
46	Can change book	12	change_book
47	Can delete book	12	delete_book
48	Can view book	12	view_book
49	Can add stakeholder book	13	add_stakeholderbook
50	Can change stakeholder book	13	change_stakeholderbook
51	Can delete stakeholder book	13	delete_stakeholderbook
52	Can view stakeholder book	13	view_stakeholderbook
53	Can add currency category	14	add_currencycategory
54	Can change currency category	14	change_currencycategory
55	Can delete currency category	14	delete_currencycategory
56	Can view currency category	14	view_currencycategory
57	Can add invoice	15	add_invoice
58	Can change invoice	15	change_invoice
59	Can delete invoice	15	delete_invoice
60	Can view invoice	15	view_invoice
61	Can add asset cash	16	add_assetcash
62	Can change asset cash	16	change_assetcash
63	Can delete asset cash	16	delete_assetcash
64	Can view asset cash	16	view_assetcash
65	Can add asset inventory raw material	17	add_assetinventoryrawmaterial
66	Can change asset inventory raw material	17	change_assetinventoryrawmaterial
67	Can delete asset inventory raw material	17	delete_assetinventoryrawmaterial
68	Can view asset inventory raw material	17	view_assetinventoryrawmaterial
69	Can add asset inventory good	18	add_assetinventorygood
70	Can change asset inventory good	18	change_assetinventorygood
71	Can delete asset inventory good	18	delete_assetinventorygood
72	Can view asset inventory good	18	view_assetinventorygood
73	Can add asset accounts receivable	19	add_assetaccountsreceivable
74	Can change asset accounts receivable	19	change_assetaccountsreceivable
75	Can delete asset accounts receivable	19	delete_assetaccountsreceivable
76	Can view asset accounts receivable	19	view_assetaccountsreceivable
77	Can add liability accounts payable	20	add_liabilityaccountspayable
78	Can change liability accounts payable	20	change_liabilityaccountspayable
79	Can delete liability accounts payable	20	delete_liabilityaccountspayable
80	Can view liability accounts payable	20	view_liabilityaccountspayable
81	Can add cash account	21	add_cashaccount
82	Can change cash account	21	change_cashaccount
83	Can delete cash account	21	delete_cashaccount
84	Can view cash account	21	view_cashaccount
85	Can add equity capital	22	add_equitycapital
86	Can change equity capital	22	change_equitycapital
87	Can delete equity capital	22	delete_equitycapital
88	Can view equity capital	22	view_equitycapital
89	Can add equity revenue	23	add_equityrevenue
90	Can change equity revenue	23	change_equityrevenue
91	Can delete equity revenue	23	delete_equityrevenue
92	Can view equity revenue	23	view_equityrevenue
93	Can add expense category	24	add_expensecategory
94	Can change expense category	24	change_expensecategory
95	Can delete expense category	24	delete_expensecategory
96	Can view expense category	24	view_expensecategory
97	Can add equity expense	25	add_equityexpense
98	Can change equity expense	25	change_equityexpense
99	Can delete equity expense	25	delete_equityexpense
100	Can view equity expense	25	view_equityexpense
101	Can add equity divident	26	add_equitydivident
102	Can change equity divident	26	change_equitydivident
103	Can delete equity divident	26	delete_equitydivident
104	Can view equity divident	26	view_equitydivident
105	Can add in transfer	27	add_intransfer
106	Can change in transfer	27	change_intransfer
107	Can delete in transfer	27	delete_intransfer
108	Can view in transfer	27	view_intransfer
109	Can add currency exchange	28	add_currencyexchange
110	Can change currency exchange	28	change_currencyexchange
111	Can delete currency exchange	28	delete_currencyexchange
112	Can view currency exchange	28	view_currencyexchange
113	Can add transaction	29	add_transaction
114	Can change transaction	29	change_transaction
115	Can delete transaction	29	delete_transaction
116	Can view transaction	29	view_transaction
117	Can add metric	30	add_metric
118	Can change metric	30	change_metric
119	Can delete metric	30	delete_metric
120	Can view metric	30	view_metric
121	Can add permission	31	add_permission
122	Can change permission	31	change_permission
123	Can delete permission	31	delete_permission
124	Can view permission	31	view_permission
125	Can add member	32	add_member
126	Can change member	32	change_member
127	Can delete member	32	delete_member
128	Can view member	32	view_member
129	Can add machine	33	add_machine
130	Can change machine	33	change_machine
131	Can delete machine	33	delete_machine
132	Can view machine	33	view_machine
133	Can add product variant attribute	34	add_productvariantattribute
134	Can change product variant attribute	34	change_productvariantattribute
135	Can delete product variant attribute	34	delete_productvariantattribute
136	Can view product variant attribute	34	view_productvariantattribute
137	Can add product file	35	add_productfile
138	Can change product file	35	change_productfile
139	Can delete product file	35	delete_productfile
140	Can view product file	35	view_productfile
141	Can add product	36	add_product
142	Can change product	36	change_product
143	Can delete product	36	delete_product
144	Can view product	36	view_product
145	Can add product collection	37	add_productcollection
146	Can change product collection	37	change_productcollection
147	Can delete product collection	37	delete_productcollection
148	Can view product collection	37	view_productcollection
149	Can add product variant attribute value	38	add_productvariantattributevalue
150	Can change product variant attribute value	38	change_productvariantattributevalue
151	Can delete product variant attribute value	38	delete_productvariantattributevalue
152	Can view product variant attribute value	38	view_productvariantattributevalue
153	Can add product variant	39	add_productvariant
154	Can change product variant	39	change_productvariant
155	Can delete product variant	39	delete_productvariant
156	Can view product variant	39	view_productvariant
157	Can add product category	40	add_productcategory
158	Can change product category	40	change_productcategory
159	Can delete product category	40	delete_productcategory
160	Can view product category	40	view_productcategory
161	Can add order	41	add_order
162	Can change order	41	change_order
163	Can delete order	41	delete_order
164	Can view order	41	view_order
165	Can add order item	42	add_orderitem
166	Can change order item	42	change_orderitem
167	Can delete order item	42	delete_orderitem
168	Can view order item	42	view_orderitem
169	Can add machine credential	43	add_machinecredential
170	Can change machine credential	43	change_machinecredential
171	Can delete machine credential	43	delete_machinecredential
172	Can view machine credential	43	view_machinecredential
173	Can add work station	44	add_workstation
174	Can change work station	44	change_workstation
175	Can delete work station	44	delete_workstation
176	Can view work station	44	view_workstation
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
1	pbkdf2_sha256$600000$RQ44rPIwqiF9sGgVYem5o5$4Yl0gxobyKb81ETmdFNKXWE08enSbXc2FwB8iItcShQ=	2025-07-09 19:01:42.993898+00	t	firat			firatdmf1@gmail.com	t	t	2025-03-07 21:23:10.896064+00
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

COPY public.authentication_member (id, user_id) FROM stdin;
\.


--
-- Data for Name: authentication_member_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_member_permissions (id, member_id, permission_id) FROM stdin;
\.


--
-- Data for Name: authentication_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.authentication_permission (id, name, description) FROM stdin;
\.


--
-- Data for Name: crm_company; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_company (id, name, email, "backgroundInfo", phone, website, address, country, created_at) FROM stdin;
3	Dichis Perdele Si Draperii	captiv.geoflor77@yahoo.com		+40 766 892 82		strada Garii, numarul 6, Targoviste	Romania	2025-06-04 09:09:24.641707+00
1	Woodline Saliveros	wsaliveros@gmail.com						2025-05-25 17:15:02.54109+00
4	Nejum Technologies, Inc.	howdy@nejum.com						2025-06-26 05:56:14.353634+00
5	PEARLINS LLC					18021 SKY PARK CIR STE K IRVINE,CA	USA	2025-06-29 10:23:47.850009+00
7	new company	new@gmail.com	ba					2025-06-29 11:51:59.844782+00
\.


--
-- Data for Name: crm_contact; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_contact (id, name, email, phone, address, country, birthday, job_title, created_at, company_id, "backgroundInfo") FROM stdin;
1	maria chatzicharalampous	mariachi@gmail.com	+30 694533 3615	3rd septemurion 112	Greece	\N		2025-06-04 08:54:26.547298+00	\N	
2	Muhammed					\N		2025-06-25 16:21:52.962849+00	\N	
3	muhammed2	muhammed@gmail.com	323946484	18021 sky park cir ste k	usa	1997-09-15	president	2025-06-26 06:13:39.531416+00	\N	my background info
5	new lead					\N		2025-06-29 12:03:58.929046+00	\N	
6	Ducile Ciprian					\N	Business Owner	2025-07-07 07:28:47.907621+00	\N	
\.


--
-- Data for Name: crm_note; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_note (id, content, created_at, modified_date, company_id, contact_id) FROM stdin;
1	lovely couple	2025-05-25 17:15:02.554352+00	2025-05-25 17:15:02.554368+00	1	\N
2	Georgiana is the contact at this company.	2025-06-04 09:09:24.645445+00	2025-06-04 09:09:24.645459+00	3	\N
3	my first note for muhammed	2025-06-26 06:13:39.632496+00	2025-06-26 06:13:39.632537+00	\N	3
4	muhammed note 2	2025-06-29 06:34:45.477686+00	2025-06-29 06:34:45.477703+00	\N	3
5	MY FIRST NOTE	2025-06-29 10:23:47.958718+00	2025-06-29 10:23:47.958761+00	5	\N
8	initial note	2025-06-29 11:51:59.958564+00	2025-06-29 11:51:59.958606+00	7	\N
9	Their cargo code from Frk is: BS-21	2025-07-10 09:36:18.543987+00	2025-07-10 09:36:18.544007+00	3	\N
\.


--
-- Data for Name: crm_supplier; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crm_supplier (id, company_name, contact_name, email, phone, website, address, country, created_at) FROM stdin;
1	KARVEN TEKSTIL SAN VE TIC LTD STI	FIRAT	firatkarven@gmail.com	5010571884	www.karvenhome.com	VAKIFLAR	Turkey	2025-03-08 22:33:31.832275+00
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2025-03-08 22:20:43.06523+00	1	curtain	1	[{"added": {}}]	40	1
2	2025-03-08 22:20:57.204552+00	1	curtain	2	[]	40	1
3	2025-03-08 22:21:02.836779+00	2	fabric	1	[{"added": {}}]	40	1
4	2025-03-08 22:33:32.057572+00	1	KARVEN TEKSTIL SAN VE TIC LTD STI	1	[{"added": {}}]	10	1
5	2025-03-13 13:08:19.313489+00	1	Mariposa - RK24539RW8	1	[{"added": {}}]	39	1
6	2025-03-13 13:08:47.029674+00	1	Color	1	[{"added": {}}]	34	1
7	2025-03-13 13:08:53.970414+00	2	Size	1	[{"added": {}}]	34	1
8	2025-03-13 13:09:09.087156+00	1	Size: 84	1	[{"added": {}}]	38	1
9	2025-03-13 13:10:54.567456+00	2	Size: 95	1	[{"added": {}}]	38	1
10	2025-03-13 18:19:52.257084+00	2	Mariposa - RK24539RW9	1	[{"added": {}}]	39	1
11	2025-03-13 18:20:20.289768+00	3	Mariposa - RK24539RW9 |Size: 95	1	[{"added": {}}]	38	1
12	2025-03-13 18:24:42.849768+00	3	Mariposa - RK24539RW9 |Size: 95	2	[{"changed": {"fields": ["Product"]}}]	38	1
13	2025-03-13 18:24:56.554555+00	1	Mariposa - RK24539RW8 |Size: 84	2	[{"changed": {"fields": ["Product"]}}]	38	1
14	2025-03-13 18:29:28.197918+00	3	Mariposa - RK24539RW9 |Size: 95	2	[{"changed": {"fields": ["Product"]}}]	38	1
15	2025-03-13 18:29:45.11263+00	3	Mariposa - RK24539RW9 |Size: 95	2	[{"changed": {"fields": ["Product"]}}]	38	1
16	2025-03-13 18:30:00.046136+00	1	Mariposa - RK24539RW8 |Size: 84	2	[{"changed": {"fields": ["Product"]}}]	38	1
17	2025-03-14 14:54:03.842387+00	1	Mariposa - RK24539RW8 |Size: 84	2	[{"changed": {"fields": ["Product"]}}]	38	1
18	2025-03-16 15:50:23.482599+00	1	Mariposa - RK24539RW8 |Size: 84	2	[{"changed": {"fields": ["Product"]}}]	38	1
19	2025-03-16 16:08:16.23849+00	3	Wave - RK24562RW8	1	[{"added": {}}]	39	1
20	2025-03-16 16:08:59.013998+00	4	Wave - RK24562GW9	1	[{"added": {}}]	39	1
21	2025-03-16 16:09:33.688059+00	5	Wave - RK24562RC8	1	[{"added": {}}]	39	1
22	2025-03-16 16:09:52.765118+00	6	Wave - RK24562GC9	1	[{"added": {}}]	39	1
23	2025-03-16 16:10:48.201918+00	4	Wave - RK24562RW8 |Color: white	1	[{"added": {}}]	38	1
24	2025-03-16 16:11:13.079189+00	5	Wave - RK24562GW9 |Color: white	1	[{"added": {}}]	38	1
25	2025-03-16 16:11:54.638928+00	6	Wave - RK24562RC8 |Color: beige	1	[{"added": {}}]	38	1
26	2025-03-16 16:12:13.775575+00	7	Wave - RK24562GC9 |Color: beige	1	[{"added": {}}]	38	1
27	2025-03-16 16:12:29.159912+00	8	Wave - RK24562RW8 |Size: 84	1	[{"added": {}}]	38	1
28	2025-03-16 16:12:51.115842+00	9	Wave - RK24562GW9 |Size: 95	1	[{"added": {}}]	38	1
29	2025-03-16 16:13:04.500607+00	10	Wave - RK24562RC8 |Size: 84	1	[{"added": {}}]	38	1
30	2025-03-16 16:13:17.145382+00	11	Wave - RK24562GC9 |Size: 95	1	[{"added": {}}]	38	1
31	2025-03-28 11:34:08.249464+00	2	RK24539	2	[{"changed": {"fields": ["Description", "Unit of measurement", "Unit of weight", "Has variants"]}}]	36	1
32	2025-03-30 05:47:53.135427+00	3	RK24562	2	[{"changed": {"fields": ["Description", "Unit of measurement", "Unit of weight"]}}, {"changed": {"name": "product variant", "object": "Wave - RK24562RW8", "fields": ["Variant featured"]}}]	36	1
33	2025-05-08 11:20:44.600998+00	19	qwesadasff	2	[{"changed": {"fields": ["Sku", "Unit of measurement", "Unit of weight"]}}]	36	1
34	2025-05-08 11:23:53.43293+00	19	qwesadasff	3		36	1
35	2025-05-08 11:23:53.531604+00	18	Welding Mask	3		36	1
36	2025-05-08 11:23:53.631244+00	17	Welding Helmet	3		36	1
37	2025-05-08 11:23:53.731664+00	16	HAM123	3		36	1
38	2025-05-08 15:02:41.861761+00	3	Media for trial product	3		35	1
39	2025-05-08 15:14:40.371021+00	14	trial product	2	[{"changed": {"fields": ["Sku", "Has variants"]}}]	36	1
40	2025-05-08 15:22:55.362563+00	14	123213	2	[{"changed": {"fields": ["Sku", "Has variants"]}}]	36	1
41	2025-05-14 18:48:40.493114+00	12	trial product - blue21 |color: blue	1	[{"added": {}}]	38	1
42	2025-05-14 18:48:58.845307+00	13	trial product - black21 |color: black	1	[{"added": {}}]	38	1
43	2025-05-15 09:37:42.530218+00	8	trial product - black21	3		39	1
44	2025-05-15 09:37:42.683552+00	7	trial product - blue21	3		39	1
45	2025-05-16 17:04:11.345382+00	7	Media for trial product	3		35	1
46	2025-05-16 17:11:08.986736+00	50	trial product - blue12 |color: blue	1	[{"added": {}}]	38	1
47	2025-06-01 08:57:29.654667+00	2	fabric	2	[{"changed": {"fields": ["Image"]}}]	40	1
48	2025-06-01 09:01:46.296854+00	1	curtain	2	[{"changed": {"fields": ["Image"]}}]	40	1
49	2025-06-01 09:01:57.545047+00	2	fabric	2	[{"changed": {"fields": ["Image"]}}]	40	1
50	2025-06-01 09:04:04.718956+00	2	fabric	2	[{"changed": {"fields": ["Image"]}}]	40	1
51	2025-06-01 09:04:36.475746+00	1	curtain	2	[{"changed": {"fields": ["Image"]}}]	40	1
52	2025-06-02 07:16:07.38095+00	12	trial product - black21	3		39	1
53	2025-06-02 07:16:07.509761+00	9	trial product - blue12	3		39	1
54	2025-06-02 09:47:59.035694+00	26	trial product - 9595	3		39	1
55	2025-06-02 09:47:59.162419+00	25	trial product - 8484	3		39	1
56	2025-06-05 03:35:01.62055+00	13	RN1381	2	[{"changed": {"fields": ["Featured"]}}]	36	1
57	2025-06-05 06:48:05.868903+00	13	RN1381	2	[{"changed": {"fields": ["Primary image"]}}]	36	1
58	2025-06-05 06:48:45.608337+00	13	RN1381	2	[{"changed": {"fields": ["Featured"]}}]	36	1
59	2025-06-05 07:00:35.417652+00	74	Media for RK12471 | Weave	1	[{"added": {}}]	35	1
60	2025-06-05 07:00:41.20029+00	1	RK12471	2	[{"changed": {"fields": ["Primary image"]}}]	36	1
61	2025-06-06 07:57:23.253552+00	396	Confetti - RN1381RM9 |size: 52' X 95 ' (130 CM x 240 cm) each	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
62	2025-06-06 07:57:42.467606+00	393	Confetti - RN1381RM8 |size: 52' X 84' (130 CM x 210 cm) each	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
63	2025-06-06 07:59:39.952928+00	393	Confetti - RN1381RM8 |size: 84	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
64	2025-06-06 07:59:57.169524+00	396	Confetti - RN1381RM9 |size: 95	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
65	2025-06-10 05:35:54.376745+00	61	Ethnic - RK48061RC9	3		39	1
66	2025-06-10 05:35:54.490521+00	60	Ethnic - RK48061RC8	3		39	1
67	2025-06-10 05:57:23.493787+00	63	Ethnic - RK48061RC8	3		39	1
68	2025-06-10 06:08:50.769659+00	431	Leather - RN1370RB9 |size: 130cm x 240cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
69	2025-06-10 06:09:16.582558+00	432	Leather - RN1370RB8 |size: 130cm x 210cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
70	2025-06-10 06:10:28.619532+00	422	Wave - RK24562RC8 |size: 130cm x 210cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
71	2025-06-10 06:11:12.79093+00	420	Wave - RK24562GC9 |size: 130cm x 240cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
72	2025-06-10 06:11:58.300163+00	418	Wave - RK24562RW8 |size: 130cm x 210cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
73	2025-06-10 06:12:26.128946+00	416	Wave - RK24562GW9 |size: 130cm x 240cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
74	2025-06-10 06:14:10.822261+00	562	Mariposa - RK24539RW9 |size: 130cm x 240cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
75	2025-06-10 06:14:15.653179+00	561	Mariposa - RK24539RW8 |size: 130cm x 210cm (Each)	2	[{"changed": {"fields": ["Attribute Value"]}}]	38	1
76	2025-06-10 06:57:49.275471+00	676	Confetti - RN1381RM8 |size: 130cm x 210cm (Each)	1	[{"added": {}}]	38	1
77	2025-06-10 06:58:09.267349+00	676	Confetti - RN1381RM9 |size: 130cm x 240cm (Each)	2	[{"changed": {"fields": ["Product variant", "Attribute Value"]}}]	38	1
78	2025-06-10 06:59:35.526692+00	677	Confetti - RN1381RM8 |size: 130cm x 210cm (Each)	1	[{"added": {}}]	38	1
79	2025-06-15 04:18:23.376987+00	1	curtain	2	[{"changed": {"fields": ["Image"]}}]	40	1
80	2025-06-15 04:18:43.948917+00	2	fabric	2	[{"changed": {"fields": ["Image"]}}]	40	1
82	2025-06-18 07:51:34.933972+00	74	RK12471	3		35	1
83	2025-07-15 15:01:07.985123+00	1	usd - US Dollars	1	[{"added": {}}]	14	1
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
8	crm	company
9	crm	contact
10	crm	supplier
11	crm	note
12	accounting	book
13	accounting	stakeholderbook
14	accounting	currencycategory
15	accounting	invoice
16	accounting	assetcash
17	accounting	assetinventoryrawmaterial
18	accounting	assetinventorygood
19	accounting	assetaccountsreceivable
20	accounting	liabilityaccountspayable
21	accounting	cashaccount
22	accounting	equitycapital
23	accounting	equityrevenue
24	accounting	expensecategory
25	accounting	equityexpense
26	accounting	equitydivident
27	accounting	intransfer
28	accounting	currencyexchange
29	accounting	transaction
30	accounting	metric
31	authentication	permission
32	authentication	member
33	operating	machine
34	marketing	productvariantattribute
35	marketing	productfile
36	marketing	product
37	marketing	productcollection
38	marketing	productvariantattributevalue
39	marketing	productvariant
40	marketing	productcategory
41	operating	order
42	operating	orderitem
43	operating	machinecredential
44	operating	workstation
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2025-03-07 21:16:07.266438+00
2	auth	0001_initial	2025-03-07 21:16:11.17651+00
3	admin	0001_initial	2025-03-07 21:16:12.206423+00
4	admin	0002_logentry_remove_auto_add	2025-03-07 21:16:12.54647+00
5	admin	0003_logentry_add_action_flag_choices	2025-03-07 21:16:13.326553+00
6	contenttypes	0002_remove_content_type_name	2025-03-07 21:16:14.016288+00
7	auth	0002_alter_permission_name_max_length	2025-03-07 21:16:15.226452+00
8	auth	0003_alter_user_email_max_length	2025-03-07 21:16:15.786528+00
9	auth	0004_alter_user_username_opts	2025-03-07 21:16:16.236698+00
10	auth	0005_alter_user_last_login_null	2025-03-07 21:16:16.808249+00
11	auth	0006_require_contenttypes_0002	2025-03-07 21:16:17.256562+00
12	auth	0007_alter_validators_add_error_messages	2025-03-07 21:16:17.696496+00
13	auth	0008_alter_user_username_max_length	2025-03-07 21:16:18.296705+00
14	auth	0009_alter_user_last_name_max_length	2025-03-07 21:16:18.85646+00
15	auth	0010_alter_group_name_max_length	2025-03-07 21:16:19.476472+00
16	auth	0011_update_proxy_permissions	2025-03-07 21:16:19.946465+00
17	auth	0012_alter_user_first_name_max_length	2025-03-07 21:16:21.176558+00
18	sessions	0001_initial	2025-03-07 21:16:22.056487+00
19	crm	0001_initial	2025-03-07 21:18:32.627946+00
20	marketing	0001_initial	2025-03-07 21:18:49.892336+00
21	authentication	0001_initial	2025-03-07 21:20:44.915849+00
22	accounting	0001_initial	2025-03-07 21:21:17.777094+00
23	todo	0001_initial	2025-03-07 21:21:40.786723+00
24	operating	0001_initial	2025-03-07 21:22:06.047219+00
25	marketing	0002_alter_productcategory_options_and_more	2025-03-09 18:29:28.398145+00
26	marketing	0003_remove_product_vendor_alter_product_collections	2025-03-09 18:57:19.46377+00
27	marketing	0004_product_supplier	2025-03-09 19:04:38.595744+00
28	marketing	0005_alter_product_supplier	2025-03-09 19:04:41.024298+00
29	marketing	0006_alter_productvariantattributevalue_unique_together	2025-03-13 13:10:24.243496+00
30	marketing	0007_alter_productvariantattributevalue_unique_together	2025-03-13 14:01:08.700788+00
31	marketing	0008_productvariantattributevalue_product	2025-03-13 18:23:54.951797+00
32	marketing	0009_alter_product_sku	2025-03-24 15:22:45.212055+00
33	marketing	0010_remove_productfile_product_variant	2025-03-24 15:38:17.635048+00
34	marketing	0011_alter_productfile_file	2025-03-26 17:51:18.833995+00
35	marketing	0012_product_has_variants	2025-03-28 11:29:39.375043+00
36	marketing	0013_remove_product_cost_productfile_product_variant	2025-05-07 21:27:55.540085+00
37	marketing	0014_remove_productfile_sequence	2025-05-07 21:31:55.190579+00
38	marketing	0015_product_datasheet_url_and_more	2025-05-08 10:49:10.586741+00
39	marketing	0016_rename_datasheet_url_productvariant_variant_datasheet_url	2025-05-08 10:49:46.654332+00
40	marketing	0017_alter_product_barcode_alter_product_featured_and_more	2025-05-08 10:59:30.865667+00
41	marketing	0018_rename_variant_productvariantattributevalue_product_variant_and_more	2025-05-15 14:59:05.704001+00
42	marketing	0019_productcategory_image	2025-06-01 08:54:09.287596+00
43	marketing	0020_remove_product_has_variants	2025-06-02 07:45:44.041648+00
44	marketing	0021_product_primary_image	2025-06-05 06:37:07.664605+00
45	marketing	0022_productfile_is_primary_productfile_sequence	2025-06-05 07:16:45.526978+00
46	marketing	0023_remove_productfile_is_primary	2025-06-06 08:05:22.688419+00
47	marketing	0024_alter_productvariantattribute_name	2025-06-09 09:58:38.975414+00
48	marketing	0025_alter_productvariantattributevalue_product_and_more	2025-06-10 05:02:39.307208+00
49	marketing	0026_alter_productvariant_product	2025-06-10 06:56:08.435168+00
50	marketing	0027_alter_productvariant_variant_sku	2025-06-10 06:56:09.193133+00
51	marketing	0028_alter_product_created_at	2025-06-11 03:16:21.710085+00
52	marketing	0029_remove_productfile_file_productfile_file_url_and_more	2025-06-13 09:05:39.722924+00
53	marketing	0030_productfile_file_path	2025-06-15 02:06:49.747304+00
54	marketing	0031_alter_productcategory_image	2025-06-15 04:11:18.822643+00
55	operating	0002_order_orderitem	2025-06-18 12:24:00.065608+00
56	operating	0003_alter_order_status	2025-06-18 12:24:30.595084+00
57	operating	0004_orderitem_notes_orderitem_status	2025-06-19 08:19:22.839002+00
58	operating	0005_order_qr_code_url	2025-06-19 08:49:42.118647+00
59	operating	0006_machinecredential_orderitem_variant	2025-06-22 13:21:30.046192+00
60	operating	0007_alter_orderitem_variant	2025-06-22 19:09:34.298052+00
61	operating	0008_alter_orderitem_variant	2025-06-22 19:40:08.975839+00
62	operating	0009_rename_variant_orderitem_product_variant	2025-06-22 19:40:10.235852+00
63	crm	0002_remove_contact_company_name_alter_note_company_and_more	2025-06-22 20:30:48.011359+00
64	crm	0003_contact_backgroundinfo_alter_contact_name	2025-06-25 06:54:36.462706+00
65	crm	0004_alter_contact_backgroundinfo	2025-06-25 06:55:16.704359+00
66	crm	0005_alter_contact_backgroundinfo	2025-06-25 07:07:41.98548+00
67	crm	0006_alter_contact_backgroundinfo	2025-06-25 07:21:28.404991+00
68	crm	0007_alter_contact_backgroundinfo	2025-06-25 07:26:46.722152+00
69	crm	0008_alter_company_backgroundinfo	2025-06-25 07:58:15.520885+00
70	crm	0009_remove_contact_city_remove_contact_state_and_more	2025-06-25 07:59:59.331978+00
71	crm	0010_alter_company_country_alter_company_name_and_more	2025-06-25 16:21:17.969785+00
72	todo	0002_rename_task_name_task_name	2025-06-26 06:30:06.131871+00
73	crm	0011_alter_contact_company	2025-06-26 15:23:58.921143+00
74	crm	0012_alter_company_name	2025-06-29 11:37:30.539264+00
75	operating	0010_workstation_rename_notes_orderitem_description_and_more	2025-07-10 04:57:37.239856+00
76	operating	0011_rename_unit_price_orderitem_price	2025-07-10 05:24:27.046857+00
77	operating	0012_orderitem_qr_code_url	2025-07-12 06:28:44.728078+00
78	operating	0013_alter_orderitem_quantity	2025-07-12 08:56:51.667807+00
79	accounting	0002_alter_assetaccountsreceivable_company_and_more	2025-07-15 12:45:36.025565+00
80	accounting	0003_remove_invoice_items_invoice_order	2025-07-15 15:23:04.153747+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
dnm9dapvsj9rji5thbxv50u0orhly2ib	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1tqfAI:WHvf1aK9VyQVRnL9si_XJCk7p0uvAEt9nzabpn7FiJQ	2025-03-21 21:23:30.219007+00
8rz3zd110v1ntkukcbb1jze410iu6jk4	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1trhVm:-fX2EzyNWSYCXtW8rkgnlryBftFizaXBxqRmK1HmEiI	2025-03-24 18:05:58.352034+00
zdmwb8fhrg3zhyuqjuftylzlypwl0ejs	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1tsiEK:jWhjqG7L9T7uawYikm3T_l7PaxZTk6fMfKOEEmMAABw	2025-03-27 13:04:08.717355+00
i1vvjikesoch26i9cpa71vxjmzhge4jw	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1tuFzd:A2cSpfovxFbJkPNrdYbnakpCLXmXeCGsTysNII8gWEE	2025-03-31 19:19:21.945658+00
flza9ctfju7zf3f8n9paj947ztpfi231	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1tuZcd:mlIEUeivPeFSWwkcx1IcvJJA37hA8chdOKz82JUQ_O4	2025-04-01 16:16:55.659377+00
5ak56qkg6j0nw2dt5py3pukk461wikfb	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1twRBl:ecL7dB4p7jNhePaZLl6SjKDqubXCjE_HMUXbNPm2mlQ	2025-04-06 19:40:53.849616+00
a1i5qpebzb42xhb1480ixx0kwtftaedi	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uBFoc:5MwO_qZ3dg2sRyzHZyLakWuONpTZPMOAvCxj_EEIU1o	2025-05-17 16:34:14.834566+00
onq4t3tj73xrpx1tcf4vfiyyvu8bv0kc	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uFGOE:2qJWDItVacGgqrPAn1ub7odW_DZ28v94mCoCUtlNZfM	2025-05-28 17:59:34.14539+00
kitxakng4h1wp1n31p0x9s5dcptbmsz3	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uGkzy:XHhJWaWbmmYokSo1adqdTBLQEQJl45QjkfIZfK49WyY	2025-06-01 20:52:42.138409+00
bmnewpslbxm607nbcmiv3wjkcjbhsgg8	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uHf9K:xmZAuEJjlJc5vkXdMZ3nnE-JgnXwcFo89Os7ZvZ2w1U	2025-06-04 08:50:06.481239+00
u7zjte1asdz8ss9bcu8okzbzugeg008m	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uHf9L:SAUSz-ualHyieWJEE5AU496d5BClzvGzGG7lKNqgHv4	2025-06-04 08:50:07.353609+00
uw7tifttfanalo7fkp2ip1kwrxqw8h46	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uJ50C:OZDrSBuqqYhrjgbXeHzR6Y0Pln1UR7QpxECAdf8TnkM	2025-06-08 06:38:32.250203+00
0lpxyp2byywk397brkqmryt7cbrvmtja	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uJTFF:tGiVycOF0QjagwfVyLrBwPN_F8Hzj6ZReVibIAb5-KU	2025-06-09 08:31:41.977538+00
5idh8241po8scjjbocy4bcif38hbn9qh	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uJzfc:M2z29fgFLT2-PYn42qMi5nM3vQTJbxVk8Tn1CDe0JCc	2025-06-10 19:09:04.723548+00
69e8ixk5ok5udk0m2ny5buwn3q229j4b	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uLtoR:EhsZWcf8q9xtyo9LQU6P5YbWkm7ZA8J7TwNZmvMKmZg	2025-06-16 01:18:03.904667+00
fbwr8sx3x6jurs4gphy3tgtwl17b3gut	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uMq7N:N-mBITPJHPv0OXxD4MhccRy1abLncvm5sQ8aSz2igRc	2025-06-18 15:33:29.47043+00
6qeweaj2yo04hro0f10c3rm518eip8tk	.eJxVjMsOwiAQRf-FtSEMb1y69xsIzIBUDU1KuzL-uzbpQrf3nHNfLKZtbXEbZYkTsTMDdvrdcsJH6Tuge-q3mePc12XKfFf4QQe_zlSel8P9O2hptG-tEbJw0nqpwBjjIVhLToIGVGiFUUpUaYKmgGCdhoJgqnckAGSyorL3B4_jNeM:1uOWgc:uhnAci8PIfa5quSuKZf2mf4tuiqH2iX0w9RPYEEkNYM	2025-06-23 07:12:50.152048+00
9ql8itdkwqs0v7qfb5vfpbwcnacbkzif	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uR5GR:tlAVO82VBr7m45BD4WTijhXPrbkshqfcZdZl0zfO2sA	2025-06-30 08:32:23.408821+00
ksur5kuqxp36d844z3rhu36cc2m2it3t	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uRC7x:5tNU0gv8ouKWaorkH0xU8C-r5yrA1BhaNh3Ij3rGKjA	2025-06-30 15:52:05.033657+00
ajfjymhn1xq1ypvw0gtfkwwsp3w6hjib	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uRC8c:pStx7C0YsmLEbUZgoZZKfXtZAmrmqIUHZDykHLaGoe0	2025-06-30 15:52:46.49235+00
2crcci32kyjq4osrdtafpknklvkn41mv	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uT6rX:Ta7UjvlDDVuiJsigbpwx4EyNo_-2RO_0LpOHteUVuEY	2025-07-05 22:39:03.100978+00
tkv7ixteviogrgbshw9p9ligoo2hi84c	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uTE4I:fKMzRjhdyky8-Q7zxD5PFE8qeZRbL60bwj4S3j5RZ8M	2025-07-06 06:20:42.782264+00
kvbahbvuc5pynuhbm5awvw2kxmdd2pcy	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uWqEL:geA8EdJB6TTw3uCgyP52LZ0A49kU60snUBQ8TM17ne0	2025-07-16 05:42:01.731312+00
7vedn9fqs9lenw77u3sbzdn9avrjoe3s	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uWwAp:m3N346lETVmHhQUwdR9Ugx7hrQdEwYc07Gy4pI_i45w	2025-07-16 12:02:47.896102+00
g77nzlh7jlxjdwl1kjc65wlo4w1ocsqt	.eJxVjMsOwiAUBf-FtSGAFMGle7-B3AdXqoYmpV0Z_12bdKHbMzPnpTKsS81rL3MeWZ2VVYffDYEepW2A79Buk6apLfOIelP0Tru-Tlyel939O6jQ67eG4AYygxMfyIpwTOiRnTXEgSEm8cULE0YobI9RRKIYmxK5kyCEpN4fCXY5Mw:1uZa35:XKWG_-N6L2vVN5mYiqB6PRFZAfvu2o7iVd7MmRLXnDU	2025-07-23 19:01:43.130874+00
\.


--
-- Data for Name: marketing_product; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_product (id, created_at, title, description, sku, barcode, tags, type, unit_of_measurement, quantity, price, featured, selling_while_out_of_stock, weight, unit_of_weight, category_id, supplier_id, datasheet_url, minimum_inventory_level, primary_image_id) FROM stdin;
11	2025-06-11 00:42:05.019378+00	Feather	Delicate embroidery brightens up any room and adds style to your perfect window view.\r\n\r\nThese airy curtain panels gently filter the sunlight while enhancing your privacy—a bold design for courageous rooms. Explore the high chemistry of teal and white, and let it glamorize your space. The silky-soft woven panels allow in beautiful diffused light while still providing privacy.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Teal & Beige\r\nHeader Type: Grommet for White Panels | Rod Pocket for Teal Panels\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral Leaf & Feather\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.5 lb (680 g)\r\n\r\nFeatures\r\n\r\nAiry & Fresh: Add a refreshing charm to your window and feel the fine weave's positivity in your room.\r\nSheer Light Filtering: Providing a fantastic additional layer to your window that blocks harmful UV lights and protects your home.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1360	\N	{}	\N	\N	\N	\N	t	f	1.45	lb	1	1	\N	\N	148
8	2025-06-09 09:13:03.420403+00	Branch	Description\r\n\r\nThese soft-textured and beautifully embroidered sheer curtain panels with a floral pattern are made of high-quality stretchable knitted fabric that makes them ultra-durable and wrinkle-resistant. Their easy-to-wash and iron characteristics help keep them looking brand-new even after every wash. Perfect for adding style to your home, office, or guest suite. \r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Champagne\r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room,  Kid's Room, Girl's Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1 lb (453 g)\r\n\r\nFeatures\r\n\r\nClassy Yet Breathable: These knitted sheers with floral embroidery add a soft and fresh look to any space in your home.\r\nSheer Light Filtering: Provides a fantastic additional layer to your window that allows sunlight to enter while still providing privacy.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 3 inches that fit curtain rods up to 1.5 inches in diameter.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1268	\N	{}	\N	\N	\N	\N	t	f	1.00	lb	1	1	\N	\N	262
9	2025-06-09 09:14:35.492712+00	Floral	Welcome in warm sunlight and decorate your room with elegant embroidery. Delicate linen-textured fabric paired with floral embroidery that winds its way from bottom to top goes with almost any room color scheme. These panels are effortless to clean; throw them in your washing machine. \r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Beige\r\nHeader Type: Grommet for White Panels | Rod Pocket for Beige Panels\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm) for Grommet | 1-inch (2.54 cm) for Rod Pocket\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral Dandelion\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 2 lb (907 g)\r\n\r\nFeatures\r\n\r\nSimple yet Stylish: Woven sheers have the feel and look of linen—compliments any decorative style.\r\nSheer Light Filtering: Perfect for windows with constant exposure to sunlight—filters and reduces the harmful UV lights and ensures a safe environment for you and your family.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1337	\N	{}	\N	\N	\N	\N	t	f	1.80	lb	1	\N	\N	\N	248
10	2025-06-09 08:23:37.18772+00	Peony	These new stylish design sheer panels will make any room cozy. They let plenty of light in and will make you feel like you've just entered a beautiful garden. Highlight your taste with these charming floral embroidered panels. \r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor: Rose Gold and Gold\r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1-inch (2.54 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral Rose\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room, Kid's Room, Girl's Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.1 lb (498 g)\r\n\r\nFeatures\r\n\r\nVibrant and Charming: Inject a splash of bold color into your house and transform any room with vibrant colors and salient patterns.\r\nSheer Light Filtering: These panels will bring a soothing accent to your windows while filtering natural light into your house.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 2.25 inches that fit curtain rods up to 1.1 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1357	\N	{}	\N	\N	\N	\N	t	f	1.15	lb	1	1	\N	\N	182
12	2025-06-09 07:50:57.616729+00	Leather	Designer-inspired floral embroidery will catch all the eyes and uncover a brand-new perspective your windows never experienced. Mind you, purchasing this product might result in overexposure to the "Where did you get those!?" phrase.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor: Brown | Beige\r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.3 lb (590 g)\r\n\r\nFeatures\r\n\r\nUnique & Stylish: Unique rooms require unique treatments. \r\nSheer Light Filtering: Adds a fantastic layer that allows sunlight to enter while providing privacy.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1370	\N	{}	\N	\N	\N	\N	t	f	\N	\N	1	\N	\N	\N	124
6	2025-06-09 09:19:59.158967+00	Lattice	These classic Moroccan Trellis Pattern Curtain Panels will turn the heads of every guest. Its uniquely embroidered Moroccan Trellis pattern will soften your room's aura with its eccentric and airy look. Its grommets' 1.6" inner diameter makes them easier to hang on most curtain rods and smoothly open and close the curtains.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Beige\r\nHeader Type: Grommet\r\nMax Rod Diameter Allowed: 1.5 inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Geometric | Morrocan Trellis | Lattice | Trefoil\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 2 lb (907 g)\r\n\r\nFeatures\r\n\r\nVersatility: The perfect combination of modern and traditional that goes to all types of rooms.\r\nSheer Light Filtering: Provides a fantastic additional layer to your window that allows sunlight to enter while still providing privacy.\r\nEasy Hanging: Each panel conveniently features a grommet measuring 1.6 inches inner diameter that fits curtain rods up to 1.5 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK48065	\N	{}	\N	units	\N	\N	t	f	1.85	lb	1	1	\N	\N	290
7	2025-06-10 06:18:24.728944+00	Dandelion	Discover the potential and lighten your space with this minimal yet stylish design. The one-of-a-kind linen-textured fabric will provide the treatment your windows deserve and catch every visitor's eye to your home decor. Ideal for windows with constant exposure to sunlight, its woven texture filters reduce harmful UV lights and ensure a safe environment for you and your family.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Beige\r\nHeader Type: Grommet\r\nMax Rod Diameter Allowed: 1.5 inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral Dandelion\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.8 lb (816 g)\r\n\r\n\r\nFeatures\r\n\r\nLarge embroidery: What is more stylish than dandelion embroidery? The bigger version! These magical panels will have a hard time not looking at them.\r\nSheer Light Filtering: Provides a fantastic additional layer to your window that allows sunlight to enter while still providing privacy.\r\nEasy Hanging: Each panel conveniently features a grommet measuring 1.6 inches inner diameter that fits curtain rods up to 1.5 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK72010	\N	{}	\N	units	\N	\N	t	f	1.80	lb	1	1	\N	\N	206
14	2025-06-21 23:07:43.70174+00	trial Product	a little description added	123213	\N	{}	\N	units	\N	\N	t	f	\N	lb	1	\N	\N	\N	\N
2	2025-06-09 09:24:22.827307+00	Mariposa	Description\r\n\r\nThese airy and lightweight sheer curtain panels will get butterflies in your stomach—yes, pun intended. The soft fabric is so silky that it feels great against your skin, and your windows will thank you. Sparkle up your windows with butterflies—ideal for youngsters or those who have not lost their youthful energy.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor: White \r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1.5 inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Butterfly, Animal\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room, Kid's Room, Girl's Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.3 lb (590 g)\r\n\r\nFeatures\r\n\r\nJoyful Yet luxurious: Transform every room with the magical beauty of butterflies.\r\nSheer Light Filtering: Perfect for windows with constant exposure to sunlight—filters and reduces the harmful UV lights and ensures a safe environment for you and your family.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 3 inches that fit curtain rods up to 1.5 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK24539	\N	{}	\N	units	\N	\N	t	f	1.30	lb	1	1	\N	\N	318
15	2025-06-02 07:06:48.509225+00	my new product		yoursku	\N	{}	\N	units	\N	\N	t	f	\N	lb	\N	\N	\N	\N	\N
4	2025-06-09 10:13:15.079021+00	Rose	Harness the power of rose ramped up with a tightly-woven fabric that provides maximum durability that will last for years. Brighten up your room with natural light and embroidered rose motifs. These sheer panels feel extraordinarily soft and smooth to the touch and provide a fantastic additional layer to your window that acts as a natural filter and protects your family against UV lights.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Off-white\r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1-inch (2.54 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Floral Rose\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.3 lb (589 g)\r\n\r\nFeatures\r\n\r\nElegant and Lightweight: Gorgeous textured woven fabric creates a simple yet beautiful environment.\r\nLight Filtering: These panels will bring a soothing accent to your windows while filtering natural light into your house.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 2.25 inches that fit curtain rods up to 1.1 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK48060	\N	{}	\N	units	\N	\N	t	f	1.30	lb	1	1	\N	\N	332
20	2025-05-22 22:17:02.6654+00	Example Title		example	\N	{}	\N	units	\N	\N	t	f	\N	lb	\N	\N	\N	\N	\N
13	2025-06-06 08:34:56.819205+00	Confetti	Curtains do not have to be plain and boring; sparkle up your window with autumn confetti—no amount of color is too much. This pair of panels provides a unique look that will set your windows apart from the crowd.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor: Confetti\r\nHeader Type: Rod Pocket\r\nMax Rod Diameter Allowed: 1.5 inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Polka Dots Confetti\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room, Kid's Room, Girl's Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.2 lb (544 g)\r\n\r\nFeatures\r\n\r\nDecorative: Decorate your room with confetti particles or autumn leaves, however you imagine.\r\nSheer Light Filtering: Provides a fantastic additional layer to your window that allows sunlight to enter while still providing privacy.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 3 inches (7.6 cm) that fit curtain rods up to 1.5 inches (3.8 cm).\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RN1381	\N	{}	\N	units	\N	\N	t	f	1.20	lb	1	1	\N	\N	76
5	2025-06-10 06:05:16.849696+00	Ethnic	Discover the potential and lighten your space with this minimal yet stylish design. The one-of-a-kind linen-textured fabric will provide the treatment your windows deserve. It is ideal for windows with constant exposure to sunlight, its woven texture filters and reduces harmful UV lights, ensuring a safe environment for you and your family.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: Beige\r\nHeader Options: Rod Pocket | Grommet\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Tribal, Abstract\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.8 lb (816 g)\r\n\r\nFeatures\r\n\r\nClassy Yet Breathable: These knitted sheers with floral embroidery add a soft and fresh look to any space in your home.\r\nSheer Light Filtering: Provides a fantastic additional layer to your window that allows sunlight to enter while still providing privacy.\r\nEasy Hanging: Each panel conveniently features a rod pocket measuring 3 inches that fit curtain rods up to 1.5 inches in diameter.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK48061	\N	{}	\N	units	\N	\N	t	f	1.60	lb	1	1	\N	\N	360
3	2025-06-08 09:47:52.340442+00	Wave	Description\r\n\r\nSimplicity combined with tradition. Let your windows look full and get the proper treatment. The delicate weave patterns and mesmerizing linen texture provide the right balance of light and privacy. These panels let you decorate your room and enjoy a new elegance. \r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Beige\r\nHeader Type: Grommet for 95" Panels | Rod Pocket for 84" Panels\r\nMax Rod Diameter Allowed: 1.5" (3.8 cm)\r\nSide Hem: 1" (2.54 cm)\r\nPattern: Geometric, Morrocan Trellis. Lattice Trefoil\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 2 lbs (907 g)\r\n\r\nFeatures\r\n\r\nModish and Intrinsic: Woven sheers have the feel and look of linen—which compliments any decorative style.\r\nSheer Light Filtering: Light-weight panels provide the right balance of privacy and sunlight—filtering the UV lights while enhancing your view with beautiful wavy patterns.\r\nEasy Hanging: Each panel conveniently fits curtain rods up to 1.5 inches.\r\nEasy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK24562	\N	{}	\N	\N	\N	\N	t	f	\N	\N	1	\N	\N	\N	90
1	2025-06-18 11:30:02.757024+00	Weave	Bring the ocean waves to your window and feel the dynamics. The panels are crafted from 100% high-grade textured fabric and feature delicate embroidery waves for a silky touch. 1.6 in (4 cm) inner grommet diameter makes the panels easier to hang on most curtain rods and enables smooth opening and closing of the curtains.\r\n\r\nProduct Details\r\n\r\nPieces Included: 2 Curtain Panels\r\nEach Panel Width: 52-Inches (132 cm)\r\nLength Options: 84-inches (213 cm) | 95-inches (241 cm)\r\nColor Options: White | Beige\r\nHeader Type: Grommet\r\nMax Rod Diameter Allowed: 1.5-inches (3.8 cm)\r\nSide Hem: 1-inch (2.54 cm)\r\nPattern: Abstract\r\nLight Filtering: Semi Sheer\r\nFire Retardant: Yes\r\nMachine Washable: Yes\r\nRoom type: Living Room, Dining Room, Bedroom, Kitchen, Home Office, Sunroom, Playroom, Nursery Room\r\nBrand: Pearlins Linen\r\nFabric Origin: Turkey\r\nPackage Weight: 1.8 lb (816 g)\r\n\r\nFeatures\r\n\r\nSoft and Decorative: Repetitive soft pattern will unlock a new look to your room.\r\nSheer Light Filtering: Light-weight panels provide the right balance of privacy and sunlight—filtering the UV lights while enhancing your view with beautiful wavy patterns.\r\nEasy Hanging: Each panel conveniently features a grommet measuring 1.6 inches (4 cm) inner diameter that fits curtain rods up to 1.5 inches (3.8 cm).\r\nEasy Care: Easy Care: Machine washable cold with a laundry bag or dry clean; gentle cycle; do not bleach; tumble dry low; cool iron if needed.\r\nTexture: Smooth, soft, comfortable, breathable, antibacterial, eco-friendly, and durable.	RK12471	\N	{}	\N	meters	\N	\N	t	f	\N	\N	1	\N	\N	\N	455
\.


--
-- Data for Name: marketing_product_collections; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_product_collections (id, product_id, productcollection_id) FROM stdin;
\.


--
-- Data for Name: marketing_productcategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productcategory (id, created_at, name, image) FROM stdin;
1	2025-06-15 04:18:23.268381+00	curtain	https://res.cloudinary.com/dnnrxuhts/image/upload/v1749961086/curtain_thumbnail_qrff0f.avif
2	2025-06-15 04:18:43.846096+00	fabric	https://res.cloudinary.com/dnnrxuhts/image/upload/v1749961112/fabric_category_image_ixm9ts.avif
\.


--
-- Data for Name: marketing_productcollection; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productcollection (id, created_at, title, description, image) FROM stdin;
\.


--
-- Data for Name: marketing_productfile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productfile (id, product_id, product_variant_id, sequence, file_url, is_primary, file_path) FROM stdin;
431	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233169/qm6hocnih4rh5vwaz18l.jpg	f	\N
79	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064776/t8coiprbskuydqcumfkx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_IMG_7953.jpg
80	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064779/aryqldolc1wcb9ktvpy1.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_IMG_7954.jpg
82	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064781/fttbvje0nymdkyo0iw9d.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_img_8054_shoped.jpg
83	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064789/cwswicq0n5drgthvgoma.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_1381_far.jpg
85	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064791/o1hevpxkd7fl2q4e0x1f.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_IMG_7950.jpg
86	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064797/ahw5qftjavrlc5vi4aim.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_IMG_7953.jpg
88	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064801/dp6ahctaljhze85hn82r.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_IMG_7956.jpg
89	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064805/ttgn0rcdfmvpml22skz8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_img_8054_shoped.jpg
92	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064807/j776e20tfzppjyudemnd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_HfiyW1b.jpg
94	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064809/cie5yifi3xuir5wjbilm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_Oo1bUg4.jpg
95	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064811/xvwkwqtmmuxky4xqpsk2.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_PfyyY0o.jpg
96	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064812/ostlv8xyrcocwx30s8si.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_Qh34a3w.jpg
98	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064816/r1vru1xdaop6jdvnzvin.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_qoWMtyL.jpg
99	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064820/mguko9k0bpjghp6luapi.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_0UWm7im.jpg
100	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064823/d4cb8eivmvadypnmxpsz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_4POSs4k.jpg
102	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064825/h7hjxspy0tul9r0okckw.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_9bRy1yi.jpg
103	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064826/hysabwhcxwfaxktzte0r.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_Eh3k6MH.jpg
105	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064827/jphpcuzq1dmt62q0r13v.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_PfoFYN6.jpg
106	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064833/y8xf9jrhf6cu81ckacqe.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_bjKUV7L.jpg
107	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064839/rlotysaubrmknzvzqlnk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_tnoHZCX.jpg
432	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233170/hlss2bhq36zf5mylr0ht.jpg	f	\N
109	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064848/ukktslpoldiqrq1u8mpf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_HCxuGFm.jpg
110	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064857/akx1thewphqmlzjzytvy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_IABGpsR.jpg
112	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064864/ujkzcyk3t8vodg4hxi2d.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_R1HMxfQ.jpg
76	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064875/asmj89a0ymkyqziwpkvz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_1381_far.jpg
77	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064773/gdljxa6jdjqadpvmokot.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_1381_topHanged.jpg
433	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233171/eannvpzbmfpd30kd3hn2.jpg	f	\N
434	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233172/bqudc6kra9mwgi6e3phs.jpg	f	\N
435	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233173/po8ygjsbdrrrtbrvmnmq.jpg	f	\N
117	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064883/dtcoxxdla03topdnn5ha.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_9GNoGqk.jpg
155	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064893/przgmin4ti51xvefhsq9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1337_white_closeup2.jpg
157	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064898/fj4a4gjm9tfznaunw5g4.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1337_white_shuffle.jpg
436	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233174/ctvtdivo1kpgclltqlll.jpg	f	\N
159	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064940/j4534gvxien8axj0vyud.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1360_white_TopHanged.jpg
118	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064945/zr5qzizhb2bhmjnkpd13.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_FsB6ZjL.jpg
119	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064953/v83uyab9ugqr5rpp51uv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_Jijlbao.jpg
122	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064961/ucmfccumf3zm7rgzt7ip.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_h1d5teI.jpg
123	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064968/svavn2u1iyureaxakag3.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_tht6ROV.jpg
126	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064971/zyau8kjihdxverppbwas.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_HfnrUIw.jpg
127	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064977/is7pb0yq3s7zsat9wruf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_IGwMjdP.jpg
129	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064979/sokfaahftc6ycuhmsqu1.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_PVDxYlo.jpg
131	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064981/lpp4bseylhgexcgasm97.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_emN2wbi.jpg
133	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064983/krdkkwagfzxz76ff9hbd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_lcrDudn.jpg
135	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064988/b3unzannhmwn2unwolc9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_5nLvtBN.jpg
137	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064994/juob1jlcow4aph9o3owl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_PAjUhXr.jpg
138	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064996/ew6ke2ob1pjbsxkohrpm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_WAUumoR.jpg
141	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065001/xtacktxbcu3ogohrinag.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_atmH4NF.jpg
142	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065003/patkc6snr1okzla0k2vt.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_gpQsulT.jpg
143	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065008/kiiciqunngt4xt5tis8w.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_hzlo1hT.jpg
437	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233174/vwqlker0fknc8cmu7wdy.jpg	f	\N
146	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065012/tj7xyzlflgdxifc45agh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1337_white_closeup.jpg
147	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065020/lligtiq4ubeplg5yorjj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1337_white_closeup2.jpg
438	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233175/fozh9nibi1em32q5ithu.jpg	f	\N
150	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065022/zohw9um3jq3qcjhhdoim.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1360_White_Cover.jpg
151	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065067/b3hayhauhdbkpblmhu18.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1360_white_TopHanged.jpg
114	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065073/zxogoqub2fif6i21fowk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_YIjRp5J.jpg
160	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750064877/fl15pawrlocqswekzofe.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1360_white_bottomHanged.jpg
439	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233176/eb0sydxrucqqzod9hli1.jpg	f	\N
440	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233177/v0pay3jrapnd03blraqe.jpg	f	\N
171	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065081/y0gyer2ewmfflkvscbqt.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_IMG_8110.jpg
174	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065083/ar8xp38uewj45mzge3lm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_bottomHanged2.jpg
441	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233178/vor2u6ilwualgupcwaqq.jpg	f	\N
175	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065088/deyzjvbi91fry9ggrjsz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_far.jpg
442	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233179/yfa1umxrnunkdwijdhzw.jpg	f	\N
443	1	78	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233180/nzcaet9tmesvqgzandh5.jpg	f	\N
177	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065093/kjghkcdc4icvefajrlgr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_itemBehind2.jpg
179	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065095/borjvwkmmngvo2m3xmeb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_IMG_8103.jpg
180	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065097/uyrxds92vglc0nut7ucu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_IMG_8104.jpg
183	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065100/gd7aadkwrevbri5v5yqq.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_bottomHanged2.jpg
184	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065104/ourtnqfbr5nhxtor2zrv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_closeupHanged.jpg
186	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065107/j69zjwakrnr77ztlu6hv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_cover.jpg
188	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065116/kbmhmsr3od2foyhkitm0.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_itemBehind.jpg
190	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065119/h9dmvkqtr5xhqoioaq7d.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_multi_far.jpg
192	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065126/x9gqj5two2gismkvvq8n.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_multi_shuffle2.jpg
194	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065130/yhcjh5cyofcmajz6fcqd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_bottomHanged.jpg
195	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065133/f2iuyyugkq8qpm3zonj7.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_bottomHanged2.jpg
198	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065136/adfnhvzinwckojtfcjyz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_cover.jpg
199	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065139/jmqusqnog9oumdfe22e8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_cover2.jpg
202	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065141/klahg83rilkkxzgrplex.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_multi_far.jpg
203	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065143/ve35yj4aa6xvlzty93bt.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_multi_shuffle.jpg
205	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065145/orq3cwxljos7gzaowfky.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_topHanged.jpg
207	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065151/e3gdtizjthpenyngqgc1.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_05sYnqi.jpg
209	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065153/h7xvcgxvjns0sxwfea2d.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_ZFx8UmU.jpg
211	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065157/wiwfydxm67ba1ad89f3v.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_kIZMNFi.jpg
213	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065159/xwsyy0wplanaigxzrr71.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_36W4Nl7.jpg
214	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065164/swixbuh7mbxoga5h6a8v.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_LDzcW1u.jpg
166	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065166/l8uqs4gjft7alnoniayb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_itemBehind.jpg
170	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065077/mnh2qzsmj0djhgplavrb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_IMG_8104.jpg
167	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065170/s5vm9ipwrmyfy0fkne7a.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_itemBehind2.jpg
444	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233181/kbx0rle2irboyfsvlsy3.jpg	f	\N
445	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233181/bgwijazhhnaxej3tjffc.jpg	f	\N
235	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065178/zmesk96nslz0dmva39vj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_itemBehind.jpg
237	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065181/fusigdszrl7ivduy6ob7.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_itemBehind3.jpg
238	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065183/rcqlpx01m1vroxsdsqn6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_shuffle.jpg
239	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065185/v9jqsf0glnysaciy6ogk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_shuffle2.jpg
241	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065190/phoy2x8q4qlrc4hr8cig.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_far.jpg
242	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065195/g5tmareyqxkrwqpmu18r.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_itemBehind.jpg
244	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065200/sc8clo5puyutjacukaah.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_itemBehind3.jpg
245	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065202/fh7tyuzuwefdxrgc2ltl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_shuffle.jpg
247	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065204/m5dpoy91kxkgwqec6ldh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_topHanged.jpg
248	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065206/gngfm31leul459fymr2z.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_cover.jpg
250	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065209/jwav5i4kwwtlo2aryfrb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_itemBehind.jpg
251	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065214/iqi4enbt4mwpcvktnpjw.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_itemBehind2.jpg
252	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065219/wvenllueolr5ndbg6pgp.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_shuffle.jpg
446	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233182/orrsmpd1lufecerxxgnt.jpg	f	\N
254	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065221/j36zzjir0klblwa0ox9f.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_topHanged.jpg
255	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065224/sdce0rth7nm7zreulseq.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_cover.jpg
257	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065228/jn3o7iqqjdiqbccfl0xd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_itemBehind.jpg
258	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065232/zxhbi4mgb8rrosxmawwn.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_itemBehind2.jpg
260	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065234/ovube1wslhu4jympjt0z.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_shuffle2.jpg
261	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065239/kpvs58wxnzlztq7vesjg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_topHanged.jpg
262	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065247/m9ycoubuecubtjfxbc1e.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_BM64TVr.jpg
264	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065252/azm4nxqsmsjzxvrajxgz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_PvvSvrG.jpg
265	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065259/q8itppjslkisn8qqgelh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_SuHDzO3.jpg
165	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065265/uimiedeucdqdp9sxoicu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_far.jpg
234	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065175/o5qja6pu11d7idfegx3d.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_far.jpg
217	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065268/hm9qrquktlqy2bbsmypr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_fk74cwZ.jpg
218	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065274/dck5fevbhiky0gwmp6hh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_hqZ8saf.jpg
276	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065286/fg0oaupqsam3ejy55l1w.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer--beige-rod-pock_pMcNRlL.jpg
447	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233183/nqzqhffp9rtnwocikmbe.jpg	f	\N
448	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233184/c66jeowaguxzj2c8a5da.jpg	f	\N
278	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065293/btnr5o05usftrli4jmym.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_8NTgC9g.jpg
449	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233185/qdjso81eao5june2rjku.jpg	f	\N
279	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065299/cvap2zsspdhwfega87oa.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_FFh1fso.jpg
282	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065305/grt5q5fcev0ycayzkch9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_r766i5X.jpg
283	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065313/pq9zgioku5xt9pgpjfig.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer--beige-rod-pock_3CYSjsO.jpg
286	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065319/jmaonxny6r8qhcict6hs.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_T0bY7gS.jpg
287	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065327/faklahanngbttwmtdbh5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_gpKrEZD.jpg
288	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065336/fdrrwf5uetpxhlm3xj1z.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_iTeml7f.jpg
291	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065339/d6nb4oci9tzfc6nft7k5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_closeupHanged.jpg
292	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065343/qi66rvwyt15kcvcmb3gh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_cover.jpg
295	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065346/yikdakx1rfjdqkqqwhjl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_shuffle.jpg
296	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065348/tyfyulapexpz1udnpdwl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_topHanged.jpg
298	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065350/d9qqlkjo6qikps5udd40.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_closeupHanged.jpg
300	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065352/vlfbrbm1lqnthmcwwlbb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_far.jpg
301	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065354/npywsdzhoiwlpmbdm0na.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_itemBehind.jpg
304	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065357/otptsmlp4kyt7ukg4do6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_bo_OqUPYr7.jpg
305	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065359/ovybe2ajgtaq27kew2xr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_closeUp.jpg
308	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065362/mjlbvmd8coevcqxxlwbc.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_itemBehind.jpg
309	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065363/wqygwjksa1qt2euf7raw.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_shuffle.jpg
311	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065366/ac89iwbg8i3asa3ximvb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_bo_ij0JZlI.jpg
313	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065368/btnfgmfyorsdqomcmphj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_cover_22.jpg
315	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065369/dt7doaza7zbwhkc9iwoh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_itemBehind.jpg
169	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065371/qqubgfmnwyjsybffyug3.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_IMG_8103.jpg
274	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065280/pkbnyxhzkp4qdzi15xq8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_fKnrQ2y.jpg
271	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065376/aks1umpnbiyzf76hdbjg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_KSop8tn.jpg
272	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065379/lucxp1hdg7q1gigo6mdi.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_RpsPCd1.jpg
325	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065382/pvd1prl6gu4hul5cwbnc.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_bottomHanged.jpg
328	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065385/zdreu2zrkmokkegvgv99.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_far.jpg
450	1	81	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233186/tdhdxqoefccmnpm1ciom.jpg	f	\N
451	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233187/kwjkfg71f3kxeq7xz4ln.jpg	f	\N
329	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065386/rf5wj3lyaluetd0du23s.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_itemBehind.jpg
452	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233187/c7jkivpfsyg4xgsrok7e.jpg	f	\N
331	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065387/lyjancfwubdmivbf5yly.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_topHanged.jpg
453	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233344/sgkhtl04n6vmob0clpym.jpg	f	\N
333	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065388/lcc2xgibou2kv6rm7ags.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_cover.jpg
454	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233345/kvdgz83nbjrwwje9nf6r.jpg	f	\N
334	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065390/epapfcz1zmvqp4yejf0p.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_far.jpg
337	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065391/zbpjzeo1rcsoxycgrcgo.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_topHanged.jpg
338	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065392/zbcht0w7gbz8ehr0xd5w.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_whitevsoffwhite2.jpg
341	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065395/neibgeu7frjjlrheulit.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_far.jpg
342	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065400/e9ojils7ukulpxoifhem.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_itemBehind.jpg
345	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065403/e1ihncvej2avvppaqr8v.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_whitevsoffwhite2.jpg
346	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065405/hafb3kmulq8qj7q3vbxy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offWhite_shuffle.jpg
348	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065407/f4t59r15k8cxafyzlvzz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offwhite_bot_7ZfDJnw.jpg
350	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065409/pfxspmiljx60xqgi8ssf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offwhite_cover.jpg
352	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065412/mch9lczthr6pzzkajciu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offwhite_itemBehind.jpg
354	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065415/mth5l1vdxhm2fsvmanmx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_bot_kSdXnQD.jpg
355	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065420/wqt0aj0221vugs7rzwle.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_clo_4g6NxAY.jpg
357	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065423/qmzfuxs84yyekduz1cty.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_far.jpg
359	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065425/u8zpxkmmrzri7tzhqxvv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_topHanged-2.jpg
361	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065428/fysiylthtq4uviszqqfn.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_co_62VbjUS.jpg
363	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065430/ercmg0dhejitfhprs9dy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_cover2.jpg
365	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065434/kgh2jjp1jdxg6embjeoi.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_it_OXTkXET.jpg
367	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065436/gcx2dby5mmufayhcp6jd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_bo_Wh0JdkV.jpg
321	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065439/il8fsw1txt8qsekzqpaj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_far.jpg
324	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065381/bxe5k5jkxd4tmliymoy7.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_topHanged.jpg
132	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065444/klqsw6sdczcigl9livm0.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_gKGOQgY.jpg
140	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065446/p7xcven7gxl89b04chlh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_afy7Bbi.jpg
455	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233347/ek0c9n1ukywe2y4ktvff.jpg	f	\N
144	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065450/hxlkvkgxj7xzrcahomoz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_mC9tC9C.jpg
456	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233347/fukzxs6ey0im0mtyuxj4.jpg	f	\N
149	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065454/p5izlmvibqbeeuxx5cqf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1337_white_shuffle.jpg
457	1	80	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233348/y7g0za9p6xitgyvq3rtx.jpg	f	\N
162	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065456/aeej7cht8vbxkyuvvzum.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_Cover.jpg
371	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065458/dz8pu5dzhjxw4rojzf0g.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_far.jpg
430	1	79	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750233168/wwzymxuwi909vc7xzv6y.jpg	f	\N
120	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065463/hymlsanvybijph7pqyjz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_enX7W3n.jpg
372	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065467/cqvuxnd72ikt4z7jkkwv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_it_TQCdTj0.jpg
374	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065472/egwnprphqxentp29onoj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_48061_ivory_far2.jpg
376	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065473/pl83sfqvey9fnrggfpqe.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_48061_ivory_shuffle2.jpg
377	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065476/rxgycnfh8ommf8o9socv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_48061_ivory_topHanged.jpg
380	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065478/vsygmaqhpozn18d3adcz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_K48061-cover-photo.jpg
381	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065561/i2v3dmakvzedc2wu6aq2.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_48061_ivory_far2.jpg
384	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065566/o3b1das9kq4ntkmhrux9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_48061_ivory_topHanged.jpg
385	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065573/ck5mrntlp267gijcinam.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_CloseUp.jpg
387	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065575/n1ar41wisomsd3cgidcj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_K48061-cover-photo.jpg
389	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065577/d8w4cbj3psveezyuk04o.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_2bW8KMS.jpg
391	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065579/jlmxxeauqvoeyme6ludf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_Brap3Ck.jpg
393	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065582/arfmm3iquln58e6i6lq5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_R13FRjK.jpg
395	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065587/xrxndncruqkbgfcbfp3x.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_0xcP5F3.jpg
396	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065592/xlegkjnmtglymnubvamy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_DfSWm5p.jpg
399	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065593/kyyly0on1oge218pjtz6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_abumsDJ.jpg
400	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065597/uqk0ipbv7vfb0i27cc6f.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_o8p9tCF.jpg
116	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065603/g0p0orgm0naeejg9eafu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_3aMPu3Y.jpg
128	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065441/nox4esosaggilw8uwkt8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_Mred4r8.jpg
191	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065609/obgovwjtkn9wgps3uhfb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_multi_shuffle.jpg
200	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065614/qavznmeopjwqjhexdwmo.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_itemBehind.jpg
204	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065617/yojsh0hgpq4phvbvulza.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_multi_shuffle2.jpg
212	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065619/llynmwh2hnpvnfxt1rfk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_ohZAkL1.jpg
267	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065622/c9z5o12fawet4tsn5pax.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_qtoT31z.jpg
273	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065625/mp9ulzbimvrhv4bteuaq.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_e8WWibn.jpg
277	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065631/rqlqur7czodlis2c6htb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_2fCFznk.jpg
281	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065636/e3apznbegalive6wqa4s.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_gCtlqW5.jpg
289	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065638/tnfszxtpdhmbfu7cfaag.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_sGOBInR.jpg
294	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065640/kiacbkkm8gmtz6nsjan1.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_itemBehind.jpg
303	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065642/vdedlkberah3eqvv2qoy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_topHanged.jpg
307	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065644/jtpkfrmizmqte6kgooeh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_far.jpg
316	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065645/aurs5a5sen9txhrropjm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_shuffle.jpg
317	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065646/f5avokwlvr41ontce4nx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_to_wiBU2DM.jpg
322	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065648/mnhbayam6pmomirakckl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_itemBehind.jpg
326	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065650/p7unhl6rpitw1dx7ruw0.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_closeUp.jpg
330	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065651/j0fefr3wklohvkgilthz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_shuffle.jpg
339	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065653/swleccygmu6ha6zc75zm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_bottomHanged.jpg
344	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065654/iu142cyg8dvfefqacqav.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_topHanged.jpg
351	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065656/uczwxcx70avqxk9o2lzd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offwhite_far.jpg
356	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065658/wzdvfs8kxvizpze0xr9l.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_cover.jpg
364	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065661/pqu7bomayb29g8ugrpbx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_far.jpg
368	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065663/w7ouicq2ikdgr7xgehqy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_co_t2aEZ7C.jpg
168	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065666/vuxwkrhlhyu6wpo7jwma.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_topHanged-2.jpg
187	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065606/zpeehanlhydsisbapji5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_cover2.jpg
178	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065668/bzvfm6dtjsz3celtnjzp.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_topHanged-2.jpg
390	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065671/gpzuc0iqivslpisnfjm1.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_6iFxtcT.jpg
394	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065672/duw5n4w53ihaix1mqcsg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_sHwP8HF.jpg
75	13	\N	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065673/loaynmr2saw7kms3dj0q.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_1381_far.jpg
81	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065675/eqxap6awjkjj9ch4hr0m.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_IMG_7956.jpg
386	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065670/skhfzqq8uspfp8d8lj9s.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_CloseUp_-_Copy.jpg
84	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065675/q2tr9zmpbr5yz3c4ky8n.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_1381_topHanged.jpg
87	13	29	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065677/bgyqeifil8yhog5js7vb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM8_IMG_7954.jpg
90	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065678/e1yzuinbdjigk5gcxnfh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_1OEQXJg.jpg
93	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065679/lyzeee3x9y1fkfvqu154.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_Oaowqqy.jpg
97	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065681/xr2lao8xoysmnomospuk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_SgByeDp.jpg
101	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065687/q0pxntc08hukfmqxjt4f.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_6CsJs8T.jpg
104	3	3	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065689/disujev6lgmrqqrnu9ts.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RW8_white-moroccan-tre_KrfXHgV.jpg
108	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065692/uouv34r98kstmmkrlly6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_EenmaIL.jpg
111	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065696/wdr5jili1mxcdnhj6tqb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_McADvf8.jpg
115	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065700/tkhw9bpesc38ugdwjldf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_u1nfdPk.jpg
121	3	5	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065705/wwlp9wsg7oshs7l6m5xh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562RC8_Beige-moroccan-tre_gvH6uSf.jpg
125	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065707/m7yn8ovtfpfpbuizwbcb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_FxpJl54.jpg
130	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065712/nniucvsisu0jmex2wt61.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_bEclQ74.jpg
134	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065716/cmfuz6atgyl9phv0ogwq.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_ohixt18.jpg
139	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065718/tmcy4axeus7i3vqn3c2z.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_ZIXM4Iw.jpg
145	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065719/mtnvzmnrf7bnu8m0l7dj.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_pwuGhvn.jpg
148	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065721/mil4wu0hbgqjoa2zuwtr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1337_white_cover2.jpg
152	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065723/mgafqt1lhqpdwvv0pjcy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1360_white_bottomHanged.jpg
373	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065725/ogz6uepxs9vruk1mkux9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_itemBehind.jpg
378	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065728/pycbbusogra53w6vkfzz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_CloseUp.jpg
78	13	30	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065732/xsshnrrpsleazwna66db.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1381/images/productSKU_RN1381_variantSKU_RN1381RM9_IMG_7950.jpg
185	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065736/obu1iw2jvaeqrvcddsjg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_closeupHanged2.jpg
193	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065738/pfcqlgeqpulahofpwbdz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_topHanged.jpg
197	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065739/gu0bwnf0olxpluygpelr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_closeupHanged2.jpg
201	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065741/zr50hkc89be6z8ctonme.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_itemBehind2.jpg
206	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065743/enhtvjy3fzbjggdimshg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_010v6Ud.jpg
210	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065744/ghhgqqvffw2fr1qzqtmm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_ZSNE9Ya.jpg
215	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065746/jvblp5amkxz95whp6ran.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_S8kxuok.jpg
216	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065747/zzsujwvssjf0gcmidngg.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_fcceeXO.jpg
219	7	40	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065748/mgavvjzanmqvuq6jmz9x.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW9_white-dandelion-em_yD1MOBg.jpg
236	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065750/csgs4yqiocijqwnh676n.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_itemBehind2.jpg
240	9	43	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065751/efbitmpkieyxnbo3fqk2.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW8_1337_white_topHanged.jpg
243	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065754/arrxsenjghcjenpl8wyf.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_itemBehind2.jpg
246	9	44	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065755/ecbm640oexo9oylpyncx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337GW9_1337_white_shuffle2.jpg
249	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065757/r8sgtqqczhibkc6k3mgx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_far.jpg
253	9	45	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065759/qgfof8vj64wxtwrj83ma.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC8_1337_champagne_shuffle2.jpg
256	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065763/g7s1vv3b6d9zql5sykov.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_far.jpg
259	9	46	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065766/wymmrof18hqpufxpxdpu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1337/images/productSKU_RN1337_variantSKU_RN1337RC9_1337_champagne_shuffle.jpg
263	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065769/pbcqnv2m6adqmm2vfo07.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_BjCZPcF.jpg
266	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065772/qrswu1gx6uqvrqm2z5bv.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_dguJMaL.jpg
269	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065775/ajojtrqharfqsn6qx5l0.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_1V7nEgq.jpg
270	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065780/ukslov2tveadxegcvlx5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_HhZQncD.jpg
275	8	48	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065784/d3kbqtgfcvyel2etvsv6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW9_white-floral-sheer-cu_oHoyeUf.jpg
280	8	49	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065787/cbrrzdk54gl0fkblp64z.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC8_sheer-beige-rod-pocke_IFMTVly.jpg
284	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065789/ywkropiyzefo3p8tkwr9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_PBGvYXm.jpg
176	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065790/xvwp0kwhf8iymfric1p0.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_itemBehind.jpg
181	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065734/wxdckg6twp8bi6kipmng.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_IMG_8110.jpg
153	11	33	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065797/v7guypu2lrgzwppmcw6n.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW8_1360_white_far.jpg
290	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065799/j5pjfuxw5uk4jwbe0ygt.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_bottom_wNumWEY.jpg
293	6	51	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065802/amyigmuy0sgzv4csrwnn.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW8_48065_white_far.jpg
297	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065804/hpyg6lmr0igwl3i5oqei.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_bottom_ziy4YNh.jpg
302	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065805/kfuvlgcoqpyxg7bpkmwd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_shuffle.jpg
306	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065807/xsjh6six7czjs6u7d3m8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_cover_22.jpg
310	6	53	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065808/u6mbe3rm0lmqt1oopn7t.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC8_48065_champagne_to_LQUaKPH.jpg
314	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065809/sugnmbuoiaos4a1f8acy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_far.jpg
319	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065811/ne7bms5xz39smrtkslaq.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_closeUp.jpg
323	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065813/yhu1pt8x0mhlebtusepd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_shuffle.jpg
327	2	2	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065815/wm3kde6sihziwum7scxu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW9_24539_white_cover.jpg
332	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065816/gs6lavpr5ykayfulcc8i.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_bottomHanged.jpg
336	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065818/sevd2wu67udxbstlbmou.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_shuffle.jpg
340	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065819/jgxpln16ucrofrvsdxl4.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_cover.jpg
343	4	57	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065821/agklh3a4lpaueauq2ive.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW9_48060_white_shuffle.jpg
349	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065822/o5tiaf9hw2kv1ycokmih.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offwhite_clo_uwc9o4I.jpg
353	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065823/cmtdn65tqgpdzmhpjxi3.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offWhite_shuffle2-2.jpg
358	4	59	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065824/usaaiuzbjcerd7gawqxb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO9_48060_offwhite_itemBehind.jpg
362	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065840/g84virmvqj3riem6p4v7.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_cover.jpg
366	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065842/u5p4tbnij9v7lxkdanlr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_itemBehind.jpg
370	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065844/u8d5x5y6oyom4xruhok6.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_cover2.jpg
375	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065845/rllzzxdvsyydozqpvexd.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_48061_ivory_shuffle.jpg
379	5	66	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065847/nvwxmuq0uwyukmaug1og.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI8_CloseUp_-_Copy.jpg
383	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065848/vvh5pnqytlxl9lyyfulx.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_48061_ivory_shuffle2.jpg
124	12	31	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065849/nwbq9bbzpwt7x2vrdtic.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB8_Brown-and-Beige-flora_7aIMrRk.jpg
136	12	32	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065792/fo1fbohovf3izrujlyiz.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1370/images/productSKU_RN1370_variantSKU_RN1370RB9_Brown-and-Beige-flora_InSCdhl.jpg
196	10	38	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065853/ylzrtqebd33a1i5sgyzh.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM9_1357_closeupHanged.jpg
208	7	39	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065854/fybb07pr0pdqdyj2ts1m.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_rK72010GW8_white-dandelion-em_STt0vly.jpg
285	8	50	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065857/dgskm0a97vyjwtga1rqa.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RC9_sheer-beige-rod-pocke_QeTG9Vk.jpg
299	6	52	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065858/h90c5wgl1v0okpmtdlma.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GW9_48065_white_cover.jpg
312	6	54	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065860/cxw91uliypbosifvzobr.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48065/images/productSKU_RK48065_variantSKU_RK48065GC9_48065_champagne_closeUp.jpg
318	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065861/mxwt5gxnoeqng9omtady.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_bottomHanged.jpg
335	4	56	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065863/lzj5j1llhtueoetevivk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RW8_48060_white_itemBehind.jpg
347	4	58	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065864/hywearqbtofo4egwe3ud.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48060/images/productSKU_RK48060_variantSKU_RK48060RO8_48060_offWhite_shuffle2.jpg
360	5	64	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065865/jzf67ftq1166sjs0ws0u.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC8_48061_champagne_bo_FooV36f.jpg
369	5	65	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065876/awnpey7jpvoqchgm2o94.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061RC9_48061_champagne_cover.jpg
382	5	67	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065878/n2qzjamheeg4rptvtvnt.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK48061/images/productSKU_RK48061_variantSKU_RK48061GI9_48061_ivory_shuffle.jpg
392	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065879/udiccukrfvx1mvbrpzlk.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_DdC7gTY.jpg
397	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065879/gawypcnozibql7bcx7e9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_VuIEV0e.jpg
398	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065880/k1vh5ypvo2ea2uuyvzeo.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_WVDpyh2.jpg
401	7	69	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065881/qve8glya6p3dcb5farz9.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC9_Beige-dandelion-em_sKryjVm.jpg
164	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065882/owrhkq6znc6zo6s7v8jl.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_bottomHanged2.jpg
182	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065850/wiykaimngseox8rs4sw2.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_bottomHanged.jpg
91	3	4	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065883/v3dwzckfscsp8gjhwhr5.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GW9_white-moroccan-tre_FS7sybw.jpg
113	3	6	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065884/wwadkcgukjz5viquydb8.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24562/images/productSKU_RK24562_variantSKU_RK24562GC9_Beige-moroccan-tre_SOciuYm.jpg
154	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065886/edco59ywbl5aeohuyv1n.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1337_white_closeup.jpg
156	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065887/rcrvg9xrifer05ttsdia.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1337_white_cover2.jpg
158	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065888/afdjbjedawezehkdqmao.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1360_White_Cover.jpg
161	11	34	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065890/pmsgmw3sxbvuczcb2pr4.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.GW9_1360_white_far.jpg
163	11	35	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065891/qrwbvm6hs03xld6ili2m.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT8_1360_bottomHanged.jpg
172	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065893/fiocu3ei9haxf8vhbevy.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_Cover.jpg
173	11	36	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065895/xecnkerunxbqkpijmxsa.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1360/images/productSKU_RN1360_variantSKU_RN1360.rT9_1360_bottomHanged.jpg
189	10	37	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065898/xlm9p09v7fmzdjfv8ivu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1357/images/productSKU_RN1357_variantSKU_RN1357RM8_1357_itemBehind2.jpg
268	8	47	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065957/nzugxrdtlq8zgeayfswm.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RN1268/images/productSKU_RN1268_variantSKU_RN1268RW8_white-floral-sheer-cu_uGDoGhD.jpg
320	2	1	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065959/nyjr9nzgorvijdmgrbmb.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK24539/images/productSKU_RK24539_variantSKU_RK24539RW8_24539_white_cover.jpg
388	7	68	0	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750065961/ir53j2naxn2ij3qyhczu.jpg	f	/Users/muhammed/Code/erp/erp/media/product_files/RK72010/images/productSKU_RK72010_variantSKU_RK72010GC8_Beige-dandelion-em_1JB7Tlj.jpg
\.


--
-- Data for Name: marketing_productvariant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productvariant (id, variant_sku, variant_barcode, variant_quantity, variant_price, variant_cost, variant_featured, product_id, variant_datasheet_url, variant_minimum_inventory_level) FROM stdin;
37	RN1357RM8	712179795327	169.00	15.55	\N	t	10	\N	\N
38	RN1357RM9	712179795334	87.00	15.55	\N	t	10	\N	\N
66	RK48061GI8	712179795280	9.00	16.75	\N	t	5	\N	\N
67	RK48061GI9	712179795303	6.00	16.75	\N	t	5	\N	\N
47	RN1268RW8	712179794931	9.00	13.90	\N	t	8	\N	\N
30	RN1381RM9	712179795358	99.00	18.70	\N	t	13	\N	\N
29	RN1381RM8	712179795341	163.00	18.70	\N	t	13	\N	\N
48	RN1268RW9	712179794948	3.00	13.90	\N	t	8	\N	\N
49	RN1268RC8	712179794955	4.00	13.90	\N	t	8	\N	\N
4	RK24562GW9	712179795228	48.00	20.00	15.70	t	3	\N	\N
3	RK24562RW8	712179795204	102.00	10.00	14.20	t	3	\N	\N
6	RK24562GC9	712179795235	46.00	0.00	15.70	t	3	\N	\N
5	RK24562RC8	712179795211	98.00	0.00	14.20	t	3	\N	\N
50	RN1268RC9	712179794962	2.00	13.90	\N	t	8	\N	\N
43	RN1337GW8	712179795013	82.00	26.50	\N	t	9	\N	\N
44	RN1337GW9	712179795037	54.00	26.50	\N	t	9	\N	\N
45	RN1337RC8	712179795020	33.00	25.00	\N	t	9	\N	\N
46	RN1337RC9	712179795044	25.00	25.00	\N	t	9	\N	\N
51	RK48065GW8	712179795112	101.00	22.75	\N	t	6	\N	\N
32	RN1370RB9	712179795372	74.00	22.60	\N	t	12	\N	\N
34	RN1360.GW9	712179795082	69.00	19.00	\N	t	11	\N	\N
31	RN1370RB8	712179795365	184.00	22.60	\N	t	12	\N	\N
52	RK48065GW9	712179795136	42.00	22.75	\N	t	6	\N	\N
33	RN1360.GW8	712179795068	81.00	19.00	\N	t	11	\N	\N
53	RK48065GC8	712179795129	79.00	22.75	\N	t	6	\N	\N
36	RN1360.rT9	712179795075	43.00	17.00	\N	t	11	\N	\N
54	RK48065GC9	712179795143	18.00	22.75	\N	t	6	\N	\N
1	RK24539RW8	712179795099	55.00	12.40	5.00	t	2	\N	\N
2	RK24539RW9	712179795105	95.00	12.40	5.00	t	2	\N	\N
35	RN1360.rT8	712179795051	78.00	17.00	\N	t	11	\N	\N
56	RK48060RW8	712179795242	91.00	14.50	\N	t	4	\N	\N
57	RK48060RW9	712179795266	49.00	14.50	\N	t	4	\N	\N
58	RK48060RO8	712179795259	92.00	14.50	\N	t	4	\N	\N
59	RK48060RO9	712179795273	34.00	14.50	\N	t	4	\N	\N
64	RK48061RC8	712179795297	50.00	15.25	\N	t	5	\N	\N
65	RK48061RC9	712179795310	47.00	15.25	\N	t	5	\N	\N
78	RK12471GW8	712179794979	44.00	13.90	\N	t	1	\N	\N
79	RK12471GW9	712179794993	53.00	13.90	\N	t	1	\N	\N
39	rK72010GW8	712179795150	74.00	20.00	\N	t	7	\N	\N
40	rK72010GW9	712179795174	10.00	20.00	\N	t	7	\N	\N
68	RK72010GC8	712179795167	91.00	20.00	\N	t	7	\N	\N
69	RK72010GC9	712179795181	45.00	20.00	\N	t	7	\N	\N
80	RK12471GC8	712179794986	75.00	13.90	\N	t	1	\N	\N
81	RK12471GC9	712179795006	25.00	13.90	\N	t	1	\N	\N
\.


--
-- Data for Name: marketing_productvariantattribute; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productvariantattribute (id, name) FROM stdin;
1	color
2	size
7	header
\.


--
-- Data for Name: marketing_productvariantattributevalue; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.marketing_productvariantattributevalue (id, product_variant_attribute_value, product_variant_attribute_id, product_variant_id, product_id) FROM stdin;
638	white	1	39	7
639	130cm x 210cm (Each)	2	39	7
640	white	1	40	7
641	130cm x 240cm (Each)	2	40	7
642	beige	1	68	7
643	130cm x 210cm (Each)	2	68	7
644	beige	1	69	7
471	130cm x 210cm (Each)	2	37	10
472	130cm x 240cm (Each)	2	38	10
645	130cm x 240cm (Each)	2	69	7
415	white	1	4	3
417	white	1	3	3
600	130cm x 210cm (Each)	2	64	5
419	beige	1	6	3
421	beige	1	5	3
539	white	1	51	6
544	white	1	52	6
550	beige	1	53	6
557	beige	1	54	6
571	white	1	56	4
572	130cm x 210cm (Each)	2	56	4
575	white	1	57	4
576	130cm x 240cm (Each)	2	57	4
579	off-white	1	58	4
580	130cm x 210cm (Each)	2	58	4
583	off-white	1	59	4
584	130cm x 240cm (Each)	2	59	4
676	130cm x 240cm (Each)	2	30	13
677	130cm x 210cm (Each)	2	29	13
678	white	1	34	11
679	130cm x 240cm (Each)	2	34	11
680	white	1	33	11
681	130cm x 210cm (Each)	2	33	11
682	teal	1	36	11
683	130cm x 240cm (Each)	2	36	11
684	teal	1	35	11
685	130cm x 210cm (Each)	2	35	11
515	white	1	47	8
516	130cm x 210cm (Each)	2	47	8
519	white	1	48	8
520	130cm x 240cm (Each)	2	48	8
599	rod pocket	7	64	5
523	beige	1	49	8
524	130cm x 210cm (Each)	2	49	8
527	beige	1	50	8
528	130cm x 240cm (Each)	2	50	8
529	white	1	43	9
530	130cm x 210cm (Each)	2	43	9
531	white	1	44	9
532	130cm x 240cm (Each)	2	44	9
533	beige	1	45	9
534	130cm x 210cm (Each)	2	45	9
535	beige	1	46	9
536	130cm x 240cm (Each)	2	46	9
604	rod pocket	7	65	5
540	130cm x 210cm (Each)	2	51	6
605	130cm x 240cm (Each)	2	65	5
545	130cm x 240cm (Each)	2	52	6
609	grommet	7	66	5
610	130cm x 210cm (Each)	2	66	5
762	white	1	78	1
551	130cm x 210cm (Each)	2	53	6
763	130cm x 210cm (Each)	2	78	1
764	white	1	79	1
614	grommet	7	67	5
615	130cm x 240cm (Each)	2	67	5
765	130cm x 240cm (Each)	2	79	1
766	beige	1	80	1
558	130cm x 240cm (Each)	2	54	6
767	130cm x 210cm (Each)	2	80	1
768	beige	1	81	1
769	130cm x 240cm (Each)	2	81	1
431	130cm x 240cm (Each)	2	32	12
432	130cm x 210cm (Each)	2	31	12
422	130cm x 210cm (Each)	2	5	3
420	130cm x 240cm (Each)	2	6	3
418	130cm x 210cm (Each)	2	3	3
416	130cm x 240cm (Each)	2	4	3
562	130cm x 240cm (Each)	2	2	2
561	130cm x 210cm (Each)	2	1	2
\.


--
-- Data for Name: operating_machine; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_machine (id, name, max_rpm, domain, workstation_id) FROM stdin;
\.


--
-- Data for Name: operating_machinecredential; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_machinecredential (id, name, api_key, is_active) FROM stdin;
\.


--
-- Data for Name: operating_order; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_order (id, created_at, status, notes, company_id, contact_id, qr_code_url) FROM stdin;
1	2025-06-19 08:24:03.113174+00	pending	This is my first order	\N	1	\N
2	2025-06-19 08:50:26.329001+00	pending	This is the note for the order	1	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1750323027/media/orders/2/qr_order_2.png
5	2025-06-30 09:16:58.794043+00	pending		\N	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1751275020/media/orders/5/qr_order_5.png
12	2025-07-02 06:23:19.426385+00	pending		\N	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1751437400/media/orders/12/qr_order_12.png
13	2025-07-02 07:52:10.728303+00	pending		1	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1751442732/media/orders/13/qr_order_13.png
15	2025-07-02 07:53:42.98999+00	pending	adding a note for the order	\N	2	https://res.cloudinary.com/dnnrxuhts/image/upload/v1751442824/media/orders/15/qr_order_15.png
30	2025-07-11 05:21:12.335252+00	pending		1	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752211274/media/orders/30/qr_order_30.png
31	2025-07-15 11:33:56.450712+00	pending		\N	3	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752579238/media/orders/31/qr_order_31.png
24	2025-07-09 08:43:25.916906+00	pending		\N	\N	\N
25	2025-07-09 09:09:56.774285+00	pending		\N	\N	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752052197/media/orders/25/qr_order_25.png
\.


--
-- Data for Name: operating_orderitem; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_orderitem (id, quantity, price, order_id, product_id, description, status, product_variant_id, qr_code_url) FROM stdin;
1	2.00	22.00	1	7	This is the product note	pending	\N	\N
2	3.00	20.00	2	11	This is the note for the product	pending	\N	\N
7	1.00	2.00	30	1	firat	pending	78	\N
8	3.00	3.00	30	15	firat2	pending	\N	\N
10	20.00	1.00	30	13	this is confetti	pending	30	\N
11	1.00	0.00	30	3		pending	4	\N
12	10.12	10.00	30	2	butterfly	pending	2	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752308392/media/orders/30/items/qr_order_30_orderitem_12_pending.png
13	1.00	20.00	30	3	trellis	pending	6	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752508338/media/orders/30/items/qr_order_30_orderitem_13_pending.png
16	5.00	5.00	31	13		pending	30	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752582818/media/orders/31/items/qr_order_31_orderitem_16_pending.png
14	20.00	30.00	31	12		pending	31	\N
15	10.00	10.00	31	12		pending	32	\N
17	1.00	1.00	31	3	updating description	pending	3	https://res.cloudinary.com/dnnrxuhts/image/upload/v1752592467/media/orders/31/items/qr_order_31_orderitem_17_pending.png
\.


--
-- Data for Name: operating_workstation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.operating_workstation (id, name) FROM stdin;
\.


--
-- Data for Name: todo_task; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.todo_task (id, name, due_date, description, completed, created_at, completed_at, company_id, contact_id) FROM stdin;
2	send resume	2025-03-09		t	2025-03-08 21:19:19.899997+00	2025-03-17 19:19:33.786578+00	\N	\N
3	EIN DELETION	2025-03-09		t	2025-03-08 22:39:23.805917+00	2025-03-17 19:19:41.09257+00	\N	\N
5	Send info to dip textil	2025-03-18		t	2025-03-17 19:25:13.474947+00	2025-03-18 16:17:10.299775+00	\N	\N
1	Pay ups	2025-03-09		t	2025-03-08 21:19:12.343137+00	2025-03-18 16:20:59.482123+00	\N	\N
4	Bring Pippa Ivory 5 m and send Justin David	2025-03-18		t	2025-03-17 19:20:10.931435+00	2025-03-24 14:20:07.147349+00	\N	\N
8	Send cipi more design photos	2025-03-31		t	2025-03-28 15:16:41.773939+00	2025-03-31 13:20:00.119506+00	\N	\N
41	guvercin kaka	2025-07-06		f	2025-07-06 12:30:53.504932+00	2025-07-06 12:30:53.504965+00	\N	\N
9	Send design prices to Cipi and classic flower designs	2025-04-03		t	2025-04-01 11:28:05.96815+00	2025-05-03 18:29:50.550242+00	\N	\N
10	Adem amca kumas	2025-04-03		t	2025-04-02 16:56:24.902603+00	2025-05-03 18:30:08.935387+00	\N	\N
19	Write to them and send goods	2025-07-07		t	2025-06-04 09:09:24.651328+00	2025-07-07 07:27:12.904622+00	3	\N
16	miray fisler	2025-05-30		t	2025-05-30 06:27:16.571431+00	2025-05-30 15:18:39.821351+00	\N	\N
15	Jocelyn	2025-05-28		t	2025-05-28 06:56:35.86623+00	2025-06-04 08:49:22.384526+00	\N	\N
13	Get the order ready	2025-05-26	N1800.G210: $5.5 etegi degistirmek istiyordu sanki\r\nN1439T.G119: 1727 deseni ile ayni renk\r\nN1414T.G105: oldugu gibi\r\n\r\n\r\n2 tane kartela ona gondermemiz lazim	t	2025-05-25 17:15:02.575667+00	2025-06-04 08:51:19.523527+00	1	\N
38	ciprian yaz	2025-07-07		t	2025-07-05 13:29:02.380109+00	2025-07-07 07:27:18.435321+00	\N	\N
12	put hometex contacts in system	2025-05-26	maria chatzicharalampous	t	2025-05-25 17:12:14.86512+00	2025-06-04 09:09:50.276358+00	\N	\N
11	Go get your akbank card	2025-06-05		t	2025-05-25 17:03:41.795139+00	2025-06-05 14:48:20.682078+00	\N	\N
24	write to georgiana	2025-06-13		t	2025-06-13 08:08:14.655122+00	2025-06-15 02:00:34.202888+00	\N	\N
20	Think of Etsy	2025-06-06	size update\r\nthink of strategies	t	2025-06-06 07:33:16.714075+00	2025-06-15 02:00:44.982808+00	\N	\N
18	Send them sample price list	2025-06-16		t	2025-06-04 08:51:49.514919+00	2025-06-16 09:56:21.630718+00	1	\N
43	Follow up with them regarding his order	2025-07-16		f	2025-07-07 07:28:48.050964+00	2025-07-07 07:28:48.051006+00	\N	6
23	Write to woodline	2025-06-13		t	2025-06-13 08:08:07.774443+00	2025-06-16 09:56:44.27834+00	\N	\N
37	Polder Pro forma gonder	2025-07-07		t	2025-07-05 13:27:43.668881+00	2025-07-07 07:29:12.035954+00	\N	\N
42	Woodline ne kadar para gondermis	2025-07-07		t	2025-07-07 06:56:34.890759+00	2025-07-07 08:06:59.208103+00	\N	\N
40	etsy order ship	2025-07-07		t	2025-07-05 16:09:06.194754+00	2025-07-08 04:39:01.575727+00	\N	\N
34	Woodline is asking for lead time	2025-07-02		t	2025-07-02 05:42:48.966829+00	2025-07-02 09:58:49.890877+00	\N	\N
36	Miray 3750 tl aldim de	2025-07-05		t	2025-07-05 08:10:48.397573+00	2025-07-05 13:29:18.091427+00	\N	\N
39	goldex para al	2025-07-07		t	2025-07-05 13:29:11.890153+00	2025-07-08 04:39:07.664778+00	\N	\N
46	call susan	2025-07-10		t	2025-07-10 04:50:22.017382+00	2025-07-10 06:34:46.114108+00	3	\N
45	Let her know about the weight and cost	2025-07-10		t	2025-07-10 04:50:16.558964+00	2025-07-11 05:10:31.743336+00	3	\N
49	ozgur ara	2025-07-11		t	2025-07-11 05:43:42.658215+00	2025-07-12 07:47:50.876375+00	\N	\N
52	hgs	2025-07-14		f	2025-07-14 15:08:58.09193+00	2025-07-14 15:08:58.091943+00	\N	\N
53	tel fatura	2025-07-14		f	2025-07-14 15:09:03.710884+00	2025-07-14 15:09:03.710898+00	\N	\N
50	Merve fotolar	2025-07-12		t	2025-07-12 05:20:35.859065+00	2025-07-14 15:38:50.689743+00	\N	\N
54	atasay	2025-07-15		f	2025-07-15 08:17:42.87896+00	2025-07-15 08:17:42.878992+00	\N	\N
55	make masterdam plans	2025-07-31		f	2025-07-15 13:44:38.357285+00	2025-07-15 13:44:38.357317+00	\N	\N
51	Miray hangi kutudan aldi	2025-07-18		f	2025-07-14 15:08:11.214936+00	2025-07-14 15:08:11.21495+00	\N	\N
47	their order	2025-07-16	include small piece of sample for his next shipment	f	2025-07-10 04:50:47.376015+00	2025-07-10 04:50:47.376044+00	1	\N
35	Techex europe	2025-07-15		f	2025-07-05 08:10:39.901436+00	2025-07-05 08:10:39.90145+00	\N	\N
21	driver license	2025-07-15		f	2025-06-13 08:07:15.537591+00	2025-06-13 08:07:15.537616+00	\N	\N
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
20241130184212	2025-01-22 15:30:01
20241220035512	2025-01-22 15:30:01
20241220123912	2025-01-22 15:30:01
20241224161212	2025-01-22 15:30:01
20250107150512	2025-01-22 15:30:01
20250110162412	2025-01-22 15:30:01
20250123174212	2025-01-24 18:48:42
20250128220012	2025-01-30 06:49:05
20250506224012	2025-06-29 07:09:32
20250523164012	2025-06-29 07:09:33
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

SELECT pg_catalog.setval('public."User_id_seq"', 4, true);


--
-- Name: accounting_assetaccountsreceivable_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_assetaccountsreceivable_id_seq', 3, true);


--
-- Name: accounting_assetcash_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_assetcash_id_seq', 1, false);


--
-- Name: accounting_assetinventorygood_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_assetinventorygood_id_seq', 1, false);


--
-- Name: accounting_assetinventoryrawmaterial_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_assetinventoryrawmaterial_id_seq', 1, false);


--
-- Name: accounting_book_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_book_id_seq', 1, true);


--
-- Name: accounting_cashaccount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_cashaccount_id_seq', 1, false);


--
-- Name: accounting_currencycategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_currencycategory_id_seq', 1, true);


--
-- Name: accounting_currencyexchange_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_currencyexchange_id_seq', 1, false);


--
-- Name: accounting_equitycapital_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equitycapital_id_seq', 1, false);


--
-- Name: accounting_equitydivident_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equitydivident_id_seq', 1, false);


--
-- Name: accounting_equityexpense_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equityexpense_id_seq', 1, false);


--
-- Name: accounting_equityrevenue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_equityrevenue_id_seq', 1, false);


--
-- Name: accounting_expensecategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_expensecategory_id_seq', 1, false);


--
-- Name: accounting_intransfer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_intransfer_id_seq', 1, false);


--
-- Name: accounting_invoice_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_invoice_id_seq', 1, false);


--
-- Name: accounting_liabilityaccountspayable_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_liabilityaccountspayable_id_seq', 1, false);


--
-- Name: accounting_metric_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_metric_id_seq', 1, false);


--
-- Name: accounting_stakeholderbook_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_stakeholderbook_id_seq', 1, false);


--
-- Name: accounting_transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounting_transaction_id_seq', 1, false);


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

SELECT pg_catalog.setval('public.auth_user_id_seq', 1, true);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- Name: authentication_member_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_member_id_seq', 1, false);


--
-- Name: authentication_member_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_member_permissions_id_seq', 1, false);


--
-- Name: authentication_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.authentication_permission_id_seq', 1, false);


--
-- Name: crm_company_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_company_id_seq', 7, true);


--
-- Name: crm_contact_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_contact_id_seq', 6, true);


--
-- Name: crm_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_note_id_seq', 9, true);


--
-- Name: crm_supplier_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crm_supplier_id_seq', 1, true);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 83, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 44, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 80, true);


--
-- Name: marketing_product_collections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_product_collections_id_seq', 1, false);


--
-- Name: marketing_product_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_product_id_seq', 20, true);


--
-- Name: marketing_productcategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productcategory_id_seq', 2, true);


--
-- Name: marketing_productcollection_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productcollection_id_seq', 1, false);


--
-- Name: marketing_productfile_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productfile_id_seq', 457, true);


--
-- Name: marketing_productvariant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productvariant_id_seq', 81, true);


--
-- Name: marketing_productvariantattribute_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productvariantattribute_id_seq', 9, true);


--
-- Name: marketing_productvariantattributevalue_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.marketing_productvariantattributevalue_id_seq', 769, true);


--
-- Name: operating_machine_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_machine_id_seq', 1, false);


--
-- Name: operating_machinecredential_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_machinecredential_id_seq', 1, false);


--
-- Name: operating_order_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_order_id_seq', 31, true);


--
-- Name: operating_orderitem_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_orderitem_id_seq', 17, true);


--
-- Name: operating_workstation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.operating_workstation_id_seq', 1, false);


--
-- Name: todo_task_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.todo_task_id_seq', 55, true);


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
-- Name: accounting_assetaccountsreceivable accounting_assetaccountsreceivable_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetaccountsreceivable_pkey PRIMARY KEY (id);


--
-- Name: accounting_assetcash accounting_assetcash_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetcash
    ADD CONSTRAINT accounting_assetcash_pkey PRIMARY KEY (id);


--
-- Name: accounting_assetinventorygood accounting_assetinventorygood_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventorygood
    ADD CONSTRAINT accounting_assetinventorygood_name_key UNIQUE (name);


--
-- Name: accounting_assetinventorygood accounting_assetinventorygood_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventorygood
    ADD CONSTRAINT accounting_assetinventorygood_pkey PRIMARY KEY (id);


--
-- Name: accounting_assetinventoryrawmaterial accounting_assetinventoryrawmaterial_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventoryrawmaterial
    ADD CONSTRAINT accounting_assetinventoryrawmaterial_pkey PRIMARY KEY (id);


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
-- Name: accounting_cashaccount accounting_cashaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashaccount_pkey PRIMARY KEY (id);


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
-- Name: accounting_currencyexchange accounting_currencyexchange_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencyexchange
    ADD CONSTRAINT accounting_currencyexchange_pkey PRIMARY KEY (id);


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
-- Name: accounting_equityexpense accounting_equityexpense_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_equityexpense_pkey PRIMARY KEY (id);


--
-- Name: accounting_equityrevenue accounting_equityrevenue_invoice_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrevenue_invoice_number_key UNIQUE (invoice_number);


--
-- Name: accounting_equityrevenue accounting_equityrevenue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityrevenue
    ADD CONSTRAINT accounting_equityrevenue_pkey PRIMARY KEY (id);


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
-- Name: accounting_intransfer accounting_intransfer_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_intransfer
    ADD CONSTRAINT accounting_intransfer_pkey PRIMARY KEY (id);


--
-- Name: accounting_invoice accounting_invoice_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_invoice
    ADD CONSTRAINT accounting_invoice_pkey PRIMARY KEY (id);


--
-- Name: accounting_liabilityaccountspayable accounting_liabilityaccountspayable_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liabilityaccountspayable
    ADD CONSTRAINT accounting_liabilityaccountspayable_pkey PRIMARY KEY (id);


--
-- Name: accounting_metric accounting_metric_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_metric
    ADD CONSTRAINT accounting_metric_pkey PRIMARY KEY (id);


--
-- Name: accounting_stakeholderbook accounting_stakeholderbook_member_id_book_id_9e19b25e_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholderbook
    ADD CONSTRAINT accounting_stakeholderbook_member_id_book_id_9e19b25e_uniq UNIQUE (member_id, book_id);


--
-- Name: accounting_stakeholderbook accounting_stakeholderbook_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholderbook
    ADD CONSTRAINT accounting_stakeholderbook_pkey PRIMARY KEY (id);


--
-- Name: accounting_transaction accounting_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_transaction
    ADD CONSTRAINT accounting_transaction_pkey PRIMARY KEY (id);


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
-- Name: authentication_member_permissions authentication_member_pe_member_id_permission_id_9c83b1c2_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member_permissions
    ADD CONSTRAINT authentication_member_pe_member_id_permission_id_9c83b1c2_uniq UNIQUE (member_id, permission_id);


--
-- Name: authentication_member_permissions authentication_member_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member_permissions
    ADD CONSTRAINT authentication_member_permissions_pkey PRIMARY KEY (id);


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
-- Name: authentication_permission authentication_permission_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_permission
    ADD CONSTRAINT authentication_permission_name_key UNIQUE (name);


--
-- Name: authentication_permission authentication_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_permission
    ADD CONSTRAINT authentication_permission_pkey PRIMARY KEY (id);


--
-- Name: crm_company crm_company_name_ff15550e_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_company
    ADD CONSTRAINT crm_company_name_ff15550e_uniq UNIQUE (name);


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
-- Name: crm_supplier crm_supplier_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crm_supplier
    ADD CONSTRAINT crm_supplier_pkey PRIMARY KEY (id);


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
-- Name: marketing_product_collections marketing_product_collec_product_id_productcollec_e8ddc69b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product_collections
    ADD CONSTRAINT marketing_product_collec_product_id_productcollec_e8ddc69b_uniq UNIQUE (product_id, productcollection_id);


--
-- Name: marketing_product_collections marketing_product_collections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product_collections
    ADD CONSTRAINT marketing_product_collections_pkey PRIMARY KEY (id);


--
-- Name: marketing_product marketing_product_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product
    ADD CONSTRAINT marketing_product_pkey PRIMARY KEY (id);


--
-- Name: marketing_product marketing_product_sku_4e12cb16_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product
    ADD CONSTRAINT marketing_product_sku_4e12cb16_uniq UNIQUE (sku);


--
-- Name: marketing_productcategory marketing_productcategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productcategory
    ADD CONSTRAINT marketing_productcategory_pkey PRIMARY KEY (id);


--
-- Name: marketing_productcollection marketing_productcollection_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productcollection
    ADD CONSTRAINT marketing_productcollection_pkey PRIMARY KEY (id);


--
-- Name: marketing_productfile marketing_productfile_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productfile
    ADD CONSTRAINT marketing_productfile_pkey PRIMARY KEY (id);


--
-- Name: marketing_productvariant marketing_productvariant_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariant
    ADD CONSTRAINT marketing_productvariant_pkey PRIMARY KEY (id);


--
-- Name: marketing_productvariantattributevalue marketing_productvariant_variant_id_attribute_id_253d4de3_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattributevalue
    ADD CONSTRAINT marketing_productvariant_variant_id_attribute_id_253d4de3_uniq UNIQUE (product_variant_id, product_variant_attribute_id);


--
-- Name: marketing_productvariantattribute marketing_productvariantattribute_name_aa8e5a9e_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattribute
    ADD CONSTRAINT marketing_productvariantattribute_name_aa8e5a9e_uniq UNIQUE (name);


--
-- Name: marketing_productvariantattribute marketing_productvariantattribute_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattribute
    ADD CONSTRAINT marketing_productvariantattribute_pkey PRIMARY KEY (id);


--
-- Name: marketing_productvariantattributevalue marketing_productvariantattributevalue_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattributevalue
    ADD CONSTRAINT marketing_productvariantattributevalue_pkey PRIMARY KEY (id);


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
-- Name: operating_machinecredential operating_machinecredential_api_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machinecredential
    ADD CONSTRAINT operating_machinecredential_api_key_key UNIQUE (api_key);


--
-- Name: operating_machinecredential operating_machinecredential_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machinecredential
    ADD CONSTRAINT operating_machinecredential_name_key UNIQUE (name);


--
-- Name: operating_machinecredential operating_machinecredential_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machinecredential
    ADD CONSTRAINT operating_machinecredential_pkey PRIMARY KEY (id);


--
-- Name: operating_order operating_order_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_order
    ADD CONSTRAINT operating_order_pkey PRIMARY KEY (id);


--
-- Name: operating_orderitem operating_orderitem_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_orderitem
    ADD CONSTRAINT operating_orderitem_pkey PRIMARY KEY (id);


--
-- Name: operating_workstation operating_workstation_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_workstation
    ADD CONSTRAINT operating_workstation_name_key UNIQUE (name);


--
-- Name: operating_workstation operating_workstation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_workstation
    ADD CONSTRAINT operating_workstation_pkey PRIMARY KEY (id);


--
-- Name: todo_task todo_task_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.todo_task
    ADD CONSTRAINT todo_task_pkey PRIMARY KEY (id);


--
-- Name: accounting_cashaccount unique_book_cashaccount; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT unique_book_cashaccount UNIQUE (book_id, name);


--
-- Name: accounting_assetinventoryrawmaterial unique_name_supplier; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventoryrawmaterial
    ADD CONSTRAINT unique_name_supplier UNIQUE (name, supplier_id);


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
-- Name: accounting_assetaccountsreceivable_book_id_9b813c34; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetaccountsreceivable_book_id_9b813c34 ON public.accounting_assetaccountsreceivable USING btree (book_id);


--
-- Name: accounting_assetaccountsreceivable_company_id_17a2d71d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetaccountsreceivable_company_id_17a2d71d ON public.accounting_assetaccountsreceivable USING btree (company_id);


--
-- Name: accounting_assetaccountsreceivable_contact_id_1f96866a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetaccountsreceivable_contact_id_1f96866a ON public.accounting_assetaccountsreceivable USING btree (contact_id);


--
-- Name: accounting_assetaccountsreceivable_currency_id_3d6903f3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetaccountsreceivable_currency_id_3d6903f3 ON public.accounting_assetaccountsreceivable USING btree (currency_id);


--
-- Name: accounting_assetaccountsreceivable_invoice_id_f7473197; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetaccountsreceivable_invoice_id_f7473197 ON public.accounting_assetaccountsreceivable USING btree (invoice_id);


--
-- Name: accounting_assetcash_book_id_c4df870a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetcash_book_id_c4df870a ON public.accounting_assetcash USING btree (book_id);


--
-- Name: accounting_assetcash_currency_id_0b544ce7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetcash_currency_id_0b544ce7 ON public.accounting_assetcash USING btree (currency_id);


--
-- Name: accounting_assetcash_transaction_id_b8c3e7c9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetcash_transaction_id_b8c3e7c9 ON public.accounting_assetcash USING btree (transaction_id);


--
-- Name: accounting_assetinventorygood_book_id_4d578031; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventorygood_book_id_4d578031 ON public.accounting_assetinventorygood USING btree (book_id);


--
-- Name: accounting_assetinventorygood_currency_id_d6290f64; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventorygood_currency_id_d6290f64 ON public.accounting_assetinventorygood USING btree (currency_id);


--
-- Name: accounting_assetinventorygood_name_fb1611c3_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventorygood_name_fb1611c3_like ON public.accounting_assetinventorygood USING btree (name varchar_pattern_ops);


--
-- Name: accounting_assetinventoryrawmaterial_book_id_687d7f7c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventoryrawmaterial_book_id_687d7f7c ON public.accounting_assetinventoryrawmaterial USING btree (book_id);


--
-- Name: accounting_assetinventoryrawmaterial_currency_id_ae5f5615; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventoryrawmaterial_currency_id_ae5f5615 ON public.accounting_assetinventoryrawmaterial USING btree (currency_id);


--
-- Name: accounting_assetinventoryrawmaterial_supplier_id_859b8417; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_assetinventoryrawmaterial_supplier_id_859b8417 ON public.accounting_assetinventoryrawmaterial USING btree (supplier_id);


--
-- Name: accounting_book_name_6eb9bad9_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_book_name_6eb9bad9_like ON public.accounting_book USING btree (name varchar_pattern_ops);


--
-- Name: accounting_cashaccount_book_id_90f88e20; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_cashaccount_book_id_90f88e20 ON public.accounting_cashaccount USING btree (book_id);


--
-- Name: accounting_cashaccount_currency_id_807cd656; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_cashaccount_currency_id_807cd656 ON public.accounting_cashaccount USING btree (currency_id);


--
-- Name: accounting_currencycategory_code_afbf6634_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencycategory_code_afbf6634_like ON public.accounting_currencycategory USING btree (code varchar_pattern_ops);


--
-- Name: accounting_currencycategory_name_62f10b06_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencycategory_name_62f10b06_like ON public.accounting_currencycategory USING btree (name varchar_pattern_ops);


--
-- Name: accounting_currencyexchange_book_id_3626bd75; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencyexchange_book_id_3626bd75 ON public.accounting_currencyexchange USING btree (book_id);


--
-- Name: accounting_currencyexchange_from_cash_account_id_4e5f1e9c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencyexchange_from_cash_account_id_4e5f1e9c ON public.accounting_currencyexchange USING btree (from_cash_account_id);


--
-- Name: accounting_currencyexchange_to_cash_account_id_25a856c2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_currencyexchange_to_cash_account_id_25a856c2 ON public.accounting_currencyexchange USING btree (to_cash_account_id);


--
-- Name: accounting_equitycapital_book_id_3bb7b1c9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_book_id_3bb7b1c9 ON public.accounting_equitycapital USING btree (book_id);


--
-- Name: accounting_equitycapital_cash_account_id_b51b8a10; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_cash_account_id_b51b8a10 ON public.accounting_equitycapital USING btree (cash_account_id);


--
-- Name: accounting_equitycapital_currency_id_fbe16291; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_currency_id_fbe16291 ON public.accounting_equitycapital USING btree (currency_id);


--
-- Name: accounting_equitycapital_member_id_3a31aa46; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitycapital_member_id_3a31aa46 ON public.accounting_equitycapital USING btree (member_id);


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
-- Name: accounting_equitydivident_member_id_160e5dde; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equitydivident_member_id_160e5dde ON public.accounting_equitydivident USING btree (member_id);


--
-- Name: accounting_equityexpense_book_id_7c69774e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityexpense_book_id_7c69774e ON public.accounting_equityexpense USING btree (book_id);


--
-- Name: accounting_equityexpense_cash_account_id_bbe4c920; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityexpense_cash_account_id_bbe4c920 ON public.accounting_equityexpense USING btree (cash_account_id);


--
-- Name: accounting_equityexpense_category_id_fedd0995; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityexpense_category_id_fedd0995 ON public.accounting_equityexpense USING btree (category_id);


--
-- Name: accounting_equityexpense_currency_id_2e603d51; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_equityexpense_currency_id_2e603d51 ON public.accounting_equityexpense USING btree (currency_id);


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
-- Name: accounting_expensecategory_name_cb9859d6_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_expensecategory_name_cb9859d6_like ON public.accounting_expensecategory USING btree (name varchar_pattern_ops);


--
-- Name: accounting_intransfer_book_id_e5b465c2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_intransfer_book_id_e5b465c2 ON public.accounting_intransfer USING btree (book_id);


--
-- Name: accounting_intransfer_currency_id_fda2e854; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_intransfer_currency_id_fda2e854 ON public.accounting_intransfer USING btree (currency_id);


--
-- Name: accounting_intransfer_destination_id_c6bc6280; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_intransfer_destination_id_c6bc6280 ON public.accounting_intransfer USING btree (destination_id);


--
-- Name: accounting_intransfer_source_id_1faa0353; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_intransfer_source_id_1faa0353 ON public.accounting_intransfer USING btree (source_id);


--
-- Name: accounting_invoice_book_id_3df06427; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_invoice_book_id_3df06427 ON public.accounting_invoice USING btree (book_id);


--
-- Name: accounting_invoice_company_id_38eec83f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_invoice_company_id_38eec83f ON public.accounting_invoice USING btree (company_id);


--
-- Name: accounting_invoice_contact_id_b3fed0ee; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_invoice_contact_id_b3fed0ee ON public.accounting_invoice USING btree (contact_id);


--
-- Name: accounting_invoice_order_id_f3577092; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_invoice_order_id_f3577092 ON public.accounting_invoice USING btree (order_id);


--
-- Name: accounting_liabilityaccountspayable_book_id_333eeb14; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_liabilityaccountspayable_book_id_333eeb14 ON public.accounting_liabilityaccountspayable USING btree (book_id);


--
-- Name: accounting_liabilityaccountspayable_currency_id_c8287afc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_liabilityaccountspayable_currency_id_c8287afc ON public.accounting_liabilityaccountspayable USING btree (currency_id);


--
-- Name: accounting_liabilityaccountspayable_supplier_id_07c161e0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_liabilityaccountspayable_supplier_id_07c161e0 ON public.accounting_liabilityaccountspayable USING btree (supplier_id);


--
-- Name: accounting_metric_book_id_2ff86ad8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_metric_book_id_2ff86ad8 ON public.accounting_metric USING btree (book_id);


--
-- Name: accounting_stakeholderbook_book_id_1ba92948; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_stakeholderbook_book_id_1ba92948 ON public.accounting_stakeholderbook USING btree (book_id);


--
-- Name: accounting_stakeholderbook_member_id_31ff9801; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_stakeholderbook_member_id_31ff9801 ON public.accounting_stakeholderbook USING btree (member_id);


--
-- Name: accounting_transaction_account_id_cd2bdf36; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_transaction_account_id_cd2bdf36 ON public.accounting_transaction USING btree (account_id);


--
-- Name: accounting_transaction_book_id_ef611a98; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_transaction_book_id_ef611a98 ON public.accounting_transaction USING btree (book_id);


--
-- Name: accounting_transaction_currency_id_73d486f9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX accounting_transaction_currency_id_73d486f9 ON public.accounting_transaction USING btree (currency_id);


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
-- Name: authentication_member_permissions_member_id_25ee1da1; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_member_permissions_member_id_25ee1da1 ON public.authentication_member_permissions USING btree (member_id);


--
-- Name: authentication_member_permissions_permission_id_18e23581; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_member_permissions_permission_id_18e23581 ON public.authentication_member_permissions USING btree (permission_id);


--
-- Name: authentication_permission_name_7b07510c_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX authentication_permission_name_7b07510c_like ON public.authentication_permission USING btree (name varchar_pattern_ops);


--
-- Name: crm_company_name_ff15550e_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX crm_company_name_ff15550e_like ON public.crm_company USING btree (name varchar_pattern_ops);


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
-- Name: marketing_product_barcode_1e6ca3df; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_barcode_1e6ca3df ON public.marketing_product USING btree (barcode);


--
-- Name: marketing_product_barcode_1e6ca3df_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_barcode_1e6ca3df_like ON public.marketing_product USING btree (barcode varchar_pattern_ops);


--
-- Name: marketing_product_category_id_c776e438; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_category_id_c776e438 ON public.marketing_product USING btree (category_id);


--
-- Name: marketing_product_collections_product_id_ab29b623; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_collections_product_id_ab29b623 ON public.marketing_product_collections USING btree (product_id);


--
-- Name: marketing_product_collections_productcollection_id_2189399f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_collections_productcollection_id_2189399f ON public.marketing_product_collections USING btree (productcollection_id);


--
-- Name: marketing_product_featured_6995ee9a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_featured_6995ee9a ON public.marketing_product USING btree (featured);


--
-- Name: marketing_product_primary_image_id_2aecf8c8; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_primary_image_id_2aecf8c8 ON public.marketing_product USING btree (primary_image_id);


--
-- Name: marketing_product_sku_4e12cb16_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_sku_4e12cb16_like ON public.marketing_product USING btree (sku varchar_pattern_ops);


--
-- Name: marketing_product_supplier_id_c9957948; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_product_supplier_id_c9957948 ON public.marketing_product USING btree (supplier_id);


--
-- Name: marketing_productfile_product_id_68c8359c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productfile_product_id_68c8359c ON public.marketing_productfile USING btree (product_id);


--
-- Name: marketing_productfile_product_variant_id_74a0d958; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productfile_product_variant_id_74a0d958 ON public.marketing_productfile USING btree (product_variant_id);


--
-- Name: marketing_productvariant_product_id_d830f278; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariant_product_id_d830f278 ON public.marketing_productvariant USING btree (product_id);


--
-- Name: marketing_productvariant_variant_barcode_dad1695f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariant_variant_barcode_dad1695f ON public.marketing_productvariant USING btree (variant_barcode);


--
-- Name: marketing_productvariant_variant_barcode_dad1695f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariant_variant_barcode_dad1695f_like ON public.marketing_productvariant USING btree (variant_barcode varchar_pattern_ops);


--
-- Name: marketing_productvariant_variant_sku_4961a567; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariant_variant_sku_4961a567 ON public.marketing_productvariant USING btree (variant_sku);


--
-- Name: marketing_productvariant_variant_sku_4961a567_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariant_variant_sku_4961a567_like ON public.marketing_productvariant USING btree (variant_sku varchar_pattern_ops);


--
-- Name: marketing_productvariantattribute_name_aa8e5a9e_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattribute_name_aa8e5a9e_like ON public.marketing_productvariantattribute USING btree (name varchar_pattern_ops);


--
-- Name: marketing_productvariantattributevalue_attribute_id_2b0d83d5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattributevalue_attribute_id_2b0d83d5 ON public.marketing_productvariantattributevalue USING btree (product_variant_attribute_id);


--
-- Name: marketing_productvariantattributevalue_product_id_65518724; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattributevalue_product_id_65518724 ON public.marketing_productvariantattributevalue USING btree (product_id);


--
-- Name: marketing_productvariantattributevalue_value_17ca7ef7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattributevalue_value_17ca7ef7 ON public.marketing_productvariantattributevalue USING btree (product_variant_attribute_value);


--
-- Name: marketing_productvariantattributevalue_value_17ca7ef7_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattributevalue_value_17ca7ef7_like ON public.marketing_productvariantattributevalue USING btree (product_variant_attribute_value varchar_pattern_ops);


--
-- Name: marketing_productvariantattributevalue_variant_id_4d257d6d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX marketing_productvariantattributevalue_variant_id_4d257d6d ON public.marketing_productvariantattributevalue USING btree (product_variant_id);


--
-- Name: operating_machine_name_eb93fe62_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_machine_name_eb93fe62_like ON public.operating_machine USING btree (name varchar_pattern_ops);


--
-- Name: operating_machine_workstation_id_057537e7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_machine_workstation_id_057537e7 ON public.operating_machine USING btree (workstation_id);


--
-- Name: operating_machinecredential_api_key_3f9a7431_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_machinecredential_api_key_3f9a7431_like ON public.operating_machinecredential USING btree (api_key varchar_pattern_ops);


--
-- Name: operating_machinecredential_name_ac1cb9ae_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_machinecredential_name_ac1cb9ae_like ON public.operating_machinecredential USING btree (name varchar_pattern_ops);


--
-- Name: operating_order_company_id_3b1f3f9e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_order_company_id_3b1f3f9e ON public.operating_order USING btree (company_id);


--
-- Name: operating_order_contact_id_7bc59ebe; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_order_contact_id_7bc59ebe ON public.operating_order USING btree (contact_id);


--
-- Name: operating_orderitem_order_id_0169742d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_orderitem_order_id_0169742d ON public.operating_orderitem USING btree (order_id);


--
-- Name: operating_orderitem_product_id_bf7c2390; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_orderitem_product_id_bf7c2390 ON public.operating_orderitem USING btree (product_id);


--
-- Name: operating_orderitem_variant_id_e4cca4cf; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_orderitem_variant_id_e4cca4cf ON public.operating_orderitem USING btree (product_variant_id);


--
-- Name: operating_workstation_name_692b14cf_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX operating_workstation_name_692b14cf_like ON public.operating_workstation USING btree (name varchar_pattern_ops);


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

CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);


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
-- Name: accounting_liabilityaccountspayable accounting_assetacco_book_id_5c5fc572_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liabilityaccountspayable
    ADD CONSTRAINT accounting_assetacco_book_id_5c5fc572_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetaccountsreceivable accounting_assetacco_book_id_9b813c34_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetacco_book_id_9b813c34_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetaccountsreceivable accounting_assetacco_company_id_17a2d71d_fk_crm_compa; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetacco_company_id_17a2d71d_fk_crm_compa FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetaccountsreceivable accounting_assetacco_contact_id_1f96866a_fk_crm_conta; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetacco_contact_id_1f96866a_fk_crm_conta FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_liabilityaccountspayable accounting_assetacco_currency_id_14f235b1_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liabilityaccountspayable
    ADD CONSTRAINT accounting_assetacco_currency_id_14f235b1_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetaccountsreceivable accounting_assetacco_currency_id_3d6903f3_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetacco_currency_id_3d6903f3_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetaccountsreceivable accounting_assetacco_invoice_id_f7473197_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetaccountsreceivable
    ADD CONSTRAINT accounting_assetacco_invoice_id_f7473197_fk_accountin FOREIGN KEY (invoice_id) REFERENCES public.accounting_invoice(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_liabilityaccountspayable accounting_assetacco_supplier_id_4b8ecab4_fk_crm_suppl; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_liabilityaccountspayable
    ADD CONSTRAINT accounting_assetacco_supplier_id_4b8ecab4_fk_crm_suppl FOREIGN KEY (supplier_id) REFERENCES public.crm_supplier(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetcash accounting_assetcash_book_id_c4df870a_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetcash
    ADD CONSTRAINT accounting_assetcash_book_id_c4df870a_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetcash accounting_assetcash_currency_id_0b544ce7_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetcash
    ADD CONSTRAINT accounting_assetcash_currency_id_0b544ce7_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetcash accounting_assetcash_transaction_id_b8c3e7c9_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetcash
    ADD CONSTRAINT accounting_assetcash_transaction_id_b8c3e7c9_fk_accountin FOREIGN KEY (transaction_id) REFERENCES public.accounting_transaction(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetinventorygood accounting_assetinve_book_id_4d578031_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventorygood
    ADD CONSTRAINT accounting_assetinve_book_id_4d578031_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetinventoryrawmaterial accounting_assetinve_book_id_687d7f7c_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventoryrawmaterial
    ADD CONSTRAINT accounting_assetinve_book_id_687d7f7c_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetinventoryrawmaterial accounting_assetinve_currency_id_ae5f5615_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventoryrawmaterial
    ADD CONSTRAINT accounting_assetinve_currency_id_ae5f5615_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetinventorygood accounting_assetinve_currency_id_d6290f64_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventorygood
    ADD CONSTRAINT accounting_assetinve_currency_id_d6290f64_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_assetinventoryrawmaterial accounting_assetinve_supplier_id_859b8417_fk_crm_suppl; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_assetinventoryrawmaterial
    ADD CONSTRAINT accounting_assetinve_supplier_id_859b8417_fk_crm_suppl FOREIGN KEY (supplier_id) REFERENCES public.crm_supplier(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_cashaccount accounting_cashaccount_book_id_90f88e20_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashaccount_book_id_90f88e20_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_cashaccount accounting_cashcateg_currency_id_ed9ccd42_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_cashaccount
    ADD CONSTRAINT accounting_cashcateg_currency_id_ed9ccd42_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_currencyexchange accounting_currencye_book_id_3626bd75_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencyexchange
    ADD CONSTRAINT accounting_currencye_book_id_3626bd75_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_currencyexchange accounting_currencye_from_cash_account_id_4e5f1e9c_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencyexchange
    ADD CONSTRAINT accounting_currencye_from_cash_account_id_4e5f1e9c_fk_accountin FOREIGN KEY (from_cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_currencyexchange accounting_currencye_to_cash_account_id_25a856c2_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_currencyexchange
    ADD CONSTRAINT accounting_currencye_to_cash_account_id_25a856c2_fk_accountin FOREIGN KEY (to_cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycap_cash_account_id_b51b8a10_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycap_cash_account_id_b51b8a10_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycap_currency_id_fbe16291_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycap_currency_id_fbe16291_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equitycapital accounting_equitycap_member_id_3a31aa46_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitycapital
    ADD CONSTRAINT accounting_equitycap_member_id_3a31aa46_fk_authentic FOREIGN KEY (member_id) REFERENCES public.authentication_member(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: accounting_equitydivident accounting_equitydiv_member_id_160e5dde_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equitydivident
    ADD CONSTRAINT accounting_equitydiv_member_id_160e5dde_fk_authentic FOREIGN KEY (member_id) REFERENCES public.authentication_member(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_equityexp_cash_account_id_bbe4c920_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_equityexp_cash_account_id_bbe4c920_fk_accountin FOREIGN KEY (cash_account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_equityexpense accounting_equityexp_currency_id_2e603d51_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_equityexpense
    ADD CONSTRAINT accounting_equityexp_currency_id_2e603d51_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: accounting_intransfer accounting_intransfe_currency_id_fda2e854_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_intransfer
    ADD CONSTRAINT accounting_intransfe_currency_id_fda2e854_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_intransfer accounting_intransfe_destination_id_c6bc6280_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_intransfer
    ADD CONSTRAINT accounting_intransfe_destination_id_c6bc6280_fk_accountin FOREIGN KEY (destination_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_intransfer accounting_intransfe_source_id_1faa0353_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_intransfer
    ADD CONSTRAINT accounting_intransfe_source_id_1faa0353_fk_accountin FOREIGN KEY (source_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_intransfer accounting_intransfer_book_id_e5b465c2_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_intransfer
    ADD CONSTRAINT accounting_intransfer_book_id_e5b465c2_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_invoice accounting_invoice_book_id_3df06427_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_invoice
    ADD CONSTRAINT accounting_invoice_book_id_3df06427_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_invoice accounting_invoice_company_id_38eec83f_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_invoice
    ADD CONSTRAINT accounting_invoice_company_id_38eec83f_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_invoice accounting_invoice_contact_id_b3fed0ee_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_invoice
    ADD CONSTRAINT accounting_invoice_contact_id_b3fed0ee_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_invoice accounting_invoice_order_id_f3577092_fk_operating_order_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_invoice
    ADD CONSTRAINT accounting_invoice_order_id_f3577092_fk_operating_order_id FOREIGN KEY (order_id) REFERENCES public.operating_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_metric accounting_metric_book_id_2ff86ad8_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_metric
    ADD CONSTRAINT accounting_metric_book_id_2ff86ad8_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_stakeholderbook accounting_stakehold_book_id_1ba92948_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholderbook
    ADD CONSTRAINT accounting_stakehold_book_id_1ba92948_fk_accountin FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_stakeholderbook accounting_stakehold_member_id_31ff9801_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_stakeholderbook
    ADD CONSTRAINT accounting_stakehold_member_id_31ff9801_fk_authentic FOREIGN KEY (member_id) REFERENCES public.authentication_member(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_transaction accounting_transacti_account_id_cd2bdf36_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_transaction
    ADD CONSTRAINT accounting_transacti_account_id_cd2bdf36_fk_accountin FOREIGN KEY (account_id) REFERENCES public.accounting_cashaccount(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_transaction accounting_transacti_currency_id_73d486f9_fk_accountin; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_transaction
    ADD CONSTRAINT accounting_transacti_currency_id_73d486f9_fk_accountin FOREIGN KEY (currency_id) REFERENCES public.accounting_currencycategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: accounting_transaction accounting_transaction_book_id_ef611a98_fk_accounting_book_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounting_transaction
    ADD CONSTRAINT accounting_transaction_book_id_ef611a98_fk_accounting_book_id FOREIGN KEY (book_id) REFERENCES public.accounting_book(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: authentication_member_permissions authentication_membe_member_id_04e54cd1_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member_permissions
    ADD CONSTRAINT authentication_membe_member_id_04e54cd1_fk_authentic FOREIGN KEY (member_id) REFERENCES public.authentication_member(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: authentication_member_permissions authentication_membe_permission_id_77771c1a_fk_authentic; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authentication_member_permissions
    ADD CONSTRAINT authentication_membe_permission_id_77771c1a_fk_authentic FOREIGN KEY (permission_id) REFERENCES public.authentication_permission(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: marketing_product marketing_product_category_id_c776e438_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product
    ADD CONSTRAINT marketing_product_category_id_c776e438_fk_marketing FOREIGN KEY (category_id) REFERENCES public.marketing_productcategory(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_product_collections marketing_product_co_product_id_ab29b623_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product_collections
    ADD CONSTRAINT marketing_product_co_product_id_ab29b623_fk_marketing FOREIGN KEY (product_id) REFERENCES public.marketing_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_product_collections marketing_product_co_productcollection_id_2189399f_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product_collections
    ADD CONSTRAINT marketing_product_co_productcollection_id_2189399f_fk_marketing FOREIGN KEY (productcollection_id) REFERENCES public.marketing_productcollection(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_product marketing_product_primary_image_id_2aecf8c8_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product
    ADD CONSTRAINT marketing_product_primary_image_id_2aecf8c8_fk_marketing FOREIGN KEY (primary_image_id) REFERENCES public.marketing_productfile(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_product marketing_product_supplier_id_c9957948_fk_crm_supplier_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_product
    ADD CONSTRAINT marketing_product_supplier_id_c9957948_fk_crm_supplier_id FOREIGN KEY (supplier_id) REFERENCES public.crm_supplier(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productfile marketing_productfil_product_id_68c8359c_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productfile
    ADD CONSTRAINT marketing_productfil_product_id_68c8359c_fk_marketing FOREIGN KEY (product_id) REFERENCES public.marketing_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productfile marketing_productfil_product_variant_id_74a0d958_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productfile
    ADD CONSTRAINT marketing_productfil_product_variant_id_74a0d958_fk_marketing FOREIGN KEY (product_variant_id) REFERENCES public.marketing_productvariant(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productvariantattributevalue marketing_productvar_product_id_65518724_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattributevalue
    ADD CONSTRAINT marketing_productvar_product_id_65518724_fk_marketing FOREIGN KEY (product_id) REFERENCES public.marketing_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productvariant marketing_productvar_product_id_d830f278_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariant
    ADD CONSTRAINT marketing_productvar_product_id_d830f278_fk_marketing FOREIGN KEY (product_id) REFERENCES public.marketing_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productvariantattributevalue marketing_productvar_product_variant_attr_4836c067_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattributevalue
    ADD CONSTRAINT marketing_productvar_product_variant_attr_4836c067_fk_marketing FOREIGN KEY (product_variant_attribute_id) REFERENCES public.marketing_productvariantattribute(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: marketing_productvariantattributevalue marketing_productvar_product_variant_id_13dc74f2_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.marketing_productvariantattributevalue
    ADD CONSTRAINT marketing_productvar_product_variant_id_13dc74f2_fk_marketing FOREIGN KEY (product_variant_id) REFERENCES public.marketing_productvariant(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_machine operating_machine_workstation_id_057537e7_fk_operating; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_machine
    ADD CONSTRAINT operating_machine_workstation_id_057537e7_fk_operating FOREIGN KEY (workstation_id) REFERENCES public.operating_workstation(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_order operating_order_company_id_3b1f3f9e_fk_crm_company_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_order
    ADD CONSTRAINT operating_order_company_id_3b1f3f9e_fk_crm_company_id FOREIGN KEY (company_id) REFERENCES public.crm_company(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_order operating_order_contact_id_7bc59ebe_fk_crm_contact_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_order
    ADD CONSTRAINT operating_order_contact_id_7bc59ebe_fk_crm_contact_id FOREIGN KEY (contact_id) REFERENCES public.crm_contact(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_orderitem operating_orderitem_order_id_0169742d_fk_operating_order_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_orderitem
    ADD CONSTRAINT operating_orderitem_order_id_0169742d_fk_operating_order_id FOREIGN KEY (order_id) REFERENCES public.operating_order(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_orderitem operating_orderitem_product_id_bf7c2390_fk_marketing_product_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_orderitem
    ADD CONSTRAINT operating_orderitem_product_id_bf7c2390_fk_marketing_product_id FOREIGN KEY (product_id) REFERENCES public.marketing_product(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: operating_orderitem operating_orderitem_product_variant_id_8ff09ade_fk_marketing; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.operating_orderitem
    ADD CONSTRAINT operating_orderitem_product_variant_id_8ff09ade_fk_marketing FOREIGN KEY (product_variant_id) REFERENCES public.marketing_productvariant(id) DEFERRABLE INITIALLY DEFERRED;


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
-- Name: FUNCTION get_auth(p_usename text); Type: ACL; Schema: pgbouncer; Owner: supabase_admin
--

REVOKE ALL ON FUNCTION pgbouncer.get_auth(p_usename text) FROM PUBLIC;
GRANT ALL ON FUNCTION pgbouncer.get_auth(p_usename text) TO pgbouncer;
GRANT ALL ON FUNCTION pgbouncer.get_auth(p_usename text) TO postgres;


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

