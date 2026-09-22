// Jubi Client - shadcn-svelte Component Types
// These types are now handled by the component definitions themselves

export interface ButtonProps {
  class?: string;
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  disabled?: boolean;
}

export interface CardProps {
  class?: string;
}

export interface InputProps {
  type?: string;
  class?: string;
  disabled?: boolean;
}

export interface TextareaProps {
  class?: string;
  disabled?: boolean;
  rows?: number;
}

export interface DialogProps {
  class?: string;
}
