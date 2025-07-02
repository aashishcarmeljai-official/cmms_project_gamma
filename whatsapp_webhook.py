import json
import logging
import uuid
import os
import requests
from datetime import datetime
from typing import Dict, Any
from models import db, WhatsAppUser, WhatsAppMessage, WorkOrder, MaintenanceSchedule
from whatsapp_integration import whatsapp

logger = logging.getLogger(__name__)

class WhatsAppWebhookHandler:
    """Handle incoming WhatsApp webhooks and messages"""
    
    @staticmethod
    def process_incoming_message(data: Dict) -> Dict:
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
                WhatsAppWebhookHandler._process_text_message(whatsapp_user, content, timestamp)
                
            elif message_type == 'image':
                media_id = message.get('image', {}).get('id')
                caption = message.get('image', {}).get('caption', '')
                WhatsAppWebhookHandler._process_media_message(whatsapp_user, 'image', media_id, caption, timestamp)
                
            elif message_type == 'video':
                media_id = message.get('video', {}).get('id')
                caption = message.get('video', {}).get('caption', '')
                WhatsAppWebhookHandler._process_media_message(whatsapp_user, 'video', media_id, caption, timestamp)
                
            elif message_type == 'interactive':
                WhatsAppWebhookHandler._process_interactive_message(whatsapp_user, message, timestamp)
            
            return {'success': True, 'message': 'Message processed successfully'}
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _process_text_message(whatsapp_user: WhatsAppUser, content: str, timestamp: int):
        """Process incoming text message"""
        # Check for commands
        if content.lower().startswith('/wo'):
            WhatsAppWebhookHandler._handle_work_order_command(whatsapp_user, content)
        elif content.lower().startswith('/status'):
            WhatsAppWebhookHandler._handle_status_command(whatsapp_user, content)
        elif content.lower().startswith('/help'):
            WhatsAppWebhookHandler._send_help_message(whatsapp_user)
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
    
    @staticmethod
    def _process_media_message(whatsapp_user: WhatsAppUser, media_type: str, media_id: str, 
                              caption: str, timestamp: int):
        """Process incoming media message"""
        # Download media and store
        media_url = WhatsAppWebhookHandler._download_media(media_id)
        
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
    
    @staticmethod
    def _process_interactive_message(whatsapp_user: WhatsAppUser, message: Dict, timestamp: int):
        """Process interactive message (button responses)"""
        interactive = message.get('interactive', {})
        button_response = interactive.get('button_reply', {})
        button_id = button_response.get('id', '')
        
        # Process button actions
        if button_id.startswith('wo_start_'):
            work_order_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_start_work_order(whatsapp_user, work_order_id)
        elif button_id.startswith('wo_view_'):
            work_order_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_view_work_order(whatsapp_user, work_order_id)
        elif button_id.startswith('wo_complete_'):
            work_order_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_complete_work_order(whatsapp_user, work_order_id)
        elif button_id.startswith('maint_done_'):
            schedule_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_mark_maintenance_done(whatsapp_user, schedule_id)
        elif button_id.startswith('maint_schedule_'):
            schedule_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_reschedule_maintenance(whatsapp_user, schedule_id)
        elif button_id.startswith('checklist_done_'):
            work_order_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_checklist_done(whatsapp_user, work_order_id)
        elif button_id.startswith('checklist_issues_'):
            work_order_id = int(button_id.split('_')[2])
            WhatsAppWebhookHandler._handle_checklist_issues(whatsapp_user, work_order_id)
    
    @staticmethod
    def _handle_work_order_command(whatsapp_user: WhatsAppUser, content: str):
        """Handle work order related commands"""
        parts = content.split()
        if len(parts) < 2:
            whatsapp.send_message(whatsapp_user.whatsapp_number, "Usage: /wo <work_order_number>")
            return
        
        work_order_number = parts[1]
        work_order = WorkOrder.query.filter_by(work_order_number=work_order_number).first()
        
        if not work_order:
            whatsapp.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} not found.")
            return
        
        # Check if user is assigned to this work order
        if work_order.assigned_technician_id != whatsapp_user.user_id:
            whatsapp.send_message(whatsapp_user.whatsapp_number, "You are not assigned to this work order.")
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
        
        whatsapp.send_interactive_message(whatsapp_user.whatsapp_number, message, buttons)
    
    @staticmethod
    def _handle_status_command(whatsapp_user: WhatsAppUser, content: str):
        """Handle status update commands"""
        parts = content.split()
        if len(parts) < 3:
            whatsapp.send_message(whatsapp_user.whatsapp_number, "Usage: /status <work_order_number> <new_status>")
            return
        
        work_order_number = parts[1]
        new_status = parts[2].lower()
        
        work_order = WorkOrder.query.filter_by(work_order_number=work_order_number).first()
        if not work_order:
            whatsapp.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} not found.")
            return
        
        if work_order.assigned_technician_id != whatsapp_user.user_id:
            whatsapp.send_message(whatsapp_user.whatsapp_number, "You are not assigned to this work order.")
            return
        
        # Update work order status
        valid_statuses = ['open', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            whatsapp.send_message(whatsapp_user.whatsapp_number, f"Invalid status. Use: {', '.join(valid_statuses)}")
            return
        
        work_order.status = new_status
        if new_status == 'in_progress':
            work_order.actual_start_time = datetime.now()
        elif new_status == 'completed':
            work_order.actual_end_time = datetime.now()
        
        db.session.commit()
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order_number} status updated to {new_status}.")
    
    @staticmethod
    def _send_help_message(whatsapp_user: WhatsAppUser):
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
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, help_text)
    
    @staticmethod
    def _handle_start_work_order(whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle start work order button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        work_order.status = 'in_progress'
        work_order.actual_start_time = datetime.now()
        db.session.commit()
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order.work_order_number} started. Good luck!")
    
    @staticmethod
    def _handle_view_work_order(whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle view work order button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        message = f"🔧 Work Order: {work_order.work_order_number}\n\nEquipment: {work_order.equipment.name}\nStatus: {work_order.status.title()}\nPriority: {work_order.priority.title()}\nDescription: {work_order.description}"
        whatsapp.send_message(whatsapp_user.whatsapp_number, message)
    
    @staticmethod
    def _handle_complete_work_order(whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle complete work order button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        work_order.status = 'completed'
        work_order.actual_end_time = datetime.now()
        db.session.commit()
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"Work order {work_order.work_order_number} marked as completed. Great job!")
    
    @staticmethod
    def _handle_mark_maintenance_done(whatsapp_user: WhatsAppUser, schedule_id: int):
        """Handle mark maintenance done button press"""
        schedule = MaintenanceSchedule.query.get(schedule_id)
        if not schedule:
            return
        
        schedule.last_performed = datetime.now()
        # Calculate next due date
        from datetime import timedelta
        if schedule.frequency == 'daily':
            schedule.next_due = datetime.now() + timedelta(days=schedule.frequency_value)
        elif schedule.frequency == 'weekly':
            schedule.next_due = datetime.now() + timedelta(weeks=schedule.frequency_value)
        elif schedule.frequency == 'monthly':
            schedule.next_due = datetime.now() + timedelta(days=30 * schedule.frequency_value)
        elif schedule.frequency == 'yearly':
            schedule.next_due = datetime.now() + timedelta(days=365 * schedule.frequency_value)
        
        db.session.commit()
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"Maintenance task marked as completed. Next due: {schedule.next_due.strftime('%Y-%m-%d')}")
    
    @staticmethod
    def _handle_reschedule_maintenance(whatsapp_user: WhatsAppUser, schedule_id: int):
        """Handle reschedule maintenance button press"""
        schedule = MaintenanceSchedule.query.get(schedule_id)
        if not schedule:
            return
        
        # For now, just send a message asking for new date
        # In a full implementation, you'd implement a conversation flow
        whatsapp.send_message(whatsapp_user.whatsapp_number, "Please contact your supervisor to reschedule this maintenance task.")
    
    @staticmethod
    def _handle_checklist_done(whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle checklist done button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        # Mark all checklist items as completed
        for checklist_item in work_order.checklist_items:
            checklist_item.is_completed = True
            checklist_item.completed_by_id = whatsapp_user.user_id
            checklist_item.completed_at = datetime.now()
        
        db.session.commit()
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"All checklist items for work order {work_order.work_order_number} marked as completed.")
    
    @staticmethod
    def _handle_checklist_issues(whatsapp_user: WhatsAppUser, work_order_id: int):
        """Handle checklist issues button press"""
        work_order = WorkOrder.query.get(work_order_id)
        if not work_order:
            return
        
        whatsapp.send_message(whatsapp_user.whatsapp_number, f"Please describe the issues you encountered with work order {work_order.work_order_number}. Send your message and we'll log it.")
    
    @staticmethod
    def _download_media(media_id: str) -> str:
        """Download media from WhatsApp and return local URL"""
        try:
            # Get media URL
            url = f"{whatsapp.base_url}/{media_id}"
            headers = {'Authorization': f'Bearer {whatsapp.access_token}'}
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
                media_response.content
            
            return f"uploads/whatsapp/{filename}"
            
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None 