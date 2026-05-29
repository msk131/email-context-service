-- Initial data for email-context-service
-- Insert basic rows into all domain tables so the app can start with sample data.
-- Adjust or remove explicit IDs if your DB uses different sequences.

BEGIN;

-- Firms
INSERT INTO firms (id, name, created_at) VALUES
  (1, 'Acme Accounting', NOW()),
  (2, 'Beta Books', NOW());

-- Accountants (users)
INSERT INTO accountants (id, firm_id, email, password_hash, role, created_at) VALUES
  (1, 1, 'admin@acme.example', 'pbkdf2:placeholder', 'superuser', NOW()),
  (2, 1, 'john.doe@acme.example', 'pbkdf2:placeholder', 'accountant', NOW()),
  (3, 2, 'admin@beta.example', 'pbkdf2:placeholder', 'firm_admin', NOW());

-- Clients
INSERT INTO clients (id, firm_id, name, external_email, created_at) VALUES
  (1, 1, 'Client One', 'client1@example.com', NOW()),
  (2, 1, 'Client Two', 'client2@example.com', NOW()),
  (3, 2, 'Beta Client', 'betaclient@example.com', NOW());

-- Emails (recipients is JSON)
INSERT INTO emails (id, client_id, sender_accountant_id, sender_email, recipients, subject, body, direction, sent_at) VALUES
  (1, 1, 2, 'john.doe@acme.example', '["client1@example.com"]'::json, 'Quarterly Report', 'Here is the quarterly report for Q1.', 'outbound', NOW() - INTERVAL '7 days'),
  (2, 1, NULL, 'client1@example.com', '["john.doe@acme.example"]'::json, 'Question about invoice', 'Can you confirm the invoice #1234?', 'inbound', NOW() - INTERVAL '6 days');

-- Email summaries (summary_encrypted is a placeholder string)
INSERT INTO email_summaries (id, client_id, summary_encrypted, actors, concluded_discussions, open_action_items, email_count_analyzed, token_in, token_out, refreshed_at) VALUES
  (1, 1, 'ENCRYPTED_PLACEHOLDER_SUMMARY', '[]'::json, '[]'::json, '[]'::json, 2, 0, 0, NOW());

-- Summarization logs
INSERT INTO summarization_logs (id, client_id, email_count, token_in, token_out, started_at, completed_at) VALUES
  (1, 1, 2, 0, 0, NOW() - INTERVAL '1 hour', NOW() - INTERVAL '30 minutes');

COMMIT;

-- NOTE: If your DB uses SERIAL/SEQUENCE for primary keys, you may need to set the sequence values
-- to avoid conflicts, e.g. (Postgres):
-- SELECT setval(pg_get_serial_sequence('firms','id'), (SELECT MAX(id) FROM firms));
