# FastAPI Form.io Integration

This project integrates Form.io's form builder and renderer with FastAPI backend, using SQLite for data storage.

## Features

- Create dynamic forms using Form.io's form builder
- Store form definitions in SQLite database
- Render forms for end-users
- Collect and store form submissions
- View form submissions

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Setup

1. Clone the repository and navigate to the project directory:

```bash
cd fastapi_formio
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

2. Open your web browser and navigate to:
   - http://localhost:5000 - Home page with list of forms
   - http://localhost:5000/builder - Create new forms
   - http://localhost:5000/forms/{form_id} - View and submit specific forms

## API Endpoints

- `GET /api/forms/` - List all forms
- `POST /api/forms/` - Create a new form
- `GET /api/forms/{form_id}` - Get a specific form
- `POST /api/forms/{form_id}/submit` - Submit form data
- `GET /api/forms/{form_id}/submissions` - Get form submissions

## Project Structure

```
fastapi_formio/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   └── database.py
├── static/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── builder.html
│   └── form.html
├── requirements.txt
└── README.md
```

## Database

The application uses SQLite as the database. The database file (`formio.db`) will be created automatically when you run the application for the first time.

## Contributing

Feel free to submit issues and enhancement requests! 