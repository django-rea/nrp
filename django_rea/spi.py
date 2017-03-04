class PluginMount(type):
    """
    Plugin mount is a metaclass based on the ideas of http://martyalchin.com/2008/jan/10/simple-plugin-framework/
    """

    def __init__(cls, name, bases, attrs):
        super(PluginMount, cls).__init__(name, bases, attrs)
        if not hasattr(cls, 'plugins'):
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            cls.plugins = []
            cls.mapping = {}
        else:
            # This must be a plugin implementation, which should be registered.
            # Simply appending it to the list is all that's needed to keep
            # track of it later.
            cls.plugins.append(cls)


class ModelProvider:
    __metaclass__ = PluginMount

    @classmethod
    def register_implementation(cls, interface, implementation):
        instance = _ModelImplementation(interface, implementation)
        if instance.interface in cls.mapping:
            raise ValueError(
                "The interface {0} is already mapped to {1}".format(
                    instance.interface,
                    cls.mapping[instance.interface])
            )
        cls.mapping[instance.interface] = instance.implementation

    @classmethod
    def get_implementation(cls, interface):
        return cls.mapping[interface]


class _ModelImplementation(ModelProvider):
    def __init__(self, interface, implementation):
        self.interface = interface
        self.implementation = implementation
