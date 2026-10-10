// Original mark: a stylized fly inside a dashed radar ring.
export function Logo({ className = "size-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} aria-hidden>
      <circle cx="32" cy="32" r="26" stroke="currentColor" strokeWidth="3" strokeDasharray="6 5" className="text-brand" />
      <path d="M32 32 L32 6 A26 26 0 0 1 54.5 19 Z" fill="currentColor" className="text-brand" opacity="0.22" />
      <ellipse cx="32" cy="35" rx="4.5" ry="7.5" fill="currentColor" className="text-brand" />
      <circle cx="32" cy="25.5" r="3.4" fill="currentColor" className="text-brand" />
      <path
        d="M28 31 C19 23 15.5 30 19 34.5 C22.5 38 27 34.5 28 33Z M36 31 C45 23 48.5 30 45 34.5 C41.5 38 37 34.5 36 33Z"
        fill="currentColor"
        className="text-foreground"
        opacity="0.8"
      />
    </svg>
  );
}
