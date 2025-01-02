document.addEventListener('DOMContentLoaded', function() {
    // Initialize challenge features
    initializeChallenges();
    
    // Update timers every minute
    updateTimers();
    setInterval(updateTimers, 60000);
});

function initializeChallenges() {
    // Generate challenge button
    const generateBtn = document.querySelector('.generate-challenge');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateChallenge);
    }

    // Accept challenge buttons
    document.querySelectorAll('.accept-challenge').forEach(btn => {
        btn.addEventListener('click', function() {
            acceptChallenge(this.dataset.challengeId);
        });
    });

    // Complete activity buttons
    document.querySelectorAll('.complete-activity').forEach(btn => {
        btn.addEventListener('click', function() {
            completeActivity(this.dataset.challengeId, this.dataset.activityIndex);
        });
    });
}

function generateChallenge() {
    const difficulty = document.querySelector('.challenge-difficulty').value;
    
    fetch('/challenges/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ difficulty: difficulty })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('success', 'New challenge generated!');
            location.reload();
        } else {
            showAlert('error', data.message);
        }
    })
    .catch(error => {
        showAlert('error', 'Failed to generate challenge');
    });
}

function acceptChallenge(challengeId) {
    fetch(`/challenges/accept/${challengeId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('success', data.message);
            location.reload();
        } else {
            showAlert('error', data.message);
        }
    })
    .catch(error => {
        showAlert('error', 'Failed to accept challenge');
    });
}

function completeActivity(challengeId, activityIndex) {
    fetch(`/challenges/complete-activity/${challengeId}/${activityIndex}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            updateProgress(challengeId, data.progress);
            if (data.challenge_completed) {
                showAlert('success', `Challenge completed! You earned ${data.points_earned} points!`);
                location.reload();
            } else {
                showAlert('success', 'Activity completed!');
                updateActivityUI(challengeId, activityIndex);
            }
        } else {
            showAlert('error', data.message);
        }
    })
    .catch(error => {
        showAlert('error', 'Failed to complete activity');
    });
}

function updateProgress(challengeId, progress) {
    const progressBar = document.querySelector(`#challenge-${challengeId} .progress-bar .progress`);
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
}

function updateActivityUI(challengeId, activityIndex) {
    const activityElement = document.querySelector(`#challenge-${challengeId} .activity-${activityIndex}`);
    if (activityElement) {
        activityElement.classList.add('completed');
        const icon = activityElement.querySelector('i');
        if (icon) {
            icon.classList.remove('fa-circle');
            icon.classList.add('fa-check-circle');
        }
        const completeBtn = activityElement.querySelector('.complete-activity');
        if (completeBtn) {
            completeBtn.remove();
        }
    }
}

function updateTimers() {
    document.querySelectorAll('.challenge-timer').forEach(timer => {
        const endTime = new Date(timer.dataset.endTime);
        const now = new Date();
        const timeLeft = endTime - now;

        if (timeLeft <= 0) {
            timer.innerHTML = '<span class="expired">Expired</span>';
        } else {
            const hours = Math.floor(timeLeft / (1000 * 60 * 60));
            const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
            timer.querySelector('.time-remaining').textContent = 
                `${hours}h ${minutes}m remaining`;
        }
    });
}

function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} fade-in`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.challenges-section');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.classList.add('fade-out');
        setTimeout(() => alertDiv.remove(), 500);
    }, 4500);
}