import functools

class cache():

    def __init__(self):
        self.cache = {}
        self.n_levels = 10

    def add(self, level, row):
        self.cache[level] = row

    def get(self, level):
        return self.cache.get(level)

    def clear(self):
        self.cache = {}

    @functools.lru_cache(maxsize=128)
    def get_parent_of(self, level, row):
        parent = level - 1
        self.add(level, row)
        if parent in range(0, self.n_levels):
            return self.cache[parent]
