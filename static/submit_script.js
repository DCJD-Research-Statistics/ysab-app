function closeLoadingOverlay() {
    document.getElementById('loadingOverlay').style.display = 'none';
    
    // Re-enable form submission if needed
    const submitButton = document.getElementById('saveForm');
    submitButton.disabled = false;
  }

  const disclaimerCheckbox = document.getElementById('disclaimer_check');
  const submitButton = document.getElementById('saveForm');
  const loadingOverlay = document.getElementById('loadingOverlay');

  disclaimerCheckbox.addEventListener('change', function() {
    if (this.checked) {
      submitButton.style.backgroundColor = 'blue';
      submitButton.disabled = false;
    } else {
      submitButton.style.backgroundColor = 'grey';
      submitButton.disabled = true;
    }
  });

  // Form submission handler
  document.querySelector('form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    loadingOverlay.style.display = 'block';
    
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

  function beforeUnloadHandler(e) {
    if (!disclaimerCheckbox.checked) {
      const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave this page?';
      e.returnValue = confirmationMessage;
      return confirmationMessage;
    }
  }

  window.addEventListener('beforeunload', beforeUnloadHandler);