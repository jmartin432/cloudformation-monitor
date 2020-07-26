import boto3
import json
import logging
import os
from string import Template

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

webhook_base = "https://hooks.slack.com/services"
webhook_path = os.environ['StaticSitesPipelineSlackWebHookPath']
slack_message = {
    "text": "CodeBuild Status Change",
    "attachments": [
        {
            "text": "",
            "color": ""
        }
    ]
}

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def send_slack_message(this_id, header, details, color):
    slack_message['text'] = header
    slack_message['attachments'][0]['text'] = details
    slack_message['attachments'][0]['color'] = color

    url = Template('$base$path').safe_substitute(base=webhook_base, path=webhook_path)
    json_message = json.dumps(slack_message).encode('utf-8')
    req = Request(url, json_message)

    try:
        response = urlopen(req)
        response.read()
        message = Template('Message posted to slack channel. Event ID: $event_id') \
            .safe_substitute(event_id=this_id)
        logger.info(message)
    except HTTPError as e:
        message = Template('Slack request failed: $code $reason') \
            .safe_substitute(code=e.code, reason=e.reason)
        logger.error(message)
    except URLError as e:
        message = Template('Server connection failed: $reason') \
            .safe_substitute(reason=e.reason)
        logger.error(message)

    return


def handler(event, context):
    logger.info(event)

    message_id = event['Records'][0]['Sns']['MessageId']
    logger.info(Template('Received CloudFormation update message. Message ID $message_id')
                .safe_substitute(message_id=message_id))

    sns_message = {}
    for line in str.splitlines(event['Records'][0]['Sns']['Message']):
        x = line.split('=')
        sns_message[x[0]] = x[1]
    logger.info(Template('SNS Message: $sns_message')
                .safe_substitute(sns_message=sns_message))

    timestamp = sns_message['Timestamp']
    logical_resource_id = sns_message['LogicalResourceId']
    resource_status = sns_message['ResourceStatus']
    stack_name = sns_message['StackName']
    if 'COMPLETE' in resource_status:
        emoji = '👍'
        color = '#30b342'
    elif 'FAILED' in resource_status:
        emoji = '😢'
        color = '#cc2d1f'
    elif 'IN_PROGRESS' in resource_status:
        emoji = '🤔'
        color = '#e0de43'
    else:
        emoji = '😕'
        color = '#065196'

    details = Template('Stack Name: $stack_name\nTimestamp: $timestamp\nResource ID: $resource_id\nResource Status: '
                       '$resource_status $emoji\nSNS Message ID: $message_id') \
        .safe_substitute(stack_name=stack_name, timestamp=timestamp, resource_id=logical_resource_id,
                         resource_status=resource_status, emoji=emoji, message_id=message_id)
    header = 'CloudFormation Status Update'
    send_slack_message(message_id, header, details, color)

    return

