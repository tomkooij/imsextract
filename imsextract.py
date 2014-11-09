import zipfile
from xml.etree import ElementTree as ET

resdict = {}


#
# walk through xml tree "folder"
#
# folder = list of elementree items
def do_folder(folder):

#    print "DEBUG: entering do_folder()"
    title = folder[0].text
    print 'map: ',title
    files = folder[1:]

    for f in files:
#        print 'file: ',f.attrib
        # is this file a folder?
        # if it is the identifier contains '_folder_'
        id = f.get('identifier')
        if '_folder_' in id:
            subfolder = f.getchildren()
            do_folder(subfolder)
        if '_folderfile_' in id:
            # identifiers zien er zo uit: 'I_rYTieTdHa_folderfile_42508'
            # we hebben alleen het getal nodig
            idval = id.split('_folderfile_')[1]
            print "bestand: ",resdict[idval]


if __name__ == '__main__':

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

    do_folder(rootfolder)
