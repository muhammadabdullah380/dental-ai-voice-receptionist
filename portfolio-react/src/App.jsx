import { useEffect, useState } from 'react'
import './portfolio.css'

const PORTFOLIO_API_URL = import.meta.env.VITE_PORTFOLIO_API_URL || 'http://127.0.0.1:8001'

const projects = [
  { name: 'Dental AI Voice Receptionist', detail: 'FastAPI, Vapi, n8n, MCP, Calendar and Sheets.', type: 'aether', year: '2026' },
  { name: 'REST API Platforms', detail: 'Django, FastAPI, authentication and business logic.', type: 'north', year: '2023-26' },
  { name: 'Automation Workflows', detail: 'Webhooks, integrations and reliable backend workflows.', type: 'pulse', year: '2023-26' },
]

const experience = [
  ['2023 - 2026', 'Python Backend Developer', 'Professional Experience', 'Designed and developed backend applications using Python and Django, RESTful APIs, PostgreSQL, authentication, validation, and business logic.'],
  ['2023 - 2026', 'API & Integration Developer', 'Professional Experience', 'Integrated external APIs and services using REST APIs and webhooks, while building data processing and automation workflows.'],
  ['2023 - 2026', 'AI Integration Developer', 'Professional Experience', 'Worked with AI integration, voice AI, Vapi, MCP, and n8n workflow automation for real-world business applications.'],
  ['2023 - 2026', 'Deployment & Infrastructure', 'Professional Experience', 'Used Docker for containerization and contributed to cloud deployment with AWS and Render.'],
]

