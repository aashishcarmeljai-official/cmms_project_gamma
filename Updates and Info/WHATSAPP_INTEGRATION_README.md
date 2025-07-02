# WhatsApp Integration for CMMS

This document provides a comprehensive guide to setting up and using the WhatsApp integration features in your CMMS system.

## 🚀 Features Overview

### Real-Time Work Order Notifications
- **New Work Order Assignments**: Automatically notify technicians when assigned to new work orders
- **Priority Escalations**: Alert technicians when work order priority is increased
- **Parts Delivery**: Notify when parts arrive for work orders
- **Interactive Buttons**: Quick action buttons for starting work, viewing details, and marking completion

### Quick Work Order Updates via WhatsApp
- **Status Updates**: Technicians can reply with status updates (e.g., "Completed")
- **Photo/Video Uploads**: Send multimedia documentation directly via WhatsApp
- **Auto-Update System**: Responses automatically update work order status in CMMS

### Multimedia Reporting
- **Photo Documentation**: Send photos of machine conditions, faults, or repair completion
- **Video Reports**: Upload video evidence of issues or completed work
- **Voice Notes**: Record audio descriptions for hands-free reporting
- **Automatic Linking**: All media is automatically linked to relevant work orders

### Simplified Checklist Submissions
- **Daily/Weekly Checklists**: Push checklists via WhatsApp with tappable buttons
- **Quick Responses**: "✔ Done" / "✖ Not Done" buttons for instant updates
- **Auto-Update Logs**: Responses update internal maintenance logs automatically

### Customer/Department Stakeholder Communication
- **Auto-Notifications**: Notify external stakeholders when work orders are created, started, or resolved
- **Status Updates**: "Work Order #1234 has started" / "Issue resolved at 3:21 PM"
- **Reduced Follow-up**: Minimize phone calls and emails

### Preventive Maintenance (PM) Reminders
- **Scheduled Alerts**: WhatsApp reminders for scheduled tasks
- **Interactive Completion**: "Mark as Done" buttons that update PM records
- **Rescheduling Options**: Quick reschedule functionality

### WhatsApp Chatbot for CMMS Interaction
- **View Work Orders**: `/wo [number]` - View assigned work order details
- **Status Updates**: `/status [number] [status]` - Update work order status
- **Help System**: `/help` - Show available commands
- **No App Required**: Full CMMS interaction without logging into the web app

### Emergency Broadcasts
- **Instant Notifications**: Immediately notify all technicians of urgent issues
- **Priority Levels**: Low, Medium, High, Critical priority options
- **Wide Reach**: Ensure all staff are notified even if not using the app
- **Targeted Broadcasts**: Send to specific users or all technicians

### Multilingual Support
- **Auto-Translation**: Automatic translation of alerts and updates
- **Language Preferences**: Support for English, Spanish, Hindi, Arabic, and more
- **Inclusive Communication**: Ensure clarity across diverse workforces

### Training & Onboarding via WhatsApp
- **Training Content**: Share training videos, tips, and onboarding materials
- **New User Support**: Help new technicians get up to speed quickly
- **Documentation**: Send SOPs and safety procedures via WhatsApp

## 🛠️ Setup Instructions

### 1. WhatsApp Business API Setup

#### Prerequisites
- WhatsApp Business Account
- Facebook Developer Account
- Verified Business Phone Number

#### Step-by-Step Setup

1. **Create Facebook App**
   ```
   Go to https://developers.facebook.com/
   Create a new app → Business → WhatsApp
   ```

2. **Configure WhatsApp Business API**
   ```
   In your app dashboard:
   - Add WhatsApp product
   - Configure phone number
   - Get access token and phone number ID
   ```

3. **Set Up Webhook**
   ```
   Webhook URL: https://yourdomain.com/whatsapp/webhook
   Verify Token: [your-custom-verify-token]
   Subscribe to: messages, message_deliveries
   ```

### 2. Environment Configuration

Add these variables to your `.env` file:

```env
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here

# Optional: Redis for background tasks
REDIS_URL=redis://localhost:6379
```

### 3. Database Migration

Run the migration script to create WhatsApp tables:

```bash
python migrate_whatsapp_tables.py
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 📱 User Setup

### 1. WhatsApp Number Verification

1. **Navigate to Verification Page**
   ```
   Go to: /whatsapp/verify
   ```

2. **Enter WhatsApp Number**
   ```
   Format: +1234567890 (with country code)
   ```

3. **Receive Verification Code**
   ```
   A 6-digit code will be sent to your WhatsApp
   ```

4. **Complete Verification**
   ```
   Enter the code and click "Verify Code"
   ```

### 2. Configure Notification Preferences

1. **Access Settings**
   ```
   Go to: /whatsapp/settings
   ```

2. **Choose Notifications**
   - Work Order Assignments
   - Priority Escalations
   - Parts Delivery
   - Maintenance Reminders
   - Emergency Broadcasts
   - Daily Checklists

3. **Set Language Preference**
   ```
   Choose your preferred language for notifications
   ```

## 🔧 API Endpoints

### Webhook Endpoint
```
POST /whatsapp/webhook
GET /whatsapp/webhook?hub.mode=subscribe&hub.verify_token=...
```

### User Management
```
GET /whatsapp/verify - Verification page
POST /whatsapp/verify - Submit verification
GET /whatsapp/settings - Settings page
POST /whatsapp/settings - Update settings
```

### Emergency Broadcasts
```
GET /whatsapp/emergency - Emergency broadcast page
POST /whatsapp/emergency - Send emergency broadcast
```

### Templates Management
```
GET /whatsapp/templates - View templates
GET /whatsapp/templates/new - Create template
POST /whatsapp/templates/new - Save template
```

### API Endpoints
```
POST /api/whatsapp/send-test - Send test message
GET /api/whatsapp/users - Get all WhatsApp users
GET /whatsapp/notifications - View notification logs
```

## 💬 WhatsApp Commands

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/wo [number]` | View work order details | `/wo WO-20241201-ABC123` |
| `/status [number] [status]` | Update work order status | `/status WO-20241201-ABC123 completed` |
| `/help` | Show available commands | `/help` |

