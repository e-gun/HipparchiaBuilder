# HipparchiaBuilder

convert greek and latin data files into a searchable database

this database can be read by HipparchiaServer

you will need:

    the TLG_E and PHI00005 and PHI7 data (presumably from cd-rom disks)
        your config file will need to point to this data properly

    the lexical data 
        Diogenes contains a folder named Perseus_Data
        some cleaning of random bad characters in that data is required [basically, strip all non-ascii chars]
        Diogenes can be found via 
            https://community.dur.ac.uk/p.j.heslin/Software/Diogenes/
        your config file will need to point to this data properly
        here's what i was using:
            $ ls -c1 -s
            total 930888
             77536 english_dictionary.txt
            221736 greek-analyses.txt
            106608 greek-lemmata.txt
             49856 greek_liddell_scott_a-de.xml
             59312 greek_liddell_scott_di-kath.xml
             67392 greek_liddell_scott_kai-pew.xml
             78160 greek_liddell_scott_pe-ww.xml
             74920 latin-analyses.txt
             29712 latin-lemmata.txt
             83368 latin_lewis_short_a-k.xml
             81768 latin_lewis_short_l-z.xml

    python 3.6
        pip
        flask
        psycopg2
        bs4
    postgresql9 [ideally 9.6]

see also: HipparchiaBSD
    these are starter files for installing hipparchia into a virtualbox (or a non-virtual one) running BSD 10.3

```

Five databases possible:
    Greek [6625 works]
    Latin [836 works]
    Papyri [49235 works]
    Inscriptions I (earlier and Greeker) [139970 works]
    Inscriptions II (later and more Westerly) [40174 works]

```