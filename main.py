from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import json
import os
from datetime import datetime
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Replace with your production frontend URL
    ],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Get token from environment variable
API_TOKEN = os.getenv("ACCESS_TOKEN")
if not API_TOKEN:
    raise ValueError("ACCESS_TOKEN not found in environment variables")

def validate_token(authorization: str = Header(None)):
    """Validate the authorization token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    
    # Check if the token matches (Bearer token format)
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format. Use 'Bearer <token>'")
    
    token = authorization.replace("Bearer ", "")
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return token

# Pydantic model for contact request (without createdAt and id as they will be auto-generated)
class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str
    phone: Optional[str] = None
    company: Optional[str] = None
    isDeleted: bool = False

# Pydantic model for contact response (includes createdAt)
class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    phone: Optional[str] = None
    company: Optional[str] = None
    createdAt: str
    isDeleted: bool

# File path for storing contacts
CONTACTS_FILE = "contacts.json"

def load_contacts():
    """Load existing contacts from JSON file"""
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_contacts(contacts):
    """Save contacts to JSON file"""
    with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)

@app.get("/hello")
async def hello():
    return {"message": "Hello! from Nitesh"}

@app.post("/api/contact", response_model=ContactResponse)
async def create_contact(contact: ContactRequest, token: str = Depends(validate_token)):
    """Create a new contact and save to JSON file"""
    try:
        # Load existing contacts
        contacts = load_contacts()
        
        # Generate next ID (max existing ID + 1, or 1 if no contacts exist)
        next_id = 1
        if contacts:
            next_id = max(c["id"] for c in contacts) + 1
        
        # Generate current timestamp in readable format
        current_time = datetime.now().isoformat()
        
        # Create contact with auto-generated id and createdAt field
        contact_data = contact.model_dump()
        contact_data["id"] = next_id
        contact_data["createdAt"] = current_time
        
        # Add new contact
        contacts.append(contact_data)
        
        # Save to file
        save_contacts(contacts)
        
        return ContactResponse(**contact_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving contact: {str(e)}")

@app.get("/api/contacts", response_model=list[ContactResponse])
async def get_contacts(token: str = Depends(validate_token)):
    """Get all contacts from JSON file"""
    try:
        contacts = load_contacts()
        return [ContactResponse(**contact) for contact in contacts]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading contacts: {str(e)}")

@app.delete("/api/contacts")
async def delete_all_contacts(token: str = Depends(validate_token)):
    """Delete all contacts"""
    try:
        contacts = load_contacts()
        
        if not contacts:
            return {"message": "No contacts to delete", "deleted_count": 0}
        
        # Store the count and contacts for response
        deleted_count = len(contacts)
        deleted_contacts = contacts.copy()
        
        # Clear all contacts
        contacts.clear()
        
        # Save the empty contacts list
        save_contacts(contacts)
        
        return {
            "message": f"All {deleted_count} contacts deleted successfully",
            "deleted_count": deleted_count,
            "deleted_contacts": deleted_contacts
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting contacts: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)