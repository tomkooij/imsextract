import zipfile
from xml.etree import ElementTree
import os
from pathlib import Path
import shutil
import unicodedata
import string

# remove illegal chars from filename/dirname
# source: http://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename-in-python
validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)


resdict = {}

FILENAME = 'tom.zip'
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
        print 'creating directory: ', str(new_path)
        new_path.mkdir() # create directory
    else:
        print 'chdir into existing directory:', str(new_path)

    new_path.resolve() # change dir

    files = folder[1:]  # files is list of files and subfolders in this folder

    for f in files:
#        print 'file: ',f.attrib
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
            bestandsnaam = resdict[idval].split('/')[1]
            print 'extracting file: ',bestandsnaam
            # WERKT NIET submappen blijven ervoor
            # zipfile.extract(resdict[idval],str(new_path)) # extract file in current dir
            # Brute force, open file, write file:
            bron = zipfile.open(resdict[idval])
            doel = open(str(new_path / bestandsnaam), "wb")
            with bron, doel:
                shutil.copyfileobj(bron, doel)

        if '_weblink_' in id:              # item is weblink. Extract
            idval = id.split('_weblink_')[1]
            url = resdict[idval] # get url from resource dict

            title = f[0].text # get title from <items>

            bestandsnaam = removeDisallowedFilenameChars(unicode(title+'.url'))
            print 'extracting weblink: ',bestandsnaam

            # .url file just a txt file with [Internet Shortcut]. Clickable in windows
            doel = open(str(new_path / bestandsnaam), "wb")
            doel.write('[InternetShortcut]\nURL=')
            doel.write(url)
            doel.write('\n')
            doel.close()



if __name__ == '__main__':

    global zipfile

    with zipfile.ZipFile(FILENAME,'r') as zipfile:

        for x in zipfile.namelist():
            index = x.find('imsmanifest.xml')
            if index != -1:
                fullpath = x[:index]
                print "FOUND", x, fullpath
                manifest = zipfile.read(x)
                #print manifest

        root = ElementTree.fromstring(manifest)

        # de volgende code is geinspireerd door:
        #    http://trac.lliurex.net/pandora/browser/simple-scorm-player
        # de xml tags worden voorafgenaam door {http://www.w3... blaat}
        # haal die eerst op:
        namespace = root.tag[1:].split("}")[0] #extract namespace from xml file

        org = root.findall(".//{%s}organisations" % namespace)
        items = root.findall(".//{%s}item" % namespace)
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

        #
        # Doorloop de XML boom zodat we bij het beginpunt van de <items> aankomen
        #
        # voodoo:
        organisations = root.getchildren()[0]
        main = organisations.getchildren()[0]
        rootfolder = main.getchildren()

        curpath = Path('.') # high level Path object (windows/posix/osx)
        rootpath = curpath  # extract in current dir

        # rootfolder is een lijst[] met items
        # loop deze (recursief door. Maak (sub)mappen en extract bestanden)
        do_folder(rootfolder, rootpath)
