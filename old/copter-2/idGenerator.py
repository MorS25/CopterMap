from multiprocessing import Lock

__author__ = 'root'
class IdGenerator:
    class __generator:
        def __init__(self):
            self.lock = Lock()
            self.lastId = 0

        def getId(self):
            self.lock.acquire()
            self.lastId += 1
            self.lock.release()
            return self.lastId

    instance = None

    def __init__(self):
        if not IdGenerator.instance:
            IdGenerator.instance = IdGenerator.__generator()

    def __getattr__(self, item):
        return getattr(self.instance, item)
