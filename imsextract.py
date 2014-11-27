"""
imsextract

Reconstrueer mappen en bestanden uit een It's Learning export (SCORM IMSContent)

reconstrueert: folder, file, image, note
geen ondersteuning voor: essay (ingeleverde opdrachten)

Tom Kooij, 10 november 2014

zie: http://github.com/tomkooij/imsextract

OPMERKINGEN:
- Alleen getest op Windows 7. Zou ook onder MAC OSX en POSIX moeten werken
- Mapnamen kunnen langer worden dan Windows toestaat. Gebruik vanuit C:\TEMP (een map met een kort eigen path)

Special characters in filenames should be supported, explaination:

imsmanifest.xml is encoded in UTF-8
filenames in zipfiles are encoded in CP437
It's Learning stores filenames in imsmanifest.xml in CP437.
These are converted to unicode by the Elementree xml parser
Finally they are converted back to CP437 in extract_file_and_write()

"""

import zipfile
from xml.etree import ElementTree
import os
import sys
from pathlib import Path
import shutil
import unicodedata
import string


TRUE = 1
FALSE = 0

# remove illegal chars from filename/dirname
# source: http://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename-in-python
validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)

#
# Just extracting from zipfile does not work. Workaround:
#
# input: name_in_zip (UTF-8 encoded string)
# path = Path() object
# name_on_disk: output filename (string)
def extract_from_zip_and_write(name_in_zip, path, name_on_disk):
    try:
        bron = zipfile.open(name_in_zip.encode('cp437')) # zip uses cp437 encoding
    except KeyError:
        failed_files.append(name_in_zip)
        return False

    doel = open(str(path / name_on_disk), "wb")
    with bron, doel:
        shutil.copyfileobj(bron, doel)
    return True


