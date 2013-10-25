#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Thomas Boch (github: tboch) - thomas dot boch at astro dot unistra dot fr
# Affiliation: Observatoire astronomique de Strasbourg

"""
CSV ingestion for Simple-Cone-Search-Creator project

This script takes a CSV file as input
and creates a directory-like structure based on HEALPix tesselation,
each directory containing the data of the given HEALPix cell.

This structure will then be used by the CGI script to serve a Cone Search service.

Input parameters:

csv_file (compulsory)
output_dir (compulsory)
ra_field (compulsory)
dec_field (compulsory)
id_field
csv_sep_char

"""

import argparse
import csv
import sys, os
import numpy
import healpy
import datetime
import json

MAX_ROWS_IN_BUFFER = 50000 # max rows before writing to disk

def get_csv_sample(csv_path, sample_size=100):
    sample = ''
    nb_rows_read = 0
    h = open(csv_path)
    while True:
        if nb_rows_read>=sample_size:
            break
        
        line = h.readline()
        if not line:
            break
        
        sample += line 
        nb_rows_read += 1
    h.close()
    
    return sample

def csv_has_header(csv_path, sample_size=100):
    """
    Determines if a CSV file has a header
    sniffing the sample_size first rows
    """
    return csv.Sniffer().has_header(get_csv_sample(csv_path))
    
def estimate_nb_rows(csv_path, sample_size=100):
    """
    Read first sample_size rows and estimate
    total number of rows in the file
    """
    sample_size = 100
    sample = get_csv_sample(csv_path, sample_size)
    return os.path.getsize(csv_path)/(len(sample)/sample_size)

def nside_for_nbsrc(nbsrc):
    """
    Chooses the best suited NSIDE value according
    to the number of sources
    """
    if nbsrc>1e8:
        return 256
    elif nbsrc>1e7:
        return 128
    elif nbsrc>1e6:
        return 64
    else:
        return 32
    
def radec2thetaphi(ra, dec):
    return (90-dec)*numpy.pi/180., ra*numpy.pi/180. 
    
def get_metafile_path(root):
    return os.path.join(root, 'metadata.json')    

def get_path(root, nside, ipix):
    """
    Return path of file for given root directory,
    nside and ipix
    """
    
    dir_idx = (ipix/10000)*10000;
    return os.path.join(root, "nside%d/dir%d/npix%d.csv" % (nside, dir_idx, ipix))

def get_cgi_config_file_name():
    return 'cgi-config.json'

def write_data_from_buffer(buffer):
    for path in buffer.keys():
        rows = buffer[path]
        with open(path, 'a') as pathHandler:
            csvwriter = csv.writer(pathHandler)
            for row in rows:
                csvwriter.writerow(row)
                    


