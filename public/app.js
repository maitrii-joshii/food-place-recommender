document.addEventListener('DOMContentLoaded', () => {
    const formSection = document.getElementById('form-section');
    const resultsSection = document.getElementById('results-section');
    const form = document.getElementById('preferences-form');
    const locationSelect = document.getElementById('location');
    const cuisineOptions = document.getElementById('cuisine-options');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner');
    const recommendationsContainer = document.getElementById('recommendations-container');
    const resetBtn = document.getElementById('reset-btn');
    const loadingState = document.getElementById('loading-state');

    // 1. Fetch metadata to populate dropdowns
    async function loadMetadata() {
        try {
            const response = await fetch('/api/metadata');
            if (!response.ok) throw new Error('Failed to load metadata');
            
            const data = await response.json();
            
            // Populate cities
            locationSelect.innerHTML = '<option value="" disabled selected>Select a city</option>';
            data.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                // Capitalize first letter of each word
                option.textContent = city.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                locationSelect.appendChild(option);
            });

            // Populate cuisines datalist
            cuisineOptions.innerHTML = '';
            data.cuisines.forEach(cuisine => {
                const option = document.createElement('option');
                option.value = cuisine.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                cuisineOptions.appendChild(option);
            });
            
        } catch (error) {
            console.error('Error loading metadata:', error);
            locationSelect.innerHTML = '<option value="" disabled selected>Error loading cities</option>';
        }
    }

    // 2. Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // UI Loading State
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        spinner.classList.remove('hidden');
        
        const formData = new FormData(form);
        const requestData = {
            location: formData.get('location'),
            budget: formData.get('budget'),
            cuisine: formData.get('cuisine') || "",
            min_rating: formData.get('min_rating') || "0",
            extra_preferences: formData.get('extra_preferences') || ""
        };

        try {
            // Show results section with shimmer loading
            formSection.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            loadingState.classList.remove('hidden');
            recommendationsContainer.innerHTML = '';

            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();
            
            loadingState.classList.add('hidden');

            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred while fetching recommendations');
            }

            renderRecommendations(data.recommendations);

        } catch (error) {
            loadingState.classList.add('hidden');
            recommendationsContainer.innerHTML = `
                <div class="recommendation-card" style="border-color: var(--error-color)">
                    <div class="card-content">
                        <h3 style="color: var(--error-color)">Oops!</h3>
                        <p>${error.message}</p>
                    </div>
                </div>
            `;
        } finally {
            // Restore button state (hidden anyway since form is hidden)
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            spinner.classList.add('hidden');
        }
    });

    // 3. Render the results
    function renderRecommendations(recommendations) {
        recommendationsContainer.innerHTML = '';
        
        if (!recommendations || recommendations.length === 0) {
            recommendationsContainer.innerHTML = '<p>No recommendations found.</p>';
            return;
        }

        const medals = ['🥇', '🥈', '🥉'];

        recommendations.forEach((rec, index) => {
            const card = document.createElement('div');
            card.className = 'recommendation-card';
            
            // Animation staggered entrance
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.animation = `fadeUp 0.5s ease forwards ${index * 0.15}s`;

            const rankBadge = document.createElement('div');
            rankBadge.className = 'rank-badge';
            rankBadge.textContent = medals[index] || `#${index + 1}`;

            const content = document.createElement('div');
            content.className = 'card-content';
            
            const title = document.createElement('h3');
            title.textContent = rec.name;
            
            const desc = document.createElement('p');
            desc.textContent = rec.explanation;

            content.appendChild(title);
            content.appendChild(desc);
            
            card.appendChild(rankBadge);
            card.appendChild(content);

            recommendationsContainer.appendChild(card);
        });

        // Add keyframes dynamically if not present
        if (!document.getElementById('dynamic-animations')) {
            const style = document.createElement('style');
            style.id = 'dynamic-animations';
            style.textContent = `
                @keyframes fadeUp {
                    to { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // 4. Handle Reset
    resetBtn.addEventListener('click', () => {
        resultsSection.classList.add('hidden');
        formSection.classList.remove('hidden');
        recommendationsContainer.innerHTML = '';
        // Note: we don't clear the form so users can tweak their previous preferences
    });

    // Initialize
    loadMetadata();
});
