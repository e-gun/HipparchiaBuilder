-- use this to (re)initialize by hand
-- \connect hipparchiaDB

CREATE EXTENSION pg_trgm;

DROP TABLE IF EXISTS authors;

CREATE TABLE authors
(
  universalid character(6),
  language character varying(10),
  idxname character varying(128),
  akaname character varying(128),
  shortname character varying(128),
  cleanname character varying(128),
  genres character varying(512),
  recorded_date character varying(64),
  converted_date integer,
  location character varying(128)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE authors
  OWNER TO hippa_wr;
GRANT ALL ON TABLE authors TO hippa_wr;
GRANT SELECT ON TABLE authors TO hippa_rd;

-- Table: works

DROP TABLE IF EXISTS works;

CREATE TABLE works
(
  universalid character(10),
  title character varying(512),
  language character varying(10),
  publication_info text,
  levellabels_00 character varying(64),
  levellabels_01 character varying(64),
  levellabels_02 character varying(64),
  levellabels_03 character varying(64),
  levellabels_04 character varying(64),
  levellabels_05 character varying(64),
  workgenre character varying(32),
  transmission character varying(32),
  worktype character varying(32),
  provenance character varying(64),
  recorded_date character varying(64),
  converted_date integer,
  wordcount integer,
  firstline integer,
  lastline integer,
  authentic boolean
)
WITH (
  OIDS=FALSE
);
ALTER TABLE works
  OWNER TO hippa_wr;
GRANT ALL ON TABLE works TO hippa_wr;
GRANT SELECT ON TABLE works TO hippa_rd;


-- Table: greek_dictionary

DROP TABLE IF EXISTS greek_dictionary;

CREATE TABLE greek_dictionary (
    entry_name character varying(256),
    metrical_entry character varying(256),
    unaccented_entry character varying(256),
    id_number real,
    pos character varying(64),
    translations text,
    entry_body text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE greek_dictionary
  OWNER TO hippa_wr;
GRANT ALL ON TABLE greek_dictionary TO hippa_wr;
GRANT SELECT ON TABLE greek_dictionary TO hippa_rd;

-- Index: gkentryword_index

DROP INDEX IF EXISTS gkentryword_index;

CREATE INDEX gkentryword_index
  ON greek_dictionary
  USING btree
  (entry_name COLLATE pg_catalog."default");

-- Table: greek_lemmata

DROP TABLE IF EXISTS greek_lemmata;

CREATE TABLE greek_lemmata
(
  dictionary_entry character varying(64),
  xref_number integer,
  derivative_forms text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE greek_lemmata
  OWNER TO hippa_wr;
GRANT ALL ON TABLE greek_lemmata TO hippa_wr;
GRANT SELECT ON TABLE greek_lemmata TO hippa_rd;

-- Index: gklemm_idx

DROP INDEX IF EXISTS gklemm_idx;

CREATE INDEX gklemm_idx
  ON greek_lemmata
  USING btree
  (dictionary_entry COLLATE pg_catalog."default");
  
-- Table: greek_morphology

DROP TABLE IF EXISTS greek_morphology;

CREATE TABLE greek_morphology
(
  observed_form character varying(64),
  xrefs character varying(128),
  prefixrefs character varying(128),
  possible_dictionary_forms jsonb,
  related_headwords character varying(256)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE greek_morphology
  OWNER TO hippa_wr;
GRANT ALL ON TABLE greek_morphology TO hippa_wr;
GRANT SELECT ON TABLE greek_morphology TO hippa_rd;

-- Index: gkmorph_idx

DROP INDEX IF EXISTS gkmorph_idx;

CREATE INDEX gkmorph_idx
  ON greek_morphology
  USING btree (observed_form COLLATE pg_catalog."default");

-- Table: latin_dictionary

DROP TABLE IF EXISTS latin_dictionary;

CREATE TABLE latin_dictionary (
    entry_name character varying(256),
    metrical_entry character varying(256),
    id_number real,
    entry_key character varying(64),
    pos character varying(64),
    translations text,
    entry_body text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE latin_dictionary
  OWNER TO hippa_wr;
GRANT ALL ON TABLE latin_dictionary TO hippa_wr;
GRANT SELECT ON TABLE latin_dictionary TO hippa_rd;

-- Index: latinentry_idx

DROP INDEX IF EXISTS latinentry_idx;

CREATE INDEX latinentry_idx
  ON latin_dictionary
  USING btree (entry_name COLLATE pg_catalog."default");

-- Table: latin_lemmata

DROP TABLE IF EXISTS latin_lemmata;

CREATE TABLE latin_lemmata
(
  dictionary_entry character varying(64),
  xref_number integer,
  derivative_forms text
)
WITH (
  OIDS=FALSE
);

ALTER TABLE latin_lemmata
  OWNER TO hippa_wr;
GRANT ALL ON TABLE latin_lemmata TO hippa_wr;
GRANT SELECT ON TABLE latin_lemmata TO hippa_rd;

-- Index: latlemm_idx

DROP INDEX IF EXISTS latlemm_idx;

CREATE INDEX latlemm_idx
  ON latin_lemmata
  USING btree
  (dictionary_entry COLLATE pg_catalog."default");

-- Table: latin_morphology

DROP TABLE IF EXISTS latin_morphology;

CREATE TABLE latin_morphology
(
    observed_form             character varying(64),
    xrefs                     character varying(128),
    prefixrefs                character varying(128),
    possible_dictionary_forms jsonb,
    related_headwords         character varying(256)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE latin_morphology
  OWNER TO hippa_wr;
GRANT ALL ON TABLE latin_morphology TO hippa_wr;
GRANT SELECT ON TABLE latin_morphology TO hippa_rd;

-- Index: latmorph_idx

DROP INDEX IF EXISTS latmorph_idx;

CREATE INDEX latmorph_idx
  ON latin_morphology
  USING btree
  (observed_form COLLATE pg_catalog."default");
