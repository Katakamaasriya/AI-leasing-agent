"""
Webhook endpoints for multi-channel lead intake
Handles incoming inquiries from various channels (email, web forms, listing sites)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from sqlalchemy.orm import Session

from .database import get_db
from .models import Lead, Conversation, ConversationMessage
from .services import ingest_normalized_inquiry, log_event
from .email_integration import send_ai_response_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/email/incoming")
async def email_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle incoming email inquiries
    Compatible with SendGrid, Mailgun, and other email providers
    """
    try:
        # Parse email data (format varies by provider)
        data = await request.json()
        
        # Extract common email fields
        sender_email = data.get("sender") or data.get("from") or data.get("email")
        sender_name = data.get("from_name") or sender_email.split("@")[0] if sender_email else "Unknown"
        subject = data.get("subject") or "Property Inquiry"
        body = data.get("text") or data.get("html") or data.get("body") or ""
        
        # Extract property info if available
        property_id = None
        if "property_id" in data:
            property_id = data["property_id"]
        
        # Create lead and conversation
        lead, conversation = ingest_normalized_inquiry(
            db=db,
            name=sender_name,
            contact=sender_email,
            channel="email",
            message=f"Subject: {subject}\n\n{body}",
            property_id=property_id
        )
        
        logger.info(f"Email webhook processed for lead {lead.id} from {sender_email}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message": "Email inquiry processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Email webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process email webhook")


@router.post("/web/inquiry")
async def web_form_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle web form submissions from property websites
    """
    try:
        data = await request.json()
        
        # Extract form fields
        name = data.get("name") or data.get("full_name") or "Web Visitor"
        email = data.get("email") or data.get("email_address")
        phone = data.get("phone") or data.get("phone_number")
        message = data.get("message") or data.get("comments") or "Web form inquiry"
        property_id = data.get("property_id")
        
        # Use email as primary contact, fallback to phone
        contact = email or phone or "web@example.com"
        channel = "email" if email else "phone"
        
        # Create lead
        lead, conversation = ingest_normalized_inquiry(
            db=db,
            name=name,
            contact=contact,
            channel=channel,
            message=message,
            property_id=property_id
        )
        
        logger.info(f"Web form processed for lead {lead.id}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message": "Web inquiry processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Web form webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process web form")


@router.post("/listing-site/{site_name}")
async def listing_site_webhook(
    site_name: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle webhooks from listing sites (Zillow, Apartments.com, etc.)
    """
    try:
        # Verify authorization
        # In production, validate API keys per site
        # if not verify_listing_site_auth(site_name, authorization):
        #     raise HTTPException(status_code=401, detail="Unauthorized")
        
        data = await request.json()
        
        # Extract listing site specific fields
        prospect_name = data.get("prospect_name") or data.get("name") or f"{site_name} Lead"
        prospect_email = data.get("email") or data.get("contact_email")
        prospect_phone = data.get("phone") or data.get("contact_phone")
        property_id = data.get("property_id") or data.get("listing_id")
        message = data.get("message") or data.get("inquiry_text") or f"Inquiry from {site_name}"
        
        # Determine contact method
        contact = prospect_email or prospect_phone or f"{site_name}@example.com"
        channel = "email" if prospect_email else "phone"
        
        # Create lead with listing site context
        lead, conversation = ingest_normalized_inquiry(
            db=db,
            name=prospect_name,
            contact=contact,
            channel=channel,
            message=f"[{site_name}] {message}",
            property_id=property_id
        )
        
        # Log listing site source
        log_event(db, lead.id, "listing_site_inquiry", site=site_name, listing_data=data)
        
        logger.info(f"Listing site webhook processed for {site_name}, lead {lead.id}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message": f"{site_name} inquiry processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Listing site webhook error for {site_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process {site_name} webhook")


@router.post("/sms/incoming")
async def sms_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming SMS messages
    Compatible with Twilio, AWS SNS, etc.
    """
    try:
        data = await request.json()
        
        # Extract SMS fields
        phone_number = data.get("from") or data.get("phone_number") or data.get("sender")
        message_body = data.get("body") or data.get("message") or data.get("text")
        
        # Create lead from SMS
        lead, conversation = ingest_normalized_inquiry(
            db=db,
            name="SMS Prospect",
            contact=phone_number,
            channel="sms",
            message=message_body,
            property_id=None  # May need to be determined from conversation
        )
        
        logger.info(f"SMS webhook processed for lead {lead.id} from {phone_number}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message": "SMS message processed successfully"
        }
        
    except Exception as e:
        logger.error(f"SMS webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process SMS webhook")


@router.post("/chat/widget")
async def chat_widget_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle chat widget messages from website
    """
    try:
        data = await request.json()
        
        # Extract chat data
        visitor_name = data.get("visitor_name") or "Website Visitor"
        visitor_email = data.get("visitor_email")
        message = data.get("message")
        property_id = data.get("property_id")
        session_id = data.get("session_id")
        
        # Use email if provided, otherwise create temporary contact
        contact = visitor_email or f"session_{session_id}@chat.temp"
        channel = "web_chat"
        
        # Create lead
        lead, conversation = ingest_normalized_inquiry(
            db=db,
            name=visitor_name,
            contact=contact,
            channel=channel,
            message=message,
            property_id=property_id
        )
        
        # Log chat session
        log_event(db, lead.id, "chat_widget_message", session_id=session_id)
        
        logger.info(f"Chat widget message processed for lead {lead.id}")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "conversation_id": conversation.id,
            "message": "Chat message processed successfully"
        }
        
    except Exception as e:
        logger.error(f"Chat widget webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat widget message")


@router.post("/lead/update")
async def lead_update_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle lead updates from external systems
    """
    try:
        data = await request.json()
        
        lead_id = data.get("lead_id")
        if not lead_id:
            raise HTTPException(status_code=400, detail="lead_id is required")
        
        lead = db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Update lead fields
        updatable_fields = ["name", "contact", "qualification_status", "human_requested"]
        for field in updatable_fields:
            if field in data:
                setattr(lead, field, data[field])
        
        # Update needs profile if provided
        if "needs_profile" in data:
            lead.needs_profile = data["needs_profile"]
        
        db.commit()
        
        logger.info(f"Lead {lead_id} updated via webhook")
        
        return {
            "success": True,
            "lead_id": lead.id,
            "message": "Lead updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lead update webhook error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update lead")


@router.get("/health")
async def webhook_health():
    """Health check endpoint for webhook monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "webhooks": {
            "email": "active",
            "web_form": "active", 
            "listing_sites": "active",
            "sms": "active",
            "chat_widget": "active",
            "lead_update": "active"
        }
    }