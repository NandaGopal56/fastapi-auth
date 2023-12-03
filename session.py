from utils import get_random_string

class SessionBase:
    '''
    Base class for sesison implementation
    '''

    def __init__(self, session_key=None) -> None:
        self._session_key = session_key
        self.accessed = False
        self.modified = False

    def __contains__(self, key):
        return key in self._session
    
    def __getitem__(self, key):
        return self._session[key]
    
    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True
    
    @property
    def key_salt(self):
        return "session_key_salt" + self.__class__.__qualname__
    
    def get(self, key, default=None):
        return self._session.get(key, default)
    
    def pop(self, key, default=None):
        self.modified = self.modified or key in self._session
        args = () if default is None else (default, )
        return self._session.pop(key, *args)
    
    def setdefault(self, key, value):
        if key in self._session:
            return self._session[key]
        else:
            self.modified = True
            self._session[key] = value
            return value
        
    def encode(self, session_dict):
        # TODO: implement actual encoding with salt, serializer etc.
        return session_dict
    
    def decode(self, session_data):
        # TODO: return actual decoded session data after accepting the encrypted signing data
        # raise exception in case of bad signature or any other exception etc and retrun empty dictionary
        return session_data
    
    def update(self, dict_):
        self._session.update(dict_)
        self.modified = True
    
    def has_key(self, key):
        return key in self._session

    def keys(self):
        return self._session.keys()
    
    def values(self):
        return self._session.values()
    
    def items(self):
        return self._session.items()
    
    def clear(self):
        '''
        To avoid unnecessary persistent storage access, we set up the internals directly 
        (loading data wastes time, since we are going to set it to an empty dict anyway)
        '''    
        self._session_cache = {}
        self.accessed = True
        self.modified = True

    def is_empty(self):
        '''
        return True when there is no session_key and the session is empty
        '''    
        try:
            return not self._session_key and not self._session_cache
        except AttributeError:
            return True
    
    def _get_new_session_key(self):
        "Return session key that is not being used."
        while True:
            session_key = get_random_string(32)
            if not self.exists(session_key):
                return session_key

    def _get_or_create_session_key(self):
        if self._session_key is None:
            self._session_key = self._get_new_session_key()
        return self._session_key

    def _validate_session_key(self, key):
        """
        Key must be truthy and at least 8 characters long. 8 characters is an
        arbitrary lower bound for some minimal key security.
        """
        return key and len(key) >= 8

    def _get_session_key(self):
        return self.__session_key

    def _set_session_key(self, value):
        """
        Validate session key on assignment. Invalid values will set to None.
        """
        if self._validate_session_key(value):
            self.__session_key = value
        else:
            self.__session_key = None


    # Methods that the child class needs to implement

    def exists(self, session_key):
        '''
        Return True if the given session_key already exists
        '''
        raise NotImplementedError(
            "Subclasses of SessionBase must provide an exists() method"
        )
    
    def create(self):
        '''
        Create a new session instance. Guaranteed to create a new object with a unique key and will ahve saved the result once (with empty data)
        befre the method return
        '''
        raise NotImplementedError(
            "Subclasses of SessionBase must provide an create() method"
        )

    def save(self, must_create=False):
        '''
        save the session data. if 'must_create' is true, create a new session object (or raise CreateError).
        Otherwise only update an existing objet and dont create one (raise UpdateError if needed).
        '''
        raise NotImplementedError(
            "Subclasses of SessionBase must provide an save() method"
        )
        
    def delete(self, session_key=None):
        '''
        Delete the session data under this key. If the key is None, use the current session key value
        '''
        raise NotImplementedError(
            "Subclasses of SessionBase must provide an delete() method"
        )

    def load(self):
        '''
        Load the session data and return a dictionary
        '''
        raise NotImplementedError(
            "Subclasses of SessionBase must provide an load() method"
        )
        
    @classmethod
    def clear_expired(cls):
        """
        Remove expired sessions from the session store.

        If this operation isn't possible on a given backend, it should raise
        NotImplementedError. If it isn't necessary, because the backend has
        a built-in expiration mechanism, it should be a no-op.
        """
        raise NotImplementedError("This backend does not support clear_expired().")