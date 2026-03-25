-- Convierte columnas TIMESTAMP WITHOUT TIME ZONE a TIMESTAMPTZ.
-- Esta migración asume que los valores actuales quedaron guardados en UTC
-- porque Django estaba ejecutándose con USE_TZ = True.

BEGIN;

SET search_path = control_horario;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'users'
          AND column_name = 'date_joined'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE users ALTER COLUMN date_joined TYPE TIMESTAMPTZ USING date_joined AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'companies'
          AND column_name = 'created_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE companies ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE ''UTC''';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'companies'
          AND column_name = 'updated_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE companies ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'user_company_membership'
          AND column_name = 'joined_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE user_company_membership ALTER COLUMN joined_at TYPE TIMESTAMPTZ USING joined_at AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'company_settings'
          AND column_name = 'updated_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE company_settings ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'time_entries'
          AND column_name = 'clock_in'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE time_entries ALTER COLUMN clock_in TYPE TIMESTAMPTZ USING clock_in AT TIME ZONE ''UTC''';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'time_entries'
          AND column_name = 'clock_out'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE time_entries ALTER COLUMN clock_out TYPE TIMESTAMPTZ USING clock_out AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'time_entry_event'
          AND column_name = 'timestamp'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE time_entry_event ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE ''UTC''';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'request_date'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ALTER COLUMN request_date TYPE TIMESTAMPTZ USING request_date AT TIME ZONE ''UTC''';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'approval_date'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ALTER COLUMN approval_date TYPE TIMESTAMPTZ USING approval_date AT TIME ZONE ''UTC''';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'new_clock_in'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ALTER COLUMN new_clock_in TYPE TIMESTAMPTZ USING new_clock_in AT TIME ZONE ''UTC''';
    ELSIF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'new_clock_in'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ADD COLUMN new_clock_in TIMESTAMPTZ';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'new_clock_out'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ALTER COLUMN new_clock_out TYPE TIMESTAMPTZ USING new_clock_out AT TIME ZONE ''UTC''';
    ELSIF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'correction_requests'
          AND column_name = 'new_clock_out'
    ) THEN
        EXECUTE 'ALTER TABLE correction_requests ADD COLUMN new_clock_out TIMESTAMPTZ';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'audit_log'
          AND column_name = 'timestamp'
          AND data_type = 'timestamp without time zone'
    ) THEN
        EXECUTE 'ALTER TABLE audit_log ALTER COLUMN timestamp TYPE TIMESTAMPTZ USING timestamp AT TIME ZONE ''UTC''';
    END IF;
END $$;

COMMIT;
