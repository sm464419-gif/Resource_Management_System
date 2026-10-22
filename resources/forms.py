from django import forms
from .models import Resource, ResourceCategory



class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = "__all__"


class ResourceCategoryForm(forms.ModelForm):
    class Meta:
        model = ResourceCategory
        fields = "__all__"