function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('portfolio-theme') === 'dark')
  const [status, setStatus] = useState('')
  const [portfolioProjects, setPortfolioProjects] = useState(projects)
  const [portfolioExperience, setPortfolioExperience] = useState(experience)

  useEffect(() => {
    document.body.classList.toggle('dark', dark)
    localStorage.setItem('portfolio-theme', dark ? 'dark' : 'light')
  }, [dark])

  useEffect(() => {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target) }
    }), { threshold: 0.15 })
    document.querySelectorAll('.reveal').forEach((item) => observer.observe(item))
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    Promise.all([
      fetch(`${PORTFOLIO_API_URL}/api/projects`).then((response) => response.ok ? response.json() : Promise.reject(new Error('Projects unavailable'))),
      fetch(`${PORTFOLIO_API_URL}/api/experience`).then((response) => response.ok ? response.json() : Promise.reject(new Error('Experience unavailable'))),
    ]).then(([loadedProjects, loadedExperience]) => {
      setPortfolioProjects(loadedProjects.map((project) => ({ ...project, type: project.project_type })))
      setPortfolioExperience(loadedExperience)
    }).catch(() => {
      // Keep the resume content visible if the API is temporarily offline.
    })
  }, [])

  const submitForm = async (event) => {
    event.preventDefault()
    const form = event.target
    const formData = new FormData(form)
    setStatus('Sending...')

    try {
      const response = await fetch(`${PORTFOLIO_API_URL}/api/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(formData.entries())),
      })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail?.[0]?.msg || 'Message could not be sent.')
      setStatus(result.message)
      form.reset()
    } catch (error) {
      setStatus(error.message || 'The portfolio API is unavailable right now.')
    }
  }

  return (
    <><header className="site-header"><a className="brand" href="#top"><span>MA</span>.</a><nav><a href="#work">Work</a><a href="#experience">Experience</a><a href="#about">About</a><a href="#contact">Contact</a></nav><button className="theme-toggle" onClick={() => setDark(!dark)} aria-label="Toggle theme">{dark ? '☾' : '☼'}</button></header>
      <main id="top"><section className="hero section-wrap"><p className="eyebrow reveal">01 / PYTHON BACKEND DEVELOPER</p><h1 className="reveal">Building<br /><em>reliable</em><br />backend systems.</h1><div className="hero-bottom reveal"><p className="intro">Muhammad ABDULLAH is a Python Backend Developer specializing in Django, FastAPI, REST APIs, AI integration, and automation.</p><a className="circle-link" href="#work">↘</a></div></section>
        <section className="work section-wrap" id="work"><div className="section-heading reveal"><span>02 / SELECTED WORK</span><span>({String(portfolioProjects.length).padStart(2, '0')})</span></div><div className="project-grid">{portfolioProjects.map((project, index) => <article className="project-card reveal" key={project.name}><div className={`project-art art-${project.type}`}><span className="art-label">{project.name.toUpperCase()} / {project.year}</span><span className="art-symbol">{project.type === 'aether' ? '✳' : project.type === 'north' ? 'NORTH' : '◉'}</span></div><div className="project-info"><div><h2>{project.name}</h2><p>{project.detail}</p></div><span>{String(index + 1).padStart(2, '0')}</span></div></article>)}</div></section>
        <section className="experience section-wrap" id="experience"><div className="section-heading reveal"><span>03 / WORK EXPERIENCE</span><span>({String(portfolioExperience.length).padStart(2, '0')})</span></div><div className="experience-list">{portfolioExperience.map((item) => { const entry = Array.isArray(item) ? { period: item[0], role: item[1], company: item[2], detail: item[3] } : item; return <article className="experience-row reveal" key={entry.role}><span className="experience-year">{entry.period}</span><div><h2>{entry.role}</h2><p className="experience-company">{entry.company}</p><p className="experience-detail">{entry.detail}</p></div><span>↗</span></article> })}</div><div className="project-list-heading reveal"><span>PROJECT LIST</span><span>({String(portfolioProjects.length).padStart(2, '0')})</span></div><div className="project-list reveal">{portfolioProjects.map((project, index) => <a href="#work" key={project.name}><span>0{index + 1}</span><strong>{project.name}</strong><small>{project.detail}</small><b>{project.year} ↗</b></a>)}</div></section>
        <section className="about section-wrap" id="about"><div className="section-heading reveal"><span>04 / ABOUT & SKILLS</span><span>✳</span></div><div className="about-content"><h2 className="reveal">Backend logic<br />for <em>real-world</em><br />problems.</h2><div className="about-copy reveal"><p>I am Muhammad ABDULLAH, a Python Backend Developer from Lahore, Pakistan, with 2.5 years of experience building scalable backend applications.</p><p>My toolkit includes Python, Django, Django REST Framework, FastAPI, Flask, PostgreSQL, SQLite, Docker, AWS, Render, Git, Postman, Vapi, n8n, and MCP.</p><p><strong>Education:</strong> Bachelor's in Computer Science, graduated 2024.</p><a className="text-link" href="#contact">Let's work together ↗</a></div></div></section>
        <section className="contact section-wrap" id="contact"><div className="section-heading reveal"><span>05 / SAY HELLO</span><span>LAHORE, PK</span></div><div className="contact-content reveal"><h2>Need a strong<br /><em>backend?</em></h2><a className="email-link" href="mailto:abdullahkhannutmn@gmail.com">abdullahkhannutmn@gmail.com ↗</a><a className="phone-link" href="tel:+923101666127">+92 310 1666127</a></div><form className="contact-form reveal" onSubmit={submitForm}><label htmlFor="name">Your name</label><input id="name" name="name" required placeholder="Your name" /><label htmlFor="email">Your email</label><input id="email" name="email" type="email" required placeholder="your@email.com" /><label htmlFor="message">Your message</label><textarea id="message" name="message" rows="3" required placeholder="Tell me about your backend project..." /><button className="submit-button">Send message ↗</button><p className="form-status">{status}</p></form></section>
      </main><footer className="site-footer section-wrap"><span>© 2026 MUHAMMAD ABDULLAH</span><div><a href="#top">Back to top ↑</a><a href="https://github.com/" target="_blank" rel="noreferrer">GitHub ↗</a><a href="https://www.linkedin.com/" target="_blank" rel="noreferrer">LinkedIn ↗</a></div></footer></>
  )
}

export default App
