import struct
from ssdaq import data
from importlib import import_module

# _index = struct.Struct()

def dynamic_import(abs_module_path, class_name):
    module_object = import_module(abs_module_path)

    target_class = getattr(module_object, class_name)

    return target_class

class Frame:
    def __init__(self):
        self._objects = {}
        self._cache = {}
    @classmethod
    def from_bytes(cls, data):
        inst = cls()
        inst.deserialize(data)
        return inst

    def add(self,key,obj):
        self._objects[key] = obj

    def items(self):
        return self._objects.items()
    def __getitem__(self, key):
        return self._objects[key]

    def keys(self):
        return self._objects.keys()

    def serialize(self):
        data_stream = bytearray()
        index = []
        classes = []
        pos = 0
        for k,v in self._objects.items():
            classes.append("{},{},{}\n".format(k,v.__class__.__name__,v.__class__.__module__))
            d = v.serialize()
            pos +=len(d)
            index.append(pos)
            data_stream.extend(d)
        n_obj = len(index)

        classes = "".join(classes)
        trailer = struct.pack("<{}I{}s3I".format(n_obj,len(classes)),*index,classes.encode(),len(classes),n_obj,pos)
        data_stream.extend(trailer)
        return data_stream

    def deserialize(self,data_stream):
        l_cls, n_obj,indexpos = struct.unpack("<3I",data_stream[-12:])
        index = struct.unpack("<{}I{}s".format(n_obj,l_cls),data_stream[indexpos:-12])
        classes = index[n_obj:][0].decode()
        index = list(index[:n_obj])
        last_pos = 0
        for i,c in zip(index,classes.split('\n')):
            key,class_,module_ = c.split(',')
            if class_ not in self._cache.keys():
                m = import_module(module_)
                self._cache[class_] = getattr(m,class_)

            cls = self._cache[class_]()
            # cls = dynamic_import(module_,class_)()
            cls.deserialize(data_stream[last_pos:i])
            self._objects[key] = cls
            last_pos = i

class FrameObject:
    def __init__(self,pack,unpack):
        self.pack = pack
        self.unpack = unpack

    def serialize(self):
        return self.pack()

    def deserialize(self,data):
        return self.unpack(data)





