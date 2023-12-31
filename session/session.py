from session.utils import get_random_string
from datetime import datetime, timedelta, timezone
import json
from session.constants import Config

class CreateError(Exception):
    """
    Used internally as a consistent exception type to catch from save 
    (see the docstring for SessionBase.save() for details).
    """
    pass

class UpdateError(Exception):
    """
    Occurs if Django tries to update a session that was deleted.
    """
    pass


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
        return json.dumps(session_dict)
    
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

    session_key = property(_get_session_key)
    _session_key = property(_get_session_key, _set_session_key)

    def _get_session(self, no_load=False):
        """
        Lazily load session from storage (unless "no_load" is True, when only
        an empty dict is stored) and store it in the current instance.
        """
        self.accessed = True
        try:
            return self._session_cache
        except AttributeError:
            if self.session_key is None or no_load:
                self._session_cache = {}
            else:
                self._session_cache = self.load()
        return self._session_cache

    _session = property(_get_session)

    def get_session_cookie_age(self):
        return Config.SESSION_COOKIE_AGE

    def get_expiry_age(self, **kwargs):
        """Get the number of seconds until the session expires.

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs["modification"]
        except KeyError:
            modification = datetime.now()
        # Make the difference between "expiry=None passed in kwargs" and
        # "expiry not passed in kwargs", in order to guarantee not to trigger
        # self.load() when expiry is provided.
        try:
            expiry = kwargs["expiry"]
        except KeyError:
            expiry = self.get("_session_expiry")

        if not expiry:  # Checks both None and 0 cases
            return self.get_session_cookie_age()
        if not isinstance(expiry, (datetime, str)):
            return expiry
        if isinstance(expiry, str):
            expiry = datetime.fromisoformat(expiry)
        delta = expiry - modification
        return delta.days * 86400 + delta.seconds

    def get_expiry_date(self, **kwargs):
        """Get session the expiry date (as a datetime object).

        Optionally, this function accepts `modification` and `expiry` keyword
        arguments specifying the modification and expiry of the session.
        """
        try:
            modification = kwargs["modification"]
        except KeyError:
            modification = datetime.now()
        # Same comment as in get_expiry_age
        try:
            expiry = kwargs["expiry"]
        except KeyError:
            expiry = self.get("_session_expiry")

        if isinstance(expiry, datetime):
            return expiry
        elif isinstance(expiry, str):
            return datetime.fromisoformat(expiry)
        expiry = expiry or self.get_session_cookie_age()
        return modification + timedelta(seconds=expiry)

    def set_expiry(self, value):
        """
        Set a custom expiration for the session. ``value`` can be an integer,
        a Python ``datetime`` or ``timedelta`` object or ``None``.

        If ``value`` is an integer, the session will expire after that many
        seconds of inactivity. If set to ``0`` then the session will expire on
        browser close.

        If ``value`` is a ``datetime`` or ``timedelta`` object, the session
        will expire at that specific future time.

        If ``value`` is ``None``, the session uses the global session expiry
        policy.
        """
        if value is None:
            # Remove any custom expiration for this session.
            try:
                del self["_session_expiry"]
            except KeyError:
                pass
            return
        if isinstance(value, timedelta):
            value = datetime.now() + value
        if isinstance(value, datetime):
            value = value.isoformat()
        self["_session_expiry"] = value

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