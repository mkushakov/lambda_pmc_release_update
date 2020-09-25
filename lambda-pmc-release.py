import requests
import json
import objectpath
import re


pmc_prod = {
    'client_id' : '',
    'client_secret' : '',
    'pmcrm_url' : 'https://pmcrm'
}
pmc_qa = {
    'client_id' : '',
    'client_secret' : '',
    'pmcrm_url' : 'https://rm-pmc-qa'
}
pmc_test = {
    'client_id' : '',
    'client_secret' : '',
    'pmcrm_url' : 'https://rm-pmc-test'
}

def get_token(client_id, client_secret):
    return requests.post('https://passport/api/auth', json={
        'client_id': client_id,
        'client_secret': client_secret,
        })
def get_releases(token, app_id, pmcrm_url):
    if app_id is 'empty':
        return requests.get(pmcrm_url+'/api/ApplicationRelease?after=null', headers={
            'Authorization':'bearer ' + token
        })
    else:
        return requests.get(pmcrm_url+'/api/ApplicationRelease?id='+app_id, headers={
            'Authorization':'bearer ' + token
        })
def put_release(token, app_id, payload, pmcrm_url):
    return requests.put(pmcrm_url+'/api/ApplicationRelease?id='+app_id, headers={
            'Authorization':'bearer ' + token
        }, json=payload)

def lambda_handler(event, context):
    
    app_release = event['queryStringParameters']['app_release']
    dbVersion = event['queryStringParameters']['dbVersion']
    
    try:
        env = event['queryStringParameters']['env']
    except KeyError:
        env = 'pmc_prod'
        
    app_id = 'empty'
    
    if (env == 'pmc_prod' or env == 'pmc'):
        client_id = pmc_prod['client_id']
        client_secret = pmc_prod['client_secret']
        pmcrm_url = pmc_prod['pmcrm_url']
    elif (env == 'pmc_qa'):
        client_id = pmc_qa['client_id']
        client_secret = pmc_qa['client_secret']
        pmcrm_url = pmc_qa['pmcrm_url']
    elif (env == 'pmc_test'):
        client_id = pmc_test['client_id']
        client_secret = pmc_test['client_secret']
        pmcrm_url = pmc_test['pmcrm_url']
    else:
        raise Exception('Not known PMC enviroment defined: {}'.format(env))
    
    print(dbVersion)
    p = re.match("^\d+\.\d+\.(\d+|\*)$", dbVersion)
    if p is None:
        return {
            'statusCode': 400,
            'body': 'Please send correct dbVersion'
         }
    
    # Geting token from Passport
    resp = get_token(client_id, client_secret)
    if resp.status_code != 200:
        return {
            'statusCode': 400,
            'body': 'Cannot authorize in Passport: {}'.format(resp.status_code)
        }
        raise Exception('Cannot authorize in Passport: {}'.format(resp.status_code))
    token = resp.json()['access_token']

    # Get application releases
    resp = get_releases(token, app_id, pmcrm_url)
    if resp.status_code != 200:
        return {
            'statusCode': 400,
            'body': 'Cannot get Application Releases \nCode: {}\nError: {}'.format(resp.status_code, resp.text)
        }
        raise Exception('Cannot get Application Releases \nCode: {}\nError: {}'.format(resp.status_code, resp.text))
    releses = resp.json()

    tree = objectpath.Tree(releses)
    result = tree.execute("$..*[@.Label is '"+app_release+"']") 
    for entry in result:
        app_id = entry['ID']

    # Get current application release payload
    if (app_id == 'empty'):
        return {
            'statusCode': 400,
            'body': 'Cannot find ID for AppRelease {} in PMC_RM'.format(app_release)
        }
    resp = get_releases(token, app_id, pmcrm_url)
    if resp.status_code != 200:
        return {
            'statusCode': 400,
            'body': 'Cannot find AppRelease {} for ID {} in PMC_RM: {}'.format(app_release, app_id, resp.text)
        }
        raise Exception('Cannot find AppRelease {} for ID {} in PMC_RM: {}'.format(app_release, app_id, resp.text))
    payload = resp.json()

    # Update database version for applicaton release
    payload.update({'DatabaseVersion': dbVersion})
    resp = put_release(token, app_id, payload, pmcrm_url)
    if resp.status_code != 204:
        return {
            'statusCode': 400,
            'body': 'Cannot update AppRelease {} {} in PMC\nCode: {} Message: {}'.format(app_release, app_id, resp.status_code, resp.text)
        }
        raise Exception('Cannot update AppRelease {} {} in PMC\nCode: {} Message: {}'.format(app_release, app_id, resp.status_code, resp.text))
    result = 'Database update for {} {} has been updated to {}'.format(app_release, app_id, dbVersion)
    print(result)

    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
