import json
import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
import requests
import urllib.parse
import inflect
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection
    
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#Test
headers = { "Content-Type": "application/json" }
host = 'search-photos-v75p4n3eibdl47fzkvk62q5zdm.us-east-1.es.amazonaws.com'
region = 'us-east-1'
lex = boto3.client('lex-runtime', region_name=region)

def lambda_handler(event, context):

    print ('event : ', event)
    q1 = event['queryStringParameters']['q']
    labels = get_labels(q1)
    print("labels", labels)
    p=inflect.engine()
    for i in range(len(labels)):
        if p.singular_noun(labels[i]):
            labels[i]=p.singular_noun(labels[i])
    if len(labels) != 0:
        img_paths,base64_data = get_photo_path(labels)
    for i in range(len(base64_data)):
        if img_paths[i][-3:]=='png':
            temp="data:image/png;base64,"+base64_data[i]
            base64_data[i]=temp
        else:
            temp="data:image/jpeg;base64,"+base64_data[i]
            base64_data[i]=temp
    
    body={'imagePaths':img_paths,'userQuery':q1,'labels': labels, 'base64': base64_data}

    if not img_paths:
        return{
            'isBase64Encoded': True,
            'statusCode':200,
            'headers': {
            'Access-Control-Allow-Headers' : 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
            'body': json.dumps('No Results found')
        }
    else:    
        return{
            'isBase64Encoded': True,
            'statusCode': 200,
            'headers': {
            'Access-Control-Allow-Headers' : 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
            'body': json.dumps(body)
        }
    
def get_labels(query):
    print(query)
    response = lex.post_text(
        botName='SearchBot',                 
        botAlias='$LATEST',
        userId="test1",           
        inputText=query
    )
    print("lex-response", response)
    
    labels = []
    if 'slots' not in response:
        print("No photo collection for query {}".format(query))
    else:
        print ("slot: ",response['slots'])
        slot_val = response['slots']
        for key,value in slot_val.items():
            if value!=None:
                labels.append(value)
    return labels

    
def get_photo_path(keys):
    
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, 'es', session_token=credentials.token)
    es = Elasticsearch(
         hosts = [{'host': host, 'port': 443}],
         http_auth = awsauth,
         use_ssl = True,
         verify_certs = True,
         connection_class = RequestsHttpConnection
     )
    
    resp = []
    for key in keys:
        if (key is not None) and key != '':
            searchData = es.search({"query": {"match": {"labels": key}}})
            resp.append(searchData)
    print(resp)
    output = []
    img_data=[]
    for r in resp:
        if 'hits' in r:
             for val in r['hits']['hits']:
                key = val['_source']['objectKey']
                data=val['_source']['base64']
                if key not in output:
                    output.append('https://assignment2b2.s3.amazonaws.com/'+key)
                    img_data.append(data)
    print (output)
    return output,img_data  
