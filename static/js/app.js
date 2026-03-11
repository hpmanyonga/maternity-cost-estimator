/**
 * Maternity Cost Estimator — Alpine.js app.
 * Auto-calculates on input change. 3-layer progressive disclosure.
 */

function estimatorApp() {
    return {
        // --- Form inputs ---
        region: 'Gauteng',
        delivery_type: 'NVD',
        risk_level: 'low',
        provider_tier: 'mid-range',
        wants_epidural: false,
        wants_doula: false,
        timing: 'pregnant',
        gestational_weeks: 12,
        planning_months: 6,

        // --- State ---
        loading: false,
        hasResults: false,
        error: null,
        data: null,
        ffsTab: 'NVD',

        // --- Lead form ---
        leadName: '',
        leadEmail: '',
        leadPhone: '',
        leadProvince: 'Gauteng',
        leadSubmitting: false,
        leadMessage: null,
        leadError: false,

        // --- Sources ---
        sources: null,
        sourcesLoaded: false,

        // --- Embed ---
        isEmbed: new URLSearchParams(window.location.search).get('embed') === 'true',

        // Debounce timer
        _debounce: null,

        init() {
            if (this.isEmbed) document.body.classList.add('embed');

            // Watch all form inputs and auto-recalculate
            this.$watch('region', () => this.debouncedEstimate());
            this.$watch('delivery_type', () => this.debouncedEstimate());
            this.$watch('risk_level', () => this.debouncedEstimate());
            this.$watch('provider_tier', () => this.debouncedEstimate());
            this.$watch('wants_epidural', () => this.debouncedEstimate());
            this.$watch('wants_doula', () => this.debouncedEstimate());
            this.$watch('timing', () => this.debouncedEstimate());
            this.$watch('gestational_weeks', () => this.debouncedEstimate());
            this.$watch('planning_months', () => this.debouncedEstimate());

            // Initial estimate
            this.getEstimate();
        },

        debouncedEstimate() {
            clearTimeout(this._debounce);
            this._debounce = setTimeout(() => this.getEstimate(), 250);
        },

        async getEstimate() {
            this.loading = true;
            this.error = null;

            try {
                const resp = await fetch('/api/estimate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        region: this.region,
                        delivery_type: this.delivery_type,
                        risk_level: this.risk_level,
                        provider_tier: this.provider_tier,
                        wants_epidural: this.wants_epidural,
                        wants_doula: this.wants_doula,
                        gestational_weeks: this.timing === 'pregnant' ? this.gestational_weeks : 0,
                        planning_months: this.timing === 'planning' ? this.planning_months : 0,
                    }),
                });
                if (!resp.ok) throw new Error('Failed');
                this.data = await resp.json();
                this.hasResults = true;
                this.ffsTab = this.data.is_undecided ? 'NVD' : null;

                if (this.isEmbed) {
                    this.$nextTick(() => {
                        window.parent.postMessage({
                            type: 'noh-estimator-resize',
                            height: document.documentElement.scrollHeight
                        }, '*');
                    });
                }
            } catch (e) {
                this.error = 'Unable to calculate. Please try again.';
            } finally {
                this.loading = false;
            }
        },

        async submitLead() {
            if (!this.leadName || !this.leadEmail) {
                this.leadMessage = 'Please enter your name and email.';
                this.leadError = true;
                return;
            }
            this.leadSubmitting = true;
            this.leadMessage = null;

            try {
                const resp = await fetch('/api/lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: this.leadName,
                        email: this.leadEmail,
                        phone: this.leadPhone || null,
                        province: this.leadProvince,
                        gestational_weeks: this.timing === 'pregnant' ? this.gestational_weeks : 0,
                        delivery_preference: this.delivery_type,
                        risk_level: this.risk_level,
                        noh_estimate_low: this.data ? this.data.noh_total.low : null,
                        noh_estimate_high: this.data ? this.data.noh_total.high : null,
                        ffs_estimate_low: this.data ? this.data.ffs_total.low : null,
                        ffs_estimate_high: this.data ? this.data.ffs_total.high : null,
                    }),
                });
                const result = await resp.json();
                this.leadMessage = result.message;
                this.leadError = false;
            } catch (e) {
                this.leadMessage = 'Something went wrong. Please try again.';
                this.leadError = true;
            } finally {
                this.leadSubmitting = false;
            }
        },

        async loadSources() {
            if (this.sourcesLoaded) return;
            try {
                const resp = await fetch('/api/sources');
                const result = await resp.json();
                this.sources = result.sources;
                this.sourcesLoaded = true;
            } catch (e) { /* silent */ }
        },

        // Scroll to lead form
        scrollToQuote() {
            const el = document.getElementById('lead-section');
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },

        // --- Helpers ---
        R(val) {
            if (val == null) return 'R 0';
            return 'R ' + val.toLocaleString('en-ZA');
        },
        range(low, high) {
            return this.R(low) + ' \u2013 ' + this.R(high);
        },

        get ffsBreakdown() {
            if (!this.data) return null;
            if (this.data.is_undecided) {
                return this.data.ffs[this.ffsTab] || this.data.ffs['NVD'];
            }
            return this.data.ffs;
        },

        get ffsRows() {
            const bd = this.ffsBreakdown;
            if (!bd) return [];
            return [
                ['Hospital', bd.hospital],
                ['Obstetrician', bd.obstetrician],
                ['Anaesthetist', bd.anaesthetist],
                ['Paediatrician', bd.paediatrician],
                ['Pathology', bd.pathology],
                ['Ultrasound', bd.ultrasound],
                ['Medication', bd.medication],
                ['Midwife', bd.midwife],
                ['Doula', bd.doula],
            ].filter(([_, v]) => v.low > 0 || v.high > 0);
        },
    };
}
