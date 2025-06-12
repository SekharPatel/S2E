const robotWrapper = document.getElementById('robotInteractionWrapper');
const pupils = document.querySelectorAll('.pupil');
const frontText = document.querySelector('.front-text');
const endText = document.querySelector('.end-text');

// --- Variables for Robot Head Rotation ---
let currentRotX = 0;
let currentRotY = 0;
let targetRotX = 0;
let targetRotY = 0;
const maxHeadRotation = 15; // Max rotation in degrees for the head
const dampingFactor = 0.08; // Smoothing factor

// --- Variables for Pupil Movement ---
let targetPupilOffsets = [];
let currentPupilOffsets = [];
const maxPupilMovement = 4; // Max pixels pupil can move from its eye's center

// --- Variables for Text Parallax ---
let targetTextFrontOffset = { x: 0, y: 0 };
let currentTextFrontOffset = { x: 0, y: 0 };
let targetTextEndOffset = { x: 0, y: 0 };
let currentTextEndOffset = { x: 0, y: 0 };
const textFrontParallaxFactor = 0.03; // Increased for more noticeable movement
const textEndParallaxFactor = 0.02;  // Increased but less than front
const textDampingFactor = 0.05;      // Slower damping for smoother movement

// Initialize pupil offset arrays
if (pupils.length > 0) {
    pupils.forEach(() => {
        targetPupilOffsets.push({ x: 0, y: 0 });
        currentPupilOffsets.push({ x: 0, y: 0 });
    });
}

document.addEventListener('mousemove', function(e) {
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    const mouseX = e.clientX;
    const mouseY = e.clientY;

    // 1. Calculate Target for Robot Head Rotation
    targetRotX = ((mouseY - centerY) / centerY) * -maxHeadRotation;
    targetRotY = ((mouseX - centerX) / centerX) * maxHeadRotation;

    // 2. Calculate Target for Pupil Movement
    pupils.forEach((pupil, index) => {
        const eye = pupil.parentElement;
        if (!eye) return;

        // Get eye's current position on screen
        const eyeRect = eye.getBoundingClientRect();
        const eyeCenterX = eyeRect.left + eyeRect.width / 2;
        const eyeCenterY = eyeRect.top + eyeRect.height / 2;

        // Calculate direction vector from eye center to mouse
        let dx = mouseX - eyeCenterX;
        let dy = mouseY - eyeCenterY;
        
        // Normalize vector (not strictly necessary for this effect, but good practice for angles)
        const distance = Math.sqrt(dx * dx + dy * dy);
        const normalizedDx = distance > 0 ? dx / distance : 0;
        const normalizedDy = distance > 0 ? dy / distance : 0;

        // Scale normalized vector by maxPupilMovement
        // This makes pupils point towards the cursor, limited by maxPupilMovement
        let pupilTargetX = normalizedDx * maxPupilMovement;
        let pupilTargetY = normalizedDy * maxPupilMovement;
        
        targetPupilOffsets[index] = { x: pupilTargetX, y: pupilTargetY };
    });

    // 3. Calculate Target for Text Parallax
    let parallaxFrontX = (mouseX - centerX) * textFrontParallaxFactor;
    let parallaxFrontY = (mouseY - centerY) * textFrontParallaxFactor;
    targetTextFrontOffset = { x: parallaxFrontX, y: parallaxFrontY };

    let parallaxEndX = (mouseX - centerX) * textEndParallaxFactor;
    let parallaxEndY = (mouseY - centerY) * textEndParallaxFactor;
    // Invert for "End" text for a sense of distance (moves less and opposite)
    targetTextEndOffset = { x: -parallaxEndX, y: -parallaxEndY }; 
});

function animateElements() {
    // --- Animate Robot Head Rotation ---
    if (robotWrapper) {
        currentRotX += (targetRotX - currentRotX) * dampingFactor;
        currentRotY += (targetRotY - currentRotY) * dampingFactor;
        robotWrapper.style.transform = `rotateX(${currentRotX}deg) rotateY(${currentRotY}deg)`;
    }

    // --- Animate Pupils ---
    pupils.forEach((pupil, index) => {
        if (targetPupilOffsets[index] && currentPupilOffsets[index]) {
            currentPupilOffsets[index].x += (targetPupilOffsets[index].x - currentPupilOffsets[index].x) * dampingFactor;
            currentPupilOffsets[index].y += (targetPupilOffsets[index].y - currentPupilOffsets[index].y) * dampingFactor;
            
            // Base transform centers the pupil itself, then add calculated offset
            pupil.style.transform = `translate(-50%, -50%) translate(${currentPupilOffsets[index].x}px, ${currentPupilOffsets[index].y}px)`;
        }
    });

    // --- Animate Front Text Parallax ---
    if (frontText) {
        currentTextFrontOffset.x += (targetTextFrontOffset.x - currentTextFrontOffset.x) * textDampingFactor;
        currentTextFrontOffset.y += (targetTextFrontOffset.y - currentTextFrontOffset.y) * textDampingFactor;
        
        // Apply smooth easing and accumulate transforms
        const frontTransform = `
            translate(-20%, -20%)
            translate3d(${currentTextFrontOffset.x}px, ${currentTextFrontOffset.y}px, 0)
        `;
        frontText.style.transform = frontTransform;
    }

    // --- Animate End Text Parallax ---
    if (endText) {
        currentTextEndOffset.x += (targetTextEndOffset.x - currentTextEndOffset.x) * textDampingFactor;
        currentTextEndOffset.y += (targetTextEndOffset.y - currentTextEndOffset.y) * textDampingFactor;
        
        // Apply smooth easing and accumulate transforms
        const endTransform = `
            translate(20%, 20%)
            translate3d(${currentTextEndOffset.x}px, ${currentTextEndOffset.y}px, 0)
        `;
        endText.style.transform = endTransform;
    }
    
    requestAnimationFrame(animateElements);
}

// Start the animation loop
if (robotWrapper || pupils.length > 0 || frontText || endText) {
    animateElements();
}

// // --- Cursor Trail Effect ---
// document.addEventListener('mousemove', function(e) {
//     let trail = document.createElement('div');
//     trail.className = 'cursor-trail';
//     document.body.appendChild(trail);
    
//     trail.style.left = (e.clientX + window.scrollX) + 'px';
//     trail.style.top = (e.clientY + window.scrollY) + 'px';
    
//     setTimeout(function() {
//         if (trail.parentElement) {
//             trail.remove();
//         }
//     }, 300); 
// });