# -*- coding: utf-8 -*-
# encoding=utf8

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
except ImportError:
    # Pour le développement en dehors de Kodi
    from mock_modules import xbmc
    from mock_modules import xbmcaddon

from . import cache, html
import sys, re, datetime, time, copy
import simplejson as json

if sys.version_info.major >= 3:
    # Python 3 stuff
    from urllib.parse import unquote, quote_plus, unquote_plus, urljoin, urlparse
    from urllib.request import Request, urlopen
else:
    # Python 2 stuff
    from urlparse import urljoin, urlparse
    from urllib import quote_plus, unquote_plus, unquote
    from urllib2 import Request, urlopen

ADDON = xbmcaddon.Addon()
ADDON_IMAGES_BASEPATH = ADDON.getAddonInfo('path')+'/resources/media/images/'
BASE_URL_SLUG = 'https://api.qub.ca/content-delivery-service/v1/entities?slug='
BASE_URL = 'https://api.qub.ca/content-delivery-service/v1/entities'

SEASON = 'Saison'
EPISODE = 'Episode'
LABEL = 'label'
FILTRES = '{"content":{"genreId":"","mediaBundleId":-1,"afficherTous":false},"show":{"' + SEASON + '":"","' + EPISODE + '":"","' + LABEL + '":""},"fullNameItems":[],"sourceId":""}'
INTEGRAL = 'Integral'

__handle__ = int(sys.argv[1])

def GetCopy(item):
    return copy.deepcopy(item)

def u(data):
    return data.encode('utf-8') #.decode('string_escape').decode('utf8')

def LoadSpecificSlugContent(slug, filtres):
    log(f"content.LoadSpecificSlugContent - Slug: {slug}")
    strURL = BASE_URL_SLUG + quote_plus(slug)
    log("Accessing: " + strURL)
    jsonData = json.loads(html.get_url_txt(strURL), encoding='utf-8')
    log("Returned:")
    log(jsonData)

    listItems = []

    if 'associatedEntities' in jsonData:
        for entity in jsonData['associatedEntities']:
            item = {}
            if 'label' in entity:
                item['title'] = entity['label']
            if 'slug' in entity:
                item['url'] = entity['slug']
            if 'mainImage' in entity and 'url' in entity['mainImage']:
                item['image'] = entity['mainImage']['url']
                item['fanart'] = entity['mainImage']['url']
            else:
                item['image'] = ADDON_IMAGES_BASEPATH + 'default-folder.png'
                item['fanart'] = ADDON.getAddonInfo('path') + '/resources/fanart.jpg'
            # Ajouter la clé 'plot' ici, même si la description n'est pas toujours présente
            item['plot'] = entity.get('description', '')

            item['isDir'] = True
            item['sortable'] = False
            item['filtres'] = GetCopy(filtres)
            item['filtres']['content']['url'] = item['url']
            item['filtres']['content']['containerId'] = item['url']
            item['filtres']['content']['genreId'] = 1

            listItems.append(item)
    elif 'name' in jsonData and 'referenceId' in jsonData: # Exemple pour un élément vidéo direct
        newItem = {
            'genreId': 1,
            'title': jsonData['name'],
            'sourceUrl': u'ref:' + jsonData['referenceId'],
            'filtres': GetCopy(filtres),
            'isDir': False,
            'sortable': False,
            'url': u'ref:' + jsonData['referenceId'],
            'image': jsonData.get('image', {}).get('url', ''),
            'fanart': jsonData.get('image', {}).get('url', ''),
            'plot': jsonData.get('description', ''), # Assurez-vous que 'description' existe toujours ou utilisez .get()
            'duration': jsonData.get('durationMillis', 0) / 1000,
            'startDate': jsonData.get('activationDate', ''),
            'genre': '',
            'rating': ''
        }
        listItems.append(newItem)
    else:
        log(f"content.LoadSpecificSlugContent - Structure JSON non gérée pour le slug")

    log("content.LoadSpecificSlugContentExit")
    return listItems

