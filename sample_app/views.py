from django.shortcuts import render
from django.utils import timezone

def index(request):
    context = {
        'current_time': timezone.now(),
    }
    return render(request, 'sample_app/index.html', context)
