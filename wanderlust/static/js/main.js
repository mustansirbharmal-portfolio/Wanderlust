document.addEventListener('DOMContentLoaded', function() {
    // Generate Activity Button
    const generateBtn = document.getElementById('generate-wander');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateActivity);
    }

    // Complete Activity Button
    const completeButtons = document.querySelectorAll('.complete-activity');
    completeButtons.forEach(button => {
        button.addEventListener('click', completeActivity);
    });

    // Category Filter Buttons
    const categoryButtons = document.querySelectorAll('.category-filter');
    categoryButtons.forEach(button => {
        button.addEventListener('click', filterActivities);
    });
});

async function generateActivity() {
    const category = document.querySelector('input[name="category"]:checked')?.value || 'random';
    const difficulty = document.querySelector('input[name="difficulty"]:checked')?.value || 'random';

    try {
        const response = await fetch('/generate_activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ category, difficulty })
        });

        if (!response.ok) throw new Error('Failed to generate activity');

        const activity = await response.json();
        displayActivity(activity);
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to generate activity. Please try again.');
    }
}

function displayActivity(activity) {
    const activityContainer = document.getElementById('activity-display');
    activityContainer.innerHTML = `
        <div class="card activity-card fade-in">
            <div class="activity-header">
                <h3>${activity.title}</h3>
                <span class="difficulty ${activity.difficulty.toLowerCase()}">${activity.difficulty}</span>
            </div>
            <p>${activity.description}</p>
            <div class="activity-details">
                <p><i class="fas fa-clock"></i> ${activity.duration} minutes</p>
                <p><i class="fas fa-map-marker-alt"></i> ${activity.location}</p>
            </div>
            <div class="activity-actions">
                <button class="btn btn-primary complete-activity" data-id="${activity.id}">Complete</button>
                <button class="btn btn-secondary save-activity" data-id="${activity.id}">Save for Later</button>
            </div>
        </div>
    `;
}

async function completeActivity(event) {
    const activityId = event.target.dataset.id;
    try {
        const response = await fetch(`/complete_activity/${activityId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) throw new Error('Failed to complete activity');

        const result = await response.json();
        if (result.success) {
            showSuccess('Activity completed! Points added to your profile.');
            updatePoints();
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to complete activity. Please try again.');
    }
}

function filterActivities(event) {
    const category = event.target.dataset.category;
    const activities = document.querySelectorAll('.activity-card');
    
    activities.forEach(activity => {
        if (category === 'all' || activity.dataset.category === category) {
            activity.style.display = 'block';
        } else {
            activity.style.display = 'none';
        }
    });
}

function updatePoints() {
    const pointsElement = document.getElementById('user-points');
    if (pointsElement) {
        fetch('/get_points')
            .then(response => response.json())
            .then(data => {
                pointsElement.textContent = data.points;
            })
            .catch(error => console.error('Error updating points:', error));
    }
}

function showSuccess(message) {
    const toast = document.createElement('div');
    toast.className = 'toast success fade-in';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function showError(message) {
    const toast = document.createElement('div');
    toast.className = 'toast error fade-in';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
