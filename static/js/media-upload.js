/**
 * Mobile-Friendly Media Upload System
 * Features: Offline support, progress tracking, compression, and enhanced UX
 */

class MediaUploadManager {
    constructor() {
        this.offlineQueue = [];
        this.isOnline = navigator.onLine;
        this.maxFileSize = 50 * 1024 * 1024; // 50MB
        this.supportedImageTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        this.supportedVideoTypes = ['video/mp4', 'video/webm', 'video/ogg'];
        this.supportedAudioTypes = ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'];
        
        this.initializeEventListeners();
        this.loadOfflineQueue();
    }

    initializeEventListeners() {
        // Online/offline status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processOfflineQueue();
            this.showNotification('Connection restored. Syncing offline data...', 'success');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showNotification('You are offline. Changes will be saved locally.', 'warning');
        });

        // Service Worker for offline support
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('Service Worker registered:', registration);
                })
                .catch(error => {
                    console.log('Service Worker registration failed:', error);
                });
        }
    }

    // File validation and compression
    async validateAndCompressFile(file, type) {
        return new Promise((resolve, reject) => {
            // Check file size
            if (file.size > this.maxFileSize) {
                reject(new Error(`File size exceeds ${this.maxFileSize / (1024 * 1024)}MB limit`));
                return;
            }

            // Check file type
            let supportedTypes;
            switch (type) {
                case 'image':
                    supportedTypes = this.supportedImageTypes;
                    break;
                case 'video':
                    supportedTypes = this.supportedVideoTypes;
                    break;
                case 'audio':
                    supportedTypes = this.supportedAudioTypes;
                    break;
                default:
                    reject(new Error('Unsupported file type'));
                    return;
            }

            if (!supportedTypes.includes(file.type)) {
                reject(new Error(`Unsupported file type: ${file.type}`));
                return;
            }

            // Compress images if needed
            if (type === 'image' && file.size > 5 * 1024 * 1024) { // 5MB
                this.compressImage(file)
                    .then(compressedFile => resolve(compressedFile))
                    .catch(error => resolve(file)); // Use original if compression fails
            } else {
                resolve(file);
            }
        });
    }

    // Image compression using Canvas
    async compressImage(file) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                // Calculate new dimensions (max 1920px width/height)
                const maxSize = 1920;
                let { width, height } = img;
                
                if (width > height) {
                    if (width > maxSize) {
                        height = (height * maxSize) / width;
                        width = maxSize;
                    }
                } else {
                    if (height > maxSize) {
                        width = (width * maxSize) / height;
                        height = maxSize;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                // Draw and compress
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob(
                    blob => {
                        const compressedFile = new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        });
                        resolve(compressedFile);
                    },
                    'image/jpeg',
                    0.8 // Quality
                );
            };

            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = URL.createObjectURL(file);
        });
    }

    // Upload with progress tracking
    async uploadFile(file, type, workOrderId, commentId = null) {
        const validatedFile = await this.validateAndCompressFile(file, type);
        
        if (!this.isOnline) {
            // Store for offline upload
            this.addToOfflineQueue(validatedFile, type, workOrderId, commentId);
            return { success: true, offline: true, message: 'File saved for offline upload' };
        }

        const formData = new FormData();
        formData.append('media_type', type);
        
        if (commentId) {
            formData.append('images', validatedFile);
        } else {
            formData.append('images', validatedFile);
        }

        const endpoint = commentId 
            ? `/api/work-orders/${workOrderId}/comments/${commentId}/upload-media`
            : `/api/work-orders/${workOrderId}/upload-media`;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(`${type} uploaded successfully!`, 'success');
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Upload failed:', error);
            // Fallback to offline storage
            this.addToOfflineQueue(validatedFile, type, workOrderId, commentId);
            this.showNotification('Upload failed. File saved for offline upload.', 'warning');
            return { success: false, offline: true, message: error.message };
        }
    }

    // Offline queue management
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
        this.updateOfflineIndicator();
    }

    async processOfflineQueue() {
        if (this.offlineQueue.length === 0) return;

        const itemsToProcess = [...this.offlineQueue];
        this.offlineQueue = [];
        this.saveOfflineQueue();

        for (const item of itemsToProcess) {
            try {
                await this.uploadFile(item.file, item.type, item.workOrderId, item.commentId);
            } catch (error) {
                // Re-add to queue if upload fails
                this.offlineQueue.push(item);
                console.error('Failed to process offline item:', error);
            }
        }

        this.saveOfflineQueue();
        this.updateOfflineIndicator();
    }

    saveOfflineQueue() {
        localStorage.setItem('mediaUploadQueue', JSON.stringify(this.offlineQueue));
    }

    loadOfflineQueue() {
        const saved = localStorage.getItem('mediaUploadQueue');
        if (saved) {
            try {
                this.offlineQueue = JSON.parse(saved);
                this.updateOfflineIndicator();
            } catch (error) {
                console.error('Failed to load offline queue:', error);
                this.offlineQueue = [];
            }
        }
    }

    updateOfflineIndicator() {
        const indicator = document.getElementById('offlineIndicator');
        if (indicator) {
            indicator.style.display = this.offlineQueue.length > 0 ? 'block' : 'none';
            indicator.textContent = `${this.offlineQueue.length} file(s) pending upload`;
        }
    }

    // Voice recording functionality
    async startVoiceRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 44100
                }
            });

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            const audioChunks = [];
            
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const audioFile = new File([audioBlob], `voice_note_${Date.now()}.webm`, {
                    type: 'audio/webm'
                });
                
                // Trigger upload or save to offline queue
                this.handleVoiceRecordingComplete(audioFile);
            };

            mediaRecorder.start();
            return mediaRecorder;

        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showNotification('Unable to access microphone', 'error');
            throw error;
        }
    }

    handleVoiceRecordingComplete(audioFile) {
        // This will be implemented by the specific page
        if (window.onVoiceRecordingComplete) {
            window.onVoiceRecordingComplete(audioFile);
        }
    }

    // Utility functions
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // File drag and drop support
    enableDragAndDrop(container, onFilesDrop) {
        container.addEventListener('dragover', (e) => {
            e.preventDefault();
            container.classList.add('drag-over');
        });

        container.addEventListener('dragleave', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');
        });

        container.addEventListener('drop', (e) => {
            e.preventDefault();
            container.classList.remove('drag-over');
            
            const files = Array.from(e.dataTransfer.files);
            onFilesDrop(files);
        });
    }

    // Generate preview for different file types
    generatePreview(file, container) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const preview = document.createElement('div');
            preview.className = 'media-preview-item';
            
            if (file.type.startsWith('image/')) {
                preview.innerHTML = `
                    <img src="${e.target.result}" alt="Preview" class="img-thumbnail">
                    <button type="button" class="btn btn-sm btn-danger remove-preview" onclick="this.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                `;
            } else if (file.type.startsWith('video/')) {
                preview.innerHTML = `
                    <video controls class="img-thumbnail">
                        <source src="${e.target.result}" type="${file.type}">
                    </video>
                    <button type="button" class="btn btn-sm btn-danger remove-preview" onclick="this.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                `;
            } else if (file.type.startsWith('audio/')) {
                preview.innerHTML = `
                    <div class="audio-preview">
                        <i class="fas fa-volume-up fa-2x text-primary"></i>
                        <p class="mb-0">${file.name}</p>
                        <button type="button" class="btn btn-sm btn-danger remove-preview" onclick="this.parentElement.parentElement.remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
            }
            
            container.appendChild(preview);
        };
        
        reader.readAsDataURL(file);
    }
}

// Initialize the media upload manager
const mediaUploadManager = new MediaUploadManager();

// Export for use in other scripts
window.MediaUploadManager = MediaUploadManager;
window.mediaUploadManager = mediaUploadManager; 