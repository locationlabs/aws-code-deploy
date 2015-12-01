"""
Deployment operations.
"""
from argparse import Namespace
from contextlib import contextmanager
from logging import getLogger
from re import search
from StringIO import StringIO
import sys

from awscli.customizations.codedeploy.push import Push
from termcolor import colored


@contextmanager
def capture_stdout():
    """
    Temporarily capture stdout.
    """
    try:
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        yield sys.stdout
    finally:
        sys.stdout = old_stdout


def push(profile, args, revision):
    """
    Run "aws deploy push" against a generated revision.

    Uses the AWS CLI directly because push logic is slightly involved and the
    code already exists.
    """
    logger = getLogger("push")

    logger.info("[{}] Pushing revision of {} to bucket: {}".format(
        colored("push", "cyan"),
        colored(args.deployment_name, "green"),
        colored(args.bucket, "green"),
    ))

    with capture_stdout() as capture, revision.make() as revision_dir:
        push_command = Push(profile.session)
        # simulate CLI args and global args
        push_command([
            "--application-name", args.application_name,
            "--s3-location", "s3://{}/{}/{}.zip".format(
                args.bucket,
                args.application_name,
                args.deployment_name,
            ),
            "--ignore-hidden-files",
            "--source", revision_dir,
        ], Namespace(
            region=profile.region_name,
            endpoint_url=None,
            verify_ssl=True,
        ))

        result = capture.getvalue()
        # Note that the push command returns the next instructions as an AWS CLI call. Parse it.
        etag = search('eTag="([a-f0-9]+)"', result).group(1)

    logger.info("[{}] Generated revision eTag: {}".format(
        colored("push", "cyan"),
        colored(etag, "green"),
    ))

    return etag


def deploy(profile, client, args):
    """
    Run "aws deploy create-deployment" (or the botocore equivalent).

    Uses botocore because this is just a single API call and there's no similar
    AWS CLI abstraction.
    """
    logger = getLogger("deploy")
    logger.info("[{}] Deploying revision {} from bucket: {}".format(
        colored("deploy", "cyan"),
        colored(args.deployment_name, "green"),
        colored(args.bucket, "green"),
    ))

    result = client.create_deployment(**{
        "applicationName": args.application_name,
        "deploymentConfigName": args.deployment_config,
        "deploymentGroupName": args.deployment_name,
        "description": args.description,
        # If the previous revision didn't have an ApplicationStop script,
        # the current script will fail every time if it attempts to process this event
        # because the script of the last successful deploy is used, not the new one.
        "ignoreApplicationStopFailures": True,
        "revision": {
            "revisionType": "S3",
            "s3Location":  {
                "bucket": args.bucket,
                "key": "{}/{}.zip".format(
                    args.application_name,
                    args.deployment_name,
                ),
                "bundleType": "zip",
                "eTag": args.etag,
            }
        },
    })

    deployment_id = result["deploymentId"]

    logger.info("[{}] Generated deployment id: {}".format(
        colored("deploy", "cyan"),
        colored(deployment_id, "green"),
    ))

    # The AWS Console doesn't currently have a great way to navigate to a deployment
    url = "https://{}.console.aws.amazon.com/codedeploy/home?region={}#/deployments/{}".format(
        profile.region_name,
        profile.region_name,
        deployment_id,
    )

    logger.info("[{}] To follow along, browse to: {}".format(
        colored("deploy", "cyan"),
        colored(url, "green"),
    ))

    return deployment_id
