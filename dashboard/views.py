from django.shortcuts import render

def home(request):
    return render(request, 'dashboard/home.html')


def control(request):
    return render(request, 'dashboard/control.html')