import os
import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secretsmanager = boto3.client('secretsmanager')

def get_secret():
    """Get Line Bot credentials from AWS Secrets Manager"""
    secret_name = os.environ['SECRET_NAME']
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        logger.error(f"Error retrieving secret: {e}")
        raise e

def generate_policy(principal_id, effect, resource, context=None):
    """Generate IAM policy document for API Gateway authorizer response"""
    auth_response = {
        'principalId': principal_id
    }
    
    if effect and resource:
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
        auth_response['policyDocument'] = policy_document
    
    # Optional context for passing information to the backend
    if context:
        auth_response['context'] = context
    
    return auth_response

def handler(event, context):
    """Lambda authorizer handler function"""
    logger.info(f"Authorizer Event: {json.dumps(event)}")
    
    try:
        # Extract headers from the event
        headers = {}
        if 'headers' in event:
            headers = event['headers'] or {}
        elif 'requestContext' in event and 'http' in event['requestContext']:
            headers = event['requestContext']['http'].get('headers', {})
        
        # Get the signature from headers (case-insensitive)
        signature = None
        for key, value in headers.items():
            if key and key.lower() == 'x-line-signature':
                signature = value
                break
        
        # Check if the signature header is present
        if not signature:
            logger.error("Missing x-line-signature header")
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Pass the signature to the main Lambda function via context
        # We can't verify the signature here because we don't have the body
        context = {
            'signature': signature
        }
        
        # Allow the request to proceed to the main Lambda function
        # The main function will verify the signature with the body
        logger.info("Signature header found, allowing request to proceed")
        return generate_policy('line-user', 'Allow', event['methodArn'], context)
        
    except Exception as e:
        logger.error(f"Error in authorizer: {e}")
        return generate_policy('user', 'Deny', event['methodArn'])
