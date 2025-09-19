document.addEventListener('DOMContentLoaded', function() {

    // --- Create Post Modal ---
    const createPostModal = document.getElementById('create-post-modal');
    const createPostTriggers = document.querySelectorAll('.create-post-trigger');
    const createPostCloseBtn = createPostModal.querySelector('.close-btn');

    createPostTriggers.forEach(btn => {
        btn.onclick = () => createPostModal.style.display = 'block';
    });
    createPostCloseBtn.onclick = () => createPostModal.style.display = 'none';

    // --- Add Story Modal ---
    const addStoryModal = document.getElementById('add-story-modal');
    const addStoryBtn = document.getElementById('add-story-btn');
    const addStoryCloseBtn = addStoryModal.querySelector('.close-btn');

    if (addStoryBtn) {
        addStoryBtn.onclick = () => addStoryModal.style.display = 'block';
    }
    if (addStoryCloseBtn) {
        addStoryCloseBtn.onclick = () => addStoryModal.style.display = 'none';
    }

    // Close modals on outside click
    window.onclick = function(event) {
        if (event.target == createPostModal) {
            createPostModal.style.display = "none";
        }
        if (event.target == addStoryModal) {
            addStoryModal.style.display = "none";
        }
        if (event.target == storyViewerModal) {
            closeStoryViewer();
        }
    }

    // --- Story Viewer ---
    const storyViewerModal = document.getElementById('story-viewer-modal');
    const storyTriggers = document.querySelectorAll('.story:not(.add-story)');
    const closeStoryViewerBtn = document.querySelector('.close-story-viewer');

    const storyUserAvatar = document.querySelector('.story-user-avatar');
    const storyUserName = document.querySelector('.story-user-name');
    const storyImage = document.querySelector('.story-image');
    const storyVideo = document.querySelector('.story-video');
    const storyProgressBarsContainer = document.querySelector('.story-progress-bars');
    const storyNavPrev = document.querySelector('.story-nav.prev');
    const storyNavNext = document.querySelector('.story-nav.next');

    let currentUserStories = [];
    let currentStoryIndex = 0;
    let storyTimer;

    storyTriggers.forEach(trigger => {
        trigger.addEventListener('click', function() {
            const userId = this.dataset.userId;
            fetch(`/api/stories/${userId}`)
                .then(response => response.json())
                .then(data => {
                    if(data.stories.length > 0) {
                        currentUserStories = data.stories;
                        storyUserAvatar.src = data.user.avatar_url;
                        storyUserName.textContent = data.user.name;
                        currentStoryIndex = 0;
                        openStoryViewer();
                    }
                });
        });
    });

    function openStoryViewer() {
        renderStoryProgressBars();
        displayStory(currentStoryIndex);
        storyViewerModal.style.display = 'flex';
    }

    function closeStoryViewer() {
        clearTimeout(storyTimer);
        storyVideo.pause();
        storyViewerModal.style.display = 'none';
    }

    function displayStory(index) {
        // Reset progress bars
        document.querySelectorAll('.progress-bar-fill').forEach((bar, i) => {
            if (i < index) {
                bar.style.width = '100%';
            } else {
                bar.style.width = '0%';
            }
        });

        const story = currentUserStories[index];
        storyVideo.pause();
        storyImage.style.display = 'none';
        storyVideo.style.display = 'none';

        if(story.content_type.startsWith('image')) {
            storyImage.src = story.content_url;
            storyImage.style.display = 'block';
            startStoryTimer(10000); // 10 seconds for images
        } else if (story.content_type.startsWith('video')) {
            storyVideo.src = story.content_url;
            storyVideo.style.display = 'block';
            storyVideo.play();
            storyVideo.onloadedmetadata = () => {
                startStoryTimer(storyVideo.duration * 1000);
            };
        }
    }

    function startStoryTimer(duration) {
        clearTimeout(storyTimer);
        // Animate current progress bar
        const currentProgressBar = document.querySelectorAll('.progress-bar-fill')[currentStoryIndex];
        setTimeout(() => { currentProgressBar.style.width = '100%'; }, 50); // Small delay to trigger transition

        storyTimer = setTimeout(nextStory, duration);
    }

    function nextStory() {
        if (currentStoryIndex < currentUserStories.length - 1) {
            currentStoryIndex++;
            displayStory(currentStoryIndex);
        } else {
            closeStoryViewer();
        }
    }

    function prevStory() {
        if (currentStoryIndex > 0) {
            currentStoryIndex--;
            displayStory(currentStoryIndex);
        }
    }

    function renderStoryProgressBars() {
        storyProgressBarsContainer.innerHTML = '';
        for(let i = 0; i < currentUserStories.length; i++) {
            const barBackground = document.createElement('div');
            barBackground.className = 'progress-bar-background';
            const barFill = document.createElement('div');
            barFill.className = 'progress-bar-fill';
            barBackground.appendChild(barFill);
            storyProgressBarsContainer.appendChild(barBackground);
        }
    }

    if (closeStoryViewerBtn) closeStoryViewerBtn.addEventListener('click', closeStoryViewer);
    if (storyNavNext) storyNavNext.addEventListener('click', nextStory);
    if (storyNavPrev) storyNavPrev.addEventListener('click', prevStory);

    // --- See More Functionality ---
    document.querySelectorAll(".see-more-btn").forEach(button => {
        const content = button.previousElementSibling;
        if (content.scrollHeight <= 80) {
            button.style.display = "none";
        }
        button.addEventListener("click", () => {
            if (content.classList.contains("collapsed")) {
                content.classList.remove("collapsed");
                content.classList.add("expanded");
                button.textContent = "See Less";
            } else {
                content.classList.remove("expanded");
                content.classList.add("collapsed");
                button.textContent = "See More";
            }
        });
    });
});
