import os
import json
import boto3
import logging
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager = boto3.client('secretsmanager')

# Get secrets from AWS Secrets Manager
def get_secret():
    secret_name = os.environ['SECRET_NAME']
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e

# Initialize Line Bot API with credentials from Secrets Manager
def get_line_bot_api():
    secret = get_secret()
    channel_access_token = secret.get('CHANNEL_ACCESS_TOKEN', '')
    channel_secret = secret.get('CHANNEL_SECRET', '')
    line_bot_api = LineBotApi(channel_access_token)
    parser = WebhookParser(channel_secret)
    return line_bot_api, parser

# Lambda handler function
def handler(event, context):
    # Log the event for debugging
    logger.info(f"Event: {json.dumps(event)}")
    
    # Get Line Bot credentials
    line_bot_api, webhook_parser = get_line_bot_api()
    
    # Extract headers from the event
    headers = event.get('headers', {}) or {}
    
    # Get the signature from headers (case-insensitive)
    signature = None
    for key, value in headers.items():
        if key and key.lower() == 'x-line-signature':
            signature = value
            break
    
    # Parse request body
    body_str = event.get('body', '{}')
    
    # Verify the signature
    try:
        if not signature:
            logger.error("Missing x-line-signature header")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Missing x-line-signature header'}),
                'headers': {'Content-Type': 'application/json'}
            }
        
        # Use Line Bot SDK's WebhookParser to verify the signature
        events = webhook_parser.parse(body_str, signature)
        logger.info("Signature verification successful")
    except InvalidSignatureError:
        logger.error(f"Invalid signature: {signature}")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid signature'}),
            'headers': {'Content-Type': 'application/json'}
        }
    except Exception as e:
        logger.error(f"Error parsing webhook: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Error: {str(e)}'}),
            'headers': {'Content-Type': 'application/json'}
        }
    
    # Process Line webhook events
    try:
        for event_obj in events:
            if isinstance(event_obj, MessageEvent) and isinstance(event_obj.message, TextMessage):
                reply_token = event_obj.reply_token
                user_message = event_obj.message.text
                
                # Echo the message back to the user (replace with your own logic)
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=f"You said: {user_message}")
                )
    except Exception as e:
        logger.error(f"Error processing events: {str(e)}")
        # Continue processing - don't fail the webhook
    
    # Return successful response
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'OK'}),
        'headers': {'Content-Type': 'application/json'}
    }
