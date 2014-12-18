from harpoon.option_spec.image_objs import Link, Command, Mount, Environment, Port, ContainerPort
from harpoon.option_spec.specs import many_item_formatted_spec
from harpoon.formatter import MergedOptionStringFormatter

from input_algorithms.spec_base import string_spec, integer_spec, required, Spec, NotSpecified, string_or_int_as_string_spec

class command_spec(Spec):
    def normalise(self, meta, command):
        return Command(meta, command)

class mount_spec(many_item_formatted_spec):
    value_name = "Volume mounting"
    specs = [string_spec, string_spec]
    optional_specs = [string_spec]
    formatter = MergedOptionStringFormatter

    def create_result(self, local_path, container_path, permissions, meta, val, dividers):
        if permissions is NotSpecified:
            permissions = 'rw'
        return Mount(local_path, container_path, permissions)

class env_spec(many_item_formatted_spec):
    value_name = "Environment Variable"
    seperators = [':', '=']

    specs = [string_spec()]
    optional_specs = [string_or_int_as_string_spec()]
    formatter = MergedOptionStringFormatter

    def create_result(self, env_name, other_val, meta, val, dividers):
        args = [env_name]
        if dividers[0] == ':':
            args.append(other_val)
        elif dividers[0] == '=':
            args.extend([None, other_val])
        return Environment(*args)

class link_spec(many_item_formatted_spec):
    value_name = "Container link"
    specs = [string_spec]
    optional_specs = [string_spec]
    formatter = MergedOptionStringFormatter

    def determine_2(self, container_name, meta, val):
        if not isinstance(container_name, basestring):
            container_name = container_name.container_name
        return container_name[container_name.rfind(":")+1:].replace('/', '-')

    def alter_1(self, container_name, meta, val):
        meta.container = None
        if not isinstance(container_name, basestring):
            meta.container = container_name
            container_name = container_name.container_name
        return container_name

    def create_result(self, container_name, link_name, meta, val, dividers):
        return Link(meta.container, container_name, link_name)

class port_spec(many_item_formatted_spec):
    value_name = "Ports"
    specs = [string_spec]
    optional_specs = [string_spec, string_spec]
    formatter = MergedOptionStringFormatter

    def create_result(self, ip, host_port, container_port, meta, val, dividers):
        if host_port in ('', NotSpecified) and container_port in ('', NotSpecified):
            container_port = ip
            ip = NotSpecified
            host_port = NotSpecified
        elif container_port in ('', NotSpecified):
            container_port = host_port
            host_port = ip
            ip = NotSpecified
        elif host_port in ('', NotSpecified):
            host_port = NotSpecified

        if host_port == '':
            host_port = NotSpecified
        if container_port == '':
            container_port = NotSpecified

        if host_port is not NotSpecified:
            host_port = integer_spec().normalise(meta.indexed_at('host_port'), host_port)
        container_port = required(container_port_spec()).normalise(meta.indexed_at('container_port'), container_port)

        return Port(ip, host_port, container_port)

class container_port_spec(many_item_formatted_spec):
    value_name = "Container port"
    specs = [integer_spec]
    optional_specs = [string_spec]
    formatter = MergedOptionStringFormatter
    seperators = ['/']

    def create_result(self, port, transport, meta, val, dividiers):
        return ContainerPort(port, transport)

