class SingletonMeta(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        """Control instance creation: only one instance is ever created."""
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance

    def __getattribute__(cls, name):
        # Always return actual attributes for internals (avoid recursion)
        if name.startswith('__') and name.endswith('__'):
            return super().__getattribute__(name)
        if name in ('_instance',):
            return super().__getattribute__(name)
        # Delegate to the instance
        instance = cls()
        return getattr(instance, name)

    def __setattr__(cls, name, value):
        if name.startswith('__') and name.endswith('__'):
            return super().__setattr__(name, value)
        if name in ('_instance',):
            return super().__setattr__(name, value)
        # Delegate attribute setting to the instance
        instance = cls()
        return setattr(instance, name, value)


class AppData(metaclass=SingletonMeta):
    """Singleton class that can be accessed anywhere without instantiation."""
    def __init__(self):
        # Initialize shared data only once
        self.data = {}  # Shared dictionary