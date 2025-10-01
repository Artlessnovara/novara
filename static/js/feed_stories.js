document.addEventListener('DOMContentLoaded', function() {
    // --- Story Creation Modal Logic ---
    const createStoryModal = document.getElementById('create-story-modal');
    const createStoryCard = document.getElementById('create-story-card');
    const createStoryFromInput = document.getElementById('create-story-from-input');
    const closeCreateStoryModal = document.getElementById('close-create-story-modal');
    const storyMediaInput = document.getElementById('story-media-input');
    const storyPreview = document.getElementById('story-preview');

    function openCreateStoryModal() {
        if(createStoryModal) createStoryModal.style.display = 'block';
    }

    function closeCreateStoryModalFunc() {
        if(createStoryModal) {
            createStoryModal.style.display = 'none';
            if(storyMediaInput) storyMediaInput.value = ''; // Reset file input
            if(storyPreview) storyPreview.style.display = 'none'; // Hide preview
        }
    }

    if(createStoryCard) createStoryCard.addEventListener('click', openCreateStoryModal);
    if(createStoryFromInput) createStoryFromInput.addEventListener('click', openCreateStoryModal);
    if(closeCreateStoryModal) closeCreateStoryModal.addEventListener('click', closeCreateStoryModalFunc);

    if(storyMediaInput) {
        storyMediaInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    if (file.type.startsWith('image/')) {
                        storyPreview.src = e.target.result;
                        storyPreview.style.display = 'block';
                    } else {
                        storyPreview.style.display = 'none';
                    }
                }
                reader.readAsDataURL(file);
            }
        });
    }

    // --- Story Viewer Logic ---
    const storyViewerModal = document.getElementById('story-viewer-modal');
    const storyViewerImage = document.getElementById('story-viewer-image');
    const storyViewerVideo = document.getElementById('story-viewer-video');
    const storyAuthorAvatar = document.querySelector('.story-author-avatar');
    const storyAuthorName = document.querySelector('.story-author-name');
    const storyProgressBarsContainer = document.querySelector('.story-progress-bars');
    const storyCloseBtn = document.getElementById('story-close-btn');
    const storyPauseBtn = document.getElementById('story-pause-btn');
    const storyPrevBtn = document.getElementById('story-prev-btn');
    const storyNextBtn = document.getElementById('story-next-btn');

    let allUserStories = {};
    let currentUserStories = [];
    let currentStoryIndex = 0;
    let storyTimer;
    let isPaused = false;
    const STORY_DURATION = 5000; // 5 seconds for images

    document.querySelectorAll('.story-card:not(.create-story-card)').forEach(card => {
        card.addEventListener('click', () => {
            const userId = card.dataset.userId;
            openStoryViewer(userId);
        });
    });

    function openStoryViewer(userId) {
        fetch(`/api/stories/${userId}`)
            .then(response => response.json())
            .then(data => {
                if (data.stories && data.stories.length > 0) {
                    currentUserStories = data.stories;
                    allUserStories[userId] = data;
                    currentStoryIndex = 0;
                    if(storyViewerModal) storyViewerModal.style.display = 'flex';
                    showStory(currentStoryIndex);
                }
            });
    }

    function showStory(index) {
        if (index < 0 || index >= currentUserStories.length) {
            closeStoryViewer();
            return;
        }

        isPaused = false;
        if(storyPauseBtn) storyPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        const story = currentUserStories[index];
        const author = allUserStories[story.user_id].user;

        if(storyAuthorAvatar) storyAuthorAvatar.src = author.avatar_url;
        if(storyAuthorName) storyAuthorName.textContent = author.name;

        // Create progress bars
        if(storyProgressBarsContainer) {
            storyProgressBarsContainer.innerHTML = '';
            currentUserStories.forEach((s, i) => {
                const bar = document.createElement('div');
                bar.className = 'progress-bar';
                const fill = document.createElement('div');
                fill.className = 'progress-bar-fill';
                if (i < index) {
                    fill.style.width = '100%';
                }
                bar.appendChild(fill);
                storyProgressBarsContainer.appendChild(bar);
            });
        }


        if(storyViewerImage) storyViewerImage.style.display = 'none';
        if(storyViewerVideo) {
            storyViewerVideo.style.display = 'none';
            storyViewerVideo.pause();
        }
        clearTimeout(storyTimer);

        const currentProgressBarFill = storyProgressBarsContainer.children[index].firstChild;

        if (story.media_type === 'image') {
            storyViewerImage.src = story.media_url;
            storyViewerImage.style.display = 'block';
            startTimer(currentProgressBarFill, STORY_DURATION);
        } else if (story.media_type === 'video') {
            storyViewerVideo.src = story.media_url;
            storyViewerVideo.style.display = 'block';
            storyViewerVideo.currentTime = 0;

            storyViewerVideo.onloadedmetadata = () => {
                storyViewerVideo.play();
                startTimer(currentProgressBarFill, storyViewerVideo.duration * 1000);
            };
            storyViewerVideo.onended = () => nextStory();
        }
    }

    function startTimer(progressBarFill, duration) {
        progressBarFill.style.transition = 'none';
        progressBarFill.style.width = '0%';
        void progressBarFill.offsetWidth;
        progressBarFill.style.transition = `width ${duration / 1000}s linear`;
        progressBarFill.style.width = '100%';
        clearTimeout(storyTimer);
        storyTimer = setTimeout(nextStory, duration);
    }

    function nextStory() {
        showStory(++currentStoryIndex);
    }

    function prevStory() {
        showStory(--currentStoryIndex);
    }

    function closeStoryViewer() {
        if(storyViewerModal) storyViewerModal.style.display = 'none';
        clearTimeout(storyTimer);
        if(storyViewerVideo) {
            storyViewerVideo.pause();
            storyViewerVideo.src = '';
        }
        if(storyViewerImage) storyViewerImage.src = '';
    }

    if(storyCloseBtn) storyCloseBtn.addEventListener('click', closeStoryViewer);
    if(storyNextBtn) storyNextBtn.addEventListener('click', nextStory);
    if(storyPrevBtn) storyPrevBtn.addEventListener('click', prevStory);
    if(storyPauseBtn) {
        storyPauseBtn.addEventListener('click', () => {
            isPaused = !isPaused;
            if(isPaused) {
                clearTimeout(storyTimer);
                if(storyViewerVideo.style.display === 'block') storyViewerVideo.pause();
                storyPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
            } else {
                resumeStory();
            }
        });
    }

    function resumeStory() {
        isPaused = false;
        const currentProgressBarFill = storyProgressBarsContainer.children[currentStoryIndex].firstChild;
        const currentWidth = parseFloat(getComputedStyle(currentProgressBarFill).width) / parseFloat(currentProgressBarFill.parentElement.offsetWidth) * 100;
        let duration = STORY_DURATION;

        if (storyViewerVideo.style.display === 'block' && !storyViewerVideo.paused) {
            duration = storyViewerVideo.duration * 1000;
        }

        const remainingDuration = duration * (1 - (currentWidth / 100));

        currentProgressBarFill.style.transition = `width ${remainingDuration / 1000}s linear`;
        currentProgressBarFill.style.width = '100%';

        storyTimer = setTimeout(nextStory, remainingDuration);
        storyPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';

        if (storyViewerVideo.style.display === 'block' && storyViewerVideo.paused) {
            storyViewerVideo.play();
        }
    }

    // --- Story Viewers Modal Logic ---
    const storyViewersModal = document.getElementById('story-viewers-modal');
    const viewStoryViewersBtn = document.getElementById('view-story-viewers-btn');
    const closeStoryViewersModalBtn = document.getElementById('close-story-viewers-modal');
    const storyViewersList = document.getElementById('story-viewers-list');

    if(viewStoryViewersBtn) {
        viewStoryViewersBtn.addEventListener('click', () => {
            const storyId = currentUserStories[currentStoryIndex].id;
            fetch(`/api/stories/${storyId}/viewers`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        storyViewersList.innerHTML = '';
                        if (data.viewers.length > 0) {
                            data.viewers.forEach(viewer => {
                                const viewerEl = document.createElement('div');
                                viewerEl.className = 'user-list-item';
                                viewerEl.innerHTML = `
                                    <div class="user-info">
                                        <img src="${viewer.avatar_url}" alt="${viewer.name}" class="profile-pic-small">
                                        <span>${viewer.name}</span>
                                    </div>
                                `;
                                storyViewersList.appendChild(viewerEl);
                            });
                        } else {
                            storyViewersList.innerHTML = '<p>No viewers yet.</p>';
                        }
                        if(storyViewersModal) storyViewersModal.style.display = 'block';
                    }
                });
        });
    }

    if(closeStoryViewersModalBtn) {
        closeStoryViewersModalBtn.addEventListener('click', () => {
            if(storyViewersModal) storyViewersModal.style.display = 'none';
        });
    }

    // --- Global Click Listener to Close Modals ---
    window.addEventListener('click', (event) => {
        if (event.target == createStoryModal) {
            closeCreateStoryModalFunc();
        }
        if (event.target == storyViewerModal) {
            closeStoryViewer();
        }
        if (event.target == storyViewersModal) {
            storyViewersModal.style.display = 'none';
        }
    });
});