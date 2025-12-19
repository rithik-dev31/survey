# SurveyLens Technical Documentation

## Overview
SurveyLens is a Django-based web application designed for creating, managing, and analyzing surveys. It features a chatbot interface for survey responses, user management, and automated report generation using AI.

## Architecture

### Technology Stack
- **Backend**: Django 5.2.9
- **Database**: PostgreSQL
- **API**: Django REST Framework 3.16.1
- **AI Integration**: OpenAI GPT-4.1-mini for chatbot and report generation
- **Frontend**: Django Templates (HTML/CSS/JS)
- **Testing**: Playwright for end-to-end testing

### Project Structure
```
surveylens/
├── surveylens/          # Main Django project
│   ├── settings.py      # Django settings
│   ├── urls.py          # URL configuration
│   ├── wsgi.py          # WSGI application
│   └── asgi.py          # ASGI application
├── administator/        # Administrator app
│   ├── models.py        # Survey models
│   ├── views.py         # Admin views
│   ├── urls.py          # Admin URLs
│   ├── signals.py       # Automated report generation
│   ├── pdf_utils.py     # PDF generation utilities
│   └── templates/       # Admin templates
├── autho/               # Authentication app
│   ├── models.py        # User profile models
│   ├── views.py         # Auth views
│   ├── urls.py          # Auth URLs
│   └── templates/       # Auth templates
├── public_user_app/     # Public user interface
│   ├── views.py         # Public user views
│   ├── urls.py          # Public user URLs
│   └── templates/       # Public user templates
├── survey_reports/      # Report storage (empty)
├── manage.py            # Django management script
├── db.sqlite3           # Development database
└── requirements.txt     # Python dependencies
```

## Apps Description

### 1. administator
**Purpose**: Core survey management and administration.

**Models**:
- `Survey`: Survey metadata (title, demographics)
- `SurveyQuestion`: Questions with types and options
- `SurveyResponse`: Legacy response storage
- `UserSurveySession`: Per-user survey progress tracking
- `UserSurveyAnswer`: Individual question answers
- `SurveyReport`: Generated reports (HTML/PDF)
- `SurveySession`, `SurveyChatSession`, `SurveyChatMessage`: Chat functionality

**Key Features**:
- Dashboard with statistics
- Survey creation and management
- Automated report generation using OpenAI
- PDF report export
- Admin chatbot interface

### 2. autho
**Purpose**: User authentication and profile management.

**Models**:
- `Public_user`: Extended user profile with demographics

**Key Features**:
- User registration and login
- Profile management
- Role-based redirection (admin vs public user)

### 3. public_user_app
**Purpose**: Public user interface for taking surveys.

**Key Features**:
- Dashboard showing pending/completed surveys
- Chatbot-based survey interface
- Real-time survey responses via AJAX

## Database Schema

### Key Relationships
- Survey → SurveyQuestion (1:many)
- Survey → UserSurveySession (1:many)
- UserSurveySession → UserSurveyAnswer (1:many)
- User → Public_user (1:1)
- Survey → SurveyReport (1:1)

### Database Configuration
- **Engine**: PostgreSQL
- **Name**: surveylens
- **User**: postgres
- **Host**: localhost
- **Port**: 5432

## API Endpoints

### Authentication (`autho/urls.py`)
- `GET /` - Index (redirects based on user type)
- `POST /signin/` - User login
- `POST /signup/` - User registration

### Administrator (`administator/urls.py`)
- `GET /administator/` - Admin welcome page
- `GET /administator/admin-dashboard-stats/` - Dashboard statistics (AJAX)
- `GET /administator/api/surveys/` - Survey list
- `GET /administator/api/surveys/<id>/` - Survey details
- `GET /administator/survey-report-pdf/<id>/` - PDF report download

### Public User (`public_user_app/urls.py`)
- `GET /User/dashboard/` - Public user dashboard
- `GET /User/start-survey/<session_id>/` - Start survey chatbot
- `POST /User/survey-answer-api/` - Submit survey answers

## AI Integration

### OpenAI Usage
1. **Chatbot**: GPT-4.1-mini for conversational survey interface
2. **Report Generation**: GPT-4.1-mini for creating HTML reports from survey data

### Configuration
- API keys stored in code (security risk - should use environment variables)
- Model: gpt-4.1-mini
- Temperature: 0.0-0.2
- Max tokens: 500-2000

## Security Considerations
- DEBUG=True in development
- Secret key exposed in settings.py
- OpenAI API keys hardcoded
- No HTTPS configuration
- CSRF exemptions on some views

## Deployment
- Static files served via Django
- Media files for PDF reports
- PostgreSQL database
- No production settings configured

## Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure PostgreSQL database

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

5. Run server:
   ```bash
   python manage.py runserver
   ```

## Testing
- Playwright configured for E2E testing
- No unit tests visible in codebase

## Future Improvements
- Move API keys to environment variables
- Implement proper authentication tokens
- Add comprehensive test suite
- Configure production settings
- Implement proper logging
- Add API documentation (DRF browsable API)
- Optimize database queries
- Add caching layer</content>
<parameter name="filePath">d:\ideahive\ideahive\README.md
