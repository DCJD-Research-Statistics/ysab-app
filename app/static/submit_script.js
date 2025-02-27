function closeLoadingOverlay() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
    
    // Re-enable form submission if needed
    const submitButton = document.getElementById('saveForm');
    if (submitButton) {
        submitButton.disabled = false;
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    const disclaimerCheckbox = document.getElementById('disclaimer_check');
    const submitButton = document.getElementById('saveForm');
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (disclaimerCheckbox && submitButton) {
        disclaimerCheckbox.addEventListener('change', function() {
            if (this.checked) {
                submitButton.style.backgroundColor = 'blue';
                submitButton.disabled = false;
            } else {
                submitButton.style.backgroundColor = 'grey';
                submitButton.disabled = true;
            }
        });
    }

    // Form submission handler
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (loadingOverlay) {
                loadingOverlay.style.display = 'block';
            }
            
            window.removeEventListener('beforeunload', beforeUnloadHandler);
            
            if (this.checkValidity()) {
                setTimeout(() => {
                    this.submit();
                }, 100);
            } else {
                closeLoadingOverlay();
                this.reportValidity();
            }
        });
    }

    function beforeUnloadHandler(e) {
        if (disclaimerCheckbox && !disclaimerCheckbox.checked) {
            const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave this page?';
            e.returnValue = confirmationMessage;
            return confirmationMessage;
        }
    }

    window.addEventListener('beforeunload', beforeUnloadHandler);
});