def LoadMainMenu(filtres):
    log("content.LoadMainMenu")

    strURL = BASE_URL_SLUG + "/qubtv-chaines"
    log("Accessing: " + strURL)
    jsonConfig = json.loads(html.get_url_txt(strURL, False), encoding='utf-8')
    log("Returned:")
    log(jsonConfig)

    xbmcaddon.Addon().setSetting('policyKey', html.get_policykey('5813221784001', 'sd748Ih4e', 'default'))

    jsonMenuItems = jsonConfig['associatedEntities']

    liste = []

    for carte in jsonMenuItems :
        if 'mainImage' in carte:
            image = carte['mainImage']['url']

            newItem = {   'genreId': 1,
                            'title': carte['label'],
                            'plot': u'Chaîne ' + carte['label'],
                            'image' : image,
                            'url' : carte['slug'],
                            'filtres' : GetCopy(filtres)
                        }

            newItem['filtres']['content']['url'] = carte['slug']
            newItem['isDir'] = True
            newItem['sortable'] = False
            newItem['fanart'] = ADDON.getAddonInfo('path') + '/resources/fanart.jpg'
            newItem['filtres']['content']['genreId'] = newItem['genreId']

            liste.append(newItem)

    # Ajouter une option pour le slug spécifique "toutes-les-emissions"
    specific_item = {
        'genreId': 1,
        'title': 'Toutes les émissions',
        'plot': 'Afficher toutes les émissions',
        'image': ADDON_IMAGES_BASEPATH + 'default-folder.png',
        'url': '/emissions/toutes-les-emissions',
        'filtres': GetCopy(filtres),
        'isDir': True,
        'sortable': False,
        'mode': 'load_specific_slug',
        'fanart': ADDON.getAddonInfo('path') + '/resources/fanart.jpg' # Ajout de fanart
    }
    liste.append(specific_item)

    log("content.LoadMainMenuExit")
    return liste

def LoadContainers(filtres):
    log("content.LoadContainers")
    log(filtres)

    if 'containerId' in filtres['content']:
        strURL = BASE_URL_SLUG + filtres['content']['containerId']
    else:
        strURL = BASE_URL_SLUG + filtres['content']['url']

    log("Accessing: " + strURL)
    jsonData = json.loads(html.get_url_txt(strURL), encoding='utf-8')
    log("Returned:")

    jsonContainers = jsonData['associatedEntities']

    listContainers = []
    if 'knownEntities' in jsonData:
        for entite in jsonData['knownEntities']:

            if 'videoStream' in entite or 'channel' in entite:
                enDirect = jsonData['knownEntities'][entite]
                newContainer = {'genreId': 1,
                                    'title': '-- En direct --',
                                    'filtres' : GetCopy(filtres)
                                    }
                try:
                    image = enDirect['image']['crops'][1]['url']
                except:
                    try:
                        image = enDirect['image']['url']
                    except:
                        image = enDirect['logo']['url']

                newContainer['image'] = image
                newContainer['fanart'] = ADDON.getAddonInfo('path')+'/fanart.jpg'

                newContainer['url'] = u'ref:' + enDirect['slug']
                newContainer['containerId'] = enDirect['slug']
                newContainer['plot'] = "."

                newContainer['filtres']['content']['containerId'] =  newContainer['containerId']
                newContainer['filtres']['content']['genreId'] = newContainer['genreId']

                newContainer['isDir'] = True
                newContainer['isForceDir'] = False
                newContainer['duration'] = 0
                newContainer['startDate'] = ''
                newContainer['genre'] = ''
                newContainer['rating'] = 'Everyone'
                newContainer['sortable'] = True

                listContainers.append(newContainer)

    for jsonContainer in jsonContainers :
        if 'name' in jsonContainer:
            if True:

                if 'associatedEntities' in jsonContainer:
                    for emission in jsonContainer['associatedEntities'] :
                        insert = True

                        if emission['discriminator'] == 'ExternalLinkPresentationEntity' or emission['discriminator'] == 'VideoPresentationEntity' or \
                                emission['discriminator'] == 'PosterPresentationEntity':
                            continue # ignore those kind of discriminator

                        for op in listContainers:
                            if op['containerId'] == emission['slug']:
                                insert = False
                                break

                        if insert:
                            newContainer = {'genreId': 1,
                                                'title': emission['label'],
                                                'filtres' : GetCopy(filtres)
                                                }
                            image = ""
                            if 'mainImage' in emission:
                                if 'crops' in emission['mainImage']:
                                    try:
                                        image = emission['mainImage']['crops'][0]['url']
                                    except:
                                        None
                                else:
                                    image = emission['mainImage']['url']

                            newContainer['image'] = image
                            newContainer['fanart'] = image

                            newContainer['url'] = newContainer['filtres']['content']['url']
                            newContainer['containerId'] = emission['slug']
                            newContainer['plot'] = "."

                            newContainer['filtres']['content']['containerId'] =  newContainer['containerId']
                            newContainer['filtres']['content']['genreId'] = newContainer['genreId']

                            newContainer['isDir'] = True
                            newContainer['sortable'] = True

                            listContainers.append(newContainer)

    log("content.LoadContainersExit")
    return listContainers

