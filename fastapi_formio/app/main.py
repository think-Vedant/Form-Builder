from fastapi import FastAPI, Depends, HTTPException, Request, Body
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import traceback

from . import models
from .database import get_db
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request validation
class FormCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    schema: dict = Field(..., description="Form.io schema")

class FormSubmission(BaseModel):
    data: dict = Field(..., description="Form submission data")

class EmailRequest(BaseModel):
    email: EmailStr
    subject: Optional[str] = "Form to fill"
    message: Optional[str] = "Please fill out this form"

app = FastAPI(title="FastAPI Form.io Builder", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/api/debug/database")
async def debug_database(db: Session = Depends(get_db)):
    try:
        # Check tenants
        tenants = db.query(models.Tenant).all()
        tenant_info = [{"id": t.id, "name": t.name, "domain": t.domain} for t in tenants]
        
        # Check forms
        forms = db.query(models.Form).all()
        form_info = [{"id": f.id, "title": f.title, "tenant_id": f.tenant_id} for f in forms]
        
        result = {
            "default_tenant_id": models.DEFAULT_TENANT_ID,
            "tenants": tenant_info,
            "forms": form_info,
            "database_url": models.SQLALCHEMY_DATABASE_URL
        }
        logger.info(f"Database debug info: {result}")
        return result
    except Exception as e:
        logger.error(f"Database debug error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# API Routes
@app.post("/api/forms/")
async def create_form(form_data: FormCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Creating form with title: {form_data.title}")
        
        # Check if default tenant is available
        if models.DEFAULT_TENANT_ID is None:
            logger.error("Default tenant not available")
            raise HTTPException(status_code=500, detail="Default tenant not initialized")
        
        # Verify tenant exists
        tenant = db.query(models.Tenant).filter(models.Tenant.id == models.DEFAULT_TENANT_ID).first()
        if not tenant:
            logger.error(f"Default tenant with ID {models.DEFAULT_TENANT_ID} not found")
            raise HTTPException(status_code=500, detail="Default tenant not found")
        
        logger.info(f"Using tenant: {tenant.name} (ID: {tenant.id})")
        
        form = models.Form(
            tenant_id=models.DEFAULT_TENANT_ID,
            title=form_data.title,
            description=form_data.description,
            schema=form_data.schema
        )
        db.add(form)
        db.commit()
        db.refresh(form)
        
        logger.info(f"Form created successfully with ID: {form.id}")
        
        return JSONResponse(
            status_code=201,
            content={
                "id": form.id,
                "title": form.title,
                "description": form.description,
                "schema": form.schema,
                "created_at": form.created_at.isoformat(),
                "tenant_id": form.tenant_id
            }
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating form: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/api/forms/{form_id}")
async def update_form(form_id: str, form_data: FormCreate, db: Session = Depends(get_db)):
    try:
        logger.info(f"Updating form with ID: {form_id}")
        
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for update")
            raise HTTPException(status_code=404, detail="Form not found")
        
        # Update form fields
        form.title = form_data.title
        form.description = form_data.description
        form.schema = form_data.schema
        
        db.commit()
        db.refresh(form)
        
        logger.info(f"Form updated successfully with ID: {form.id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "id": form.id,
                "title": form.title,
                "description": form.description,
                "schema": form.schema,
                "created_at": form.created_at.isoformat(),
                "updated_at": form.updated_at.isoformat(),
                "tenant_id": form.tenant_id
            }
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/forms/")
async def list_forms(db: Session = Depends(get_db)):
    try:
        logger.info("Listing all forms")
        forms = db.query(models.Form).all()
        logger.info(f"Found {len(forms)} forms")
        return [
            {
                "id": form.id,
                "title": form.title,
                "description": form.description,
                "created_at": form.created_at.isoformat(),
                "tenant_id": form.tenant_id
            }
            for form in forms
        ]
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/forms/{form_id}")
async def get_form(form_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Getting form with ID: {form_id}")
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found")
            raise HTTPException(status_code=404, detail="Form not found")
        
        logger.info(f"Form found: {form.title}")
        return {
            "id": form.id,
            "title": form.title,
            "description": form.description,
            "schema": form.schema,
            "created_at": form.created_at.isoformat(),
            "tenant_id": form.tenant_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/forms/{form_id}/submit")
async def submit_form(
    form_id: int,
    submission: FormSubmission,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Submitting form {form_id}")
        
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for submission")
            raise HTTPException(status_code=404, detail="Form not found")
        
        logger.info(f"Form found: {form.title}, tenant_id: {form.tenant_id}")
        
        form_submission = models.FormSubmission(
            form_id=form_id,
            tenant_id=form.tenant_id,  # Use the form's tenant_id
            data=submission.data
        )
        db.add(form_submission)
        db.commit()
        db.refresh(form_submission)
        
        logger.info(f"Form submission created with ID: {form_submission.id}")
        
        return JSONResponse(
            status_code=201,
            content={
                "id": form_submission.id,
                "form_id": form_submission.form_id,
                "tenant_id": form_submission.tenant_id,
                "data": form_submission.data,
                "submitted_at": form_submission.submitted_at.isoformat()
            }
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/forms/{form_id}/submissions")
async def get_form_submissions(form_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Getting submissions for form {form_id}")
        
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found")
            raise HTTPException(status_code=404, detail="Form not found")
        
        submissions = db.query(models.FormSubmission).filter(
            models.FormSubmission.form_id == form_id
        ).all()
        
        logger.info(f"Found {len(submissions)} submissions for form {form_id}")
        
        return [
            {
                "id": sub.id,
                "data": sub.data,
                "submitted_at": sub.submitted_at.isoformat(),
                "tenant_id": sub.tenant_id
            }
            for sub in submissions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting submissions for form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/api/forms/{form_id}")
async def delete_form(form_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Deleting form {form_id}")
        
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Form not found")
        
        logger.info(f"Deleting form: {form.title}")
        db.delete(form)
        db.commit()
        
        logger.info(f"Form {form_id} deleted successfully")
        return JSONResponse(
            status_code=200,
            content={"message": "Form deleted successfully"}
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/forms/{form_id}/send-email")
async def send_form_email(
    form_id: int,
    email_request: EmailRequest,
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Sending email for form {form_id} to {email_request.email}")
        
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for email sending")
            raise HTTPException(status_code=404, detail="Form not found")

        # Generate the form URL
        form_url = f"http://localhost:5000/forms/{form_id}"

        # Create email content
        email_content = f"""
        <html>
            <body>
                <h2>Form: {form.title}</h2>
                <p>{email_request.message}</p>
                <p>Please click the link below to fill out the form:</p>
                <a href="{form_url}">{form_url}</a>
            </body>
        </html>
        """

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email_request.subject
        msg['From'] = "your-email@example.com"  # Replace with your email
        msg['To'] = email_request.email
        
        # Add HTML content
        msg.attach(MIMEText(email_content, 'html'))

        # TODO: Configure your SMTP settings
        # smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        # smtp_server.starttls()
        # smtp_server.login('your-email@example.com', 'your-password')
        # smtp_server.send_message(msg)
        # smtp_server.quit()

        logger.info(f"Email prepared for {email_request.email} (SMTP not configured)")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Form link sent to {email_request.email}",
                "form_url": form_url
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email for form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Frontend Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/builder", response_class=HTMLResponse)
async def form_builder(request: Request):
    return templates.TemplateResponse("builder.html", {"request": request})

@app.get("/builder/{form_id}", response_class=HTMLResponse)
async def edit_form_builder(request: Request, form_id: str, db: Session = Depends(get_db)):
    try:
        logger.info(f"Loading form builder for editing form {form_id}")
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for editing")
            raise HTTPException(status_code=404, detail="Form not found")
        
        logger.info(f"Loading form for editing: {form.title}")
        return templates.TemplateResponse(
            "builder.html",
            {"request": request, "form": form, "is_edit": True}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading form builder for form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/forms/{form_id}", response_class=HTMLResponse)
async def render_form(request: Request, form_id: int, db: Session = Depends(get_db)):
    try:
        logger.info(f"Rendering form {form_id}")
        form = db.query(models.Form).filter(models.Form.id == form_id).first()
        if not form:
            logger.warning(f"Form with ID {form_id} not found for rendering")
            raise HTTPException(status_code=404, detail="Form not found")
        
        logger.info(f"Rendering form: {form.title}")
        return templates.TemplateResponse(
            "form.html",
            {"request": request, "form": form}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering form {form_id}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 