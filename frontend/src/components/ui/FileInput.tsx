import { forwardRef, type InputHTMLAttributes } from 'react';

/** Keep the native file picker for browser security and drag/drop compatibility. */
export const FileInput = forwardRef<HTMLInputElement, Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>>(
  function FileInput(props, ref) {
    return <input {...props} ref={ref} type="file" />;
  },
);
