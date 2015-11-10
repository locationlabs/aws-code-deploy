#!/usr/bin/env python
from argparse import ArgumentParser
from logging import basicConfig, getLogger
from os import environ

from awsenv.main import get_profile
from botocore.client import Config
from botocore.exceptions import ClientError

from awscodedeploy.deploy import push, deploy
from awscodedeploy.revision import Revision
from awscodedeploy.wait import wait_for_deploy


def parse_args():
    """
    Parse arguments.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--application-name",
        required=True,
        help="CodeDeploy application name",
    )
    parser.add_argument(
        "--deployment-config",
        default="CodeDeployDefault.OneAtATime",
        help="CodeDeploy deployment configuration",
    )
    parser.add_argument(
        "--deployment-id",
        help="CodeDeploy deployment id to poll",
    )
    parser.add_argument(
        "--deployment-name",
        required=True,
        help="CodeDeploy deployment name",
    )
    parser.add_argument(
        "--description",
        help="Description of this deployment"
    )
    parser.add_argument(
        "--profile",
        default=environ.get("AWS_PROFILE"),
        help="AWS CLI profile",
    )
    parser.add_argument(
        "--bucket",
        help="Name of the bucket to use; defaults to the Location Labs convention",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Skip the deploy step",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Skip the waitstep",
    )
    parser.add_argument(
        "--socket-timeout",
        type=float,
        default=2.0,
        help="Set the client socket timeouts",
    )
    parser.add_argument(
        "--sleep-timeout",
        type=float,
        default=1.0,
        help="Set the poll loop's sleep timeout",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=1,
    )

    args = parser.parse_args()

    if not args.description and not args.deployment_id:
        parser.error("One of --description or --deployment-id is required.")

    if not args.profile:
        parser.error("One of --profile or AWS_PROFILE is required.")

    if args.bucket is None:
        # LocationLabs buckets should be named "locationlabs-<silo>-<type>-deploy"
        args.bucket = "locationlabs-{}-deploy".format("-".join(args.profile.split("-")[0:2]))

    return args


def initialize_logging(verbosity):
    """
    Set logging verbosity.
    """
    level = ["WARN", "INFO", "DEBUG"][min(verbosity, 2)]
    basicConfig(level=level, format="%(message)s")
    getLogger("botocore").setLevel("DEBUG" if level == "DEBUG" else "WARN")


def main():
    """
    CLI entry point.
    """
    args = parse_args()
    initialize_logging(args.verbose)
    logger = getLogger("cli")

    revision = Revision()

    try:
        profile = get_profile(profile=args.profile)

        client = profile.create_client("codedeploy", config=Config(
            connect_timeout=args.socket_timeout,
            read_timeout=args.socket_timeout,
        ))

        if not args.deployment_id:
            etag = push(profile, args, revision)
        else:
            etag = None

        if not args.no_deploy and etag:
            args.deployment_id = deploy(profile, client, args, etag)

        if not args.no_wait and args.deployment_id:
            wait_for_deploy(client, args)

        return 0
    except ClientError as error:
        logger.error(error)
        return 1
