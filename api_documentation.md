# AI-Powered Quiz API Documentation (v1)

This document provides a comprehensive reference for all available API endpoints, request bodies, and expected responses.

- **Base URL**: `https://quiz-backend-production-9038.up.railway.app/api/v1` (Production)
- **Local URL**: `http://127.0.0.1:8000/api/v1` (Local Development)
- **Format**: All requests and responses are in `application/json`
- **Authentication**: Bearer Token (JWT)

---

## 🔐 Authentication (`/api/v1/auth/`)

### 1. Register
`POST /register/` (Public)
Create a new user account. Returns standard user info and a pair of JWT tokens.

**Request Body**:
```json
{
    "username": "new_user",
    "email": "user@example.com",
    "password": "strongpassword123",
    "role": "player" // or "admin"
}
```

### 2. Login
`POST /login/` (Public)
Exchange credentials for access and refresh tokens.

**Request Body**:
```json
{ "username": "new_user", "password": "strongpassword123" }
```

**Response**:
```json
{
    "access": "eyJ0eX...",
    "refresh": "eyJ0eX...",
    "user": { "id": "uuid", "username": "new_user", "role": "player" }
}
```

### 3. Profile
`GET /profile/` (Authenticated)
Returns details of the currently authenticated user.

### 4. Admin User Management
`GET /admin/users/` (Admin Only)
List all users with filtering by role and status.

---

## 📂 Categories (`/api/v1/categories/`)

| Method | Endpoint | Access |
|---|---|---|
| GET | `/` | Authenticated |
| POST | `/` | Admin Only |
| GET | `/{id}/` | Authenticated |
| PATCH | `/{id}/` | Admin Only |
| DELETE | `/{id}/` | Admin Only |

---

## 🤖 Quizzes (`/api/v1/quizzes/`)

### 1. Create Quiz
`POST /` (Authenticated)
Triggers background AI generation.

**Request Body**:
```json
{
    "title": "Introduction to Python",
    "topic": "Python basics, variables, and loops",
    "category": "category_uuid",
    "difficulty": "easy", // easy, medium, hard
    "number_of_questions": 5
}
```

**Response**:
`201 Created` - Quiz entry created. Status will be `generating`.

### 2. List/Filter Quizzes
`GET /` (Authenticated)
- **Players**: See all published quizzes + their own.
- **Admins**: See all quizzes.
- **Filters**: `?category=uuid`, `?difficulty=easy`, `?status=ready`, `?search=keyword`.

### 3. Toggle Publish
`POST /{id}/publish/` (Owner/Admin Only)
Switches `is_published` between `true` and `false`.

### 4. Regenerate Questions
`POST /{id}/regenerate/` (Owner/Admin Only)
Retries AI generation if the previous attempt failed.

---

## 📝 Attempts (`/api/v1/attempts/`)

### 1. Start Attempt
`POST /start/{quiz_id}/` (Authenticated)
Initializes a new quiz attempt. Verifies that the quiz is published and ready.

### 2. Submit Answer
`POST /{id}/submit_answer/` (Attempt Owner Only)
Answer a specific question.
**Note**: Correctness is not revealed in the response.

**Request Body**:
```json
{
    "question_id": "uuid",
    "selected_option": 0 // index 0-3
}
```

### 3. Complete Attempt
`POST /{id}/complete/` (Attempt Owner Only)
Finalizes the attempt, calculates the score, and reveals all answers/explanations.

---

## 📈 Analytics (`/api/v1/analytics/`)

| Endpoint | Data Returned | Access |
|---|---|---|
| `GET /me/` | Total completed, avg score, total time | Authenticated |
| `GET /me/categories/` | Performance breakdown by category | Authenticated |
| `GET /quizzes/{id}/` | Accuracy % for each question in a quiz | Owner or Admin |
| `GET /leaderboard/` | Top 20 user rankings globally | Authenticated |
| `GET /system/` | System health, total users, popular quizzes | Admin Only |

---

## 📋 Status Codes

- `200 OK`: Successful retrieval or update.
- `201 Created`: Successful creation (Quiz, Attempt, Registration).
- `400 Bad Request`: Validation failure or invalid operation (e.g. submitting after completion).
- `401 Unauthorized`: Missing or invalid Bearer token.
- `403 Forbidden`: Permission denied (e.g. player accessing admin analytics).
- `404 Not Found`: Resource does not exist.
- `429 Too Many Requests`: Rate limit exceeded (Creation: 10/hour).
