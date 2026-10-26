from django.contrib import admin

from .models import Guset, Movie, Reservation

admin.site.register((Movie, Guset, Reservation))
