from flask import Flask, render_template, request
from flask_assets import Bundle, Environment

import dataset
import vcoApi
import os
import urllib3
from deepdiff import DeepDiff

urllib3.disable_warnings()


app = Flask(__name__)
app.secret_key = "super secret key"

env = Environment(app)
js = Bundle('https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js', 'https://code.jquery.com/ui/1.12.1/jquery-ui.js' ,'js/clarity-icons.min.js', 'js/clarity-icons-api.js',
            'js/clarity-icons-element.js', 'js/custom-elements.min.js', 'js/backup.js')
env.register('js_all', js)

css = Bundle('css/modal.css', 'css/clarity-ui.min.css', 'css/clarity-icons.min.css')
env.register('css_all', css)

dir_path = os.path.dirname(os.path.realpath(__file__))

####################################################################
vcoUsername = 'super@velocloud.net'
vcoPassword ='vcadm!n'
####################################################################

vcoClient = vcoApi.VcoRequestManager("192.168.20.15", verify_ssl=False)
vcoClient.authenticate(vcoUsername, vcoPassword, is_operator=True)
db = dataset.connect('sqlite:///'+dir_path+'/database.db')
# db = dataset.connect('sqlite:///tmp/database.db')

print('=================')
print(dir_path)

@app.route('/')
def listEnterprises():

    resp = vcoClient.call_api("network/getNetworkEnterprises", {
    })

    table = db['enterpriseList']
    for enterprise in resp:
        table.upsert(dict(enterpriseId=enterprise['id'], name=enterprise['name']), ['id'])


    return render_template('enterprises.html', table=resp)


@app.route('/enterprise/<int:enterpriseId>')

def listEdges(enterpriseId):

    resp = vcoClient.call_api("enterprise/getEnterpriseEdgeList",{
  "enterpriseId": enterpriseId,
    })



    table = db['edgeList']
    for edge in resp:
        table.upsert(dict(enterpriseId=enterpriseId, edgeId=edge['id'], edgeName=edge['name']), ['enterpriseId', 'edgeId'])

    profileResp = vcoClient.call_api("enterprise/getEnterpriseConfigurationsPolicies", {
        "enterpriseId": enterpriseId,
    })

    table = db['profileList']
    for profile in profileResp:
        table.upsert(dict(enterpriseId=enterpriseId, profileId=profile['id'], profileName=profile['name']), ['enterpriseId', 'profileId'])

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)

    return render_template('edges.html', profiles=profileResp, enterpriseId=enterpriseId, table=resp, enterprise=enterprise)

@app.route('/enterprise/<int:enterpriseId>/edge/<int:edgeId>/delete', methods=[ 'POST'])
def initiateDeleteEdgeModulePost(enterpriseId, edgeId):

    table = db['edgeList']
    edge = table.find_one(enterpriseId=enterpriseId, edgeId=edgeId)


    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)


    for moduleId in modules:
        table = db['edgeSpecificModules']
        table.delete(enterpriseId=enterpriseId, edgeId=edgeId, id=moduleId)
        print('deleted module id '+ str(moduleId))

    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId)
        backups = list(backupsIter)
    except:
        print('no backups')

    return render_template('edgeBackups.html', edgeName=edge['edgeName'], enterprise=enterprise, backups=list(backups), enterpriseId=enterpriseId, edgeId=edgeId)


@app.route('/enterprise/<int:enterpriseId>/edge/<int:edgeId>/compare', methods=[ 'POST'])
def initiateCompareEdgeModulePost(enterpriseId, edgeId):

    compareList = []

    currentConfigList = request.json['currentConfigCompare']
    backedupConfigList = request.json['backedUpConfig']

    if len(currentConfigList) + len(backedupConfigList) != 2:
        return('Invalid number of configs selected')

    configList = []


    # return ('working')

    table = db['edgeList']
    edge = table.find_one(enterpriseId=enterpriseId, edgeId=edgeId)



    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)


    edgeSpecificModules = getEdgeModules(enterpriseId, edgeId)

    for key in currentConfigList:
        for module in edgeSpecificModules:
            if module['id'] == int(key):
                configList.append(module)


    for moduleId in backedupConfigList:
        table = db['edgeSpecificModules']
        restoreIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId, id=int(moduleId))
        restore = list(restoreIter)

        configList.append(restore[0]['data'])

    ddiff = DeepDiff(configList[1], configList[0], ignore_order=True, exclude_paths={"root['refs']", "root['version']", "root['modified']"}).pretty()
    if ddiff == "":
        ddiff = "No changes detected"
    # returnString = pprint.pformat(ddiff, indent=2)

    return(ddiff.replace('\n', '<br>'))


