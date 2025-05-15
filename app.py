#!/usr/bin/env python3
import os

from aws_cdk import App, Environment

from line_bot_lambda_oneclick.line_bot_lambda_oneclick_stack import LineBotLambdaOneclickStack


app = App()
LineBotLambdaOneclickStack(app, "LineBotLambdaOneclickStack",
    # Use the current AWS account and region from the CLI configuration
    env=Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')
    ),
    description="Line Bot Lambda webhook with API Gateway or function URL options"
)

app.synth()
