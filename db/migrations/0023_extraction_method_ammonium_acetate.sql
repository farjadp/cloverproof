-- 0023: soil-test extraction method `ammonium-acetate` (NH4OAc), added to the engine in
-- 0.3.0 (PR #41) for Ontario potassium: the OMAFA-accredited K test uses an ammonium
-- acetate extract (pack ca-on v1; docs/agronomist-todo.md #17). The DB enum mirrors the
-- engine enum (test_migrations.test_enums_match_engine), so a lab value recorded with
-- this method can be stored and fed to the engine unchanged (CLAUDE.md rule 7: method
-- stored on every value).
--
-- `alter type ... add value` cannot be used in the same transaction that adds it, so
-- this file only adds the label. Catalog-only: no row is rewritten.

set local role cp_migrator;

alter type extraction_method add value if not exists 'ammonium-acetate' after 'mehlich-3';
