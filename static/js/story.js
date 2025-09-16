document.addEventListener('DOMContentLoaded', function() {
    const storyCards = document.querySelectorAll('.story-card:not(.create-story-card)');

    if (storyCards.length > 0) {
        const storyViewer = document.createElement('div');
        storyViewer.classList.add('story-viewer');
        storyViewer.innerHTML = `
            <span class="close-btn">&times;</span>
            <div class="story-header">
                <div class="story-user-info">
                    <img src="" alt="" class="story-user-avatar">
                    <span class="story-user-name"></span>
                </div>
                <div class="story-actions">
                    <button class="story-action-btn" id="mute-btn"><i class="fas fa-volume-up"></i></button>
                    <button class="story-action-btn" id="more-btn"><i class="fas fa-ellipsis-v"></i></button>
                </div>
            </div>
            <div class="story-viewer-content"></div>
            <div class="story-progress-bars"></div>
            <div class="story-nav-left"></div>
            <div class="story-nav-right"></div>
            <div class="more-menu">
                <a href="#" class="more-menu-item">Report</a>
                <a href="#" class="more-menu-item">Copy Link</a>
            </div>
        `;
        document.body.appendChild(storyViewer);

        const closeBtn = storyViewer.querySelector('.close-btn');
        const storyHeader = storyViewer.querySelector('.story-header');
        const storyUserAvatar = storyHeader.querySelector('.story-user-avatar');
        const storyUserName = storyHeader.querySelector('.story-user-name');
        const muteBtn = storyHeader.querySelector('#mute-btn');
        const moreBtn = storyHeader.querySelector('#more-btn');
        const moreMenu = storyViewer.querySelector('.more-menu');
        const storyContent = storyViewer.querySelector('.story-viewer-content');
        const progressBarsContainer = storyViewer.querySelector('.story-progress-bars');
        const navLeft = storyViewer.querySelector('.story-nav-left');
        const navRight = storyViewer.querySelector('.story-nav-right');

        let allUsersWithStories = [];
        let currentUserIndex = 0;
        let currentStoryIndex = 0;
        let progressTimeout;
        let currentUserStories = [];
        let currentVideoElement = null;

        storyCards.forEach((card) => {
            card.addEventListener('click', () => {
                const userId = card.dataset.userId;
                allUsersWithStories = Array.from(storyCards).map(c => c.dataset.userId);
                currentUserIndex = allUsersWithStories.indexOf(userId);
                loadUserStories(userId);
            });
        });

        function loadUserStories(userId) {
            fetch(`/feed/api/stories/${userId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.stories.length > 0) {
                        currentUserStories = data.stories;
                        storyUserAvatar.src = data.user_info.profile_pic;
                        storyUserName.textContent = data.user_info.name;
                        currentStoryIndex = 0;
                        openStoryViewer();
                    }
                });
        }

        function openStoryViewer() {
            storyViewer.style.display = 'block';
            showStory(currentStoryIndex);
        }

        function closeStoryViewer() {
            storyViewer.style.display = 'none';
            clearTimeout(progressTimeout);
            if (currentVideoElement) {
                currentVideoElement.pause();
                currentVideoElement = null;
            }
            storyContent.innerHTML = '';
            moreMenu.style.display = 'none';
        }

        function showStory(index) {
            clearTimeout(progressTimeout);
            if (currentVideoElement) {
                currentVideoElement.pause();
                currentVideoElement = null;
            }
            const story = currentUserStories[index];
            storyContent.innerHTML = '';

            muteBtn.style.display = 'none';

            if (story.content_type === 'image') {
                const img = document.createElement('img');
                img.src = story.content;
                img.classList.add('story-viewer-image');
                storyContent.appendChild(img);
                progressTimeout = setTimeout(nextStory, 5000);
            } else if (story.content_type === 'video') {
                muteBtn.style.display = 'block';
                const video = document.createElement('video');
                video.src = story.content;
                video.classList.add('story-viewer-video');
                video.autoplay = true;
                video.controls = false;
                video.muted = true;
                video.onended = () => nextStory();
                storyContent.appendChild(video);
                currentVideoElement = video;
            } else if (story.content_type === 'text') {
                const textDiv = document.createElement('div');
                textDiv.classList.add('story-viewer-text');
                textDiv.textContent = story.content;
                textDiv.style.backgroundColor = story.background || '#000';
                storyContent.appendChild(textDiv);
                progressTimeout = setTimeout(nextStory, 5000);
            }

            fetch(`/feed/api/story/${story.id}/view`, { method: 'POST' });

            progressBarsContainer.innerHTML = '';
            currentUserStories.forEach((s, i) => {
                const bar = document.createElement('div');
                bar.classList.add('progress-bar');
                if (i < index) bar.classList.add('filled');
                progressBarsContainer.appendChild(bar);
            });

            const currentBar = progressBarsContainer.children[index];
            if (currentBar) {
                currentBar.classList.add('active');
            }
        }

        function nextStory() {
            clearTimeout(progressTimeout);
            if (currentStoryIndex < currentUserStories.length - 1) {
                currentStoryIndex++;
                showStory(currentStoryIndex);
            } else {
                nextUser();
            }
        }

        function prevStory() {
            clearTimeout(progressTimeout);
            if (currentStoryIndex > 0) {
                currentStoryIndex--;
                showStory(currentStoryIndex);
            } else {
                prevUser();
            }
        }

        function nextUser() {
            if (currentUserIndex < allUsersWithStories.length - 1) {
                currentUserIndex++;
                loadUserStories(allUsersWithStories[currentUserIndex]);
            } else {
                closeStoryViewer();
            }
        }

        function prevUser() {
            if (currentUserIndex > 0) {
                currentUserIndex--;
                loadUserStories(allUsersWithStories[currentUserIndex]);
            } else {
                closeStoryViewer();
            }
        }

        closeBtn.addEventListener('click', closeStoryViewer);
        navLeft.addEventListener('click', prevStory);
        navRight.addEventListener('click', nextStory);

        moreBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            moreMenu.style.display = moreMenu.style.display === 'block' ? 'none' : 'block';
        });

        muteBtn.addEventListener('click', () => {
            if (currentVideoElement) {
                currentVideoElement.muted = !currentVideoElement.muted;
                muteBtn.innerHTML = currentVideoElement.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
            }
        });

        document.addEventListener('click', (e) => {
            if (!moreMenu.contains(e.target) && !moreBtn.contains(e.target)) {
                moreMenu.style.display = 'none';
            }
        });
    }
});
