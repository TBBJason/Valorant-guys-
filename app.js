// Presentation App JavaScript
class PresentationApp {
    constructor() {
        this.currentSlide = 1;
        this.totalSlides = 12;
        this.isTransitioning = false;
        
        this.slides = document.querySelectorAll('.slide');
        this.prevBtn = document.getElementById('prev-btn');
        this.nextBtn = document.getElementById('next-btn');
        this.currentSlideSpan = document.getElementById('current-slide');
        this.totalSlidesSpan = document.getElementById('total-slides');
        this.bookmakerChart = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateSlideCounter();
        this.updateNavigationButtons();
        this.showCurrentSlide();
        
        // Initialize chart if starting on slide 8
        if (this.currentSlide === 8) {
            setTimeout(() => this.initializeBookmakerChart(), 500);
        }
    }

    setupEventListeners() {
        // Navigation button events with explicit binding
        if (this.prevBtn) {
            this.prevBtn.onclick = () => {
                console.log('Previous button clicked');
                this.previousSlide();
            };
        }
        
        if (this.nextBtn) {
            this.nextBtn.onclick = () => {
                console.log('Next button clicked');
                this.nextSlide();
            };
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.isTransitioning) return;
            
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.previousSlide();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.nextSlide();
            }
        });

        // Touch/swipe navigation for mobile
        let startX = 0;
        let endX = 0;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });

        document.addEventListener('touchend', (e) => {
            if (this.isTransitioning) return;
            
            endX = e.changedTouches[0].clientX;
            const diff = startX - endX;
            const swipeThreshold = 50;

            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    this.nextSlide();
                } else {
                    this.previousSlide();
                }
            }
        });
    }

    nextSlide() {
        if (this.isTransitioning || this.currentSlide >= this.totalSlides) {
            return;
        }
        
        console.log('Moving to next slide:', this.currentSlide + 1);
        this.goToSlide(this.currentSlide + 1);
    }

    previousSlide() {
        if (this.isTransitioning || this.currentSlide <= 1) {
            return;
        }
        
        console.log('Moving to previous slide:', this.currentSlide - 1);
        this.goToSlide(this.currentSlide - 1);
    }

    goToSlide(slideNumber) {
        if (slideNumber < 1 || slideNumber > this.totalSlides || this.isTransitioning) {
            return;
        }

        this.isTransitioning = true;
        
        // Hide current slide
        if (this.slides[this.currentSlide - 1]) {
            this.slides[this.currentSlide - 1].classList.remove('active');
        }

        // Update current slide number
        this.currentSlide = slideNumber;

        // Show new slide after brief delay
        setTimeout(() => {
            this.showCurrentSlide();
            this.updateSlideCounter();
            this.updateNavigationButtons();
            
            // Handle chart initialization for slide 8
            if (this.currentSlide === 8) {
                setTimeout(() => this.initializeBookmakerChart(), 200);
            }
            
            this.isTransitioning = false;
        }, 50);
    }

    showCurrentSlide() {
        // Hide all slides first
        this.slides.forEach(slide => {
            slide.classList.remove('active');
        });

        // Show current slide
        if (this.slides[this.currentSlide - 1]) {
            this.slides[this.currentSlide - 1].classList.add('active');
        }
    }

    updateSlideCounter() {
        if (this.currentSlideSpan) {
            this.currentSlideSpan.textContent = this.currentSlide;
        }
        if (this.totalSlidesSpan) {
            this.totalSlidesSpan.textContent = this.totalSlides;
        }
    }

    updateNavigationButtons() {
        if (this.prevBtn) {
            this.prevBtn.disabled = (this.currentSlide === 1);
            this.prevBtn.textContent = this.currentSlide === 1 ? 'Start' : '← Previous';
        }
        
        if (this.nextBtn) {
            this.nextBtn.disabled = (this.currentSlide === this.totalSlides);
            this.nextBtn.textContent = this.currentSlide === this.totalSlides ? 'End' : 'Next →';
        }
    }

    initializeBookmakerChart() {
        const canvas = document.getElementById('bookmaker-chart');
        if (!canvas) {
            console.log('Chart canvas not found');
            return;
        }

        // Destroy existing chart if it exists
        if (this.bookmakerChart) {
            this.bookmakerChart.destroy();
            this.bookmakerChart = null;
        }

        // Get canvas context
        const ctx = canvas.getContext('2d');
        
        // Bookmaker data
        const bookmakerData = {
            "Pinnacle": {"avg_margin": 0.172, "variance": 0.099},
            "Thunderpick": {"avg_margin": 0.156, "variance": 0.116},
            "Bet365": {"avg_margin": 0.180, "variance": 0.134},
            "Betway": {"avg_margin": 0.176, "variance": 0.147},
            "888Sport": {"avg_margin": 0.204, "variance": 0.149},
            "Unibet": {"avg_margin": 0.178, "variance": 0.164}
        };

        const labels = Object.keys(bookmakerData);
        const marginData = labels.map(label => bookmakerData[label].avg_margin);
        const varianceData = labels.map(label => bookmakerData[label].variance);

        // Chart colors
        const marginColor = '#1FB8CD';
        const varianceColor = '#FFC185';

        try {
            this.bookmakerChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Average Margin (%)',
                            data: marginData,
                            backgroundColor: marginColor,
                            borderColor: marginColor,
                            borderWidth: 1
                        },
                        {
                            label: 'Variance (%)',
                            data: varianceData,
                            backgroundColor: varianceColor,
                            borderColor: varianceColor,
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Bookmaker Margins vs Variance',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            color: '#333'
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#333'
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Percentage (%)',
                                color: '#666'
                            },
                            ticks: {
                                color: '#666',
                                callback: function(value) {
                                    return value.toFixed(3) + '%';
                                }
                            },
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Bookmakers',
                                color: '#666'
                            },
                            ticks: {
                                color: '#666'
                            },
                            grid: {
                                color: 'rgba(0,0,0,0.1)'
                            }
                        }
                    }
                }
            });
            
            console.log('Chart initialized successfully');
        } catch (error) {
            console.error('Error creating chart:', error);
        }
    }

    // Public methods for external control
    getCurrentSlide() {
        return this.currentSlide;
    }

    getTotalSlides() {
        return this.totalSlides;
    }

    setSlide(slideNumber) {
        this.goToSlide(slideNumber);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing presentation...');
    
    // Create the main presentation app
    window.presentationApp = new PresentationApp();
    
    // Add interactive features
    setupInteractiveFeatures();
    
    console.log('Presentation initialized');
});