@app.route('/enterprise/<int:enterpriseId>/edge/<int:edgeId>/restore', methods=[ 'POST'])
def initiateRestoreEdgeModulePost(enterpriseId, edgeId):

    table = db['edgeList']
    edge = table.find_one(enterpriseId=enterpriseId, edgeId=edgeId)


    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)

    edgeSpecificModules = getEdgeModules(enterpriseId, edgeId)

    for moduleId in modules:
        table = db['edgeSpecificModules']
        restoreIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId, id=moduleId)
        restore = list(restoreIter)


        restoreData = {}
        restoreData['data'] = restore[0]['data']['data']
        print('restore module id: ' + str(moduleId))
        resp = vcoClient.call_api("configuration/updateConfigurationModule", {
            "enterpriseId": enterpriseId,
            "_update": restoreData,
            "id": int(restore[0]['moduleId']),
            "name": restore[0]['moduleName']

        })

    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId)
        backups = list(backupsIter)
    except:
        print('no backups')

    return render_template('edgeBackups.html', enterprise=enterprise, edgeName=edge['edgeName'], backups=list(backups), modules=edgeSpecificModules, enterpriseId=enterpriseId, edgeId=edgeId)


@app.route('/enterprise/<int:enterpriseId>/edge/<int:edgeId>/backup', methods=[ 'POST'])
def initiateBackupEdgeModulePost(enterpriseId, edgeId):

    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    backupSetName = request.form['name']


    table = db['edgeList']
    edge = table.find_one(enterpriseId=enterpriseId, edgeId=edgeId)

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)

    edgeSpecificModules = getEdgeModules(enterpriseId, edgeId)

    for moduleId in modules:
        for module in edgeSpecificModules:
            if module['id'] == moduleId:
                table = db['edgeSpecificModules']
                table.upsert(dict(enterpriseId=enterpriseId, edgeName=edge['edgeName'], backupSetName=backupSetName, moduleName=module['name'], edgeId=edgeId, moduleId=moduleId, version=module['version'], data=module), ['version', 'moduleName', 'backupSetName'])



        table = db['edgeSpecificModules']
        backups = []

        try:
            backupsIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId)
            backups = list(backupsIter)
        except:
            print('no backups')



    return render_template('edgeBackups.html', enterprise=enterprise, backups=backups, edgeName=edge['edgeName'], modules=edgeSpecificModules, enterpriseId=enterpriseId, edgeId=edgeId)

@app.route('/enterprise/<int:enterpriseId>/edge/<int:edgeId>')
def getEdgeBackups(enterpriseId, edgeId):

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)


    table = db['edgeList']
    edge = table.find_one(enterpriseId=enterpriseId, edgeId=edgeId)

    edgeSpecificModules = getEdgeModules(enterpriseId, edgeId)


    edgeModules = []
    for module in edgeSpecificModules:
        if module['name'] != 'controlPlane':
            edgeModules.append(module)
    table = db['edgeSpecificModules']
    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, edgeId=edgeId)
        backups = list(backupsIter)
    except:
        print('no backups')


    return render_template('edgeBackups.html', edgeName=edge['edgeName'], enterprise=enterprise, backups=list(backups), modules=edgeModules, enterpriseId=enterpriseId, edgeId=edgeId)

@app.route('/enterprise/<int:enterpriseId>/profile/<int:profileId>')
def getProfileBackups(enterpriseId, profileId):

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)


    table = db['profileList']
    profile = table.find_one(enterpriseId=enterpriseId, profileId=profileId)

    modulesAll = getProfileModules(enterpriseId, profileId)



    ignoredModules = ['controlPlane', 'analyticsSettings', 'WAN']
    modules = []
    for module in modulesAll:
        if not any(x.lower() == module['name'].lower() for x in ignoredModules):
            modules.append(module)

    table = db['profileModules']
    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, profileId=profileId)
        backups = list(backupsIter)
    except:
        print('no backups')


    return render_template('profileBackups.html', profileName=profile['profileName'], enterprise=enterprise, backups=list(backups), modules=modules, enterpriseId=enterpriseId, profileId=profileId)

@app.route('/enterprise/<int:enterpriseId>/profile/<int:profileId>/backup', methods=[ 'POST'])
def initiateBackupProfileModulePost(enterpriseId, profileId):

    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    backupSetName = request.form['name']


    table = db['profileList']
    profile = table.find_one(enterpriseId=enterpriseId, profileId=profileId)

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)

    profileModules = getProfileModules(enterpriseId, profileId)


    for moduleId in modules:
        for module in profileModules:
            if module['id'] == moduleId:
                table = db['profileModules']
                table.upsert(dict(enterpriseId=enterpriseId, profileName=profile['profileName'], backupSetName=backupSetName, moduleName=module['name'], profileId=profileId, moduleId=moduleId, version=module['version'], data=module), ['version', 'moduleName', 'backupSetName'])



        table = db['profileModules']
        backups = []

        try:
            backupsIter = table.find(enterpriseId=enterpriseId, profileId=profileId)
            backups = list(backupsIter)
        except:
            print('no backups')



    return render_template('profileBackups.html', profileName=profile['profileName'], enterprise=enterprise, backups=list(backups), modules=modules, enterpriseId=enterpriseId, profileId=profileId)

