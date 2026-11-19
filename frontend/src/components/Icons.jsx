// Small line icons (inline SVG, 24x24 grid). They inherit the text colour.
const Icon = ({ children, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {children}
  </svg>
);

export const BuildingIcon = (props) => (
  <Icon {...props}>
    <rect x="4" y="3" width="16" height="18" rx="1.5" />
    <path d="M9 7h.01M15 7h.01M9 11h.01M15 11h.01M9 15h.01M15 15h.01M10 21v-3h4v3" />
  </Icon>
);

export const HomeIcon = (props) => (
  <Icon {...props}>
    <path d="M3 10.5 12 3l9 7.5" />
    <path d="M5 9.5V21h14V9.5" />
    <path d="M10 21v-6h4v6" />
  </Icon>
);

export const SparkleIcon = (props) => (
  <Icon {...props}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
    <path d="M19 17l.7 1.8 1.8.7-1.8.7L19 22l-.7-1.8-1.8-.7 1.8-.7z" />
  </Icon>
);

export const ArrowRightIcon = (props) => (
  <Icon {...props}><path d="M5 12h14M13 6l6 6-6 6" /></Icon>
);

export const SendIcon = (props) => (
  <Icon {...props}><path d="M12 19V5M5 12l7-7 7 7" /></Icon>
);

export const ChevronDownIcon = (props) => (
  <Icon {...props}><path d="m6 9 6 6 6-6" /></Icon>
);

export const StopIcon = (props) => (
  <Icon {...props}><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" /></Icon>
);

export const CopyIcon = (props) => (
  <Icon {...props}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15V6a2 2 0 0 1 2-2h9" />
  </Icon>
);

export const CheckIcon = (props) => (
  <Icon {...props}><path d="m5 12 5 5 9-10" /></Icon>
);

export const RetryIcon = (props) => (
  <Icon {...props}>
    <path d="M4 12a8 8 0 0 1 13.7-5.7L20 8.5" />
    <path d="M20 4v4.5h-4.5" />
    <path d="M20 12a8 8 0 0 1-13.7 5.7L4 15.5" />
    <path d="M4 20v-4.5h4.5" />
  </Icon>
);

export const PlusIcon = (props) => (
  <Icon {...props}><path d="M12 5v14M5 12h14" /></Icon>
);

export const HistoryIcon = (props) => (
  <Icon {...props}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 3v5h5" />
    <path d="M12 7v5l3 2" />
  </Icon>
);

export const TrashIcon = (props) => (
  <Icon {...props}>
    <path d="M4 7h16M10 11v6M14 11v6" />
    <path d="M6 7l1 13h10l1-13M9 7V4h6v3" />
  </Icon>
);

export const CloseIcon = (props) => (
  <Icon {...props}><path d="M6 6l12 12M18 6 6 18" /></Icon>
);

export const ChatIcon = (props) => (
  <Icon {...props}><path d="M4 5h16v11H9l-5 4z" /></Icon>
);

export const LinkIcon = (props) => (
  <Icon {...props}>
    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
  </Icon>
);
