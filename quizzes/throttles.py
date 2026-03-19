from rest_framework.throttling import UserRateThrottle


class QuizCreateThrottle(UserRateThrottle):
    scope = 'quiz_create'