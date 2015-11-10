# aws-code-deploy

Automation tool for running an AWS CodeDeploy from the CLI. Supports:

 - Generating revisions using docker-compose.
 - Pushing a revision to S3.
 - Deploying a revision.
 - Watching revision status.


## Generating Revisions


t.b.d.


## Installing

t.b.d.


## Credentials

It is expected that you will set `AWS_PROFILE`. See [awsenv]() for credential management examples.

 [awsenv]: https://github.com/locationlabs/awsenv


## Usage:

Assuming that your CodeDeploy application exists, run:

    aws-code-deploy --application-name <application-name> --deployment-name <deployment-name> --description <description>

Use `--help` for other options.
