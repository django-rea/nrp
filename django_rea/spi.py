from django.db.models import Model
from django.db.models.base import ModelBase
from django.utils import six


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
    """
    A class mapping registry.
    """

    mapping = {}

    @classmethod
    def register_implementation(cls, interface, implementation, replace=False):
        """
        Registers an implementation as a mapping.
        :param interface:
        :param implementation:
        :param replace:
        :return:
        """
        if interface in cls.mapping and not replace:
            raise ValueError(
                "The interface {0} is already mapped to {1}".format(
                    interface,
                    cls.mapping[interface])
            )
        cls.mapping[interface] = implementation

    @classmethod
    def get_implementation(cls, interface):
        return cls.mapping[interface]


class ModelProviderMeta(ModelBase):
    def __init__(cls, what, bases=None, dict=None):
        super(ModelProviderMeta, cls).__init__(what, bases, dict)
        ModelProvider.register_implementation(cls, cls, replace=True)
