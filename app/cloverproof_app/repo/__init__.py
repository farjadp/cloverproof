"""Data-access layer.

Rule: every function that reads or writes organisation-owned data takes `org_id`
explicitly and filters by it. The only queries without an organisation are the auth
lookups (user by email, session by token hash) and account creation by the CLI.
Functions never commit; the caller's `Database.connection()` block owns the transaction.
"""
