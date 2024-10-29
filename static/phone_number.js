function formatPhoneNumber(input) {
    // Remove any non-numeric characters
    var phoneNumber = input.value.replace(/\D/g, '');

    // Check if the length is greater than 10, trim it
    if (phoneNumber.length > 10) {
      phoneNumber = phoneNumber.substr(0, 10);
    }

    // Add dashes in the required format
    var formattedPhoneNumber =
      phoneNumber.slice(0, 3) + '-' + phoneNumber.slice(3, 6) + '-' + phoneNumber.slice(6, 10);

    // Update the input field value
    input.value = formattedPhoneNumber;
  }