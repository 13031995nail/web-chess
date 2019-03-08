from django.urls import path, include, re_path

from django.contrib import admin

admin.autodiscover()

import hello.views

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/

urlpatterns = [
    re_path('^newgame$', hello.views.new_game, name='newgame'),
    re_path('^net$', hello.views.move, name='net'),
    re_path('^([\w]+)$', hello.views.move, name='move'),
    re_path('^$', hello.views.index, name="index"),
]
