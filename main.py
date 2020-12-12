import requests, sys, socket, subprocess
from requests.exceptions import InvalidURL, ConnectionError
import xml.etree.ElementTree as ET

##########
#Variable#
##########

VIDEOPLAYER_PATH = ""

#########
#Classes#
#########


class Server():

    def __init__(self, ip, port, ogresp):
        self.ip = ip
        self.port = port
        self.url = "http://" + str(ip) + ":" + str(port)
        self.headers = ogresp
        self.contentDirResp = ""
        self.folders = [] #mappa("Root")
        self.fonderIds = []
        self.contents = []
        #   {'id': '64$0',
        #   'parentID': '64',
        #   'restricted': '1',
        #   'searchable': '1',
        #   'childCount': '2',
        #   'title': 'Anime',
        #   'class': 'object.container.storageFolder',
        #   'storageUsed': '-1',
        #   'children': {}}

    def addContentDirResp(self, resp):
        self.contentDirResp = str(resp)

    def cannotReach(self):
        self.contentDirResp = None

    def addFolder(self, folderToAdd):
        if not (folderToAdd['id'] in self.fonderIds):
            self.fonderIds.append(folderToAdd['id'])
            self.folders.append(folderToAdd)
    
    def addContent(self, contentToAdd):
        if not (contentToAdd in self.contents):
            self.contents.append(contentToAdd)
    
    def save_cont_to_file(self, file):
        with open(file, "a+") as f:
            f.write(str(self.contents))

class mappa():
    def __init__(self, adat, ismappa=True, children=None, name=None):
        self.name = name
        self.adat = adat
        self.isfolder = ismappa
        try:
            self.title = adat['title']
        except TypeError as error:
            pass
        self.children = []
        if children is not None:
            for child in children:
                self.add_child(child)
    
    def __str__(self):
        return str(self.adat)

    def add_child(self, child):
        assert isinstance(child, mappa)
        self.children.append(child)

    def add_children(self, children):
        for child in children:
            self.add_child(child)

    def add_content(self, adat):
        self.adat = adat

    def print_self(self):
        print(self.adat)
        if self.children == []:
            return
        for child in self.children:
            child.print_self()

    def print_level(self, level):
        if level == 0:
                print(self.title)
                return
        for child in self.children:
            child.print_level(level-1)
    
    def add_child_to(self, childto_add, name):
        if self.name == name:
            self.add_child(childto_add)
        if self.children == []:
            return 1001
        for child in self.children:
            if child.name == name:
                child.add_child(childto_add)
                return
            else:
                child.add_child_to(childto_add, name)

    def return_data_of(self, name):
        if self.name == name:
            print(self)
        for child in self.children:
            child.return_data_of(name)

    def print_children(self):
        for child in self.children:
            print(child.title)

    def return_level_of(self, name, level=0):
        if self.name == name:
            return level
        for child in self.children:
            child.return_level_of(name, level= level + 1)


################
#The mighty one#
################


fomappa = mappa({"title":"null"},name="0")


###########
#Functions#
###########


def find_local_servers():
    """
    Checks for UPNP devices on the local network


    Returns a list of Server objects containing the server IPs, PORTs and responses

    If no Devices are found returns None
    """

    msg = b'M-SEARCH * HTTP/1.1\r\nHOST:239.255.255.250:1900\r\nST:upnp:rootdevice\r\nMX:2\r\nMAN:"ssdp:discover"\r\n\r\n'
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.settimeout(2)
    s.sendto(msg, ('239.255.255.250', 1900))

    servers = []
    try:
        while True:
            fordata = []
            (data, address) = s.recvfrom(65507)
            fordata.append(str(data).split("\\r\\n")[0][2:])
            for x in str(data).split("\\r\\n"):
                if x != "'" and x != "" and x.find("b'") == -1:
                    fordata.append(x)
            servers.append((fordata, address))
    except socket.timeout:
        if len(servers) == 0:
            return None

    rt = []
    for serv in servers:
        rt.append(Server(serv[1][0], serv[1][1], serv[0]))

    return rt


def soap_req(Server, raw, data_binary=None, formated=True):
    """
    SOAP request with curl


    Server : A Server class object

    *Optional Key Word: 

        data_binary = Data

        formated = True | False, Format the data or not, default is False

    Returns the response from the SOAP call, and if its the main ContentDir resp, then saves it to the Server class Object.
    """

    data = raw
    headers = {"Content-Type": "text/xml; charset=utf-8",
               "SOAPAction": "\"urn:schemas-upnp-org:service:ContentDirectory:1#Browse\""}
    # Make SOAP request
    try:
        for header in Server.headers:
            if header.find("Location") > -1 or header.find("LOCATION") > -1 or header.find("location") > -1:
                webpath = header[9:-13]
        r = requests.post(webpath, data=data, headers=headers)
    except ConnectionError:
        print("Cannot connect to server...\n")
        Server.cannotReach()
        return

    resp = r.content

    if formated:
        resp = str(resp).replace("&lt;", "<").replace(
                "&gt;", ">").replace("\\r\\n", "")[2:-1]

    #print("Successfully recived response\n")

    if Server.contentDirResp == "":
        Server.addContentDirResp(resp)

    return resp


