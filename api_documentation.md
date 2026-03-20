# API Documentation

**Base URL:** `https://quiz-backend-production-9038.up.railway.app/api/v1`

**Interactive Docs:** [Swagger UI](https://quiz-backend-production-9038.up.railway.app/api/docs/) | [ReDoc](https://quiz-backend-production-9038.up.railway.app/api/redoc/)

**Authentication:** JWT Bearer tokens. Include `Authorization: Bearer <access_token>` header on all authenticated requests.

---

## Authentication

### Register
```
POST /auth/register/
Access: Public
```
**Request:**
```json
{
    "username": "player1",
    "email": "player1@example.com",
    "password": "StrongPass123!",
    "password_confirm": "StrongPass123!",
    "role": "player"
}
```
**Response (201):**
```json
{
    "user": {
        "id": "uuid",
        "username": "player1",
        "email": "player1@example.com",
        "role": "player",
        "date_joined": "2026-03-20T...",
        "updated_at": "2026-03-20T..."
    },
    "tokens": {
        "access": "eyJ...",
        "refresh": "eyJ..."
    }
}
```

### Login
```
POST /auth/login/
Access: Public
```
**Request:**
```json
{
    "username": "player1",
    "password": "StrongPass123!"
}
```
**Response (200):** Same format as register.

### Refresh Token
```
POST /auth/token/refresh/
Access: Public
```
**Request:**
```json
{
    "refresh": "eyJ..."
}
```
**Response (200):**
```json
{
    "access": "eyJ...",
    "refresh": "eyJ..."
}
```

### Logout
```
POST /auth/logout/
Access: Authenticated
```
**Request:**
```json
{
    "refresh": "eyJ..."
}
```
**Response (200):**
```json
{
    "message": "Logout successful."
}
```

### Profile
```
GET /auth/profile/
PATCH /auth/profile/
Access: Authenticated
```
**GET Response (200):**
```json
{
    "id": "uuid",
    "username": "player1",
    "email": "player1@example.com",
    "role": "player",
    "date_joined": "2026-03-20T...",
    "updated_at": "2026-03-20T..."
}
```
**PATCH Request:** Send only the fields to update. `role` is read-only.

---

## Categories

### List Categories
```
GET /categories/
Access: Authenticated
```
**Response (200):**
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Python",
            "description": "Python programming quizzes",
            "created_at": "2026-03-20T...",
            "quiz_count": 5
        }
    ]
}
```

### Create Category
```
POST /categories/
Access: Admin only
```
**Request:**
```json
{
    "name": "Python",
    "description": "Python programming quizzes"
}
```

### Get / Update / Delete Category
```
GET /categories/{id}/
PATCH /categories/{id}/
DELETE /categories/{id}/
Access: GET = Authenticated, PATCH/DELETE = Admin only
```

---

## Quizzes

### List Quizzes
```
GET /quizzes/
Access: Authenticated
```
Players see published + own quizzes. Admins see all quizzes.

**Query Parameters:**
- `?category=uuid` — filter by category
- `?difficulty=easy|medium|hard` — filter by difficulty
- `?status=ready|failed|pending` — filter by status
- `?search=keyword` — search title and topic
- `?ordering=-created_at|title` — sort results

**Response (200):**
```json
{
    "count": 10,
    "next": "...?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "title": "Python Basics",
            "topic": "Python fundamentals",
            "description": null,
            "category": "uuid",
            "category_name": "Python",
            "difficulty": "easy",
            "number_of_questions": 5,
            "status": "ready",
            "is_published": true,
            "time_limit_seconds": null,
            "created_by": "player1 (player)",
            "created_at": "2026-03-20T..."
        }
    ]
}
```

### Create Quiz
```
POST /quizzes/
Access: Authenticated
Rate Limit: 10 per hour
```
Triggers AI question generation in the background. Quiz starts with `status: pending`, transitions to `generating`, then `ready` or `failed`.

**Request:**
```json
{
    "title": "Python Basics",
    "topic": "Python fundamentals including variables, data types, and loops",
    "category": "uuid (optional)",
    "difficulty": "easy",
    "number_of_questions": 5,
    "time_limit_seconds": 600
}
```
**Response (201):**
```json
{
    "id": "uuid",
    "title": "Python Basics",
    "topic": "Python fundamentals...",
    "difficulty": "easy",
    "number_of_questions": 5,
    "status": "pending"
}
```

### Get Quiz Detail
```
GET /quizzes/{id}/
Access: Authenticated
```
Owner and admin see questions with correct answers. Other players see questions without correct answers.

### Update Quiz
```
PATCH /quizzes/{id}/
Access: Owner or Admin
```
Can update: title, description, category, difficulty, is_published, time_limit_seconds.
Cannot update: topic, number_of_questions (these affect generated questions).

### Delete Quiz
```
DELETE /quizzes/{id}/
Access: Owner or Admin
```

### My Quizzes
```
GET /quizzes/my_quizzes/
Access: Authenticated
```
Returns only quizzes created by the current user.

### Publish / Unpublish
```
POST /quizzes/{id}/publish/
Access: Owner or Admin
```
Toggles the `is_published` flag.

### Regenerate Questions
```
POST /quizzes/{id}/regenerate/
Access: Owner or Admin
```
Only works on quizzes with `status: failed`. Deletes existing questions and triggers AI generation again.

---

## Quiz Attempts

### Start Attempt
```
POST /attempts/start/{quiz_id}/
Access: Authenticated
```
**Validations:**
- Quiz must have `status: ready`
- Quiz must be published (or user is the owner)
- User cannot have an existing in-progress attempt for this quiz

**Response (201):**
```json
{
    "id": "uuid",
    "quiz": "uuid",
    "quiz_title": "Python Basics",
    "status": "in_progress",
    "total_questions": 5,
    "score": null,
    "questions": [
        {
            "id": "uuid",
            "question_text": "What is Python?",
            "options": ["A language", "A snake", "A game", "A food"],
            "order": 0
        }
    ]
}
```
Note: `correct_option` and `explanation` are NOT included during active attempts.

### Submit Answer
```
POST /attempts/{id}/submit_answer/
Access: Attempt owner only
```
**Request:**
```json
{
    "question_id": "uuid",
    "selected_option": 0
}
```
**Response (201):**
```json
{
    "answer": {
        "id": "uuid",
        "question_id": "uuid",
        "selected_option": 0,
        "answered_at": "2026-03-20T..."
    },
    "progress": {
        "answered": 1,
        "total": 5
    }
}
```
Note: `is_correct` is NOT included. Results are revealed only after completion.

### Complete Attempt
```
POST /attempts/{id}/complete/
Access: Attempt owner only
```
**Response (200):**
```json
{
    "id": "uuid",
    "quiz": "uuid",
    "quiz_title": "Python Basics",
    "status": "completed",
    "score": 4,
    "total_questions": 5,
    "correct_answers": 4,
    "score_percentage": "80.00",
    "started_at": "2026-03-20T...",
    "completed_at": "2026-03-20T...",
    "answers": [
        {
            "id": "uuid",
            "question_id": "uuid",
            "selected_option": 0,
            "is_correct": true,
            "answered_at": "2026-03-20T..."
        }
    ],
    "questions": [
        {
            "id": "uuid",
            "question_text": "What is Python?",
            "options": ["A language", "A snake", "A game", "A food"],
            "correct_option": 0,
            "explanation": "Python is a programming language.",
            "order": 0
        }
    ]
}
```
After completion: `is_correct` on answers and `correct_option`/`explanation` on questions are revealed.

### List Attempts
```
GET /attempts/
Access: Authenticated (players see own, admins see all)
```

### Get Attempt Detail
```
GET /attempts/{id}/
Access: Attempt owner or Admin
```

---

## Analytics

### My Stats
```
GET /analytics/me/
Access: Authenticated
```
**Response (200):**
```json
{
    "total_quizzes_attempted": 10,
    "total_completed": 8,
    "total_in_progress": 1,
    "average_score_percentage": "75.50",
    "best_score_percentage": "100.00",
    "total_questions_answered": 50,
    "correct_answers_total": 38,
    "overall_accuracy": "76.00"
}
```

### Category Performance
```
GET /analytics/me/categories/
Access: Authenticated
```
**Response (200):**
```json
[
    {
        "category_id": "uuid",
        "category_name": "Python",
        "quizzes_attempted": 3,
        "average_score": "80.00",
        "best_score": "100.00",
        "total_attempts": 5
    }
]
```

### Quiz Stats
```
GET /analytics/quizzes/{id}/
Access: Quiz owner or Admin
```
**Response (200):**
```json
{
    "quiz_id": "uuid",
    "quiz_title": "Python Basics",
    "total_attempts": 25,
    "total_completed": 20,
    "completion_rate": "80.00",
    "average_score": "72.50",
    "highest_score": "100.00",
    "lowest_score": "20.00",
    "question_breakdown": [
        {
            "question_id": "uuid",
            "question_text": "What is Python?",
            "total_answers": 20,
            "correct_count": 18,
            "accuracy_percentage": "90.00"
        }
    ]
}
```

### Leaderboard
```
GET /analytics/leaderboard/
Access: Authenticated
```
**Query Parameters:**
- `?category=uuid` — filter by category

**Response (200):**
```json
[
    {
        "rank": 1,
        "user_id": "uuid",
        "username": "player1",
        "total_quizzes_completed": 15,
        "average_score": "92.50",
        "total_correct_answers": 120
    }
]
```

### System Stats
```
GET /analytics/system/
Access: Admin only
```
**Response (200):**
```json
{
    "total_users": 50,
    "active_users": 48,
    "total_quizzes": 30,
    "published_quizzes": 22,
    "total_attempts": 200,
    "completed_attempts": 180,
    "completion_rate": "90.00",
    "average_score": "74.30",
    "most_popular_quizzes": [
        {"id": "uuid", "title": "Python Basics", "attempt_count": 45}
    ]
}
```

---

## Admin User Management

### List Users
```
GET /auth/admin/users/
Access: Admin only
```
**Query Parameters:**
- `?role=admin|player`
- `?is_active=true|false`
- `?search=keyword`

### Get / Update User
```
GET /auth/admin/users/{id}/
PATCH /auth/admin/users/{id}/
Access: Admin only
```
**PATCH — Updatable fields:** `role`, `is_active` only. Admin cannot deactivate themselves.

---

## Error Responses

All errors follow a consistent format:
```json
{
    "error": "error_code",
    "message": "Human readable description."
}
```

| Status | Code | Meaning |
|---|---|---|
| 400 | validation_error | Invalid input data |
| 401 | authentication_error | Missing or invalid JWT token |
| 403 | permission_denied | User lacks permission |
| 404 | not_found | Resource doesn't exist |
| 409 | conflict | Duplicate resource (e.g. in-progress attempt exists) |
| 429 | throttled | Rate limit exceeded |

---

## Rate Limits

| Scope | Limit |
|---|---|
| Anonymous | 20 requests/hour |
| Authenticated | 200 requests/hour |
| Quiz creation | 10 requests/hour |

---

## AI Providers (Multi-Provider Fallback)

Quiz questions are generated using a fallback chain of AI providers:

1. **Groq** (Llama 3.3 70B) — Primary, fastest
2. **Google Gemini** (Flash) — Secondary backup
3. **OpenRouter** (Llama 3.3) — Tertiary backup

If one provider fails, the system automatically tries the next. Each attempt is logged in the AIGenerationLog for admin monitoring.