### Status Options
- `open` - Work order is open
- `in_progress` - Work has started
- `completed` - Work is finished
- `cancelled` - Work order cancelled

## 📊 Notification Types

### 1. Work Order Notifications

**New Assignment**
```
🔧 New Work Order Assigned

Work Order: WO-20241201-ABC123
Equipment: HVAC Unit #5
Priority: High
Description: Compressor failure detected...

[Start Work] [View Details]
```

**Priority Escalation**
```
🚨 Priority Escalated

Work Order: WO-20241201-ABC123
Equipment: HVAC Unit #5
Priority: Medium → High
Please prioritize this work order.
```

### 2. Maintenance Reminders

```
📅 Maintenance Reminder

Equipment: HVAC Unit #5
Task: Monthly filter replacement
Due: 2024-12-01 09:00

[Mark as Done] [Reschedule]
```

### 3. Emergency Broadcasts

```
🚨 EMERGENCY: Critical Equipment Failure

HVAC Unit #5 has overheated and needs immediate shutdown.
All operations in Building A should be stopped.

Priority: CRITICAL
```

## 🔒 Security Considerations

### 1. Access Control
- Only verified WhatsApp numbers can receive notifications
- Users must verify their own phone numbers
- Admin controls for emergency broadcasts

### 2. Data Privacy
- Phone numbers are encrypted in database
- Verification codes expire after 10 minutes
- Users can disable notifications anytime

### 3. Rate Limiting
- WhatsApp API has rate limits
- System implements queuing for high-volume scenarios
- Error handling for failed deliveries

## 🚨 Troubleshooting

### Common Issues

1. **Verification Code Not Received**
   - Check phone number format (include country code)
   - Ensure number is registered with WhatsApp
   - Wait 2-3 minutes for delivery

2. **Webhook Not Receiving Messages**
   - Verify webhook URL is accessible
   - Check verify token matches
   - Ensure SSL certificate is valid

3. **Messages Not Sending**
   - Verify WhatsApp Business API credentials
   - Check phone number ID is correct
   - Ensure access token is valid

4. **Database Errors**
   - Run migration script again
   - Check database permissions
   - Verify table structure

### Debug Mode

Enable debug logging by setting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Support

For technical support:
1. Check the logs in `/whatsapp/notifications`
2. Verify WhatsApp Business API status
3. Test with `/api/whatsapp/send-test` endpoint

## 📈 Best Practices

### 1. Message Design
- Keep messages concise and actionable
- Use emojis for visual clarity
- Include relevant work order numbers
- Provide clear next steps

### 2. Notification Management
- Don't over-notify users
- Use appropriate priority levels
- Respect user preferences
- Provide opt-out options

### 3. Emergency Procedures
- Use emergency broadcasts sparingly
- Include clear action items
- Follow up with detailed instructions
- Log all emergency communications

### 4. Training
- Train users on available commands
- Provide help documentation
- Regular refresher sessions
- Monitor usage patterns

## 🔄 Integration with Existing Features

### Work Order System
- Automatic notifications on assignment
- Status updates via WhatsApp
- Photo/video documentation
- Checklist completion

### Maintenance Schedules
- Reminder notifications
- Interactive completion
- Rescheduling options
- Progress tracking

### User Management
- WhatsApp verification process
- Notification preferences
- Language settings
- Activity logging

### Reporting
- Notification delivery reports
- User engagement metrics
- Response time tracking
- Communication logs

## 🎯 Future Enhancements

### Planned Features
- **Advanced Chatbot**: AI-powered responses
- **Voice Commands**: Voice-to-text integration
- **Group Chats**: Team-based communications
- **Analytics Dashboard**: Detailed usage reports
- **Custom Templates**: User-defined message templates
- **Integration APIs**: Third-party system connections

### Scalability
- **Background Processing**: Celery integration for high volume
- **Caching**: Redis for performance optimization
- **Load Balancing**: Multiple webhook endpoints
- **Monitoring**: Health checks and alerts

---

## 📞 Support

For questions or issues with the WhatsApp integration:

1. **Documentation**: Check this README and inline code comments
2. **Logs**: Review `/whatsapp/notifications` for delivery status
3. **Testing**: Use `/api/whatsapp/send-test` for verification
4. **Configuration**: Verify environment variables and webhook setup

The WhatsApp integration provides a powerful way to keep your maintenance team connected and responsive, ensuring critical information reaches the right people at the right time. 