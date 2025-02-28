$(document).ready(function() {
    $('#divisionAllocationsForm').submit(function(event) {
        event.preventDefault();
        var formData = {};
        $('.form-control').each(function() {
            formData[this.name] = $(this).val();
        });
        $.ajax({
            url: $('#divisionAllocationsForm').data('url'),
            type: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    alert('Division allocations updated successfully!');
                } else {
                    alert('Failed to update division allocations: ' + response.error);
                }
            },
            error: function(xhr, status, error) {
                alert('An error occurred: ' + xhr.responseText);
            }
        });
    });

    function updateTotal() {
        var total = 0;
        $('.form-control').each(function() {
            if (this.name !== 'totalAllocation') {
                total += Number($(this).val());
            }
        });
        $('#totalAllocation').val(total);
    }

    $('.form-control').on('input', updateTotal);
    updateTotal();
});