// Setup interactive features for enhanced user experience
function setupInteractiveFeatures() {
    // Add hover effects for cards
    const cards = document.querySelectorAll('.data-card, .market-card, .timing-card, .arbitrage-card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = 'var(--shadow-lg)';
            card.style.transition = 'all 0.2s ease';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = 'var(--shadow-sm)';
        });
    });

    // Add helpful navigation info
    const infoDiv = document.createElement('div');
    infoDiv.style.cssText = `
        position: fixed;
        bottom: 80px;
        left: 20px;
        background: var(--color-surface);
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        color: var(--color-text-secondary);
        opacity: 0.8;
        z-index: 20;
        border: 1px solid var(--color-border);
    `;
    infoDiv.textContent = 'Use ← → arrow keys or buttons to navigate';
    document.body.appendChild(infoDiv);

    // Auto-hide the info after 5 seconds
    setTimeout(() => {
        infoDiv.style.opacity = '0';
        infoDiv.style.transition = 'opacity 0.3s ease';
        setTimeout(() => {
            if (infoDiv.parentNode) {
                infoDiv.parentNode.removeChild(infoDiv);
            }
        }, 300);
    }, 5000);

    // Add click to expand functionality for arbitrage cards
    document.addEventListener('click', (e) => {
        const card = e.target.closest('.arbitrage-card');
        if (card) {
            card.classList.toggle('expanded');
        }
    });
}

// Utility functions
const DataUtils = {
    formatCurrency: (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 2
        }).format(amount);
    },

    formatPercentage: (value, decimals = 1) => {
        return `${(value * 100).toFixed(decimals)}%`;
    },

    calculateArbitrageProfit: (odds1, odds2) => {
        const impliedProb1 = 1 / odds1;
        const impliedProb2 = 1 / odds2;
        const totalImpliedProb = impliedProb1 + impliedProb2;
        
        if (totalImpliedProb < 1) {
            const profit = ((1 - totalImpliedProb) / totalImpliedProb) * 100;
            return profit.toFixed(2);
        }
        return 0;
    }
};

// Export utilities
window.DataUtils = DataUtils;