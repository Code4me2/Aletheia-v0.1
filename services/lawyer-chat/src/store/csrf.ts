import { create } from 'zustand';
import { getApiEndpoint } from '@/lib/api-config';

interface CsrfStore {
  csrfToken: string | null;
  setCsrfToken: (token: string | null) => void;
  fetchCsrfToken: () => Promise<void>;
}

export const useCsrfStore = create<CsrfStore>((set) => ({
  csrfToken: null,
  
  setCsrfToken: (token) => set({ csrfToken: token }),
  
  fetchCsrfToken: async () => {
    try {
      const response = await fetch(`/chat${getApiEndpoint('/csrf')}`, {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        set({ csrfToken: data.csrfToken });
      } else {
        // Silently fail - error will be handled by retry logic
        set({ csrfToken: null });
      }
    } catch (error) {
      // Silently fail - error will be handled by retry logic
      set({ csrfToken: null });
    }
  }
}));