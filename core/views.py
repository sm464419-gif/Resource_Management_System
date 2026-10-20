from django.shortcuts import render


def base(request):
    return render(request, 'core/base.html')

def home(request):
    return render(request, 'core/home.html')