(function () {
    const BACKEND_URL = window.CONFIG.BACKEND_URL;

    document.addEventListener('DOMContentLoaded', () => {
        console.log('Text JS loaded');

        // Mode Switching Logic
        const modeBtns = document.querySelectorAll('.mode-btn');
        const textMode = document.getElementById('text-mode');
        const audioMode = document.getElementById('audio-mode');

        modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                console.log('Switching to mode:', mode);

                // Update button states
                modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Toggle mode content
                if (mode === 'text') {
                    textMode.classList.add('active');
                    audioMode.classList.remove('active');
                } else {
                    textMode.classList.remove('active');
                    audioMode.classList.add('active');
                }
            });
        });

        // Text Form Submission
        const textForm = document.getElementById('text-form');
        const resultsSection = document.getElementById('results-section');
        const errorSection = document.getElementById('error-section');
        const resetBtn = document.getElementById('reset-btn');
        const errorResetBtn = document.getElementById('error-reset-btn');

        textForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const transcript = document.getElementById('transcript').value;
            const duration = document.getElementById('text-duration').value || null;

            const submitBtn = textForm.querySelector('.submit-btn');
            const btnText = submitBtn.querySelector('.btn-text');
            const loader = submitBtn.querySelector('.loader');

            submitBtn.disabled = true;
            btnText.style.display = 'none';
            loader.classList.remove('hidden');

            try {
                const response = await fetch(`${BACKEND_URL}/score`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        transcript: transcript,
                        duration: duration ? parseInt(duration) : null
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log('Score result:', result);

                displayResults(result, false);

            } catch (error) {
                console.error('Error scoring text:', error);
                showError();
            } finally {
                submitBtn.disabled = false;
                btnText.style.display = 'inline';
                loader.classList.add('hidden');
            }
        });

        // Results Display
        function displayResults(result, showTranscription) {
            const inputSection = document.querySelector('.input-section');
            if (inputSection) inputSection.style.display = 'none';
            if (errorSection) errorSection.classList.add('hidden');
            if (resultsSection) resultsSection.classList.remove('hidden');

            const overallScore = result.overall_score || 0;
            document.getElementById('overall-score').textContent = overallScore;

            const circle = document.getElementById('score-circle');
            const circumference = 565;
            const offset = circumference - (overallScore / 100) * circumference;
            circle.style.strokeDashoffset = offset;

            if (showTranscription && result.transcription) {
                const transcriptionBox = document.getElementById('transcription-box');
                const transcriptionText = document.getElementById('transcription-text');
                transcriptionBox.classList.remove('hidden');
                transcriptionText.textContent = result.transcription;
            } else {
                document.getElementById('transcription-box').classList.add('hidden');
            }

            const breakdownItems = document.getElementById('breakdown-items');
            breakdownItems.innerHTML = '';

            if (result.breakdown) {
                result.breakdown.forEach(item => {
                    const percentage = (item.score / item.max) * 100;

                    const element = document.createElement('div');
                    element.className = 'breakdown-item';
                    element.innerHTML = `
                        <div class="breakdown-header">
                            <span class="criterion">${item.criterion}</span>
                            <span class="score-val">${item.score}/${item.max}</span>
                        </div>
                        <div class="progress-bg">
                            <div class="progress-fill" style="width: ${percentage}%"></div>
                        </div>
                        <div class="feedback">${item.feedback || ''}</div>
                    `;
                    breakdownItems.appendChild(element);
                });
            }
        }

        function showError() {
            const inputSection = document.querySelector('.input-section');
            if (inputSection) inputSection.style.display = 'none';
            if (resultsSection) resultsSection.classList.add('hidden');
            if (errorSection) errorSection.classList.remove('hidden');
        }

        function reset() {
            const inputSection = document.querySelector('.input-section');
            if (inputSection) inputSection.style.display = 'block';
            if (resultsSection) resultsSection.classList.add('hidden');
            if (errorSection) errorSection.classList.add('hidden');
            document.getElementById('transcription-box').classList.add('hidden');

            // Reset forms
            textForm.reset();

            // Reset circle animation
            const circle = document.getElementById('score-circle');
            if (circle) circle.style.strokeDashoffset = 565;
        }

        if (resetBtn) resetBtn.addEventListener('click', reset);
        if (errorResetBtn) errorResetBtn.addEventListener('click', reset);

        // Expose globally for audio.js (if needed)
        window.displayResults = displayResults;
        window.showError = showError;
    });
})();
