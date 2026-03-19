from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('quizzes.urls')),
    path('api/', include('attempts.urls')),
    path('api/', include('analytics.urls')),
]