# def update_data_file(dirId, datafile):
#     """
#     Updates the `datafile` to request the folder with folderid `fid`

#     return : None
#     """

#     parsed = ET.parse(datafile)
#     root = parsed.getroot()
#     root[0][0][0].text = dirId
#     parsed.write(datafile)
#     print("Updated data file to ", dirId)

def update_data_file_open(dirId, raw):# datafile):
 
    newraw = ""

    for line in raw.split('\n'):
        if line.find('ObjectID') > -1:
            sline = line.strip()
            newline = "      " + sline[:10] + str(dirId) + sline[-11:]
        else:
            newline = line
        newraw += newline + '\n'
    

    return newraw

def parse_dir_resp(Server, response=None, tree=None):
    """
    Parse the response from a Standard MiniDLNA server, returns the Main Dirs


    `Server` : A Server class Object, has to have an ContectDir response or it has to be included in `respone` 

    *Optional Key Word:

    `response` = None, adds the found Dirs to the Server class Object
    """

    if Server.contentDirResp is None:
        print("The Server cannot be reached")
        return
    if response is None:
        if Server.contentDirResp == "":
            print("The Server class Object, has to have an ContectDir response or it has to be included in `response`")
            return
        else:
            response = Server.contentDirResp



    root = ET.fromstring(response)
    browseResponse = {"Result": None, "NumberReturned": None,
                      "TotalMatches": None, "UpdateID": None}

    for body in root:
        for rawBrowseResponse in body:
            for elem in rawBrowseResponse:
                #print(elem)
                try:
                    browseResponse[elem.tag] = elem
                except KeyError:
                    pass
    if browseResponse["Result"] == None:
        print("Didnt recive response")
        return
    # [0] Element is ?Didl-lite? which contains the folder containers


    for cont_or_item in browseResponse["Result"][0]:
        try:
            tag = cont_or_item.tag[cont_or_item.tag.find("}")+1:]
        except TypeError:
            continue
        if tag == 'container':
            folder = cont_or_item.attrib
            for infos in cont_or_item:
                folder[infos.tag[infos.tag.find("}")+1:]] = infos.text
            Server.addFolder(folder)
            fomappa.add_child_to(mappa(folder,name=folder['id']),folder['parentID'])
        elif tag == 'item':
            content = cont_or_item.attrib
            for infos in cont_or_item:
                content[infos.tag[infos.tag.find("}")+1:]] = infos.text
            #Server.addContent(content)
            fomappa.add_child_to(mappa(content,name=content['id'], ismappa=False),content['parentID'])

def parse_dir(Server, dirId, data_binary, tree=None):
    """
    Parse the directories of a Server class object

    `Server` : the Server to parse

    `dirId` : the Id of the directory to parse

    `data_binary` : data file used for the SOAP request
    """

    newdata_binary = update_data_file_open(dirId, data_binary)
    resp = soap_req(Server, newdata_binary, formated=True)
    parse_dir_resp(Server, response=resp, tree=tree)

    return

######
#Main#
######


def main():
    """
    main.py

    Options:

        --help : Writes info about the program #future

    """

    #This is working
    # if len(sys.argv) < 4:
    #     print("Please use : main.py `ip` `port` `datafile`")
    #     exit()

    # ip = sys.argv[1]
    # port = sys.argv[2]
    # datafile = sys.argv[3]
    # host = "http://" + ip + ":" + port

    # with open("./resp.xml") as f:
    #     text = f.read()


    print("Waiting for Server response...\n")
    # Find local Servers

    Servers = find_local_servers()
    while Servers is None:
        print("...")
        Servers = find_local_servers()
    print("Found :", len(Servers), " Servers")

    mainfile = "./data/main.data"
    subfile = "./data/sub.data"
    
    with open(subfile, 'r+') as f:
        raw = f.read()

    for i, Server in enumerate(Servers):
        if len(Server.headers) > 8:
            print(f'{i+1}) {Server.ip}:{Server.port} \n Status: {Server.headers[0]} \n {Server.headers[6]} \n {Server.headers[7]} \n {Server.headers[8]}')
    curServer = Servers[int(input("Choose a server: "))-1]
    

    #parse the whole server
    newraw = update_data_file_open(0, raw)
    soap_req(curServer, newraw, formated=True)

    parse_dir_resp(curServer)
    for fid in curServer.fonderIds:
        parse_dir(curServer, fid, newraw)
    
    actualmappa = fomappa
    mappasorrend = []
    for y in range(100):
        print("0) Back")
        for i, x in enumerate(actualmappa.children):
            print(f'{i+1}) {x.title}')
        inp = int(input("Choose a folder: ")) - 1
        if inp == -1:
            actualmappa = mappasorrend[-1]
        else:
            if not actualmappa.children[inp].isfolder:
                subprocess.run(VIDEOPLAYER_PATH + actualmappa.children[inp].adat['res'])
            else:
                mappasorrend.append(actualmappa)
                actualmappa = actualmappa.children[inp]

if __name__ == "__main__":
    main()