def extract_imsfile(filename, destination_path):

    #global manifest  #development
    global resdict, failed_files

    # dictionary to store <resource> information (location of files in zipfile)
    resdict = {}
    failed_files = []

    #
    # walk through xml tree "folder"
    #
    # RECURSIVE FUNCTION!
    #
    # folder = list of elementree items
    # path = pathlib Path object "the current path"
    #
    def do_folder(folder, path):

        #print "DEBUG: entering do_folder(). old path=", path
        title = removeDisallowedFilenameChars(unicode(folder[0].text))
        new_path = path / title # add subfolder to path
        if not new_path.exists():
            if (verbose):
                print 'creating directory: ', str(new_path)
            new_path.mkdir() # create directory
        else:
            if (verbose):
                print 'chdir into existing directory:', str(new_path)

        new_path.resolve() # change dir

        files = folder[1:]  # files is list of files and subfolders in this folder

        for f in files:
            # is this file a folder?
            # if it is the identifier contains '_folder_'
            id = f.get('identifier')

            if '_folder_' in id:                  # item is subfolder! branch into
                subfolder = f.getchildren()
                do_folder(subfolder,new_path)

            if '_folderfile_' in id:              # item is file. Extract
                # identifiers zien er zo uit: 'I_rYTieTdHa_folderfile_42508'
                # we hebben alleen het getal nodig
                idval = id.split('_folderfile_')[1]
                bestandsnaam = removeDisallowedFilenameChars(unicode(resdict[idval].split('/')[1]))
                if (verbose):
                    print 'extracting file: ',bestandsnaam
                extract_from_zip_and_write(resdict[idval], new_path, bestandsnaam)

            if '_weblink_' in id:              # item is weblink. Extract
                idval = id.split('_weblink_')[1]
                url = resdict[idval] # get url from resource dict

                title = f[0].text # get title from <items>

                bestandsnaam = removeDisallowedFilenameChars(unicode(title+'.url'))
                if (verbose):
                    print 'extracting weblink: ',bestandsnaam

                # .url file just a txt file with [Internet Shortcut]. Clickable in windows
                try:
                    doel = open(str(new_path / bestandsnaam), "wb")
                    doel.write('[InternetShortcut]\nURL=')
                    doel.write(url)
                    doel.write('\n')
                    doel.close()
                except IOError:
                    print "Cannot create:", str(new_path / bestandsnaam)
                    failed_files.append(str(new_path/ bestandsnaam))

            if '_note_' in id:              # item is note. Extract html contents
                idval = id.split('_note_')[1]

                title = f[0].text # get title from <items>
                bestandsnaam = removeDisallowedFilenameChars(unicode(title+'.html'))
                if (verbose):
                    print 'extracting note: ',bestandsnaam
                extract_from_zip_and_write(resdict[idval], new_path, bestandsnaam)

            if '_picture_' in id:              # item is image. Extract

                idval = id.split('_picture_')[1]
                bestandsnaam = resdict[idval][1].split('/')[1]
                folder_in_zip = resdict[idval][0].split('/')[0]

                if (verbose):
                    print 'extracting image: ',bestandsnaam

                # The correct imagefile is NOT in the <rescources> dict.
                #  Images are renamed and an .html container is used

                # get .html and recover imagefilename (sigh!)
                htmlfile = zipfile.open(resdict[idval][0])
                lines = htmlfile.readlines()

                for line in lines:
                    x = line.find('src=')
                    if (x != -1):
                        imagefilename = line[x:x+20].split('\'')[1]
                        print "reconstructed imagefilename (in zip): ", imagefilename

                bestandsnaam_in_zip = folder_in_zip + '/' + imagefilename

                extract_from_zip_and_write(bestandsnaam_in_zip, new_path, bestandsnaam)

        #
        # END OF local function: do_folder()
        #

    #
    # START
    #
    global zipfile # zipfile is used in do_folder()

    try:
        with zipfile.ZipFile(filename,'r') as zipfile:

            # Zoek het manifest en lees de XML tree
            try:
                manifest = zipfile.read('imsmanifest.xml')
            except KeyError:
                print 'imsmanifest.xml not found in zip. Bad export?'
                return False

            root = ElementTree.fromstring(manifest)

            # de volgende code is geinspireerd door:
            #    http://trac.lliurex.net/pandora/browser/simple-scorm-player
            # de xml tags worden voorafgenaam door {http://www.w3... blaat}
            # haal die eerst op:
            namespace = root.tag[1:].split("}")[0] #extract namespace from xml file
            #
            # Maak lijsten van XML items. Gebruikt voor development
            # Alleen resources (<resources>) is nodig in de rest van de code
            #
            org = root.findall(".//{%s}organisations" % namespace) # for development
            items = root.findall(".//{%s}item" % namespace) # for development
            resources = root.findall(".//{%s}resource" % namespace)

            #
            # Maak een dict met alle <resource> (bestanden)
            #
            # resdict is global
            for r in resources:
                # identifiers zien er zo uit: 'R_rYTieTdHa_folderfile_42508'
                # we hebben alleen het laatste getal nodig
                if '_folderfile_' in r.get('identifier'):
                    resdict[r.get('identifier').split('_folderfile_')[1]] = r.get('href')
                if '_weblink_' in r.get('identifier'):
                    resdict[r.get('identifier').split('_weblink_')[1]] = r.get('href')
                if '_note_' in r.get('identifier'):
                    resdict[r.get('identifier').split('_note_')[1]] = r.get('href')
                if '_picture_' in r.get('identifier'):
                    # _picture_ has two items. [0] = html container [1] = actual imagefile
                    # as the actual imagefilename is *not* the archivefilename, we use the html to recover filename
                    resdict[r.get('identifier').split('_picture_')[1]] = [r[0].get('href') , r[1].get('href')]
            #
            # Doorloop de XML boom zodat we bij het beginpunt van de <items> aankomen
            #
            # voodoo:
            organisations = root.getchildren()[0]
            main = organisations.getchildren()[0]
            rootfolder = main.getchildren()

            destpath = Path(destination_path) # high level Path object (windows/posix/osx)

            # rootfolder is een lijst[] met items
            # loop deze (recursief door. Maak (sub)mappen en extract bestanden)
            do_folder(rootfolder, destpath)

            if len(failed_files)==0:
                print "Klaar: Alle bestanden uitgepakt!"
                return True
            else:
                print "\n\n ERRORS:"
                for file in failed_files:
                    print "mislukt: ", file
                return False

    except IOError:
        print('IOError: File not found?')



def print_usage_and_exit():
    print 'Usage: imsextract [-v] inputfile <outputpath>'
    print 'examples:\nimsextract export.zip    - extract to current folder'
    print 'imsextract export.zip D:\yourfolder  - extract to specified folder'
    print 'use -v to print verbose output'
    sys.exit(0)

if __name__ == '__main__':

    global verbose
    verbose = FALSE # do not print verbose output

    print 'imsextract - Extract Its Learning IMSContent SCORM package'
    print 'Get the source at: http://github.com/tomkooij/imsextract\n'
    path = Path('.')  # default path

    arg = sys.argv   # get command line arguments
    # arg[0] == filename
    # arg[1] == first argument etc

    if len(arg)==1:
        print_usage_and_exit()

    if (arg[1][0] == '-v'):
        verbose = TRUE;

    if len(arg)>=2:
        filename = str(arg[1])
        # path already at default, set if specified at command line:
        if len(arg)==3:
            path = Path(str(arg[2]))
            if not path.exists():
                print 'creating directory: ', str(path)
                path.mkdir() # create directory
        #
        # DO IT!
        #
        extract_imsfile(filename, path)
    else:
        print_usage_and_exit()

#EOF
