"""
URLs para o app extratos_app
"""
from django.urls import path
from . import views

app_name = 'extratos'

urlpatterns = [
    path('', views.index, name='index'),
    path('processar/', views.processar_extratos_view, name='processar'),
    path('resultado/<uuid:processamento_id>/', views.resultado, name='resultado'),
    path('download/<uuid:processamento_id>/', views.download_resultado, name='download'),
]
