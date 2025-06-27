# Photo/Video Upload System for Work Orders

## Overview

The CMMS application now includes a comprehensive media upload system designed specifically for technicians working in the field. This system supports photos, videos, and voice notes with mobile-first design and robust offline capabilities.

## Features

### 🎯 Core Features
- **Photo Upload**: Capture and upload images showing problems or completed work
- **Video Upload**: Record videos demonstrating issues or procedures
- **Voice Notes**: Record audio notes for hands-free documentation
- **Mobile-First Design**: Optimized for mobile devices with touch-friendly interfaces
- **Offline Support**: Work continues even with poor internet connectivity
- **Progress Tracking**: Real-time upload progress indicators
- **File Compression**: Automatic image compression to reduce upload times
- **Drag & Drop**: Intuitive file upload interface

### 📱 Mobile Optimizations
- Touch-friendly buttons and controls
- Responsive design for all screen sizes
- Optimized for poor internet connections
- Voice recording with noise suppression
- Camera integration for direct photo/video capture

### 🔄 Offline Capabilities
- Local storage of media files when offline
- Automatic sync when connection is restored
- Background sync using Service Workers
- Queue management for pending uploads
- Data persistence across browser sessions

## Technical Implementation

### Database Schema Changes

#### WorkOrder Model Enhancements
```python
class WorkOrder(db.Model):
    # ... existing fields ...
    images = db.Column(db.Text)  # Store image file paths as JSON
    videos = db.Column(db.Text)  # Store video file paths as JSON
    voice_notes = db.Column(db.Text)  # Store voice note file paths as JSON
```

#### WorkOrderComment Model Enhancements
```python
class WorkOrderComment(db.Model):
    # ... existing fields ...
    images = db.Column(db.Text)  # Store image file paths as JSON
    videos = db.Column(db.Text)  # Store video file paths as JSON
    voice_notes = db.Column(db.Text)  # Store voice note file paths as JSON
```

### File Upload Configuration

#### Supported File Types
- **Images**: PNG, JPG, JPEG, GIF, WebP
- **Videos**: MP4, AVI, MOV, WMV, FLV, WebM, MKV
- **Audio**: MP3, WAV, OGG, M4A, AAC

#### File Size Limits
- Maximum file size: 50MB per file
- Automatic image compression for files > 5MB
- Progressive upload for large files

### API Endpoints

#### Work Order Media Upload
```
POST /api/work-orders/{work_order_id}/upload-media
Content-Type: multipart/form-data

Parameters:
- media_type: "image" | "video" | "voice"
- images/videos/voice_notes: File upload(s)

Response:
{
    "success": true,
    "message": "2 image(s) uploaded successfully",
    "uploaded_files": ["uploads/work_orders/20241201_143022_image1.jpg"]
}
```

#### Comment Media Upload
```
POST /api/work-orders/{work_order_id}/comments/{comment_id}/upload-media
Content-Type: multipart/form-data

Parameters:
- media_type: "image" | "video" | "voice"
- images/videos/voice_notes: File upload(s)
```

#### Offline Data Sync
```
POST /api/work-orders/{work_order_id}/sync-offline-data
Content-Type: application/json

Body:
{
    "status": "completed",
    "completion_notes": "Task completed successfully",
    "offline_media": [
        {
            "type": "image",
            "file_data": "data:image/jpeg;base64,/9j/4AAQ...",
            "extension": "jpg"
        }
    ]
}
```

## User Interface

### Work Order Creation Form

#### Media Upload Section
- **Photo Upload**: Camera icon button with preview grid
- **Video Upload**: Video camera icon button with thumbnail previews
- **Voice Recording**: Microphone button with recording timer
- **File Browser**: Traditional file picker for existing files

#### Mobile-First Design Elements
- Large touch targets (minimum 44px)
- Swipe gestures for media navigation
- Full-screen media viewer
- Voice recording with visual feedback

### Work Order Detail View

#### Media Gallery
- **Tabbed Interface**: Separate tabs for photos, videos, and voice notes
- **Grid Layout**: Responsive grid with hover effects
- **Modal Viewer**: Full-screen media playback
- **Download Options**: Direct download links for media files

#### Comment Media
- **Inline Previews**: Thumbnail previews in comments
- **Expandable View**: Click to view full-size media
- **Audio Player**: Embedded audio controls for voice notes

## Offline Functionality

### Service Worker Implementation
```javascript
// Cache static files for offline access
const STATIC_FILES = [
    '/',
    '/static/css/style.css',
    '/static/js/media-upload.js',
    // ... other static assets
];

// Handle offline media requests
async function handleMediaRequest(request) {
    const cache = await caches.open(MEDIA_CACHE);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
        return cachedResponse;
    }
    
    // Fallback for uncached media
    return new Response('Media not available offline');
}
```

### Offline Queue Management
```javascript
class MediaUploadManager {
    addToOfflineQueue(file, type, workOrderId, commentId = null) {
        const queueItem = {
            id: Date.now() + Math.random(),
            file: file,
            type: type,
            workOrderId: workOrderId,
            commentId: commentId,
            timestamp: new Date().toISOString()
        };
        
        this.offlineQueue.push(queueItem);
        this.saveOfflineQueue();
    }
}
```

