"""
Watch deployment.
"""
from logging import getLogger
from time import sleep

from botocore.exceptions import ClientError
from termcolor import colored


class FailedDeploymentException(Exception):
    pass


def get_deployment(client, args):
    deployment = client.get_deployment(**{
        "deploymentId": args.deployment_id,
    })
    status = deployment["deploymentInfo"]["status"]
    overview = deployment["deploymentInfo"].get("deploymentOverview")
    return status, overview


def get_instance_ids(client, args):
    try:
        return client.list_deployment_instances(**{
            "deploymentId": args.deployment_id,
        })["instancesList"]
    except ClientError as error:
        if "hasn't completed adding instances" in error.message:
            return []
        raise


def get_instance_data(client, args, instance_id):
    deployment_instance = client.get_deployment_instance(**{
        "deploymentId": args.deployment_id,
        "instanceId": instance_id,
    })
    instance_status = deployment_instance["instanceSummary"]["status"]
    instance_events = deployment_instance["instanceSummary"]["lifecycleEvents"]
    return instance_status, instance_events


def print_status(args, status):
    logger = getLogger("wait")
    logger.info("[{}]: Deployment status is now: {}".format(
        colored(args.deployment_id, "cyan"),
        colored(status, "red" if status == "Failed" else "green"),
    ))


def print_overview(args, overview):
    if not overview:
        return
    logger = getLogger("wait")
    logger.info("[{}]: Failed: {} InProgress: {} Skipped: {} Succedeed: {} Pending: {}".format(  # noqa
        colored(args.deployment_id, "cyan"),
        colored(overview["Failed"], "red"),
        colored(overview["InProgress"], "green"),
        colored(overview["Skipped"], "green"),
        colored(overview["Succeeded"], "green"),
        colored(overview["Pending"], "green"),
    ))


def print_instance_status(args, instance_id, instance_status):
    logger = getLogger("wait")
    logger.info("[{}]: Instance status is now: {}".format(
        colored(instance_id, "cyan"),
        colored(instance_status, "red" if instance_status == "Failed" else "green"),
    ))


def print_instance_event(args, instance_id, instance_event):
    # print log tail for new events; seems to only appear on errors?
    if "diagnostics" not in instance_event:
        return

    log_tail = instance_event["diagnostics"]["logTail"].strip()
    if not log_tail:
        return

    logger = getLogger("wait")
    logger.info("[{}]: Instance log: \n{}".format(
        colored(instance_id, "cyan"),
        log_tail,
    ))


def is_done(overview, instance_statuses):
    if not overview or not instance_statuses:
        return False

    finished_instances = overview["Failed"] + overview["Succeeded"] + overview["Skipped"]
    total_instances = len(instance_statuses)
    return finished_instances >= total_instances


def wait_for_deploy(client, args):
    """
    Wait for a deployment and update the console.

    Refactor me!
    """
    last_status = None
    overview = None
    instance_statuses = dict()
    instances_seen = dict()

    while not is_done(overview, instance_statuses):

        # sleep first; the deploy won't be ready immediately anyway
        sleep(args.sleep_timeout)

        # fetch the deployment and print changes
        new_status, overview = get_deployment(client, args)

        if new_status != last_status:
            last_status = new_status
            print_status(args, new_status)
            print_overview(args, overview)

        # fetch each instance and print changes
        for instance_id in get_instance_ids(client, args):
            instance_status, instance_events = get_instance_data(client, args, instance_id)

            instances_seen.setdefault(instance_id, set())

            if instance_statuses.get(instance_id) != instance_status:
                instance_statuses[instance_id] = instance_status
                print_instance_status(args, instance_id, instance_status)

            for instance_event in instance_events:
                # event log data isn't showing up; it only appears to show up on errors
                # and probably doesn't appear when the event is first seen
                if instance_event["lifecycleEventName"] not in instances_seen[instance_id]:
                    instances_seen[instance_id].add(instance_event["lifecycleEventName"])
                    print_instance_event(args, instance_id, instance_event)

    if overview["Failed"]:
        raise FailedDeploymentException
