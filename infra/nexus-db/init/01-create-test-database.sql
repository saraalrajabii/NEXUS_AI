-- Runs once, the first time the nexus-db volume is created.
-- A separate database for automated tests, so tests never touch real data.
CREATE DATABASE nexus_test;
