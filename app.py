#!/usr/bin/env python3
import os

import aws_cdk as cdk

from line_bot_lambda_oneclick.line_bot_lambda_oneclick_stack import LineBotLambdaOneclickStack


app = cdk.App()
LineBotLambdaOneclickStack(app, "LineBotLambdaOneclickStack",
    # Use the current AWS account and region from the CLI configuration
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'), 
        region=os.getenv('CDK_DEFAULT_REGION')
    ),
    description="Line Bot Lambda webhook with API Gateway or function URL options"
)

app.synth()
