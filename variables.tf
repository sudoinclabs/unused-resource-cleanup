variable "EMAIL" {
    description = "Detailed notifications are sent to this email from SNS Topic"
    type = string
}

variable "IGNORE_WINDOW" {
    description = "Resources with activity in this window will be ignored. Value must be between 1 and 90"
    type = number
    default = 15
}

variable "DETAILED_NOTIFICATIONS" {
    description = "TRUE/FALSE, determines if detailed notifications are sent to SNS_ARN"
    type = string
    default = "TRUE"
}

variable "REGIONS" {
    description = "Comma seperated string of regions"
    type = string
    default = "us-east-1, us-east-2"
}