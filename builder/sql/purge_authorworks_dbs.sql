-- Table: public.authors

DROP TABLE public.authors;

CREATE TABLE public.authors
(
  universalid character(6),
  language character varying(10),
  idxname character varying(128),
  akaname character varying(128),
  shortname character varying(128),
  cleanname character varying(128),
  genres character varying(512),
  recorded_date character varying(64),
  converted_date character varying(8),
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

DROP TABLE public.works;

CREATE TABLE public.works
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
  converted_date character varying(8),
  wordcount integer,
  firstline integer,
  lastline integer,
  authentic boolean
)
WITH (
  OIDS=FALSE
);
ALTER TABLE public.works
  OWNER TO hippa_wr;
GRANT ALL ON TABLE public.works TO hippa_wr;
GRANT SELECT ON TABLE public.works TO hippa_rd;
-- see: http://stackoverflow.com/questions/4202135/how-to-drop-multiple-tables-in-postgresql-using-a-wildcard


CREATE OR REPLACE FUNCTION massdelete(IN _schema TEXT, IN _parttionbase TEXT) 
RETURNS void 
LANGUAGE plpgsql
AS
$$
DECLARE
    row     record;
BEGIN
    FOR row IN 
        SELECT
            table_schema,
            table_name
        FROM
            information_schema.tables
        WHERE
            table_type = 'BASE TABLE'
        AND
            table_schema = _schema
        AND
            table_name ILIKE (_parttionbase || '%')
    LOOP
    	EXECUTE 'DROP TABLE ' || quote_ident(row.table_schema) || '.' || quote_ident(row.table_name);
        RAISE INFO 'Dropped table: %', quote_ident(row.table_schema) || '.' || quote_ident(row.table_name);
    END LOOP;
END;
$$;

SELECT massdelete('public', 'gr____w___');
SELECT massdelete('public', 'lt____w___');

-- if you get a memory error, then turn the following on and off selectively...

SELECT massdelete('public', 'gr___0w___');
SELECT massdelete('public', 'gr___1w___');
SELECT massdelete('public', 'gr___2w___');
SELECT massdelete('public', 'gr___3w___');
SELECT massdelete('public', 'gr___4w___');
SELECT massdelete('public', 'gr___5w___');
SELECT massdelete('public', 'gr___6w___');
SELECT massdelete('public', 'gr___7w___');
SELECT massdelete('public', 'gr___8w___');
SELECT massdelete('public', 'gr___9w___');
