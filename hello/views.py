from django.shortcuts import render
from django.http import HttpResponse

from .models import Greeting

# Create your views here.
def index(request):
    return render(request, "index.html", {'board': 'rnbqkbnrpppppppp11111111111111111111111111111111PPPPPPPPRNBQKBNR'})


def index1(request):
    return render(request, "index.html", {'board': '1nbqkbnrppppppppr1111111111111111111111111111111PPPPPPPPRNBQKBNR'})
