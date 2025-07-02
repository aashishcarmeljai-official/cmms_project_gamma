import os
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
from googletrans import Translator
from models import db, WhatsAppUser, WhatsAppMessage, WhatsAppTemplate, NotificationLog, WorkOrder, User, Equipment, MaintenanceSchedule, EmergencyBroadcast
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsAppIntegration:
    """WhatsApp Business API Integration for CMMS"""
    
    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.verify_token = os.getenv('WHATSAPP_VERIFY_TOKEN')
        self.base_url = "https://graph.facebook.com/v18.0"
        self.translator = Translator()
        
        if not all([self.access_token, self.phone_number_id]):
            logger.warning("WhatsApp credentials not configured. WhatsApp features will be disabled.")
    
    def send_message(self, phone_number: str, message: str, message_type: str = 'text', 
                    media_url: str = None, template_id: str = None, template_variables: Dict = None) -> Dict:
        """Send WhatsApp message"""
        if not self.access_token or not self.phone_number_id:
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            if template_id and template_variables:
                # Send template message
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': phone_number,
                    'type': 'template',
                    'template': {
                        'name': template_id,
                        'language': {
                            'code': 'en'
                        },
                        'components': []
                    }
                }
                
                # Add variables if provided
                if template_variables:
                    components = []
                    for key, value in template_variables.items():
                        components.append({
                            'type': 'body',
                            'parameters': [{'type': 'text', 'text': str(value)}]
                        })
                    payload['template']['components'] = components
                    
            elif message_type == 'text':
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': phone_number,
                    'type': 'text',
                    'text': {'body': message}
                }
            elif message_type in ['image', 'video', 'audio', 'document']:
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': phone_number,
                    'type': message_type,
                    message_type: {
                        'link': media_url,
                        'caption': message if message else None
                    }
                }
            else:
                return {'success': False, 'error': 'Unsupported message type'}
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                return {'success': True, 'message_id': response_data.get('messages', [{}])[0].get('id')}
            else:
                logger.error(f"WhatsApp API error: {response_data}")
                return {'success': False, 'error': response_data.get('error', {}).get('message', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def send_interactive_message(self, phone_number: str, message: str, buttons: List[Dict]) -> Dict:
        """Send interactive message with buttons"""
        if not self.access_token or not self.phone_number_id:
            return {'success': False, 'error': 'WhatsApp not configured'}
        
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'messaging_product': 'whatsapp',
                'to': phone_number,
                'type': 'interactive',
                'interactive': {
                    'type': 'button',
                    'body': {'text': message},
                    'action': {
                        'buttons': buttons
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            
            if response.status_code == 200:
                return {'success': True, 'message_id': response_data.get('messages', [{}])[0].get('id')}
            else:
                logger.error(f"WhatsApp API error: {response_data}")
                return {'success': False, 'error': response_data.get('error', {}).get('message', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"Error sending interactive WhatsApp message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def translate_message(self, message: str, target_language: str) -> str:
        """Translate message to target language"""
        try:
            if target_language == 'en':
                return message
            
            translation = self.translator.translate(message, dest=target_language)
            return translation.text
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return message
    
    def notify_work_order_assignment(self, work_order: WorkOrder) -> bool:
        """Send WhatsApp notification for new work order assignment"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        # Translate message based on user's preferred language
        message = f"🔧 New Work Order Assigned\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\nPriority: {work_order.priority.title()}\nDescription: {work_order.description[:100]}..."
        
        translated_message = self.translate_message(message, whatsapp_user.preferred_language)
        
        # Create interactive buttons
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': f'wo_start_{work_order.id}',
                    'title': 'Start Work'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': f'wo_view_{work_order.id}',
                    'title': 'View Details'
                }
            }
        ]
        
        result = self.send_interactive_message(whatsapp_user.whatsapp_number, translated_message, buttons)
        
        # Log the notification
        notification = NotificationLog(
            notification_type='whatsapp',
            recipient_id=work_order.assigned_technician.id,
            recipient_whatsapp_id=whatsapp_user.id,
            subject='New Work Order Assignment',
            content=translated_message,
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error'),
            work_order_id=work_order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return result['success']
    
    def notify_priority_escalation(self, work_order: WorkOrder, old_priority: str) -> bool:
        """Send WhatsApp notification for priority escalation"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        message = f"🚨 Priority Escalated\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\nPriority: {old_priority.title()} → {work_order.priority.title()}\nPlease prioritize this work order."
        
        translated_message = self.translate_message(message, whatsapp_user.preferred_language)
        
        result = self.send_message(whatsapp_user.whatsapp_number, translated_message)
        
        # Log the notification
        notification = NotificationLog(
            notification_type='whatsapp',
            recipient_id=work_order.assigned_technician.id,
            recipient_whatsapp_id=whatsapp_user.id,
            subject='Work Order Priority Escalated',
            content=translated_message,
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error'),
            work_order_id=work_order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return result['success']
    
    def notify_parts_delivery(self, work_order: WorkOrder, parts: List[str]) -> bool:
        """Send WhatsApp notification for parts delivery"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        parts_list = '\n'.join([f"• {part}" for part in parts])
        message = f"📦 Parts Delivered\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\n\nDelivered Parts:\n{parts_list}\n\nYou can now proceed with the repair."
        
        translated_message = self.translate_message(message, whatsapp_user.preferred_language)
        
        result = self.send_message(whatsapp_user.whatsapp_number, translated_message)
        
        # Log the notification
        notification = NotificationLog(
            notification_type='whatsapp',
            recipient_id=work_order.assigned_technician.id,
            recipient_whatsapp_id=whatsapp_user.id,
            subject='Parts Delivered',
            content=translated_message,
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error'),
            work_order_id=work_order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return result['success']
    
    def send_maintenance_reminder(self, maintenance_schedule: MaintenanceSchedule) -> bool:
        """Send WhatsApp reminder for scheduled maintenance"""
        if not maintenance_schedule.assigned_team:
            return False
        
        # Get all team members with WhatsApp
        team_members = maintenance_schedule.assigned_team.members
        success_count = 0
        
        for member in team_members:
            whatsapp_user = WhatsAppUser.query.filter_by(user_id=member.id).first()
            if not whatsapp_user or not whatsapp_user.is_verified:
                continue
            
            message = f"📅 Maintenance Reminder\n\nEquipment: {maintenance_schedule.equipment.name}\nTask: {maintenance_schedule.description}\nDue: {maintenance_schedule.next_due.strftime('%Y-%m-%d %H:%M')}"
            
            translated_message = self.translate_message(message, whatsapp_user.preferred_language)
            
            # Create interactive buttons
            buttons = [
                {
                    'type': 'reply',
                    'reply': {
                        'id': f'maint_done_{maintenance_schedule.id}',
                        'title': 'Mark as Done'
                    }
                },
                {
                    'type': 'reply',
                    'reply': {
                        'id': f'maint_schedule_{maintenance_schedule.id}',
                        'title': 'Reschedule'
                    }
                }
            ]
            
            result = self.send_interactive_message(whatsapp_user.whatsapp_number, translated_message, buttons)
            
            if result['success']:
                success_count += 1
            
            # Log the notification
            notification = NotificationLog(
                notification_type='whatsapp',
                recipient_id=member.id,
                recipient_whatsapp_id=whatsapp_user.id,
                subject='Maintenance Reminder',
                content=translated_message,
                status='sent' if result['success'] else 'failed',
                error_message=result.get('error'),
                maintenance_schedule_id=maintenance_schedule.id
            )
            db.session.add(notification)
        
        db.session.commit()
        return success_count > 0
    
    def send_emergency_broadcast(self, emergency: EmergencyBroadcast) -> bool:
        """Send emergency broadcast to all technicians"""
        try:
            # Get all active technicians with WhatsApp
            if emergency.recipients == 'all':
                whatsapp_users = WhatsAppUser.query.filter_by(is_active=True).all()
            else:
                recipient_ids = json.loads(emergency.recipients)
                whatsapp_users = WhatsAppUser.query.filter(
                    WhatsAppUser.user_id.in_(recipient_ids),
                    WhatsAppUser.is_active == True
                ).all()
            
            success_count = 0
            
            for whatsapp_user in whatsapp_users:
                if not whatsapp_user.is_verified:
                    continue
                
                message = f"🚨 EMERGENCY: {emergency.title}\n\n{emergency.message}\n\nPriority: {emergency.priority.upper()}"
                
                translated_message = self.translate_message(message, whatsapp_user.preferred_language)
                
                result = self.send_message(whatsapp_user.whatsapp_number, translated_message)
                
                if result['success']:
                    success_count += 1
                
                # Log the notification
                notification = NotificationLog(
                    notification_type='whatsapp',
                    recipient_id=whatsapp_user.user_id,
                    recipient_whatsapp_id=whatsapp_user.id,
                    subject=f'EMERGENCY: {emergency.title}',
                    content=translated_message,
                    status='sent' if result['success'] else 'failed',
                    error_message=result.get('error')
                )
                db.session.add(notification)
            
            db.session.commit()
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending emergency broadcast: {str(e)}")
            return False
    
    def notify_stakeholders(self, work_order: WorkOrder, event_type: str) -> bool:
        """Notify external stakeholders about work order events"""
        # This would typically involve getting stakeholder contact info from a separate table
        # For now, we'll implement a basic version
        
        message_templates = {
            'created': f"Work Order #{work_order.work_order_number} has been created for {work_order.equipment.name}",
            'started': f"Work Order #{work_order.work_order_number} has started at {datetime.now().strftime('%I:%M %p')}",
            'completed': f"Work Order #{work_order.work_order_number} has been completed at {datetime.now().strftime('%I:%M %p')}"
        }
        
        message = message_templates.get(event_type, f"Work Order #{work_order.work_order_number} status updated")
        
        # In a real implementation, you would get stakeholder contacts from database
        # For now, we'll return True as placeholder
        return True
    
    def process_incoming_message(self, data: Dict) -> Dict:
        """Process incoming WhatsApp message webhook"""
        try:
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return {'success': True, 'message': 'No messages to process'}
            
            message = messages[0]
            phone_number = message.get('from')
            message_type = message.get('type')
            timestamp = message.get('timestamp')
            
            # Find WhatsApp user
            whatsapp_user = WhatsAppUser.query.filter_by(whatsapp_number=phone_number).first()
            if not whatsapp_user:
                return {'success': False, 'error': 'WhatsApp user not found'}
            
            # Process different message types
            if message_type == 'text':
                content = message.get('text', {}).get('body', '')
                self._process_text_message(whatsapp_user, content, timestamp)
                
            elif message_type == 'image':
                media_id = message.get('image', {}).get('id')
                caption = message.get('image', {}).get('caption', '')
                self._process_media_message(whatsapp_user, 'image', media_id, caption, timestamp)
                
            elif message_type == 'video':
                media_id = message.get('video', {}).get('id')
                caption = message.get('video', {}).get('caption', '')
                self._process_media_message(whatsapp_user, 'video', media_id, caption, timestamp)
                
            elif message_type == 'interactive':
                self._process_interactive_message(whatsapp_user, message, timestamp)
            
            return {'success': True, 'message': 'Message processed successfully'}
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_text_message(self, whatsapp_user: WhatsAppUser, content: str, timestamp: int):
        """Process incoming text message"""
        # Check for commands
        if content.lower().startswith('/wo'):
            self._handle_work_order_command(whatsapp_user, content)
        elif content.lower().startswith('/status'):
            self._handle_status_command(whatsapp_user, content)
        elif content.lower().startswith('/help'):
            self._send_help_message(whatsapp_user)
        else:
            # Store as regular message
            message = WhatsAppMessage(
                whatsapp_user_id=whatsapp_user.id,
                message_type='text',
                direction='inbound',
                content=content
            )
            db.session.add(message)
            db.session.commit()
    
    def _process_media_message(self, whatsapp_user: WhatsAppUser, media_type: str, media_id: str, 
                              caption: str, timestamp: int):
        """Process incoming media message"""
        # Download media and store
        media_url = self._download_media(media_id)
        
        message = WhatsAppMessage(
            whatsapp_user_id=whatsapp_user.id,
            message_type=media_type,
            direction='inbound',
            content=caption or '',
            media_url=media_url,
            media_type=media_type
        )
        db.session.add(message)
        db.session.commit()
    
    def _process_interactive_message(self, whatsapp_user: WhatsAppUser, message: Dict, timestamp: int):
        """Process interactive message (button responses)"""
        interactive = message.get('interactive', {})
        button_response = interactive.get('button_reply', {})
        button_id = button_response.get('id', '')
        
        # Process button actions
        if button_id.startswith('wo_start_'):
            work_order_id = int(button_id.split('_')[2])
            self._handle_start_work_order(whatsapp_user, work_order_id)
        elif button_id.startswith('wo_view_'):
            work_order_id = int(button_id.split('_')[2])
            self._handle_view_work_order(whatsapp_user, work_order_id)
        elif button_id.startswith('maint_done_'):
            schedule_id = int(button_id.split('_')[2])
            self._handle_mark_maintenance_done(whatsapp_user, schedule_id)
        elif button_id.startswith('maint_schedule_'):
            schedule_id = int(button_id.split('_')[2])
            self._handle_reschedule_maintenance(whatsapp_user, schedule_id)
    
    def _handle_work_order_command(self, whatsapp_user: WhatsAppUser, content: str):
        """Handle work order related commands"""
        parts = content.split()
        if len(parts) < 2:
            self.send_message(whatsapp_user.whatsapp_number, "Usage: /wo <work_order_number>")
            return
        
        work_order_number = parts[1]
        work_order = WorkOrder.query.filter_by(work_order_number=work_order_number).first()
        
        if not work_order:
            self.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} not found.")
            return
        
        # Check if user is assigned to this work order
        if work_order.assigned_technician_id != whatsapp_user.user_id:
            self.send_message(whatsapp_user.whatsapp_number, "You are not assigned to this work order.")
            return
        
        # Send work order details
        message = f"🔧 Work Order Details\n\nNumber: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\nStatus: {work_order.status.title()}\nPriority: {work_order.priority.title()}\nDescription: {work_order.description}"
        
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': f'wo_start_{work_order.id}',
                    'title': 'Start Work'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': f'wo_complete_{work_order.id}',
                    'title': 'Mark Complete'
                }
            }
        ]
        
        self.send_interactive_message(whatsapp_user.whatsapp_number, message, buttons)
    
    def _handle_status_command(self, whatsapp_user: WhatsAppUser, content: str):
        """Handle status update commands"""
        parts = content.split()
        if len(parts) < 3:
            self.send_message(whatsapp_user.whatsapp_number, "Usage: /status <work_order_number> <new_status>")
            return
        
        work_order_number = parts[1]
        new_status = parts[2].lower()
        
        work_order = WorkOrder.query.filter_by(work_order_number=work_order_number).first()
        if not work_order:
            self.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} not found.")
            return
        
        if work_order.assigned_technician_id != whatsapp_user.user_id:
            self.send_message(whatsapp_user.whatsapp_number, "You are not assigned to this work order.")
            return
        
        # Update work order status
        valid_statuses = ['open', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            self.send_message(whatsapp_user.whatsapp_number, f"Invalid status. Use: {', '.join(valid_statuses)}")
            return
        
        work_order.status = new_status
        if new_status == 'in_progress':
            work_order.actual_start_time = datetime.now()
        elif new_status == 'completed':
            work_order.actual_end_time = datetime.now()
        
        db.session.commit()
        
        self.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} status updated to {new_status}.")
    
    def _send_help_message(self, whatsapp_user: WhatsAppUser):
        """Send help message with available commands"""
        help_text = """🤖 CMMS WhatsApp Bot Commands

📋 Available Commands:
• /wo <work_order_number> - View work order details
• /status <work_order_number> <status> - Update work order status
• /help - Show this help message

📱 Interactive Features:
• Reply to notifications with buttons
• Send photos/videos for work documentation
• Use quick status updates

Need more help? Contact your supervisor."""
        
        self.send_message(whatsapp_user.whatsapp_number, help_text)
    
    def _handle_start_work_order(self, whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle start work order button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        work_order.status = 'in_progress'
        work_order.actual_start_time = datetime.now()
        db.session.commit()
        
        self.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order.work_order_number} started. Good luck!")
    
    def _handle_view_work_order(self, whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle view work order button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        message = f"🔧 Work Order: {work_order.work_order_number}\n\nEquipment: {work_order.equipment.name}\nStatus: {work_order.status.title()}\nPriority: {work_order.priority.title()}\nDescription: {work_order.description}"
        self.send_message(whatsapp_user.whatsapp_number, message)
    
    def _handle_mark_maintenance_done(self, whatsapp_user: WhatsAppUser, schedule_id: int):
        """Handle mark maintenance done button press"""
        schedule = MaintenanceSchedule.query.get(schedule_id)
        if not schedule:
            return
        
        schedule.last_performed = datetime.now()
        # Calculate next due date
        if schedule.frequency == 'daily':
            schedule.next_due = datetime.now() + timedelta(days=schedule.frequency_value)
        elif schedule.frequency == 'weekly':
            schedule.next_due = datetime.now() + timedelta(weeks=schedule.frequency_value)
        elif schedule.frequency == 'monthly':
            schedule.next_due = datetime.now() + timedelta(days=30 * schedule.frequency_value)
        elif schedule.frequency == 'yearly':
            schedule.next_due = datetime.now() + timedelta(days=365 * schedule.frequency_value)
        
        db.session.commit()
        
        self.send_message(whatsapp_user.whatsapp_number, f"Maintenance task marked as completed. Next due: {schedule.next_due.strftime('%Y-%m-%d')}")
    
    def _handle_reschedule_maintenance(self, whatsapp_user: WhatsAppUser, schedule_id: int):
        """Handle reschedule maintenance button press"""
        schedule = MaintenanceSchedule.query.get(schedule_id)
        if not schedule:
            return
        
        # For now, just send a message asking for new date
        # In a full implementation, you'd implement a conversation flow
        self.send_message(whatsapp_user.whatsapp_number, "Please contact your supervisor to reschedule this maintenance task.")
    
    def _download_media(self, media_id: str) -> str:
        """Download media from WhatsApp and return local URL"""
        try:
            # Get media URL
            url = f"{self.base_url}/{media_id}"
            headers = {'Authorization': f'Bearer {self.access_token}'}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            media_data = response.json()
            media_url = media_data.get('url')
            
            if not media_url:
                return None
            
            # Download media
            media_response = requests.get(media_url, headers=headers)
            if media_response.status_code != 200:
                return None
            
            # Save to local storage
            filename = f"whatsapp_media_{uuid.uuid4()}.jpg"  # Assuming image for now
            filepath = os.path.join('static', 'uploads', 'whatsapp', filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'wb') as f:
                f.write(media_response.content)
            
            return f"uploads/whatsapp/{filename}"
            
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None

# Global instance
whatsapp = WhatsAppIntegration() 