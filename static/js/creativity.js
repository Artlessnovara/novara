document.addEventListener('DOMContentLoaded', function() {
    const fab = document.getElementById('fab-create');
    const modal = document.getElementById('create-modal');
    const closeModalBtn = modal.querySelector('.close-modal-btn');
    const modalFormContent = document.getElementById('modal-form-content');
    const tabs = document.querySelector('.creativity-tabs');

    // --- Modal and Form Loading ---
    function getActiveCategory() {
        const activeTab = tabs.querySelector('.tab-link.active');
        return activeTab ? activeTab.dataset.category : 'all';
    }

    function loadForm(category) {
        const invalidCategories = ['all', 'challenges', 'top_creators', 'reels'];
        if (invalidCategories.includes(category)) {
            let message = "You cannot create a post in this category.";
            if (category === 'reels') {
                message = "Please go to the main Reels page to upload a reel.";
            }
            modalFormContent.innerHTML = `<p>${message}</p>`;
            return;
        }

        fetch(`/feed/api/get_form/${category}`)
            .then(response => response.text())
            .then(html => {
                modalFormContent.innerHTML = html;
                // Add the category to the form for submission
                const form = modalFormContent.querySelector('form');
                if (form) {
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'category';
                    hiddenInput.value = category;
                    form.appendChild(hiddenInput);
                }
            })
            .catch(error => {
                console.error('Error loading form:', error);
                modalFormContent.innerHTML = '<p>Error loading form. Please try again.</p>';
            });
    }

    if (fab && modal && closeModalBtn && tabs) {
        fab.addEventListener('click', () => {
            const category = getActiveCategory();
            loadForm(category);
            modal.style.display = 'block';
        });

        closeModalBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        window.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    // --- General API handler for actions ---
    function handleAction(e) {
        const button = e.target.closest('.btn-action');
        if (!button) return;

        const { targetType, targetId, action } = button.dataset;

        let url = '';
        let body = {};
        let confirmationPrompt = null;

        if (action === 'like') {
            url = `/feed/api/${targetType}/${targetId}/like`;
        } else if (action === 'bookmark') {
            url = '/feed/api/bookmark';
            body = { target_type: targetType, target_id: targetId };
        } else if (action === 'share') {
            url = `/feed/api/${targetType}/${targetId}/share`;
            confirmationPrompt = "Add a comment to your share (optional):";
        } else {
            return;
        }

        const processRequest = (comment = null) => {
            if (comment !== null) {
                body.content = comment;
            }
            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: Object.keys(body).length ? JSON.stringify(body) : null
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateUI(button, action, data);
                } else {
                    alert(data.message || 'An error occurred.');
                }
            })
            .catch(error => console.error('Error:', error));
        };

        if (confirmationPrompt) {
            const comment = prompt(confirmationPrompt);
            // If user cancels prompt, comment will be null, so we don't proceed
            if (comment !== null) {
                processRequest(comment);
            }
        } else {
            processRequest();
        }
    }

    function updateUI(button, action, data) {
        if (action === 'like') {
            const likeCountSpan = button.querySelector('.like-count');
            if (likeCountSpan) {
                likeCountSpan.textContent = data.likes_count;
            }
            button.classList.toggle('liked', data.liked_by_user);
        } else if (action === 'bookmark') {
            button.classList.toggle('bookmarked', data.bookmarked);
        } else if (action === 'share') {
            alert(data.message || 'Shared successfully!');
            // Reload to see the flash message on the server-rendered page
            window.location.reload();
        }
    }

    document.querySelector('.tab-content-wrapper').addEventListener('click', handleAction);


    // --- Lightbox for Image Zoom ---
    const lightboxModal = document.getElementById('lightbox-modal');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const closeLightboxBtn = document.querySelector('.close-lightbox-btn');

    document.querySelectorAll('.zoomable-image').forEach(image => {
        image.addEventListener('click', function() {
            lightboxModal.style.display = 'block';
            lightboxImg.src = this.src;
            lightboxCaption.innerHTML = this.alt;
        });
    });

    if (closeLightboxBtn) {
        closeLightboxBtn.addEventListener('click', () => {
            lightboxModal.style.display = 'none';
        });
    }

    // Close lightbox if clicked outside of the image
    window.addEventListener('click', (e) => {
        if (e.target === lightboxModal) {
            lightboxModal.style.display = 'none';
        }
    });

    // --- Reel Card Hover to Play ---
    document.querySelectorAll('.reel-card').forEach(card => {
        const video = card.querySelector('video');
        card.addEventListener('mouseenter', () => {
            video.play();
        });
        card.addEventListener('mouseleave', () => {
            video.pause();
        });
    });
});
