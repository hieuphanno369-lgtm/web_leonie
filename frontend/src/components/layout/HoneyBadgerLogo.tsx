type Props = {
  /** Rendered width & height in px (SVG is square). Default 32. */
  size?: number
  className?: string
}

/**
 * Honey Badger brand mark — black/silver badger with amber "fearless" eyes.
 * Self-contained SVG (colors inlined, gradient ids namespaced `hb-*` to avoid
 * collisions). Source design: standalone HTML logo provided by the owner.
 */
export default function HoneyBadgerLogo({ size = 32, className }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="Honey Badger logo"
    >
      <defs>
        <linearGradient id="hb-silver" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#cfd3d8" />
        </linearGradient>
        <radialGradient id="hb-gold" cx="50%" cy="40%">
          <stop offset="0%" stopColor="#fff3c4" />
          <stop offset="55%" stopColor="#ffb300" />
          <stop offset="100%" stopColor="#c97a00" />
        </radialGradient>
        <filter id="hb-glow" x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.4" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Tech rings */}
      <circle cx="100" cy="100" r="94" fill="none" stroke="#5a5e66" strokeWidth="1" opacity=".35" />
      <circle cx="100" cy="100" r="86" fill="none" stroke="#ffb300" strokeWidth=".6" opacity=".25" strokeDasharray="3 7" />

      {/* Shoulders / body */}
      <path d="M40 178 C40 142 68 130 100 130 C132 130 160 142 160 178 Z" fill="#0d0d0f" stroke="#4a4e56" strokeWidth="1.2" />
      {/* Dorsal silver stripe */}
      <path d="M86 178 C84 146 90 132 100 132 C110 132 116 146 114 178 Z" fill="url(#hb-silver)" />

      {/* Ears */}
      <circle cx="66" cy="60" r="9" fill="#0d0d0f" stroke="#4a4e56" strokeWidth="1" />
      <circle cx="134" cy="60" r="9" fill="#0d0d0f" stroke="#4a4e56" strokeWidth="1" />

      {/* Head / face */}
      <path d="M70 56 C80 46 120 46 130 56 C149 66 153 92 140 112 C130 130 110 140 100 140 C90 140 70 130 60 112 C47 92 51 66 70 56 Z" fill="#0d0d0f" stroke="#5a5e66" strokeWidth="1.3" />

      {/* White cap with fierce widow's-peak */}
      <path d="M58 84 C50 58 78 48 100 48 C122 48 150 58 142 84 C130 75 116 73 108 79 L100 94 L92 79 C84 73 70 75 58 84 Z" fill="url(#hb-silver)" />

      {/* Eyes (amber highlight) */}
      <g filter="url(#hb-glow)">
        <ellipse cx="81" cy="100" rx="9" ry="5.4" fill="url(#hb-gold)" transform="rotate(-18 81 100)" />
        <ellipse cx="119" cy="100" rx="9" ry="5.4" fill="url(#hb-gold)" transform="rotate(18 119 100)" />
      </g>
      <ellipse cx="82" cy="100" rx="3" ry="3.4" fill="#1a1300" transform="rotate(-18 82 100)" />
      <ellipse cx="118" cy="100" rx="3" ry="3.4" fill="#1a1300" transform="rotate(18 118 100)" />
      <circle cx="80" cy="98" r="1.1" fill="#fff" />
      <circle cx="116" cy="98" r="1.1" fill="#fff" />

      {/* Snout highlight + nose */}
      <path d="M88 118 C92 114 108 114 112 118 C108 126 92 126 88 118 Z" fill="#1c1c20" />
      <ellipse cx="100" cy="122" rx="6" ry="4.6" fill="#000" />
      <ellipse cx="98" cy="120" rx="1.6" ry="1.2" fill="#5a5e66" />
      <path d="M100 127 L100 132" stroke="#3a3e46" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M100 132 C95 135 92 134 90 132 M100 132 C105 135 108 134 110 132" fill="none" stroke="#3a3e46" strokeWidth="1.2" strokeLinecap="round" />

      {/* Claws highlight */}
      <g stroke="url(#hb-silver)" strokeWidth="2" strokeLinecap="round" opacity=".9">
        <path d="M70 174 L67 182" />
        <path d="M78 175 L76 183" />
        <path d="M86 175 L85 183" />
        <path d="M130 174 L133 182" />
        <path d="M122 175 L124 183" />
        <path d="M114 175 L115 183" />
      </g>

      {/* Tech accent dots */}
      <circle cx="30" cy="100" r="1.6" fill="#ffb300" opacity=".7" />
      <circle cx="170" cy="100" r="1.6" fill="#ffb300" opacity=".7" />
    </svg>
  )
}
