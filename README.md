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

in addition to the build environment itself, you will need data to insert into it:

    the TLG_E and PHI00005 and PHI7 files (presumably from cd-rom disks)
        your config file will need to point to this data properly

    the lexical data 
        see HipparchiaBSD on how to acquire the lexical data
        [00_FreeBSD_initial_setup.txt or 01_macOS_hipparchia_installation.txt under 'ACQUIRING THE LEXICA']

    minimum software requirements:
        python 3.6
            pip
            flask
            psycopg2
            bs4
        postgresql9.6
