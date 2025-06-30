# QR Code-Based Failure Reporting System

## 🎯 Overview

The QR Code-Based Failure Reporting System allows users to quickly report equipment failures by scanning a QR code attached to a machine. This feature provides a mobile-friendly interface for field technicians and operators to report issues without needing to access the main CMMS interface.

## 🚀 Features

### **Core Functionality**
- **QR Code Generation**: Generate unique QR codes for each equipment item
- **Mobile-Optimized Interface**: Responsive design that works on smartphones and tablets
- **Media Capture**: Support for photos, videos, and audio recordings
- **Automatic Work Order Creation**: Submits create high-priority work orders automatically
- **Equipment Status Updates**: Automatically updates equipment status to "maintenance"

### **User Experience**
- **Pre-filled Equipment Data**: Equipment details are automatically populated
- **Simple Form Interface**: Easy-to-use form with clear instructions
- **Offline Support**: Form data is saved locally if connection is lost
- **Success Confirmation**: Clear feedback when report is submitted

## 📱 How It Works

### **1. QR Code Generation**
- Each equipment item gets a unique QR code
- QR codes link directly to the failure reporting page for that specific equipment
- QR codes can be printed and attached to equipment

### **2. Failure Reporting Process**
1. **Scan QR Code**: User scans QR code with smartphone camera
2. **Auto-Redirect**: Browser opens the failure reporting page
3. **Pre-filled Data**: Equipment information is automatically populated
4. **Report Issue**: User fills out failure description and captures media
5. **Submit Report**: Creates work order and updates equipment status

### **3. Work Order Creation**
- **Automatic Priority**: High urgency reports create "urgent" priority work orders
- **Media Attachments**: Photos, videos, and audio are attached to the work order
- **Equipment Status**: Equipment status changes to "maintenance" if operational
- **Notification**: Maintenance team is notified of the new work order

## 🛠️ Technical Implementation

### **Routes Added**

#### **QR Failure Reporting**
```python
@app.route('/qr-report/<equipment_id>', methods=['GET', 'POST'])
def qr_failure_report(equipment_id):
    """QR code failure reporting page"""
```

#### **QR Code Generation**
```python
@app.route('/generate-qr/<equipment_id>')
@login_required
def generate_qr_code(equipment_id):
    """Generate QR code for equipment failure reporting"""
```

#### **API Endpoints**
```python
@app.route('/api/qr-equipment/<equipment_id>')
def api_qr_equipment(equipment_id):
    """API endpoint for QR code equipment data"""
```

### **Templates Created**

1. **`qr_failure_report.html`**: Main failure reporting form
2. **`qr_failure_report_success.html`**: Success confirmation page
3. **`generate_qr.html`**: QR code generation interface

### **Features Implemented**

#### **Media Capture**
- **Photo Capture**: Take photos using device camera
- **Video Recording**: Record short videos (10 seconds max)
- **Audio Recording**: Record voice messages
- **File Upload**: Upload existing media files
- **Preview**: Real-time preview of captured media

#### **Form Features**
- **Auto-save**: Form data saved to localStorage
- **Validation**: Required field validation
- **Responsive Design**: Works on all device sizes
- **Offline Support**: Graceful handling of connection issues

#### **Work Order Integration**
- **Automatic Creation**: Work orders created with proper priority
- **Media Attachments**: Files saved and linked to work order
- **Equipment Updates**: Status changes handled automatically
- **Reporter Information**: Optional contact details captured

## 📋 Usage Instructions

### **For Administrators**

#### **Generating QR Codes**
1. Navigate to Equipment → Select Equipment → Click "Generate QR Code"
2. Download QR code in PNG, SVG, or PDF format
3. Print and attach QR codes to equipment
4. Use bulk generation script for multiple equipment

#### **Bulk QR Code Generation**
```bash
# Generate QR codes for all equipment
python generate_qr_codes.py --base-url "https://your-cmms-domain.com"

# Generate in specific format
python generate_qr_codes.py --format svg --output-dir qr_codes_svg

# Custom base URL for production
python generate_qr_codes.py --base-url "https://cmms.company.com"
```

### **For Field Users**

#### **Reporting a Failure**
1. **Scan QR Code**: Use smartphone camera to scan QR code on equipment
2. **Verify Equipment**: Check that correct equipment details are shown
3. **Describe Issue**: Fill out failure description and type
4. **Add Media**: Take photos, record video, or add audio
5. **Submit Report**: Click submit to create work order
6. **Get Confirmation**: Receive work order number and next steps

#### **Best Practices**
- **Clear Photos**: Take clear, well-lit photos of the issue
- **Video Duration**: Keep videos under 10 seconds for quick upload
- **Audio Quality**: Record in quiet environment for clear audio
- **Contact Info**: Provide name and phone for follow-up questions

