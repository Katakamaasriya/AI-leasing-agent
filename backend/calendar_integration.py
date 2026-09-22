"""
Microsoft 365 Calendar Integration for Tour Scheduling
This module handles integration with Microsoft Graph API for calendar operations
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import requests

from msal import ConfidentialClientApplication

logger = logging.getLogger(__name__)

# Microsoft 365 Configuration
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID")
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")

# Graph API endpoints
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftCalendarClient:
    """Client for Microsoft 365 Calendar operations via Graph API"""
    
    def __init__(self):
        self.app = None
        self.access_token = None
        self.token_expires = None
        
        if all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
            self._initialize_app()
        else:
            logger.warning("Microsoft 365 credentials not configured, calendar integration disabled")
    
    def _initialize_app(self):
        """Initialize MSAL application"""
        try:
            self.app = ConfidentialClientApplication(
                client_id=CLIENT_ID,
                authority=f"https://login.microsoftonline.com/{TENANT_ID}",
                client_credential=CLIENT_SECRET
            )
            logger.info("Microsoft 365 calendar client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Microsoft 365 client: {e}")
    
    def _get_access_token(self) -> Optional[str]:
        """Get or refresh access token"""
        if not self.app:
            return None
            
        try:
            # Check if token is still valid
            if self.access_token and self.token_expires and datetime.now() < self.token_expires:
                return self.access_token
            
            # Get new token
            result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                # Token expires in expires_in seconds (typically 3600)
                self.token_expires = datetime.now() + timedelta(seconds=result.get("expires_in", 3600) - 300)
                logger.info("Successfully obtained Microsoft 365 access token")
                return self.access_token
            else:
                logger.error(f"Failed to get access token: {result.get('error_description')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    def _make_graph_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """Make authenticated request to Microsoft Graph API"""
        token = self._get_access_token()
        if not token:
            return None
            
        try:
            url = f"{GRAPH_API_BASE}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Graph API request failed: {e}")
            return None
    
    def check_availability(self, calendar_id: str, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Check calendar availability for a time slot"""
        try:
            # Format times for Graph API
            start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%S")
            end_iso = end_time.strftime("%Y-%m-%dT%H:%M:%S")
            
            schedule_request = {
                "schedules": [calendar_id],
                "startTime": {
                    "dateTime": start_iso,
                    "timeZone": "UTC"
                },
                "endTime": {
                    "dateTime": end_iso,
                    "timeZone": "UTC"
                },
                "availabilityViewInterval": 60  # 60-minute intervals
            }
            
            result = self._make_graph_request(
                "POST",
                "me/calendar/getSchedule",
                data=schedule_request
            )
            
            if result and len(result.get("value", [])) > 0:
                schedule_info = result["value"][0]
                availability_view = schedule_info.get("availabilityView", "")
                
                # Check if the slot is free (0 = free, 1 = tentative, 2 = busy, 3 = out of office, 4 = working elsewhere)
                is_available = all(char == '0' for char in availability_view)
                
                return {
                    "available": is_available,
                    "availability_view": availability_view,
                    "schedule_id": schedule_info.get("scheduleId")
                }
            
            return {"available": False, "error": "Could not check availability"}
            
        except Exception as e:
            logger.error(f"Error checking calendar availability: {e}")
            return {"available": False, "error": str(e)}
    
    def create_event(self, calendar_id: str, subject: str, start_time: datetime, end_time: datetime, 
                    body: str, attendees: Optional[List[str]] = None, location: Optional[str] = None) -> Dict[str, Any]:
        """Create a calendar event"""
        try:
            event_data = {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "start": {
                    "dateTime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "timeZone": "UTC"
                }
            }
            
            if location:
                event_data["location"] = {
                    "displayName": location
                }
            
            if attendees:
                event_data["attendees"] = [
                    {
                        "emailAddress": {
                            "address": email,
                            "name": email.split("@")[0]
                        },
                        "type": "required"
                    }
                    for email in attendees
                ]
            
            result = self._make_graph_request(
                "POST",
                f"users/{calendar_id}/calendar/events",
                data=event_data
            )
            
            if result:
                logger.info(f"Successfully created calendar event: {subject}")
                return {
                    "success": True,
                    "event_id": result.get("id"),
                    "web_link": result.get("webLink")
                }
            
            return {"success": False, "error": "Failed to create event"}
            
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {"success": False, "error": str(e)}
    
    def get_free_slots(self, calendar_id: str, start_date: datetime, end_date: datetime, 
                      duration_minutes: int = 30) -> List[Dict[str, Any]]:
        """Get available time slots for a date range"""
        try:
            # Get calendar view for the date range
            start_iso = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            end_iso = end_date.strftime("%Y-%m-%dT%H:%M:%S")
            
            result = self._make_graph_request(
                "GET",
                f"users/{calendar_id}/calendar/calendarView?startDateTime={start_iso}&endDateTime={end_iso}"
            )
            
            if not result:
                return []
            
            existing_events = result.get("value", [])
            
            # Generate potential slots (9 AM - 6 PM, Monday - Saturday)
            available_slots = []
            current_date = start_date.date()
            end_date_obj = end_date.date()
            
            while current_date <= end_date_obj:
                # Skip Sunday
                if current_date.weekday() != 6:  # 6 = Sunday
                    # Generate slots from 9 AM to 6 PM
                    slot_start = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=9)
                    slot_end = slot_start + timedelta(minutes=duration_minutes)
                    day_end = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=18)
                    
                    while slot_end <= day_end:
                        # Check if slot conflicts with existing events
                        slot_available = True
                        for event in existing_events:
                            event_start = datetime.fromisoformat(event["start"]["dateTime"].replace('Z', '+00:00'))
                            event_end = datetime.fromisoformat(event["end"]["dateTime"].replace('Z', '+00:00'))
                            
                            # Check for overlap
                            if not (slot_end <= event_start or slot_start >= event_end):
                                slot_available = False
                                break
                        
                        if slot_available:
                            available_slots.append({
                                "start": slot_start,
                                "end": slot_end,
                                "duration_minutes": duration_minutes
                            })
                        
                        slot_start = slot_end
                        slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                current_date += timedelta(days=1)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error getting free slots: {e}")
            return []


