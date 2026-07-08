# TestForge AI — AI QA Test Case Generator

TestForge AI is a full-stack AI-powered QA test case generation platform. It helps QA engineers, developers, students, and software teams convert software requirements, user stories, and SRS documents into structured, editable, and export-ready test cases.

The project is designed as a practical QA workflow tool, not just a simple AI demo. Users can create projects, upload requirement documents, generate test cases using local or cloud LLMs, edit generated test cases, view analytics, export reports, and generate Playwright automation scaffolds.

---

## Key Features

### 1. User Authentication

- User signup
- User login
- Token-based authentication
- User-specific projects and test cases
- Protected backend routes

Each user can manage their own QA projects and generated test case history.

---

### 2. Project Dashboard

Users can create and manage different QA projects from the dashboard.

Example projects:

- E-commerce Website QA
- Banking App QA
- Hospital Management System QA
- CRM Workflow Testing
- AI Chatbot QA

Project dashboard features include:

- Create new project
- View all saved projects
- Select active project
- Delete old projects
- View project-based QA analytics

---

### 3. AI Test Case Generator

The core feature of the application is AI-based test case generation.

Users can enter:

- Module name
- Requirement title
- Requirement description
- User story
- Test case count
- Required test types

The system generates structured QA test cases with:

- Test case title
- Test type
- Priority
- Severity
- Preconditions
- Test steps
- Test data
- Expected result

Supported test case categories include:

- Functional testing
- Negative testing
- Boundary testing
- Validation testing
- UI testing
- API testing
- Security testing
- Performance testing

---

### 4. Ollama Local LLM Support

TestForge AI supports local LLM execution using Ollama.

Supported local models include:

- Llama 3.1
- Mistral
- Any other model available through Ollama

This allows the project to run without relying only on paid AI APIs.

Example Ollama setup:

```bash
ollama pull llama3.1:8b
```

or:

```bash
ollama pull mistral
```

Backend `.env` configuration for Ollama:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

### 5. Optional OpenAI Support

The project also supports OpenAI as an optional AI provider.

Example `.env` configuration:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

If an OpenAI API key is provided, the backend can use OpenAI to generate more refined test cases.

---

### 6. Fallback Generator

If no AI provider is available, the project uses a fallback generator.

The fallback generator is a local template-based system that creates basic demo test cases. It is useful for testing the UI, dashboard, exports, charts, and project flow without requiring an API key or local LLM.

AI engine priority in auto mode:

1. OpenAI, if API key is available
2. Ollama, if local Ollama is running
3. Fallback generator, if no LLM is available

Example `.env` setting:

```env
LLM_PROVIDER=auto
```

---

### 7. AI Engine Status Panel

The dashboard includes an AI engine status panel that shows which generation mode is currently active.

Possible statuses:

- OpenAI active
- Ollama active
- Fallback generator active
- LLM unavailable

This makes the system transparent and easier to debug during development.

---

### 8. SRS / Document Upload

Users can upload requirement documents and use the extracted text to generate test cases.

Supported file types:

- PDF
- DOCX
- TXT
- SRS documents

Upload workflow:

1. User uploads a requirement document
2. Backend extracts readable text
3. User reviews or uses the extracted text
4. AI generates test cases from the document content

This feature makes the tool more useful for real QA documentation workflows.

---

### 9. Editable Test Case Table

Generated test cases are displayed in an editable table.

Users can review and update:

- Title
- Test type
- Priority
- Severity
- Preconditions
- Steps
- Test data
- Expected result

Additional actions include:

- Save updates
- Delete test cases
- Duplicate test cases
- Approve or review generated cases
- Search and filter test cases

This allows QA engineers to refine AI-generated output before exporting or using it.

---

### 10. Delete History Feature

The project includes history management features.

Users can:

- Delete selected requirement history
- Delete generated test cases
- Clear all generated history
- Keep projects while removing previous test case data
- Delete complete projects when no longer needed

This keeps the dashboard clean and helps users manage older test data.

---

### 11. QA Analytics Dashboard

The dashboard includes analytics to make the project more professional and visually attractive.

Analytics include:

- Total projects
- Total requirements
- Total generated test cases
- Test cases by type
- Test cases by priority
- Test cases by severity
- QA coverage score

---

### 12. Pie Charts and Visual Reports

The application includes chart-based visual analytics.

Pie charts help show:

- Test type distribution
- Priority distribution
- Severity distribution
- QA coverage balance

These charts make the tool more attractive for customers, clients, and portfolio presentation.

---

### 13. Export Options

Users can export generated test cases in multiple formats.

Supported exports:

- CSV
- Excel
- PDF
- Jira-style CSV
- Playwright `.spec.ts` scaffold

These export options make the tool useful for QA documentation, client reports, team handovers, and test automation planning.

---

### 14. Jira-Style CSV Export

The Jira CSV export creates a format that can be used for Jira-style issue or task imports.

Exported columns can include:

- Issue type
- Summary
- Description
- Priority
- Labels
- Test steps
- Expected result

This helps QA teams move generated test cases into project management workflows.

---

### 15. Playwright Automation Script Generator

The project can generate Playwright test scaffold files from manual test cases.

The generated file includes:

- Test case structure
- Playwright `test()` blocks
- TODO comments for selectors
- Expected result placeholders

Because the system does not know the exact UI selectors of every website, it generates a clean automation starting point that developers can complete.

Example output:

```ts
import { test, expect } from '@playwright/test';

test('Verify user login with valid credentials', async ({ page }) => {
  // TODO: Navigate to the login page
  // TODO: Fill email and password fields
  // TODO: Click login button
  // TODO: Add assertion for successful login
});
```

