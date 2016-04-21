import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.ext import ndb

from models import User, Game, Score, GameState
from models import StringMessage, NewGameForm, GameForm, MakeMoveForm,\
    ScoreForms, GameForms, UserForm, UserForms
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
GET_HIGH_SCORES_REQUEST = endpoints.ResourceContainer(
        results=messages.IntegerField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
NEW_USER_REQUEST = endpoints.ResourceContainer(
    user_name=messages.StringField(1), email=messages.StringField(2))
USER_REQUEST = endpoints.ResourceContainer(
        user_name=messages.StringField(1),)

MEMCACHE_AVG_SCORE = 'AVG_SCORE'


@endpoints.api(name='memory_game', version='v1')
class MemoryGameAPI(remote.Service):
    """Game API"""
    @endpoints.method(request_message=NEW_USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Creates a new player. Requires email and a unique username."""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'A Player with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.key = ndb.Key(User, user.name)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(response_message=UserForms,
                      path='user/ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns all players ranked by their cumulative points."""
        users = User.query(User.score > 0).fetch()
        users = sorted(users, key=lambda x: x.score, reverse=True)
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates a new game."""
        if request.size < 1:
            raise endpoints.BadRequestException(
                'Board size must be greater than zero.')
        elif request.size > 500:
            raise endpoints.BadRequestException(
                'Board size must be 500 or less.')
        user = User.query(User.name == request.user).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A player with that name does not exist!')
        game = Game.new_game(request.size, user.key)

        return game.to_form()

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Returns the specified game in its current state.
           Completed and cancelled games will show all cards revealed.
        """
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            hide_solution = True
            if game.status != GameState.Active:
                hide_solution = False
            return game.to_form(hide_solution)
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='user/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all player's past and current games, including cancelled."""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.BadRequestException('Player not found!')

        games = Game.query(ancestor=user.key)
        forms = []
        for game in games:
            hide_solution = True
            if game.status != GameState.Active:
                hide_solution = False
            game_form = game.to_form(hide_solution)
            forms.append(game_form)
        return GameForms(items=forms)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/cancel',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """Cancels a game. Only active games can be cancelled."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and (game.status is GameState.Active):
            game.cancel_game()
            return StringMessage(message='Cancelled the game with key: {}.'.
                                 format(request.urlsafe_game_key))
        elif game and (game.status is GameState.Completed):
            raise endpoints.BadRequestException('Game is already over!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns guessed card values and current board state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        if game.status is GameState.Completed:
            raise endpoints.NotFoundException('Game already over')

        card1, card2 = request.card1, request.card2
        try:
            game.make_move(card1, card2)
            return game.to_form(card1=card1, card2=card2)
        except ValueError as error:
            raise endpoints.BadRequestException(error.message)

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Returns the card guessing history of a game."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        return StringMessage(message=str(game.history))

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Returns scores from all completed games."""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=GET_HIGH_SCORES_REQUEST,
                      response_message=ScoreForms,
                      path='scores/highest',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """Ranks the top N games (player/score) in descending order. If 'N' is
           not specified, returns the top 3 game scores.
        """
        # Found this nifty pythonic idiom on Stack Overflow (http://tinyurl.com/n3nv8fl)
        results = request.results or 3
        scores = Score.query().order(-Score.size).fetch(results)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of the specified player's scores for completed games."""

        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'A player with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @staticmethod
    def _get_average_score():
        """Gets the cached average score."""
        return str(memcache.get(MEMCACHE_AVG_SCORE)) or 0

    @staticmethod
    def cache_average_score():
        """Populates memcache with the average score across all players."""
        users = User.query().fetch()
        if users:
            count = len(users)
            total_score = sum([user.score for user in users])
            average = float(total_score)/count
            memcache.set(MEMCACHE_AVG_SCORE, str(average))


api = endpoints.api_server([MemoryGameAPI])
