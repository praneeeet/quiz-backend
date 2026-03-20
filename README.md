# AI-Powered Quiz API

A comprehensive REST API for a quiz application that handles user management, AI-powered quiz generation, quiz attempts with scoring, and detailed performance analytics. Built with Django, Django REST Framework, and PostgreSQL.

---

## Key Features
- **Multi-provider AI Fallback**: Self-healing question generation that tries multiple providers in sequence (Groq → Gemini → OpenRouter) to ensure 100% uptime even if one service is down.
- **RESTful Architecture**: Clean, versioned API endpoints with JWT authentication and role-based access control.
- **Interactive Attempts**: Real-time quiz taking with automated scoring and post-completion answer reveal.
- **Performance Analytics**: Detailed personal and global statistics with efficient database denormalization.

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
GEMINI_API_KEY=your-gemini-api-key
OPENROUTER_API_KEY=your-openrouter-api-key
```

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
## Design Decisions

The system is designed as a modular monolith with 5 Django apps — accounts, quizzes, ai_service, attempts, and analytics. Each app owns one responsibility and dependencies flow in one direction: accounts depends on nothing, quizzes depends on accounts, ai_service depends on quizzes, attempts depends on both accounts and quizzes, and analytics reads from attempts and quizzes but writes nothing. This structure keeps the codebase navigable and makes it possible to extract any module into a standalone service if needed later.

Authentication uses JWT tokens with a short-lived access token (60 minutes) and a long-lived refresh token (7 days). The access token is stateless — no database lookup on every request. The refresh token supports rotation and blacklisting, so when a user logs out, the refresh token is invalidated immediately. All endpoints require authentication by default; public endpoints like register and login explicitly opt out. This "secure by default" approach means forgetting to add permissions to a new endpoint results in it being private, not public.

The User model extends Django's AbstractUser with UUID primary keys and a role-based access control system. UUIDs prevent sequential ID enumeration on a public API. The role field (admin/player) is separate from Django's is_staff because app-level permissions and Django admin panel access are different concerns. Admin users have full visibility across the system — they see all quizzes, all attempts, and can manage user accounts. Players only see published quizzes and their own data.

Quiz creation triggers AI question generation through a multi-provider fallback system. The system implements a chain-of-responsibility pattern: it first attempts generation via Groq (Llama 3.3 70B), then falls back to Google Gemini (2.0 Flash) if Groq fails, and finally uses OpenRouter as a last resort. This multi-provider approach was chosen for maximum reliability — external AI services often have strict rate limits or occasional downtime. By depending on a chain of providers rather than a single one, the system ensures that quiz creation remains functional even during service interruptions from one or two providers.

The generation lifecycle is tracked via a status field on the Quiz model (pending → generating → ready → failed), making the system ready for future asynchronous processing with Celery. Every generation attempt is logged in detail, capturing the exact prompt, raw response, timing, and specific provider used, which is critical for monitoring costs and debugging parser failures.

The attempt flow is designed around answer security. When a user starts an attempt, questions are served without correct answers or explanations. Answers are submitted one at a time and the response confirms receipt but does not reveal correctness. Only when the user completes the attempt does the system calculate the score and reveal all correct answers, explanations, and per-question results. This is enforced at the serializer level — different serializers physically include or exclude fields based on attempt status, so even direct API calls cannot bypass this.

Data integrity for historical attempts is maintained through deliberate denormalization. The total question count is snapshotted at attempt creation so future quiz edits don't corrupt historical scores. Correct answer counts and score percentages are computed once on completion and stored, avoiding expensive aggregation queries on every analytics or leaderboard request. The is_correct field on each answer is computed on save to eliminate joins in per-question accuracy analytics.

Caching is applied selectively — only on data where slight staleness is acceptable (category list and quiz-level stats for creators) and explicitly avoided on user-facing analytics where users expect to see their new scores immediately. API rate limiting operates at three tiers: anonymous users (20/hour), authenticated users (200/hour), and quiz creation (10/hour) since each creation triggers an external AI call with its own cost and rate limits.

The system includes several production-readiness features beyond core functionality. 

-API rate limiting operates at three tiers — anonymous users at 20 requests per hour to prevent brute-force attacks, authenticated users at 200 per hour for general usage, and a stricter 10 per hour specifically for quiz creation since each triggers an external AI call.

-API documentation is auto-generated from the codebase using drf-spectacular, serving both Swagger UI and ReDoc interfaces for frontend developers to explore and 
test endpoints.

-All endpoints are versioned under /api/v1/ using URL path versioning so future breaking changes can be introduced as v2 without disrupting existing clients.

-The test suite covers 27 automated tests across all modules — authentication flows, permission enforcement, the complete attempt lifecycle, score calculation accuracy, and answer visibility logic — using mocked AI calls so tests run fast without external dependencies.

-The Admin Interface is customized with inline question editing, attempt inspection, and AI generation log review for operational monitoring.

---

## 🤖 AI Integration Strategy

The system utilizes a **Provider-Agnostic Interface** (`BaseQuizProvider`) that abstracts the specifics of different AI services. This decoupled design allowed us to implement a robust multi-provider strategy:

- **Multi-Provider Fallback**: We implement a chain-of-responsibility pattern. If the primary provider (Groq) fails due to rate limits or downtime, the system automatically tries Google Gemini, and finally falls back to OpenRouter.
- **Detailed Audit Trail**: Every AI generation attempt is logged in the `AIGenerationLog` model, capturing the exact prompt, raw response, latency, and any error messages.
- **Fail-safe Task Processing**: While we prefer background processing via Celery for better UX, we've implemented a **Hybrid Generation Logic**. If the Celery worker or Redis broker is offline, the system gracefully falls back to synchronous generation, ensuring the core functionality is always available.

---

## 🚧 Challenges Faced & Solutions

- **Challenge: Unreliable AI JSON Formatting**
  - **Context**: AI models occasionally include preamble text ("Here is your quiz...") or wrap the result in markdown code blocks, which breaks standard JSON parsers.
  - **Solution**: Developed a specialized `_parse_response` utility that uses regex and string manipulation to strip markdown ticks and extract only the valid JSON payload before validation.

- **Challenge: Balancing Answer Security with User Experience**
  - **Context**: We needed to allow quiz creators to see their own answers while strictly hiding them from players who are currently attempting the quiz.
  - **Solution**: Implemented dynamic serializer switching in the `QuizViewSet`. The API detects the user's relationship to the quiz and serves a "Redacted" version of the questions to players, ensuring correct answers never leave the server during an active attempt.

- **Challenge: Avoiding Sequential ID Guessing**
  - **Context**: Using standard integer IDs (1, 2, 3) makes the API vulnerable to enumeration attacks where users can guess and access private quiz data.
  - **Solution**: Migrated the entire database schema to use **UUIDv4** for all primary keys. This makes IDs non-guessable and adds an essential layer of security to the RESTful interface.


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

