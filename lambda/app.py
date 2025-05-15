import os
import json
import boto3
import logging
import uuid
import requests
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FileMessage
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager = boto3.client('secretsmanager')
s3 = boto3.client('s3')

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
    return line_bot_api, parser, channel_access_token

# Handle file upload from Line Bot
def handle_file_upload(line_bot_api, message_id, channel_access_token, file_name=None):
    try:
        # Get the S3 bucket name from environment variable
        bucket_name = os.environ['UPLOAD_BUCKET_NAME']
        
        # Get file content from Line Message API
        url = f'https://api-data.line.me/v2/bot/message/{message_id}/content'
        headers = {'Authorization': f'Bearer {channel_access_token}'}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get file content: {response.status_code} {response.text}")
            return None
        
        # Generate a unique filename while preserving original name
        content_type = response.headers.get('Content-Type', '')
        
        # Get original filename or use a default name based on content type
        original_filename = file_name if file_name else 'file'
        
        # Remove file extension from original filename if present
        if '.' in original_filename:
            original_name = original_filename.rsplit('.', 1)[0]
        else:
            original_name = original_filename
            
        # Clean the filename to remove any potentially problematic characters
        original_name = ''.join(c for c in original_name if c.isalnum() or c in '-_')
        
        # Set file extension based on content type
        file_extension = 'bin'  # Default extension
        if 'image' in content_type:
            file_extension = content_type.split('/')[1]
        elif 'audio' in content_type:
            file_extension = content_type.split('/')[1]
        elif 'video' in content_type:
            file_extension = content_type.split('/')[1]
        elif 'application/pdf' in content_type:
            file_extension = 'pdf'
        
        # Create filename with original name and UUID for uniqueness
        filename = f"{uuid.uuid4().hex[:8]}_{original_name}.{file_extension}"
        
        # Upload file to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=response.content,
            ContentType=content_type
        )
        
        logger.info(f"File uploaded to S3: {bucket_name}/{filename}")
        return f"s3://{bucket_name}/{filename}"
    
    except Exception as e:
        logger.error(f"Error handling file upload: {e}")
        return None

# Lambda handler function
def handler(event, context):
    # Log the event for debugging
    logger.info(f"Event: {json.dumps(event)}")
    
    # Get Line Bot credentials
    line_bot_api, webhook_parser, channel_access_token = get_line_bot_api()
    
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
            reply_token = event_obj.reply_token
            
            if isinstance(event_obj, MessageEvent):
                # Handle text messages
                if isinstance(event_obj.message, TextMessage):
                    user_message = event_obj.message.text
                    
                    # Echo the message back to the user
                    line_bot_api.reply_message(
                        reply_token,
                        TextSendMessage(text=f"You said: {user_message}")
                    )
                
                # Handle file messages
                elif isinstance(event_obj.message, FileMessage):
                    message_id = event_obj.message.id
                    file_name = event_obj.message.file_name
                    file_size = event_obj.message.file_size
                    
                    logger.info(f"Received file: {file_name}, size: {file_size}")
                    
                    # Upload file to S3
                    s3_path = handle_file_upload(line_bot_api, message_id, channel_access_token, file_name)
                    
                    if s3_path:
                        # Reply with success message
                        line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=f"File '{file_name}' uploaded successfully!")
                        )
                    else:
                        # Reply with error message
                        line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=f"Sorry, there was an error processing your file.")
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
