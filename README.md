# aws-code-deploy

Automation tool for running an AWS CodeDeploy from the CLI. Supports:

 - Generating revisions using variable strategies, including [docker-compose](https://docs.docker.com/compose/).
 - Pushing a revision to S3.
 - Deploying a revision.
 - Watching revision status.

[![Build Status](https://travis-ci.org/locationlabs/aws-code-deploy.png)](https://travis-ci.org/locationlabs/aws-code-deploy)


## Prerequisites

It is assumed that you are familiar with AWS CodeDeploy and have already configured your CodeDeploy application, deployment,
and all relevant access controls.

It is also expected that you have configured the AWS CLI's usual credentials via `aws configure`. In addition, cross-account
access profiles are supported via [awsenv](https://github.com/locationlabs/awsenv). Just set `AWS_PROFILE` or run `--profile`.


## Installing

Use `pip`:

    pip install awscodedeploy


## Basic Usage:

The most basic usage generates the equivalent of a "hello world" revision and deploys it:

    aws-code-deploy \
	  --application-name <application-name> \
	  --deployment-name <deployment-name> \
	  --description <description> \
	  --hello-world

Use `--help` for other options.


## Docker Compose

The CLI options supports multiple revision types, including `--docker-compose`, which should specify the path to a valid
`docker-compose.yml` file. If selected, this revision will:

 -  Stop and remove the previous compose, if any.
 -  Pull all images specified in the compose.
 -  Run the docker compose.

This provides a clean abstraction around arbitrary deployment logic. Be sure your access controls are configured properly!
