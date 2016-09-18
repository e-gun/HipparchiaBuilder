# HipparchiaBuilder

convert tlg-e and phi author files into a database

this database can be read by HipparchiaServer

you will need:

    the tlg and phi data (presumably from a cd-rom disk)
        your config file will need to point to this data properly

    the lexical data 
        Diogenes contains a folder named Perseus_Data
        some cleaning of random bad characters in that data is required [basically, strip all high value ascii chars]
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

    python 3.5
        pip
        flask
        psycopg2
        bs4
    postgresql9

see also: HipparchiaBSD
    these are starter files for installing hipparchia into a virtualbox (or a non-virtual one) running BSD 10.3
