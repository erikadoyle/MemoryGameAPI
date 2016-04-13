#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging
import webapp2
from google.appengine.api import mail, app_identity
from google.appengine.ext import ndb
from api import MemoryGameAPI
from utils import get_by_urlsafe

from models import User, Game, GameState


class SendChallengeEmail(webapp2.RequestHandler):
    def get(self):
        """Send a challenge email to each player whose score is less than the
        global average. Email body also includes a count of active games and
        their urlsafe keys. Called every hour using a cron job"""
        users = User.query()

        for user in users:
            subject = 'Is your memory better than average?'
            avg = int(float(MemoryGameAPI._get_average_score()))
            if (user.score < avg):
                diff = avg - user.score
                body = 'Greetings {}, Your current Memory Game score is: {}. '
                'It is {} less than the average score of {}. Keep going!'.\
                    format(diff, avg)

                games = Game.query(Game.user == user.key).\
                    filter(Game.status == GameState.Active)
                if games.count() > 0:
                    active_games = 'You have {} games in progress. Their' \
                                   ' keys are: {}'.\
                                   format(user.name, games.count(), ', '.
                                          join(game.key.urlsafe() for game in games))
                    body += active_games
                logging.debug(body)
                mail.send_mail('noreply@{}.appspotmail.com'.
                               format(app_identity.get_application_id()),
                               user.email, subject, body)


class UpdateAverageScore(webapp2.RequestHandler):
    def get(self):
        """Updates average player score in memcache."""
        MemoryGameAPI.cache_average_score()
        self.response.set_status(204)


class SendCongratsEmail(webapp2.RequestHandler):
    def post(self):
        """Send email to the winning player comparing their score to average."""
        user = get_by_urlsafe(self.request.get('user_key'), User)
        game = get_by_urlsafe(self.request.get('game_key'), Game)
        subject = 'Congratulations'
        body = 'Congratulations {}, for completing the game  {}. '\
               'Your current score is now {}. The average score is {}. '\
               'Keep it up!'.format(user.name, game.key.urlsafe(),
                                    user.score,
                                    MemoryGameAPI._get_average_score())
        logging.debug(body)
        mail.send_mail('noreply@{}.appspotmail.com'.
                       format(app_identity.get_application_id()), user.email,
                       subject, body)


app = webapp2.WSGIApplication([
    ('/tasks/send_congrats_email', SendCongratsEmail),
    ('/crons/cache_average_score', UpdateAverageScore),
    ('/crons/send_challenge', SendChallengeEmail)
], debug=True)
