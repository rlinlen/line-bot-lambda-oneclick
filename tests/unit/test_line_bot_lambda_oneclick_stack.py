import aws_cdk as core
import aws_cdk.assertions as assertions

from line_bot_lambda_oneclick.line_bot_lambda_oneclick_stack import LineBotLambdaOneclickStack

# example tests. To run these tests, uncomment this file along with the example
# resource in line_bot_lambda_oneclick/line_bot_lambda_oneclick_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = LineBotLambdaOneclickStack(app, "line-bot-lambda-oneclick")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
