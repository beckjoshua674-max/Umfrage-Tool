/**
 * Frontend Logic for "Ask Alma" Survey Tool
 * 
 * V1: This script currently only simulates a submission for the mockup.
 * In the future, this will dynamically load the survey config from the backend
 * and submit the responses via API.
 */

document.addEventListener('DOMContentLoaded', () => {
    const surveyForm = document.getElementById('survey-form');

    if (surveyForm) {
        surveyForm.addEventListener('submit', handleSurveySubmit);
    }
});

/**
 * Handles the submission of the survey form.
 * Prevents default reload, gathers data, and simulates an API POST request.
 * 
 * @param {Event} event 
 */
function handleSurveySubmit(event) {
    event.preventDefault(); // Prevent page reload

    // Gather form data
    const formData = new FormData(event.target);
    const results = {};
    
    for (let [key, value] of formData.entries()) {
        results[key] = value;
    }

    console.log('Gathered Survey Data:', results);

    // Validation (simple mockup check)
    if (!results.q1 || !results.q2) {
        alert('Bitte beantworten Sie alle Fragen, bevor Sie die Umfrage absenden.');
        return;
    }

    // TODO: In V1/V2, send this data to the backend via fetch() API.
    // Example:
    // fetch('/api/results', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(results)
    // })

    // Simulate successful submission
    simulateApiCall(results);
}

/**
 * Simulates a delay for an API call to show user feedback.
 */
function simulateApiCall(data) {
    const submitBtn = document.querySelector('.btn-primary');
    const originalText = submitBtn.textContent;
    
    submitBtn.textContent = 'Wird gesendet...';
    submitBtn.disabled = true;

    setTimeout(() => {
        alert('Vielen Dank! Ihre Antworten wurden erfolgreich gespeichert.');
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
        
        // Reset form after successful submission
        document.getElementById('survey-form').reset();
    }, 1000); // 1s simulated delay
}
