-- V2-21 Postgres append-only triggers (architecture §3.2). Shared DDL stays in 002_v2_core.sql.
CREATE OR REPLACE FUNCTION ledger_raise_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'ledger is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION ledger_outbox_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.event_id IS DISTINCT FROM OLD.event_id
     OR NEW.stream IS DISTINCT FROM OLD.stream
     OR NEW.envelope_json IS DISTINCT FROM OLD.envelope_json
     OR NEW.created_at IS DISTINCT FROM OLD.created_at
     OR NEW.seq IS DISTINCT FROM OLD.seq THEN
    RAISE EXCEPTION 'ledger is append-only';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION ledger_charges_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.charges_status = 'PENDING' THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'ledger is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS orders_no_delete ON orders;
CREATE TRIGGER orders_no_delete BEFORE DELETE ON orders
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS order_events_no_delete ON order_events;
CREATE TRIGGER order_events_no_delete BEFORE DELETE ON order_events
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS fills_no_delete ON fills;
CREATE TRIGGER fills_no_delete BEFORE DELETE ON fills
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS trades_no_delete ON trades;
CREATE TRIGGER trades_no_delete BEFORE DELETE ON trades
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS charges_no_delete ON charges;
CREATE TRIGGER charges_no_delete BEFORE DELETE ON charges
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS risk_decisions_no_delete ON risk_decisions;
CREATE TRIGGER risk_decisions_no_delete BEFORE DELETE ON risk_decisions
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS recon_runs_no_delete ON recon_runs;
CREATE TRIGGER recon_runs_no_delete BEFORE DELETE ON recon_runs
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();

DROP TRIGGER IF EXISTS order_events_no_update ON order_events;
CREATE TRIGGER order_events_no_update BEFORE UPDATE ON order_events
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS fills_no_update ON fills;
CREATE TRIGGER fills_no_update BEFORE UPDATE ON fills
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS risk_decisions_no_update ON risk_decisions;
CREATE TRIGGER risk_decisions_no_update BEFORE UPDATE ON risk_decisions
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS recon_runs_no_update ON recon_runs;
CREATE TRIGGER recon_runs_no_update BEFORE UPDATE ON recon_runs
  FOR EACH ROW EXECUTE FUNCTION ledger_raise_append_only();
DROP TRIGGER IF EXISTS charges_no_update ON charges;
CREATE TRIGGER charges_no_update BEFORE UPDATE ON charges
  FOR EACH ROW EXECUTE FUNCTION ledger_charges_guard();
DROP TRIGGER IF EXISTS outbox_no_update ON outbox;
CREATE TRIGGER outbox_no_update BEFORE UPDATE ON outbox
  FOR EACH ROW EXECUTE FUNCTION ledger_outbox_guard();
