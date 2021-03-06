#coding: spec

from harpoon.executor import docker_context as docker_context_maker
from harpoon.option_spec.harpoon_specs import HarpoonSpec
from harpoon.ship.builder import Builder
from harpoon.ship.runner import Runner

from tests.helpers import HarpoonCase

from input_algorithms.meta import Meta
import codecs
import uuid
import six
import os

mtime = 1431170923

describe HarpoonCase, "Building docker images":
    def make_image(self, options, harpoon_options=None, image_name="awesome_image"):
        config_root = self.make_temp_dir()
        if harpoon_options is None:
            harpoon_options = {}
        harpoon_options["docker_context"] = self.docker_client
        harpoon_options["docker_context_maker"] = docker_context_maker
        harpoon = HarpoonSpec().harpoon_spec.normalise(Meta({}, []), harpoon_options)
        if "harpoon" not in options:
            options["harpoon"] = harpoon
        everything = {"harpoon": harpoon, "mtime": mtime, "_key_name_1": image_name, "config_root": config_root}
        return HarpoonSpec().image_spec.normalise(Meta(everything, []), options)

    it "Builds an image":
        ident = str(uuid.uuid1())
        ident_tag = "{0}:latest".format(ident)

        images = self.docker_client.images()
        repo_tags = [image["RepoTags"] for image in images]
        assert all(ident_tag not in repo_tag_list for repo_tag_list in repo_tags), images

        conf = self.make_image({"context": False, "commands": ["FROM {0}".format(os.environ["BASE_IMAGE"])]})
        conf.image_name = ident
        Builder().build_image(conf)

        images = self.docker_client.images()
        repo_tags = [image["RepoTags"] for image in images]
        assert any(ident_tag in repo_tag_list for repo_tag_list in repo_tags), "Couldn't find {0} in {1}".format(ident_tag, images)

        self.docker_client.remove_image(ident_tag)

    it "knows if the build was cached":
        from_line = "FROM {0}".format(os.environ["BASE_IMAGE"])
        commands1 = [from_line]
        commands2 = [from_line, "RUN echo {0}".format(uuid.uuid1())]
        commands3 = commands2 + [["ADD", {"content": "blah", "dest": "/tmp/blah", "mtime": mtime}]]
        with self.a_built_image({"context": False, "commands": commands1}) as (cached, conf1):
            assert cached

            with self.a_built_image({"context": False, "commands": commands2}) as (cached, conf2):
                assert not cached

                with self.a_built_image({"context": False, "commands": commands2}) as (cached, conf3):
                    assert cached

                    with self.a_built_image({"context": False, "commands": commands3}) as (cached, conf4):
                        assert not cached

    it "can steal files from other containers":
        from_line = "FROM {0}".format(os.environ["BASE_IMAGE"])

        commands1 = [
              from_line
            , "RUN mkdir /tmp/blah"
            , "RUN echo 'lol' > /tmp/blah/one"
            , "RUN echo 'hehehe' > /tmp/blah/two"
            , "RUN mkdir /tmp/blah/another"
            , "RUN echo 'hahahha' > /tmp/blah/another/three"
            , "RUN echo 'hello' > /tmp/other"
            ]

        conf1 = self.make_image({"context": False, "commands": commands1}, image_name="one")

        commands2 = [
              from_line

            , [ "ADD"
              , { "dest": "/tmp/copied"
                , "content":
                  { "image": conf1
                  , "path": "/tmp/blah"
                  }
                , "mtime": 1463473251
                }
              ]

            , [ "ADD"
              , { "dest": "/tmp/copied/other"
                , "content":
                  { "image": conf1
                  , "path": "/tmp/other"
                  }
                , "mtime": 1463473251
                }
              ]

            , "CMD find /tmp/copied -type f -exec echo {} \; -exec cat {} \;"
            ]

        fake_sys_stdout = self.make_temp_file()
        fake_sys_stderr = self.make_temp_file()
        harpoon_options = {"no_intervention": True, "stdout": fake_sys_stdout, "tty_stdout": fake_sys_stdout, "tty_stderr": fake_sys_stderr}
        with self.a_built_image({"context": False, "commands": commands2}, harpoon_options=harpoon_options, images={"one": conf1}, image_name="two") as (_, conf2):
            Runner().run_container(conf2, {"one": conf1, "two": conf2})

        with codecs.open(fake_sys_stdout.name) as fle:
            output = fle.read().strip()

        if isinstance(output, six.binary_type):
            output = output.decode('utf-8')
        output = '\n'.join([line for line in output.split('\n') if "lxc-start" not in line])

        expected = """
        Step 1 : .+
        .+
        Step 2 : .+
        .+
        Removing .+
        Step 3 : .+
        .+
        Removing .+
        Step 4 : .+
        .+
        .+
        Removing .+
        Successfully built .+
        /tmp/copied/other
        hello
        /tmp/copied/one
        lol
        /tmp/copied/another/three
        hahahha
        /tmp/copied/two
        hehehe
        """

        self.assertReMatchLines(expected, output)
