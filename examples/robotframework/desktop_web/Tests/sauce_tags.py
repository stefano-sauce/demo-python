"""Robot Framework variable file: builds the Sauce Labs `tags` list for a suite.

Usage in a resource file:  Variables  sauce_tags.py  framework:robotframework  usecase:...
SAUCE_TAGS (comma-separated, e.g. "ci:cron") is appended so scheduled runs can be told
apart from manual ones.
"""
import os


def get_variables(*tags):
    extra = [t.strip() for t in os.environ.get('SAUCE_TAGS', '').split(',') if t.strip()]
    slugged = [t.lower().replace(' ', '-') for t in tags]
    return {'SAUCE_TAGS_LIST': ['repo:demo-python', 'lang:python', *slugged, *extra]}
