Simple-Cone-Search-Creator
==========================

Simple Cone Search Creator (SCSC) aims at providing a very easy way to set up a Cone Search service, complying with the IVOA standard described at http://www.ivoa.net/documents/REC/DAL/ConeSearch-20080222.html
This allows to quickly setup a service queriable by position by various tools and libraries (Topcat, Aladin, astroquery)

Requirements are minimal on the server side: you'll only need an HTTP server able to execute CGI scripts (no database, no Tomcat needed).

Python libraries requirements:

SCSC is made of 2 parts :

- an ingestor
- a CGI Python script 


1. Ingestion

The ingestor takes a data file formatted in CSV, and converts it in an ad-hoc set of files, later used by the CGI script. 


2. CGI Python script

The CGI is responsabile to parse the cone search query, and outputs data accordingly, in compliance with the Cone Search standard defined in this document.

Once the data has been ingested 

python -m CGIHTTPServer





Generated services have been tested against xxx validators