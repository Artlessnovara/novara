document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('post-resource-modal');
    const btn = document.getElementById('post-resource-btn');
    const span = document.querySelector('#post-resource-modal .close-btn');

    if(btn) {
        btn.onclick = function(e) {
            e.preventDefault();
            modal.style.display = "block";
        }
    }
    if(span) {
        span.onclick = function() {
            modal.style.display = "none";
        }
    }
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
});
