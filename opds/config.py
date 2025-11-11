"""
This file contains all Global variables
"""
import os

DB_PATH = "database/db.json"

OAUTH_LINK = "https://archive.org/services/oauth2/access_token.php"
USER_PROFILE_LINK = "https://archive.org/services/loans/loan/?action=user_profile"
SHELF_LINK = "https://archive.org/services/loans/loan/?action=user_bookshelf"

ITEMS_PER_PAGE = 25
ITEMS_PER_GROUP = 10
IA_SEARCH_ENGINE_LIMIT_PAGE = 10000
cpu_count = os.cpu_count() or 4
MAX_WORKERS = min(cpu_count * 5, 50)


AUTHENTICATION_DOCUMENT = """{
    "title": "Log in",
    "id": "/authentication_document",
    "description": "Log in to the Internet Archive to continue.",
    "authentication": [
       {
      "type": "http://opds-spec.org/auth/oauth/password",
      "labels": {
        "login": "Username / Email address",
        "password": "Password"
      },
      "links": [
        {
          "rel": "authenticate",
          "href": "%s",
          "type": "application/json"
        },
        {
          "rel": "refresh",
          "href": "%s",
          "type": "application/json"
        }
      ]
    }
     ],
     "links": [
         {"rel": "logo", "href": "https://archive.org/images/glogo.jpg", "type": "image/jpeg"},
         {"rel": "profile", "href": "%s", "type": "application/opds-profile+json"},
         {"rel": "register", "href": "https://archive.org/account/login.createaccount.php", "type": "text/html"},
         {"rel": "help", "href": "mailto:info@archive.org"},
         {"rel": "about", "href": "https://archive.org/about/", "type": "text/html"},
     ]
}""" % (OAUTH_LINK, OAUTH_LINK, USER_PROFILE_LINK)

