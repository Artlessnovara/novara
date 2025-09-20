document.addEventListener('DOMContentLoaded', () => {

    // --- Generic Modal Handler ---
    function setupModal(buttonSelector, modalId) {
        const openBtn = document.querySelector(buttonSelector);
        const modal = document.getElementById(modalId);
        if (!openBtn || !modal) {
            // console.warn(`Modal or button not found for: ${buttonSelector}, ${modalId}`);
            return;
        }

        const closeBtn = modal.querySelector('.close-btn');

        openBtn.addEventListener('click', () => modal.style.display = 'block');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => modal.style.display = 'none');
        }
        window.addEventListener('click', (event) => {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        });
    }

    // --- Generic AJAX Form Submission Handler ---
    function handleAjaxFormSubmit(formId, onSuccess) {
        const form = document.getElementById(formId);
        if (!form) {
            // console.warn(`Form not found: ${formId}`);
            return;
        }

        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const url = this.action;

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    onSuccess(data);
                    const modal = form.closest('.modal');
                    if (modal) {
                        modal.style.display = 'none';
                    }
                    form.reset();
                    // In a real app, you'd use a nicer notification system
                    console.log(data.message);
                } else {
                    console.error('Form submission error:', data.errors);
                    // Create a user-friendly error message
                    let errorMsg = 'Please correct the following errors:\n';
                    for (const field in data.errors) {
                        errorMsg += `\n- ${field}: ${data.errors[field].join(', ')}`;
                    }
                    alert(errorMsg);
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                alert('An unexpected network error occurred.');
            });
        });
    }

    // --- Setup All Modals ---
    setupModal('.profile-actions .btn-primary', 'edit-profile-modal');
    setupModal('.profile-certificates .btn-add', 'add-certificate-modal');
    setupModal('.profile-badges .btn-add', 'add-badge-modal');
    setupModal('.profile-social-links .btn-add', 'add-social-link-modal');

    // --- Setup All AJAX Form Submissions ---

    // Edit Profile
    handleAjaxFormSubmit('edit-profile-form', (data) => {
        if (data.user) {
            document.querySelector('.profile-info h1').textContent = data.user.name;
            document.querySelector('.profile-info .tagline').textContent = data.user.bio;
            if (data.user.profile_pic) {
                // Add a cache-busting query parameter to force image reload
                document.querySelector('.profile-pic img').src = `/static/profile_pics/${data.user.profile_pic}?t=${new Date().getTime()}`;
            }
        }
    });

    // Add Certificate
    handleAjaxFormSubmit('add-certificate-form', (data) => {
        const cert = data.certificate;
        const grid = document.querySelector('.certificates-grid');
        const noItemsMsg = grid.querySelector('p');
        if (noItemsMsg) noItemsMsg.remove();

        const newCertCard = `
            <div class="certificate-card">
                <div class="cert-icon"><i class="fas fa-award"></i></div>
                <div class="cert-details">
                    <h4>${cert.title}</h4>
                    <p>Issued: ${cert.issued_date}</p>
                </div>
            </div>`;
        grid.insertAdjacentHTML('beforeend', newCertCard);
    });

    // Add Badge
    handleAjaxFormSubmit('add-badge-form', (data) => {
        const badge = data.badge;
        const carousel = document.querySelector('.badges-carousel');
        const noItemsMsg = carousel.querySelector('p');
        if (noItemsMsg) noItemsMsg.remove();

        const newBadgeItem = `
            <div class="badge-item">
                <img src="${badge.icon_url}" alt="${badge.name}">
                <p>${badge.name}</p>
            </div>`;
        carousel.insertAdjacentHTML('beforeend', newBadgeItem);
    });

    // Add Social Link
    handleAjaxFormSubmit('add-social-link-form', (data) => {
        const link = data.link;
        const row = document.querySelector('.social-links-row');
        const noItemsMsg = row.querySelector('p');
        if (noItemsMsg) noItemsMsg.remove();

        const newLinkItem = `
            <a href="${link.url}" target="_blank" class="social-link-btn">
                <i class="fab fa-${link.platform}"></i>
            </a>`;
        row.insertAdjacentHTML('beforeend', newLinkItem);
    });

    // --- Animated Counters ---
    const counters = document.querySelectorAll('.animated-counter');
    const speed = 200;

    const animateCounter = (counter) => {
        const target = +counter.getAttribute('data-target');
        // Start from 0
        let count = 0;
        const isPercent = counter.innerText.includes('%');

        // Calculate increment
        const inc = target / speed;

        const updateCount = () => {
            if (count < target) {
                count += inc;
                // Ensure we don't overshoot the target
                if (count > target) count = target;
                counter.innerText = Math.ceil(count) + (isPercent ? '%' : '');
                setTimeout(updateCount, 1);
            } else {
                counter.innerText = target + (isPercent ? '%' : '');
            }
        };
        updateCount();
    };

    // Use Intersection Observer to trigger animation only when visible
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => {
        observer.observe(counter);
    });
});
