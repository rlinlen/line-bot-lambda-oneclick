# Line Bot Lambda One-Click Deployment

This project creates a serverless Line Bot webhook using AWS Lambda with API Gateway and Lambda authorizer for security.

## Architecture

- **AWS Lambda**: Hosts the Line Bot webhook handler
- **Lambda Layer**: Contains the Line Bot SDK and dependencies
- **API Gateway with Lambda Authorizer**: Provides secure HTTPS endpoint with custom authorization
- **AWS Secrets Manager**: Securely stores Line Bot credentials
- **Line Bot SDK**: Handles Line Message API interactions
- **Amazon S3**: Stores files uploaded through the Line Bot

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Line Developer account and a Line Bot channel created
3. Channel access token and channel secret from Line Developer Console
4. Node.js and Python installed
5. AWS CDK installed

## Deployment Instructions

1. Clone this repository
2. Install dependencies:
   ```
   cd line-bot-lambda-oneclick
   uv venv .venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. Deploy the stack:
   ```
   # To create a new S3 bucket automatically:
   cdk deploy
   
   # To use an existing S3 bucket:
   cdk deploy -c bucket_name=your-existing-bucket-name
   ```

4. After deployment, you'll receive three outputs:
   - `LineBotWebhookUrl`: The URL to set as webhook URL in Line Developer Console
   - `SetupInstructions`: Instructions for setting up Line Bot credentials
   - `FileUploadBucketName`: The name of the S3 bucket used for file uploads
   - `BucketInfo`: Information about whether a new bucket was created or an existing one was used

5. Update the secret in AWS Secrets Manager with your Line Bot credentials:
   - Go to AWS Secrets Manager console
   - Find the secret with the name from the output
   - Update the secret value with your credentials:
   ```json
   {
     "CHANNEL_ACCESS_TOKEN": "your-channel-access-token",
     "CHANNEL_SECRET": "your-channel-secret"
   }
   ```

6. Set the webhook URL in Line Developer Console:
   - Go to your Line Bot settings in Line Developer Console
   - Set the webhook URL to the `LineBotWebhookUrl` value from the CDK output
   - Verify the webhook

## Security Features

- **API Gateway with Lambda Authorizer**: Validates Line signatures before forwarding requests to the webhook Lambda
- **Signature Verification**: Each request is verified using the Line signature
- **Secrets Manager**: Line Bot credentials are stored securely in AWS Secrets Manager

Why API Gateway? Otherwise everyone can call your lambda function. With API Gateway, we filter most of the traffic, and it can integrate with the AWS WAF to protect your API when needed.

## Lambda Layer

This project uses a Lambda Layer to manage the Line Bot SDK dependency. The Layer is automatically created during deployment and contains:
- line-bot-sdk
- boto3

Benefits of using Lambda Layers:
- Separates dependencies from function code
- Reduces deployment package size
- Makes function code updates faster
- Allows sharing dependencies across multiple functions

## S3 Bucket Options

You have two options for the S3 bucket used to store files uploaded through the Line Bot:

1. **Create a new bucket**: By default, the stack will create a new S3 bucket with appropriate security settings.
2. **Use an existing bucket**: You can specify an existing bucket name using the CDK context parameter `bucket_name`.

When using an existing bucket, make sure it has appropriate permissions and security settings.

## Customization

To customize the bot's behavior, modify the `lambda/app.py` file. The current implementation is a simple echo bot that replies with the received message and handles file uploads.

## Cleanup

To remove all resources created by this stack:

```
cdk destroy
```

Note: If you used the default configuration, the S3 bucket will be retained even after stack deletion to prevent accidental data loss. You'll need to delete it manually if desired.
