# HipparchiaBuilder

convert greek and latin data files into a searchable database

```

Five databases possible:
    Greek [6625 works]
    Latin [836 works]
    Papyri [49235 works]
    Inscriptions I (earlier and Greeker) [139970 works]
    Inscriptions II (later and more Westerly) [40174 works]

```

these databases can be read by HipparchiaServer

in order to prepare the build environment you should look at HipparchiaBSD first

there you will find starter files for installing hipparchia onto macOS or into a virtualbox (or a non-virtual one) running BSD 10.3 or 11.0

in addition to the build environment itself, you will need:

data to insert into the builder:

```
    the TLG_E and/or PHI00005 and/or PHI7 files (presumably from cd-rom disks)
        your config file will need to point to this data properly

    the lexical data 
        see HipparchiaBSD on how to acquire the lexical data
        [00_FreeBSD_initial_setup.txt or 01_macOS_hipparchia_installation.txt under 'ACQUIRING THE LEXICA']

    HipparchiaServer knows what it does and does not know: any combination of core data is acceptable, but unusual
    combinations of data can be expected to produce unusual results (e.g., only Greek Documentary papyri and the Latin
    lexicon and no Latin grammar): some items are more or less meant to go together. But it is possible to install
    just a subset of one corpus: only Homer, for example.

```

minimum software requirements:
```
    python 3.6
        pip
        flask
        psycopg2
        bs4
        websockets
    postgresql 9.6
```

hardware recommendations:
```
	a multicore processor
	c. 1G RAM per thread (to be on the very, very safe side)
	SSD with 15G spare space: 12G for the output and 3G for the input.
	[du -h -d 0 inside of /usr/local/var/postgres outputs '12G']

	minimum requirements are not presently known, but 512MB of RAM is probably required to run HipparchiaServer with 1 thread

```