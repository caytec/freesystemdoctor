import './style.css'

const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const $  = (s, c = document) => c.querySelector(s)
const $$ = (s, c = document) => [...c.querySelectorAll(s)]

/* ─────────────── i18n (PL ⇄ EN) ───────────────
   Initial <html lang> is set by an inline <head> script (no FOUC).
   Here we only wire up the toggle button. */
const langToggle = $('#langToggle')
langToggle?.addEventListener('click', () => {
  const next = document.documentElement.lang === 'pl' ? 'en' : 'pl'
  document.documentElement.lang = next
  localStorage.setItem('fsd-lang', next)
})

/* ─────────────── Nav: scroll state + mobile menu ─────────────── */
const nav = $('#nav')
const burger = $('#navBurger')
const navLinks = $('#navLinks')

const onNavScroll = () => nav.classList.toggle('is-scrolled', window.scrollY > 30)
onNavScroll()

burger?.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open')
  burger.setAttribute('aria-expanded', String(open))
})
$$('#navLinks a').forEach(a =>
  a.addEventListener('click', () => {
    nav.classList.remove('is-open')
    burger?.setAttribute('aria-expanded', 'false')
  })
)

/* ─────────────── Scroll progress bar ─────────────── */
const progress = $('#scrollProgress')
const updateProgress = () => {
  const h = document.documentElement
  const max = h.scrollHeight - h.clientHeight
  progress.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%'
}

/* ─────────────── Parallax (rAF, batched with scroll) ─────────────── */
const parallaxEls = $$('[data-parallax]').map(el => ({
  el,
  speed: parseFloat(el.dataset.parallax) || 0.2,
}))

let ticking = false
const onScroll = () => {
  if (!ticking) {
    requestAnimationFrame(() => {
      const y = window.scrollY
      if (!prefersReduced) {
        for (const { el, speed } of parallaxEls) {
          el.style.transform = `translate3d(0, ${(-y * speed).toFixed(1)}px, 0)`
        }
      }
      updateProgress()
      onNavScroll()
      ticking = false
    })
    ticking = true
  }
}
window.addEventListener('scroll', onScroll, { passive: true })
updateProgress()

/* ─────────────── Reveal on scroll (stagger) ─────────────── */
const revealEls = $$('[data-reveal]')
if (prefersReduced || !('IntersectionObserver' in window)) {
  revealEls.forEach(el => el.classList.add('is-in'))
} else {
  const io = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          const sibs = [...entry.target.parentElement.children].filter(c =>
            c.hasAttribute('data-reveal')
          )
          const idx = Math.max(0, sibs.indexOf(entry.target))
          entry.target.style.transitionDelay = Math.min(idx, 6) * 70 + 'ms'
          entry.target.classList.add('is-in')
          obs.unobserve(entry.target)
        }
      })
    },
    { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
  )
  revealEls.forEach(el => io.observe(el))
}

/* ─────────────── Animated counters ─────────────── */
const animateCount = el => {
  const target = parseFloat(el.dataset.target) || 0
  if (prefersReduced) { el.textContent = target; return }
  const dur = 1400
  const start = performance.now()
  const tick = now => {
    const p = Math.min((now - start) / dur, 1)
    const eased = 1 - Math.pow(1 - p, 3)
    el.textContent = Math.round(target * eased)
    if (p < 1) requestAnimationFrame(tick)
    else el.textContent = target
  }
  requestAnimationFrame(tick)
}
if ('IntersectionObserver' in window) {
  const co = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach(e => {
        if (e.isIntersecting) { animateCount(e.target); obs.unobserve(e.target) }
      })
    },
    { threshold: 0.6 }
  )
  $$('.count').forEach(el => co.observe(el))
} else {
  $$('.count').forEach(el => (el.textContent = el.dataset.target))
}

/* ─────────────── Gauge live animation ─────────────── */
const mockup = $('#mockup')
if (mockup && 'IntersectionObserver' in window) {
  const go = new IntersectionObserver(
    (entries, obs) => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('is-live'); obs.unobserve(e.target) }
      })
    },
    { threshold: 0.4 }
  )
  go.observe(mockup)
} else {
  mockup?.classList.add('is-live')
}

/* ─────────────── Mouse spotlight on cards ─────────────── */
if (!prefersReduced && window.matchMedia('(pointer:fine)').matches) {
  $$('.card').forEach(card => {
    card.addEventListener('pointermove', e => {
      const r = card.getBoundingClientRect()
      card.style.setProperty('--mx', `${e.clientX - r.left}px`)
      card.style.setProperty('--my', `${e.clientY - r.top}px`)
    })
  })

  /* ─────────────── 3D tilt on hero mockup ─────────────── */
  const tilt = $('[data-tilt]')
  const visual = $('.hero__visual')
  if (tilt && visual) {
    const MAX = 9
    visual.addEventListener('pointermove', e => {
      const r = visual.getBoundingClientRect()
      const px = (e.clientX - r.left) / r.width - 0.5
      const py = (e.clientY - r.top) / r.height - 0.5
      tilt.style.transform =
        `rotateY(${px * MAX}deg) rotateX(${-py * MAX}deg) translateZ(0)`
    })
    visual.addEventListener('pointerleave', () => {
      tilt.style.transform = 'rotateY(0) rotateX(0)'
    })
  }
}

/* ─────────────── Active nav link on scroll ─────────────── */
const sections = $$('main section[id]')
if ('IntersectionObserver' in window) {
  const so = new IntersectionObserver(
    entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          $$('#navLinks a').forEach(a =>
            a.classList.toggle('is-active', a.getAttribute('href') === `#${e.target.id}`)
          )
        }
      })
    },
    { rootMargin: '-45% 0px -50% 0px' }
  )
  sections.forEach(s => so.observe(s))
}

/* ─────────────── Year in footer (auto) ─────────────── */
// (kept static "2026" in HTML for no-JS; nothing to do here)
