# Create public SNS topic
resource "aws_sns_topic" "nc_notify" {
  name = "nc_notify"
}

# create an email subscription for the SNS topic 
module "sns-email-subscription" {
  source  = "QuiNovas/sns-email-subscription/aws"
  version = "0.0.3"
  email_address = var.EMAIL
  topic_arn = aws_sns_topic.nc_notify.arn
}

# Create IAM Role for Lambda Custom Function
resource "aws_iam_role" "ncResourceFinder_role1" {
  name = "ncResourceFinder_role1"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

# Create policy: Add More permissions for other resources.
resource "aws_iam_policy" "ncResourceFinder_policy" {
  name        = "ncResourceFinder_policy"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "cloudtrail:LookupEvents",
                "cloudtrail:StartLogging",
                "cloudtrail:GetTrailStatus",
                "cloudtrail:DescribeTrails",
                "cloudtrail:CreateTrail",
                "logs:CreateLogGroup",
                "logs:PutLogEvents",
                "logs:CreateLogStream",
                "sns:Publish",
                "ec2:DescribeVolumeAttribute",
                "ec2:DescribeVolumeStatus",
                "ec2:DescribeVolumes",
                "ec2:*"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}

# Attach policy to role
resource "aws_iam_policy_attachment" "example" {
  name       = "Attach ncResourceFinder_policy to ncResourceFinder_role1 "
  roles      = [aws_iam_role.ncResourceFinder_role1.name]
  policy_arn = aws_iam_policy.ncResourceFinder_policy.arn
}

# Create zip file for code directory
data "archive_file" "init" {
  type = "zip"
  source_dir = "${path.module}/code"
  output_path = "${path.module}/code.zip"
}

# Create Lambda function
resource "aws_lambda_function" "ncResourceFinder" {
    function_name = "ncResourceFinder"
    filename      = data.archive_file.init.output_path
    role          = aws_iam_role.ncResourceFinder_role1.arn
    handler       = "ncResourceFinder.lambda_handler"
    timeout       = 180
    memory_size   = 256
    runtime       = "python3.8"

    source_code_hash = filebase64sha256(data.archive_file.init.output_path)

    environment {
        variables = {
            IGNORE_WINDOW = var.IGNORE_WINDOW,
            REGIONS = var.REGIONS,
            SNS_ARN = aws_sns_topic.nc_notify.arn,
            DETAILED_NOTIFICATIONS = var.DETAILED_NOTIFICATIONS
        }
    }
}

# CloudWatch Events rule
resource "aws_cloudwatch_event_rule" "console" {
    name        = "cron-rule"
    description = "Run function based of CRON: every 15 days"
    # Run at 00:00 every 15 days.
    schedule_expression = "cron(0 0 */15 * ? *)"
}

# Add ncResourceFinder as target
resource "aws_cloudwatch_event_target" "lambda" {
    rule      = aws_cloudwatch_event_rule.console.name
    target_id = "trigger-ncResourceFinder"
    arn       = aws_lambda_function.ncResourceFinder.arn
}

# Allow event_rule to invoke ncResourceFinder
resource "aws_lambda_permission" "allow_cloudwatch_to_call_ncResourceFinder" {
  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ncResourceFinder.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.console.arn
}