# Global calendar client instance
calendar_client = MicrosoftCalendarClient()


def check_calendar_availability_365(calendar_email: str, start_time: datetime, 
                                   end_time: datetime) -> Dict[str, Any]:
    """Check Microsoft 365 calendar availability"""
    return calendar_client.check_availability(calendar_email, start_time, end_time)


def create_tour_event_365(calendar_email: str, prospect_name: str, prospect_email: str,
                          property_name: str, address: str, start_time: datetime, 
                          duration_minutes: int = 30) -> Dict[str, Any]:
    """Create a tour event in Microsoft 365 calendar"""
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    subject = f"Property Tour: {property_name} - {prospect_name}"
    body = f"""
    <h2>Property Tour Scheduled</h2>
    <p><strong>Prospect:</strong> {prospect_name} ({prospect_email})</p>
    <p><strong>Property:</strong> {property_name}</p>
    <p><strong>Address:</strong> {address}</p>
    <p><strong>Time:</strong> {start_time.strftime('%A, %B %d, %Y at %I:%M %p')}</p>
    <p><em>Please bring ID and proof of income for qualification.</em></p>
    """
    
    return calendar_client.create_event(
        calendar_id=calendar_email,
        subject=subject,
        start_time=start_time,
        end_time=end_time,
        body=body,
        attendees=[prospect_email] if prospect_email else None,
        location=address
    )


def get_available_tour_slots_365(calendar_email: str, days_ahead: int = 7, 
                                duration_minutes: int = 30) -> List[Dict[str, Any]]:
    """Get available tour slots for the next N days"""
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days_ahead)
    
    return calendar_client.get_free_slots(calendar_email, start_date, end_date, duration_minutes)