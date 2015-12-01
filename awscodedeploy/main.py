#!/usr/bin/env python
from argparse import ArgumentParser, FileType
from getpass import getuser
from logging import basicConfig, getLogger
from os import environ

from awsenv.main import get_profile
from botocore.client import Config
from botocore.exceptions import ClientError

from awscodedeploy.deploy import push, deploy
from awscodedeploy.revision import HelloWorldRevision, DockerComposeRevision
from awscodedeploy.wait import FailedDeploymentException, wait_for_deploy


def parse_args():
    """
    Parse arguments.
    """
    parser = ArgumentParser()
    parser.add_argument(
        "--application-name",
        "-a",
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
        "-d",
        required=True,
        help="CodeDeploy deployment name",
    )
    parser.add_argument(
        "--description",
        required=False,
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
        "--etag",
        help="Etag of the revision to use",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hello-world", action="store_true")
    group.add_argument("--docker-compose", type=FileType("r"))

    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Skip the push step",
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
        "--step-timeout",
        type=int,
        default=300,
        help="Set the timeout for each step (ApplicationStop, Install, etc)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=1,
    )

    args = parser.parse_args()

    if not args.description:
        args.description = "Deployed by {} via aws-code-deploy".format(
            getuser(),
        )

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


def choose_revision(args):
    if args.hello_world:
        return HelloWorldRevision()
    if args.docker_compose:
        return DockerComposeRevision(
            deployment_name=args.deployment_name,
            compose_file=args.docker_compose,
            timeout=args.step_timeout,
        )
    raise Exception("Unsupported revision")


def main():
    """
    CLI entry point.
    """
    args = parse_args()
    initialize_logging(args.verbose)
    logger = getLogger("cli")

    revision = choose_revision(args)
    try:
        profile = get_profile(profile=args.profile)

        client = profile.create_client("codedeploy", config=Config(
            connect_timeout=args.socket_timeout,
            read_timeout=args.socket_timeout,
        ))

        # push the revision to S3
        if not args.no_push and not args.deployment_id:
            args.etag = push(profile, args, revision)

        # deploy from the revision
        if not args.no_deploy and args.etag:
            args.deployment_id = deploy(profile, client, args)

        # wait for the deploy to finish
        if not args.no_wait and args.deployment_id:
            wait_for_deploy(client, args)

        return 0
    except (ClientError, FailedDeploymentException) as error:
        logger.error(error)
        return 1
