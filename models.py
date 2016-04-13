import math
import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    games = ndb.IntegerProperty(default=0)
    score = ndb.IntegerProperty(default=0)

    def to_form(self):
        return UserForm(name=self.name,
                        email=self.email,
                        games=self.games,
                        score=self.score)

    def add_match(self, game_size):
        """Adds the points for the match to the lifetime total"""
        points = int(math.pow(game_size, 2))
        self.score += points
        self.put()
        return points

    def add_game(self):
        """Adds a completed game to the lifetime total"""
        self.games += 1
        self.put()

    def remove_points(self, points):
        """Removes points previously scored during a now cancelled game."""
        self.score - points
        self.put()


class GameState:
    """Enumeration for the status of a game."""
    Active, Completed, Cancelled = range(3)


class Game(ndb.Model):
    """Game object"""
    board = ndb.PickleProperty(required=True)
    status = ndb.IntegerProperty(default=GameState.Active)
    user = ndb.KeyProperty(kind='User')
    score = ndb.IntegerProperty(default=0)
    history = ndb.PickleProperty(required=True)
    size = ndb.IntegerProperty(default=4)

    @classmethod
    def new_game(cls, size, user):
        """Creates and returns a new game"""
        game = Game(status=GameState.Active,
                    user=user,
                    score=0,
                    size=size)

        # Structure the Game as a child of its User creator
        game_id = Game.allocate_ids(size=1, parent=user)[0]
        game.key = ndb.Key(Game, game_id, parent=user)

        # Setup the board
        board = []
        values = [i for i in range(size)]

        # Copy and append the list to itself: each card value gets a match
        values.extend(values)

        # Shuffle the card order
        random.shuffle(values)

        # Create the card objects and add to the board
        for value in values:
            # Card: Each card (named by int) has a match in the deck
            # Cleared: indicates if the card's still on the board (unmatched)
            card = {}
            card["value"] = value
            card["cleared"] = False
            board.append(card)
        game.board = board
        game.history = []
        game.put()
        return game

    def to_form(self, hide_solution=True, card1=None, card2=None):
        """Returns a GameForm representation of the Game."""
        board = self.board
        # Don't expose the card values if this is an active game
        if hide_solution:
            board = list(self.board)
            index = 0
            for card in board:
                # Only show the values of the chosen cards if a move is being made
                if card1 != index and card2 != index:
                    card.pop("value")
                index += 1

        # Report the status as a string
        strings = ["active", "completed", "cancelled"]
        status = strings[self.status]

        form = GameForm(urlsafe_key=self.key.urlsafe(),
                        board=str(board),
                        status=status,
                        score=self.score)
        return form

    def tally_match(self):
        """Adds the points for the new match to the player's lifetime total."""
        points = self.user.get().add_match(self.size)
        self.score += points

    def end_game(self):
        """Ends the game."""
        self.status = GameState.Completed
        self.put()
        score = Score(date=date.today(), size=self.size, user=self.user, game=self.key)

        # Structure the Score as a child the Game to which it represents
        score_id = Score.allocate_ids(size=1, parent=self.key)[0]
        score.key = ndb.Key(Score, score_id, parent=self.key)

        score.put()

        # Update the user models
        self.user.get().add_game()

    def cancel_game(self):
        """Cancels the game."""
        self.status = GameState.Cancelled
        self.put()
        # Previous points for this game are recalled
        self.user.get().remove_points(self.score)


class Score(ndb.Model):
    """Score object"""
    date = ndb.DateProperty(required=True)
    size = ndb.IntegerProperty(required=True)
    user = ndb.KeyProperty(kind='User')
    game = ndb.KeyProperty(kind='Game')

    def to_form(self):
        return ScoreForm(date=str(self.date),
                         size=int(math.pow(self.size, 2)),
                         user=self.user.get().name,
                         game=self.game.urlsafe())


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    status = messages.StringField(2, required=True)
    score = messages.IntegerField(3, required=True)
    board = messages.StringField(4, required=True)


class GameForms(messages.Message):
    """Container for multiple GameForm"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    size = messages.IntegerField(1, required=True)
    user = messages.StringField(2, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    card1 = messages.IntegerField(1, required=True)
    card2 = messages.IntegerField(2, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    date = messages.StringField(1, required=True)
    size = messages.IntegerField(2, required=True)
    user = messages.StringField(3, required=True)
    game = messages.StringField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class UserForm(messages.Message):
    """User Form"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2, required=True)
    games = messages.IntegerField(3, required=True)
    score = messages.IntegerField(4, required=True)


class UserForms(messages.Message):
    """Container for multiple User Forms"""
    items = messages.MessageField(UserForm, 1, repeated=True)
