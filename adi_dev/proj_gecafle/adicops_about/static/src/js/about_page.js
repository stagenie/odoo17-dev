/** @odoo-module **/

import { Component, onMounted, useRef } from "@odoo/owl";

/**
 * About Page Component avec fonctionnalités interactives
 */
export class AboutPageComponent extends Component {
    setup() {
        this.headerRef = useRef("header");

        onMounted(() => {
            this.initializeAboutPage();
        });
    }

    /**
     * Initialise les fonctionnalités de la page About
     */
    initializeAboutPage() {
        this.setupScrollEffects();
        this.setupParallax();
        this.setupSmoothScrolling();
        this.setupImageLazyLoading();
        this.setupColorTheme();
    }

    /**
     * Effets de défilement
     */
    setupScrollEffects() {
        const sections = document.querySelectorAll('.section, .info_card');

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        sections.forEach(section => {
            observer.observe(section);
        });
    }

    /**
     * Effet parallaxe pour l'en-tête
     */
    setupParallax() {
        const header = document.querySelector('.adicops_header');
        const enableParallax = document.querySelector('.adicops_about_page.enable_parallax');

        if (header && enableParallax) {
            window.addEventListener('scroll', () => {
                const scrolled = window.pageYOffset;
                const rate = scrolled * -0.5;
                header.style.transform = `translateY(${rate}px)`;
            });
        }
    }

    /**
     * Défilement doux vers les sections
     */
    setupSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Chargement paresseux des images
     */
    setupImageLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => {
            imageObserver.observe(img);
        });
    }

    /**
     * Application du thème de couleurs personnalisé
     */
    setupColorTheme() {
        const aboutPage = document.querySelector('.adicops_about_page');
        if (aboutPage) {
            // Récupération des couleurs depuis les données Odoo
            const primaryColor = aboutPage.dataset.primaryColor || '#2C3E50';
            const secondaryColor = aboutPage.dataset.secondaryColor || '#3498DB';
            const backgroundColor = aboutPage.dataset.backgroundColor || '#FFFFFF';
            const textColor = aboutPage.dataset.textColor || '#2C3E50';

            // Application des variables CSS
            document.documentElement.style.setProperty('--primary-color', primaryColor);
            document.documentElement.style.setProperty('--secondary-color', secondaryColor);
            document.documentElement.style.setProperty('--background-color', backgroundColor);
            document.documentElement.style.setProperty('--text-color', textColor);
        }
    }

    /**
     * Gestion des liens sociaux avec analytics
     */
    trackSocialClick(platform) {
        console.log(`Social link clicked: ${platform}`);
        // Ici on peut ajouter Google Analytics ou autre
        if (typeof gtag !== 'undefined') {
            gtag('event', 'social_click', {
                'social_platform': platform,
                'page': 'about'
            });
        }
    }

    /**
     * Animation d'apparition des cartes
     */
    animateCards() {
        const cards = document.querySelectorAll('.info_card, .contact_card, .social_card');

        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
            card.classList.add('animate-fadeInUp');
        });
    }

    /**
     * Changement de thème (mode sombre/clair)
     */
    toggleTheme() {
        const aboutPage = document.querySelector('.adicops_about_page');
        aboutPage.classList.toggle('dark-theme');

        // Sauvegarder la préférence
        localStorage.setItem('adicops_theme',
            aboutPage.classList.contains('dark-theme') ? 'dark' : 'light'
        );
    }

    /**
     * Restaurer le thème sauvegardé
     */
    restoreTheme() {
        const savedTheme = localStorage.getItem('adicops_theme');
        if (savedTheme === 'dark') {
            document.querySelector('.adicops_about_page').classList.add('dark-theme');
        }
    }
}

// CSS d'animation supplémentaire
const animationCSS = `
    @keyframes animate-fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animate-fadeInUp {
        animation: animate-fadeInUp 0.6s ease-out forwards;
    }

    .animate-in {
        opacity: 1;
        transform: translateY(0);
        transition: all 0.6s ease-out;
    }

    .section, .info_card {
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.6s ease-out;
    }

    .lazy {
        opacity: 0;
        transition: opacity 0.3s;
    }
`;

// Injection du CSS
if (!document.getElementById('adicops-animations')) {
    const style = document.createElement('style');
    style.id = 'adicops-animations';
    style.textContent = animationCSS;
    document.head.appendChild(style);
}

// Auto-initialisation
document.addEventListener('DOMContentLoaded', () => {
    const aboutPage = document.querySelector('.adicops_about_page');
    if (aboutPage) {
        new AboutPageComponent().initializeAboutPage();
    }
});
