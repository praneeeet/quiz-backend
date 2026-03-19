from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, QuizViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'quizzes', QuizViewSet, basename='quiz')

urlpatterns = [
    path('', include(router.urls)),
]
