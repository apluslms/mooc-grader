class MonitoredDict(dict):
    """
    A dict which records fields that have been accessed at least once
    """
    def __init__(self, *args, **kwargs):
        self.accessed = set()
        return super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        self.accessed.add(key)
        return super().__getitem__(key)

    def __repr__(self):
        super_ = super().__repr__()
        return 'MonitoredDict({})'.format(super_)
