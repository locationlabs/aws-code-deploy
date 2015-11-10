"""
Revision object model.
"""
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp
from textwrap import dedent
from os import mkdir
from os.path import join

from yaml import dump


class Hook(object):
    def __init__(self, script, timeout=300, user="root"):
        self.script = script
        self.timeout = timeout
        self.user = user

    def to_dict(self):
        return dict(
            location="scripts/{}".format(self.script),
            timeout=self.timeout,
            runas=self.user,
        )


class Revision(object):

    @property
    def after_install(self):
        return []

    @property
    def application_stop(self):
        return []

    @property
    def application_start(self):
        return []

    @property
    def before_install(self):
        return [
            Hook("test"),
        ]

    def to_dict(self):
        return dict(
            version=0.0,
            os="linux",
            hooks={
                "ApplicationStart": [
                    hook.to_dict() for hook in self.application_start
                ],
                "ApplicationStop": [
                    hook.to_dict() for hook in self.application_stop
                ],
                "AfterInstall": [
                    hook.to_dict() for hook in self.after_install
                ],
                "BeforeInstall": [
                    hook.to_dict() for hook in self.before_install
                ],
            }
        )

    def to_yaml(self):
        return dump(self.to_dict())


def write_script(revision_dir, hook):
    with open(join(revision_dir, "scripts/{}".format(hook.script)), "w") as file_:
        file_.write(dedent("""\
              #!/bin/bash
              
              /bin/true
               """))


@contextmanager
def make_revision(revision):
    """
    Create a revision in a temporary directory.
    """
    try:
        revision_dir = mkdtemp()

        mkdir(join(revision_dir, "scripts"))

        with open(join(revision_dir, "appspec.yml"), "w") as file_:
            file_.write(revision.to_yaml())

        for hook in revision.application_start:
            write_script(revision_dir, hook)

        for hook in revision.application_stop:
            write_script(revision_dir, hook)

        for hook in revision.before_install:
            write_script(revision_dir, hook)

        for hook in revision.after_install:
            write_script(revision_dir, hook)

        yield revision_dir
    finally:
        rmtree(revision_dir)
