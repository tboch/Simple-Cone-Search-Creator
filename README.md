Simple-Cone-Search-Creator
==========================

Introduction
------------

Simple Cone Search Creator (SCSC) aims at providing a very easy way to set up a Cone Search service, complying with the IVOA standard described at http://www.ivoa.net/documents/REC/DAL/ConeSearch-20080222.html
This allows to quickly setup a service queriable by position by various tools and libraries (Topcat, Aladin, etc).

Requirements are minimal on the server side: you will only need an HTTP server able to execute CGI scripts (no database, no Tomcat needed).

Python libraries requirements: numpy, healpy

Getting started
---------------

SCSC is made of 2 parts :

- an ingestor
- a CGI Python script 

The starting point is a CSV file (with or without initial header line) 
having at least right ascension and declination in decimal degrees in the ICRS coordinate system.

1.  Ingestion

    The ingestor takes a data file formatted in CSV, and converts it in an ad-hoc set of files, later used by the CGI script.
    Usage:
    
        ./ingest.py --csvfile CSVFILE --outputdir OUTPUTDIR --rafield RAFIELD --decfield DECFIELD [--idfield IDFIELD] [--debug]
    
    CSVFILE
     : (compulsory) path to the CSV input file
    OUTPUTDIR
     : (compulsory) directory that will contain the data converted to the ad-hoc format
    RAFIELD
     : (compulsory) name or index (zero-based) in the CSV file of the field holding the right ascension
    DECFIELD
     : (compulsory) name or index (zero-based) in the CSV file of the field holding the declination
    IDFIELD
     : (optional)   name or index (zero-based) in the CSV file of the field holding the identifier string. If not given, the script will generate an identifier based on the row index.
    
    Example:
    
        ./ingest.py --csvfile ../test-data/2MASX.csv --outputdir 2MASX-cs --rafield RAJ2000 --decfield DEJ2000 --idfield 2MASX
        
    If the CSV file has no header, the script will automatically create column names (col_0, col_1, ...).
    
    Once the data has been parsed and converted, a small summary of the parsing is displayed. If some rows were ignored, 
    you might want to re-run the ingestion adding the `--debug` flag to get more information.
    
    You might want to review the file OUTPUTDIR/metadata.json which describes the different fields. Feel free to update this file 
    as long as you do not change the number of fields and do not remove the description of FIELDS holding UCD POS_EQ_RA_MAIN and POS_EQ_DEC_MAIN.
    
    A `cgi-config.json` file is also created in OUTPUTDIR.

2.  CGI Python script

    The CGI is responsible to parse the cone search query, and outputs data accordingly, in compliance with the Cone Search standard defined in this document.

    Once the data has been ingested, here is how to test the cone search service:
    * `cd TEMP_DIR`
    * `mkdir cgi-bin`
    * Copy `cs.py` and `OUTPUTDIR/cgi-config.json` to `TEMP_DIR/cgi-bin`
    * Launch from `TEMP_DIR` the command  `python -m CGIHTTPServer 1234`
    * Open the link http://0.0.0.0:1234/cgi-bin/cs.py?RA=0&DEC=0&SR=0 in your browser.
      You should see an XML file with the list of <FIELD> elements.
    * If the previous step is working, we can go further and test the service in [Aladin](http://aladin.u-strasbg.fr/) :
      + Launch Aladin
      + Go to File-->Open
      + Click on *Others* tab, at the bottom right of the window, and select *Generic Cone Search query*
      + Enter `http://0.0.0.0:1234/cgi-bin/cs.py?` as the base URL, enter a target and a radius and Submit
      + You should be able to visualize sources in the requested cone
    * We might also try our service in [TOPCAT](http://www.star.bris.ac.uk/~mbt/topcat/):
      + Launch TOPCAT
      + Go to File-->Load Table
      + Go to Data Sources-->Cone Search
      + Enter `http://0.0.0.0:1234/cgi-bin/cs.py?` as the Cone URL (bottom panel of the window)
      + Enter a position and a radius and click on OK
      + A new table with corresponding sources should appear in TOPCAT
        


    Deploying the cone search service on production server is just a matter of copying `OUTPUTDIR` data, CGI script `cs.py` along with `cgi-config.json` 
    and ajusting path in `cgi-config.json`


Compliance with Cone search standard
------------------------------------

Generated cone search services have been tested against VO Paris (http://voparis-validator.obspm.fr/) and NVO validators (http://nvo.ncsa.uiuc.edu/dalvalidate/csvalidate.html).

Limitations
-----------

We have tested successfully our scripts to generate a Cone Search service from a 18 million rows CSV file. (PPMX data with 26 columns)
Ingestion of the data took 15 minutes.
Querying a 10 degrees radius cone centered on LMC outputs the 113,686 corresponding rows in 7 seconds.
Queries with a radius smaller than 1 degree are usually returned in less than 1 second.

Feedback
--------

Please send your comments, questions, bug reports, etc to thomas.boch@astro.unistra.fr
