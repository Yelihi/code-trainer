import type { ComponentPropsWithRef } from 'react';
import './select.css';

export function Select({ className = '', multiple, size, ...props }: ComponentPropsWithRef<'select'>) {
  const listbox = multiple || (size !== undefined && size > 1);
  return <span className="select-field">
    <select {...props} multiple={multiple} size={size} className={`select-control ${className}`} />
    {!listbox && <span className="select-chevron" aria-hidden="true" />}
  </span>;
}
