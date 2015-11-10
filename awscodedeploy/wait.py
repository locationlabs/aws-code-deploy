"""
Watch deployment.
"""
from logging import getLogger
from time import sleep

from botocore.exceptions import ClientError
from termcolor import colored


def wait_for_deploy(client, args):
    """
    Wait for a deployment and update the console.

    Refactor me!
    """
    logger = getLogger("wait")

    done = False
    status = None
    overview = None
    instance_statuses = dict()
    seen = dict()

    while not done:
        sleep(args.sleep_timeout)

        deployment = client.get_deployment(**{
            "deploymentId": args.deployment_id,
        })
        overview = deployment["deploymentInfo"].get("deploymentOverview")
        new_status = deployment["deploymentInfo"]["status"]

        if overview and instance_statuses:
            finished_instances = overview["Failed"] + overview["Succeeded"] + overview["Skipped"]
            total_instances = len(instance_statuses)
            done = finished_instances >= total_instances

        # print overview if changed
        if new_status != status:
            status = new_status
            logger.info("[{}]: Deployment status is now: {}".format(
                colored(args.deployment_id, "cyan"),
                colored(status, "red" if status == "Failed" else "green"),
            ))
            if overview:
                logger.info("[{}]: Failed: {} InProgress: {} Skipped: {} Succedeed: {} Pending: {}".format(  # noqa
                    colored(args.deployment_id, "cyan"),
                    colored(overview["Failed"], "red"),
                    colored(overview["InProgress"], "green"),
                    colored(overview["Skipped"], "green"),
                    colored(overview["Succeeded"], "green"),
                    colored(overview["Pending"], "green"),
                ))

        try:
            instances = client.list_deployment_instances(**{
                "deploymentId": args.deployment_id,
            })
        except ClientError as error:
            if "hasn't completed adding instances" in error.message:
                continue
            raise
        for instance_id in instances["instancesList"]:
            seen.setdefault(instance_id, set())
            deployment_instance = client.get_deployment_instance(**{
                "deploymentId": args.deployment_id,
                "instanceId": instance_id,
            })
            instance_status = deployment_instance["instanceSummary"]["status"]

            # print instance if changed
            if instance_statuses.get(instance_id) != instance_status:
                instance_statuses[instance_id] = instance_status
                logger.info("[{}]: Instance status is now: {}".format(
                    colored(instance_id, "cyan"),
                    colored(instance_status, "red" if instance_status == "Failed" else "green"),
                ))

            for event in deployment_instance["instanceSummary"]["lifecycleEvents"]:
                if event["lifecycleEventName"] not in seen[instance_id]:
                    seen[instance_id].add(event["lifecycleEventName"])
                    # print log tail for new events; seems to only appear on errors?
                    if "diagnostics" in event:
                        log_tail = event["diagnostics"]["logTail"].strip()
                        if log_tail:
                            logger.info("[{}]: Instance log: \n{}".format(
                                colored(instance_id, "cyan"),
                                log_tail,
                            ))
