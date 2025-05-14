from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_apigateway as apigw,
    aws_iam as iam,
    CfnOutput,
    BundlingOptions,
)
from constructs import Construct

class LineBotLambdaOneclickStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a secret for Line Bot credentials
        line_bot_secret = secretsmanager.Secret(
            self, "LineBotCredentials",
            description="Line Bot API credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"CHANNEL_ACCESS_TOKEN":"","CHANNEL_SECRET":""}',
                generate_string_key="password"  # This is just a placeholder, not used
            )
        )
        
        # Create a Lambda Layer with the Line Bot SDK and dependencies
        line_bot_layer = _lambda.LayerVersion(
            self, "LineBotLayer",
            code=_lambda.Code.from_asset("lambda", 
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements-layer.txt -t /asset-output/python && cp -r /asset-input/* /asset-output/"
                    ],
                )
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            description="Layer containing Line Bot SDK and dependencies",
        )

        # Create Lambda function for Line Bot webhook
        line_bot_lambda = _lambda.Function(
            self, "LineBotFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset("lambda"),
            handler="app.handler",
            timeout=Duration.seconds(30),
            layers=[line_bot_layer],  # Attach the layer to the Lambda function
            environment={
                "SECRET_NAME": line_bot_secret.secret_name,
            }
        )

        # Grant Lambda function permission to read the secret
        line_bot_secret.grant_read(line_bot_lambda)

        # Create Lambda authorizer for API Gateway
        line_authorizer_lambda = _lambda.Function(
            self, "LineAuthorizerFunction",
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset("lambda/authorizer"),
            handler="authorizer.handler",
            timeout=Duration.seconds(10),
            layers=[line_bot_layer],  # Attach the layer to the authorizer
            environment={
                "SECRET_NAME": line_bot_secret.secret_name,
            }
        )

        # Grant authorizer Lambda function permission to read the secret
        line_bot_secret.grant_read(line_authorizer_lambda)

        # Create API Gateway with Lambda authorizer
        api = apigw.RestApi(
            self, "LineBotApi",
            description="API Gateway for Line Bot webhook",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=10,
                throttling_burst_limit=20
            )
        )
        
        # Create Lambda authorizer with support for request parameters
        authorizer = apigw.RequestAuthorizer(
            self, "LineAuthorizer",
            handler=line_authorizer_lambda,
            identity_sources=[
                "method.request.header.x-line-signature"
            ],
            results_cache_ttl=Duration.seconds(0)  # Disable caching for signature verification
        )
        
        # Create API Gateway resource and method
        webhook_resource = api.root.add_resource("webhook")
        webhook_method = webhook_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                line_bot_lambda,
                proxy=True,  # Use proxy integration to pass all request data
                passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_TEMPLATES,
                request_parameters={
                    "integration.request.header.x-line-signature": "method.request.header.x-line-signature"
                }
            ),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.CUSTOM,
            request_parameters={
                "method.request.header.x-line-signature": True
            }
        )
        
        # Set the webhook URL
        webhook_url = f"{api.url}webhook"
        
        # Output the API Gateway URL
        CfnOutput(
            self, "LineBotWebhookUrl",
            value=webhook_url,
            description="API Gateway URL for Line Bot webhook"
        )

        # Output instructions for setting up the secret
        CfnOutput(
            self, "SetupInstructions",
            value=f"Update the secret '{line_bot_secret.secret_name}' with your Line Bot credentials",
            description="Instructions for setting up Line Bot credentials"
        )
