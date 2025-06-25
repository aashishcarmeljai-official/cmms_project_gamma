// JavaScript for Flask Web Application

// Check application health
async function checkHealth() {
    const statusElement = document.getElementById('status');
    const button = event.target;
    
    // Update button state
    button.disabled = true;
    button.innerHTML = 'Checking...';
    statusElement.textContent = 'Checking...';
    
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (response.ok) {
            statusElement.textContent = '✅ ' + data.message;
            statusElement.parentElement.className = 'alert alert-success';
        } else {
            statusElement.textContent = '❌ Error: ' + data.message;
            statusElement.parentElement.className = 'alert alert-danger';
        }
    } catch (error) {
        statusElement.textContent = '❌ Connection failed';
        statusElement.parentElement.className = 'alert alert-danger';
        console.error('Error:', error);
    } finally {
        // Reset button state
        button.disabled = false;
        button.innerHTML = 'Check Health';
    }
}

// Auto-check health on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check health after a short delay
    setTimeout(checkHealth, 1000);
    
    // Add smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Add loading animation
function showLoading(element) {
    element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
}

function hideLoading(element, originalText) {
    element.innerHTML = originalText;
} 