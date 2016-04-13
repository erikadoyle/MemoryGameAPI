import logging
from google.appengine.ext import ndb
import endpoints


def get_by_urlsafe(urlsafe, model):
    """Returns an ndb.Model entity corresponding to the urlsafe key. Checks
        that the type of entity returned is of the correct kind. Raises an
        error if the key String is malformed or the entity is of the incorrect
        kind.
    Args:
        urlsafe: A urlsafe key string
        model: The expected entity kind
    Returns:
        The entity corresponding to the urlsafe key or None if no entity
        exists.
    Raises:
        ValueError if kind is incorrect
    """
    try:
        key = ndb.Key(urlsafe=urlsafe)
    except TypeError:
        raise endpoints.BadRequestException('Invalid Key')
    except Exception, e:
        if e.__class__.__name__ == 'ProtocolBufferDecodeError':
            raise endpoints.BadRequestException('Invalid Key')
        else:
            raise

    entity = key.get()
    if not entity:
        return None
    if not isinstance(entity, model):
        raise ValueError('Incorrect Kind')
    return entity


def check_complete(board):
    """Checks the board. If all matches have been found, returns True."""
    for card in board:
        if not card["cleared"]:
            return False
    return True
