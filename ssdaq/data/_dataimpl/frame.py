import struct
import numpy as np
from importlib import import_module
import pyarrow
import logging

class PyArrowSerializer:
    def __init__(self,obj):
        self.obj = obj

    def serialize(self):
        return pyarrow.serialize(self.obj).to_buffer()

    @classmethod
    def deserialize(cls,data):
        return pyarrow.deserialize(data)

def dynamic_import(abs_module_path, class_name):
    module_object = import_module(abs_module_path)

    target_class = getattr(module_object, class_name)

    return target_class


class Frame:
    def __init__(self):
        self._objects = {}
        self._cache = {}
        self._serialized = {}
        self._log = logging.getLogger(__name__)

    def add(self, key, obj):
        #add checks here to see if the object supports serialization
        self._objects[key] = obj

    def items(self):
        for k,v in self._objects.items():
            yield k,v

        for k,v in self._serialized.items():
            if k in self._objects:

                continue
            self._deserialized_obj(k)
            yield k, self._objects[k]

    def __setitem__(self,key,obj):
        self.add(key,obj)

    def __getitem__(self, key):
        if key not in self._objects and key in self._serialized:
            self._deserialized_obj(key)
        return self._objects[key]

    def get(self,key):
        """ Behaves like the dict version of `get`. Returns
            the object if it exiest in the frame. If not
            the return value is None.

        Args:
            key (str): the key string

        Returns:
            obj or None: the object stored at `key` or n
        """
        if key not in self._objects and key in self._serialized:
            self._deserialized_obj(key)
        return self._objects.get(key)

    def keys(self):
        """

        Returns:
            TYPE: Description
        """
        keys = set(list(self._objects.keys())+list(self._serialized.keys()))
        return iter(list(keys))

    def serialize(self)->bytes:
        """Serializes the frame to a bytestream

        Returns:
            bytes: serialized frame
        """
        data_stream = bytearray()
        index = []
        classes = []
        pos = 0
        for k, v in self.items():
            if isinstance(v, np.ndarray) or isinstance(v, tuple):
                v = PyArrowSerializer(v)
            classes.append(
                "{},{},{}\n".format(k, v.__class__.__name__, v.__class__.__module__)
            )
            d = v.serialize()
            pos += len(d)
            index.append(pos)
            data_stream.extend(d)
        n_obj = len(index)

        classes = "".join(classes)
        trailer = struct.pack(
            "<{}I{}s3I".format(n_obj, len(classes)),
            *index,
            classes.encode(),
            len(classes),
            n_obj,
            pos
        )
        data_stream.extend(trailer)
        return data_stream

    def _deserialized_obj(self,key):
        class_,data = self._serialized[key]
        if self._cache[class_] is not None:
            cls = self._cache[class_]
            try:
                self._objects[key] = cls.deserialize(data)
            except Exception as e:
                self._log.error("And error occured while deserializing object {} of type {}:\n{}".format(key,class_,e))
        else:
            # If we don't know how to deserialize the object we just expose
            # the raw byte stream
            self._objects[key] = data
    @classmethod
    def deserialize(cls,data_stream:bytes):
        inst = cls()
        inst.deserialize_m(data_stream)
        return inst
    def deserialize_m(self, data_stream:bytes):
        """Deserializes a frame from byte buffer

        Args:
            data_stream (bytes): byte buffer to be deserialized
        """
        l_cls, n_obj, indexpos = struct.unpack("<3I", data_stream[-12:])
        index = struct.unpack("<{}I{}s".format(n_obj, l_cls), data_stream[indexpos:-12])
        classes = index[n_obj:][0].decode()
        index = list(index[:n_obj])
        last_pos = 0
        for i, c in zip(index, classes.split("\n")):
            key, class_, module_ = c.split(",")

            if class_ not in self._cache.keys():
                try:
                    m = import_module(module_)
                    self._cache[class_] = getattr(m, class_)
                except AttributeError:
                    self._cache[class_] = None
                    self._log.warn(f"Failed to import class `{class_}` to deserialize object at key: `{key}`")
            self._serialized[key] = (class_,data_stream[last_pos:i])
            last_pos = i

    @classmethod
    def unpack(cls,data_stream:bytes):
        return cls.deserialize(data_stream)#frame

    def pack(self):
        return self.serialize()

    def __str__(self):
        s ="{\n"
        for k in set(list(self._objects.keys())+list(self._serialized.keys())):
            if k not in self._objects:
                class_,_ = self._serialized[k]
                obj_str = "**serialized data**"
            else:
                class_ = type(self._objects[k])
                obj_str = self._objects[k].__str__()
            s+=f"`{k}` <{class_}>: {obj_str},\n"
        s +="}"
        return s
    def __repr__(self):
        return self.__str__()


class FrameObject:
    def __init__(self, pack, unpack):
        self.pack = pack
        self.unpack = unpack

    def serialize(self):
        return self.pack()
    # @classmethod
    def deserialize(self, data):
        return self.unpack(data)


#  @classmethod
#  def from_bytes(cls, data):
#      inst = cls()
#      inst.unpack(data)
#      return inst
