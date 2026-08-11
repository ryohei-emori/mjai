module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			DEFAULT: '0.25rem',
  			lg: '0.5rem',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)',
  			xl: '0.75rem',
  			full: '9999px'
  		},
  		spacing: {
  			'container-margin': '1.5rem',
  			'card-gap': '1.25rem',
  			'gutter': '1rem',
  			'section': '2rem',
  			'topappbar': '4rem'
  		},
		fontSize: {
			'headline-lg': ['1.5rem', { lineHeight: '2rem', letterSpacing: '0', fontWeight: '700' }],
			'headline-md': ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '0.0125em', fontWeight: '600' }],
			'body-base': ['1rem', { lineHeight: '1.5rem', letterSpacing: '0.03125em', fontWeight: '400' }],
			'body-sm': ['0.875rem', { lineHeight: '1.25rem', letterSpacing: '0.025em', fontWeight: '400' }],
			'metadata': ['0.75rem', { lineHeight: '1rem', letterSpacing: '0.03125em', fontWeight: '500' }],
			'label-caps': ['0.625rem', { lineHeight: '1rem', letterSpacing: '0.1em', fontWeight: '600' }]
		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			},
  			// MD3 Semantic Colors
  			surface: {
  				DEFAULT: 'hsl(var(--surface))',
  				container: 'hsl(var(--surface-container))',
  				'container-low': 'hsl(var(--surface-container-low))',
  				'container-lowest': 'hsl(var(--surface-container-lowest))',
  				'container-high': 'hsl(var(--surface-container-high))',
  				'container-highest': 'hsl(var(--surface-container-highest))'
  			},
  			'on-surface': 'hsl(var(--on-surface))',
  			'on-surface-variant': 'hsl(var(--on-surface-variant))',
  			outline: {
  				DEFAULT: 'hsl(var(--outline))',
  				variant: 'hsl(var(--outline-variant))'
  			},
  			error: 'hsl(var(--error))',
  			'on-error': 'hsl(var(--on-error))',
  			tertiary: 'hsl(var(--tertiary))',
  			'on-tertiary': 'hsl(var(--on-tertiary))',
  			'md3-primary': 'hsl(var(--md3-primary))',
  			'on-primary': 'hsl(var(--on-primary))',
  			'primary-container': 'hsl(var(--primary-container))',
  			'on-primary-container': 'hsl(var(--on-primary-container))',
  			// Session status colors
  			'session-active': '#2563EB',
  			'session-complete': '#16A34A',
  			'session-empty': '#64748B'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}
