/**
 * Frontend Logic for "Ask Alma" Survey Tool
 */

let currentSurveyId = null;

document.addEventListener('DOMContentLoaded', () => {
    const surveyForm = document.getElementById('survey-form');
    
    if (surveyForm) {
        surveyForm.addEventListener('submit', handleSurveySubmit);
    }

    loadSurvey();
});

/**
 * Loads the survey configuration from the mock JSON file.
 */
async function loadSurvey() {
    const loadingEl = document.getElementById('loading');
    const formEl = document.getElementById('survey-form');
    const containerEl = document.getElementById('questions-container');

    loadingEl.classList.remove('hidden');
    formEl.classList.add('hidden');

    try {
        const response = await fetch('./mock-data/survey-questions.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentSurveyId = data.survey_id;
        
        // Build the UI
        buildSurveyUI(data.questions, containerEl);
        
        loadingEl.classList.add('hidden');
        formEl.classList.remove('hidden');
    } catch (error) {
        console.error('Error loading survey:', error);
        loadingEl.textContent = 'Fehler beim Laden der Umfrage.';
    }
}

/**
 * Dynamically builds the survey HTML elements.
 * 
 * @param {Array} questions 
 * @param {HTMLElement} container 
 */
function buildSurveyUI(questions, container) {
    container.innerHTML = ''; // Clear container

    questions.forEach((q, index) => {
        const block = document.createElement('div');
        block.className = 'question-block';
        block.id = q.id;

        if (q.type === 'text') {
            const label = document.createElement('label');
            label.className = 'question-label';
            label.htmlFor = `${q.id}-input`;
            label.textContent = q.label;
            
            const textarea = document.createElement('textarea');
            textarea.id = `${q.id}-input`;
            textarea.name = q.id;
            textarea.rows = 4;
            textarea.placeholder = "Ihre Antwort...";
            if (q.required) textarea.required = true;

            block.appendChild(label);
            block.appendChild(textarea);
        } else if (q.type === 'multiple_choice') {
            const label = document.createElement('p');
            label.className = 'question-label';
            label.textContent = q.label;

            const optionsDiv = document.createElement('div');
            optionsDiv.className = 'options';

            q.options.forEach(opt => {
                const optLabel = document.createElement('label');
                optLabel.className = 'option-label';
                
                const input = document.createElement('input');
                input.type = 'radio';
                input.name = q.id;
                input.value = opt.value;
                if (q.required) input.required = true; // browser will enforce at least one selection

                optLabel.appendChild(input);
                optLabel.appendChild(document.createTextNode(' ' + opt.text));
                optionsDiv.appendChild(optLabel);
            });

            block.appendChild(label);
            block.appendChild(optionsDiv);
        }

        container.appendChild(block);
    });
}

/**
 * Handles the submission of the survey form.
 * 
 * @param {Event} event 
 */
function handleSurveySubmit(event) {
    event.preventDefault(); // Prevent page reload

    // Gather form data
    const formData = new FormData(event.target);
    const answers = {};
    
    for (let [key, value] of formData.entries()) {
        answers[key] = value;
    }

    const payload = {
        survey_id: currentSurveyId,
        timestamp: new Date().toISOString(),
        answers: answers
    };

    console.log('Gathered Survey Data:', payload);

    // TODO: In V2, send this payload to the backend API via fetch()
    
    // Simulate successful submission
    simulateApiCall(payload);
}

/**
 * Simulates a delay for an API call to show user feedback.
 */
function simulateApiCall(payload) {
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
    }, 1000);
}
