-- Convierte columnas TIMESTAMP WITHOUT TIME ZONE a TIMESTAMPTZ.
-- Esta migracion asume que los valores actuales quedaron guardados en UTC
-- porque Django estaba ejecutandose con USE_TZ = True.
--
-- A diferencia de la version anterior, este script detecta el esquema real
-- donde estan las tablas (priorizando control_horario y despues public) y
-- muestra NOTICE de cada cambio aplicado.

BEGIN;

DO $$
DECLARE
    target_schema text;
    rec record;
BEGIN
    SELECT n.nspname
    INTO target_schema
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'time_entries'
      AND c.relkind = 'r'
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY CASE
        WHEN n.nspname = 'control_horario' THEN 0
        WHEN n.nspname = 'public' THEN 1
        ELSE 2
    END
    LIMIT 1;

    IF target_schema IS NULL THEN
        RAISE EXCEPTION 'No se ha encontrado la tabla time_entries en ningun esquema de usuario.';
    END IF;

    RAISE NOTICE 'Aplicando migracion de timezone sobre el esquema %', target_schema;

    FOR rec IN
        SELECT *
        FROM (
            VALUES
                ('users', 'date_joined'),
                ('companies', 'created_at'),
                ('companies', 'updated_at'),
                ('user_company_membership', 'joined_at'),
                ('company_settings', 'updated_at'),
                ('time_entries', 'clock_in'),
                ('time_entries', 'clock_out'),
                ('time_entry_event', 'timestamp'),
                ('correction_requests', 'request_date'),
                ('correction_requests', 'approval_date'),
                ('correction_requests', 'new_clock_in'),
                ('correction_requests', 'new_clock_out'),
                ('audit_log', 'timestamp')
        ) AS columns_to_fix(table_name, column_name)
    LOOP
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = target_schema
              AND table_name = rec.table_name
              AND column_name = rec.column_name
              AND data_type = 'timestamp without time zone'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.%I ALTER COLUMN %I TYPE TIMESTAMPTZ USING %I AT TIME ZONE ''UTC''',
                target_schema,
                rec.table_name,
                rec.column_name,
                rec.column_name
            );
            RAISE NOTICE 'Convertida %.% a TIMESTAMPTZ', rec.table_name, rec.column_name;
        ELSIF rec.table_name = 'correction_requests'
          AND rec.column_name IN ('new_clock_in', 'new_clock_out')
          AND NOT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema = target_schema
                AND table_name = rec.table_name
                AND column_name = rec.column_name
          ) THEN
            EXECUTE format(
                'ALTER TABLE %I.%I ADD COLUMN %I TIMESTAMPTZ',
                target_schema,
                rec.table_name,
                rec.column_name
            );
            RAISE NOTICE 'Anadida %.% como TIMESTAMPTZ', rec.table_name, rec.column_name;
        ELSE
            RAISE NOTICE 'Sin cambios en %.%', rec.table_name, rec.column_name;
        END IF;
    END LOOP;
END $$;

COMMIT;
