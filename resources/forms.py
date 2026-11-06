from django import forms
from .models import Resource, ResourceCategory



class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        exclude = ['qr_code', 'device_code']


class ResourceCategoryForm(forms.ModelForm):
    class Meta:
        model = ResourceCategory
        fields = "__all__"
