import json
import logging
from datetime import datetime
from typing import List, Dict
from models import db, WhatsAppUser, NotificationLog, WorkOrder, MaintenanceSchedule, EmergencyBroadcast
from whatsapp_integration import whatsapp

logger = logging.getLogger(__name__)

class WhatsAppNotifications:
    """WhatsApp notification handlers for CMMS"""
    
    @staticmethod
    def notify_work_order_assignment(work_order: WorkOrder) -> bool:
        """Send WhatsApp notification for new work order assignment"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        # Translate message based on user's preferred language
        message = f"🔧 New Work Order Assigned\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\nPriority: {work_order.priority.title()}\nDescription: {work_order.description[:100]}..."
        
        translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
        
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
        
        result = whatsapp.send_interactive_message(whatsapp_user.whatsapp_number, translated_message, buttons)
        
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
    
    @staticmethod
    def notify_priority_escalation(work_order: WorkOrder, old_priority: str) -> bool:
        """Send WhatsApp notification for priority escalation"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        message = f"🚨 Priority Escalated\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\nPriority: {old_priority.title()} → {work_order.priority.title()}\nPlease prioritize this work order."
        
        translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
        
        result = whatsapp.send_message(whatsapp_user.whatsapp_number, translated_message)
        
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
    
    @staticmethod
    def notify_parts_delivery(work_order: WorkOrder, parts: List[str]) -> bool:
        """Send WhatsApp notification for parts delivery"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        parts_list = '\n'.join([f"• {part}" for part in parts])
        message = f"📦 Parts Delivered\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\n\nDelivered Parts:\n{parts_list}\n\nYou can now proceed with the repair."
        
        translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
        
        result = whatsapp.send_message(whatsapp_user.whatsapp_number, translated_message)
        
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
    
    @staticmethod
    def send_maintenance_reminder(maintenance_schedule: MaintenanceSchedule) -> bool:
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
            
            translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
            
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
            
            result = whatsapp.send_interactive_message(whatsapp_user.whatsapp_number, translated_message, buttons)
            
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
    
    @staticmethod
    def send_emergency_broadcast(emergency: EmergencyBroadcast) -> bool:
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
                
                translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
                
                result = whatsapp.send_message(whatsapp_user.whatsapp_number, translated_message)
                
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
    
    @staticmethod
    def notify_stakeholders(work_order: WorkOrder, event_type: str) -> bool:
        """Notify external stakeholders about work order events"""
        message_templates = {
            'created': f"Work Order #{work_order.work_order_number} has been created for {work_order.equipment.name}",
            'started': f"Work Order #{work_order.work_order_number} has started at {datetime.now().strftime('%I:%M %p')}",
            'completed': f"Work Order #{work_order.work_order_number} has been completed at {datetime.now().strftime('%I:%M %p')}"
        }
        
        message = message_templates.get(event_type, f"Work Order #{work_order.work_order_number} status updated")
        
        # In a real implementation, you would get stakeholder contacts from database
        # For now, we'll return True as placeholder
        return True
    
    @staticmethod
    def send_checklist_reminder(work_order: WorkOrder, checklist_items: List[str]) -> bool:
        """Send checklist reminder via WhatsApp"""
        if not work_order.assigned_technician:
            return False
        
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=work_order.assigned_technician.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        checklist_text = '\n'.join([f"• {item}" for item in checklist_items])
        message = f"📋 Daily Checklist Reminder\n\nWork Order: {work_order.work_order_number}\nEquipment: {work_order.equipment.name}\n\nPlease complete:\n{checklist_text}"
        
        translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
        
        # Create interactive buttons for each checklist item
        buttons = [
            {
                'type': 'reply',
                'reply': {
                    'id': f'checklist_done_{work_order.id}',
                    'title': 'All Done'
                }
            },
            {
                'type': 'reply',
                'reply': {
                    'id': f'checklist_issues_{work_order.id}',
                    'title': 'Report Issues'
                }
            }
        ]
        
        result = whatsapp.send_interactive_message(whatsapp_user.whatsapp_number, translated_message, buttons)
        
        # Log the notification
        notification = NotificationLog(
            notification_type='whatsapp',
            recipient_id=work_order.assigned_technician.id,
            recipient_whatsapp_id=whatsapp_user.id,
            subject='Daily Checklist Reminder',
            content=translated_message,
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error'),
            work_order_id=work_order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return result['success']
    
    @staticmethod
    def send_training_content(user: User, training_type: str, content_url: str) -> bool:
        """Send training content via WhatsApp"""
        whatsapp_user = WhatsAppUser.query.filter_by(user_id=user.id).first()
        if not whatsapp_user or not whatsapp_user.is_verified:
            return False
        
        message = f"📚 Training Content Available\n\nType: {training_type}\n\nClick the link below to access your training materials."
        
        translated_message = whatsapp.translate_message(message, whatsapp_user.preferred_language)
        
        # Send as document with link
        result = whatsapp.send_message(
            whatsapp_user.whatsapp_number, 
            translated_message, 
            message_type='document',
            media_url=content_url
        )
        
        # Log the notification
        notification = NotificationLog(
            notification_type='whatsapp',
            recipient_id=user.id,
            recipient_whatsapp_id=whatsapp_user.id,
            subject=f'Training: {training_type}',
            content=translated_message,
            status='sent' if result['success'] else 'failed',
            error_message=result.get('error')
        )
        db.session.add(notification)
        db.session.commit()
        
        return result['success'] 