@app.route('/enterprise/<int:enterpriseId>/profile/<int:profileId>/compare', methods=[ 'POST'])
def initiateCompareProfileModulePost(enterpriseId, profileId):


    currentConfigList = request.json['currentConfigCompare']
    backedupConfigList = request.json['backedUpConfig']

    if len(currentConfigList) + len(backedupConfigList) != 2:
        return('Invalid number of configs selected')

    configList = []



    profileModules = getProfileModules(enterpriseId, profileId)

    for key in currentConfigList:
        for module in profileModules:
            if module['id'] == int(key):
                configList.append(module)


    for moduleId in backedupConfigList:
        table = db['profileModules']
        restoreIter = table.find(enterpriseId=enterpriseId, profileId=profileId, id=int(moduleId))
        restore = list(restoreIter)

        configList.append(restore[0]['data'])

    ddiff = DeepDiff(configList[1], configList[0], ignore_order=True, exclude_paths={"root['refs']", "root['version']", "root['modified']"}).pretty()
    if ddiff == "":
        ddiff = "No changes detected"
    # returnString = pprint.pformat(ddiff, indent=2)

    return(ddiff.replace('\n', '<br>'))

@app.route('/enterprise/<int:enterpriseId>/profile/<int:profileId>/delete', methods=[ 'POST'])
def initiateDeleteProfileModulePost(enterpriseId, profileId):

    table = db['profileList']
    profile = table.find_one(enterpriseId=enterpriseId, profileId=profileId)

    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)


    for moduleId in modules:
        table = db['profileModules']
        table.delete(enterpriseId=enterpriseId, profileId=profileId, id=moduleId)
        print('deleted module id '+ str(moduleId))

    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, profileId=profileId)
        backups = list(backupsIter)
    except:
        print('no backups')

    return render_template('profileBackups.html', profileName=profile['profileName'], enterprise=enterprise, backups=list(backups),
                           modules=modules, enterpriseId=enterpriseId, profileId=profileId)

@app.route('/enterprise/<int:enterpriseId>/profile/<int:profileId>/restore', methods=[ 'POST'])
def initiateRestoreProfileModulePost(enterpriseId, profileId):

    table = db['profileList']
    profile = table.find_one(enterpriseId=enterpriseId, profileId=profileId)

    modules = []
    for item in request.form:
        if item != 'name':
            modules.append(int(item))

    table = db['enterpriseList']
    enterprise = table.find_one(enterpriseId=enterpriseId)

    profileModules = getProfileModules(enterpriseId, profileId)

    for moduleId in modules:
        table = db['profileModules']
        restoreIter = table.find(enterpriseId=enterpriseId, profileId=profileId, id=moduleId)
        restore = list(restoreIter)


        restoreData = {}

        restoreData['data'] = restore[0]['data']['data']
        restoreData['name'] = restore[0]['moduleName']

        print('restore module id: ' + str(moduleId))
        resp = vcoClient.call_api("configuration/updateConfigurationModule", {
            "enterpriseId": enterpriseId,
            "_update": restoreData,
            "id": int(restore[0]['moduleId'])

        })

    backups = []

    try:
        backupsIter = table.find(enterpriseId=enterpriseId, profileId=profileId)
        backups = list(backupsIter)
    except:
        print('no backups')

    return render_template('profileBackups.html', profileName=profile['profileName'], enterprise=enterprise,
                           backups=list(backups),
                           modules=modules, enterpriseId=enterpriseId, profileId=profileId)


def getEdgeModules(enterpriseId, edgeId):

    resp = vcoClient.call_api("edge/getEdgeConfigurationStack", {
        "enterpriseId": enterpriseId,
        "edgeId": edgeId

    })

    edgeSpecificModules = []
    profileModules = []

    for item in resp:

        if item['name'] == 'Edge Specific Profile':
            edgeSpecificModules = item['modules']
        else:
            profileModules = item['modules']

    return edgeSpecificModules

def getProfileModules(enterpriseId, profileId):


    resp = vcoClient.call_api("configuration/getConfiguration",{
        "enterpriseId": enterpriseId,
        "id": profileId,
        "with": ["modules", "edgeCount"]

    })


    respModules = resp['modules']


    return respModules

if __name__ == '__main__':
    app.run()
