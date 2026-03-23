import { useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileUp, FileWarning, Sparkles } from 'lucide-react';
import { cn } from '../../utils/cn';

interface FileDropzoneProps {
  disabled?: boolean;
  error?: string;
  onSelect: (file: File) => void;
}

const acceptedFormats = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
};

export const FileDropzone = ({ disabled, error, onSelect }: FileDropzoneProps) => {
  const dropzone = useDropzone({
    accept: acceptedFormats,
    disabled,
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
    onDropAccepted: ([file]) => onSelect(file),
  });

  const message = useMemo(() => {
    const rejection = dropzone.fileRejections[0]?.errors[0]?.message;
    return rejection ?? error;
  }, [dropzone.fileRejections, error]);

  return (
    <div>
      <div
        {...dropzone.getRootProps()}
        className={cn(
          'group rounded-[28px] border border-dashed border-border bg-surface/85 p-8 transition focus-within:border-primary/60 hover:border-primary/60 hover:shadow-glow',
          dropzone.isDragActive && 'border-primary shadow-glow',
          disabled && 'cursor-not-allowed opacity-70',
        )}
      >
        <input {...dropzone.getInputProps()} aria-label="Upload a contract document" />
        <div className="flex flex-col items-center gap-4 text-center">
          <span className="rounded-full border border-primary/30 bg-primary/10 p-4 text-primary transition group-hover:animate-pulseRing">
            <FileUp className="h-8 w-8" />
          </span>
          <div>
            <p className="text-xl font-semibold">Drag and drop your contract</p>
            <p className="mt-2 text-sm leading-7 text-text-secondary">
              PDF, DOCX, or TXT up to 10MB. We’ll simulate parsing, risk scoring, and AI explanation generation.
            </p>
          </div>
          <button type="button" className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-white">
            <Sparkles className="h-4 w-4" />
            Choose File
          </button>
        </div>
      </div>
      {message ? (
        <p className="mt-3 inline-flex items-center gap-2 text-sm text-risk-critical">
          <FileWarning className="h-4 w-4" />
          {message}
        </p>
      ) : null}
    </div>
  );
};
