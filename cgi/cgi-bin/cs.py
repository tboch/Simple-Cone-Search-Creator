#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Thomas Boch (github: tboch) - thomas dot boch at astro dot unistra dot fr
# Affiliation: Observatoire astronomique de Strasbourg


"""
CGI script for Simple-Cone-Search-Creator project

This script enables a Cone Search service
from a data structure previously created using
the ingestion script ingest.py
"""

import cgi
import cgitb
import json
import sys, os
import csv
import math
import numpy
import healpy

cgitb.enable() # for debugging purposes, can be commented

def print_header():
    """
    Print header of HTTP request
    """
    print "Content-type: text/xml;content=x-votable"
    print

def output_error(msg, exit=True):
    print_header()
    print votable_start()
    print '<INFO ID="Error" name="Error" value="%s" />' % (msg)
    print votable_end()
    if exit:
        sys.exit()
    
def xml_preamble():
    return '<?xml version="1.0"?>'

def votable_start():
    return '<VOTABLE version="1.1" xmlns="http://www.ivoa.net/xml/VOTable/v1.1">'
    
def votable_end():
    return '</VOTABLE>'

def resource_start():
    return '<RESOURCE>'

def resource_end():
    return '</RESOURCE>'

def table_start():
    return '<TABLE>'

def table_end():
    return '</TABLE>'

def table_end():
    return '</TABLE>'

def data_start():
    """
    return open tags for DATA and TABLEDATA
    """
    return '<DATA><TABLEDATA>'

def data_end():
    """
    return closing tags for DATA and TABLEDATA
    """
    return '</TABLEDATA></DATA>'

def radec2thetaphi(ra, dec):
    return math.radians((90-dec)), math.radians(ra) 


def get_cgi_config_file_name():
    return 'cgi-config.json'

def get_metafile_path(root):
    return os.path.join(root, 'metadata.json')

def get_path(root, nside, ipix):
    """
    Return path of file for given root directory,
    nside and ipix
    """
    
    dir_idx = (ipix/10000)*10000;
    return os.path.join(root, "nside%d/dir%d/npix%d.csv" % (nside, dir_idx, ipix))    

def fields_as_votable(fields):
    sb = []
    for f in fields:
        sb.append('<FIELD name="%s"' % (f['name']))
        for attr in ('ucd', 'unit', 'datatype', 'arraysize', 'ID'):
            if attr in f:
                sb.append(' %s="%s"' % (attr, f[attr]))
        
        sb.append(' />\n')

    return ''.join(sb)

def sph_dist(ra1, dec1,ra2, dec2):
    """
    Compute the spherical distance between 2 pairs of coordinates
    using the Haversine formula
    
    Input coordinates are in decimal degrees
    Output: angular distance in decimal degrees
    """
    ra1_rad  = math.radians(ra1)
    dec1_rad = math.radians(dec1)
    ra2_rad  = math.radians(ra2)
    dec2_rad = math.radians(dec2)

    d = math.sin((dec1_rad-dec2_rad)/2)**2;
    d += math.sin((ra1_rad-ra2_rad)/2)**2 * math.cos(dec1_rad)*math.cos(dec2_rad)

    return math.degrees(2*math.asin(math.sqrt(d)))

# check if config file is present
conf_path = get_cgi_config_file_name()
data_path = None
if not os.path.exists(conf_path):
    # perhaps data is in the same directory
    metadata_path = get_metafile_path('.')
    if not os.path.exists(metadata_path):
        output_error('Service error: could not find config file %s' % (conf_path))
    else:
        data_path = os.path.abspath('.')
else:
    with open(conf_path) as h:
        config = json.loads(h.read())
    
    data_path = os.path.abspath(config['dataPath'])
    
metadata_path = get_metafile_path(data_path)
if not os.path.exists(metadata_path):
    output_error('Service error: could not find metadata file %s' % (metadata_path))
    
with open(metadata_path) as h:
    metadata = json.loads(h.read())
        
# retrieve info
fields = metadata['fields']
nside = metadata['nside']

# retrieve parameters
params = cgi.FieldStorage()
# check presence of compulsory parameters
for param_name in ('RA', 'DEC', 'SR'):
    if param_name not in params:
        output_error('Missing compulsory parameter %s' % (param_name))
        
ra_str  = params.getfirst('RA')
dec_str = params.getfirst('DEC')
sr_str  = params.getfirst('SR')

# Check if parameters are floating values
try:
    ra = float(ra_str)
except:
    output_error("Could not parse value '%s' of RA parameter as a float" % (ra_str))
try:
    dec = float(dec_str)
except:
    output_error("Could not parse value '%s' of DEC parameter as a float" % (dec_str))
try:
    sr = float(sr_str)
except:
    output_error("Could not parse value '%s' of SR parameter as a float" % (sr_str))

# Check if parameters are withing sensible range
if ra<0 or ra>=360:
    output_error('Value for RA parameter should be in range [0, 360[')
if dec<-90 or dec>90:
    output_error('Value for DEC parameter should be in range [-90, 90]')
if sr<0:
    output_error('value for SR parameter should be >=0')

# find RA and DEC indexes (needed to compute distance to center)
ra_idx = None
dec_idx = None
k = -1
for f in fields:
    k += 1
    if ra_idx and dec_idx:
        break
    if 'ucd' in f:
        if f['ucd']=='POS_EQ_RA_MAIN':
            ra_idx = k
        elif f['ucd']=='POS_EQ_DEC_MAIN':
            dec_idx = k
    
if ra_idx==None:
    output_error("Could not find field with ucd='POS_EQ_RA_MAIN'. Missing info in %s" % (metadata_path))

if dec_idx==None:
    output_error("Could not find field with ucd='POS_EQ_DEC_MAIN'. Missing info in %s" % (metadata_path))


print_header()
print xml_preamble()
print votable_start()
print resource_start()
print table_start()
print fields_as_votable(fields)
print data_start()

# healpix query to retrieve data in requested cone
theta, phi = radec2thetaphi(ra, dec) 
vec = healpy.ang2vec(theta, phi)
healpix_cells = healpy.query_disc(nside, vec, math.radians(sr), inclusive=True, nest=True)
for ipix in healpix_cells:
    ipix_path = get_path(data_path, nside, ipix)
    if not os.path.exists(ipix_path):
        continue
    
    with open(ipix_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        # test distance
        for row in reader:
            row_ra  = float(row[ra_idx])
            row_dec = float(row[dec_idx])
            dist = sph_dist(ra, dec, row_ra, row_dec)
            if dist>sr:
                continue 
            print '<TR><TD>',
            print '</TD><TD>'.join(row),
            print '</TD></TR>'

        
#print '<!-- ' + str(healpix_cells) + '-->'


print data_end()
print table_end()
print resource_end()
print votable_end()