### Background Sync
- Automatic sync when connection is restored
- Queue processing with retry logic
- Progress indicators for sync operations
- Conflict resolution for concurrent edits

## File Management

### Upload Directory Structure
```
static/uploads/
├── work_orders/
│   ├── 20241201_143022_image1.jpg
│   ├── 20241201_143025_video1.mp4
│   └── 20241201_143030_voice1.wav
└── comments/
    ├── 20241201_143035_comment1.jpg
    └── 20241201_143040_comment2.mp4
```

### File Naming Convention
- Format: `YYYYMMDD_HHMMSS_microseconds_filename.ext`
- Example: `20241201_143022_123456_image1.jpg`
- Ensures unique filenames and chronological ordering

### Security Measures
- File type validation
- File size limits
- Secure filename generation
- Path traversal prevention
- Content-Type verification

## Performance Optimizations

### Image Compression
```javascript
async compressImage(file) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Resize to max 1920px width/height
    const maxSize = 1920;
    let { width, height } = img;
    
    if (width > height) {
        if (width > maxSize) {
            height = (height * maxSize) / width;
            width = maxSize;
        }
    }
    
    // Compress with 80% quality
    canvas.toBlob(blob => {
        const compressedFile = new File([blob], file.name, {
            type: 'image/jpeg',
            lastModified: Date.now()
        });
    }, 'image/jpeg', 0.8);
}
```

### Progressive Loading
- Lazy loading for media galleries
- Thumbnail generation for videos
- Audio waveform generation for voice notes
- Caching strategies for frequently accessed media

### Network Optimization
- Chunked uploads for large files
- Retry logic with exponential backoff
- Connection quality detection
- Adaptive quality based on network speed

## User Experience Features

### Voice Recording
- **Noise Suppression**: Automatic background noise reduction
- **Echo Cancellation**: Prevents audio feedback
- **Visual Feedback**: Recording timer and status indicators
- **Quality Settings**: Configurable audio quality

### Camera Integration
- **Direct Capture**: Camera access for immediate photos/videos
- **Multiple Selection**: Choose multiple files at once
- **Preview Before Upload**: Review media before submission
- **Edit Options**: Basic cropping and rotation

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader**: ARIA labels and descriptions
- **High Contrast**: Support for high contrast themes
- **Voice Commands**: Voice control for hands-free operation

## Error Handling

### Upload Failures
- Automatic retry with exponential backoff
- Offline storage for failed uploads
- User notification of upload status
- Manual retry options

### Network Issues
- Connection quality detection
- Adaptive upload strategies
- Offline mode indicators
- Sync status notifications

### File Validation
- Real-time file type checking
- Size limit enforcement
- Format compatibility verification
- Corrupted file detection

## Testing

### Manual Testing Checklist
- [ ] Photo upload from camera
- [ ] Photo upload from gallery
- [ ] Video upload and playback
- [ ] Voice recording and playback
- [ ] Offline functionality
- [ ] Sync when connection restored
- [ ] File size limits
- [ ] File type validation
- [ ] Mobile responsiveness
- [ ] Touch interactions

### Automated Testing
```javascript
// Example test for media upload
describe('Media Upload', () => {
    test('should upload image successfully', async () => {
        const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
        const result = await mediaUploadManager.uploadFile(file, 'image', 1);
        expect(result.success).toBe(true);
    });
    
    test('should handle offline upload', async () => {
        // Simulate offline mode
        navigator.onLine = false;
        const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' });
        const result = await mediaUploadManager.uploadFile(file, 'image', 1);
        expect(result.offline).toBe(true);
    });
});
```

## Deployment Considerations

### Server Configuration
- Increase upload file size limits
- Configure proper MIME types
- Set up CDN for media delivery
- Implement backup strategies

### Security Headers
```
Content-Security-Policy: default-src 'self'; media-src 'self' data: blob:;
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

### Performance Monitoring
- Upload success rates
- File size distributions
- Network usage patterns
- User interaction metrics

## Future Enhancements

### Planned Features
- **AI Image Analysis**: Automatic problem detection in photos
- **Video Transcription**: Speech-to-text for voice notes
- **AR Integration**: Augmented reality for equipment identification
- **Batch Processing**: Bulk media operations
- **Advanced Compression**: AI-powered image optimization

### Technical Improvements
- **WebRTC**: Real-time video streaming
- **WebAssembly**: Client-side video processing
- **IndexedDB**: Enhanced offline storage
- **Push Notifications**: Real-time sync notifications

## Support and Maintenance

### Troubleshooting
- Check browser console for errors
- Verify file permissions
- Test network connectivity
- Clear browser cache and storage

### Monitoring
- Upload success rates
- File size trends
- User adoption metrics
- Performance benchmarks

### Updates
- Regular security updates
- Performance optimizations
- Feature enhancements
- Compatibility improvements

---

This media upload system provides technicians with powerful tools for documenting their work, while ensuring reliability in challenging network conditions. The mobile-first design and offline capabilities make it ideal for field work scenarios. 