## 🔧 Configuration

### **Required Dependencies**
```txt
qrcode[pil]==7.4.2
```

### **File Upload Settings**
- **Image Formats**: JPG, PNG, GIF
- **Video Formats**: MP4, WebM, MOV
- **Audio Formats**: MP3, WAV, WebM
- **Max File Size**: 10MB per file
- **Storage Location**: `static/uploads/work_orders/`

### **Work Order Settings**
- **Default Priority**: High for urgent issues, Medium for others
- **Response Time**: 2-4 hours for urgent, 24 hours for high priority
- **Auto-assignment**: Assigned to default admin user (configurable)

## 📱 Mobile Optimization

### **Progressive Web App Features**
- **Add to Home Screen**: Users can install as app
- **Offline Support**: Basic functionality works offline
- **Push Notifications**: Status updates (future enhancement)
- **Camera Integration**: Direct access to device camera

### **Responsive Design**
- **Mobile First**: Optimized for smartphone screens
- **Touch Friendly**: Large buttons and touch targets
- **Fast Loading**: Optimized for slow connections
- **Battery Efficient**: Minimal resource usage

## 🔒 Security Considerations

### **Access Control**
- **Public Access**: QR reporting pages are publicly accessible
- **Rate Limiting**: Implement rate limiting for abuse prevention
- **File Validation**: Validate uploaded file types and sizes
- **Input Sanitization**: Sanitize all user inputs

### **Data Protection**
- **Secure Uploads**: Files stored in secure location
- **Access Logging**: Log all QR code access attempts
- **Spam Prevention**: Implement CAPTCHA for repeated submissions
- **Privacy**: Minimal data collection (optional contact info)

## 🚀 Deployment

### **Production Setup**
1. **Update Base URL**: Change QR code URLs to production domain
2. **SSL Certificate**: Ensure HTTPS for secure file uploads
3. **File Storage**: Configure proper file storage location
4. **Database**: Ensure database can handle increased load

### **Monitoring**
- **QR Code Usage**: Track QR code scan statistics
- **File Uploads**: Monitor upload success/failure rates
- **Work Order Creation**: Track automatic work order creation
- **Error Logging**: Monitor for any system errors

## 📊 Analytics & Reporting

### **Usage Metrics**
- **QR Code Scans**: Number of QR codes scanned
- **Report Submissions**: Success/failure rates
- **Media Uploads**: Types and sizes of uploaded files
- **Response Times**: Time from report to work order creation

### **Equipment Insights**
- **Most Reported**: Equipment with highest failure reports
- **Issue Patterns**: Common failure types and descriptions
- **Location Trends**: Areas with most reported issues
- **Seasonal Patterns**: Time-based failure trends

## 🔮 Future Enhancements

### **Planned Features**
- **Push Notifications**: Real-time status updates
- **Voice-to-Text**: Convert audio to text descriptions
- **AI Analysis**: Automatic issue categorization
- **Integration**: Connect with external maintenance systems
- **Multi-language**: Support for multiple languages
- **Advanced Media**: 360° photos, thermal imaging support

### **Integration Possibilities**
- **IoT Sensors**: Automatic failure detection
- **Predictive Maintenance**: AI-powered failure prediction
- **Inventory Integration**: Automatic parts ordering
- **Technician App**: Dedicated mobile app for technicians
- **Customer Portal**: Customer-facing status updates

## 🐛 Troubleshooting

### **Common Issues**

#### **QR Code Not Working**
- **Check URL**: Ensure base URL is correct
- **Test Link**: Verify QR code links to correct page
- **Print Quality**: Ensure QR code is printed clearly
- **Lighting**: Ensure good lighting for scanning

#### **Media Upload Failures**
- **File Size**: Check file size limits
- **Format**: Verify supported file formats
- **Permissions**: Check camera/microphone permissions
- **Storage**: Ensure sufficient device storage

#### **Form Submission Issues**
- **Internet Connection**: Check network connectivity
- **Browser Compatibility**: Test with different browsers
- **JavaScript**: Ensure JavaScript is enabled
- **Cache**: Clear browser cache if needed

### **Support Contacts**
- **Technical Issues**: IT Support Team
- **QR Code Problems**: Maintenance Manager
- **System Access**: System Administrator
- **Emergency**: Emergency Contact Number

## 📚 Additional Resources

### **Documentation**
- [QR Code Best Practices](https://www.qrcode.com/en/howto/)
- [Mobile Web Development](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [File Upload Security](https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload)

### **Training Materials**
- **User Guide**: Step-by-step instructions for field users
- **Video Tutorials**: Visual guides for common tasks
- **FAQ**: Frequently asked questions and answers
- **Best Practices**: Tips for effective failure reporting

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Maintainer**: CMMS Development Team 