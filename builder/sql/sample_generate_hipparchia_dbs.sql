-- Role: hippa_wr

-- DROP ROLE hippa_wr;

CREATE ROLE hippa_wr LOGIN
  ENCRYPTED PASSWORD 'yourpasshere'
  NOSUPERUSER INHERIT CREATEDB NOCREATEROLE NOREPLICATION;

-- Role: hippa_rd

-- DROP ROLE hippa_rd;

CREATE ROLE hippa_rd LOGIN
  ENCRYPTED PASSWORD 'yourotherpasshere'
  NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;

-- Database: "hipparchiaDB"

DROP DATABASE "hipparchiaDB";

CREATE DATABASE "hipparchiaDB"
  WITH OWNER = hippa_wr
       ENCODING = 'UTF8'
       TABLESPACE = pg_default
       CONNECTION LIMIT = -1;


-- Table: public.authors

-- DROP TABLE public.authors;

CREATE TABLE public.authors
(
  universalid character(6),
  language character varying(10),
  idxname character varying(128),
  akaname character varying(128),
  shortname character varying(128),
  cleanname character varying(128),
  genres character varying(512),
  floruit character varying(8),
  location character varying(128)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.authors
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.authors TO hippa_wr;
GRANT SELECT ON TABLE public.authors TO hippa_rd;

-- Table: public.works

-- DROP TABLE public.works;

CREATE TABLE public.works
(
  universalid character(10),
  title character varying(256),
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
  wordcount integer,
  authentic boolean
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.works
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.works TO hippa_wr;
GRANT SELECT ON TABLE public.works TO hippa_rd;

-- Table: public.greek_dictionary

-- DROP TABLE public.greek_dictionary;

CREATE TABLE public.greek_dictionary
(
  entry_name character varying(64),
  unaccented_entry character varying(64),
  id_number character varying(8),
  entry_type character varying(8),
  entry_options "char",
  entry_body text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.greek_dictionary
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.greek_dictionary TO hippa_wr;
GRANT SELECT ON TABLE public.greek_dictionary TO hippa_rd;

-- Index: public.gkentryword_index

-- DROP INDEX public.gkentryword_index;

CREATE INDEX gkentryword_index
  ON public.greek_dictionary
  USING btree
  (entry_name COLLATE pg_catalog."default");

-- Table: public.greek_lemmata

-- DROP TABLE public.greek_lemmata;

CREATE TABLE public.greek_lemmata
(
  dictionary_entry character varying(64),
  xref_number integer,
  derivative_forms text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.greek_lemmata
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.greek_lemmata TO hippa_wr;
GRANT SELECT ON TABLE public.greek_lemmata TO hippa_rd;

-- Index: public.gklemm_idx

-- DROP INDEX public.gklemm_idx;

CREATE INDEX gklemm_idx
  ON public.greek_lemmata
  USING btree
  (dictionary_entry COLLATE pg_catalog."default");
  
-- Table: public.greek_morphology

-- DROP TABLE public.greek_morphology;

CREATE TABLE public.greek_morphology
(
  observed_form character varying(64),
  possible_dictionary_forms text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.greek_morphology
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.greek_morphology TO hippa_wr;
GRANT SELECT ON TABLE public.greek_morphology TO hippa_rd;

-- Index: public.gkmorph_idx

-- DROP INDEX public.gkmorph_idx;

CREATE INDEX gkmorph_idx
  ON public.greek_morphology
  USING btree
  (observed_form COLLATE pg_catalog."default");

-- Table: public.latin_dictionary

-- DROP TABLE public.latin_dictionary;

CREATE TABLE public.latin_dictionary
(
  entry_name character varying(64),
  id_number character varying(8),
  entry_type character varying(8),
  entry_key character varying(64),
  entry_options "char",
  entry_body text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.latin_dictionary
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.latin_dictionary TO hippa_wr;
GRANT SELECT ON TABLE public.latin_dictionary TO hippa_rd;

-- Index: public.latinentry_idx

-- DROP INDEX public.latinentry_idx;

CREATE INDEX latinentry_idx
  ON public.latin_dictionary
  USING btree
  (entry_name COLLATE pg_catalog."default");

-- Table: public.latin_lemmata

-- DROP TABLE public.latin_lemmata;

CREATE TABLE public.latin_lemmata
(
  dictionary_entry character varying(64),
  xref_number integer,
  derivative_forms text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.latin_lemmata
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.latin_lemmata TO hippa_wr;
GRANT SELECT ON TABLE public.latin_lemmata TO hippa_rd;

-- Index: public.latlemm_idx

-- DROP INDEX public.latlemm_idx;

CREATE INDEX latlemm_idx
  ON public.latin_lemmata
  USING btree
  (dictionary_entry COLLATE pg_catalog."default");

-- Table: public.latin_morphology

-- DROP TABLE public.latin_morphology;

CREATE TABLE public.latin_morphology
(
  observed_form character varying(64),
  possible_dictionary_forms text
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.latin_morphology
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.latin_morphology TO hippa_wr;
GRANT SELECT ON TABLE public.latin_morphology TO hippa_rd;

-- Index: public.latmorph_idx

-- DROP INDEX public.latmorph_idx;

CREATE INDEX latmorph_idx
  ON public.latin_morphology
  USING btree
  (observed_form COLLATE pg_catalog."default");



