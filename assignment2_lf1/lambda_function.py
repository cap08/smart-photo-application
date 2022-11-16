import json
import os
import time
import logging
import boto3
import base64
from datetime import datetime
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):

    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    credentials = boto3.Session().get_credentials()

    logger.debug(credentials)
    records = event['Records']
    print(records)
    region = 'us-east-1'
    service = 'es'
    #with open('cat_pic600.jpg', "rb") as cf:
        #base64_image=base64.b64encode(cf.read())
        #base_64_binary = base64.decodebytes(base64_image)
    #resp = self.rekog_client.detect_labels(Image={'Bytes': base_64_binary})

    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    rekognition = boto3.client('rekognition')

    for record in records:

        s3object = record['s3']
        bucket = s3object['bucket']['name']
        objectKey = s3object['object']['key']
        s3 = boto3.client('s3')
        resp = s3.get_object(Bucket=bucket, Key=objectKey)
        image_bytes = resp['Body'].read()
        #base64_image=base64.b64encode(image_bytes)
        base_64_binary = base64.decodebytes(image_bytes)


        image = {
            'S3Object' : {
                'Bucket' : bucket,
                'Name' : objectKey
            }
        }
        print(image)
        response = rekognition.detect_labels(Image = {'Bytes':base_64_binary},MaxLabels=10,MinConfidence=80)
        labels = list(map(lambda x : x['Name'], response['Labels']))
        timestamp = datetime.now().strftime('%Y-%d-%mT%H:%M:%S')
        host="search-photos-v75p4n3eibdl47fzkvk62q5zdm.us-east-1.es.amazonaws.com"
        
        es = Elasticsearch(
            hosts=[{'host': host, 'port':443}],
            http_auth = awsauth,
            use_ssl = True,
            verify_certs = True,
            connection_class = RequestsHttpConnection)

        esObject = json.dumps({
            'objectKey' : objectKey,
            'bucket' : bucket,
            'createdTimesatamp' : timestamp,
            'base64': image_bytes.decode('utf-8'),
            'labels' : labels
        })

        es.index(index = "photos", doc_type = "Photo", id = objectKey, body = esObject, refresh = True)


    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }