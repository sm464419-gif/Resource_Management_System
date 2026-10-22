from django.contrib import admin
from .models import Resource, ResourceCategory

admin.site.register(Resource)
admin.site.register(ResourceCategory)