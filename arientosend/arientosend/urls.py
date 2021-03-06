"""arientosend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
# from django.contrib import admin
from send import views

# don't rearrange the order of the links
urlpatterns = [
    # url(r'^admin/', admin.site.urls),
    url(r'^index', views.index),
    url(r'^client-send', views.client_send),
    url(r'^client', views.client),
    url(r'^refclient', views.refclient),
    url(r'^download/(?P<key>\w+)/$', views.download),
    url(r'^download/(?P<key>\w+)/retrieve$', views.retrieve),
    url(r'^guest-send', views.guest_send),
    url(r'^guest', views.guest),
    url(r'^login', views.login),
    url(r'^logout', views.logout),
    url(r'^two-factor', views.two_factor),
    url(r'^user-download', views.user_download),
    url(r'^$', views.index),
]
