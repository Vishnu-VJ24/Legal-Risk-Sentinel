import { Separator } from 'react-resizable-panels';

export const ResizableDivider: React.FC<{ label: string }> = ({ label }) => (
  <Separator
    aria-label={label}
    className="group relative w-3 shrink-0 cursor-col-resize bg-transparent before:absolute before:inset-y-0 before:left-1/2 before:w-px before:bg-slate-300 hover:before:bg-sky-500"
  />
);
