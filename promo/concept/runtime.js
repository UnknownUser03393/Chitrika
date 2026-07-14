const slides = [...document.querySelectorAll(".slide")];
const progressBar = document.querySelector("#progressBar");
const currentLabel = document.querySelector("#current");
const captureMode = new URLSearchParams(window.location.search).has("capture");

const autoplay = new URLSearchParams(window.location.search).has("autoplay");
let index = 0;
let playing = autoplay;
let startedAt = performance.now();
let frameId = 0;
const landingUrl = `${window.location.protocol}//${window.location.hostname}:8080/?promo=1`;

if (autoplay) document.body.classList.add("is-autoplay");
if (captureMode) document.body.classList.add("capture-waiting");

window.startPromoPlayback = () => {
  document.body.classList.remove("capture-waiting");
  playing = true;
  startedAt = performance.now();
};

function duration() {
  return Number(slides[index].dataset.duration || 5000);
}

function show(nextIndex) {
  if (nextIndex >= slides.length) {
    document.body.classList.add("is-transitioning");
    window.setTimeout(() => window.location.assign(landingUrl), 420);
    return;
  }
  slides[index].classList.remove("is-active");
  index = (nextIndex + slides.length) % slides.length;
  slides[index].classList.add("is-active");
  currentLabel.textContent = String(index + 1).padStart(2, "0");
  startedAt = performance.now();
  progressBar.style.width = "0%";
}

function tick(now) {
  if (playing) {
    const elapsed = now - startedAt;
    const ratio = Math.min(elapsed / duration(), 1);
    progressBar.style.width = `${ratio * 100}%`;
    if (ratio >= 1) show(index + 1);
  }
  frameId = requestAnimationFrame(tick);
}

function togglePlay() {
  playing = !playing;
  document.body.classList.toggle("is-paused", !playing);
  startedAt = performance.now();
}

document.addEventListener("keydown", (event) => {
  if (["ArrowRight", "PageDown"].includes(event.key)) show(index + 1);
  if (["ArrowLeft", "PageUp"].includes(event.key)) show(index - 1);
  if (event.key === " ") { event.preventDefault(); togglePlay(); }
  if (event.key.toLowerCase() === "f") document.documentElement.requestFullscreen?.();
});

cancelAnimationFrame(frameId);
frameId = requestAnimationFrame(tick);