def trace(msg):
    if debug:
        print(msg)
    

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Parse a CSV file and create the directory')
    parser.add_argument("-f", "--csvfile", help="CSV input file")
    parser.add_argument("-r", "--rafield", help="Name (or index) of the field holding right ascension")
    parser.add_argument("-d", "--decfield", help="Name (or index) of the field holding declination")
    parser.add_argument("-i", "--idfield", help="Name (or index) of the field holding the ID of the current record")
    parser.add_argument("-o", "--outputdir", help="Output directory path")
    parser.add_argument("--nside", help="Force nside used")
    parser.add_argument("--debug", help="Enables debugging information", action="store_true")
    
    
    usage = '%s --csvfile <CSV-FILE> --rafield <RA-FIELD> --decfield <DEC-FIELD> --outputdir <OUTPUT-DIR> ' % (sys.argv[0])
    args = parser.parse_args()
    if not args.csvfile or not args.outputdir or not args.rafield or not args.decfield:
        print('Usage:\n%s' % (usage))
        sys.exit(1)

    csvfile = args.csvfile
    ra = args.rafield
    dec = args.decfield
    outputdir = args.outputdir
    idfield = args.idfield
    debug = args.debug
    
    raIdx = -1
    decIdx = -1
    idIdx = -1
    
    # check params (does file exist, does output dir exist and is empty)
    if not os.path.exists(outputdir):
        print 'Output directory "%s" does not exist ! ' % (outputdir)
        sys.exit(1)
        
    if len(os.listdir(outputdir))>0:
        print 'Output directory "%s" is not empty' % (outputdir)
        sys.exit(1)
        
    
    has_header = csv_has_header(csvfile)
    trace('Has header: %s' % (has_header))
    
    nb_rows_estimation = estimate_nb_rows(csvfile)
    trace('Nb rows estimated: %d' % (nb_rows_estimation))
    
    if args.nside:
        nside = int(args.nside)
        trace('NSIDE chosen by user: %s' % (nside))
    else:
        nside = nside_for_nbsrc(nb_rows_estimation)
        trace('Chosen NSIDE: %d' % (nside))
    
    buffer = {} # opened files
    nb_rows_in_buffer = 0
    header_fields = None
    nb_rows_read = 0
    nb_valid_data_rows = 0
    nb_total_data_rows = 0
    delimiter = ','
    print ''
    first_row = None
    # TODO : find if ra and dec in sexa
    with open(csvfile) as f:
        csvreader = csv.reader(f, delimiter=delimiter)
        for row in csvreader:
            if nb_rows_read%10 == 0:
                sys.stdout.write("\033[F")
                print 'Processing row #%d' % (nb_rows_read)
            ####### retrieve header fields names #######
            if nb_rows_read==0:
                if has_header:
                    header_fields = row
                    nb_rows_read += 1
                else:
                    header_fields = ['col_'+str(i) for i in range(0, len(row))]
                    
                len_header_fields = len(header_fields)
                # retrieve RA and dec indexes
                if ra in header_fields:
                    raIdx = header_fields.index(ra)
                else:
                    try:
                        raIdx = int(ra)
                    except:
                        pass
                
                if dec in header_fields:
                    decIdx = header_fields.index(dec)
                else:
                    try:
                        decIdx = int(dec)
                    except:
                        pass
                    
                if raIdx<0:
                    print 'Could not find ra field "%s"' % (ra)
                if decIdx<0:
                    print 'Could not find dec field "%s"' % (dec)

                if raIdx<0 or decIdx<0:
                    sys.exit(1)
                    
                # retrieve ID field
                id_field_missing = False
                if idfield:
                    if idfield in header_fields:
                        idIdx = header_fields.index(idfield)
                    else:
                        try:
                            idIdx = int(idfield)
                        except:
                            pass
                        
                    if idIdx<0:
                        print 'Could not find id field "%s"' % (id)
                        sys.exit(1)
                else:
                    id_field_missing = True
                
                if has_header:
                    continue
            ###### END OF retrieve header fields names #######
            
            if nb_rows_read==1:
                first_row = row
            
            # TODO: take into account sexa coordinates
            is_valid = True
            
            if len(row)!=len_header_fields:
                is_valid = False
                trace('Row has a different number of fields than header: %d versus %d' % (len(row), len_header_fields)) 
            else:
                
                try:  
                    ra = float(row[raIdx])
                except:
                    is_valid= False
                    trace('Could not parse "%s" as right ascension' % (row[raIdx]))
                try:
                    dec = float(row[decIdx])
                except:
                    is_valid = False
                    trace('Could not parse "%s" as declination' % (row[decIdx]))
                
                
            if not is_valid:
                trace('Invalid line: %s\n' % (delimiter.join(row)))
                nb_total_data_rows += 1
                nb_rows_read += 1
                continue
            
            theta, phi = radec2thetaphi(ra, dec)
            ipix = healpy.pixelfunc.ang2pix(nside, theta, phi, nest=True)
            path = get_path(outputdir, nside, ipix)
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            
            if path in buffer:
                rows = buffer[path]
            else:
                rows = []
                buffer[path] = rows
            
            # generate an ID
            if id_field_missing:
                row.append('id_%d' % (nb_total_data_rows))
                
            rows.append(row)
            nb_rows_in_buffer += 1
            # write all data in buffer
            if nb_rows_in_buffer>MAX_ROWS_IN_BUFFER:
                write_data_from_buffer(buffer)
                nb_rows_in_buffer = 0
                buffer = {}
                
                
            
            #ipix = healpy.heal  
            nb_rows_read += 1
            nb_valid_data_rows += 1
            nb_total_data_rows += 1
            
    # write remaining data from buffer
    sys.stdout.write("\033[F")
    print 'Processing row #%d' % (nb_rows_read)
    write_data_from_buffer(buffer)
    
    # write metadata
    h = open(get_metafile_path(outputdir), 'w')
    meta = {'creationDate': str(datetime.datetime.now()), 'nside': nside}
    fields = []
    header_names = header_fields
    if id_field_missing:
        header_names.append('record_ID')
        idIdx = len(header_names)-1
        
    
    for k in range(0, len(header_fields)):
        field = {'name': header_fields[k]}
        if k==raIdx:
            field['ucd'] = 'POS_EQ_RA_MAIN'
            field['unit'] = 'deg'
            field['datatype'] = 'double'
        elif k==decIdx:
            field['ucd'] = 'POS_EQ_DEC_MAIN'
            field['unit'] = 'deg'
            field['datatype'] = 'double'
        elif k==idIdx:
            field['ucd'] = 'ID_MAIN'
            field['datatype'] = 'char'
            field['arraysize'] = '*'
        else:
            # try to guess datatype from first_row
            if first_row:
                if type(first_row[k])==str:
                    field['datatype'] = 'char'
                    field['arraysize'] = '*'
                elif type(first_row[k])==int:
                    field['datatype'] = 'int'
                elif type(first_row[k])==float:
                    field['datatype'] = 'double'
             
            
        fields.append(field)
    meta['fields'] = fields
    h.write(json.dumps(meta, indent = 4, sort_keys = True))
    h.close()
    
    # write CGI config file
    config_path =  os.path.join(outputdir, get_cgi_config_file_name())
    config = {'dataPath': os.path.abspath(outputdir)}
    h = open(config_path, 'w')
    h.write(json.dumps(config))
    h.close()
            
    
    # TODO : suite des opérations
    
    print '\n%d lines parsed:' % (nb_rows_read)
    if has_header:
        print '   - 1 header line'
    else:
        print '   - no header line'
    print '   - %d valid data rows' % (nb_valid_data_rows)
    print '   - %d invalid data rows (ignored)' % (nb_total_data_rows-nb_valid_data_rows)
    
    if not debug and nb_total_data_rows!=nb_valid_data_rows:
        print '   --> To get more information about invalid rows, try relaunching with --debug flag'
        
    print '\nData has been organized in output directory "%s"' % (outputdir)
    
    print '\nColumns have been described in file "%s". You might want to have a look at this file and update/correct the definitions.' % (get_metafile_path(outputdir))
    
    print '\nThe configuration file for the CGI has been written to "%s". Copy this file to the directory of the CGI script.' % (config_path)
    
    print '\n*** What now ? ***'
    print 'You might want to:'
    print '1. Test the Cone Search service from the command line:'
    print '2. Test the Cone Search service'
    print '3. Deploy the service on your production server:'
    print '   Simply copy the newly created data directory ... on your server'
    print '   Copy the CGI script along with ... and adjust dataPath if needed'
    print '   Test ...'
    
