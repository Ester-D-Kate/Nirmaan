(function () {
    const BACKEND_URL = window.CONFIG.BACKEND_URL;

    document.addEventListener('DOMContentLoaded', () => {
        console.log('Audio JS loaded');

        const recordTab = document.querySelector('[data-tab="record"]');
        const uploadTab = document.querySelector('[data-tab="upload"]');
        const recordTabContent = document.getElementById('record-tab');
        const uploadTabContent = document.getElementById('upload-tab');

        const recordBtn = document.getElementById('record-btn');
        const audioPlayback = document.getElementById('audio-playback');
        const submitRecordingBtn = document.getElementById('submit-recording');

        const audioUploadForm = document.getElementById('audio-upload-form');
        const audioFileInput = document.getElementById('audio-file');
        const fileNameDisplay = document.getElementById('file-name');
        const recordingTime = document.getElementById('recording-time');
        const statusText = document.querySelector('.status-text');

        const resultsSection = document.getElementById('results-section');
        const errorSection = document.getElementById('error-section');
        const resetBtn = document.getElementById('reset-btn');
        const errorResetBtn = document.getElementById('error-reset-btn');

        let mediaRecorder;
        let audioChunks = [];
        let recordedBlob;
        let recordingInterval;
        let seconds = 0;

        if (!recordTab || !uploadTab) {
            console.error('Audio tabs not found');
            return;
        }

        // Tab Switching Logic
        recordTab.addEventListener('click', () => {
            recordTab.classList.add('active');
            uploadTab.classList.remove('active');
            recordTabContent.classList.add('active');
            uploadTabContent.classList.remove('active');
        });

        uploadTab.addEventListener('click', () => {
            uploadTab.classList.add('active');
            recordTab.classList.remove('active');
            uploadTabContent.classList.add('active');
            recordTabContent.classList.remove('active');
        });

        // Record Button Logic (Start / Stop)
        recordBtn.addEventListener('click', async () => {
            console.log('Record button clicked. Current state:', mediaRecorder ? mediaRecorder.state : 'inactive');
            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                await startRecording();
            } else {
                stopRecording();
            }
        });

        async function startRecording() {
            try {
                console.log('Requesting microphone access...');
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                console.log('Microphone access granted');

                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                seconds = 0;

                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });

                mediaRecorder.addEventListener('stop', () => {
                    console.log('Recording stopped');
                    // Use the actual MIME type from the recorder
                    const mimeType = mediaRecorder.mimeType || 'audio/webm';
                    recordedBlob = new Blob(audioChunks, { type: mimeType });
                    console.log('Recorded audio type:', mimeType);
                    const audioUrl = URL.createObjectURL(recordedBlob);
                    audioPlayback.src = audioUrl;
                    audioPlayback.classList.remove('hidden');
                    submitRecordingBtn.classList.remove('hidden');
                    statusText.textContent = 'Recording complete. Review or submit.';

                    // Reset UI
                    recordBtn.classList.remove('recording');
                    clearInterval(recordingInterval);
                });

                mediaRecorder.start();
                console.log('MediaRecorder started');

                // Update UI for Recording State
                recordBtn.classList.add('recording');
                submitRecordingBtn.classList.add('hidden');
                audioPlayback.classList.add('hidden');

                statusText.textContent = 'Recording... Tap square to stop';
                recordingTime.textContent = '00:00';

                startTimer();

            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Unable to access microphone. Please check permissions.');
            }
        }

        function stopRecording() {
            if (mediaRecorder && (mediaRecorder.state === 'recording' || mediaRecorder.state === 'paused')) {
                console.log('Stopping recording...');
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        }

        function startTimer() {
            clearInterval(recordingInterval);
            recordingInterval = setInterval(() => {
                seconds++;
                const mins = Math.floor(seconds / 60);
                const secs = seconds % 60;
                recordingTime.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
            }, 1000);
        }

        // Submit Recording Logic
        submitRecordingBtn.addEventListener('click', async () => {
            if (!recordedBlob) return;

            const btnText = submitRecordingBtn.querySelector('.btn-text');
            const loader = submitRecordingBtn.querySelector('.loader');

            submitRecordingBtn.disabled = true;
            btnText.style.display = 'none';
            loader.classList.remove('hidden');

            try {
                const formData = new FormData();
                // Use appropriate file extension based on MIME type
                const extension = recordedBlob.type.includes('webm') ? 'webm' : 'wav';
                formData.append('audio_file', recordedBlob, `recording.${extension}`);
                formData.append('duration', seconds);

                console.log('Submitting recording...');

                const response = await fetch(`${BACKEND_URL}/audio/score`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log('Audio score result:', result);

                displayResults(result, true);

            } catch (error) {
                console.error('Error scoring audio:', error);
                showError();
            } finally {
                submitRecordingBtn.disabled = false;
                btnText.style.display = 'inline';
                loader.classList.add('hidden');
            }
        });

        // File Upload Logic
        audioFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                fileNameDisplay.textContent = file.name;
            } else {
                fileNameDisplay.textContent = 'Click to browse audio file';
            }
        });

        // Helper function to extract audio duration
        function getAudioDuration(file) {
            return new Promise((resolve, reject) => {
                const audio = new Audio();
                const objectUrl = URL.createObjectURL(file);

                audio.addEventListener('loadedmetadata', () => {
                    URL.revokeObjectURL(objectUrl);
                    resolve(audio.duration);
                });

                audio.addEventListener('error', () => {
                    URL.revokeObjectURL(objectUrl);
                    reject(new Error('Failed to load audio metadata'));
                });

                audio.src = objectUrl;
            });
        }

        audioUploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const file = audioFileInput.files[0];
            if (!file) {
                alert('Please choose an audio file');
                return;
            }

            const submitBtn = audioUploadForm.querySelector('.submit-btn');
            const btnText = submitBtn.querySelector('.btn-text');
            const loader = submitBtn.querySelector('.loader');

            submitBtn.disabled = true;
            btnText.style.display = 'none';
            loader.classList.remove('hidden');

            try {
                // Extract duration from audio file
                const duration = await getAudioDuration(file);
                console.log('Extracted audio duration:', duration, 'seconds');

                const formData = new FormData();
                formData.append('audio_file', file);
                formData.append('duration', Math.round(duration)); // Send duration in seconds

                console.log('Uploading file...');

                const response = await fetch(`${BACKEND_URL}/audio/score`, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();
                console.log('Audio upload score result:', result);

                displayResults(result, true);

            } catch (error) {
                console.error('Error uploading audio:', error);
                showError();
            } finally {
                submitBtn.disabled = false;
                btnText.style.display = 'inline';
                loader.classList.add('hidden');
            }
        });

        // Results Display Logic
        function displayResults(result, showTranscription) {
            console.log('displayResults called with:', result);

            const inputSection = document.querySelector('.input-section');
            console.log('Elements found:', {
                inputSection,
                resultsSection,
                errorSection,
                overallScoreEl: document.getElementById('overall-score'),
                circle: document.getElementById('score-circle')
            });

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
            if (audioUploadForm) audioUploadForm.reset();
            fileNameDisplay.textContent = 'Click to browse audio file';

            // Reset circle animation
            const circle = document.getElementById('score-circle');
            if (circle) circle.style.strokeDashoffset = 565;
        }

        if (resetBtn) resetBtn.addEventListener('click', reset);
        if (errorResetBtn) errorResetBtn.addEventListener('click', reset);

    });
})();
