import abc


class Store:

    @abc.abstractmethod
    def put(self, key, value, overwrite):
        """Stores the value under the specified key.
        If key exists and overwrite is False, key is not updated.
        Returns True is key is updated, False otherwise.
        """
        pass

    @abc.abstractmethod
    def get(self, key):
        """Returns the key value.
        Throws error if key does not exist.
        """
        pass

    @abc.abstractmethod
    def append(self, key, value):
        """Appends the given value to the key value.
        Returns the updated key value or throws error if key does not exist.
        """
        pass

    @abc.abstractmethod
    def remove(self, key):
        """Removes and returns the given key.
        Throws error if key does not exist.
        """
        pass