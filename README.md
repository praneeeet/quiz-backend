# AI-Powered Quiz API

A comprehensive REST API for a quiz application that handles user management, AI-powered quiz generation, quiz attempts with scoring, and detailed performance analytics. Built with Django, Django REST Framework, and PostgreSQL.

---

## Local Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Git

### Step 1: Clone and create virtual environment
```bash
git clone <repo-url>
cd quiz-backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Create PostgreSQL database
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Run these commands
CREATE DATABASE quiz_db;
CREATE USER quiz_user WITH PASSWORD 'your_password';
ALTER ROLE quiz_user SET client_encoding TO 'utf8';
ALTER ROLE quiz_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE quiz_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE quiz_db TO quiz_user;
\q
```

### Step 4: Configure environment variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your-random-secret-key-here
DATABASE_NAME=quiz_db
DATABASE_USER=quiz_user
DATABASE_PASSWORD=your_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
GROQ_API_KEY=your-groq-api-key
```

Get a free Groq API key at https://console.groq.com/keys

### Step 5: Run migrations and create admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 6: Start the server
```bash
python manage.py runserver
```

### Step 7: Access the API
- Swagger documentation: http://127.0.0.1:8000/api/docs/
- ReDoc documentation: http://127.0.0.1:8000/api/redoc/
- Django admin panel: http://127.0.0.1:8000/admin/

### Running Tests
```bash
python manage.py test
```

---

## Database Schema and Model Relationships

### Entity Relationship Summary

```
User ||--o{ Quiz            (created_by, CASCADE)
User ||--o{ QuizAttempt     (user, CASCADE)
Category ||--o{ Quiz        (category, SET_NULL)
Quiz ||--o{ Question        (quiz, CASCADE)
Quiz ||--o{ QuizAttempt     (quiz, CASCADE)
Quiz ||--o{ AIGenerationLog (quiz, CASCADE)
QuizAttempt ||--o{ AttemptAnswer (attempt, CASCADE)
Question ||--o{ AttemptAnswer   (question, CASCADE)
```

### Models

**User** (extends Django's AbstractUser)
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key, auto-generated |
| username | CharField | Unique, inherited |
| email | EmailField | Unique, required |
| password | CharField | Hashed by Django |
| role | CharField | Choices: `admin`, `player`. Default: `player` |
| date_joined | DateTimeField | Auto-set on creation |
| updated_at | DateTimeField | Auto-set on every save |

**Category**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| name | CharField(100) | Unique |
| description | TextField | Optional |
| created_at | DateTimeField | Auto-set |

**Quiz**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| title | CharField(255) | Required |
| topic | CharField(255) | Free text sent to AI as prompt |
| description | TextField | Optional |
| category | FK → Category | Nullable, SET_NULL on delete |
| difficulty | CharField | Choices: `easy`, `medium`, `hard` |
| number_of_questions | PositiveInteger | Default: 10 |
| status | CharField | Choices: `pending`, `generating`, `ready`, `failed` |
| is_published | Boolean | Default: False |
| time_limit_seconds | PositiveInteger | Optional |
| created_by | FK → User | CASCADE on delete |
| created_at | DateTimeField | Auto-set |
| updated_at | DateTimeField | Auto-set on every save |

**Question**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| quiz | FK → Quiz | CASCADE on delete |
| question_text | TextField | The question body |
| question_type | CharField | Default: `mcq` (extensible for future types) |
| options | JSONField | List of 4 option strings |
| correct_option | PositiveSmallInteger | Index 0-3 into options array |
| explanation | TextField | Optional, AI-generated |
| order | PositiveSmallInteger | Display sequence within quiz |

Constraint: `unique_together = (quiz, order)`

**QuizAttempt**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| user | FK → User | CASCADE on delete |
| quiz | FK → Quiz | CASCADE on delete |
| status | CharField | Choices: `in_progress`, `completed`, `timed_out` |
| score | PositiveInteger | Nullable, set on completion |
| total_questions | PositiveInteger | Snapshot from quiz at attempt creation |
| correct_answers | PositiveInteger | Nullable, count of correct on completion |
| score_percentage | Decimal(5,2) | Nullable, computed on completion |
| started_at | DateTimeField | Auto-set on creation |
| completed_at | DateTimeField | Nullable, set on completion |

Indexes: `(user, quiz)`, `(user, status)`

**AttemptAnswer**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| attempt | FK → QuizAttempt | CASCADE on delete |
| question | FK → Question | CASCADE on delete |
| selected_option | PositiveSmallInteger | Nullable (null = skipped) |
| is_correct | Boolean | Computed on save by comparing selected_option to question.correct_option |
| answered_at | DateTimeField | Auto-set |

Constraint: `unique_together = (attempt, question)`
Index: `(question, is_correct)`

**AIGenerationLog**
| Field | Type | Details |
|---|---|---|
| id | UUID | Primary key |
| quiz | FK → Quiz | CASCADE on delete |
| provider | CharField | Default: `groq` |
| prompt_sent | TextField | Exact prompt sent to AI |
| raw_response | TextField | Raw AI response for debugging |
| status | CharField | Choices: `success`, `failed`, `timeout`, `pending` |
| response_time_ms | Integer | Latency tracking |
| error_message | TextField | Optional, stores failure reason |
| created_at | DateTimeField | Auto-set |

### Deliberate Denormalizations

| Field | Model | Justification |
|---|---|---|
| `options` (JSONField) | Question | Options are fixed-size (always 4), always co-fetched with question, never queried independently. Eliminates a JOIN per question with zero practical downside. Validated at serializer level. |
| `total_questions` | QuizAttempt | Snapshotted from quiz at attempt creation. If the quiz is later edited, historical attempts must reflect what the user actually faced, not the current quiz state. |
| `correct_answers` | QuizAttempt | Computed once on completion. Avoids COUNT query across AttemptAnswer table on every analytics/history read. |
| `score_percentage` | QuizAttempt | Computed once on completion. Avoids repeated division in analytics aggregation queries (AVG, MAX, MIN across thousands of attempts). |
| `is_correct` | AttemptAnswer | Derived from `selected_option == question.correct_option`, but stored separately so analytics queries ("what % got question 5 right?") don't need to JOIN the Question table. |

---

## API Endpoint Overview

### Authentication (`/api/v1/auth/`)
| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| POST | `/register/` | Create user account, returns JWT tokens | Public |
| POST | `/login/` | Authenticate, returns access + refresh tokens | Public |
| POST | `/token/refresh/` | Get new access token using refresh token | Public |
| POST | `/logout/` | Blacklist refresh token | Authenticated |
| GET | `/profile/` | View current user profile | Authenticated |
| PATCH | `/profile/` | Update current user profile | Authenticated |
| GET | `/admin/users/` | List all users with filtering | Admin only |
| GET/PATCH | `/admin/users/{id}/` | View or update any user (role, is_active) | Admin only |

### Categories (`/api/v1/categories/`)
| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/` | List all categories (cached 300s) | Authenticated |
| POST | `/` | Create category | Admin only |
| GET | `/{id}/` | Category detail with quiz count | Authenticated |
| PATCH | `/{id}/` | Update category | Admin only |
| DELETE | `/{id}/` | Delete category | Admin only |

### Quizzes (`/api/v1/quizzes/`)
| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/` | List quizzes (filtered, paginated) | Authenticated (player sees published+own, admin sees all) |
| POST | `/` | Create quiz (triggers AI generation) | Authenticated (rate limited: 10/hour) |
| GET | `/{id}/` | Quiz detail with questions | Authenticated (answers hidden for non-owner players) |
| PATCH | `/{id}/` | Update quiz metadata | Owner or Admin |
| DELETE | `/{id}/` | Delete quiz | Owner or Admin |
| POST | `/{id}/publish/` | Toggle publish status | Owner or Admin |
| POST | `/{id}/regenerate/` | Retry AI generation for failed quizzes | Owner or Admin |
| GET | `/my_quizzes/` | List current user's quizzes | Authenticated |

Filtering: `?category=uuid`, `?difficulty=easy|medium|hard`, `?status=ready|failed`, `?search=keyword`

### Attempts (`/api/v1/attempts/`)
| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/` | List attempts | Authenticated (player sees own, admin sees all) |
| GET | `/{id}/` | Attempt detail with answers and questions | Attempt owner or Admin |
| POST | `/start/{quiz_id}/` | Start new attempt | Authenticated |
| POST | `/{id}/submit_answer/` | Submit answer to a question | Attempt owner only |
| POST | `/{id}/complete/` | Finalize attempt, calculate score | Attempt owner only |

### Analytics (`/api/v1/analytics/`)
| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/me/` | Current user's overall performance stats | Authenticated |
| GET | `/me/categories/` | Performance breakdown by category | Authenticated |
| GET | `/quizzes/{id}/` | Quiz stats with per-question accuracy breakdown | Owner or Admin |
| GET | `/leaderboard/` | Top 20 performers (supports `?category=uuid` filter) | Authenticated |
| GET | `/system/` | Platform-wide stats (users, quizzes, attempts, popular quizzes) | Admin only |

---

### Status Lifecycle
```
User creates quiz → status: pending
AI service called → status: generating
Questions parsed and saved → status: ready
Any error occurs → status: failed (user can retry via /regenerate/)
```


---

## Testing Approach

### Overview
27 automated tests across all 4 modules using DRF's `APITestCase`. Tests cover authentication flows, permission enforcement, the complete attempt lifecycle, score calculation accuracy, answer visibility logic, and admin access control.

### What's Tested
- **Auth**: Registration (success, duplicates, weak passwords), login (success, wrong credentials), profile access and update, logout
- **Permissions**: Player vs admin access differences across all endpoints — category creation blocked for players, quiz visibility filtered by role, attempt visibility scoped to user
- **Attempt lifecycle**: Start → submit answers → complete → score calculated correctly, with checks for duplicate attempts, wrong-quiz answers, and post-completion submission rejection
- **Analytics**: Stats return zeros for new users, update after completion, quiz stats restricted to owner/admin, system stats admin-only

### How Tests Work
- Tests use a temporary database created and destroyed automatically — real data is never touched
- `force_authenticate` bypasses JWT for speed — we're testing view logic, not the JWT library
- AI generator is mocked with `unittest.mock.patch` — no real API calls during tests
- Each test is independent with fresh data via `setUp`

### Running Tests
```bash
python manage.py test                    # Run all tests
python manage.py test accounts           # Run only auth tests
python manage.py test quizzes            # Run only quiz tests
python manage.py test attempts           # Run only attempt tests
python manage.py test analytics          # Run only analytics tests
```

---

## Potential Improvements

Given more time, I would add:

- **Background task processing**: Celery + Redis for async AI generation — the schema already supports this via the status field
- **Quiz time enforcement**: Backend check on `submit_answer` and `complete` to auto-timeout attempts that exceed `time_limit_seconds`
- **More question types**: True/False and Multiple Select — the `question_type` field already exists for extensibility
- **WebSocket support**: Real-time quiz sessions for competitive multiplayer
- **Docker containerization**: Dockerfile and docker-compose for consistent deployment
- **CI/CD pipeline**: GitHub Actions for automated testing on push
- **Redis cache backend**: Replace in-memory cache with Redis for production multi-process environments