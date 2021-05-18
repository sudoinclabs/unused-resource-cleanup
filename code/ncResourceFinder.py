import json
import itertools
from datetime import datetime, timedelta 
import os, os.path, sys
import boto3
import botocore
from botocore.exceptions import ClientError

### environment variables:
#### IGNORE_WINDOW -- resources with activity in this window will be ignored even if they are available; e.g. for a 30 day IGNORE_WINDOW, a volume detached 29 days ago will not be flagged, but a volume detached 31 days ago will. Value must be between 1 and 90
#### SNS_ARN -- Full ARN for SNS topic to send notifications to, this topic is also used to send detailed notifications when enabled
#### DETAILED_NOTIFICATIONS -- TRUE/FALSE, determines if detailed notifications are sent to SNS_ARN with the list of volumes found

# Helpers
def detailedNotifier(ncResourceDict):
    sns = boto3.client('sns')
    message = json.dumps(ncResourceDict, indent=4, default=str)
    try:
        response = sns.publish(
            TopicArn=os.environ["SNS_ARN"],
            Message=message,
        )
        return response
    except ClientError as err:
        print(err)

def validateEnvironmentVariables():
    if(int(os.environ["IGNORE_WINDOW"]) < 1 or int(os.environ["IGNORE_WINDOW"]) > 90):
        print("Invalid value provided for IGNORE_WINDOW. Please choose a value between 1 day and 90 days.")
        raise ValueError('Bad IGNORE_WINDOW value provided')
    if(os.environ["DETAILED_NOTIFICATIONS"].upper() not in ["TRUE", "FALSE"]):
        print("Invalid value provided for DETAILED_NOTIFICATIONS. Please choose TRUE or FALSE.")
        raise ValueError('Bad DETAILED_NOTIFICATIONS value provided')

def getNCVolumes(rgn, startDateTime, status):
    # returns list of volumes
    ec2 = boto3.client('ec2', region_name=rgn)
    ncVolumes = []
    filterList = [{'Name': 'status', 'Values': [status]}]
    response = ec2.describe_volumes(Filters=filterList)

    try:
        volumes = response['Volumes']
    except:
        volumes = []

    if volumes:
        for vol in volumes:
            # Extract and filter based on CreateTime date. 
            if vol['CreateTime'].date() < startDateTime.date():
                ncVolumes.append(vol)
    return ncVolumes

def getNCInstances(rgn, startDateTime, status):
    # returns list of instances
    ec2 = boto3.client('ec2', region_name=rgn)
    ncInstances = []
    filterList = [{'Name': 'instance-state-name', 'Values': status}]
    response = ec2.describe_instances(Filters=filterList)
   
    for res in response.get('Reservations'):
        
        try:
            instances = res.get('Instances')
        except:
            instances = []

        if instances:
            for ins in instances:
                # Extract and filter based on CreateTime date. 
                if ins['LaunchTime'].date() < startDateTime.date():
                    ncInstances.append(ins)
    
    return ncInstances

def getCloudTrailEvents(startDateTime, rgn, resourceType):
    # gets CloudTrail events from startDateTime until "now"
    cloudTrail = boto3.client('cloudtrail', region_name=rgn)
    attrList = [{'AttributeKey': 'ResourceType', 'AttributeValue': resourceType}]
    eventList = []
    response = cloudTrail.lookup_events(LookupAttributes=attrList, StartTime=startDateTime, MaxResults=50)
    eventList += response['Events']
    while('NextToken' in response):
        response = cloudTrail.lookup_events(LookupAttributes=attrList, StartTime=startDateTime, MaxResults=50, NextToken=response['NextToken'])
        eventList += response['Events']
    return eventList

def getRecentResources(events, resourceType):
    # parses volumes from list of events from CloudTrail
    recentResources = []
    for e in events:
        for i in e['Resources']:
            if i['ResourceType'] == resourceType:
                recentResources.append(i['ResourceName'])
    recentResourceSet = set(recentResources) # remove duplicates
    return recentResourceSet

def lambda_handler(event, context):
    acctID = context.invoked_function_arn.split(":")[4]
     # used with Lambda to get desired SNS topic ARN
    snsArn = [{"Arn": os.environ["SNS_ARN"]}]
    
    # validate environment variables
    try:
        validateEnvironmentVariables()
    except ValueError as vErr:
        print(vErr)
        sys.exit(1)

    # collect available EBS volumes and attachment history
    startDateTime = datetime.today() - timedelta(days=int(os.environ["IGNORE_WINDOW"])) # IGNORE_WINDOW defined in environment variables

    try:
        # Split the commma seperated regions string
        temp = os.environ["REGIONS"]
        regions = temp.replace(" ","").split()
    except Exception as e:
        print(e)
        sys.exit(1)

    # Services to scan
    services = ["AWS::EC2::Instance","AWS::EC2::Volume"]

    flaggedResourceDict = {}
    for rgn in regions:
        flaggedResourceDict[rgn] = {}

        # "AWS::EC2::Volume"
        ncVolumes = getNCVolumes(rgn, startDateTime, 'available')

        flaggedResourceDict[rgn][services[1]] = []
        for vol in ncVolumes:
            flaggedResourceDict[rgn][services[1]].append({
                'State'     : vol['State'],
                'VolumeId'  : vol['VolumeId'],
                'CreateTime': vol['CreateTime']
            })

        # "AWS::EC2::Instance"
        ncInstances = getNCInstances(rgn, startDateTime, ['running','stopped'])
        flaggedResourceDict[rgn][services[0]] = []

        for ins in ncInstances:
            flaggedResourceDict[rgn][services[0]].append({
                'InstanceId': ins['InstanceId'],
                'LaunchTime': ins['LaunchTime'],
                'State': ins['State'].get('Name'),
                'BlockDeviceMappings': ins['BlockDeviceMappings']
            })

    # print(json.dumps(flaggedResourceDict, indent=4, default=str))

    # CloudTrail trail to identify recently used resources. 
    cloudTrailResources = {}
    for rgn in regions:
        cloudTrailResources[rgn] = {}
        for serv in services:
            eventList = getCloudTrailEvents(startDateTime, rgn, serv)
            activeResources = getRecentResources(eventList, serv)
            
            cloudTrailResources[rgn][serv] = list(activeResources)

    # print(cloudTrailResources)

    serv_id_dict = {
        'AWS::EC2::Volume':'VolumeId',
        'AWS::EC2::Instance':'InstanceId'
    }

    # Subtract cloudtrailResources from flaggedResourceDict
    output = {}
    for rgn in regions:
        output[rgn] = {}
        for serv in services:
            output[rgn][serv] = []
            for res in flaggedResourceDict[rgn][serv]:
                if res.get(serv_id_dict[serv]) not in cloudTrailResources[rgn][serv]:
                    output[rgn][serv].append(res)
    
    print(json.dumps(output, indent=4, default=str))

    if(os.environ["DETAILED_NOTIFICATIONS"].upper() == "TRUE"):
        try:
            print(detailedNotifier(output))
        except ClientError as err:
            print(err)