-- V2-08b planner extras bag. Triggers for this version are installed in migrate.py
-- (CREATE TRIGGER bodies contain ';' which the statement splitter must not cut).
ALTER TABLE entry_plans ADD COLUMN payload_json TEXT;
