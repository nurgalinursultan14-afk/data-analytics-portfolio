-- Normalized schema: one row per posting, child tables for the many-valued fields.
CREATE TABLE postings (
    id            TEXT PRIMARY KEY,
    company       TEXT NOT NULL,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,      -- Software, Data/AI, Hardware, Product, Quant
    active        INTEGER NOT NULL,   -- 1 = still open at snapshot time
    date_posted   TEXT,               -- ISO date
    date_updated  TEXT,               -- ISO date (for closed postings ~ date marked inactive)
    sponsorship   TEXT,               -- 'Other' means not stated
    ats           TEXT,               -- applicant tracking system, from the apply URL
    url           TEXT
);
CREATE TABLE posting_terms     (id TEXT REFERENCES postings(id), term TEXT);
CREATE TABLE posting_locations (id TEXT REFERENCES postings(id), location TEXT,
                                state TEXT, country TEXT, is_remote INTEGER);
CREATE TABLE posting_degrees   (id TEXT REFERENCES postings(id), degree TEXT);

-- From git history (extract_history.py): snapshot dates when each posting was first seen / first closed.
CREATE TABLE status_history (id TEXT PRIMARY KEY, first_seen TEXT, first_closed TEXT);

CREATE INDEX ix_terms_term ON posting_terms(term);
CREATE INDEX ix_loc_state  ON posting_locations(state);

-- Convenience view: Summer 2027 internships only.
CREATE VIEW s27 AS
SELECT p.* FROM postings p
WHERE EXISTS (SELECT 1 FROM posting_terms t WHERE t.id = p.id AND t.term = 'Summer 2027');
