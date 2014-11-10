import zipfile
from xml.etree import ElementTree as ET
import os
from pathlib import Path
import shutil

resdict = {}


#
# walk through xml tree "folder"
#
# RECURSIVE FUNCTION!
#
# folder = list of elementree items
# path = pathlib Path object "the current path"
#
def do_folder(folder, path):

    print "DEBUG: entering do_folder(). old path=", path
    title = folder[0].text
    new_path = path / title # add subfolder to path
    print 'creating directory: ', str(new_path)
    new_path.mkdir() # create directory
    new_path.resolve() # change dir
    files = folder[1:]

    for f in files:
#        print 'file: ',f.attrib
        # is this file a folder?
        # if it is the identifier contains '_folder_'
        id = f.get('identifier')
        if '_folder_' in id:
            subfolder = f.getchildren()
            do_folder(subfolder,new_path)
        if '_folderfile_' in id:
            # identifiers zien er zo uit: 'I_rYTieTdHa_folderfile_42508'
            # we hebben alleen het getal nodig
            idval = id.split('_folderfile_')[1]
            bestandsnaam = resdict[idval].split('/')[1]
            print "bestand: ",bestandsnaam
            # WERKT NIET submappen blijven ervoor
            # zipfile.extract(resdict[idval],str(new_path)) # extract file in current dir
            # Brute force, open file, write file:
            bron = zipfile.open(resdict[idval])
            doel = open(str(new_path / bestandsnaam), "wb")
            with bron, doel:
                shutil.copyfileobj(bron, doel)

if __name__ == '__main__':

    global zipfile

    with zipfile.ZipFile('Export_Biologie_klas_5_2014-11-07.zip','r') as zipfile:

        for x in zipfile.namelist():
            index = x.find('imsmanifest.xml')
            if index != -1:
                fullpath = x[:index]
                print "FOUND", x, fullpath
                manifest = zipfile.read(x)
                #print manifest

        root = ET.fromstring(manifest)

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
            resdict[r.get('identifier').split('_folderfile_')[1]] = r.get('href')

        #
        # Doorloop de XML boom
        #
        organisations = root.getchildren()[0]
        main = organisations.getchildren()[0]
        rootfolder = main.getchildren()

        # rootfolder is een lijst[] met items
        # loop deze (recursief door. Maak (sub)mappen en extract bestanden)
        curpath = Path('.') # high level Path object (windows/posix/osx)
        rootpath = curpath / 'testdir' # do je ding in een test map
        do_folder(rootfolder, rootpath)
