-- 003_rls_lockdown.sql
-- Lock down RLS policies for production security.
--
-- Principle: anon key can INSERT leads/quote_requests only.
--            Authenticated users (admin) get full CRUD.
--            Service role bypasses RLS entirely (Supabase default).

-- ============================================================
-- leads table
-- ============================================================
ALTER TABLE IF EXISTS leads ENABLE ROW LEVEL SECURITY;

-- Drop any existing permissive policies to start clean
DROP POLICY IF EXISTS "anon_insert_leads" ON leads;
DROP POLICY IF EXISTS "authenticated_all_leads" ON leads;
DROP POLICY IF EXISTS "Enable insert for anonymous users" ON leads;
DROP POLICY IF EXISTS "Enable read access for all users" ON leads;

-- Anon can INSERT only (public lead capture form)
CREATE POLICY "anon_insert_leads" ON leads
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated users (admin) can read, update, delete
CREATE POLICY "authenticated_all_leads" ON leads
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- quote_requests table
-- ============================================================
ALTER TABLE IF EXISTS quote_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_insert_quote_requests" ON quote_requests;
DROP POLICY IF EXISTS "authenticated_all_quote_requests" ON quote_requests;
DROP POLICY IF EXISTS "Enable insert for anonymous users" ON quote_requests;
DROP POLICY IF EXISTS "Enable read access for all users" ON quote_requests;

-- Anon can INSERT only (public QuickQuote form)
CREATE POLICY "anon_insert_quote_requests" ON quote_requests
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated users (admin) can read, update, delete
CREATE POLICY "authenticated_all_quote_requests" ON quote_requests
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- episode_quotes table
-- ============================================================
ALTER TABLE IF EXISTS episode_quotes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_insert_episode_quotes" ON episode_quotes;
DROP POLICY IF EXISTS "authenticated_all_episode_quotes" ON episode_quotes;

-- Anon can INSERT (QuickQuote creates quote records before request)
CREATE POLICY "anon_insert_episode_quotes" ON episode_quotes
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated users get full access
CREATE POLICY "authenticated_all_episode_quotes" ON episode_quotes
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- installment_schedules table
-- ============================================================
ALTER TABLE IF EXISTS installment_schedules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_insert_installment_schedules" ON installment_schedules;
DROP POLICY IF EXISTS "authenticated_all_installment_schedules" ON installment_schedules;

CREATE POLICY "anon_insert_installment_schedules" ON installment_schedules
    FOR INSERT
    TO anon
    WITH CHECK (true);

CREATE POLICY "authenticated_all_installment_schedules" ON installment_schedules
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- audit_logs table
-- ============================================================
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_insert_audit_logs" ON audit_logs;
DROP POLICY IF EXISTS "authenticated_all_audit_logs" ON audit_logs;

-- Anon can INSERT (public QuickQuote writes audit events)
CREATE POLICY "anon_insert_audit_logs" ON audit_logs
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated users can read audit logs
CREATE POLICY "authenticated_all_audit_logs" ON audit_logs
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- Pricing data tables (read-only for anon)
-- ============================================================
-- These tables contain public pricing data loaded by the estimator.
-- Anon can SELECT only. Authenticated users get full access.

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'hospital_packages',
            'obstetrician_fees',
            'anaesthetist_fees',
            'paediatrician_fees',
            'pathology_fees',
            'ultrasound_radiology',
            'midwife_doula_fees',
            'medications_supplements',
            'pricing_sources'
        ])
    LOOP
        -- Only apply if table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tbl) THEN
            EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);

            -- Drop existing policies
            EXECUTE format('DROP POLICY IF EXISTS "anon_select_%s" ON %I', tbl, tbl);
            EXECUTE format('DROP POLICY IF EXISTS "authenticated_all_%s" ON %I', tbl, tbl);
            EXECUTE format('DROP POLICY IF EXISTS "Enable read access for all users" ON %I', tbl);

            -- Anon: SELECT only
            EXECUTE format(
                'CREATE POLICY "anon_select_%s" ON %I FOR SELECT TO anon USING (true)',
                tbl, tbl
            );

            -- Authenticated: full access
            EXECUTE format(
                'CREATE POLICY "authenticated_all_%s" ON %I FOR ALL TO authenticated USING (true) WITH CHECK (true)',
                tbl, tbl
            );
        END IF;
    END LOOP;
END
$$;
