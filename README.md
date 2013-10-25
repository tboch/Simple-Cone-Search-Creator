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
        ./ingest.py --csvfile CSVFILE --outputdir OUTPUTDIR
        
    (compulsory)
    (optional)
        
    If the CSV file has no header, the script will automatically create column names (col_0, col_1, ...).
    
    Once the data has been parsed and converted, a small summary of the parsing is displayed. If some rows were ignored, 
    you might want to re-run the ingestion adding the `--debug` flag to get more information.

2.  CGI Python script

    
    The CGI is responsabile to parse the cone search query, and outputs data accordingly, in compliance with the Cone Search standard defined in this document.

    Once the data has been ingested 

python -m CGIHTTPServer



Compliance with Cone search standard
------------------------------------

Generated cone search services have been tested against VO Paris (http://voparis-validator.obspm.fr/) and NVO validators (http://nvo.ncsa.uiuc.edu/dalvalidate/csvalidate.html).

Limitations
-----------

We have tested successfully our scripts to generate a Cone Search service from a 10 million rows CSV file. (PPMX data with 26 columns)
Ingestion of the data took xxx.
Querying a 10 degrees cone centered on LMC outputs the nnn corresponding rows in mmm seconds. 
