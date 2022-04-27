#!/usr/bin/env python3
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


def output_error(votable, msg, exit=True):
    info="""
    <INFO ID="Error" name="Error" value="{}" />""".format(msg)
    print (votable.format(content=info))
    if exit:
        sys.exit()
    

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
    return os.path.join(root, "nside{}/dir{}/npix{}.csv".format(
      nside, dir_idx, ipix))    

def make_fields_as_votable(fields):
    sb = ""
    for f in fields:
        attributes=""
        for attr_name in ('ucd', 'unit', 'datatype', 'arraysize', 'ID'):
            if attr_name in f:
                attributes+="""{}="{}" """.format(attr_name, f[attr_name])
        sb+="""
      <FIELD name="{name}" {attributes}/>""".format(
          name=f['name'],
          attributes=attributes
          )

    return sb

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

def main():
    votable="""Content-type: text/xml;content=x-votable\n
<?xml version="1.0"?>
<VOTABLE version="1.1" xmlns="http://www.ivoa.net/xml/VOTable/v1.1">{content}
</VOTABLE>
"""

    content="""
  <RESOURCE>
    <TABLE>{fields}
      <DATA>
        <TABLEDATA>{tabledata}
        </TABLEDATA>
      </DATA>
    </TABLE>
  </RESOURCE>
"""

    tabledata=""
    
    # check if config file is present
    script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    conf_path = os.path.join(script_dir, get_cgi_config_file_name())
    data_path = None
    if not os.path.exists(conf_path):
        # perhaps data is in the same directory
        metadata_path = get_metafile_path('.')
        if not os.path.exists(metadata_path):
            output_error(votable, 
            'Service error: could not find config file {}'.format(
              conf_path))
        else:
            data_path = os.path.abspath('.')
    else:
        with open(conf_path) as h:
            config = json.loads(h.read())
        
        data_path = os.path.abspath(config['dataPath'])
        
    metadata_path = get_metafile_path(data_path)
    if not os.path.exists(metadata_path):
        output_error(votable, 
          'Service error: could not find metadata file {}'.format(
          metadata_path))
        
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
            output_error(votable, 
              "Missing compulsory parameter {}".format(param_name))
            
    ra_str  = params.getfirst('RA')
    dec_str = params.getfirst('DEC')
    sr_str  = params.getfirst('SR')

    # Check if parameters are floating values
    try:
        ra = float(ra_str)
    except:
        output_error(votable, 
          "Could not parse value '{}' of RA parameter as a float".format(
          ra_str))
    try:
        dec = float(dec_str)
    except:
        output_error(votable, 
          "Could not parse value '{}' of DEC parameter as a float".format(
          dec_str))
    try:
        sr = float(sr_str)
    except:
        output_error(votable, 
          "Could not parse value '{}' of SR parameter as a float".format(
          sr_str))

    # Check if parameters are withing sensible range
    if ra<0 or ra>=360:
        output_error(votable, 
          'Value for RA parameter should be in range [0, 360[')
    if dec<-90 or dec>90:
        output_error(votable, 
          'Value for DEC parameter should be in range [-90, 90]')
    if sr<0:
        output_error(votable, 
          'Value for SR parameter should be >=0')

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
        output_error(votable, 
          """Could not find field with ucd='POS_EQ_RA_MAIN'. 
          Missing info in {}""".format(metadata_path))

    if dec_idx==None:
        output_error(votable, 
          """Could not find field with ucd='POS_EQ_DEC_MAIN'. 
          Missing info in {}""".format(metadata_path))



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
                tabledata+="""
          <TR>
            <TD>{row_data}</TD>
          </TR>""".format(
                row_data="""</TD>
            <TD>""".join(row))

    fields_as_votable=make_fields_as_votable(fields)

    print (votable.format(
      content=content.format(
        fields=fields_as_votable, 
        tabledata=tabledata)
        ))

        
#print '<!-- ' + str(healpix_cells) + '-->'
if __name__ == "__main__":
    main()