---

## Tech Stack

### Backend

- Python
- FastAPI
- SQLite
- SQLModel / SQLAlchemy style database models
- JWT/token-based authentication
- Python document parsing libraries
- Export generation libraries

### Frontend

- HTML
- CSS
- JavaScript
- Dashboard-style UI
- Editable tables
- Chart components

### AI / LLM

- Ollama local LLM support
- Llama 3.1 support
- Mistral support
- Optional OpenAI support
- Local fallback generator

### Reports and Automation

- CSV export
- Excel export
- PDF export
- Jira CSV export
- Playwright scaffold export

---

## Project Folder Structure

```text
testforge-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── requirements.py
│   │   │   ├── test_cases.py
│   │   │   ├── analytics.py
│   │   │   ├── exports.py
│   │   │   └── history.py
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── ollama_service.py
│   │   │   ├── openai_service.py
│   │   │   ├── fallback_service.py
│   │   │   ├── export_service.py
│   │   │   └── document_service.py
│   │   └── static/
│   │       ├── index.html
│   │       ├── styles.css
│   │       └── app.js
│   ├── requirements.txt
│   ├── .env.example
│   └── qa_generator.db
└── README.md
```

---

## How to Run the Project

### 1. Extract the ZIP File

Extract the project ZIP file and open the extracted folder in VS Code.

---

### 2. Open Backend Folder

```bash
cd backend
```

---

### 3. Create Virtual Environment

For Windows:

```bash
py -3.11 -m venv .venv
```

If the above command does not work, use:

```bash
python -m venv .venv
```

---

### 4. Activate Virtual Environment

For Windows PowerShell:

```bash
.venv\Scripts\activate
```

After activation, the terminal should show:

```text
(.venv)
```

---

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 6. Create Environment File

```bash
copy .env.example .env
```

---

### 7. Configure LLM Provider

To use Ollama:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

To use OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

To automatically choose the available provider:

```env
LLM_PROVIDER=auto
```

---

### 8. Run Ollama Model

Install Ollama, then pull a model:

```bash
ollama pull llama3.1:8b
```

or:

```bash
ollama pull mistral
```

Check installed models:

```bash
ollama list
```

---

### 9. Start FastAPI Backend

```bash
uvicorn app.main:app --reload
```

The backend should start at:

```text
http://127.0.0.1:8000
```

Open this URL in your browser.

---

## How to Use the Application

1. Sign up or log in
2. Create a QA project
3. Select the project from the dashboard
4. Enter module name and requirement details
5. Select test case types
6. Choose number of test cases
7. Generate and save test cases
8. Review and edit generated test cases
9. View dashboard analytics and pie charts
10. Export test cases as CSV, Excel, PDF, Jira CSV, or Playwright script
11. Delete old history or remove projects when needed

---

## Example Requirement Input

```text
Feature: User Login

The system should allow registered users to log in using email and password.
Email must be in a valid format.
Password field should be masked.
Empty fields should show validation messages.
After 5 failed login attempts, the account should be locked for 15 minutes.
Successful login should redirect the user to the dashboard.
```

Example generated test cases:

- Verify login with valid credentials
- Verify login with invalid password
- Verify login with empty email field
- Verify email format validation
- Verify password masking
- Verify account lock after 5 failed attempts
- Verify successful redirect to dashboard

---

## Backend Logic Overview

When a user generates test cases, the backend follows this flow:

```text
User enters requirement
        ↓
Frontend sends request to FastAPI
        ↓
FastAPI checks selected LLM provider
        ↓
Backend sends prompt to Ollama/OpenAI/fallback generator
        ↓
Generated test cases are returned as structured data
        ↓
Backend validates and saves test cases in SQLite
        ↓
Frontend displays the results in tables and charts
```

---

## Environment Variables

Example `.env` file:

```env
DATABASE_URL=sqlite:///./qa_generator.db
SECRET_KEY=change-this-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

LLM_PROVIDER=auto

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## Why This Project Is Useful

Writing test cases manually can take a lot of time, especially when requirements are long or unclear. TestForge AI speeds up the QA documentation process by generating structured test cases from requirements and documents.

It is useful for:

- QA engineers
- Manual testers
- Automation testers
- Software developers
- Freelancers
- Students
- Software houses
- Startup teams

---

## Future Improvements

Possible future features:

- Full React frontend
- PostgreSQL database
- Team collaboration
- Role-based access control
- Direct Jira API integration
- GitHub Issues integration
- TestRail integration
- Advanced requirement coverage scoring
- AI-based duplicate test case detection
- AI-based missing test case suggestions
- Fully runnable Playwright automation generation
- Docker deployment
- Cloud deployment on Azure, Render, or Railway

---

## Project Summary

TestForge AI is a practical AI-powered QA platform that converts requirements and SRS documents into structured test cases. It supports local LLMs through Ollama, optional OpenAI integration, editable test case management, project dashboards, analytics, pie charts, document uploads, history deletion, and multiple export formats.

The goal of the project is to make QA documentation faster, cleaner, and easier to manage while also providing a strong portfolio-level full-stack AI application.

---

## Author

**RAYYAN HUSSAIN**

Aspiring Web Developer | AI Automation Learner  | Building Modern & Responsive Websites, Chatbots and Digital Solutions | Skilled in HTML, CSS, Java Script, Python | Open to Projects & Collaborations.

---

 ## License

>This project is open-source and available for learning, portfolio, and development purposes.


