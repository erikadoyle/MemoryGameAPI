# Memory Game API

Memory, or [Concentration](https://en.wikipedia.org/wiki/Concentration_(game)),
is a simple game consisting of a deck of card pairs. The cards are placed
face-down on the table, and the player inspects the card values, two at a time,
looking for matches. After each turn the cards are again placed face-down,
unless a pair is found, in which case the cards are cleared from the
table. The game objective is to find all card pairs in the fewest amount of turns.

This is a backend API for running single-player Memory games and tracking lifetime
scores and global averages across multiple registered players.

Each successful match results in points scored for the player. The amount of
points is calculated according to the size ( *number of matches* ) of the game,
where each match results in `size ^ 2` points added to the player's lifetime score.
If the game is cancelled, the previously scored points for it are recalled (subtracted)
from the player's lifetime score.

The card table (or *playing board*) is represented as a list of card objects,
where card positions correspond to indices of the list. Each card object has
the following properties:
```
{
    cleared: True / False
    value: [0 - # of matches specified upon game creation)
}
```
Upon each submission of a guess (`makeMove()`), the API will return the playing
board exposing the values of the two guessed cards and also the status
('cleared' value) of all the cards.

The API also records the history of the game, so that in-progress and
completed games can be re-created.

## Set-Up Instructions:
**Prerequisites**
- Create a new project using your Google developer account in the
[Google Cloud Platform console](https://console.cloud.google.com).
- Install the [Google App Engine SDK for Python](https://cloud.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).

1. Update the value of application in app.yaml to the app ID you have registered
 in the App Engine admin console and would like to use to host your instance of the game.
2. Run the app with the App Engine devserver dev_appserver.py DIR. To clear the
 local datastore for debugging purposes, use the `--clear_datastore=yes` command line switch.
3. You can verify the API service is running by going to the local server's address (by default localhost:8080).
To interact with the API directly:

- Launch Chrome with the following switches: `[path-to-Chrome] --user-data-dir=test --unsafely-treat-insecure-origin-as-secure=http://localhost:8080`
- Navigate to `http://localhost:8080/_ah/api/explorer`

## Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration.
 - main.py: Taskqueue and cronjob handlers.
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.

## Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will
    raise a ConflictException if a User with that user_name already exists.

 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: player, size
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game. 'size' of the game specifies the number
    of matching card pairs in the deck.

 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.

 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, card1, card2
    - Returns: GameForm with new game state (including values of the two specified cards)
    - Description: This is called specifying the two cards that the User wishes to reveal.
    If this causes a game to end, a corresponding Score entity will be created,
    unless the game is tied - in which case the game will be deleted.

 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).

 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms.
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.

 - **get_user_games**
    - Path: 'user/games'
    - Method: GET
    - Parameters: user_name
    - Returns: GameForms with 1 or more GameForm inside.
    - Description: Returns the current state of all the User's games (including active,
      cancelled, and completed games).

 - **cancel_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: DELETE
    - Parameters: urlsafe_game_key
    - Returns: StringMessage confirming deletion
    - Description: Deletes the game. If the game is already completed an error
    will be thrown.

 - **get_user_rankings**
    - Path: 'user/ranking'
    - Method: GET
    - Parameters: None
    - Returns: UserForms
    - Description: Returns the rankings of all players that have played at least one game by their
    lifetime score.

 - **get_high_scores**
    - Path: 'scores/highest'
    - Method: GET
    - Parameters: results (optional)
    - Returns: ScoreForms
    - Description: Returns the rankings from the top N games (player/score) in descending order. If 'N' (results) is not specified, returns the top three game scores.

 - **get_game_history**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: StringMessage containing history
    - Description: Returns the move history of a game as a stringified list of
    tuples in the form (card1, card2) eg: [(0,3), (1,2)]

## Models Included:
 - **User**
    - Stores unique user_name and (optional) email address. Also keeps track of total get_user_games
      completed and lifetime score.

 - **Game**
    - Stores game state, history, solution, size and in-game score.
    Associated with User model via KeyProperty 'user'.

 - **Score**
    - Records completed games. Associated with User and Game model via KeyProperty.

## Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, status, score, board).
 - **NewGameForm**
    - Used to create a new game (user, size)
 - **MakeMoveForm**
    - Inbound make move form (card1, card2).
 - **ScoreForm**
    - Representation of a completed game's Score (date, size, user, urlsafe_key).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **UserForm**
    - Representation of User (games, score).
 - **UserForms**
    - Container for one or more UserForm.
 - **StringMessage**
    - General purpose String container.

## Credits
The basic structure of the files here is based off code for the
[Udacity Guess-a-Number Game](https://github.com/udacity/FSND-P4-Design-A-Game/tree/master/Skeleton%20Project%20Guess-a-Number). This code is intended for educational purposes only in fulfillment of the [Project 4: Design a Game](https://github.com/udacity/FSND-P4-Design-A-Game) requirement of the
[Udacity Full-Stack Web Developer Nanodegree Program](https://www.udacity.com/course/full-stack-web-developer-nanodegree--nd004).
