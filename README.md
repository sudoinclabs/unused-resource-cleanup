AWS Unused Resource Finder
=================================

This Terraform module sets up the infrastructure to identify resources which have not been used for `X` days across multiple regions.

Module creates a Lambda function, CloudWatch Events rule (cron) to invoke Lambda, SNS topic to notify user along with reuired roles and policies.

### Lambda Function Logic:
Scan account for services across regions while filtering based on CreateTime/launch_time then use cloudtrail logs to identify unused resrouces.

```py
Services = ["AWS::EC2::Instance","AWS::EC2::Volume"]
```

Requirements
------------

| Name | Version |
|------|---------|
| terraform | 0.15.0 |

Providers
---------

| Name | Version |
|------|---------|
| aws  | 3.34.0  |

Module Input Variables
----------------------

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| IGNORE_WINDOW | Resources with activity in this window will be ignored. Value must be between 1 and 90 | `number` | `15` | No |
| REGIONS | Comma seperated string of regions | `string` | `"us-east-1, us-east-2"` | No |
| DETAILED_NOTIFICATIONS | TRUE/FALSE, determines if detailed notifications are sent to SNS_ARN | `string` | `"TRUE"` | No |
| EMAIL | Detailed notifications are sent to this email from SNS Topic | `string` | `"test@test.com"` | No |

-----
Usage
-----

```hcl
module "unused-resource-cleanup" {
  source = "https://github.com/sudoinclabs/unused-resource-cleanup"
  EMAIL = "saif.ali@sudoconsultants.com"
  IGNORE_WINDOW =  1
  DETAILED_NOTIFICATIONS = "TRUE"
  REGIONS = "us-east-1, us-east-2"
}
```

Install
-------

```shell
pip install -r requirements.txt -t ./code
```
The file [requirements.txt](./requirements.txt) includes all required libraries for the python code.

----------------
Folder Structure
----------------
The folder [code](./code) includes code for lambda.

```bash
$ tree
.
├── main.tf                   # Contains HCL for provisioning the resources
├── requirements.txt          # Install required libraries for the lambda function
├── .gitignore                
└── code
    └── lambda_function.py
```

Author
======

saif.ali@sudoconsultants.com

License
=======

[MIT](./LICENSE)