// Keep the public API address here; private SMTP settings stay in the backend environment.
const portfolioApiUrl = 'http://127.0.0.1:8001';

// Cache the page elements once so each feature can reuse the same DOM references.
const themeToggle = document.querySelector('.theme-toggle');
const contactForm = document.querySelector('#contact-form');
const revealItems = document.querySelectorAll('.reveal');

// Apply the saved theme immediately so the page opens in the visitor's last selected mode.
const savedTheme = localStorage.getItem('portfolio-theme');
if (savedTheme === 'dark' && themeToggle) {
  document.body.classList.add('dark');
  themeToggle.textContent = '☾';
}

// Toggle the theme and save the choice for the next visit.
themeToggle?.addEventListener('click', () => {
  const isDark = document.body.classList.toggle('dark');
  themeToggle.textContent = isDark ? '☾' : '☼';
  localStorage.setItem('portfolio-theme', isDark ? 'dark' : 'light');
});

// Reveal content only when it enters the viewport to create a lightweight entrance animation.
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

revealItems.forEach((item) => observer.observe(item));

// Submit contact details to the backend so the server can save the message and send email securely.
contactForm?.addEventListener('submit', async (event) => {
  event.preventDefault();

  const status = contactForm.querySelector('.form-status');
  const submitButton = contactForm.querySelector('.submit-button');
  const formData = new FormData(contactForm);

  status.textContent = 'Sending...';
  submitButton.disabled = true;

  try {
    const response = await fetch(`${portfolioApiUrl}/api/contact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.fromEntries(formData.entries())),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail?.[0]?.msg || 'Message could not be sent.');
    }

    status.textContent = result.message;
    contactForm.reset();
  } catch (error) {
    status.textContent = error.message || 'The portfolio API is unavailable right now.';
  } finally {
    submitButton.disabled = false;
  }
});