"""
Revision object model.
"""
from abc import ABCMeta, abstractproperty
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp
from textwrap import dedent
from os import mkdir
from os.path import basename, dirname, join

from yaml import dump, load


APPLICATION_START = "ApplicationStart"
APPLICATION_STOP = "ApplicationStop"
AFTER_INSTALL = "AfterInstall"
BEFORE_INSTALL = "BeforeInstall"

EVENTS = [
    APPLICATION_START,
    APPLICATION_STOP,
    AFTER_INSTALL,
    BEFORE_INSTALL,
]


class Hook(object):
    """
    Generic script hook.

    Defines an event (e.g. ApplicationStart), a script name, and the script
    content to run. Timeouts and users can be configured as well.
    """
    def __init__(self, event, name, content, timeout=300, user="root"):
        self.event = event
        self.name = name
        self.content = content
        self.timeout = timeout
        self.user = user

    def to_appspec_dict(self):
        return dict(
            location="scripts/{}".format(self.name),
            timeout=self.timeout,
            runas=self.user,
        )

    def write(self, revision_dir):
        """
        Write the script to the revision dir.
        """
        with open(join(revision_dir, "scripts/{}".format(self.name)), "w") as file_:
            file_.write(self.content)


class Revision(object):
    """
    Generic revision.

    Should be extended.
    """
    __metaclass__ = ABCMeta

    @abstractproperty
    def hooks(self):
        """
        Return a list of script hooks.
        """
        pass

    @abstractproperty
    def files(self):
        """
        Return a mapping from destination path to file content.
        """
        pass

    def to_appspec_dict(self):
        return dict(
            version=0.0,
            os="linux",
            hooks={
                event: [
                    hook.to_appspec_dict() for hook in self.hooks
                    if hook.event == event
                ] for event in EVENTS
            },
            files=[
                dict(
                    source="files/{}".format(basename(name)),
                    destination=dirname(name),
                ) for name in self.files
            ],
        )

    def write(self, revision_dir):
        """
        Write out the revision bundle.
        """
        # write appspec.yml
        with open(join(revision_dir, "appspec.yml"), "w") as file_:
            file_.write(dump(self.to_appspec_dict()))

        # write hook scripts
        for hook in self.hooks:
            hook.write(revision_dir)

        # write files
        for name, content in self.files.items():
            with open(join(revision_dir, "files", basename(name)), "w") as dest:
                dest.write(content)

    @contextmanager
    def make(self):
        """
        Create this revision in a temporary directory.
        """
        try:
            revision_dir = mkdtemp()
            mkdir(join(revision_dir, "scripts"))
            mkdir(join(revision_dir, "files"))
            self.write(revision_dir)
            yield revision_dir
        finally:
            rmtree(revision_dir)


class HelloWorldRevision(Revision):
    """
    Test revision. Just echoes "hello world"
    """
    @property
    def hooks(self):
        return [
            Hook(
                event=AFTER_INSTALL,
                name="echo_hello_world",
                content=dedent("""\
                #!/bin/bash

                echo hello world
                """),
            ),
        ]

    @property
    def files(self):
        return {}


class DockerComposeRevision(Revision):
    """
    Revision that uses Docker Compose. Currently only supports compose files
    with a single service.
    """
    def __init__(self, deployment_name, compose_file, timeout):
        self.deployment_name = deployment_name
        self.compose_data = load(compose_file)
        self.timeout = timeout

        # validate compose data has only 1 service.
        if len(self.compose_data) != 1:
            raise Exception(
                "DockerComposeRevision only supports compose files with a single service"
            )

    @property
    def images(self):
        """
        Extract the set of docker images from the compose data.
        """
        return set([
            container["image"]
            for name, container in self.compose_data.items()
            if "image" in container
        ])

    @property
    def services(self):
        """
        Return the list of services from the compose data.
        """
        return [name for name, _ in self.compose_data.items()]

    @property
    def hooks(self):
        """
        Defines three hooks:
         - Stops application using docker compose.
         - Before installation, pulls images.
         - Starts application using docker compose.
        """
        return [
            Hook(
                event=APPLICATION_STOP,
                name="stop_and_remove",
                content="\n".join([
                    "#!/bin/bash",
                    ""
                    "mkdir -p /etc/docker-compose/{}".format(self.deployment_name),
                    "cd /etc/docker-compose/{}".format(self.deployment_name),
                    "test -r docker-compose.yml && docker-compose stop || /bin/true",
                    "test -r docker-compose.yml && docker-compose rm -f || /bin/true",
                    "",
                ]),
                timeout=self.timeout,
            ),
            Hook(
                event=BEFORE_INSTALL,
                name="pull_images",
                content="\n".join([
                    "#!/bin/bash",
                    "",
                    "mkdir -p /etc/docker-compose/{}".format(self.deployment_name),
                    ""
                ] + [
                    "docker pull {}".format(image)
                    for image in self.images
                ] + [
                    "",
                ]),
                timeout=self.timeout,
            ),
            Hook(
                event=APPLICATION_START,
                name="docker-compose",
                content=dedent("""\
                #!/bin/bash

                cd /etc/docker-compose/{}
                docker-compose run --rm {}
                """.format(self.deployment_name,
                           self.services[0])),
                timeout=self.timeout,
            ),
        ]

    @property
    def files(self):
        """
        Copy compose data into appropriate directory.
        """
        destination = "/etc/docker-compose/{}/docker-compose.yml".format(
            self.deployment_name,
        )
        return {
            destination: dump(self.compose_data)
        }
