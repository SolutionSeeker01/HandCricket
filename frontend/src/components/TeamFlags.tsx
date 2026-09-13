import React from 'react';

export const IndiaFlag: React.FC<{ className?: string }> = ({ className = 'w-10 h-10' }) => (
  <svg viewBox="0 0 36 36" className={`${className} rounded-full shadow-md border-2 border-white/25 shrink-0`}>
    <clipPath id="tf-clip-ind">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#tf-clip-ind)">
      <rect x="0" y="0" width="36" height="12" fill="#FF9933" />
      <rect x="0" y="12" width="36" height="12" fill="#FFFFFF" />
      <rect x="0" y="24" width="36" height="12" fill="#138808" />
      <circle cx="18" cy="18" r="4.2" fill="none" stroke="#000080" strokeWidth="0.9" />
      <circle cx="18" cy="18" r="0.9" fill="#000080" />
      {Array.from({ length: 8 }).map((_, i) => (
        <line
          key={i}
          x1="18"
          y1="18"
          x2={18 + 4.2 * Math.cos((i * Math.PI) / 4)}
          y2={18 + 4.2 * Math.sin((i * Math.PI) / 4)}
          stroke="#000080"
          strokeWidth="0.6"
        />
      ))}
    </g>
  </svg>
);

export const AustraliaFlag: React.FC<{ className?: string }> = ({ className = 'w-10 h-10' }) => (
  <svg viewBox="0 0 36 36" className={`${className} rounded-full shadow-md border-2 border-white/25 shrink-0`}>
    <clipPath id="tf-clip-aus">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#tf-clip-aus)">
      <rect x="0" y="0" width="36" height="36" fill="#00008B" />
      <rect x="0" y="0" width="18" height="18" fill="#00247D" />
      <line x1="0" y1="0" x2="18" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#FFFFFF" strokeWidth="2.5" />
      <line x1="0" y1="0" x2="18" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      <line x1="18" y1="0" x2="0" y2="18" stroke="#CF142B" strokeWidth="1.2" />
      <line x1="9" y1="0" x2="9" y2="18" stroke="#FFFFFF" strokeWidth="3.5" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#FFFFFF" strokeWidth="3.5" />
      <line x1="9" y1="0" x2="9" y2="18" stroke="#CF142B" strokeWidth="1.8" />
      <line x1="0" y1="9" x2="18" y2="9" stroke="#CF142B" strokeWidth="1.8" />
      <circle cx="28" cy="8" r="1.2" fill="#FFFFFF" />
      <circle cx="23" cy="13" r="1.2" fill="#FFFFFF" />
      <circle cx="31" cy="15" r="1.2" fill="#FFFFFF" />
      <circle cx="28" cy="22" r="1.5" fill="#FFFFFF" />
      <circle cx="25" cy="29" r="1.7" fill="#FFFFFF" />
    </g>
  </svg>
);

export const EnglandFlag: React.FC<{ className?: string }> = ({ className = 'w-10 h-10' }) => (
  <svg viewBox="0 0 36 36" className={`${className} rounded-full shadow-md border-2 border-white/25 shrink-0`}>
    <clipPath id="tf-clip-eng">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#tf-clip-eng)">
      <rect x="0" y="0" width="36" height="36" fill="#FFFFFF" />
      <rect x="15" y="0" width="6" height="36" fill="#CF142B" />
      <rect x="0" y="15" width="36" height="6" fill="#CF142B" />
    </g>
  </svg>
);

export const SouthAfricaFlag: React.FC<{ className?: string }> = ({ className = 'w-10 h-10' }) => (
  <svg viewBox="0 0 36 36" className={`${className} rounded-full shadow-md border-2 border-white/25 shrink-0`}>
    <clipPath id="tf-clip-sa">
      <circle cx="18" cy="18" r="18" />
    </clipPath>
    <g clipPath="url(#tf-clip-sa)">
      <rect x="0" y="0" width="36" height="18" fill="#E03C31" />
      <rect x="0" y="18" width="36" height="18" fill="#001489" />
      <polygon points="0,0 16,18 0,36 6,36 22,18 6,0" fill="#FFFFFF" />
      <rect x="16" y="14" width="20" height="8" fill="#FFFFFF" />
      <polygon points="0,2 14,18 0,34 4,34 18,18 4,2" fill="#007749" />
      <rect x="16" y="15.5" width="20" height="5" fill="#007749" />
      <polygon points="0,5 11,18 0,31" fill="#FFB81C" />
      <polygon points="0,8 8,18 0,28" fill="#000000" />
    </g>
  </svg>
);

export const TeamFlagBadge: React.FC<{ id: string; className?: string }> = ({
  id,
  className = 'w-10 h-10',
}) => {
  const normId = id?.toUpperCase();
  if (normId === 'IND') return <IndiaFlag className={className} />;
  if (normId === 'AUS') return <AustraliaFlag className={className} />;
  if (normId === 'ENG') return <EnglandFlag className={className} />;
  if (normId === 'SA') return <SouthAfricaFlag className={className} />;
  return (
    <div className={`${className} rounded-full bg-gradient-to-br from-blue-600 to-indigo-800 border-2 border-white/25 flex items-center justify-center font-black text-xs text-white shadow-md shrink-0`}>
      {id?.slice(0, 3) || '???'}
    </div>
  );
};