def LoadContainerItems(filtres):
    log("content.LoadContainerItems")
    log(filtres)

    strURL = BASE_URL_SLUG + filtres['content']['containerId']
    log("Accessing: " + strURL)
    jsonData = json.loads(html.get_url_txt(strURL), encoding='utf-8')
    log("Returned:")

    listItems = []
    try:
        if jsonData['discriminator'] == 'VideoShowEntity':
            for season in jsonData['knownEntities']['seasons']['associatedEntities']:
                strURL = BASE_URL_SLUG + season['slug']
                log("Accessing: " + strURL)

                jsonDataSaison = json.loads(html.get_url_txt(strURL), encoding='utf-8')

                for emission in jsonDataSaison['knownEntities']['relatedVideos']['associatedEntities'] :
                    for episode in emission['associatedEntities'] :
                        newItem = { 'genreId': 1,
                                    'title': 'Saison ' + str(season['seasonNumber']) + ' - ' + emission['name'] + ' - ' + episode['label'],
                                    'sourceUrl' : episode['slug'],
                                    'filtres' : GetCopy(filtres)
                                    }
                        newItem['isDir'] = False
                        newItem['sortable'] = False
                        newItem['url'] = episode['slug']
                        newItem['filtres']['content']['containerId'] = season['slug']
                        newItem['image'] = episode['mainImage']['url']
                        newItem['fanart'] = episode['mainImage']['url']
                        newItem['plot'] = episode.get('description')
                        newItem['duration'] = episode['durationMillis'] / 1000
                        newItem['startDate'] = episode['activationDate']
                        newItem['genre'] = ''
                        newItem['rating'] = ''

                        listItems.append(newItem)

        elif jsonData['discriminator'] == 'VideoStreamEntity':
            newItem = { 'genreId': 1,
                        'title': jsonData['name'],
                        'sourceUrl' : u'ref:' + jsonData['referenceId'],
                        'filtres' : GetCopy(filtres)
                        }
            newItem['isDir'] = False
            newItem['sortable'] = False
            newItem['url'] = newItem['sourceUrl']
            newItem['filtres']['content']['containerId'] = newItem['sourceUrl']
            newItem['image'] = jsonData['image']['url']
            newItem['fanart'] = jsonData['image']['url']
            newItem['plot'] = ''
            newItem['duration'] = ''
            newItem['startDate'] = ''
            newItem['genre'] = ''
            newItem['rating'] = ''

            listItems.append(newItem)

    except:
        log("content.LoadContainers: Error occured while processing")

    log("content.LoadContainerItemsExit")
    return listItems

def log(msg):
    """ function docstring """
    if xbmcaddon.Addon().getSetting('DebugMode') == 'true':
        xbmc.log('[%s - DEBUG]: %s' % (xbmcaddon.Addon().getAddonInfo('name'), msg))



try:
    mmock = xbmc.MODEMOCK
    val = {"content": {"genreId": 1, "mediaBundleId": -1, "afficherTous": False, "url": "/qub", 'containerId': '/qub/isabelle-marechal'}, "show": {"Saison": "", "Episode": "", "label": ""}, "fullNameItems": [], "sourceId": ""}
    LoadContainers(val)
except:
    None